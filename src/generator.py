"""The generator: writes (or rewrites) the lesson."""
from __future__ import annotations

import re
import difflib

def build_system_prompt(template: str, reference_notes: str, rules: list[str]) -> str:
    if rules:
        rules_block = "LEARNED RULES (from past failures, follow them strictly)\n" + "\n".join(f"- {r}" for r in rules)
    else:
        rules_block = ""
    return template.replace("{rules}", rules_block).replace("{reference_notes}", reference_notes)


def build_user_prompt(topic: str, attempt: int, rules: list[str], prev_lesson: str | None = None,
                      feedback: str | None = None, failed_ids: list[str] | None = None) -> str:
    # The three header lines are also machine-readable (the mock model uses them).
    head = (
        f"TOPIC: {topic}\n"
        f"ATTEMPT: {attempt}\n"
        f"LEARNED_RULES_COUNT: {len(rules)}\n"
        f"FAILED_CHECKS: {', '.join(failed_ids or [])}\n\n"
    )
    if not prev_lesson:
        return head + f"Write the beginner lesson on: {topic}. Assume the learner starts from zero."
    return (
        head
        + f"Your previous lesson on '{topic}' was REJECTED by the quality reviewer.\n\n"
        + "<previous_lesson>\n" + prev_lesson + "\n</previous_lesson>\n\n"
        + "FAILED CHECKPOINTS AND REASONS\n" + (feedback or "") + "\n\n"
        + "Rewrite the lesson. Fix ONLY the failed checkpoints and keep everything that already passes. "
        + "Follow all the language rules again. Return only the full corrected lesson in Markdown."
    )


def clean_output(text: str) -> str:
    """Remove accidental ```markdown fences and chatty preambles."""
    text = text.strip()
    text = re.sub(r"^```(?:markdown|md)?\s*\n", "", text)
    text = re.sub(r"\n```\s*$", "", text)
    idx = text.find("# ")
    if idx > 0 and idx < 400 and not text.lstrip().startswith("#"):
        text = text[idx:]  # drop "Sure! Here is your lesson:" style intro
    return text.strip() + "\n"


def generate_lesson(llm, system_template: str, reference_notes: str, topic: str, attempt: int,
                    rules: list[str], prev_lesson: str | None = None, feedback: str | None = None,
                    failed_ids: list[str] | None = None) -> str:
    system = build_system_prompt(system_template, reference_notes, rules)
    user = build_user_prompt(topic, attempt, rules, prev_lesson, feedback, failed_ids)
    return clean_output(llm.chat(system, user, task="generate"))


def summarize_changes(llm, prev, new, failed_ids, feedback):
    """Summarize lesson changes locally without another LLM call."""

    diff = list(
        difflib.unified_diff(
            prev.splitlines(),
            new.splitlines(),
            lineterm="",
            n=0
        )
    )

    removed = [
        line[1:].strip()[:180]
        for line in diff
        if line.startswith("-") and not line.startswith("---")
    ]

    added = [
        line[1:].strip()[:180]
        for line in diff
        if line.startswith("+") and not line.startswith("+++")
    ]

    parts = [
        f"Changes made after failing: {', '.join(failed_ids)}."
    ]

    if removed:
        parts.append("Removed or replaced: " + " | ".join(removed[:2]))

    if added:
        parts.append("Added or updated: " + " | ".join(added[:2]))

    return " ".join(parts)


def make_glossary(llm, lesson: str, language: str) -> str:
    """Optional bonus: a small glossary in the learner's own language (the company teaches in vernacular)."""
    system = "You write clear glossaries for beginners."
    user = (
        f"From this lesson, list 8 key terms. For each give: the English term, then its meaning in simple {language}. "
        f"Use a Markdown table with columns English | {language}. Return only the table.\n\n{lesson}"
    )
    return llm.chat(system, user, temperature=0.2, task="glossary").strip()
