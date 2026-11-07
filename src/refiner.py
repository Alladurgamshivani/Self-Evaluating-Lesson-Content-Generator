"""The self-evolving step.

After every run we look at the failure history. If a checkpoint keeps failing, an LLM writes ONE new,
specific rule for the generator prompt. Rules are stored in memory and injected on every later run.

Safety decisions (explain these in your video):
  * The refiner can add rules to the GENERATOR prompt only. It can never edit the rubric or the evaluator,
    so the system cannot make its own exam easier.
  * A rule is added only after a repeated failure (threshold), not after a single unlucky run.
  * Rule text is sanitised and rejected if it tries to talk about the rubric/evaluator.
  * Rules are capped per check, and every change is written to prompt_changelog.md for human review.
  * Rubric changes are only PROPOSED (memory/rubric_proposals.json). A human applies them and bumps RUBRIC_VERSION.
"""
from __future__ import annotations

import os
import re

from .memory import Memory
from .rubric import CHECK_BY_ID

THRESHOLD = int(os.getenv("REFINER_THRESHOLD", "2"))  # NEW failures of one check before we act (lower it only for demos)
MAX_RULES_PER_CHECK = 3
MAX_RULES_TOTAL = 12
FORBIDDEN = re.compile(r"rubric|evaluator|reviewer|checker|ignore (all|previous)|pass the", re.IGNORECASE)


def _sanitize(rule: str) -> str | None:
    rule = rule.strip().strip('"').strip("'").splitlines()[0] if rule.strip() else ""
    rule = re.sub(r"^[-*\d.\s]+", "", rule).strip()
    if not (15 <= len(rule) <= 260) or FORBIDDEN.search(rule):
        return None
    return rule


def learn_from_history(memory: Memory, llm, say=print) -> list[dict]:
    """Return the list of new rules added (possibly empty)."""
    counts = memory.failure_counts()
    added: list[dict] = []
    for check_id, n in counts.most_common():
        if check_id not in CHECK_BY_ID or len(memory.rules()) + len(added) >= MAX_RULES_TOTAL:
            continue
        existing = memory.rules_for(check_id)
        baseline = max((r["failures_at_creation"] for r in existing), default=0)
        if n - baseline < THRESHOLD or len(existing) >= MAX_RULES_PER_CHECK:
            continue
        check = CHECK_BY_ID[check_id]
        reasons = memory.recent_reasons(check_id)
        system = (
            "You improve the instructions of an AI that writes beginner lessons for 12th-grade students in India "
            "with limited English. You write short, specific, actionable rules."
        )
        user = (
            f"CHECK_ID: {check_id}\nCHECK: {check.name}: {check.question}\n"
            f"This check has failed {n} times. Recent failure reasons:\n"
            + "\n".join(f"- {r}" for r in reasons)
            + "\n\nExisting rules for this check (do not repeat them):\n"
            + "\n".join(f"- {r['rule']}" for r in existing)
            + "\n\nWrite ONE new rule for the lesson writer: one sentence, imperative mood, specific and concrete, "
            "at most 30 words. Do not mention checks, reviewers or scores. Return only the rule."
        )
        rule = _sanitize(llm.chat(system, user, temperature=0.3, task="refine"))
        if not rule:
            say(f"   [memory] refiner produced an unusable rule for {check_id}; skipped.")
            continue
        entry = memory.add_rule(check_id, rule, n, reasons)
        say(f"   [memory] NEW RULE {entry['id']} for {check_id}: {rule}")
        added.append(entry)
    return added


def propose_rubric_changes(memory: Memory, llm, say=print) -> list[dict]:
    """If a check keeps failing EVEN AFTER prompt rules were added, the problem may be the check itself
    (too strict, ambiguous, or a weak heuristic). The system may only PROPOSE a rubric change.
    A human reviews it, edits src/rubric.py and bumps RUBRIC_VERSION. The rubric is never edited automatically."""
    counts = memory.failure_counts()
    made: list[dict] = []
    for check_id, n in counts.most_common():
        rules = memory.rules_for(check_id)
        if check_id not in CHECK_BY_ID or not rules:
            continue
        last_rule_failures = max(r["failures_at_creation"] for r in rules)
        done = max((p["failures_at_creation"] for p in memory.proposals() if p["check_id"] == check_id), default=0)
        if n - max(last_rule_failures, done) < THRESHOLD:
            continue
        check = CHECK_BY_ID[check_id]
        system = "You review a quality rubric for beginner lessons and suggest careful, minimal improvements."
        user = (
            f"CHECK_ID: {check_id}\nCHECK: {check.name}: {check.question}\n"
            f"It keeps failing ({n} times) even after these writer rules were added:\n"
            + "\n".join(f"- {r['rule']}" for r in rules)
            + "\nRecent failure reasons:\n" + "\n".join(f"- {r}" for r in memory.recent_reasons(check_id))
            + "\n\nIn at most 3 sentences: is the check unclear, too strict, or judged by a weak heuristic? "
            "Suggest ONE precise rewording or fix for a human to review. Do not lower the quality bar."
        )
        text = llm.chat(system, user, temperature=0.2, task="rubric_proposal").strip()
        if text:
            entry = memory.add_proposal(check_id, text, n)
            say(f"   [memory] RUBRIC PROPOSAL {entry['id']} for {check_id} (pending human review): {text[:160]}")
            made.append(entry)
    return made