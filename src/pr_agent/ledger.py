"""decisions.tsv: one row per decision, append-only.

Columns follow show-me-your-work (ts, phase, decision, why, evidence, result)
with `run` and `subject` added so a reader can filter one run or one issue.
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

COLUMNS = ("ts", "run", "phase", "subject", "decision", "why", "evidence", "result")


def clean(value: object) -> str:
    """Single-line cell; a leading formula character gets a quote so spreadsheets never execute it."""
    text = str(value if value is not None else "")
    text = text.replace("\t", " ").replace("\r", " ").replace("\n", " ").strip()
    if len(text) > 1 and text[0] in ("=", "+", "-", "@"):  # a bare "-" means "none" and stays as is
        text = "'" + text
    return text


def append_tsv(path: Path, columns: tuple[str, ...], rows: list[list[object]]) -> None:
    """Append rows to a side table under ledger/, writing the header on first use."""
    new = not path.exists() or path.stat().st_size == 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        if new:
            fh.write("\t".join(columns) + "\n")
        for row in rows:
            fh.write("\t".join(clean(c) for c in row) + "\n")


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class Ledger:
    path: Path
    run: str = ""

    def log(self, phase: str, subject: str, decision: str, why: str = "", evidence: str = "", result: str = "") -> dict[str, str]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        row = dict(zip(COLUMNS, (now_iso(), self.run, phase, subject, decision, why, evidence, result)))
        row = {k: clean(v) for k, v in row.items()}
        new = not self.path.exists() or self.path.stat().st_size == 0
        with self.path.open("a", encoding="utf-8") as fh:
            if new:
                fh.write("\t".join(COLUMNS) + "\n")
            fh.write("\t".join(row[c] for c in COLUMNS) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        return row

    def rows(self) -> list[dict[str, str]]:
        if not self.path.exists():
            return []
        with self.path.open(encoding="utf-8") as fh:
            return list(csv.DictReader(fh, delimiter="\t", quoting=csv.QUOTE_NONE))

    def run_rows(self, run: str) -> list[dict[str, str]]:
        return [r for r in self.rows() if r.get("run") == run]


def sync_to_dataset(local_dir: Path, repo_id: str, token: str | None = None) -> str:
    """Mirror the ledger folder into a Hugging Face dataset repo, under `ledger/`.

    The dataset is created private on first sync. Each sync is one commit, so the
    dataset's history is also a history of the ledger.
    """
    from huggingface_hub import HfApi  # optional dependency

    api = HfApi(token=token)
    api.create_repo(repo_id, repo_type="dataset", private=True, exist_ok=True)
    api.upload_folder(
        repo_id=repo_id, repo_type="dataset", folder_path=str(local_dir), path_in_repo="ledger",
        commit_message="sync ledger", allow_patterns=["*.tsv", "runs/**", "media/**"],
    )
    return f"https://huggingface.co/datasets/{repo_id}/tree/main/ledger"
