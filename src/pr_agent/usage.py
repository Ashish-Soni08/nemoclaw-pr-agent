"""Model menu and the usage guard.

Hugging Face spend limits only exist for Team/Enterprise orgs, so the agent
enforces its own. Hermes records tokens per session in $HERMES_HOME/state.db;
the guard prices them with the menu and returns a wake gate the cron
pre-step prints. Over budget means the run is skipped before any tokens are spent.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .http import Client


@dataclass
class ModelEntry:
    id: str
    roles: list[str]
    price_in: float  # USD per 1M input tokens
    price_out: float  # USD per 1M output tokens
    note: str = ""

    def cost(self, tokens_in: int, tokens_out: int) -> float:
        return tokens_in / 1e6 * self.price_in + tokens_out / 1e6 * self.price_out


def menu(agent_cfg: dict[str, Any]) -> list[ModelEntry]:
    return [ModelEntry(m["id"], m.get("roles", []), float(m["price_in"]), float(m["price_out"]), m.get("note", "")) for m in agent_cfg.get("models", [])]


def _lookup(entries: list[ModelEntry], model: str | None) -> ModelEntry | None:
    if not model:
        return None
    base = model.split(":")[0].lower()
    for e in entries:
        if e.id.lower() == base or e.id.lower().endswith("/" + base.split("/")[-1]):
            return e
    return None


@dataclass
class UsageReport:
    month_usd: float
    day_usd: float
    by_model: dict[str, dict[str, float]]
    unknown_models: list[str]
    month_budget: float
    day_budget: float

    @property
    def over(self) -> str:
        if self.month_usd >= self.month_budget:
            return f"monthly budget used: ${self.month_usd:.2f} of ${self.month_budget:.2f}"
        if self.day_usd >= self.day_budget:
            return f"daily budget used: ${self.day_usd:.2f} of ${self.day_budget:.2f}"
        return ""


def report(state_db: Path, entries: list[ModelEntry], month_budget: float, day_budget: float, now: datetime | None = None) -> UsageReport:
    now = now or datetime.now(timezone.utc)
    month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc).timestamp()
    day_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc).timestamp()
    by_model: dict[str, dict[str, float]] = {}
    unknown: set[str] = set()
    month = day = 0.0
    priciest = max(entries, key=lambda e: e.price_out) if entries else ModelEntry("?", [], 5.0, 15.0)
    if state_db.exists():
        con = sqlite3.connect(f"file:{state_db}?mode=ro", uri=True, timeout=10)
        try:
            rows = con.execute(
                "SELECT model, COALESCE(input_tokens,0)+COALESCE(cache_read_tokens,0)+COALESCE(cache_write_tokens,0), "
                "COALESCE(output_tokens,0)+COALESCE(reasoning_tokens,0), started_at FROM sessions WHERE started_at >= ?",
                (month_start,),
            ).fetchall()
        finally:
            con.close()
        for model, t_in, t_out, started in rows:
            entry = _lookup(entries, model)
            if entry is None:
                unknown.add(model or "unknown")
                entry = priciest
            cost = entry.cost(t_in, t_out)
            agg = by_model.setdefault(model or "unknown", {"in": 0, "out": 0, "usd": 0.0})
            agg["in"] += t_in
            agg["out"] += t_out
            agg["usd"] += cost
            month += cost
            if started >= day_start:
                day += cost
    return UsageReport(round(month, 4), round(day, 4), by_model, sorted(unknown), month_budget, day_budget)


def served_models(base_url: str, token: str) -> set[str]:
    """Which ids the router serves right now (host-side check, needs HF_TOKEN)."""
    data = Client(base_url, headers={"Authorization": f"Bearer {token}"}).get_json("/models")
    return {m["id"] for m in data.get("data", [])}
