"""The Telegram run summary: what the agent looked at, what it chose and why, what's out there now.

Built from the ledger and the PR registry only, so it can't claim anything
the agent didn't log. Hermes delivers the cron job's final response to Telegram,
rendering **bold**; everything else is plain text so a missed escape can't break it.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from .publish import Registry

# Phase -> (marker, label) for what became of a taken issue, last one wins.
OUTCOMES = {
    "pr.opened": ("🚀", "PR opened"),
    "pr.refused": ("🛑", "PR refused"),
    "claim.posted": ("💬", "Plan posted, waiting on maintainers"),
    "gate": ("🧪", "Gate"),
    "fix.abandoned": ("🛑", "Fix abandoned"),
    "issue.stop": ("⛔", "Stopped"),
}
FOLLOW_UPS = ("follow-up.reply", "follow-up.push")
DROP_REASONS = (
    ("closed", "closed"), ("stars", "too few stars"), ("license", "no OSS license"),
    ("assigned", "assigned"), ("claimed", "already claimed"), ("inactive", "inactive repo"),
    ("already fixed", "already fixed"), ("GitHub error", "GitHub error"),
)


def _name(subject: str) -> str:
    return subject.removeprefix("issue:")


def _short(text: str, limit: int = 110) -> str:
    first = re.split(r"(?<=[.;:])\s", text.strip(), maxsplit=1)[0].rstrip(".;:")
    return first if len(first) <= limit else first[:limit].rsplit(" ", 1)[0].rstrip(",;") + "…"


def _drop_reason(decision: str) -> str:
    for key, label in DROP_REASONS:
        if key in decision:
            return label
    return "other"


def _when(rows: list[dict[str, str]]) -> str:
    stamps = sorted(r["ts"] for r in rows if r.get("ts"))
    if not stamps:
        return ""
    start, end = stamps[0], stamps[-1]
    return f"{start[:10]}, {start[11:16]}–{end[11:16]} UTC"


def _out_there(registry: Registry) -> list[str]:
    prs = registry.prs()
    state = Counter(p.get("state") for p in prs.values())
    waiting = sum(1 for c in registry.claims().values() if c.get("status") == "waiting")
    lines = [f"📬 **Out there:** {state['open']} open PRs · {state['merged']} merged · {state['closed']} closed · {waiting} plans waiting"]
    for p in [p for p in prs.values() if p.get("state") == "open"][:5]:
        lines.append(f"• {p['title']}\n  {p['url']}")
    return lines


def run_summary(rows: list[dict[str, str]], registry: Registry, run: str, usage_line: str = "") -> str:
    lines = [f"🦞 **PR agent run** · {_when(rows) or run}"]

    disc = [r for r in rows if r["phase"] == "discover.summary"]
    if disc:
        lines.append(f"🔎 **Scouted:** {disc[-1]['decision']}")
    elif rows:
        lines.append("🔎 Discovery did not finish this run.")
    dropped = Counter(_drop_reason(r["decision"]) for r in rows if r["phase"] in ("discover.verify", "discover.precedent") and r["decision"].startswith("dropped"))
    if dropped:
        lines.append("🚮 **Dropped:** " + " · ".join(f"{n} {why}" for why, n in dropped.most_common(5)))
    policy = Counter(r["result"] for r in rows if r["phase"] == "policy")
    if policy:
        lines.append("📜 **AI policy:** " + " · ".join(f"{n} {verdict}" for verdict, n in policy.most_common()))

    takes = [r for r in rows if r["phase"] == "triage" and r["result"] == "take"]
    skips = [r for r in rows if r["phase"] == "triage" and r["result"] == "skip"]
    # The agent may log a second take row with its investigation; one entry per issue.
    takes = list({r["subject"]: r for r in reversed(takes)}.values())[::-1]
    if takes or skips:
        lines.append("")
        lines.append(f"✅ **Took {len(takes)} of {len(takes) + len(skips)}**")
        for r in takes:
            lane = re.search(r"\(([^;)]+)", r["decision"])
            lines.append(f"• **{_name(r['subject'])}**" + (f" ({lane.group(1)})" if lane else ""))
            lines.append(f"  {_short(r['why'])}")
            if r["evidence"].startswith("http"):
                lines.append(f"  {r['evidence']}")
            done = [o for o in rows if o["subject"] == r["subject"] and o["phase"] in OUTCOMES]
            if done:
                o = done[-1]
                mark, label = OUTCOMES[o["phase"]]
                detail = o["evidence"] if o["phase"] == "pr.opened" else _short(o["decision"].removeprefix("stopped: "))
                lines.append(f"  {mark} {label}: {detail}")
        if skips:
            lines.append("")
            lines.append(f"⏭️ **Skipped {len(skips)}**")
            for r in skips[:5]:
                lines.append(f"• {_name(r['subject'])}: {_short(r['why'], 90)}")
            if len(skips) > 5:
                lines.append(f"• …and {len(skips) - 5} more in the ledger")

    follow = [r for r in rows if r["phase"] in FOLLOW_UPS]
    if follow:
        lines.append("")
        lines.append("🔁 **Follow-ups**")
        for r in follow:
            lines.append(f"• {_name(r['subject'])}: {_short(r['decision'])} {r['evidence']}".rstrip())

    lines.append("")
    lines += _out_there(registry)
    if usage_line:
        lines.append(f"💸 {usage_line}")
    return "\n".join(lines)


def daily_digest(rows: list[dict[str, str]], registry: Registry, day: str) -> str:
    today = [r for r in rows if r["ts"].startswith(day)]
    runs = {r["run"] for r in today if r["phase"] == "start"} or {r["run"] for r in today if r["run"]}
    triaged = [r for r in today if r["phase"] == "triage"]
    takes = {r["subject"] for r in triaged if r["result"] == "take"}
    skips = {r["subject"] for r in triaged if r["result"] == "skip"}
    opened = [r for r in today if r["phase"] == "pr.opened"]
    plans = [r for r in today if r["phase"] == "claim.posted"]
    stops = [r for r in today if r["phase"] == "issue.stop"]
    lines = [
        f"📰 **PR agent daily digest** · {day}",
        "",
        f"🏃 {len(runs)} runs · {len(takes) + len(skips)} issues triaged · {len(takes)} taken · {len(skips)} skipped",
        f"🚀 {len(opened)} PRs opened · 💬 {len(plans)} plans posted · ⛔ {len(stops)} stopped",
    ]
    for r in opened:
        lines.append(f"• {_name(r['subject'])}\n  {r['evidence']}")
    for r in stops:
        lines.append(f"• {_name(r['subject'])}: {_short(r['decision'].removeprefix('stopped: '))}")
    lines.append("")
    lines += _out_there(registry)
    return "\n".join(lines)


def compact_candidates(cands: list[dict[str, Any]]) -> list[dict[str, Any]]:
    keep = ("issue_id", "url", "title", "lane_hint", "policy", "claim_required", "ambiguous_claims", "precedent_prs")
    return [{k: c.get(k) for k in keep if c.get(k) not in (None, [], "")} | {"labels": c["github"]["labels"]} for c in cands]
