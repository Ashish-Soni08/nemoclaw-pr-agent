import json

import pytest

from pr_agent import cli
from pr_agent.lessons import MAX_PER_REPO, Lessons


@pytest.fixture()
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("PR_AGENT_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "hermes"))
    return tmp_path / "home"


def test_add_list_drop_and_ledger_rows(home, capsys):
    assert cli.main(["lesson", "add", "o/r", "o/r wants a CHANGELOG entry", "--source", "review", "--evidence", "https://github.com/o/r/pull/1#c1"]) == 0
    lid = json.loads(capsys.readouterr().out)["id"]
    assert cli.main(["lesson", "add", "*", "keep docs PRs free of reformatting", "--source", "pr.closed", "--evidence", "row 12"]) == 0
    capsys.readouterr()
    assert cli.main(["lesson", "list", "--repo", "O/R"]) == 0
    listed = json.loads(capsys.readouterr().out)
    assert len(listed) == 2 and listed[0].startswith(f"{lid} [o/r]")
    assert cli.main(["lesson", "list", "--repo", "x/y"]) == 0
    assert len(json.loads(capsys.readouterr().out)) == 1
    assert cli.main(["lesson", "drop", lid]) == 0
    capsys.readouterr()
    ledger = (home / "ledger" / "decisions.tsv").read_text()
    assert "lesson.add\to/r" in ledger and "lesson.drop\to/r" in ledger


def test_rejects_bad_input(home):
    for argv in (["lesson", "add", "not a repo", "x", "--source", "review", "--evidence", "e"],
                 ["lesson", "add", "o/r", "x", "--source", "made-up", "--evidence", "e"],
                 ["lesson", "add", "o/r", "x" * 300, "--source", "review", "--evidence", "e"]):
        with pytest.raises(SystemExit):
            cli.main(argv)


def test_duplicates_skip_and_oldest_retire(tmp_path):
    book = Lessons(tmp_path / "lessons.tsv")
    book.add("o/r", "same", "review", "e")
    assert "duplicate" in book.add("o/r", "Same", "review", "e")
    for i in range(MAX_PER_REPO):
        book.add("o/r", f"lesson {i}", "review", "e")
    active = book.active("o/r")
    assert len(active) == MAX_PER_REPO and active[0]["lesson"] == "lesson 0"
