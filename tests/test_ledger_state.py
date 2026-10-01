from datetime import timedelta

from pr_agent.ledger import Ledger, clean
from pr_agent.state import CreditBook, SeenStore, today


def test_ledger_rows_are_single_line_and_formula_safe(tmp_path):
    led = Ledger(tmp_path / "decisions.tsv", run="r1")
    led.log("triage", "issue:a/b#1", "=HYPERLINK(evil)", "two\nlines\there", "-1", "+x")
    led.log("triage", "issue:a/b#2", "skip", "why", "", "skip")
    Ledger(tmp_path / "decisions.tsv", run="r2").log("start", "r2", "started", "", "", "open")

    text = (tmp_path / "decisions.tsv").read_text().splitlines()
    assert text[0] == "ts\trun\tphase\tsubject\tdecision\twhy\tevidence\tresult"
    assert len(text) == 4
    rows = led.rows()
    assert rows[0]["decision"] == "'=HYPERLINK(evil)"
    assert rows[0]["why"] == "two lines here"
    assert rows[0]["evidence"] == "'-1"
    assert [r["subject"] for r in led.run_rows("r1")] == ["issue:a/b#1", "issue:a/b#2"]


def test_clean_handles_none():
    assert clean(None) == ""


def test_seen_store_skip_windows(tmp_path):
    seen = SeenStore(tmp_path / "seen.tsv")
    seen.mark("issue:a/b#1", "verify", "closed", 14)
    seen.mark("issue:a/b#2", "pr", "pr opened", None)
    assert seen.is_fresh_skip("issue:a/b#1")["last_verdict"] == "closed"
    assert seen.is_fresh_skip("issue:a/b#1", on=today() + timedelta(days=15)) is None
    assert seen.is_fresh_skip("issue:a/b#2", on=today() + timedelta(days=999))["recheck_after"] == "never"
    assert seen.is_fresh_skip("issue:a/b#3") is None


def test_seen_store_keeps_first_seen(tmp_path):
    seen = SeenStore(tmp_path / "seen.tsv")
    seen.mark("issue:a/b#1", "verify", "kept", 14)
    first = seen.load()["issue:a/b#1"]["first_seen"]
    seen.mark("issue:a/b#1", "triage", "take", None)
    row = seen.load()["issue:a/b#1"]
    assert row["first_seen"] == first
    assert row["last_stage"] == "triage"


def test_credit_book_sums_by_run_and_month(tmp_path):
    book = CreditBook(tmp_path / "credits.tsv")
    book.add("r1", 4, "aa")
    book.add("r1", 4, "bb")
    book.add("r2", 2, "cc")
    assert book.spent() == 10
    assert book.spent(run="r1") == 8
    assert book.spent(month="1999-01") == 0
