"""The rubric: hard PASS/FAIL checkpoints. No scores, no partial credit.

Design rules
------------
* Every checkpoint is a yes/no question.
* `kind` says WHO judges it:
    - "code"     -> deterministic Python (src/checks.py). Cheap, exact, cannot be talked into passing.
    - "llm"      -> a reviewer model (needs understanding of meaning).
    - "code+llm" -> both must pass.
* `fix_hint` is sent back to the generator on a retry, so a failure always comes with a concrete direction.
* The rubric is changed only by a human (and the version below is bumped).
  The self-evolving loop is NOT allowed to edit it, otherwise the system could make its own exam easier.
"""
from __future__ import annotations

from dataclasses import dataclass

RUBRIC_VERSION = "1.2"  # 1.1: C2 fails on invented facts. 1.2: C3 code half accepts glossary-style definitions ("Term - meaning")


@dataclass(frozen=True)
class Check:
    id: str
    name: str
    question: str
    kind: str  # "code" | "llm" | "code+llm"
    fix_hint: str

    @property
    def uses_llm(self) -> bool:
        return "llm" in self.kind

    @property
    def uses_code(self) -> bool:
        return "code" in self.kind


CHECKS: list[Check] = [
    Check(
        "C1", "Covers the key points",
        "Does the lesson clearly explain WHAT the topic is, WHY it matters and HOW it works "
        "(all three present, each with real content)?",
        "llm",
        "Make sure the lesson explains what it is, why it matters and how it works, each with real detail.",
    ),
    Check(
        "C2", "Accurate and grounded",
        "Is EVERY factual statement consistent with the reference notes? "
        "FAIL if any statement contradicts the notes or states a confident claim the notes do not support "
        "(for example saying RAG retrains or fine-tunes the model). Also FAIL if the lesson invents specific "
        "real-world facts, such as a price, fare, date or statistic, or attributes data to a real organization.",
        "llm",
        "Remove or correct every statement that is not supported by the reference notes. Do not invent facts.",
    ),
    Check(
        "C3", "No unexplained jargon, simple words",
        "Is every technical term explained the first time it is used, and is the vocabulary simple enough for "
        "a 12th-grade learner with limited English (no idioms, no slang, no unexplained abbreviations)?",
        "code+llm",
        "Explain each technical term in the same sentence where it first appears. Replace hard words and idioms "
        "with simple everyday words.",
    ),
    Check(
        "C4", "Short, easy sentences",
        "Is the average sentence length at most 15 words, with at most 10% of sentences longer than 25 words?",
        "code",
        "Split long sentences. Aim for one idea per sentence, about 10 to 14 words.",
    ),
    Check(
        "C5", "Teaches by example",
        "Does the lesson contain at least 2 concrete, worked examples, at least one from everyday Indian life, "
        "plus a simple analogy?",
        "llm",
        "Add concrete worked examples from everyday Indian life (college, exams, schemes, banks) and one analogy.",
    ),
    Check(
        "C6", "Coherent teaching flow",
        "Are the sections Hook, What Is It?, Why It Matters, How It Works, Example, Recap, Check Yourself all "
        "present in that order, and does each section build on the one before it (no jumps, no repeats)?",
        "code+llm",
        "Use exactly the required level-2 headings in the required order. Each section must build on the previous one.",
    ),
    Check(
        "C7", "Recap and self-check",
        "Does the Recap have at least 3 points and does Check Yourself have at least 3 questions that end with '?'",
        "code",
        "Add a Recap with 4 to 6 bullet points and a Check Yourself section with exactly 3 numbered questions.",
    ),
    Check(
        "C8", "Right length",
        "Is the lesson between 500 and 1200 words?",
        "code",
        "Keep the lesson between 600 and 1000 words.",
    ),
]

CHECK_BY_ID = {c.id: c for c in CHECKS}
LLM_CHECK_IDS = [c.id for c in CHECKS if c.uses_llm]
CODE_CHECK_IDS = [c.id for c in CHECKS if c.uses_code]


def checkpoints_text(ids: list[str] | None = None) -> str:
    """Rubric text that goes into the evaluator prompt."""
    rows = []
    for c in CHECKS:
        if ids is None or c.id in ids:
            rows.append(f"{c.id} - {c.name}: {c.question}")
    return "\n".join(rows)