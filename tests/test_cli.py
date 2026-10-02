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
    assert got["model.triage"] == "zai-org/GLM-5.3" and got["model.fix"] == "moonshotai/Kimi-K2.7-Code"
    assert set(got) >= {"model.gate", "model.summary", "firecrawl.per_run_credits", "schedule"}
