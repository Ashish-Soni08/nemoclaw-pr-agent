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
    assert report(db, MENU, month_budget=10, day_budget=0, now=now).over == ""
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
    text = run_summary(led.run_rows("r1"), reg, "r1", "$0.40 / $400 HF", "https://huggingface.co/datasets/me/l/viewer")
    assert "🔎 **Found** 40 → 12 live on GitHub → 3 candidates" in text
    assert "🚮 **Dropped** 2 assigned" in text
    assert "✅ **Took 1**" in text
    assert "• [o/a#3](https://github.com/o/a/issues/3): clear repro, one function" in text
    assert "🚀 PR opened: https://github.com/o/a/pull/9" in text
    assert "⏭️ **Skipped 1**\n• o/a#4: needs a design decision" in text
    assert "x/y#1" not in text
    assert "1 open PRs" in text
    assert "💸 **Spend** $0.40 / $400 HF" in text
    assert "📒 [Full ledger](https://huggingface.co/datasets/me/l/viewer)" in text


def test_run_summary_shows_why_a_take_stopped(tmp_path):
    led = Ledger(tmp_path / "d.tsv", "r1")
    led.log("triage", "issue:o/a#5", "take (ask-first; bug-fix)", "Docs drift with three live findings. Long detail follows here", "https://github.com/o/a/issues/5", "take")
    led.log("triage", "issue:o/a#5", "take; 3 findings live", "investigation done", "/sandbox/ws", "take")
    led.log("issue.stop", "issue:o/a#5", "stopped: cannot post claim (token 403 in this org)", "plan saved", "/sandbox/plan.md", "stopped")
    text = run_summary(led.run_rows("r1"), Registry(tmp_path), "r1")
    assert text.count("o/a#5") == 1
    assert "• [o/a#5](https://github.com/o/a/issues/5): Docs drift with three live findings" in text
    assert "   ⛔ Stopped: cannot post claim (token 403 in this org)" in text


def test_daily_digest_counts_the_day(tmp_path):
    from pr_agent.summary import daily_digest
    led = Ledger(tmp_path / "d.tsv", "r1")
    led.log("start", "r1", "started", "cron tick", "", "open")
    led.log("triage", "issue:o/a#1", "take", "fixable", "", "take")
    led.log("triage", "issue:o/a#2", "skip", "not a bug", "", "skip")
    led.log("pr.opened", "issue:o/a#1", "opened o/a#9", "gate passed", "https://github.com/o/a/pull/9", "open")
    day = led.rows()[0]["ts"][:10]
    led.log("issue.stop", "issue:o/a#3", "stopped: cannot post claim (token 403)", "plan saved", "", "stopped")
    text = daily_digest(led.rows(), Registry(tmp_path), day, ["Today $1.20", "Left: $388 HF"])
    assert "1 runs · 2 triaged · 1 taken · 1 PRs" in text
    assert "• 🚀 https://github.com/o/a/pull/9" in text
    assert "🏁 PRs all-time: none yet" in text
    assert "💸 Today $1.20\nLeft: $388 HF" in text
    assert "⚠️ **Needs you**\n• o/a#3: cannot post claim (token 403)" in text


def test_tokens_for_one_run(tmp_path):
    from pr_agent.spend import append_tokens
    now = datetime(2026, 10, 15, 12, tzinfo=timezone.utc)
    db = tmp_path / "state.db"
    state_db(db, [
        ("a", "nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-FP8", now.timestamp() - 3600, 5, 5),
        ("b", "Qwen/Qwen3.5-397B-A17B", now.timestamp() - 60, 1_000_000, 500_000),
    ])
    by_model = report(db, MENU, 10, 0, now=now, since=now.timestamp() - 120).by_model
    out = tmp_path / "ledger" / "tokens.tsv"
    assert append_tokens(out, "run-1", "pr-agent-run", by_model) == 1
    header, row = out.read_text().splitlines()
    assert header.split("\t") == ["ts", "run", "subject", "step", "model", "tokens_in", "tokens_out", "cost_usd"]
    assert row.split("\t")[1:] == ["run-1", "-", "pr-agent-run", "Qwen/Qwen3.5-397B-A17B", "1000000", "500000", "1.8000"]


def test_run_summary_groups_extra_skips(tmp_path):
    led = Ledger(tmp_path / "d.tsv", "r1")
    led.log("policy", "o/a", "AI policy allows", "AGENTS.md", "-", "allows")
    led.log("policy", "o/b", "AI policy unclear", "none", "-", "unclear")
    for i, repo in enumerate(["a", "b", "c", "d", "e"]):
        led.log("triage", f"issue:o/{repo}#{i}", "skip", f"reason {i}", "", "skip")
    text = run_summary(led.run_rows("r1"), Registry(tmp_path), "r1")
    assert "🛡️ **AI policy** 1 allow · 1 unclear · 0 ban" in text
    assert "• d, e: reasons in the ledger" in text
    assert "o/d#3" not in text


def test_router_models_pins_cheapest_provider_with_tools(monkeypatch):
    from pr_agent import usage

    data = {"data": [{"id": "a/m", "providers": [
        {"provider": "cheap", "status": "live", "pricing": {"input": 0.1, "output": 0.2}, "supports_tools": False},
        {"provider": "mid", "status": "live", "pricing": {"input": 0.3, "output": 0.5}, "supports_tools": True},
        {"provider": "pricey", "status": "live", "pricing": {"input": 1.0, "output": 2.0}, "supports_tools": True},
    ]}]}

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        def get_json(self, path):
            return data

    monkeypatch.setattr(usage, "Client", FakeClient)
    got = usage.router_models("https://router", "t")["a/m"]
    assert got["pin"] == "a/m:mid" and got["pin_price"] == [0.3, 0.5]
    assert [p["provider"] for p in got["providers"]] == ["cheap", "mid", "pricey"]


def test_lambda_bills_wall_clock_since_launch():
    from datetime import datetime, timezone
    from pr_agent.spend import lambda_billed
    insts = [{"name": "old", "launched_at": "2026-10-01T19:04:00Z", "ended_at": "2026-10-01T20:00:00Z"},
             {"name": "vm", "launched_at": "2026-10-02T18:28:00Z"}]
    row = lambda_billed(insts, 1.29, 500, now=datetime(2026, 10, 4, 18, 19, tzinfo=timezone.utc))
    assert round(row.used, 2) == round(56 / 60 + 47 + 51 / 60, 2)
    assert round(row.cost_usd, 2) == round(row.used * 1.29, 2)
    assert "vm running since 2026-10-02 18:28 UTC" in row.source and "old" not in row.source


def test_cached_input_is_priced_at_the_cache_rate():
    glm = ModelEntry("zai-org/GLM-5.3", ["main"], 1.4, 4.4, price_cache_read=0.14)
    # Oct 1-4 token totals from Hermes; Hugging Face billed $8.05 for them.
    assert abs(glm.cost(845_539, 163_394 + 88_559, 41_475_520) - 8.05) < 0.1
    assert ModelEntry("x", [], 1.0, 2.0).cost(0, 0, 1_000_000) == 0.1


def test_firecrawl_remaining_comes_from_the_api(tmp_path):
    class Resp:
        ok = True
        def json(self):
            return {"success": True, "data": {"remainingCredits": 73633, "planCredits": 1000}}
    class C:
        def request(self, method, path):
            return Resp()
    book = CreditBook(tmp_path / "c.tsv")
    book.add("r", 396, "q")
    row = firecrawl(book, 70000, client=C())
    assert (row.used, row.remaining, row.limit) == (396, 73633, 74029)
    assert row.source.startswith("api:")


def test_sessions_are_priced_as_the_served_model(tmp_path):
    import sqlite3
    from datetime import datetime, timezone
    db = tmp_path / "state.db"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE sessions (model TEXT, input_tokens INT, cache_read_tokens INT, cache_write_tokens INT, output_tokens INT, reasoning_tokens INT, started_at REAL)")
    now = datetime(2026, 10, 4, 12, tzinfo=timezone.utc)
    con.execute("INSERT INTO sessions VALUES ('Qwen/Qwen3.5-397B-A17B', 1000000, 0, 0, 0, 0, ?)", (now.timestamp(),))
    con.commit(); con.close()
    assert report(db, MENU, 10, 0, now=now).month_usd == 0.6
    assert report(db, MENU, 10, 0, now=now, served_model="nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-FP8").month_usd == 0.5


def test_huggingface_bill_comes_from_its_usage_endpoint():
    from pr_agent.spend import huggingface_billed
    seen = []
    class Resp:
        def __init__(self, ok):
            self.ok = ok
        def json(self):
            return {"usage": {"inferenceProviders": {"usedNanoUsd": 10255033440, "numRequests": 1063}}}
    class C:
        def __init__(self, ok=True):
            self.ok = ok
        def request(self, method, path):
            seen.append(path)
            return Resp(self.ok)
    row = huggingface_billed("t", 400, client=C(), now=datetime(2026, 10, 4, 19, tzinfo=timezone.utc))
    assert (row.cost_usd, row.remaining, row.limit) == (10.255, 389.745, 400)
    assert row.source.startswith("api:") and "1063 requests" in row.source
    # Unix seconds for Oct 1 and Nov 1 UTC.
    assert seen[0].endswith("startDate=1790812800&endDate=1793491200")
    assert huggingface_billed("t", 400, client=C(ok=False)) is None


def test_guard_counts_hf_bill_when_it_beats_the_estimate(tmp_path):
    from pr_agent.spend import huggingface, last_billed
    tsv = tmp_path / "spend.tsv"
    tsv.write_text("ts\tprovider\tused\tunit\tcost_usd\tremaining\tlimit\tsource\n"
                   "2026-09-30T23:55:00Z\thuggingface\t390\tusd\t390\t10\t400\tapi:/api/settings/billing/usage-v2 inferenceProviders\n"
                   "2026-10-10T14:10:00Z\thuggingface\t239.84\tusd\t239.84\t160.16\t400\tapi:/api/settings/billing/usage-v2 inferenceProviders\n"
                   "2026-10-10T14:11:00Z\thuggingface\t111.71\tusd\t111.71\t288.29\t400\testimate:hermes-state.db tokens\n")
    now = datetime(2026, 10, 10, 15, tzinfo=timezone.utc)
    # The newest bill this month, never our own estimate rows or last month's bill.
    assert last_billed(tsv, now) == 239.84
    assert last_billed(tsv, datetime(2026, 11, 1, 1, tzinfo=timezone.utc)) is None
    assert last_billed(tmp_path / "missing.tsv", now) is None
    assert huggingface(239.84, 400, billed=True).source.startswith("billed:")


def test_app_guard_takes_the_higher_of_bill_and_estimate(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from pr_agent.cli import App
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    (tmp_path / "ledger").mkdir()
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    tsv = tmp_path / "ledger" / "spend.tsv"
    tsv.write_text("ts\tprovider\tused\tunit\tcost_usd\tremaining\tlimit\tsource\n"
                   f"{month}-01T00:05:00Z\thuggingface\t400\tusd\t400\t0\t400\tapi:billing\n")
    app = SimpleNamespace(s=SimpleNamespace(agent={"usage": {"monthly_budget_usd": 400, "daily_budget_usd": 0}}, ledger_dir=tmp_path / "ledger"))
    g = App.guard(app)
    assert (g.month_usd, g.billed) == (400, True) and g.over.startswith("monthly budget used")
    tsv.write_text(tsv.read_text().replace("\t400\tusd\t400\t0", "\t0.01\tusd\t0.01\t399.99"))
    state_db(tmp_path / "state.db", [("s", "nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-FP8", datetime.now(timezone.utc).timestamp(), 1_000_000, 0)])
    app.s.agent["models"] = [{"id": "nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-FP8", "price_in": 0.5, "price_out": 1.5}]
    g = App.guard(app)
    assert (g.month_usd, g.billed) == (0.5, False)
