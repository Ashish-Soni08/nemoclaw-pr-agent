import json

import pytest

from pr_agent import cli


@pytest.fixture()
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("PR_AGENT_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "hermes"))
    for name in ("GITHUB_TOKEN", "PRAGENT_GITHUB_TOKEN", "FIRECRAWL_API_KEY", "PRAGENT_FIRECRAWL_KEY"):
        monkeypatch.delenv(name, raising=False)
    return tmp_path / "home"


def test_log_show_and_summary(home, capsys):
    assert cli.main(["run-start", "--label", "test"]) == 0
    run = capsys.readouterr().out.strip()
    assert cli.main(["log", "triage", "issue:o/r#1", "take (go-directly; bug-fix)", "--why", "clear repro", "--result", "take"]) == 0
    capsys.readouterr()
    assert cli.main(["summary", "run"]) == 0
    text = capsys.readouterr().out
    assert "**PR agent run**" in text and "• [o/r#1](https://github.com/o/r/issues/1): clear repro" in text
    assert "💸 **Spend** $0.00 / $" in text
    assert "📒 [Full ledger](https://nemoclaw-pr-agent-ledger.vercel.app)" in text
    spend = (home / "ledger" / "spend.tsv").read_text().splitlines()
    assert spend[0].split("\t") == ["ts", "provider", "used", "unit", "cost_usd", "remaining", "limit", "source"]
    assert [l.split("\t")[1] for l in spend[1:]] == ["huggingface", "firecrawl", "lambda"]


def test_prestep_reports_missing_token_instead_of_crashing(home, capsys):
    assert cli.main(["prestep-run"]) == 0
    gate = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert gate["wakeAgent"] is True
    assert "GITHUB_TOKEN is not set" in gate["context"]["error"]


def test_decide_rejects_bad_issue_id(home):
    with pytest.raises(SystemExit):
        cli.main(["decide", "not-an-issue", "take", "--why", "x"])


def test_decide_normalizes_issue_ids(home, capsys):
    assert cli.main(["decide", "o/r#5", "skip", "--why", "needs design"]) == 0
    seen = (home / "state" / "seen.tsv").read_text()
    assert "issue:o/r#5" in seen


def test_policy_block_is_logged_and_stored(home, capsys):
    assert cli.main(["policy", "o/r", "--block", "--why", "no AI PRs please", "--evidence", "https://github.com/o/r/pull/9#c2"]) == 0
    assert json.loads(capsys.readouterr().out)["blocked"] is True
    assert "o/r" in json.loads((home / "state" / "policy" / "blocked.json").read_text())
    rows = (home / "ledger" / "decisions.tsv").read_text().splitlines()
    assert rows[-1].split("\t")[2:5] == ["policy.block", "o/r", "stopped working in this repo for good"]


def test_run_start_records_run_config(home):
    from pr_agent.cli import App
    app = App()
    run = app.run_start("run")
    rows = [l.split("\t") for l in (app.s.ledger_dir / "run_config.tsv").read_text().splitlines()]
    assert rows[0] == ["run", "key", "value"]
    got = {k: v for r, k, v in rows[1:] if r == run}
    assert got["config"].startswith("config/agent.yaml @ ")
    assert got["model.triage"] == "zai-org/GLM-5.3" and got["model.fix"] == "Qwen/Qwen3-Coder-480B-A35B-Instruct"
    assert set(got) >= {"model.gate", "model.summary", "firecrawl.per_run_credits", "schedule"}


def test_agent_side_drop_is_not_recorded_as_a_maintainer_no(home, capsys, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "x")
    from pr_agent.cli import App
    App().registry.save_claim("issue:o/r#3", {"repo": "o/r", "number": 3, "status": "waiting", "comment_url": "https://github.com/o/r/issues/3#c1"})
    assert cli.main(["claim", "set", "issue:o/r#3", "dropped", "--why", "fix needs a CI workflow edit"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "dropped"
    row = (home / "ledger" / "decisions.tsv").read_text().splitlines()[-1].split("\t")
    assert row[2:5] == ["claim.status", "issue:o/r#3", "claim dropped"]


def test_changed_agent_code_is_logged_for_a_human(home, tmp_path, monkeypatch):
    import hashlib
    from pr_agent.cli import App
    repo = tmp_path / "deployed"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "pkg.py").write_text("x = 1\n")
    (repo / ".deployed-manifest").write_text(hashlib.sha256(b"x = 1\n").hexdigest() + "  src/pkg.py\n")
    monkeypatch.setattr(cli, "REPO_ROOT", repo)
    app = App()
    assert app.code_drift("r1") == ""
    (repo / "src" / "pkg.py").write_text("x = 2\n")
    assert "src/pkg.py" in app.code_drift("r1")
    row = (home / "ledger" / "decisions.tsv").read_text().splitlines()[-1].split("\t")
    assert row[2:5] == ["tool.error", "r1", "pr-agent's own code was changed since deploy"]


def test_run_now_refuses_near_the_schedule_and_during_a_run(home, tmp_path, monkeypatch):
    from datetime import datetime, timezone
    from pr_agent import runnow
    from pr_agent.cli import App, run_now
    hermes = tmp_path / "hermes"
    (hermes / "cron").mkdir(parents=True)
    (hermes / "cron" / "jobs.json").write_text(json.dumps({"jobs": [{"id": "j1", "name": "pr-agent-run", "schedule": "0 */4 * * *"}]}))
    started = []
    monkeypatch.setattr(runnow, "start", lambda job_id, log: started.append(job_id))
    monkeypatch.setattr(runnow, "cron_process_running", lambda: False)
    app = App()
    near = run_now(app, "owner asked", datetime(2026, 10, 4, 19, 45, tzinfo=timezone.utc))
    assert near["started"] is False and "20:00 UTC, in 15 min" in near["reason"]
    far = run_now(app, "owner asked", datetime(2026, 10, 4, 21, 0, tzinfo=timezone.utc))
    assert far["started"] is True and started == ["j1"]
    assert app.ledger.rows()[-1]["phase"] == "chat.run"
    app.run_start("run")
    busy = run_now(app, "again")
    assert busy["started"] is False and "already in progress" in busy["reason"]


def test_next_cron_time():
    from datetime import datetime, timezone
    from pr_agent.runnow import next_cron_time
    now = datetime(2026, 10, 4, 19, 37, tzinfo=timezone.utc)
    assert next_cron_time("0 */4 * * *", now) == datetime(2026, 10, 4, 20, 0, tzinfo=timezone.utc)
    assert next_cron_time("30 */2 * * *", now) == datetime(2026, 10, 4, 20, 30, tzinfo=timezone.utc)
    assert next_cron_time("0 9 * * 1", now) is None


def test_scripts_next_to_the_keyed_interpreter_are_quarantined(home, tmp_path, monkeypatch):
    # 2026-10-04: a run wrote probe-*.py into its state folder and ran them with the keyed
    # interpreter, calling GitHub directly. The next pre-step sets them aside and logs it.
    from pr_agent.cli import App
    monkeypatch.setattr(cli, "REPO_ROOT", tmp_path / "no-deploy")
    app = App()
    (home / "bin").mkdir(parents=True, exist_ok=True)
    (home / "bin" / "python").write_text("interpreter")
    (home / "bin" / "python").chmod(0o755)
    (home / "probe-ref.py").write_text("import pr_agent")
    (home / "probe.sh").write_text("exec python")
    (home / "provider-env").write_text("PLACEHOLDER=1")
    (home / "workspaces" / "o__r__1").mkdir(parents=True)
    (home / "workspaces" / "o__r__1" / "setup.py").write_text("repo code")

    warning = app.code_drift("r1")

    assert "probe-ref.py" in warning and "probe.sh" in warning
    assert not (home / "probe-ref.py").exists() and (home / "quarantine" / "r1" / "probe-ref.py").exists()
    assert (home / "bin" / "python").exists() and (home / "provider-env").exists()
    assert (home / "workspaces" / "o__r__1" / "setup.py").exists()
    row = (home / "ledger" / "decisions.tsv").read_text().splitlines()[-1].split("\t")
    assert row[2] == "tool.error" and row[-1] == "quarantined"
    assert app.code_drift("r2") == ""


def test_keyed_interpreter_only_runs_the_pr_agent_launcher():
    from pathlib import Path

    import pr_agent
    keyed = pr_agent.KEYED_PYTHON
    assert pr_agent._launched_by_pr_agent("/usr/bin/python3", ["python3", "probe.py"])
    assert pr_agent._launched_by_pr_agent(keyed, [keyed, "-c", pr_agent.LAUNCH, "pr", "open"])
    assert not pr_agent._launched_by_pr_agent(keyed, [keyed, "probe-ref.py"])
    assert not pr_agent._launched_by_pr_agent(keyed, [keyed, "-c", "import pr_agent.github"])
    # bin/pr-agent must start the interpreter with exactly this program.
    launcher = (Path(__file__).parents[1] / "bin" / "pr-agent").read_text()
    assert f"'{pr_agent.LAUNCH}'" in launcher


def test_hold_stops_every_github_write_and_scheduled_work(home, capsys, monkeypatch):
    # 2026-10-04: a run opened a PR nine seconds after its job was paused. A hold is checked
    # before each write, so it also stops a run that is already going.
    from pr_agent.cli import App
    from pr_agent.github import Held
    from fakes import FakeTransport, client
    monkeypatch.setenv("PRAGENT_GITHUB_TOKEN", "placeholder")
    app = App()
    assert cli.main(["hold", "on", "--why", "owner said stop on Telegram"]) == 0
    capsys.readouterr()
    fake = FakeTransport().add("POST", "/repos/o/r/pulls", {"number": 1})
    gh = app.gh()
    gh.client = client("https://api.github.com", fake)
    with pytest.raises(Held, match="owner said stop"):
        gh.open_pr("o/r", "bot:b", "main", "t", "b", False)
    assert fake.calls == []
    assert app.prestep_run() == {"wakeAgent": False} and app.prestep_follow_up() == {"wakeAgent": False}
    assert app.ledger.rows()[-1]["phase"] == "hold"
    assert cli.main(["hold", "status"]) == 0 and '"held": true' in capsys.readouterr().out
    assert cli.main(["hold", "off", "--why", "fixed"]) == 0
    capsys.readouterr()
    assert app.hold_reason() == ""


def test_follow_up_waits_while_the_main_run_is_going(home):
    from pr_agent.cli import App
    app = App()
    live = app.run_start("run")
    assert app.prestep_follow_up() == {"wakeAgent": False}
    row = app.ledger.rows()[-1]
    assert row["phase"] == "lock" and live in row["why"]


def test_run_now_can_start_the_follow_up_and_respects_a_hold(home, tmp_path, monkeypatch):
    from datetime import datetime, timezone
    from pr_agent import runnow
    from pr_agent.cli import App, run_now
    (tmp_path / "hermes" / "cron").mkdir(parents=True)
    (tmp_path / "hermes" / "cron" / "jobs.json").write_text(json.dumps({"jobs": [
        {"id": "j1", "name": "pr-agent-run", "schedule": "0 */4 * * *"},
        {"id": "j2", "name": "pr-agent-follow-up", "schedule": {"kind": "cron", "expr": "30 */2 * * *"}}]}))
    started = []
    monkeypatch.setattr(runnow, "start", lambda job_id, log: started.append(job_id))
    monkeypatch.setattr(runnow, "cron_process_running", lambda: False)
    app = App()
    at = datetime(2026, 10, 4, 21, 0, tzinfo=timezone.utc)
    assert run_now(app, "check the ComfyUI review", at, follow_up=True)["started"] is True and started == ["j2"]
    app.set_hold(True, "testing")
    held = run_now(app, "again", at)
    assert held["started"] is False and "on hold" in held["reason"]


def test_hold_and_lock_rows_dont_keep_a_crashed_run_alive():
    from datetime import datetime, timezone
    from pr_agent.runnow import run_in_progress
    rows = [{"ts": "2026-10-04T20:00:00Z", "run": "r1", "phase": "start", "decision": "started run run"},
            {"ts": "2026-10-04T20:05:00Z", "run": "r1", "phase": "triage", "decision": "take"},
            {"ts": "2026-10-04T21:10:00Z", "run": "r1", "phase": "hold", "decision": "put on hold"},
            {"ts": "2026-10-04T21:12:00Z", "run": "r1", "phase": "lock", "decision": "skipped follow-up"}]
    assert run_in_progress(rows, datetime(2026, 10, 4, 21, 20, tzinfo=timezone.utc)) == ""


def test_a_stopped_run_can_be_closed_so_the_lock_frees(home, monkeypatch):
    from datetime import datetime, timezone
    from pr_agent import runnow
    from pr_agent.cli import App, end_run
    monkeypatch.setattr(runnow, "cron_process_running", lambda: False)
    app = App()
    killed = app.run_start("run")
    assert runnow.run_in_progress(app.ledger.rows(), datetime.now(timezone.utc)) == killed
    assert end_run(app, "nope", "x")["ended"] is False
    assert end_run(app, killed, "gateway restarted by operator")["ended"] is True
    assert runnow.run_in_progress(app.ledger.rows(), datetime.now(timezone.utc)) == ""
    assert end_run(app, killed, "again")["reason"].endswith("already ended")


def test_run_start_refuses_inside_a_live_run(home):
    from pr_agent.cli import App, manual_start
    app = App()
    live = app.run_start("run")
    res = manual_start(app, "manual")
    assert res == {"started": False, "run": live, "reason": res["reason"]}
    assert "already going" in res["reason"]
    assert [r["run"] for r in app.ledger.rows() if r.get("phase") == "start"] == [live]


def test_claim_cannot_be_marked_approved_once_its_pr_is_open(home, monkeypatch):
    import pytest
    from pr_agent.cli import App, main
    monkeypatch.setenv("PRAGENT_GITHUB_TOKEN", "placeholder")
    reg = App().registry
    reg.save_claim("issue:acme/lib#7", {"status": "build", "comment_url": "https://github.com/acme/lib/issues/7#c"})
    reg.save_pr("acme/lib#9", {"issue_id": "issue:acme/lib#7", "repo": "acme/lib", "state": "open"})
    with pytest.raises(SystemExit, match="maintainer said yes"):
        main(["claim", "set", "acme/lib#7", "approved", "--why", "PR opened"])
    assert reg.claims()["issue:acme/lib#7"]["status"] == "build"


def test_a_pinned_repo_requires_a_claim_even_without_a_written_rule(home, monkeypatch):
    from pr_agent import policy as policy_mod
    from pr_agent.cli import App
    app = App()
    app.s.query_bank["pinned"] = [{"repo": "kestra-io/kestra", "claim_required": True}]
    monkeypatch.setattr(policy_mod, "check", lambda gh, repo, cache: policy_mod.PolicyVerdict(repo, "unclear", False, []))
    assert app.policy("Kestra-io/Kestra", None).claim_required is True
    assert app.policy("acme/lib", None).claim_required is False


def test_unanswered_claims_build_unless_the_repo_requires_a_yes(home, monkeypatch):
    from pr_agent import policy as policy_mod
    from pr_agent.cli import App
    app = App()
    gated = {"kubeflow/pipelines"}
    monkeypatch.setattr(policy_mod, "check", lambda gh, repo, cache: policy_mod.PolicyVerdict(repo, "unclear", repo in gated, []))
    for iid, repo in (("issue:nous/hermes#1", "nous/hermes"), ("issue:kubeflow/pipelines#2", "kubeflow/pipelines"), ("issue:nous/hermes#3", "nous/hermes")):
        app.registry.save_claim(iid, {"repo": repo, "status": "waiting", "comment_url": "u"})
    claims = [
        {"issue_id": "issue:nous/hermes#1", "state": "waiting", "replies": [], "assignees": []},
        {"issue_id": "issue:kubeflow/pipelines#2", "state": "waiting", "replies": [], "assignees": []},
        {"issue_id": "issue:nous/hermes#3", "state": "waiting", "replies": [{"author": "m", "body": "please wait"}], "assignees": []},
    ]
    out = app._build_unanswered(None, claims)
    assert [c["state"] for c in out] == ["build", "waiting", "waiting"]
    assert app.registry.claims()["issue:nous/hermes#1"]["status"] == "build"
    assert app.registry.claims()["issue:kubeflow/pipelines#2"]["status"] == "waiting"


def test_a_thumbs_down_on_the_plan_stops_build_directly(home, monkeypatch):
    from pr_agent import policy as policy_mod
    from pr_agent.cli import App
    app = App()
    monkeypatch.setattr(policy_mod, "check", lambda gh, repo, cache: policy_mod.PolicyVerdict(repo, "unclear", False, []))
    app.registry.save_claim("issue:plotly/plotly.js#8076", {"repo": "plotly/plotly.js", "status": "build", "comment_url": "u"})
    app.registry.save_claim("issue:nous/hermes#1", {"repo": "nous/hermes", "status": "waiting", "comment_url": "u"})
    frown = [{"author": "camdecoster", "content": "-1"}]
    claims = [
        {"issue_id": "issue:plotly/plotly.js#8076", "state": "waiting", "replies": [], "reactions": frown, "assignees": []},
        {"issue_id": "issue:nous/hermes#1", "state": "waiting", "replies": [], "reactions": [{"author": "x", "content": "+1"}], "assignees": []},
    ]
    out = app._build_unanswered(None, claims)
    assert [c["state"] for c in out] == ["waiting", "build"]
    assert app.registry.claims()["issue:plotly/plotly.js#8076"]["status"] == "waiting"
