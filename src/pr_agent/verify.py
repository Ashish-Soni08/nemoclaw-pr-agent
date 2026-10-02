"""Live GitHub checks for one Index hit. Cheapest checks first, stop at the first failure."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .github import GitHub

CLAIM = re.compile(
    r"\b(i'?ll (take|work on|pick up|handle)|i am (working|on it)|i'?m (working|on it|taking)|working on (this|it)|"
    r"can i (take|work on)|assign (this|it) to me|let me (take|work on)|i('d| would) like to work on)\b",
    re.IGNORECASE,
)
GO_DIRECT_LABELS = {"good first issue", "help wanted", "good-first-issue", "help-wanted", "contributions welcome", "easy"}
OSI_UNKNOWN = {None, "", "NOASSERTION", "OTHER"}


@dataclass
class Verdict:
    keep: bool
    reason: str
    evidence: str
    issue: dict[str, Any] = field(default_factory=dict)
    repo: dict[str, Any] = field(default_factory=dict)
    ambiguous_claims: list[str] = field(default_factory=list)


def _age_days(ts: str, now: datetime) -> float:
    return (now - datetime.fromisoformat(ts.replace("Z", "+00:00"))).total_seconds() / 86400


def verify_hit(gh: GitHub, full: str, number: int, cfg: dict[str, Any], now: datetime | None = None) -> Verdict:
    now = now or datetime.now(timezone.utc)
    issue_url = f"https://github.com/{full}/issues/{number}"
    repo = gh.repo(full)
    repo_url = f"https://github.com/{full}"
    if repo.get("archived"):
        return Verdict(False, "repo archived", repo_url)
    if repo.get("disabled") or not repo.get("has_issues", True):
        return Verdict(False, "repo has issues disabled", repo_url)
    if _age_days(repo["pushed_at"], now) > cfg.get("repo_pushed_within_days", 60):
        return Verdict(False, f"repo inactive: last push {repo['pushed_at'][:10]}", repo_url)
    spdx = (repo.get("license") or {}).get("spdx_id")
    if spdx in OSI_UNKNOWN:
        return Verdict(False, f"no recognised open-source license ({spdx or 'none'})", repo_url)
    stars = repo.get("stargazers_count", 0)
    if not cfg.get("min_stars", 0) <= stars <= cfg.get("max_stars", 10**9):
        return Verdict(False, f"stars {stars} outside window", repo_url)

    issue = gh.issue(full, number)
    if "pull_request" in issue:
        return Verdict(False, "is a pull request, not an issue", issue_url)
    if issue.get("state") != "open":
        return Verdict(False, f"issue {issue.get('state')}", issue_url)
    if issue.get("locked"):
        return Verdict(False, "issue locked", issue_url)
    if issue.get("assignees") or issue.get("assignee"):
        who = ",".join(a["login"] for a in issue.get("assignees") or [issue["assignee"]])
        return Verdict(False, f"assigned to {who}", issue_url)
    if _age_days(issue["updated_at"], now) > cfg.get("issue_updated_within_days", 180):
        return Verdict(False, f"stale: last update {issue['updated_at'][:10]}", issue_url)
    labels = {l["name"].lower() for l in issue.get("labels", [])}
    blocked = labels & {s.lower() for s in cfg.get("skip_labels", [])}
    if blocked:
        return Verdict(False, f"label {sorted(blocked)[0]}", issue_url)

    ambiguous: list[str] = []
    for event in gh.timeline(full, number):
        kind = event.get("event")
        if kind == "cross-referenced":
            src = (event.get("source") or {}).get("issue") or {}
            if "pull_request" in src and src.get("state") == "open":
                return Verdict(False, f"open PR #{src.get('number')} references it", src.get("html_url", issue_url))
        if kind == "connected":
            return Verdict(False, "a PR is linked to it", issue_url)
        if kind == "commented" and CLAIM.search(event.get("body") or ""):
            age = _age_days(event.get("created_at", issue["created_at"]), now)
            author = (event.get("user") or event.get("actor") or {}).get("login", "?")
            if age <= cfg.get("claim_hard_days", 14):
                return Verdict(False, f"claimed in a comment by {author}", event.get("html_url", issue_url))
            if age <= cfg.get("claim_window_days", 30):
                ambiguous.append(f"{author} ({int(age)}d ago): {(event.get('body') or '')[:160]}")

    return Verdict(True, "open, unassigned, nobody on it", issue_url, issue=issue, repo=repo, ambiguous_claims=ambiguous)


def lane_hint(issue: dict[str, Any]) -> str:
    labels = {l["name"].lower() for l in issue.get("labels", [])}
    return "go-directly" if labels & GO_DIRECT_LABELS else "ask-first"
