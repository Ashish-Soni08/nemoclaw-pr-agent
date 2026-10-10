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
    (Path(ws.path) / ".pr-agent").mkdir(exist_ok=True)
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
    # Ashish, 2026-10-10: five per repo, so a second fix in the same repo opens.
    five = {**LIMITS, "max_open_prs_per_repo": 5}
    preflight(ws, ALLOW, reg, five, "fix(pkg): add numbers", BODY)
    for n in range(2, 6):
        reg.save_pr(f"o/r#{n}", {"repo": "o/r", "state": "open", "opened_at": "1999-01-01"})
    with pytest.raises(Refused, match="5 open PRs in o/r, the cap"):
        preflight(ws, ALLOW, reg, five, "fix(pkg): add numbers", BODY)


def test_open_pr_pushes_via_api_and_adds_footer(ws, tmp_path, gh, fake):
    fix(ws)
    record_gate(ws, "pass", "no findings", ["thermo-nuclear-review", "security-review"])
    fake.add("GET", "/user", {"login": "bot"})
    fake.add("GET", "/repos/bot/r", {"fork": True, "parent": {"full_name": "o/r"}})
    fake.add("POST", "/repos/bot/r/merge-upstream", {})
    fake.add("GET", "/repos/bot/r/git/ref/heads/main", {"object": {"sha": ws.base_sha}})
    fake.add("GET", f"/repos/bot/r/git/commits/{ws.base_sha}", {"tree": {"sha": "basetree"}})
    fake.add("POST", "/repos/bot/r/git/blobs", {"sha": "blob1"})
    fake.add("POST", "/repos/bot/r/git/trees", {"sha": "tree1"})
    fake.add("POST", "/repos/bot/r/git/commits", {"sha": "commit1"})
    fake.add("POST", "/repos/bot/r/git/refs", {"ref": "refs/heads/pr-agent/issue-7"})
    fake.add("POST", "/repos/o/r/pulls", {"number": 42, "html_url": "https://github.com/o/r/pull/42"})
    reg, led = Registry(tmp_path), Ledger(tmp_path / "d.tsv", "r1")

    pr = open_pr(gh, ws, ALLOW, reg, led, LIMITS, "fix(pkg): add numbers", BODY, "https://hf.co/datasets/x")

    assert pr["number"] == 42
    tree = fake.called("POST", "/git/trees")[0]
    assert tree["base_tree"] == "basetree" and [t["path"] for t in tree["tree"]] == ["pkg.py"]
    sent = fake.called("POST", "/repos/o/r/pulls")[0]
    assert sent["head"] == "bot:pr-agent/issue-7" and sent["draft"] is False
    assert "autonomous AI agent" in sent["body"] and "Fixes https://github.com/o/r/issues/7" in sent["body"]
    assert sent["body"].startswith("> Written by an autonomous AI agent")
    assert reg.prs()["o/r#42"]["state"] == "open"
    assert led.rows()[-1]["phase"] == "pr.opened"
    with pytest.raises(Refused, match="already have an open PR"):
        open_pr(gh, ws, ALLOW, reg, led, LIMITS, "fix(pkg): add numbers", BODY, "")
    assert led.rows()[-1]["phase"] == "pr.refused"


def _fork_moved(fake, ws, compare):
    fake.add("GET", "/user", {"login": "bot"})
    fake.add("GET", "/repos/bot/r", {"fork": True, "parent": {"full_name": "o/r"}})
    fake.add("POST", "/repos/bot/r/merge-upstream", {})
    fake.add("GET", "/repos/bot/r/git/ref/heads/main", {"object": {"sha": "newhead"}})
    fake.add("GET", f"/repos/bot/r/compare/{ws.base_sha}...newhead", compare)
    fake.add("GET", "/repos/bot/r/git/commits/newhead", {"tree": {"sha": "newtree"}})
    fake.add("POST", "/repos/bot/r/git/blobs", {"sha": "blob1"})
    fake.add("POST", "/repos/bot/r/git/trees", {"sha": "tree1"})
    fake.add("POST", "/repos/bot/r/git/commits", {"sha": "commit1"})
    fake.add("POST", "/repos/bot/r/git/refs", {"ref": "refs/heads/pr-agent/issue-7"})
    fake.add("POST", "/repos/o/r/pulls", {"number": 42, "html_url": "https://github.com/o/r/pull/42"})


def test_push_builds_on_the_current_upstream_head(ws, tmp_path, gh, fake):
    # Upstream merged CI changes since the workspace was cloned: building on the old base would roll them back.
    fix(ws)
    record_gate(ws, "pass", "no findings", ["thermo-nuclear-review", "security-review"])
    _fork_moved(fake, ws, {"status": "ahead", "files": [{"filename": ".github/workflows/ci.yml"}]})
    reg, led = Registry(tmp_path), Ledger(tmp_path / "d.tsv", "r1")

    open_pr(gh, ws, ALLOW, reg, led, LIMITS, "fix(pkg): add numbers", BODY, "")

    assert fake.called("POST", "/git/trees")[0]["base_tree"] == "newtree"
    assert fake.called("POST", "/git/commits")[0]["parents"] == ["newhead"]
    assert reg.prs()["o/r#42"]["parent"] == "newhead"


@pytest.mark.parametrize("compare, why", [
    ({"status": "ahead", "files": [{"filename": "pkg.py"}]}, "upstream changed pkg.py"),
    ({"status": "ahead", "files": [{"filename": "new.py", "previous_filename": "pkg.py"}]}, "upstream changed pkg.py"),
    ({"status": "diverged", "files": []}, "doesn't contain the workspace base"),
    ({"status": "ahead", "files": [{"filename": f"f{i}"} for i in range(300)]}, "too many files"),
])
def test_push_refuses_when_upstream_touched_our_files(ws, tmp_path, gh, fake, compare, why):
    fix(ws)
    record_gate(ws, "pass", "no findings", ["thermo-nuclear-review", "security-review"])
    _fork_moved(fake, ws, compare)
    reg, led = Registry(tmp_path), Ledger(tmp_path / "d.tsv", "r1")

    with pytest.raises(Refused, match=why):
        open_pr(gh, ws, ALLOW, reg, led, LIMITS, "fix(pkg): add numbers", BODY, "")
    assert not fake.called("POST", "/git/commits") and not fake.called("POST", "/pulls")
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
    fake.add("POST", "/repos/o/r/issues/8/comments", {"id": 2, "html_url": "https://github.com/o/r/issues/8#c2"})
    post_claim(gh, "o/r", 8, "issue:o/r#8", "plan", ALLOW, reg, led, {**LIMITS, "max_claims_per_day": 0})


def test_symlink_to_a_secret_is_never_published(ws, tmp_path):
    secret = tmp_path / "secrets.env"
    secret.write_text("GITHUB_TOKEN=real-token\n")
    fix(ws)
    Path(ws.path, "notes.txt").symlink_to(secret)
    record_gate(ws, "pass", "no findings", ["thermo", "security"])
    with pytest.raises(Refused, match="symlink"):
        preflight(ws, ALLOW, Registry(tmp_path), LIMITS, "fix(pkg): add numbers", BODY)


def test_follow_up_push_checks_workflows(ws, tmp_path):
    from pr_agent.publish import check_changes

    fix(ws)
    wf = Path(ws.path, ".github", "workflows")
    wf.mkdir(parents=True)
    (wf / "ci.yml").write_text("on: push\n")
    with pytest.raises(Refused, match="CI workflows"):
        check_changes(ws, LIMITS)


def test_unclear_policy_needs_the_switch(ws, tmp_path):
    unclear = PolicyVerdict("o/r", "unclear", False, [])
    fix(ws)
    record_gate(ws, "pass", "no findings", ["thermo", "security"])
    with pytest.raises(Refused, match="policy is unclear"):
        preflight(ws, unclear, Registry(tmp_path), LIMITS, "fix(pkg): add numbers", BODY)
    preflight(ws, unclear, Registry(tmp_path), LIMITS, "fix(pkg): add numbers", BODY, allow_unclear=True)


def test_pr_outcome_logged_once(gh, fake, tmp_path):
    from pr_agent.publish import pr_updates
    reg, led = Registry(tmp_path), Ledger(tmp_path / "d.tsv", "r2")
    reg.save_pr("o/r#42", {"repo": "o/r", "number": 42, "url": "https://github.com/o/r/pull/42", "issue_id": "issue:o/r#7", "state": "open"})
    fake.add("GET", "/user", {"login": "bot"})
    fake.add("GET", "/repos/o/r/pulls/42", {"state": "closed", "merged_at": "2026-10-02T10:00:00Z", "merged_by": {"login": "maint"}})
    fake.add("GET", "/repos/o/r/pulls/42/comments?per_page=100", [])
    fake.add("GET", "/repos/o/r/issues/42/comments?per_page=100", [])
    assert pr_updates(gh, reg, led)[0]["state"] == "merged"
    row = led.rows()[-1]
    assert (row["phase"], row["subject"], row["decision"], row["why"], row["result"]) == ("pr.outcome", "issue:o/r#7", "merged o/r#42", "merged by maint", "merged")
    assert pr_updates(gh, reg, led) == [] and len(led.rows()) == 1


def test_gate_hash_ignores_repo_diff_drivers(ws, tmp_path):
    # Repo code can set diff.external; an empty diff must not make every change look gated.
    import subprocess
    subprocess.run(["git", "config", "diff.external", "true"], cwd=ws.path, check=True)
    fix(ws)
    record_gate(ws, "pass", "no findings", ["thermo", "security"])
    Path(ws.path, "pkg.py").write_text("def add(a, b):\n    return b - a\n")
    with pytest.raises(Refused, match="diff changed"):
        preflight(ws, ALLOW, Registry(tmp_path), LIMITS, "fix(pkg): add numbers", BODY)


def test_diff_cap_counts_renames_and_refuses_binaries(ws, tmp_path):
    from pr_agent.workspace import diff_lines, UnsafeChange
    Path(ws.path, "big.py").write_text("x = 1\n" * 300)
    import subprocess
    subprocess.run(["git", "add", "big.py"], cwd=ws.path, check=True)
    subprocess.run(["git", "commit", "-qm", "big"], cwd=ws.path, check=True)
    ws.base_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ws.path, capture_output=True, text=True).stdout.strip()
    Path(ws.path, "big.py").rename(Path(ws.path, "moved.py"))
    assert diff_lines(Path(ws.path), ws.base_sha) == 600
    Path(ws.path, "blob.bin").write_bytes(b"\x00\x01" * 100)
    with pytest.raises(UnsafeChange, match="binary"):
        diff_lines(Path(ws.path), ws.base_sha)


def test_changed_files_keeps_exec_bit_and_unicode_paths(ws):
    fix(ws)
    script = Path(ws.path, "run.sh")
    script.write_text("#!/bin/sh\n")
    script.chmod(0o755)
    Path(ws.path, "é.py").write_text("y = 2\n")
    changes = changed_files(Path(ws.path), ws.base_sha)
    assert changes["run.sh"].mode == "100755"
    assert changes["é.py"] == b"y = 2\n" and changes["pkg.py"].mode == "100644"


def test_refuses_pr_while_claim_is_not_approved(ws, tmp_path):
    fix(ws)
    record_gate(ws, "pass", "no findings", ["thermo", "security"])
    reg = Registry(tmp_path)
    reg.save_claim("issue:o/r#7", {"repo": "o/r", "number": 7, "status": "declined"})
    with pytest.raises(Refused, match="claim on this issue is declined"):
        preflight(ws, ALLOW, reg, LIMITS, "fix(pkg): add numbers", BODY)
    reg.save_claim("issue:o/r#7", {"status": "approved"})
    preflight(ws, ALLOW, reg, LIMITS, "fix(pkg): add numbers", BODY)


def test_refuses_body_that_would_hide_the_disclosure(ws, tmp_path):
    fix(ws)
    record_gate(ws, "pass", "no findings", ["thermo", "security"])
    for trick in ("<!-- hidden", "--> <!-- hidden", "~~~\nhidden", "````\nhidden", "</details><details>",
                  "````\n```\nhidden", "~~~\n```\nhidden", "<details>\n<details>x</details>",
                  "<details>\n```\n</details>\n```\nhidden", "```\n<!--\n```\n-->\nhidden",
                  "<div>\n```\n</div>\n\n```\nhidden", "<!-- x -->",
                  "- item\n  ```\n<!--\n```\nhidden", "- item\n  ```\n```\nhidden", "> ```\nx", "- <div>"):
        with pytest.raises(Refused, match="raw HTML"):
            preflight(ws, ALLOW, Registry(tmp_path), LIMITS, "fix(pkg): add numbers", BODY + trick)


def test_one_open_pr_per_repo_ignores_case(tmp_path):
    reg = Registry(tmp_path)
    reg.save_pr("Org/Repo#1", {"repo": "Org/Repo", "number": 1, "state": "open"})
    assert reg.open_in_repo("org/repo") == ["Org/Repo#1"]


def test_build_claim_opens_unless_the_repo_requires_a_yes(ws, tmp_path):
    from dataclasses import replace
    fix(ws)
    record_gate(ws, "pass", "no findings", ["thermo", "security"])
    reg = Registry(tmp_path)
    reg.save_claim("issue:o/r#7", {"repo": "o/r", "number": 7, "status": "build"})
    with pytest.raises(Refused, match="wait for a maintainer"):
        preflight(ws, replace(ALLOW, claim_required=True), reg, LIMITS, "fix(pkg): add numbers", BODY)
    preflight(ws, ALLOW, reg, LIMITS, "fix(pkg): add numbers", BODY)


def test_build_claims_are_handed_on_until_a_pr_exists(gh, fake, tmp_path):
    from conftest import issue_json
    from pr_agent.publish import claim_updates
    fake.add("GET", "/user", {"login": "agent"})
    fake.add("GET", "/repos/o/r/issues/7", issue_json("o/r", 7, created_at="2026-01-01T00:00:00Z"))
    fake.add("GET", "/repos/o/r/issues/7/comments*", [])
    reg = Registry(tmp_path)
    reg.save_claim("issue:o/r#7", {"repo": "o/r", "number": 7, "comment_id": 1, "claimed_at": "2026-01-01T00:00:00+00:00", "status": "build"})
    assert [c["state"] for c in claim_updates(gh, reg)] == ["build"]
    reg.save_pr("o/r#9", {"repo": "o/r", "number": 9, "issue_id": "issue:o/r#7", "state": "open"})
    assert claim_updates(gh, reg) == []


def test_balanced_markup_is_fine():
    from pr_agent.publish import leaves_open
    ok = "```py\nx = 1\n```\n\n````\n```\n<!-- literal -->\n<details>\n````\nUse `a < b` here.\n"
    assert not leaves_open(ok)
    # Inside an HTML block GitHub renders fence lines as raw text, so any raw HTML counts.
    assert leaves_open("<div>\n```\n<details>\n```\n</div>\n")


def test_pr_updates_keep_the_finding_and_the_review_summary(gh, fake, tmp_path):
    # 2026-10-04: CodeRabbit's inline comment opened with its script logs; cut at 800 characters
    # nothing of the finding was left, and the request itself sat in the review summary.
    from pr_agent.publish import pr_updates
    reg = Registry(tmp_path)
    reg.save_pr("o/r#42", {"repo": "o/r", "number": 42, "url": "https://github.com/o/r/pull/42", "state": "open"})
    logs = "<details><summary>🧩 Analysis chain</summary>\n\n" + "rg output line\n" * 300 + "</details>"
    fake.add("GET", "/user", {"login": "bot"})
    fake.add("GET", "/repos/o/r/pulls/42", {"state": "open"})
    fake.add("GET", "/repos/o/r/pulls/42/reviews?per_page=100", [
        {"id": 7, "user": {"login": "coderabbitai[bot]"}, "state": "CHANGES_REQUESTED", "body": "Prompt to fix: return the token within a bounded cooldown <!-- internal -->"},
        {"id": 8, "user": {"login": "maint"}, "state": "APPROVED", "body": ""}])
    fake.add("GET", "/repos/o/r/pulls/42/comments?per_page=100", [
        {"id": 9, "pull_request_review_id": 7, "user": {"login": "coderabbitai[bot]"}, "path": "a.ts", "line": 3, "html_url": "u", "body": logs + "\n\n**Retry backoff per submission.** Use a cooldown."}])
    fake.add("GET", "/repos/o/r/issues/42/comments?per_page=100", [])

    new = pr_updates(gh, reg)[0]["new_comments"]

    summary, inline = new
    assert summary["kind"] == "review_summary" and "bounded cooldown" in summary["body"] and "internal" not in summary["body"]
    assert inline["review_id"] == 7 and "Use a cooldown" in inline["body"] and "rg output" not in inline["body"]


def _upstream_commit(git_repo, path, text):
    import subprocess
    Path(git_repo, path).write_text(text)
    subprocess.run(["git", "commit", "-qam", f"edit {path}"], cwd=git_repo, check=True, capture_output=True)
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=git_repo, check=True, capture_output=True, text=True).stdout.strip()


def test_rebase_moves_the_change_onto_upstream(ws, git_repo):
    from pr_agent.workspace import rebase
    fix(ws)
    Path(ws.path, "notes.py").write_text("x = 1\n")
    head = _upstream_commit(git_repo, "tests/test_pkg.py", "from pkg import add\n\ndef test_add():\n    assert add(2, 2) == 4\n")
    old = ws.base_sha

    res = rebase(ws, fetch_url=str(git_repo))

    assert res == {"rebased": True, "base_sha": head, "previous_base": old, "conflicts": []}
    changes = changed_files(Path(ws.path), ws.base_sha)
    assert sorted(changes) == ["notes.py", "pkg.py"] and changes["pkg.py"].endswith(b"a + b\n")
    assert "add(2, 2)" in Path(ws.path, "tests", "test_pkg.py").read_text()


def test_rebase_conflict_leaves_the_workspace_as_it_was(ws, git_repo):
    from pr_agent.workspace import rebase
    fix(ws)
    old = ws.base_sha
    _upstream_commit(git_repo, "pkg.py", "def add(a, b):\n    return sum((a, b))\n")

    res = rebase(ws, fetch_url=str(git_repo))

    assert res["rebased"] is False and res["conflicts"] == ["pkg.py"] and ws.base_sha == old
    assert Path(ws.path, "pkg.py").read_text().endswith("a + b\n")
    assert sorted(changed_files(Path(ws.path), old)) == ["pkg.py"]


def test_dco_signoff_only_for_listed_repos(ws, tmp_path, gh, fake):
    from pr_agent.publish import signoff_for
    dco = {"repos": ["O/R"], "name": "Owner Name", "email": "1+owner@users.noreply.github.com"}
    assert signoff_for(dco, "other/repo", "fix: x") is None
    with pytest.raises(Refused, match="Signed-off-by"):
        signoff_for(dco, "other/repo", "fix: x\n\nSigned-off-by: Agent <a@b>")

    fix(ws)
    record_gate(ws, "pass", "no findings", ["thermo-nuclear-review", "security-review"])
    _fork_moved(fake, ws, {"status": "ahead", "files": []})
    open_pr(gh, ws, ALLOW, Registry(tmp_path), Ledger(tmp_path / "d.tsv", "r1"), LIMITS, "fix(pkg): add numbers", BODY, "", dco=dco)

    commit = fake.called("POST", "/git/commits")[0]
    who = {"name": "Owner Name", "email": "1+owner@users.noreply.github.com"}
    assert commit["author"] == who and commit["committer"] == who
    assert commit["message"].endswith("\n\nSigned-off-by: Owner Name <1+owner@users.noreply.github.com>")


def test_no_signoff_by_default(ws, tmp_path, gh, fake):
    fix(ws)
    record_gate(ws, "pass", "no findings", ["thermo-nuclear-review", "security-review"])
    _fork_moved(fake, ws, {"status": "ahead", "files": []})
    open_pr(gh, ws, ALLOW, Registry(tmp_path), Ledger(tmp_path / "d.tsv", "r1"), LIMITS, "fix(pkg): add numbers", BODY, "")
    commit = fake.called("POST", "/git/commits")[0]
    assert "author" not in commit and "Signed-off-by" not in commit["message"]


def test_claim_updates_report_reactions_and_a_frown_stops_build(gh, fake, tmp_path):
    from conftest import issue_json
    from pr_agent.publish import claim_updates
    fake.add("GET", "/user", {"login": "agent"})
    fake.add("GET", "/repos/o/r/issues/7", issue_json("o/r", 7, created_at="2026-01-01T00:00:00Z"))
    fake.add("GET", "/repos/o/r/issues/7/comments*", [])
    fake.add("GET", "/repos/o/r/issues/comments/1/reactions*", [{"user": {"login": "maint"}, "content": "-1"}, {"user": {"login": "agent"}, "content": "+1"}])
    reg = Registry(tmp_path)
    reg.save_claim("issue:o/r#7", {"repo": "o/r", "number": 7, "comment_id": 1, "claimed_at": "2026-01-01T00:00:00+00:00", "status": "build"})
    (c,) = claim_updates(gh, reg)
    assert c["state"] == "waiting" and c["reactions"] == [{"author": "maint", "content": "-1"}]


def test_push_404_on_existing_ref_explains_the_workflow_scope(gh, fake):
    from pr_agent.http import HttpError
    fake.add("GET", "/repos/bot/r/git/commits/p1", {"tree": {"sha": "t0"}})
    fake.add("POST", "/repos/bot/r/git/blobs", {"sha": "b1"})
    fake.add("POST", "/repos/bot/r/git/trees", {"sha": "t1"})
    fake.add("POST", "/repos/bot/r/git/commits", {"sha": "c1"})
    fake.add("GET", "/repos/bot/r/git/ref/heads/pr-agent/issue-7", {"object": {"sha": "old"}})
    with pytest.raises(HttpError, match="Sync fork"):
        gh.push_files("bot/r", "pr-agent/issue-7", "p1", {"a.md": b"x"}, "docs: x")


def test_reply_guard_refuses_a_reply_ahead_of_the_branch():
    # hermes-agent#135681, 2026-10-09: "both done" was posted though the push never landed.
    from pr_agent.publish import reply_guard

    rec = {"tree": "t1", "pushed_at": "2026-10-09T10:00:00+00:00"}
    with pytest.raises(Refused, match="aren't on the PR yet"):
        reply_guard(rec, "Thanks, will look.", "2026-10-09T09:00:00Z", ws_tree="t2")
    with pytest.raises(Refused, match="nothing was pushed"):
        reply_guard(rec, "Both done: added the noqa and a behavior test.", "2026-10-09T11:00:00Z", ws_tree="t1")
    reply_guard(rec, "Done, pushed in the latest commit.", "2026-10-09T09:00:00Z", ws_tree="t1")
    reply_guard(rec, "Good question: the helper keeps the old signature on purpose.", "2026-10-09T11:00:00Z", ws_tree="t1")
    # Records from before the guard have no tree; the opened time stands in for the last push.
    with pytest.raises(Refused, match="nothing was pushed"):
        reply_guard({"opened_at": "2026-10-08T00:00:00+00:00"}, "Fixed.", "2026-10-09T11:00:00Z")


def test_latest_feedback_ignores_the_agent(gh, fake):
    from pr_agent.publish import latest_feedback

    fake.add("GET", "/user", {"login": "bot"})
    fake.add("GET", "/repos/o/r/pulls/5/comments", [
        {"id": 1, "user": {"login": "rev"}, "created_at": "2026-10-09T08:00:00Z"},
        {"id": 2, "user": {"login": "bot"}, "created_at": "2026-10-09T12:00:00Z"},
    ])
    fake.add("GET", "/repos/o/r/issues/5/comments", [{"id": 3, "user": {"login": "rev"}, "created_at": "2026-10-09T09:00:00Z"}])
    fake.add("GET", "/repos/o/r/pulls/5/reviews", [{"id": 4, "user": {"login": "rev"}, "submitted_at": "2026-10-09T10:00:00Z"}])
    rec = {"repo": "o/r", "number": 5}
    assert latest_feedback(gh, rec, 1) == "2026-10-09T08:00:00Z"
    assert latest_feedback(gh, rec) == "2026-10-09T10:00:00Z"


def test_sync_fork_reports_a_refusal(gh, fake):
    fake.add("POST", "/repos/bot/r/merge-upstream", {"message": "Not Found"}, status=404)
    assert gh.sync_fork("bot/r", "main") == "HTTP 404 Not Found"
    fake.add("POST", "/repos/bot/r/merge-upstream", {"merge_type": "fast-forward"})
    assert gh.sync_fork("bot/r", "main") == ""
