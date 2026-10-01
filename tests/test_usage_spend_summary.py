import sqlite3
from datetime import datetime, timezone

from pr_agent.ledger import Ledger
from pr_agent.publish import Registry
from pr_agent.spend import firecrawl, lambda_hours
from pr_agent.state import CreditBook
from pr_agent.summary import run_summary
from pr_agent.usage import ModelEntry, report

MENU = [ModelEntry("nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-FP8", ["main"], 0.5, 1.5), ModelEntry("Qwen/Qwen3.5-397B-A17B", ["fix"], 0.6, 2.4)]


def state_db(path, rows):
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE sessions (id TEXT, model TEXT, started_at REAL, input_tokens INT, output_tokens INT, cache_read_tokens INT, cache_write_tokens INT, reasoning_tokens INT)")
    con.executemany("INSERT INTO sessions VALUES (?,?,?,?,?,0,0,0)", rows)
    con.commit()
    con.close()


def test_guard_prices_sessions_and_flags_budget(tmp_path):
    now = datetime(2026, 10, 15, 12, tzinfo=timezone.utc)
    today = now.timestamp() - 60
    last_week = datetime(2026, 10, 8, tzinfo=timezone.utc).timestamp()
    last_month = datetime(2026, 9, 30, tzinfo=timezone.utc).timestamp()
    db = tmp_path / "state.db"
    state_db(db, [
        ("a", "nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-FP8", today, 2_000_000, 1_000_000),
        ("b", "Qwen/Qwen3.5-397B-A17B:fireworks-ai", last_week, 1_000_000, 0),
        ("c", "mystery/model", last_week, 0, 1_000_000),
        ("d", "nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-FP8", last_month, 9_000_000, 9_000_000),
    ])
    rep = report(db, MENU, month_budget=10, day_budget=2, now=now)
    assert rep.day_usd == 2.5
    assert rep.month_usd == 2.5 + 0.6 + 2.4
    assert rep.unknown_models == ["mystery/model"]
    assert rep.over == "daily budget used: $2.50 of $2.00"
    assert report(db, MENU, month_budget=5, day_budget=10, now=now).over.startswith("monthly budget used")
    assert report(tmp_path / "missing.db", MENU, 10, 2, now=now).month_usd == 0


def test_spend_rows(tmp_path):
    book = CreditBook(tmp_path / "c.tsv")
    book.add("r", 24, "q")
    fc = firecrawl(book, 1000)
    assert (fc.used, fc.remaining, fc.unit) == (24, 976, "credits")
    proc = tmp_path / "proc"
    (proc / "sys/kernel/random").mkdir(parents=True)
    (proc / "sys/kernel/random/boot_id").write_text("boot-1\n")
    (proc / "uptime").write_text("7200.0 100.0\n")
    first = lambda_hours(tmp_path, 0.79, 75, proc=proc)
    (proc / "sys/kernel/random/boot_id").write_text("boot-2\n")
    (proc / "uptime").write_text("3600.0 1.0\n")
    second = lambda_hours(tmp_path, 0.79, 75, proc=proc)
    assert first.used == 2.0
    assert second.used == 3.0
    assert second.cost_usd == round(3 * 0.79, 4)
    assert second.remaining == 75 - round(3 * 0.79, 4)


def test_run_summary_reads_only_the_ledger(tmp_path):
    led = Ledger(tmp_path / "d.tsv", "r1")
    led.log("discover.summary", "r1", "40 hits, 12 verified, 3 candidates", "end", "x", "credits run 28, month 120")
    led.log("discover.verify", "issue:o/a#1", "dropped: assigned to bob", "", "", "dropped")
    led.log("discover.verify", "issue:o/a#2", "dropped: assigned to amy", "", "", "dropped")
    led.log("triage", "issue:o/a#3", "take (go-directly; bug-fix)", "clear repro, one function", "", "take")
    led.log("triage", "issue:o/a#4", "skip", "needs a design decision", "", "skip")
    led.log("pr.opened", "issue:o/a#3", "opened o/a#9", "self-review gate passed on this diff", "https://github.com/o/a/pull/9", "open")
    Ledger(tmp_path / "d.tsv", "other").log("triage", "issue:x/y#1", "take", "not this run", "", "take")
    reg = Registry(tmp_path)
    reg.save_pr("o/a#9", {"state": "open", "url": "https://github.com/o/a/pull/9", "title": "fix(a): cast"})
    text = run_summary(led.run_rows("r1"), reg, "r1", "Model spend today $0.40.")
    assert "Looked at: 40 hits, 12 verified, 3 candidates" in text
    assert "Dropped on GitHub check: 2 assigned." in text
    assert "Chose 1 of 2 candidates:" in text
    assert "+ issue:o/a#3: clear repro, one function" in text
    assert "- skipped issue:o/a#4: needs a design decision" in text
    assert "https://github.com/o/a/pull/9" in text
    assert "x/y#1" not in text
    assert "1 open PRs" in text
