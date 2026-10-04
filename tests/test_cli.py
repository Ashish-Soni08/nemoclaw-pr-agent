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
