"""Everything that writes to someone else's repository, behind hard checks.

A PR opens only when all of these hold, checked here in code, not in a prompt:
the self-review gate passed on exactly this diff, the repo's AI policy allows
it, the daily and per-repo caps have room, and the body has the required
sections. The AI disclosure footer is added here, so it can't be forgotten.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .github import GitHub
from .ledger import Ledger
from .policy import PolicyVerdict
from .state import read_json, write_json
from .workspace import Meta, UnsafeChange, changed_files, diff_hash, diff_text

REQUIRED_SECTIONS = ("## Why", "## Scope", "## Blast Radius", "## Verification")
TITLE = re.compile(r"^(feat|fix|docs|refactor|test|chore|perf)(\([\w./-]+\))?: \S.{0,70}$")


class Refused(RuntimeError):
    """A publish precondition failed. The message says which, for the ledger."""


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Registry:
    """state/prs.json and state/claims.json: what the agent has out in the world."""

    state_dir: Path

    @property
    def prs_path(self) -> Path:
        return self.state_dir / "prs.json"

    @property
    def claims_path(self) -> Path:
        return self.state_dir / "claims.json"

    def prs(self) -> dict[str, dict[str, Any]]:
        return read_json(self.prs_path, {})

    def claims(self) -> dict[str, dict[str, Any]]:
        return read_json(self.claims_path, {})

    def save_pr(self, key: str, data: dict[str, Any]) -> None:
        prs = self.prs()
        prs[key] = {**prs.get(key, {}), **data}
        write_json(self.prs_path, prs)

    def save_claim(self, issue_id: str, data: dict[str, Any]) -> None:
        claims = self.claims()
        claims[issue_id] = {**claims.get(issue_id, {}), **data}
        write_json(self.claims_path, claims)

    def opened_today(self) -> int:
        day = utcnow().date().isoformat()
        return sum(1 for p in self.prs().values() if p.get("opened_at", "").startswith(day))

    def claims_today(self) -> int:
        day = utcnow().date().isoformat()
        return sum(1 for c in self.claims().values() if c.get("claimed_at", "").startswith(day))

    def open_in_repo(self, repo: str) -> list[str]:
        return [k for k, p in self.prs().items() if p.get("repo") == repo and p.get("state") == "open"]


def record_gate(meta: Meta, verdict: str, findings: str, reviewers: list[str]) -> dict[str, Any]:
    if verdict not in ("pass", "fail"):
        raise SystemExit("verdict must be pass or fail")
    gate = {
        "verdict": verdict,
        "diff_hash": diff_hash(Path(meta.path), meta.base_sha),
        "findings": findings,
        "reviewers": reviewers,
        "at": utcnow().isoformat(timespec="seconds"),
    }
    write_json(Path(meta.path) / ".pr-agent" / "gate.json", gate)
    return gate


def check_body(body: str) -> None:
    missing = [s for s in REQUIRED_SECTIONS if s not in body]
    if missing:
        raise Refused(f"PR body is missing {', '.join(missing)}")
    if "## Summary" in body or "## Test plan" in body:
        raise Refused("PR body uses Summary/Test plan boilerplate; use Why, Scope, Blast Radius, Verification")


def footer(issue_url: str, ledger_url: str, gate: dict[str, Any]) -> str:
    lines = [
        "",
        "---",
        "This pull request was written by an autonomous AI agent ([nemoclaw-pr-agent](https://github.com/Ashish-Soni08/nemoclaw-pr-agent)) "
        "running on NVIDIA NemoClaw. A self-review gate (correctness and security passes) approved this exact diff before it was opened. "
        "A human did not review it first.",
        f"Fixes {issue_url}",
    ]
    if ledger_url:
        lines.append(f"Every decision behind it is logged: {ledger_url}")
    lines.append("If AI-written PRs aren't welcome here, say so and the agent will close this and skip the repo.")
    return "\n".join(lines)


def check_changes(meta: Meta, limits: dict[str, Any]) -> dict[str, bytes | None]:
    """What may leave the sandbox, for a new PR and for every follow-up push alike."""
    ws = Path(meta.path)
    try:
        changes = changed_files(ws, meta.base_sha)
    except UnsafeChange as why:
        raise Refused(str(why)) from None
    if not changes:
        raise Refused("no changes to publish")
    n_lines = sum(1 for l in diff_text(ws, meta.base_sha).splitlines() if l[:1] in "+-" and l[:3] not in ("+++", "---"))
    if n_lines > limits.get("max_diff_lines", 400):
        raise Refused(f"diff is {n_lines} lines, over the {limits.get('max_diff_lines', 400)} line cap")
    if len(changes) > limits.get("max_files", 20):
        raise Refused(f"diff touches {len(changes)} files, over the cap")
    for path in changes:
        if path.startswith(".github/workflows/"):
            raise Refused("agent never edits CI workflows")
    return changes


def preflight(meta: Meta, policy: PolicyVerdict, registry: Registry, limits: dict[str, Any], title: str, body: str, allow_unclear: bool = False) -> tuple[dict[str, Any], dict[str, bytes | None]]:
    ws = Path(meta.path)
    gate = read_json(ws / ".pr-agent" / "gate.json", None)
    if not gate:
        raise Refused("no self-review gate verdict for this workspace")
    if gate["verdict"] != "pass":
        raise Refused(f"self-review gate failed: {gate['findings'][:200]}")
    if gate["diff_hash"] != diff_hash(ws, meta.base_sha):
        raise Refused("diff changed after the gate passed; run the gate again")
    if not policy.permits(allow_unclear):
        raise Refused(f"repo AI policy is {policy.verdict}")
    if 0 < limits.get("max_prs_per_day", 0) <= registry.opened_today():
        raise Refused("daily PR cap reached")
    if len(registry.open_in_repo(meta.repo)) >= limits.get("max_open_prs_per_repo", 1):
        raise Refused(f"already have an open PR in {meta.repo}")
    if not TITLE.match(title):
        raise Refused("title must be Conventional Commits: type(scope): subject, under ~70 chars")
    check_body(body)
    changes = check_changes(meta, limits)
    return gate, changes


def open_pr(gh: GitHub, meta: Meta, policy: PolicyVerdict, registry: Registry, ledger: Ledger, limits: dict[str, Any], title: str, body: str, ledger_url: str, draft: bool = False, allow_unclear: bool = False) -> dict[str, Any]:
    try:
        gate, changes = preflight(meta, policy, registry, limits, title, body, allow_unclear)
    except Refused as why:
        ledger.log("pr.refused", meta.issue_id, "did not open PR", str(why), meta.path, "refused")
        raise
    issue_url = f"https://github.com/{meta.repo}/issues/{meta.number}"
    full_body = body.rstrip() + "\n" + footer(issue_url, ledger_url, gate)
    fork = gh.ensure_fork(meta.repo)
    gh.sync_fork(fork, meta.base_branch)
    commit_sha = gh.push_files(fork, meta.branch, meta.base_sha, changes, f"{title}\n\nFixes {issue_url}")
    head = f"{fork.split('/')[0]}:{meta.branch}"
    pr = gh.open_pr(meta.repo, head, meta.base_branch, title, full_body, draft)
    key = f"{meta.repo}#{pr['number']}"
    registry.save_pr(
        key,
        {
            "repo": meta.repo,
            "number": pr["number"],
            "url": pr["html_url"],
            "issue_id": meta.issue_id,
            "title": title,
            "state": "open",
            "opened_at": utcnow().isoformat(timespec="seconds"),
            "commit": commit_sha,
            "workspace": meta.path,
            "seen_comment_ids": [],
        },
    )
    ledger.log("pr.opened", meta.issue_id, f"opened {key}", "self-review gate passed on this diff", pr["html_url"], "open")
    return pr


CLAIM_TEMPLATE = (
    "Hi! I'd like to work on this. I'm an autonomous AI agent "
    "([nemoclaw-pr-agent](https://github.com/Ashish-Soni08/nemoclaw-pr-agent)); my plan:\n\n{plan}\n\n"
    "I'll only open a PR if a maintainer is happy for me to take it. If AI-written contributions aren't wanted here, "
    "just say so and I'll leave the issue alone."
)


def post_claim(gh: GitHub, repo: str, number: int, issue_id: str, plan: str, policy: PolicyVerdict, registry: Registry, ledger: Ledger, limits: dict[str, Any], allow_unclear: bool = False) -> dict[str, Any]:
    if not policy.permits(allow_unclear):
        raise Refused(f"repo AI policy is {policy.verdict}")
    if issue_id in registry.claims():
        raise Refused("already claimed")
    if 0 < limits.get("max_claims_per_day", 0) <= registry.claims_today():
        raise Refused("daily claim cap reached")
    plan = plan.strip()
    if not plan or len(plan) > 800:
        raise Refused("plan must be 1-800 characters")
    comment = gh.comment(repo, number, CLAIM_TEMPLATE.format(plan=plan))
    registry.save_claim(issue_id, {"repo": repo, "number": number, "comment_url": comment["html_url"], "comment_id": comment["id"], "claimed_at": utcnow().isoformat(timespec="seconds"), "status": "waiting"})
    ledger.log("claim.posted", issue_id, "asked maintainers to take the issue", "repo expects contributors to ask first", comment["html_url"], "waiting")
    return comment


def ack_comments(registry: Registry, key: str, ids: list[int]) -> None:
    rec = registry.prs()[key]
    registry.save_pr(key, {"seen_comment_ids": sorted(set(rec.get("seen_comment_ids", [])) | set(ids))})


def claim_updates(gh: GitHub, registry: Registry, expire_days: int = 7) -> list[dict[str, Any]]:
    """Maintainer replies on issues we asked for. The model judges the text; assignment counts as yes."""
    out = []
    me = gh.login()
    for issue_id, claim in registry.claims().items():
        if claim.get("status") != "waiting":
            continue
        issue = gh.issue(claim["repo"], claim["number"])
        assignees = {a["login"] for a in issue.get("assignees") or []}
        replies = [
            {"author": c["user"]["login"], "association": c.get("author_association"), "body": c["body"][:600], "url": c["html_url"]}
            for c in gh.comments(claim["repo"], claim["number"], since=claim["claimed_at"])
            if c["id"] != claim["comment_id"] and c["user"]["login"] != me
        ]
        age = (utcnow() - datetime.fromisoformat(claim["claimed_at"])).days
        state = "assigned-to-us" if me in assignees else ("closed" if issue["state"] != "open" else ("expired" if age >= expire_days and not replies else "waiting"))
        out.append({"issue_id": issue_id, "state": state, "assignees": sorted(assignees), "replies": replies, "age_days": age})
    return out


def pr_updates(gh: GitHub, registry: Registry, ledger: Ledger | None = None) -> list[dict[str, Any]]:
    """New review comments, conversation comments and state changes on our open PRs.

    A PR seen merged or closed for the first time gets a pr.outcome row, keyed on the
    same issue id as its pr.opened row."""
    out = []
    me = gh.login()
    for key, rec in registry.prs().items():
        if rec.get("state") != "open":
            continue
        pr = gh.pr(rec["repo"], rec["number"])
        state = "merged" if pr.get("merged_at") else pr["state"]
        seen = set(rec.get("seen_comment_ids", []))
        new = []
        for c in gh.pr_review_comments(rec["repo"], rec["number"]):
            if c["id"] not in seen and c["user"]["login"] != me:
                new.append({"kind": "review", "id": c["id"], "author": c["user"]["login"], "path": c.get("path"), "line": c.get("line"), "body": c["body"][:800], "url": c["html_url"]})
        for c in gh.comments(rec["repo"], rec["number"]):
            if c["id"] not in seen and c["user"]["login"] != me:
                new.append({"kind": "conversation", "id": c["id"], "author": c["user"]["login"], "body": c["body"][:800], "url": c["html_url"]})
        # Comments stay "new" until the agent answers or acks them, so a crashed run loses nothing.
        registry.save_pr(key, {"state": state, "checked_at": utcnow().isoformat(timespec="seconds")})
        if state != "open" and ledger is not None:
            by = (pr.get("merged_by") or {}).get("login") if state == "merged" else ""
            why = f"merged by {by}" if by else ("merged" if state == "merged" else "closed without merging")
            ledger.log("pr.outcome", rec.get("issue_id") or key, f"{state} {key}", why, rec["url"], state)
        if new or state != "open":
            out.append({"pr": key, "url": rec["url"], "state": state, "new_comments": new})
    return out
