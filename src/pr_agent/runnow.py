"""`pr-agent run-now`: start the scheduled run early when the owner asks on Telegram.

It starts the same cron job the schedule does (same pre-step, guard and rules), so asking from
chat adds no new powers. It refuses while a run is in progress or when the next one is close.
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# Closer than this to the next scheduled run, just wait for it.
NEAR = timedelta(minutes=30)
# A run with no end row (a crashed session) stops counting as in progress after this long.
RUN_MAX = timedelta(hours=2)
# Longer than a fix sub-agent may work without writing a ledger row (its timeout is 60 min).
RUN_QUIET = timedelta(minutes=70)


def _field(spec: str, lo: int, hi: int) -> set[int]:
    out: set[int] = set()
    for part in spec.split(","):
        rng, _, step = part.partition("/")
        if rng == "*":
            a, b = lo, hi
        elif "-" in rng:
            a, b = (int(x) for x in rng.split("-"))
        else:
            a = b = int(rng)
        out |= set(range(a, b + 1, int(step) if step else 1))
    return out


def next_cron_time(expr: str, now: datetime) -> datetime | None:
    """Next time a "minute hour * * *" schedule fires after now, or None for anything fancier."""
    parts = expr.split()
    if len(parts) != 5 or parts[2:] != ["*", "*", "*"]:
        return None
    try:
        minutes, hours = _field(parts[0], 0, 59), _field(parts[1], 0, 23)
    except ValueError:
        return None
    t = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
    for _ in range(24 * 60):
        if t.minute in minutes and t.hour in hours:
            return t
        t += timedelta(minutes=1)
    return None


def find_job(jobs_path: Path, name: str) -> dict[str, Any] | None:
    try:
        jobs = json.loads(jobs_path.read_text()).get("jobs", [])
    except (OSError, ValueError):
        return None
    return next((j for j in jobs if j.get("name") == name), None)


def job_schedule(job: dict[str, Any]) -> str:
    s = job.get("schedule", "")
    if isinstance(s, dict):
        s = s.get("expr") or s.get("cron") or s.get("value") or ""
    return str(s)


def run_in_progress(rows: list[dict[str, str]], now: datetime) -> str:
    """Id of a run that started recently and hasn't logged run.end, or ""."""
    started, ended, last = {}, set(), {}
    for r in rows:
        # Chat rows carry the last run's id but aren't that run's activity.
        if not r.get("phase", "").startswith("chat."):
            last[r.get("run", "")] = r.get("ts", "")
        if r.get("phase") == "start" and r.get("decision", "").startswith("started") and "skipped" not in r.get("decision", ""):
            started[r.get("run", "")] = r.get("ts", "")
        elif r.get("phase") == "run.end":
            ended.add(r.get("run", ""))
    for run, ts in sorted(started.items(), key=lambda kv: kv[1], reverse=True):
        if run in ended:
            continue
        try:
            age = now - datetime.fromisoformat(ts.replace("Z", "+00:00"))
            quiet = now - datetime.fromisoformat(last[run].replace("Z", "+00:00"))
        except ValueError:
            continue
        # A crashed run never logs run.end; a long silence means it's over.
        if age <= RUN_MAX and quiet <= RUN_QUIET:
            return run
    return ""


def cron_process_running() -> bool:
    try:
        return subprocess.run(["pgrep", "-f", "[h]ermes cron run"], capture_output=True, timeout=10).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def start(job_id: str, log: Path) -> None:
    """Start the job detached, so it outlives the chat turn that asked for it."""
    with log.open("w") as fh:
        subprocess.Popen(["hermes", "cron", "run", job_id], stdout=fh, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True)
