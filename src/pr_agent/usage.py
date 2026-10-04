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
    price_cache_read: float | None = None  # USD per 1M cached input tokens; default 10% of price_in

    def cost(self, tokens_in: int, tokens_out: int, tokens_cached: int = 0) -> float:
        cached = self.price_cache_read if self.price_cache_read is not None else self.price_in * 0.1
        return tokens_in / 1e6 * self.price_in + tokens_cached / 1e6 * cached + tokens_out / 1e6 * self.price_out


def menu(agent_cfg: dict[str, Any]) -> list[ModelEntry]:
    return [ModelEntry(m["id"], m.get("roles", []), float(m["price_in"]), float(m["price_out"]), m.get("note", ""),
                       float(m["price_cache_read"]) if m.get("price_cache_read") is not None else None) for m in agent_cfg.get("models", [])]


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
        if self.day_budget > 0 and self.day_usd >= self.day_budget:
            return f"daily budget used: ${self.day_usd:.2f} of ${self.day_budget:.2f}"
        return ""


def report(state_db: Path, entries: list[ModelEntry], month_budget: float, day_budget: float, now: datetime | None = None, since: float | None = None,
           served_model: str = "") -> UsageReport:
    """Spend from Hermes' session records, month to date (or from `since`, an epoch, when given).

    `served_model`: NemoClaw's inference route sends every request to the onboarded model whatever a
    session asked for, so sessions are priced as that model (Hermes records the requested one)."""
    now = now or datetime.now(timezone.utc)
    month_start = since if since is not None else datetime(now.year, now.month, 1, tzinfo=timezone.utc).timestamp()
    day_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc).timestamp()
    by_model: dict[str, dict[str, float]] = {}
    unknown: set[str] = set()
    month = day = 0.0
    priciest = max(entries, key=lambda e: e.price_out) if entries else ModelEntry("?", [], 5.0, 15.0)
    if state_db.exists():
        con = sqlite3.connect(f"file:{state_db}?mode=ro", uri=True, timeout=10)
        try:
            rows = con.execute(
                # Cache reads are most of the input (every turn re-sends the context) and bill at a fraction
                # of the input price; pricing them at full rate overstated spend ~7x (HF billed $8.05, we said $60).
                "SELECT model, COALESCE(input_tokens,0)+COALESCE(cache_write_tokens,0), COALESCE(cache_read_tokens,0), "
                "COALESCE(output_tokens,0)+COALESCE(reasoning_tokens,0), started_at FROM sessions WHERE started_at >= ?",
                (month_start,),
            ).fetchall()
        finally:
            con.close()
        for model, t_in, t_cached, t_out, started in rows:
            entry = _lookup(entries, served_model or model)
            if entry is None:
                unknown.add(model or "unknown")
                entry = priciest
            cost = entry.cost(t_in, t_out, t_cached)
            agg = by_model.setdefault(model or "unknown", {"in": 0, "cached": 0, "out": 0, "usd": 0.0})
            agg["in"] += t_in
            agg["cached"] += t_cached
            agg["out"] += t_out
            agg["usd"] += cost
            month += cost
            if started >= day_start:
                day += cost
    return UsageReport(round(month, 4), round(day, 4), by_model, sorted(unknown), month_budget, day_budget)


def router_models(base_url: str, token: str) -> dict[str, dict[str, Any]]:
    """What the router serves right now (host-side check, needs HF_TOKEN): id -> cheapest live
    provider's price per 1M tokens, whether any provider supports tool calls, and the longest context."""
    data = Client(base_url, headers={"Authorization": f"Bearer {token}"}).get_json("/models")
    out: dict[str, dict[str, Any]] = {}
    for m in data.get("data", []):
        live = [p for p in m.get("providers") or [] if p.get("status", "live") == "live"]
        priced = [p for p in live if (p.get("pricing") or {}).get("input") is not None]
        cheapest = min(priced, key=lambda p: p["pricing"]["input"] + p["pricing"].get("output", 0), default=None)
        with_tools = [p for p in priced if p.get("supports_tools")]
        cheapest_tools = min(with_tools, key=lambda p: p["pricing"]["input"] + p["pricing"].get("output", 0), default=None)
        out[m["id"]] = {
            "price_in": cheapest["pricing"]["input"] if cheapest else None,
            "price_out": cheapest["pricing"].get("output") if cheapest else None,
            # The model id to configure so the router always uses the cheapest provider that can call tools.
            "pin": f"{m['id']}:{cheapest_tools['provider']}" if cheapest_tools and cheapest_tools.get("provider") else None,
            "pin_price": [cheapest_tools["pricing"]["input"], cheapest_tools["pricing"].get("output")] if cheapest_tools else None,
            "providers": sorted(
                ({"provider": p.get("provider"), "in": p["pricing"]["input"], "out": p["pricing"].get("output"), "tools": bool(p.get("supports_tools"))} for p in priced),
                key=lambda r: r["in"] + (r["out"] or 0)),
            "tools": any(p.get("supports_tools") for p in live) if live else None,
            "context": max((p.get("context_length") or 0 for p in live), default=0) or None,
        }
    return out
