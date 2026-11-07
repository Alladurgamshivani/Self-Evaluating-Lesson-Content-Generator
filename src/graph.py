"""The workflow: generate -> evaluate -> (fail? log + regenerate) -> finalize -> update memory.

                 +-----------------------------------------------+
                 |                                               |
START -> load_memory -> generate -> evaluate -- pass ----------> finalize -> update_memory -> END
                          ^            |
                          |            +-- fail, retries left --> log_rejection --+
                          +------------------------------------------------------+
                                       +-- fail, no retries left -> finalize (best attempt, flagged)

The loop ALWAYS ends: it stops when the lesson passes or when max_retries is used up.

LangGraph is used when installed. If it is missing, a tiny fallback runner executes the SAME node functions
in the SAME order, so behaviour and tests are identical.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, TypedDict

from .evaluator import evaluate, format_feedback, score_line
from .generator import generate_lesson, make_glossary, summarize_changes
from .memory import Memory
from .refiner import learn_from_history, propose_rubric_changes
from .reporting import build_rejection_log
from .rubric import RUBRIC_VERSION

try:  # LangGraph is optional at import time
    from langgraph.graph import END, StateGraph
    HAVE_LANGGRAPH = True
except ImportError:  # pragma: no cover
    HAVE_LANGGRAPH = False

ROOT = Path(__file__).resolve().parent.parent


class State(TypedDict, total=False):
    topic: str
    seed_lesson: str            # optional: start from this lesson instead of generating (used by --inject-error)
    run_id: str
    max_retries: int
    memory_rules: list
    attempts: list              # [{"attempt": 1, "lesson": "...", "eval": {...}}]
    rejection_log: list         # [{"attempt": 1, "failed": [...], "what_changed": "..."}]
    retry_count: int
    final_lesson: str
    status: str                 # PASSED | NEEDS_HUMAN_REVIEW
    new_rules: list
    pending_lesson: str         # scratch: handed from generate to evaluate


@dataclass
class Context:
    gen_llm: object
    eval_llm: object
    memory: Memory
    out_dir: Path
    reference_notes: str
    generator_prompt: str
    evaluator_prompt: str
    say: Callable[[str], None] = print
    glossary_lang: str | None = None
    mock: bool = False
    usage_objects: list = field(default_factory=list)

    def usage(self) -> dict:
        calls = pt = ct = 0
        for u in {id(l.usage): l.usage for l in (self.gen_llm, self.eval_llm)}.values():
            d = u.as_dict()
            calls += d["calls"]; pt += d["prompt_tokens"]; ct += d["completion_tokens"]
        return {"calls": calls, "prompt_tokens": pt, "completion_tokens": ct}


# ----------------------------------------------------------------------------------------------
# routing (kept as a plain function so it is easy to unit-test and to explain)
# ----------------------------------------------------------------------------------------------
def route_after_evaluate(state: State) -> str:
    last = state["attempts"][-1]["eval"]
    if last["overall_pass"]:
        return "finalize"
    if len(state["attempts"]) >= state["max_retries"] + 1:  # 1 first try + max_retries retries
        return "finalize"
    return "log_rejection"


# ----------------------------------------------------------------------------------------------
def make_nodes(ctx: Context) -> dict[str, Callable[[State], dict]]:
    def load_memory(state: State) -> dict:
        rules = ctx.memory.top_rules()
        ctx.say(f"[memory] loaded {len(rules)} learned rule(s) and {len(ctx.memory.history())} past run(s)")
        for r in rules:
            ctx.say(f"   - {r}")
        return {"memory_rules": rules, "attempts": [], "rejection_log": [], "retry_count": 0}

    def generate(state: State) -> dict:
        attempts = state["attempts"]
        n = len(attempts) + 1
        prev = attempts[-1] if attempts else None
        if n == 1 and state.get("seed_lesson"):
            ctx.say(f"[attempt {n}] using the provided seed lesson (no generation call)")
            return {"pending_lesson": state["seed_lesson"]}
        ctx.say(f"[attempt {n}] generating lesson..." if n == 1 else f"[attempt {n}] regenerating with feedback...")
        feedback = format_feedback(prev["eval"]) if prev else None
        failed = prev["eval"]["failed_ids"] if prev else None
        lesson = generate_lesson(
            ctx.gen_llm, ctx.generator_prompt, ctx.reference_notes, state["topic"], n,
            state["memory_rules"], prev["lesson"] if prev else None, feedback, failed,
        )
        update: dict = {"pending_lesson": lesson}
        if prev:  # fill in "what changed" for the previous rejection
            changed = summarize_changes(ctx.gen_llm, prev["lesson"], lesson, failed, feedback)
            log = [dict(r) for r in state["rejection_log"]]
            log[-1]["what_changed"] = changed
            update["rejection_log"] = log
            ctx.say(f"   what changed: {changed}")
        return update

    def evaluate_node(state: State) -> dict:
        n = len(state["attempts"]) + 1
        lesson = state["pending_lesson"]
        ev = evaluate(lesson, ctx.reference_notes, ctx.eval_llm, ctx.evaluator_prompt)
        # If the JUDGE broke (rate limit, empty reply), judge the same lesson again.
        # A broken judge must not use up a generation retry or count as a lesson failure.
        for again in range(2):
            if not ev.get("evaluator_error"):
                break
            ctx.say(f"[attempt {n}] the reviewer returned no valid verdict; re-evaluating the same lesson ({again + 1}/2)")
            time.sleep(0 if ctx.mock else 20)
            ev = evaluate(lesson, ctx.reference_notes, ctx.eval_llm, ctx.evaluator_prompt)
        verdict = "PASS" if ev["overall_pass"] else "FAIL " + ", ".join(ev["failed_ids"])
        ctx.say(f"[attempt {n}] evaluated: {score_line(ev)} -> {verdict}")
        for c in ev["checks"]:
            if not c["pass"]:
                ctx.say(f"   x {c['id']} {c['name']}: {c['reason'][:200]}")
        attempts = state["attempts"] + [{"attempt": n, "lesson": lesson, "eval": ev}]
        return {"attempts": attempts}

    def log_rejection(state: State) -> dict:
        last = state["attempts"][-1]
        failed = [{"id": c["id"], "name": c["name"], "reason": c["reason"]} for c in last["eval"]["checks"] if not c["pass"]]
        log = state["rejection_log"] + [{"attempt": last["attempt"], "failed": failed, "what_changed": ""}]
        return {"rejection_log": log, "retry_count": state["retry_count"] + 1}

    def finalize(state: State) -> dict:
        attempts = state["attempts"]
        passing = [a for a in attempts if a["eval"]["overall_pass"]]
        trusted = [a for a in attempts if not a["eval"].get("evaluator_error")] or attempts
        if passing:
            best, status = passing[0], "PASSED"
        else:  # no pass: ship the attempt with the most passed checks, but flag it
            best = max(trusted, key=lambda a: sum(c["pass"] for c in a["eval"]["checks"]))
            status = "NEEDS_HUMAN_REVIEW"
        lesson = best["lesson"]
        if status == "PASSED" and ctx.glossary_lang and not ctx.mock:
            ctx.say(f"[finalize] adding {ctx.glossary_lang} glossary (bonus, added after evaluation)")
            lesson = lesson.rstrip() + f"\n\n## Glossary ({ctx.glossary_lang})\n\n" + make_glossary(ctx.gen_llm, lesson, ctx.glossary_lang) + "\n"
        ctx.say(f"[finalize] status: {status} (attempt {best['attempt']} shipped)")
        return {"final_lesson": lesson, "status": status}

    def update_memory(state: State) -> dict:
        ctx.out_dir.mkdir(parents=True, exist_ok=True)
        (ctx.out_dir / "runs").mkdir(exist_ok=True)
        attempts = state["attempts"]
        usage = ctx.usage()

        (ctx.out_dir / "final_lesson.md").write_text(state["final_lesson"], encoding="utf-8")
        log_md = build_rejection_log(state["topic"], state["run_id"], attempts, state["rejection_log"],
                                     state["status"], usage, RUBRIC_VERSION, state["max_retries"])
        (ctx.out_dir / "rejection_log.md").write_text(log_md, encoding="utf-8")
        (ctx.out_dir / "runs" / f"{state['run_id']}.json").write_text(
            json.dumps({"state": {k: v for k, v in state.items() if k != "pending_lesson"}, "usage": usage},
                       indent=2, ensure_ascii=False), encoding="utf-8")

        reasons: dict[str, list[str]] = {}
        for a in attempts:
            for c in a["eval"]["checks"]:
                if not c["pass"] and "[evaluator error]" not in c["reason"]:
                    reasons.setdefault(c["id"], []).append(c["reason"][:300])
        ctx.memory.append_run({
            "run_id": state["run_id"], "topic": state["topic"],
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "mode": "mock" if ctx.mock else f"{getattr(ctx.gen_llm, 'provider', '?')}/{getattr(ctx.gen_llm, 'model', '?')}",
            "attempts": len(attempts), "passed": state["status"] == "PASSED",
            "failed_per_attempt": [[c["id"] for c in a["eval"]["checks"]
                                    if not c["pass"] and "[evaluator error]" not in c["reason"]] for a in attempts],
            "injected": bool(state.get("seed_lesson")),
            "reasons": reasons, "usage": usage, "rubric_version": RUBRIC_VERSION,
        })
        new_rules = learn_from_history(ctx.memory, ctx.gen_llm, ctx.say)
        propose_rubric_changes(ctx.memory, ctx.gen_llm, ctx.say)
        ctx.say(f"[memory] run saved. Rules in memory: {len(ctx.memory.rules())}. LLM calls this run: {usage['calls']}")
        return {"new_rules": new_rules}

    return {
        "load_memory": load_memory, "generate": generate, "evaluate": evaluate_node,
        "log_rejection": log_rejection, "finalize": finalize, "update_memory": update_memory,
    }


# ----------------------------------------------------------------------------------------------
class _FallbackApp:
    """Same flow as the LangGraph graph, used only when langgraph is not installed."""

    def __init__(self, nodes):
        self.nodes = nodes

    def invoke(self, state: State) -> State:
        s = dict(state)
        s.update(self.nodes["load_memory"](s))
        while True:
            s.update(self.nodes["generate"](s))
            s.update(self.nodes["evaluate"](s))
            if route_after_evaluate(s) == "finalize":
                break
            s.update(self.nodes["log_rejection"](s))
        s.update(self.nodes["finalize"](s))
        s.update(self.nodes["update_memory"](s))
        return s  # type: ignore[return-value]


def build_app(ctx: Context, force_fallback: bool = False):
    nodes = make_nodes(ctx)
    if HAVE_LANGGRAPH and not force_fallback:
        g = StateGraph(State)
        for name, fn in nodes.items():
            g.add_node(name, fn)
        g.set_entry_point("load_memory")
        g.add_edge("load_memory", "generate")
        g.add_edge("generate", "evaluate")
        g.add_conditional_edges("evaluate", route_after_evaluate,
                                {"finalize": "finalize", "log_rejection": "log_rejection"})
        g.add_edge("log_rejection", "generate")
        g.add_edge("finalize", "update_memory")
        g.add_edge("update_memory", END)
        return g.compile()
    return _FallbackApp(nodes)


def new_run_id() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")