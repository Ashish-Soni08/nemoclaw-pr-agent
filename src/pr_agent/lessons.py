"""ledger/lessons.tsv: what the agent learned from its own PR outcomes, read back on every run.

The agent writes a lesson after a PR is merged or closed, a claim is answered, a review
asks for changes or the gate fails. Lessons are hints for triage and fixes. They never
change the rules: skills, policy checks and the `pr-agent` guards stay hand-edited.
A human drops a bad lesson with `pr-agent lesson drop <id>`; every add and drop is a
ledger row, and the file syncs to the dataset with the rest of the ledger.
"""

from __future__ import annotations

import csv
import re
import secrets
from dataclasses import dataclass
from pathlib import Path

from .ledger import clean, now_iso

COLUMNS = ("id", "ts", "run", "scope", "lesson", "source", "evidence", "status")
SOURCES = ("pr.merged", "pr.closed", "review", "claim.approved", "claim.declined", "gate.fail", "triage", "other")
MAX_CHARS = 240
# Oldest active lessons retire past these counts, so the prompt stays small.
MAX_GLOBAL = 25
MAX_PER_REPO = 10
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


@dataclass
class Lessons:
    path: Path
    run: str = ""

    def rows(self) -> list[dict[str, str]]:
        if not self.path.exists():
            return []
        with self.path.open(encoding="utf-8") as fh:
            return list(csv.DictReader(fh, delimiter="\t", quoting=csv.QUOTE_NONE))

    def active(self, repo: str = "") -> list[dict[str, str]]:
        """Global lessons plus, when a repo is given, that repo's own (repo names compare case-insensitively)."""
        scopes = {"*"} | ({repo.lower()} if repo else set())
        return [r for r in self.rows() if r["status"] == "active" and r["scope"].lower() in scopes]

    def add(self, scope: str, lesson: str, source: str, evidence: str) -> dict[str, str]:
        scope = scope.strip() or "*"
        if scope != "*" and not REPO_RE.match(scope):
            raise ValueError("scope is * (every repo) or owner/repo")
        if source not in SOURCES:
            raise ValueError(f"source is one of {', '.join(SOURCES)}")
        text = clean(lesson)
        if not text:
            raise ValueError("empty lesson")
        if len(text) > MAX_CHARS:
            raise ValueError(f"keep a lesson under {MAX_CHARS} characters; it is a hint, not a write-up")
        if not evidence.strip():
            raise ValueError("--evidence is required (the PR, comment or ledger row it comes from)")
        rows = self.rows()
        if any(r["status"] == "active" and r["scope"].lower() == scope.lower() and r["lesson"].lower() == text.lower() for r in rows):
            return {"duplicate": text}
        row = {"id": "L" + secrets.token_hex(3), "ts": now_iso(), "run": self.run, "scope": scope, "lesson": text,
               "source": source, "evidence": clean(evidence), "status": "active"}
        rows.append(row)
        limit = MAX_GLOBAL if scope == "*" else MAX_PER_REPO
        same = [r for r in rows if r["status"] == "active" and r["scope"].lower() == scope.lower()]
        for old in same[: max(0, len(same) - limit)]:
            old["status"] = "retired"
        self._write(rows)
        return row

    def drop(self, lesson_id: str) -> dict[str, str] | None:
        rows = self.rows()
        hit = next((r for r in rows if r["id"] == lesson_id), None)
        if hit:
            hit["status"] = "dropped"
            self._write(rows)
        return hit

    def _write(self, rows: list[dict[str, str]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            fh.write("\t".join(COLUMNS) + "\n")
            for r in rows:
                fh.write("\t".join(clean(r.get(c, "")) for c in COLUMNS) + "\n")
        tmp.replace(self.path)


def compact(rows: list[dict[str, str]]) -> list[str]:
    """One line per lesson for the agent's context."""
    return [f"{r['id']} [{r['scope']}] {r['lesson']}" for r in rows]
