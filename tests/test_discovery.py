import json

import pytest

from conftest import iso, issue_json, repo_json
from fakes import FakeTransport, client
from pr_agent.devindex import CreditCapReached, DevIndex, credits_for, parse_id
from pr_agent.discover import DiscoveryRun, plan_queries
from pr_agent.github import GitHub
from pr_agent.ledger import Ledger
from pr_agent.state import CreditBook, SeenStore

BANK = {
    "topics": ["llm", "pandas", "nlp", "mlops"],
    "shapes": ["bug with traceback", "regression", "good first issue"],
    "topics_per_run": 3,
    "shapes_per_run": 2,
    "k": 20,
    "max_credits_per_run": 30,
    "max_credits_per_month": 900,
    "precedent_reserve_credits": 10,
    "max_candidates_per_run": 8,
    "recheck_after_days": 14,
    "verify": {"min_stars": 200, "max_stars": 30000, "skip_labels": ["wontfix"]},
}


def test_credits_and_ids():
    assert credits_for(10) == 2
    assert credits_for(11) == 4
    assert credits_for(20) == 4
    assert parse_id("issue:pandas-dev/pandas#123") == ("issue", "pandas-dev/pandas", 123)
    assert parse_id("readme:foo/bar") is None


def test_rotation_advances_and_wraps(tmp_path):
    rot = tmp_path / "rotation.json"
    first = plan_queries(BANK, rot)
    second = plan_queries(BANK, rot)
    assert first.topics == ["llm", "pandas", "nlp"]
    assert second.topics == ["mlops", "llm", "pandas"]
    assert first.shapes == ["bug with traceback", "regression"]
    assert second.shapes == ["good first issue", "bug with traceback"]
    assert len(first.queries) == 6
    assert first.queries[0]["topic"] == "llm" and first.queries[0]["language"] == "Python"


def test_index_refuses_before_spending_over_cap(tmp_path):
    fake = FakeTransport().add("POST", "/v2/search/developer", {"data": {"results": []}})
    idx = DevIndex(client("https://api.firecrawl.dev", fake), CreditBook(tmp_path / "c.tsv"), "r1", max_per_run=6, max_per_month=900)
    idx.search({"query": "q", "k": 20})
    with pytest.raises(CreditCapReached):
        idx.search({"query": "q2", "k": 20})
    assert len(fake.calls) == 1
    assert CreditBook(tmp_path / "c.tsv").spent(run="r1") == 4


def test_index_monthly_cap_survives_restart(tmp_path):
    book = CreditBook(tmp_path / "c.tsv")
    book.add("old", 898, "x")
    fake = FakeTransport().add("POST", "/v2/search/developer", {"data": {"results": []}})
    idx = DevIndex(client("https://api.firecrawl.dev", fake), book, "r2", max_per_run=30, max_per_month=900)
    with pytest.raises(CreditCapReached):
        idx.search({"query": "q", "k": 10 + 1})
    assert fake.calls == []


def test_index_429_backs_off_then_skips(tmp_path):
    fake = FakeTransport().add("POST", "/v2/search/developer", {"error": "slow down"}, status=429)
    idx = DevIndex(client("https://api.firecrawl.dev", fake), CreditBook(tmp_path / "c.tsv"), "r1")
    res = idx.search({"query": "q", "k": 10})
    assert res.skipped.startswith("rate limited")
    assert len(fake.calls) == 3
    assert idx.spent_this_run == 0


def hit(full, n, text="Traceback ..."):
    return {"id": f"issue:{full}#{n}", "type": "issue", "url": f"https://github.com/{full}/issues/{n}", "title": f"t{n}", "passages": [{"text": text}]}


def build(tmp_path, index_results, gh_routes):
    fi = FakeTransport()
    queue = list(index_results)

    def search(method, url, body):
        if body["types"] == ["issue"]:
            return 200, {"data": {"results": queue.pop(0) if queue else [], "coverage": {"issue": "ok"}}}
        return 200, {"data": {"results": gh_routes.get("precedent", {}).get(body["repos"][0], []), "coverage": {"pull_request": "ok"}}}

    fi.add("POST", "/v2/search/developer", search)
    fg = FakeTransport()
    for method, path, payload in gh_routes["routes"]:
        fg.add(method, path, payload)
    idx = DevIndex(client("https://api.firecrawl.dev", fi), CreditBook(tmp_path / "c.tsv"), "r1")
    gh = GitHub(client("https://api.github.com", fg), sleep=lambda s: None)
    ledger = Ledger(tmp_path / "decisions.tsv", run="r1")
    seen = SeenStore(tmp_path / "seen.tsv")
    run = DiscoveryRun(idx, gh, seen, ledger, BANK, tmp_path / "run", tmp_path / "rotation.json")
    return run, fi, fg, ledger, seen


def test_discovery_run_end_to_end(tmp_path):
    a, b = "org/alpha", "org/beta"
    routes = [
        ("GET", f"/repos/{a}", repo_json(a)),
        ("GET", f"/repos/{b}", repo_json(b, archived=True)),
        ("GET", f"/repos/{a}/issues/1", issue_json(a, 1, labels=[{"name": "good first issue"}])),
        ("GET", f"/repos/{a}/issues/1/timeline*", []),
        ("GET", f"/repos/{a}/issues/2", issue_json(a, 2, assignees=[{"login": "someone"}])),
        ("GET", f"/repos/{a}/issues/3", issue_json(a, 3)),
        ("GET", f"/repos/{a}/issues/3/timeline*", [{"event": "commented", "created_at": iso(3), "body": "I'm working on this, PR soon", "user": {"login": "dev"}}]),
        ("GET", f"/repos/{a}/issues/4", issue_json(a, 4)),
        ("GET", f"/repos/{a}/issues/4/timeline*", [{"event": "cross-referenced", "source": {"issue": {"number": 9, "state": "open", "pull_request": {}, "html_url": "https://github.com/org/alpha/pull/9"}}}]),
        ("GET", f"/repos/{a}/issues/5", issue_json(a, 5, title="Wrong dtype")),
        ("GET", f"/repos/{a}/issues/5/timeline*", []),
        ("GET", f"/repos/{a}/pulls/77", {"merged_at": iso(1), "html_url": "https://github.com/org/alpha/pull/77"}),
    ]
    precedent = {a: [{"id": f"pull_request:{a}#77", "url": "https://github.com/org/alpha/pull/77", "title": "Fix dtype", "passages": [{"text": "Fixes #5 by casting"}]},
                     {"id": f"pull_request:{a}#60", "url": "https://github.com/org/alpha/pull/60", "title": "Other", "passages": [{"text": "unrelated"}]}]}
    first = [hit(a, 1), hit(a, 2), hit(a, 3), hit(b, 7)]
    second = [hit(a, 1), hit(a, 4), hit(a, 5), {"id": "readme:org/alpha", "type": "readme"}]
    run, fi, fg, ledger, seen = build(tmp_path, [first, second], {"routes": routes, "precedent": precedent})
    run.seen.mark("issue:org/alpha#99", "verify", "closed", 14)

    summary = run.run()

    cands = [json.loads(l) for l in (tmp_path / "run" / "candidates.jsonl").read_text().splitlines()]
    assert [c["issue_id"] for c in cands] == ["issue:org/alpha#1"]
    assert cands[0]["lane_hint"] == "go-directly"
    assert cands[0]["precedent_prs"] == ["https://github.com/org/alpha/pull/77", "https://github.com/org/alpha/pull/60"]
    # 5 issue queries at 4 credits (the 6th is held back for precedent), then precedent checks at 2 each.
    issue_queries = [b for b in fi.called("POST", "/v2/search/developer") if b["types"] == ["issue"]]
    assert len(issue_queries) == 5
    assert summary["credits_run"] == 5 * 4 + 2 * 2
    by_subject = {r["subject"]: r for r in ledger.rows() if r["phase"] in ("discover.verify", "discover.precedent")}
    assert by_subject["issue:org/beta#7"]["decision"] == "dropped: repo archived"
    assert by_subject["issue:org/alpha#2"]["decision"] == "dropped: assigned to someone"
    assert by_subject["issue:org/alpha#3"]["decision"] == "dropped: claimed in a comment by dev"
    assert by_subject["issue:org/alpha#4"]["decision"] == "dropped: open PR #9 references it"
    assert by_subject["issue:org/alpha#5"]["decision"] == "dropped: already fixed"
    assert seen.is_fresh_skip("issue:org/alpha#5")["recheck_after"] == "never"
    assert seen.is_fresh_skip("issue:org/alpha#2")["last_verdict"] == "assigned to someone"


def test_discovery_stops_when_index_unavailable(tmp_path):
    fi = FakeTransport().add("POST", "/v2/search/developer", {"data": {"results": [], "coverage": {"issue": "unavailable"}}})
    idx = DevIndex(client("https://api.firecrawl.dev", fi), CreditBook(tmp_path / "c.tsv"), "r1")
    gh = GitHub(client("https://api.github.com", FakeTransport()))
    run = DiscoveryRun(idx, gh, SeenStore(tmp_path / "s.tsv"), Ledger(tmp_path / "d.tsv", "r1"), BANK, tmp_path / "run", tmp_path / "rot.json")
    summary = run.run()
    assert summary["index_unavailable"] is True
    assert len(fi.calls) == 1
    assert summary["candidates"] == 0


def test_queries_rotate_languages(tmp_path):
    from pr_agent.discover import plan_queries
    bank = {"topics": ["llm", "nlp"], "shapes": ["bug"], "topics_per_run": 2, "shapes_per_run": 1, "languages": ["Python", "JavaScript", "TypeScript"]}
    first = [q["language"] for q in plan_queries(bank, tmp_path / "rot.json").queries]
    second = [q["language"] for q in plan_queries(bank, tmp_path / "rot.json").queries]
    assert first == ["Python", "JavaScript"]
    assert second == ["TypeScript", "Python"]


def test_per_run_cap_spans_separate_processes(tmp_path):
    # Each pr-agent call builds its own DevIndex; the per-run backstop must still add up.
    fake = FakeTransport().add("POST", "/v2/search/developer", {"data": {"results": []}})
    first = DevIndex(client("https://api.firecrawl.dev", fake), CreditBook(tmp_path / "c.tsv"), "r1", max_per_run=6, max_per_month=900)
    first.search({"query": "q", "k": 20})
    second = DevIndex(client("https://api.firecrawl.dev", fake), CreditBook(tmp_path / "c.tsv"), "r1", max_per_run=6, max_per_month=900)
    with pytest.raises(CreditCapReached):
        second.search({"query": "q2", "k": 20})
    assert len(fake.calls) == 1


def test_lane_hint_builds_directly_unless_the_issue_is_unsettled():
    from pr_agent.verify import lane_hint
    assert lane_hint({"labels": []}) == "go-directly"
    assert lane_hint({"labels": [{"name": "bug"}, {"name": "documentation"}]}) == "go-directly"
    assert lane_hint({"labels": [{"name": "Needs-Triage"}]}) == "ask-first"
    assert lane_hint({"labels": [{"name": "RFC"}]}) == "ask-first"
