"""One discovery run: Index search -> seen filter -> GitHub verify -> precedent -> candidates.jsonl.

The Index finds; GitHub confirms; the model triages what this writes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .devindex import CreditCapReached, DevIndex, credits_for, parse_id
from .github import GitHub
from .http import HttpError
from .ledger import Ledger
from .state import SeenStore, read_json, write_json
from .verify import lane_hint, verify_hit


@dataclass
class Plan:
    queries: list[dict[str, Any]]
    topics: list[str]
    shapes: list[str]


def plan_queries(bank: dict[str, Any], rotation_path: Path) -> Plan:
    """Take the next topics and shapes in the rotation, so every topic gets covered over a few runs."""
    topics: list[str] = bank["topics"]
    shapes: list[str] = bank["shapes"]
    rot = read_json(rotation_path, {"topic": 0, "shape": 0})
    # One language per query, rotating, so every run covers several languages for the same credits.
    languages: list[str] = bank.get("languages") or [bank.get("language", "Python")]
    lang_at = rot.get("language", 0)
    t_n, s_n = bank.get("topics_per_run", 3), bank.get("shapes_per_run", 2)
    run_topics = [topics[(rot["topic"] + i) % len(topics)] for i in range(t_n)]
    run_shapes = [shapes[(rot["shape"] + i) % len(shapes)] for i in range(s_n)]
    queries = []
    for topic in run_topics:
        for shape in run_shapes:
            language = languages[(lang_at + len(queries)) % len(languages)]
            queries.append(
                {
                    "query": shape,
                    "types": ["issue"],
                    "k": bank.get("k", 20),
                    "passages": 2,
                    "language": language,
                    "topic": topic,
                    "min_stars": bank.get("min_stars", 200),
                    "max_stars": bank.get("max_stars", 30000),
                    "archived": False,
                    "fork": False,
                }
            )
    write_json(rotation_path, {"topic": (rot["topic"] + t_n) % len(topics), "shape": (rot["shape"] + s_n) % len(shapes), "language": (lang_at + len(queries)) % len(languages)})
    return Plan(queries, run_topics, run_shapes)


@dataclass
class DiscoveryRun:
    index: DevIndex
    gh: GitHub
    seen: SeenStore
    ledger: Ledger
    bank: dict[str, Any]
    out_dir: Path
    rotation_path: Path
    hits: dict[str, dict[str, Any]] = field(default_factory=dict)
    summary: dict[str, Any] = field(default_factory=dict)

    def run(self) -> dict[str, Any]:
        plan = plan_queries(self.bank, self.rotation_path)
        self._pinned()
        self._search(plan)
        survivors = self._verify()
        candidates = self._precedent(survivors)
        path = self.out_dir / "candidates.jsonl"
        self.out_dir.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(c) + "\n" for c in candidates))
        self.summary.update(
            candidates=len(candidates),
            candidates_path=str(path),
            credits_run=self.index.spent_this_run,
            credits_month=self.index.month_spent(),
            topics=plan.topics,
        )
        self.ledger.log(
            "discover.summary",
            self.ledger.run,
            f"{self.summary.get('hits', 0)} hits, {self.summary.get('verified', 0)} verified, {len(candidates)} candidates",
            "end of discovery",
            str(path),
            f"credits run {self.index.spent_this_run}, month {self.summary['credits_month']}",
        )
        return self.summary

    def _pinned(self) -> None:
        """Repos the owner named (query bank `pinned`): their open, unassigned issues with the given
        label come straight from GitHub, ahead of the Index search, and go through the same checks."""
        for pin in self.bank.get("pinned") or []:
            repo, label = pin["repo"], pin.get("label")
            q = f"repo:{repo} is:issue is:open no:assignee" + (f' label:"{label}"' if label else "")
            try:
                found = self.gh.search_issues(q, per_page=pin.get("max_issues", 5), sort="updated")
            except HttpError as err:
                self.ledger.log("discover.pinned", repo, "pinned search failed", str(err)[:120], q, "error")
                continue
            for issue in found:
                hid = f"issue:{repo}#{issue['number']}"
                hit = {"id": hid, "url": issue["html_url"], "title": issue["title"], "passages": [{"text": (issue.get("body") or "")[:1200]}]}
                self.hits.setdefault(hid, {"hit": hit, "query": q, "topic": f"pinned:{repo}", "repo": repo, "number": issue["number"], "pinned": True})
            self.ledger.log("discover.pinned", repo, f"{len(found)} open {label or 'unassigned'} issues", pin.get("why", "pinned by the owner"), q, f"{len(found)} hits")

    def _search(self, plan: Plan) -> None:
        reserve = self.bank.get("precedent_reserve_credits", 10)
        for body in plan.queries:
            if self.index.spent_this_run + credits_for(body["k"]) + reserve > self.index.max_per_run:
                self.ledger.log("discover.query", body["query"][:60], "skipped query", f"keep {reserve} credits for precedent checks", f"topic={body['topic']}", "skipped")
                continue
            try:
                res = self.index.search(body)
            except CreditCapReached as cap:
                self.ledger.log("discover.query", body["query"][:60], "stopped searching", "credit cap", str(cap), "cap reached")
                break
            cov = res.coverage.get("issue") if isinstance(res.coverage, dict) else None
            if cov == "unavailable":
                self.ledger.log("discover.query", body["query"][:60], "index unavailable for issues", "coverage says unavailable", f"q={res.query_hash}", "ended run")
                self.summary["index_unavailable"] = True
                break
            self.ledger.log(
                "discover.query",
                f"{body['topic']}: {body['query'][:60]}",
                f"{len(res.hits)} hits" if not res.skipped else "query skipped",
                res.skipped or f"k={body['k']} credits={res.credits}",
                f"q={res.query_hash} coverage={json.dumps(res.coverage, sort_keys=True)}",
                f"coverage {cov or 'unknown'}",
            )
            for hit in res.hits:
                parsed = parse_id(hit.get("id", ""))
                if not parsed or parsed[0] != "issue":
                    continue
                hid = hit["id"]
                if hid not in self.hits:
                    self.hits[hid] = {"hit": hit, "query": body["query"], "topic": body["topic"], "repo": parsed[1], "number": parsed[2]}
        self.summary["hits"] = len(self.hits)

    def _verify(self) -> list[dict[str, Any]]:
        cfg = self.bank.get("verify", {})
        cap = self.bank.get("max_verify_per_run", 40)
        survivors: list[dict[str, Any]] = []
        checked = 0
        for hid, item in self.hits.items():
            row = self.seen.is_fresh_skip(hid)
            if row:
                self.ledger.log("discover.seen", hid, f"skipped: seen on {row['first_seen']}", row["last_verdict"], "state/seen.tsv", "skipped")
                continue
            if checked >= cap:
                break
            checked += 1
            try:
                # A pinned repo was chosen by the owner, so the star window doesn't apply.
                v = verify_hit(self.gh, item["repo"], item["number"], {**cfg, "min_stars": 0, "max_stars": 10**9} if item.get("pinned") else cfg)
            except HttpError as err:
                self.ledger.log("discover.verify", hid, "dropped: GitHub error", str(err)[:120], item["hit"].get("url", ""), "dropped")
                continue
            self.ledger.log("discover.verify", hid, "kept" if v.keep else f"dropped: {v.reason}", "live GitHub check", v.evidence, "kept" if v.keep else "dropped")
            if not v.keep:
                self.seen.mark(hid, "verify", v.reason, self.bank.get("recheck_after_days", 14))
                continue
            item["verdict"] = v
            survivors.append(item)
        self.summary["verified"] = checked
        return survivors[: self.bank.get("max_candidates_per_run", 8)]

    def _precedent(self, survivors: list[dict[str, Any]]) -> list[dict[str, Any]]:
        candidates = []
        for item in survivors:
            v = item["verdict"]
            hid = f"issue:{item['repo']}#{item['number']}"
            precedent: list[str] = []
            fixed_by = None
            body = {"query": v.issue["title"], "types": ["pull_request"], "repos": [item["repo"]], "k": 10, "passages": 1}
            if self.index.can_spend(10):
                try:
                    res = self.index.search(body)
                    for hit in res.hits:
                        parsed = parse_id(hit.get("id", ""))
                        if not parsed:
                            continue
                        text = " ".join(p.get("text", "") for p in hit.get("passages", [])) + " " + hit.get("title", "")
                        if f"#{item['number']}" in text and fixed_by is None:
                            pr = self.gh.pr(item["repo"], parsed[2])
                            if pr.get("merged_at"):
                                fixed_by = pr["html_url"]
                                continue
                        precedent.append(hit.get("url", ""))
                except (CreditCapReached, HttpError) as err:
                    self.ledger.log("discover.precedent", hid, "precedent check failed", str(err)[:120], "", "none")
            if fixed_by:
                self.ledger.log("discover.precedent", hid, "dropped: already fixed", "a merged PR references this issue", fixed_by, "already fixed")
                self.seen.mark(hid, "precedent", f"fixed by {fixed_by}", None)
                continue
            self.ledger.log("discover.precedent", hid, f"{len(precedent[:3])} precedent PRs", "examples of how this repo writes fixes", " ".join(precedent[:3]) or "-", "precedent found" if precedent else "none")
            issue, repo = v.issue, v.repo
            candidates.append(
                {
                    "issue_id": hid,
                    "url": issue["html_url"],
                    "repo": item["repo"],
                    "number": item["number"],
                    "title": issue["title"],
                    "found_by": {"query": item["query"], "topic": item["topic"]},
                    "pinned": bool(item.get("pinned")),
                    "passages": [p.get("text", "")[:1200] for p in item["hit"].get("passages", [])],
                    "github": {
                        "labels": [l["name"] for l in issue.get("labels", [])],
                        "comments": issue.get("comments", 0),
                        "created_at": issue["created_at"],
                        "updated_at": issue["updated_at"],
                        "stars": repo.get("stargazers_count"),
                        "default_branch": repo.get("default_branch"),
                    },
                    "ambiguous_claims": v.ambiguous_claims,
                    "precedent_prs": precedent[:3],
                    "lane_hint": lane_hint(issue),
                }
            )
            self.seen.mark(hid, "candidate", "candidate", self.bank.get("recheck_after_days", 14))
        return candidates
