import sys
from pathlib import Path

import pytest

from pr_agent.ledger import Ledger
from pr_agent.policy import PolicyVerdict
from pr_agent.publish import Refused, Registry, open_pr, post_claim, preflight, record_gate
from pr_agent.workspace import changed_files, prepare, run_tests

BODY = "## Why\nadd() subtracted.\n\n## Scope\n- `pkg.add`\n\n## Blast Radius\nOne function.\n\n## Verification\n`pytest` 1 passed.\n"
LIMITS = {"max_prs_per_day": 3, "max_open_prs_per_repo": 1, "max_diff_lines": 400, "max_files": 20, "max_claims_per_day": 1}
ALLOW = PolicyVerdict("o/r", "allows", False, ["AGENTS.md"])


@pytest.fixture()
def ws(git_repo, tmp_path):
    meta = prepare("issue:o/r#7", "o/r", 7, "main", tmp_path / "workspaces", clone_url=str(git_repo))
    return meta


def fix(meta):
    Path(meta.path, "pkg.py").write_text("def add(a, b):\n    return a + b\n")


def test_prepare_is_idempotent_and_detects_pytest(ws, git_repo, tmp_path):
    again = prepare("issue:o/r#7", "o/r", 7, "main", tmp_path / "workspaces", clone_url=str(git_repo))
    assert again.path == ws.path
    assert ws.branch == "pr-agent/issue-7"
    assert ws.test_cmd.endswith("-m pytest -x -q")


def test_tests_run_without_secrets(ws, monkeypatch):
    monkeypatch.setenv("PRAGENT_GITHUB_TOKEN", "secret-value")
    Path(ws.path, "tests", "test_env.py").write_text("import os\n\ndef test_no_token():\n    assert 'PRAGENT_GITHUB_TOKEN' not in os.environ\n")
    res = run_tests(Path(ws.path), f"{sys.executable} -m pytest -q tests/test_env.py")
    assert res["passed"], res["tail"]


def test_changed_files_ignores_agent_dirs(ws):
    fix(ws)
    Path(ws.path, "new_test.py").write_text("x = 1\n")
    (Path(ws.path) / ".pr-agent" / "notes.md").write_text("private")
    changes = changed_files(Path(ws.path), ws.base_sha)
    assert sorted(changes) == ["new_test.py", "pkg.py"]
    assert changes["pkg.py"].endswith(b"a + b\n")


def test_refuses_without_gate(ws, tmp_path):
    fix(ws)
    with pytest.raises(Refused, match="no self-review gate"):
        preflight(ws, ALLOW, Registry(tmp_path), LIMITS, "fix(pkg): add numbers", BODY)


def test_refuses_when_diff_changes_after_gate(ws, tmp_path):
    fix(ws)
    record_gate(ws, "pass", "no findings", ["thermo", "security"])
    Path(ws.path, "pkg.py").write_text("def add(a, b):\n    return b + a\n")
    with pytest.raises(Refused, match="diff changed"):
        preflight(ws, ALLOW, Registry(tmp_path), LIMITS, "fix(pkg): add numbers", BODY)


def test_refuses_failed_gate_banned_repo_bad_title_and_body(ws, tmp_path):
    fix(ws)
    record_gate(ws, "fail", "breaks callers", ["thermo"])
    with pytest.raises(Refused, match="gate failed"):
        preflight(ws, ALLOW, Registry(tmp_path), LIMITS, "fix(pkg): add numbers", BODY)
    record_gate(ws, "pass", "ok", ["thermo", "security"])
    with pytest.raises(Refused, match="policy is bans"):
        preflight(ws, PolicyVerdict("o/r", "bans", False, []), Registry(tmp_path), LIMITS, "fix(pkg): add numbers", BODY)
    with pytest.raises(Refused, match="Conventional Commits"):
        preflight(ws, ALLOW, Registry(tmp_path), LIMITS, "Fixed the add function.", BODY)
    with pytest.raises(Refused, match="missing ## Blast Radius"):
        preflight(ws, ALLOW, Registry(tmp_path), LIMITS, "fix(pkg): add numbers", BODY.replace("## Blast Radius", "## Risk"))


def test_refuses_workflow_edits_and_caps(ws, tmp_path):
    fix(ws)
    wf = Path(ws.path, ".github", "workflows")
    wf.mkdir(parents=True)
    (wf / "ci.yml").write_text("on: push\n")
    record_gate(ws, "pass", "ok", [])
    with pytest.raises(Refused, match="CI workflows"):
        preflight(ws, ALLOW, Registry(tmp_path), LIMITS, "fix(pkg): add numbers", BODY)
    (wf / "ci.yml").unlink()
    record_gate(ws, "pass", "ok", [])
    reg = Registry(tmp_path)
    reg.save_pr("o/r#1", {"repo": "o/r", "state": "open", "opened_at": "1999-01-01"})
    with pytest.raises(Refused, match="already have an open PR"):
        preflight(ws, ALLOW, reg, LIMITS, "fix(pkg): add numbers", BODY)


def test_open_pr_pushes_via_api_and_adds_footer(ws, tmp_path, gh, fake):
    fix(ws)
    record_gate(ws, "pass", "no findings", ["thermo-nuclear-review", "security-review"])
    fake.add("GET", "/user", {"login": "bot"})
    fake.add("GET", "/repos/bot/r", {"fork": True, "parent": {"full_name": "o/r"}})
    fake.add("POST", "/repos/bot/r/merge-upstream", {})
    fake.add("GET", f"/repos/bot/r/git/commits/{ws.base_sha}", {"tree": {"sha": "basetree"}})
    fake.add("POST", "/repos/bot/r/git/blobs", {"sha": "blob1"})
    fake.add("POST", "/repos/bot/r/git/trees", {"sha": "tree1"})
    fake.add("POST", "/repos/bot/r/git/commits", {"sha": "commit1"})
    fake.add("POST", "/repos/bot/r/git/refs", {"ref": "refs/heads/pr-agent/issue-7"})
    fake.add("POST", "/repos/o/r/pulls", {"number": 42, "html_url": "https://github.com/o/r/pull/42"})
    reg, led = Registry(tmp_path), Ledger(tmp_path / "d.tsv", "r1")

    pr = open_pr(gh, ws, ALLOW, reg, led, LIMITS, "fix(pkg): add numbers", BODY, "https://hf.co/buckets/x")

    assert pr["number"] == 42
    tree = fake.called("POST", "/git/trees")[0]
    assert tree["base_tree"] == "basetree" and [t["path"] for t in tree["tree"]] == ["pkg.py"]
    sent = fake.called("POST", "/repos/o/r/pulls")[0]
    assert sent["head"] == "bot:pr-agent/issue-7" and sent["draft"] is False
    assert "autonomous AI agent" in sent["body"] and "Fixes https://github.com/o/r/issues/7" in sent["body"]
    assert reg.prs()["o/r#42"]["state"] == "open"
    assert led.rows()[-1]["phase"] == "pr.opened"
    with pytest.raises(Refused, match="already have an open PR"):
        open_pr(gh, ws, ALLOW, reg, led, LIMITS, "fix(pkg): add numbers", BODY, "")
    assert led.rows()[-1]["phase"] == "pr.refused"


def test_claim_posts_once_and_respects_cap(gh, fake, tmp_path):
    fake.add("POST", "/repos/o/r/issues/7/comments", {"id": 1, "html_url": "https://github.com/o/r/issues/7#c1"})
    reg, led = Registry(tmp_path), Ledger(tmp_path / "d.tsv", "r1")
    post_claim(gh, "o/r", 7, "issue:o/r#7", "Cast the dtype in `read_csv` and add a test.", ALLOW, reg, led, LIMITS)
    body = fake.called("POST", "/issues/7/comments")[0]["body"]
    assert "autonomous AI agent" in body and "Cast the dtype" in body
    with pytest.raises(Refused, match="already claimed"):
        post_claim(gh, "o/r", 7, "issue:o/r#7", "again", ALLOW, reg, led, LIMITS)
    with pytest.raises(Refused, match="daily claim cap"):
        post_claim(gh, "o/r", 8, "issue:o/r#8", "plan", ALLOW, reg, led, LIMITS)
