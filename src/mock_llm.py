"""A fake LLM for testing the PLUMBING (loop, logging, memory) with no API key and no internet.

It is a simulation, NOT a measure of quality. Real runs use src/llm.py.
How it behaves:
  generate : attempt 1 = a deliberately bad lesson, attempt 2 = a nearly good lesson,
             attempt 3 = a good lesson. If learned rules exist in memory, it starts one step better
             (this imitates the self-evolving effect so you can see the plumbing work offline).
             If the only failed check is C2 (wrong fact), it returns the good lesson at once.
  evaluate : simple keyword rules for the LLM-judged checks (C1, C2, C3, C5, C6).
  others   : canned replies.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .llm import Usage

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"

CANNED_RULES = {
    "C1": "Always include one short paragraph each for what it is, why it matters and how it works.",
    "C2": "State only facts that appear in the reference notes. Never say the model is retrained or fine-tuned.",
    "C3": "Explain every technical term in the same sentence where it first appears, using an everyday comparison.",
    "C4": "Write sentences of 8 to 14 words. Split any sentence that has more than one idea.",
    "C5": "Give two worked examples from Indian student life, such as a college helpdesk and a scholarship form.",
    "C6": "Use the seven required headings exactly, in order, and end every section with a bridge to the next one.",
    "C7": "End with a Recap of 4 to 6 bullets and a Check Yourself section of exactly 3 numbered questions.",
    "C8": "Keep the whole lesson between 600 and 1000 words.",
}

EXAMPLE_MARKERS = re.compile(r"example|imagine|for instance|suppose", re.IGNORECASE)


def _good() -> str:
    return (EXAMPLES / "good_lesson.md").read_text(encoding="utf-8")


def _bad() -> str:
    return (EXAMPLES / "mock" / "attempt1_bad.md").read_text(encoding="utf-8")


def _partial() -> str:
    """The good lesson without the Check Yourself section (so C6 and C7 fail)."""
    return re.split(r"\n## Check Yourself", _good())[0].rstrip() + "\n"


def _retrain_claim(text):
    sentences = re.split(r"(?<=[.!?])\s+", text)

    retrain_pattern = re.compile(
        r"\b(retrain\w*|fine[- ]tun\w*)\b",
        re.IGNORECASE
    )

    for sentence in sentences:
        # Only flag a retraining claim when it is about RAG.
        if not re.search(r"\bRAG\b", sentence, re.IGNORECASE):
            continue

        if not retrain_pattern.search(sentence):
            continue

        # Ignore explicit statements denying retraining.
        if re.search(
            r"\b(does not|do not|doesn't|don't|never|without|no need to)\b",
            sentence,
            re.IGNORECASE
        ):
            continue

        return True

    return False


class MockLLM:
    provider = "mock"
    model = "mock-1"

    def __init__(self) -> None:
        self.usage = Usage()

    def chat(self, system: str, user: str, temperature: float | None = None, task: str = "") -> str:
        self.usage.add(0, 0)
        if task == "generate":
            return self._generate(user)
        if task == "evaluate":
            return self._evaluate(user)
        if task == "summarize":
            ids = self._failed_ids(user)
            return f"(mock) Rewrote the lesson to fix: {', '.join(ids) or 'the reported problems'}."
        if task == "rubric_proposal":
            return "(mock) The check wording may be ambiguous; consider listing exact examples of what counts as a failure."
        if task == "refine":
            m = re.search(r"CHECK_ID:\s*(C\d)", user)
            return CANNED_RULES.get(m.group(1) if m else "", "Follow the checkpoints exactly.")
        return ""

    # -------------------------------------------------------------------------------------------
    @staticmethod
    def _failed_ids(user: str) -> list[str]:
        m = re.search(r"FAILED_CHECKS:\s*([C0-9, ]*)", user)
        return [x.strip() for x in m.group(1).split(",") if x.strip()] if m else []

    def _generate(self, user: str) -> str:
        attempt = int(re.search(r"ATTEMPT:\s*(\d+)", user).group(1))
        rules = int((re.search(r"LEARNED_RULES_COUNT:\s*(\d+)", user) or [0, "0"])[1])
        failed = self._failed_ids(user)
        if failed and set(failed) <= {"C2"}:
            return _good()
        n = attempt + (1 if rules > 0 else 0)
        return _bad() if n <= 1 else _partial() if n == 2 else _good()

    def _evaluate(self, user: str) -> str:
        m = re.search(r"<lesson>(.*?)</lesson>", user, re.S)
        text = m.group(1) if m else ""
        low = text.lower()
        has = {k: bool(re.search(r"^##\s+.*\b" + k + r"\b", low, re.M)) for k in ("what", "why", "how")}
        c1 = all(has.values())
        c2 = not _retrain_claim(text) and "Indian Railways" not in text
        examples = len(EXAMPLE_MARKERS.findall(text))
        c5 = examples >= 3
        c6 = has["what"] and has["why"] and has["how"]
        out = [
            {"id": "C1", "pass": c1, "reason": "what/why/how all present" if c1 else
             "One of the sections What, Why or How is missing."},
            {"id": "C2", "pass": c2, "reason": "No claim contradicts the notes." if c2 else
             "The lesson makes a claim that the notes do not support (retraining, or an invented real-world fact)."},
            {"id": "C3", "pass": True, "reason": "Vocabulary looks simple (mock)."},
            {"id": "C5", "pass": c5, "reason": "Two or more examples found." if c5 else
             "Fewer than two concrete examples were found."},
            {"id": "C6", "pass": c6, "reason": "Sections build on each other (mock)." if c6 else
             "The flow is broken because core sections are missing."},
        ]
        return json.dumps({"checks": out})