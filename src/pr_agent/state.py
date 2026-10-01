"""Small TSV/JSON state files that make each cron run idempotent."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

SEEN_COLUMNS = ("issue_id", "first_seen", "last_stage", "last_verdict", "recheck_after")
NEVER = "never"


def today() -> date:
    return datetime.now(timezone.utc).date()


@dataclass
class SeenStore:
    """state/seen.tsv: issues already looked at, and when they may be looked at again."""

    path: Path

    def load(self) -> dict[str, dict[str, str]]:
        if not self.path.exists():
            return {}
        with self.path.open(encoding="utf-8") as fh:
            return {r["issue_id"]: r for r in csv.DictReader(fh, delimiter="\t")}

    def is_fresh_skip(self, issue_id: str, on: date | None = None) -> dict[str, str] | None:
        """Return the row when this issue should be skipped today."""
        row = self.load().get(issue_id)
        if not row:
            return None
        after = row.get("recheck_after", "")
        if after == NEVER:
            return row
        if after and date.fromisoformat(after) > (on or today()):
            return row
        return None

    def mark(self, issue_id: str, stage: str, verdict: str, recheck_days: int | None) -> None:
        rows = self.load()
        first = rows.get(issue_id, {}).get("first_seen") or today().isoformat()
        recheck = NEVER if recheck_days is None else (today() + timedelta(days=recheck_days)).isoformat()
        rows[issue_id] = {"issue_id": issue_id, "first_seen": first, "last_stage": stage, "last_verdict": verdict, "recheck_after": recheck}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=SEEN_COLUMNS, delimiter="\t", lineterminator="\n")
            writer.writeheader()
            for row in rows.values():
                writer.writerow({k: str(row.get(k, "")).replace("\t", " ") for k in SEEN_COLUMNS})
        tmp.replace(self.path)


@dataclass
class CreditBook:
    """state/firecrawl_credits.tsv: one line per Index call, so caps survive restarts."""

    path: Path

    def _rows(self) -> list[tuple[str, str, int]]:
        if not self.path.exists():
            return []
        out = []
        for line in self.path.read_text().splitlines()[1:]:
            parts = line.split("\t")
            if len(parts) >= 3:
                out.append((parts[0], parts[1], int(parts[2])))
        return out

    def spent(self, run: str | None = None, month: str | None = None) -> int:
        return sum(
            credits
            for ts, row_run, credits in self._rows()
            if (month is None or ts.startswith(month)) and (run is None or row_run == run)
        )

    def add(self, run: str, credits: int, query_hash: str) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        new = not self.path.exists()
        with self.path.open("a", encoding="utf-8") as fh:
            if new:
                fh.write("ts\trun\tcredits\tquery_hash\n")
            fh.write(f"{datetime.now(timezone.utc).isoformat(timespec='seconds')}\t{run}\t{credits}\t{query_hash}\n")


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text())


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True))
    tmp.replace(path)
