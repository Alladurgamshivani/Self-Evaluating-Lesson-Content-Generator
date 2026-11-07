"""The evaluator: a HYBRID judge. Code checks + LLM checks, strict PASS/FAIL, fails closed.

Why hybrid?
  * code  -> exact, free, repeatable, cannot be sweet-talked (sentence length, headings, length, jargon use)
  * LLM   -> understands meaning (is it true? is it relatable? does it flow?)
Why "fail closed"?
  If the LLM reviewer returns broken JSON or forgets a check, that check is marked FAIL, never PASS.
  An evaluator that silently passes when it is confused is worse than no evaluator.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .checks import CODE_CHECKS
from .rubric import CHECKS, CHECK_BY_ID, LLM_CHECK_IDS, checkpoints_text

ROOT = Path(__file__).resolve().parent.parent
EVALUATOR_ERROR = "[evaluator error]"  # marks "the judge broke", which is NOT the same as "the lesson is bad"


def _extract_json(raw: str) -> dict | None:
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.M).strip()
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        return json.loads(raw[start: end + 1])
    except json.JSONDecodeError:
        return None


def run_llm_checks(lesson: str, reference_notes: str, llm, prompt_template: str) -> dict[str, tuple[bool, str]]:
    system = (
        prompt_template.replace("{checkpoints}", checkpoints_text(LLM_CHECK_IDS))
        .replace("{reference_notes}", reference_notes)
    )
    user = "Review this lesson.\n\n<lesson>\n" + lesson + "\n</lesson>"
    parsed = None
    raw_preview = ""
    for attempt in range(2):  # one retry if the JSON is broken
        raw = llm.chat(system, user if attempt == 0 else user + "\n\nReturn ONLY valid JSON.", temperature=0.0, task="evaluate")
        raw_preview = (raw or "")[:120]
        parsed = _extract_json(raw)
        if parsed and isinstance(parsed.get("checks"), list):
            break
        parsed = None
    results: dict[str, tuple[bool, str]] = {}
    if parsed:
        for item in parsed["checks"]:
            cid = str(item.get("id", "")).strip()
            if cid in LLM_CHECK_IDS:
                results[cid] = (bool(item.get("pass")) is True, str(item.get("reason", "")).strip() or "(no reason given)")
    for cid in LLM_CHECK_IDS:  # fail closed
        if cid not in results:
            results[cid] = (False, f"{EVALUATOR_ERROR} The reviewer did not return a valid verdict for this check (treated as FAIL). Raw reply started with: {raw_preview!r}")
    return results


def evaluate(lesson: str, reference_notes: str, llm, prompt_template: str) -> dict:
    """Return {"checks": [...], "overall_pass": bool, "failed_ids": [...], "metrics": {...}}."""
    code_results: dict[str, tuple[bool, str, dict]] = {cid: fn(lesson) for cid, fn in CODE_CHECKS.items()}
    llm_results = run_llm_checks(lesson, reference_notes, llm, prompt_template)

    checks, metrics = [], {}
    for c in CHECKS:
        parts_pass, reasons, sources = [], [], []
        if c.uses_code:
            ok, why, m = code_results[c.id]
            metrics.update(m)
            parts_pass.append(ok)
            sources.append("code")
            if not ok:
                reasons.append(f"[code] {why}")
            elif c.kind == "code":
                reasons.append(why)
        if c.uses_llm:
            ok, why = llm_results[c.id]
            parts_pass.append(ok)
            sources.append("llm")
            if not ok:
                reasons.append(f"[llm] {why}")
            elif c.kind == "llm":
                reasons.append(why)
        passed = all(parts_pass)
        if passed and not reasons:
            reasons.append("OK")
        checks.append({
            "id": c.id, "name": c.name, "pass": passed,
            "reason": " | ".join(reasons), "judged_by": "+".join(sources),
        })
    failed = [c["id"] for c in checks if not c["pass"]]
    broken = any(EVALUATOR_ERROR in c["reason"] for c in checks)
    return {"checks": checks, "overall_pass": not failed, "failed_ids": failed, "metrics": metrics,
            "evaluator_error": broken}


def format_feedback(eval_result: dict) -> str:
    """Turn failed checks into feedback for the generator: reason + what to do about it."""
    lines = []
    for c in eval_result["checks"]:
        if not c["pass"]:
            lines.append(f"- {c['id']} ({c['name']}) FAILED: {c['reason']}\n  How to fix: {CHECK_BY_ID[c['id']].fix_hint}")
    return "\n".join(lines)


def score_line(eval_result: dict) -> str:
    n = len(eval_result["checks"])
    ok = sum(1 for c in eval_result["checks"] if c["pass"])
    return f"{ok}/{n} checks passed"