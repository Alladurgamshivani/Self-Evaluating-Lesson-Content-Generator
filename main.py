#!/usr/bin/env python3
"""Self-Evaluating Lesson Content Generator: command line interface.

Examples
  python main.py --mock                              # no API key needed, tests the whole loop offline
  python main.py --topic "Introduction to RAG"       # real run (needs an API key in .env)
  python main.py --inject-error                      # deliberate error demo for the video
  python main.py --eval-suite                        # test the evaluator against known-bad lessons
  python main.py --show-memory                       # print what the system has learned
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src import llm as llm_mod
from src.eval_suite import GOOD, inject_error, run_suite
from src.evaluator import evaluate
from src.graph import HAVE_LANGGRAPH, Context, build_app, new_run_id
from src.memory import Memory
from src.mock_llm import MockLLM

ROOT = Path(__file__).resolve().parent


def build_context(args) -> Context:
    llm_mod.load_env()
    if args.mock:
        gen = eval_ = MockLLM()
    else:
        usage = llm_mod.Usage()
        gen = llm_mod.LLM.from_env("generator", usage)
        eval_ = llm_mod.LLM.from_env("evaluator", usage)
        print(f"[setup] generator: {gen.provider}/{gen.model} | evaluator: {eval_.provider}/{eval_.model}")
    memory_dir = Path(args.memory_dir or (ROOT / ("memory_mock" if args.mock else "memory")))
    out_dir = Path(args.out_dir or (ROOT / ("outputs/mock_run" if args.mock else "outputs")))
    return Context(
        gen_llm=gen, eval_llm=eval_, memory=Memory(memory_dir), out_dir=out_dir,
        reference_notes=(ROOT / "prompts" / "reference_notes.md").read_text(encoding="utf-8"),
        generator_prompt=(ROOT / "prompts" / "generator_v1.md").read_text(encoding="utf-8"),
        evaluator_prompt=(ROOT / "prompts" / "evaluator_v1.md").read_text(encoding="utf-8"),
        glossary_lang=args.glossary, mock=args.mock,
    )


def _run() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--topic", default="Introduction to RAG (Retrieval-Augmented Generation)")
    p.add_argument("--max-retries", type=int, default=2, help="retries after the first attempt (default 2)")
    p.add_argument("--mock", action="store_true", help="use a fake model: tests plumbing with no API key")
    p.add_argument("--inject-error", action="store_true", help="start from a lesson with a deliberate wrong fact")
    p.add_argument("--eval-suite", action="store_true", help="check the evaluator against known-bad lessons")
    p.add_argument("--evaluate-only", metavar="FILE", help="just evaluate a lesson file and print the verdict")
    p.add_argument("--show-memory", action="store_true", help="print learned rules and run history")
    p.add_argument("--reset-memory", action="store_true", help="delete learned rules and history")
    p.add_argument("--glossary", metavar="LANGUAGE", help="bonus: append a glossary in e.g. Telugu or Hindi")
    p.add_argument("--memory-dir"); p.add_argument("--out-dir")
    p.add_argument("--no-langgraph", action="store_true", help="force the built-in fallback runner")
    args = p.parse_args()
    args.max_retries = max(0, min(args.max_retries, 3))  # hard cap: the loop must stay cheap and finite

    try:
        ctx = build_context(args)
    except llm_mod.LLMError as e:
        print(f"Setup problem: {e}", file=sys.stderr)
        return 2

    if args.reset_memory:
        ctx.memory.reset(); print("Memory cleared."); return 0
    if args.show_memory:
        print("LEARNED RULES"); [print(f"  {r['id']} [{r['check_id']}] {r['rule']}") for r in ctx.memory.rules()]
        print("\nRUBRIC PROPOSALS (never applied automatically)"); [print(f"  {p['id']} [{p['check_id']}] {p['status']}: {p['proposal']}") for p in ctx.memory.proposals()]
        print("\nFAILURE COUNTS PER CHECK", dict(ctx.memory.failure_counts()))
        print("RUNS"); [print(f"  {r['run_id']} {r['topic'][:30]:30} attempts={r['attempts']} passed={r['passed']}") for r in ctx.memory.history()]
        return 0
    if args.eval_suite:
        return 0 if run_suite(ctx.reference_notes, ctx.eval_llm, ctx.evaluator_prompt) else 1
    if args.evaluate_only:
        text = Path(args.evaluate_only).read_text(encoding="utf-8")
        ev = evaluate(text, ctx.reference_notes, ctx.eval_llm, ctx.evaluator_prompt)
        for c in ev["checks"]:
            print(f"{c['id']} {'PASS' if c['pass'] else 'FAIL'}  {c['name']}: {c['reason']}")
        print("OVERALL:", "PASS" if ev["overall_pass"] else "FAIL")
        return 0 if ev["overall_pass"] else 1

    engine = "LangGraph" if HAVE_LANGGRAPH and not args.no_langgraph else "built-in fallback runner (langgraph not installed)"
    print(f"[setup] workflow engine: {engine}\n[setup] topic: {args.topic}\n")
    state = {"topic": args.topic, "run_id": new_run_id(), "max_retries": args.max_retries}
    if args.inject_error:
        base = GOOD  # always start from the known-good lesson, never from an earlier flagged output
        state["seed_lesson"] = inject_error(base)
        print("[inject-error] a wrong sentence was planted: 'RAG works by retraining the model on your documents.'\n")

    result = build_app(ctx, force_fallback=args.no_langgraph).invoke(state)
    print(f"\nDone. Status: {result['status']}")
    print(f"  Lesson:        {ctx.out_dir / 'final_lesson.md'}")
    print(f"  Rejection log: {ctx.out_dir / 'rejection_log.md'}")
    if result["status"] != "PASSED":
        print("  WARNING: no attempt passed all checks. Review the rejection log before using this lesson.")
    return 0 if result["status"] == "PASSED" else 1


def main() -> int:
    try:
        return _run()
    except llm_mod.LLMError as e:  # API problems print one clear line instead of a long traceback
        print(f"\nModel call failed: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())