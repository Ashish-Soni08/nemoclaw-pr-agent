"""The Telegram run summary: what the agent looked at, what it chose and why, what's out there now.

Built from the ledger and the PR registry only, so it can't claim anything
the agent didn't log. Hermes delivers the cron job's final response to Telegram,
rendering **bold**; everything else is plain text so a missed escape can't break it.
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import datetime
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


def _span(rows: list[dict[str, str]]) -> str:
    stamps = sorted(r["ts"] for r in rows if r.get("ts"))
    if not stamps:
        return ""
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    try:
        mins = round((datetime.strptime(stamps[-1], fmt) - datetime.strptime(stamps[0], fmt)).total_seconds() / 60)
    except ValueError:
        return f"{stamps[0][11:16]} UTC"
    return f"{stamps[0][11:16]} UTC · {mins} min"


def _issue_url(subject: str) -> str:
    m = re.fullmatch(r"(?:issue:)?([\w.-]+/[\w.-]+)#(\d+)", subject)
    return f"https://github.com/{m.group(1)}/issues/{m.group(2)}" if m else ""


def _repo(subject: str) -> str:
    return _name(subject).split("/", 1)[-1].split("#", 1)[0]


def _found(decision: str) -> str:
    m = re.match(r"(\d+) hits, (\d+) verified, (\d+) candidates", decision)
    return f"{m.group(1)} → {m.group(2)} live on GitHub → {m.group(3)} candidates" if m else decision


def _verdict(result: str) -> str:
    if result.startswith("allow"):
        return "allow"
    if result.startswith("ban"):
        return "ban"
    return result or "unclear"


def _out_there(registry: Registry) -> list[str]:
    prs = registry.prs()
    state = Counter(p.get("state") for p in prs.values())
    waiting = sum(1 for c in registry.claims().values() if c.get("status") == "waiting")
    lines = [f"📬 **Out there** {state['open']} open PRs · {state['merged']} merged · {waiting} claims"]
    for p in [p for p in prs.values() if p.get("state") == "open"][:5]:
        lines.append(f"• [{p['title']}]({p['url']})")
    return lines


def run_summary(rows: list[dict[str, str]], registry: Registry, run: str, usage_line: str = "", ledger_url: str = "") -> str:
    lines = [f"🦞 **PR agent run** · {_span(rows) or run}", ""]

    disc = [r for r in rows if r["phase"] == "discover.summary"]
    if disc:
        lines.append(f"🔎 **Found** {_found(disc[-1]['decision'])}")
    elif rows:
        lines.append("🔎 Discovery did not finish this run.")
    dropped = Counter(_drop_reason(r["decision"]) for r in rows if r["phase"] in ("discover.verify", "discover.precedent") and r["decision"].startswith("dropped"))
    if dropped:
        lines.append("🚮 **Dropped** " + " · ".join(f"{n} {why}" for why, n in dropped.most_common(4)))
    policy = Counter(_verdict(r["result"]) for r in rows if r["phase"] == "policy")
    if policy:
        lines.append(f"🛡️ **AI policy** {policy['allow']} allow · {policy['unclear']} unclear · {policy['ban']} ban")

    takes = [r for r in rows if r["phase"] == "triage" and r["result"] == "take"]
    skips = [r for r in rows if r["phase"] == "triage" and r["result"] == "skip"]
    # The agent may log a second take row with its investigation; one entry per issue.
    takes = list({r["subject"]: r for r in reversed(takes)}.values())[::-1]
    if takes:
        lines.append("")
        lines.append(f"✅ **Took {len(takes)}**")
        for r in takes:
            url = _issue_url(r["subject"])
            name = f"[{_name(r['subject'])}]({url})" if url else _name(r["subject"])
            lines.append(f"• {name}: {_short(r['why'], 80)}")
            done = [o for o in rows if o["subject"] == r["subject"] and o["phase"] in OUTCOMES]
            if done:
                o = done[-1]
                mark, label = OUTCOMES[o["phase"]]
                detail = o["evidence"] if o["phase"] == "pr.opened" else _short(o["decision"].removeprefix("stopped: "), 80)
                lines.append(f"   {mark} {label}: {detail}")
    if skips:
        lines.append("")
        lines.append(f"⏭️ **Skipped {len(skips)}**")
        for r in skips[:3]:
            lines.append(f"• {_name(r['subject'])}: {_short(r['why'], 60)}")
        if len(skips) > 3:
            rest = list(dict.fromkeys(_repo(r["subject"]) for r in skips[3:]))
            lines.append(f"• {', '.join(rest[:4])}{' and more' if len(rest) > 4 else ''}: reasons in the ledger")

    follow = [r for r in rows if r["phase"] in FOLLOW_UPS]
    if follow:
        lines.append("")
        lines.append("🔁 **Follow-ups**")
        for r in follow:
            lines.append(f"• {_name(r['subject'])}: {_short(r['decision'])} {r['evidence']}".rstrip())

    lines.append("")
    lines += _out_there(registry)
    if usage_line:
        lines.append(f"💸 **Spend** {usage_line}")
    if ledger_url:
        lines.append(f"📒 [Full ledger]({ledger_url})")
    return "\n".join(lines)


def daily_digest(rows: list[dict[str, str]], registry: Registry, day: str, spend_lines: list[str] | None = None) -> str:
    today = [r for r in rows if r["ts"].startswith(day)]
    runs = {r["run"] for r in today if r["phase"] == "start"} or {r["run"] for r in today if r["run"]}
    triaged = [r for r in today if r["phase"] == "triage"]
    takes = {r["subject"] for r in triaged if r["result"] == "take"}
    skips = {r["subject"] for r in triaged if r["result"] == "skip"}
    opened = [r for r in today if r["phase"] == "pr.opened"]
    stops = list({r["subject"]: r for r in today if r["phase"] in ("issue.stop", "pr.refused")}.values())
    try:
        label = datetime.strptime(day, "%Y-%m-%d").strftime("%a %-d %b")
    except ValueError:
        label = day
    lines = [
        f"📊 **Daily digest** · {label}",
        "",
        f"{len(runs)} runs · {len(takes) + len(skips)} triaged · {len(takes)} taken · {len(opened)} PRs",
    ]
    for r in opened:
        lines.append(f"• 🚀 {r['evidence']}")
    status = Counter(p.get("state", "?") for p in registry.prs().values())
    lines.append("🏁 PRs all-time: " + (" · ".join(f"{n} {s}" for s, n in status.most_common()) or "none yet"))
    if spend_lines:
        lines.append("")
        lines += [f"💸 {spend_lines[0]}"] + spend_lines[1:]
    if stops:
        lines.append("")
        lines.append("⚠️ **Needs you**")
        for r in stops:
            lines.append(f"• {_name(r['subject'])}: {_short(r['decision'].removeprefix('stopped: '), 80)}")
    return "\n".join(lines)


def compact_candidates(cands: list[dict[str, Any]]) -> list[dict[str, Any]]:
    keep = ("issue_id", "url", "title", "lane_hint", "policy", "claim_required", "track", "ambiguous_claims", "taken_by", "precedent_prs")
    return [{k: c.get(k) for k in keep if c.get(k) not in (None, [], "")} | {"labels": c["github"]["labels"]} for c in cands]
