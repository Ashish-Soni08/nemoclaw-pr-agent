"""The Telegram run summary: what the agent looked at, what it chose and why, what's out there now.

Built from the ledger and the PR registry only, so it can't claim anything
the agent didn't log. Hermes delivers the cron job's final response to Telegram.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from .publish import Registry


def run_summary(rows: list[dict[str, str]], registry: Registry, run: str, usage_line: str = "") -> str:
    phases = Counter(r["phase"] for r in rows)
    lines = [f"PR agent run {run}"]
    disc = [r for r in rows if r["phase"] == "discover.summary"]
    if disc:
        lines.append(f"Looked at: {disc[-1]['decision']} ({disc[-1]['result']}).")
    elif phases:
        lines.append("Discovery did not finish this run.")
    dropped = Counter(r["decision"].split(":", 1)[1].strip().split(" ")[0] for r in rows if r["phase"] == "discover.verify" and r["result"] == "dropped" and ":" in r["decision"])
    if dropped:
        lines.append("Dropped on GitHub check: " + ", ".join(f"{n} {why}" for why, n in dropped.most_common(4)) + ".")
    policies = [r for r in rows if r["phase"] == "policy"]
    if policies:
        lines.append("AI policy: " + "; ".join(f"{r['subject']} {r['result']}" for r in policies[:5]) + ".")
    takes = [r for r in rows if r["phase"] == "triage" and r["result"] == "take"]
    skips = [r for r in rows if r["phase"] == "triage" and r["result"] == "skip"]
    if takes or skips:
        lines.append("")
        lines.append(f"Chose {len(takes)} of {len(takes) + len(skips)} candidates:")
        for r in takes:
            lines.append(f"+ {r['subject']}: {r['why']}")
        for r in skips[:5]:
            lines.append(f"- skipped {r['subject']}: {r['why']}")
        if len(skips) > 5:
            lines.append(f"- and {len(skips) - 5} more skipped (see ledger)")
    outcomes = [r for r in rows if r["phase"] in ("pr.opened", "pr.refused", "claim.posted", "gate", "fix.abandoned", "follow-up.reply", "follow-up.push")]
    if outcomes:
        lines.append("")
        lines.append("What happened:")
        for r in outcomes:
            lines.append(f"* {r['subject']}: {r['decision']} ({r['why']}) {r['evidence']}".rstrip())
    prs = registry.prs()
    open_prs = [p for p in prs.values() if p.get("state") == "open"]
    merged = [p for p in prs.values() if p.get("state") == "merged"]
    closed = [p for p in prs.values() if p.get("state") == "closed"]
    waiting = [k for k, c in registry.claims().items() if c.get("status") == "waiting"]
    lines.append("")
    lines.append(f"Out there now: {len(open_prs)} open PRs, {len(merged)} merged, {len(closed)} closed, {len(waiting)} claims waiting on maintainers.")
    for p in open_prs[:5]:
        lines.append(f"  {p['url']} ({p['title']})")
    if usage_line:
        lines.append(usage_line)
    return "\n".join(lines)


def daily_digest(rows: list[dict[str, str]], registry: Registry, day: str) -> str:
    today = [r for r in rows if r["ts"].startswith(day)]
    runs = sorted({r["run"] for r in today if r["run"]})
    opened = [r for r in today if r["phase"] == "pr.opened"]
    takes = [r for r in today if r["phase"] == "triage" and r["result"] == "take"]
    prs = registry.prs()
    lines = [
        f"PR agent daily digest {day}",
        f"{len(runs)} runs, {len(takes)} issues taken, {len(opened)} PRs opened.",
    ]
    for r in opened:
        lines.append(f"  {r['evidence']}")
    status: Counter[str] = Counter(p.get("state", "?") for p in prs.values())
    lines.append("All-time PRs: " + (", ".join(f"{n} {s}" for s, n in status.most_common()) or "none yet") + ".")
    return "\n".join(lines)


def compact_candidates(cands: list[dict[str, Any]]) -> list[dict[str, Any]]:
    keep = ("issue_id", "url", "title", "lane_hint", "policy", "claim_required", "ambiguous_claims", "precedent_prs")
    return [{k: c.get(k) for k in keep if c.get(k) not in (None, [], "")} | {"labels": c["github"]["labels"]} for c in cands]
