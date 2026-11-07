"""Builds the human-readable rejection log (outputs/rejection_log.md)."""
from __future__ import annotations

from datetime import datetime


def build_rejection_log(topic: str, run_id: str, attempts: list[dict], rejection_log: list[dict],
                        status: str, usage: dict, rubric_version: str, max_retries: int) -> str:
    out = [
        f"# Rejection log: {topic}",
        "",
        f"- Run: `{run_id}`  |  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"- Rubric version: {rubric_version}  |  Max retries: {max_retries}",
        f"- Final status: **{status}**",
        f"- LLM calls: {usage.get('calls', 0)}  |  Prompt tokens: {usage.get('prompt_tokens', 0)}  |  "
        f"Completion tokens: {usage.get('completion_tokens', 0)}",
        "",
    ]
    rej_by_attempt = {r["attempt"]: r for r in rejection_log}
    for a in attempts:
        ev = a["eval"]
        n_ok = sum(1 for c in ev["checks"] if c["pass"])
        verdict = "PASSED" if ev["overall_pass"] else "FAILED"
        out.append(f"## Attempt {a['attempt']}: {verdict} ({n_ok}/{len(ev['checks'])} checks)")
        out.append("")
        out.append("| Check | Result | Judged by | Reason |")
        out.append("|---|---|---|---|")
        for c in ev["checks"]:
            mark = "PASS" if c["pass"] else "**FAIL**"
            reason = c["reason"].replace("|", "/").replace("\n", " ")
            out.append(f"| {c['id']} {c['name']} | {mark} | {c['judged_by']} | {reason} |")
        out.append("")
        out.append(f"Metrics: {ev.get('metrics', {}).get('words', '?')} words, "
                   f"{ev.get('metrics', {}).get('avg_words_per_sentence', '?')} avg words/sentence.")
        rej = rej_by_attempt.get(a["attempt"])
        if rej:
            out.append("")
            out.append(f"**What changed on retry:** {rej.get('what_changed') or '(not recorded)'}")
            nxt = next((x for x in attempts if x["attempt"] == a["attempt"] + 1), None)
            if nxt:
                after = {c["id"]: c for c in nxt["eval"]["checks"]}
                out.append("")
                out.append("**Did the retry fix it?**")
                for c in ev["checks"]:
                    if not c["pass"]:
                        now = "PASS" if after[c["id"]]["pass"] else "still FAIL"
                        out.append(f"- {c['id']} {c['name']}: FAIL -> {now}")
                m0, m1 = ev.get("metrics", {}), nxt["eval"].get("metrics", {})
                out.append(f"- Words: {m0.get('words', '?')} -> {m1.get('words', '?')}; "
                           f"average sentence: {m0.get('avg_words_per_sentence', '?')} -> {m1.get('avg_words_per_sentence', '?')}")
        out.append("")
    if status != "PASSED":
        out += [
            "## Needs human review",
            "",
            "The retry limit was reached without a fully passing lesson. The best attempt was shipped, "
            "but it is flagged. A human must review the failed checks above before learners see it.",
            "",
        ]
    return "\n".join(out)