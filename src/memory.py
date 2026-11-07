"""Persistent memory (plain JSON files, easy to open and show on camera).

memory/run_history.json    one record per run: topic, attempts, which checks failed, reasons, cost
memory/lessons_learned.json  short rules the self-evolving step wrote; they are injected into the generator
memory/prompt_changelog.md   human-readable history of every rule that was added and why
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path


class Memory:
    def __init__(self, directory: Path):
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.history_path = self.dir / "run_history.json"
        self.rules_path = self.dir / "lessons_learned.json"
        self.changelog_path = self.dir / "prompt_changelog.md"
        self.proposals_path = self.dir / "rubric_proposals.json"

    # -- low level ------------------------------------------------------------------------------
    def _read(self, path: Path) -> list:
        if not path.exists():
            return []
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            # Never crash a run because memory is corrupted: keep a backup and start fresh.
            path.rename(path.with_suffix(".corrupt.json"))
            return []

    def _write(self, path: Path, data: list) -> None:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    # -- run history ----------------------------------------------------------------------------
    def history(self) -> list[dict]:
        return self._read(self.history_path)

    def append_run(self, record: dict) -> None:
        runs = self.history()
        runs.append(record)
        self._write(self.history_path, runs)

    def failure_counts(self) -> Counter:
        """How many attempts (across all runs) failed each check."""
        counts: Counter = Counter()
        for run in self.history():
            if run.get("injected"):   # deliberate-error demos are tests, not real generator failures
                continue
            for failed in run.get("failed_per_attempt", []):
                counts.update(failed)
        return counts

    def recent_reasons(self, check_id: str, limit: int = 5) -> list[str]:
        reasons: list[str] = []
        for run in self.history():
            reasons.extend(run.get("reasons", {}).get(check_id, []))
        return reasons[-limit:]

    # -- learned rules --------------------------------------------------------------------------
    def rules(self) -> list[dict]:
        return self._read(self.rules_path)

    def rules_for(self, check_id: str) -> list[dict]:
        return [r for r in self.rules() if r["check_id"] == check_id]

    def top_rules(self, k: int = 6) -> list[str]:
        """Rules to inject into the next generator prompt: most frequently failing checks first."""
        counts = self.failure_counts()
        ranked = sorted(self.rules(), key=lambda r: (counts.get(r["check_id"], 0), r["created"]), reverse=True)
        return [r["rule"] for r in ranked[:k]]

    def add_rule(self, check_id: str, rule: str, failures_at_creation: int, evidence: list[str]) -> dict:
        rules = self.rules()
        entry = {
            "id": f"L{len(rules) + 1}",
            "check_id": check_id,
            "rule": rule,
            "created": datetime.now().isoformat(timespec="seconds"),
            "failures_at_creation": failures_at_creation,
        }
        rules.append(entry)
        self._write(self.rules_path, rules)
        with self.changelog_path.open("a", encoding="utf-8") as f:
            f.write(
                f"## {entry['created']}: new rule {entry['id']} for {check_id}\n"
                f"- Rule: {rule}\n- Why: check {check_id} had failed {failures_at_creation} time(s). Evidence:\n"
                + "".join(f"  - {e[:200]}\n" for e in evidence)
                + "\n"
            )
        return entry

    # -- rubric proposals: suggestions for a HUMAN to review. They are never applied automatically. ------
    def proposals(self) -> list[dict]:
        return self._read(self.proposals_path)

    def add_proposal(self, check_id: str, text: str, failures_at_creation: int) -> dict:
        items = self.proposals()
        entry = {
            "id": f"P{len(items) + 1}",
            "check_id": check_id,
            "proposal": text,
            "status": "PENDING HUMAN REVIEW",
            "created": datetime.now().isoformat(timespec="seconds"),
            "failures_at_creation": failures_at_creation,
        }
        items.append(entry)
        self._write(self.proposals_path, items)
        return entry

    def reset(self) -> None:
        for p in (self.history_path, self.rules_path, self.changelog_path, self.proposals_path):
            if p.exists():
                p.unlink()