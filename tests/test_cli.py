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
    assert f"PR agent run {run}" in text and "+ issue:o/r#1: clear repro" in text
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
