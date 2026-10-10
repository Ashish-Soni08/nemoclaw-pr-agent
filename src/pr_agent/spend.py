"""ledger/spend.tsv: one row per provider per snapshot, in one shape the UI can chart.

Columns: ts, provider, used, unit, cost_usd, remaining, limit, source.
`remaining` and `limit` are in the same unit as `used`. `source` says whether
a number came from the provider's API or from our own estimate.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .devindex import BASE_URL as FIRECRAWL_URL
from .ledger import append_tsv
from .http import Client
from .state import CreditBook, read_json, write_json

COLUMNS = ("ts", "provider", "used", "unit", "cost_usd", "remaining", "limit", "source")


@dataclass
class SpendRow:
    provider: str
    used: float
    unit: str
    cost_usd: float
    remaining: float | None
    limit: float | None
    source: str

    def cells(self, ts: str) -> list[str]:
        fmt = lambda v: "" if v is None else f"{v:.4f}".rstrip("0").rstrip(".")  # noqa: E731
        return [ts, self.provider, fmt(self.used), self.unit, fmt(self.cost_usd), fmt(self.remaining), fmt(self.limit), self.source]


def append(path: Path, rows: list[SpendRow]) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    new = not path.exists() or path.stat().st_size == 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        if new:
            fh.write("\t".join(COLUMNS) + "\n")
        for row in rows:
            fh.write("\t".join(row.cells(ts)) + "\n")


def huggingface(month_usd: float, budget: float, billed: bool = False) -> SpendRow:
    source = "estimate:hermes-state.db tokens x provider prices, cached input at the cache rate (month to date)"
    if billed:
        source = "billed:HF's month-to-date bill as the host last read it (higher than our token estimate)"
    return SpendRow("huggingface", month_usd, "usd", month_usd, max(budget - month_usd, 0), budget, source)


def last_billed(path: Path, now: datetime | None = None) -> float | None:
    """The newest HF bill the host's ledger sync handed into the sandbox this month, or None.

    Our estimate prices every token at one provider's rates, but HF spreads requests over providers
    with their own prices (Oct 10: we said $112, HF billed $240), so the guard can't trust it alone.
    Only the host can read the bill; it uploads billed/huggingface.json after every sync. A bill only
    grows within a month, so an older reading this month is still a floor."""
    now = now or datetime.now(timezone.utc)
    try:
        seen = read_json(path, None)
        if seen and str(seen["at"]).startswith(now.strftime("%Y-%m")):
            return float(seen["usd"])
    except (OSError, KeyError, TypeError, ValueError):
        pass
    return None


def write_billed(path: Path, row: SpendRow, now: datetime | None = None) -> None:
    """Host side: save the bill where sync-ledger.sh uploads it into the sandbox for the guard."""
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, {"usd": row.cost_usd, "at": (now or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ"), "source": row.source})


HF_URL = "https://huggingface.co"


def huggingface_billed(token: str, budget: float, client: Client | None = None, now: datetime | None = None) -> SpendRow | None:
    """Hugging Face's own month-to-date Inference Providers bill, or None if the endpoint won't say.

    The endpoint is what HF's billing page uses (undocumented), so the guard's estimate stays the
    budget check and the fallback. It needs a token with "Read billing usage", which only the host has.
    """
    now = now or datetime.now(timezone.utc)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end = start.replace(year=start.year + 1, month=1) if start.month == 12 else start.replace(month=start.month + 1)
    c = client or Client(HF_URL, headers={"Authorization": f"Bearer {token}"})
    try:
        # Dates are Unix seconds; milliseconds are refused as "more than one billing period in the future".
        resp = c.request("GET", f"/api/settings/billing/usage-v2?startDate={int(start.timestamp())}&endDate={int(end.timestamp())}")
        if not resp.ok:
            return None
        ip = ((resp.json() or {}).get("usage") or {}).get("inferenceProviders") or {}
        used = round(float(ip["usedNanoUsd"]) / 1e9, 4)
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return SpendRow("huggingface", used, "usd", used, round(max(budget - used, 0), 4), budget,
                    f"api:/api/settings/billing/usage-v2 inferenceProviders ({ip.get('numRequests', '?')} requests, month to date)")


def firecrawl(book: CreditBook, plan_credits: int, api_key: str = "", client: Client | None = None) -> SpendRow:
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    used = book.spent(month=month)
    remaining: float | None = max(plan_credits - used, 0)
    source = "local:firecrawl_credits.tsv (month to date)"
    if api_key or client:
        c = client or Client(FIRECRAWL_URL, headers={"Authorization": f"Bearer {api_key}"})
        try:
            resp = c.request("GET", "/v2/team/credit-usage")
            if resp.ok:
                data = (resp.json() or {}).get("data", {})
                left = data.get("remainingCredits", data.get("remaining_credits"))
                if left is not None:
                    # Firecrawl's remaining covers every balance on the team, not just the plan; the limit is what
                    # was left at the start plus what we used, so the bar adds up. Firecrawl's usage history leaves
                    # out Developer Index searches, so "used" stays our own count of this agent's calls.
                    remaining = float(left)
                    plan_credits = int(remaining + used)
                    source = "api:/v2/team/credit-usage (remaining, all balances); used = this agent's own calls (local count)"
        except (OSError, ValueError):
            pass
    return SpendRow("firecrawl", used, "credits", 0.0, remaining, plan_credits, source)


def lambda_hours(state_dir: Path, rate_usd: float, credit_usd: float, proc: Path = Path("/proc")) -> SpendRow:
    """Uptime per boot, summed over boots. A paused instance doesn't bill, so this tracks real cost."""
    boots_path = state_dir / "lambda_boots.json"
    boots: dict[str, float] = read_json(boots_path, {})
    try:
        boot_id = (proc / "sys/kernel/random/boot_id").read_text().strip()
        uptime = float((proc / "uptime").read_text().split()[0])
        boots[boot_id] = max(boots.get(boot_id, 0.0), uptime)
        write_json(boots_path, boots)
        source = "estimate:uptime x hourly rate (all boots)"
    except OSError:
        source = "estimate:no /proc access, last known"
    hours = sum(boots.values()) / 3600
    cost = hours * rate_usd
    return SpendRow("lambda", round(hours, 3), "hours", round(cost, 4), max(credit_usd - cost, 0), credit_usd, source)


def lambda_billed(instances: list[dict[str, Any]], rate_usd: float, credit_usd: float, now: datetime | None = None) -> SpendRow:
    """Lambda bills every hour an instance exists, run or not: wall-clock from launch to end (or now)."""
    now = now or datetime.now(timezone.utc)
    hours, cost, running = 0.0, 0.0, []
    for inst in instances:
        start = datetime.fromisoformat(str(inst["launched_at"]).replace("Z", "+00:00"))
        end = datetime.fromisoformat(str(inst["ended_at"]).replace("Z", "+00:00")) if inst.get("ended_at") else now
        h = max((end - start).total_seconds(), 0) / 3600
        hours += h
        cost += h * float(inst.get("hourly_usd", rate_usd))
        if not inst.get("ended_at"):
            running.append(f"{inst.get('name', 'vm')} running since {start.strftime('%Y-%m-%d %H:%M')} UTC")
    source = "estimate:wall-clock since launch x hourly rate" + (f"; {', '.join(running)}" if running else "")
    return SpendRow("lambda", round(hours, 3), "hours", round(cost, 4), max(credit_usd - cost, 0), credit_usd, source)


def snapshot(state_dir: Path, ledger_dir: Path, cfg: dict[str, Any], hf_month_usd: float, firecrawl_key: str = "",
             hf_billed: bool = False) -> list[SpendRow]:
    s = cfg.get("spend", {})
    rows = [
        huggingface(hf_month_usd, cfg.get("usage", {}).get("monthly_budget_usd", 20), hf_billed),
        firecrawl(CreditBook(state_dir / "firecrawl_credits.tsv"), s.get("firecrawl_plan_credits", 1000), firecrawl_key),
        lambda_billed(s["lambda_instances"], s.get("lambda_hourly_usd", 1.29), s.get("lambda_credit_usd", 75)) if s.get("lambda_instances")
        else lambda_hours(state_dir, s.get("lambda_hourly_usd", 1.29), s.get("lambda_credit_usd", 75)),
    ]
    append(ledger_dir / "spend.tsv", rows)
    return rows



TOKEN_COLUMNS = ("ts", "run", "subject", "step", "model", "tokens_in", "tokens_out", "cost_usd")


def append_tokens(path: Path, run: str, step: str, by_model: dict[str, dict[str, float]], subject: str = "-") -> int:
    """ledger/tokens.tsv: one row per (subject, step, model), written at the end of a run.

    Hermes' session records don't say which issue a session worked on, so run-wide rows
    use subject "-" and the cron job name as the step."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = [[ts, run, subject, step, model, str(int(agg["in"] + agg.get("cached", 0))), str(int(agg["out"])), f"{agg['usd']:.4f}"] for model, agg in sorted(by_model.items())]
    append_tsv(path, TOKEN_COLUMNS, rows)
    return len(rows)
