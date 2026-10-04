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


def huggingface(month_usd: float, budget: float) -> SpendRow:
    return SpendRow("huggingface", month_usd, "usd", month_usd, max(budget - month_usd, 0), budget, "estimate:hermes-state.db x menu prices (month to date)")


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
                if "remaining_credits" in data:
                    remaining = float(data["remaining_credits"])
                    source = "api:/v2/team/credit-usage (remaining); local (used)"
        except OSError:
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


def snapshot(state_dir: Path, ledger_dir: Path, cfg: dict[str, Any], hf_month_usd: float, firecrawl_key: str = "") -> list[SpendRow]:
    s = cfg.get("spend", {})
    rows = [
        huggingface(hf_month_usd, cfg.get("usage", {}).get("monthly_budget_usd", 20)),
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
    rows = [[ts, run, subject, step, model, str(int(agg["in"])), str(int(agg["out"])), f"{agg['usd']:.4f}"] for model, agg in sorted(by_model.items())]
    append_tsv(path, TOKEN_COLUMNS, rows)
    return len(rows)
