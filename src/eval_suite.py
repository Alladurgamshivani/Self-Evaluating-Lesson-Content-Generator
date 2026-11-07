"""Test the TESTER. Deliberately broken lessons that the evaluator MUST reject.

This is the "evaluation instinct" in practice: never assume the evaluator works, prove it.
Each case starts from a known-good lesson, breaks exactly one thing, and states which checkpoint should fail.
A "control" case (the untouched good lesson) must pass, so we also catch an evaluator that fails everything.
"""
from __future__ import annotations

import re
import time
from pathlib import Path

from .evaluator import evaluate

ROOT = Path(__file__).resolve().parent.parent
GOOD = (ROOT / "examples" / "good_lesson.md").read_text(encoding="utf-8")

WRONG_FACT_SENTENCE = "RAG works by retraining the model on your documents."


def _wrong_fact(t: str) -> str:
    return t.replace("RAG does not retrain the model.", WRONG_FACT_SENTENCE)


def _long_sentences(t: str) -> str:
    out = []
    for line in t.splitlines():
        if line.startswith("#") or not line.strip():
            out.append(line)
        else:
            out.append(re.sub(r"\.\s+", ", and because of that, ", line))
    return "\n".join(out)


def _no_recap(t: str) -> str:
    return re.split(r"\n## Recap", t)[0].rstrip() + "\n"


def _jargon_first(t: str) -> str:
    return t.replace(
        "## Hook\n\n",
        "## Hook\n\nToday we study RAG with an LLM, embeddings, a vector database and hallucination checks. ",
        1,
    )


def _invented_facts(t: str) -> str:
    return t.replace(
        "You do not need to train the AI again.",
        "You do not need to train the AI again. The Indian Railways senior citizen fare from Delhi to Jaipur is 540 rupees.",
        1,
    )


def _no_examples(t: str) -> str:
    t = re.sub(r"\n## Example\n.*?\n## Recap", "\n## Recap", t, flags=re.S)
    t = re.sub(r"[^.\n]*\b(Imagine|example|Example)\b[^.\n]*\.", "", t)
    return t


# (case name, function that breaks the good lesson, checkpoints that MUST fail; empty = must pass)
CASES = [
    ("control_good_lesson", lambda t: t, []),
    ("wrong_fact_retraining", _wrong_fact, ["C2"]),
    ("run_on_sentences", _long_sentences, ["C4"]),
    ("missing_recap_and_quiz", _no_recap, ["C7"]),
    ("jargon_before_definition", _jargon_first, ["C3"]),
    ("no_examples", _no_examples, ["C5"]),
    ("invented_real_world_fact", _invented_facts, ["C2"]),
]


def _judge(lesson: str, reference_notes: str, llm, prompt_template: str, say) -> dict:
    """Evaluate; if the JUDGE itself broke (rate limit, empty reply), try again before giving up."""
    ev = evaluate(lesson, reference_notes, llm, prompt_template)
    for _ in range(2):
        if not ev.get("evaluator_error"):
            break
        say("   (the reviewer returned no valid verdict; trying again)")
        time.sleep(0 if getattr(llm, "provider", "") == "mock" else 20)
        ev = evaluate(lesson, reference_notes, llm, prompt_template)
    return ev


def run_suite(reference_notes: str, llm, prompt_template: str, say=print) -> bool:
    all_ok = True
    say(f"{'case':28} {'expected':14} {'actually failed':30} result")
    say("-" * 86)
    for name, mutate, expected in CASES:
        ev = _judge(mutate(GOOD), reference_notes, llm, prompt_template, say)
        failed = ev["failed_ids"]
        if ev.get("evaluator_error"):
            result, ok = "INCONCLUSIVE (the reviewer kept failing, not a lesson problem)", False
        else:
            ok = set(expected) <= set(failed) if expected else not failed
            result = "OK" if ok else "EVALUATOR MISSED IT" if expected else "FALSE ALARM ON GOOD LESSON"
        all_ok &= ok
        say(f"{name:28} {','.join(expected) or 'PASS':14} {','.join(failed) or 'none':30} {result}")
        if getattr(llm, "provider", "") != "mock":
            time.sleep(3)  # be gentle with free-tier rate limits
    say("-" * 86)
    say("Evaluator is behaving as designed." if all_ok else "Evaluator has a blind spot or was inconclusive: see rows above.")
    return all_ok


def inject_error(lesson: str) -> str:
    """Used by `main.py --inject-error`: put one wrong sentence into a good lesson."""
    if "RAG does not retrain the model." in lesson:
        return lesson.replace("RAG does not retrain the model.", WRONG_FACT_SENTENCE)
    return lesson.replace("## How It Works\n", "## How It Works\n\n" + WRONG_FACT_SENTENCE + "\n", 1)