from datetime import datetime, timedelta, timezone

from pr_agent import hoststats as hs

NOW = datetime(2026, 10, 4, 20, 0, tzinfo=timezone.utc)


def _proc(tmp_path, procs):
    proc = tmp_path / "proc"
    for pid, (cmd, cg) in procs.items():
        d = proc / str(pid)
        d.mkdir(parents=True)
        (d / "cmdline").write_bytes(cmd.replace(" ", "\0").encode())
        (d / "cgroup").write_text(f"0::{cg}\n")
    return proc


def test_agent_share_is_its_own_cgroups_not_sessions_or_the_root(tmp_path, monkeypatch):
    monkeypatch.delenv("PR_AGENT_CGROUPS", raising=False)
    proc = _proc(tmp_path, {
        10: ("/usr/bin/containerd-shim -id abc", "/system.slice/containerd.service"),
        11: ("python3 -m hermes gateway", "/system.slice/containerd.service/k8s/pod1"),
        12: ("openshell gateway", "/"),
        13: ("bash nemoclaw status", "/user.slice/user-1000.slice/session-3.scope"),
        14: ("python3 train.py", "/srv-lab.slice"),
    })
    assert hs.agent_cgroups(proc) == {"/system.slice/containerd.service"}


def test_cgroup_usage_sums_cpu_and_memory(tmp_path):
    root = tmp_path / "cg"
    for name, usec, mem in (("a", 2_000_000, 1024), ("b", 1_000_000, 2048)):
        (root / name).mkdir(parents=True)
        (root / name / "cpu.stat").write_text(f"usage_usec {usec}\nuser_usec 1\n")
        (root / name / "memory.current").write_text(str(mem * 100))  # mostly page cache
        (root / name / "memory.stat").write_text(f"anon {mem}\nfile {mem * 99}\n")
    assert hs.cgroup_usage({"/a", "/b"}, root) == ({"/a": 2_000_000, "/b": 1_000_000}, 3072)
    assert hs.cgroup_usage({"/missing"}, root) == ({}, None)


def test_cpu_counts_only_cgroups_seen_in_both_samples():
    prev = {"/a": 1_000_000}
    cur = {"/a": 31_000_000, "/new": 900_000_000}
    assert hs.cpu_cores(prev, cur, 60) == 0.5


def test_current_run_ignores_finished_and_stale_runs(tmp_path):
    led = tmp_path / "decisions.tsv"
    rows = [
        ("2026-10-04T16:00:00Z", "old", "start"),  # never ended, but too long ago
        ("2026-10-04T18:30:00Z", "done", "start"), ("2026-10-04T18:40:00Z", "done", "run.end"),
        ("2026-10-04T19:30:00Z", "live", "start"),
        ("2026-10-04T18:00:00Z", "crashed", "start"),  # quiet for 45+ minutes
    ]
    led.write_text("ts\trun\tphase\tsubject\n" + "".join(f"{t}\t{r}\t{p}\tx\n" for t, r, p in rows))
    assert hs.current_run(led, NOW) == "live"
    assert hs.current_run(led, NOW + timedelta(hours=3)) == "-"


def test_samples_keep_seven_days(tmp_path):
    path = tmp_path / "host.tsv"
    hs.append_trimmed(path, {"ts": "2026-09-26T00:00:00Z", "run": "-"}, NOW - timedelta(days=8))
    hs.append_trimmed(path, {"ts": "2026-10-04T19:59:00Z", "run": "-"}, NOW)
    lines = path.read_text().splitlines()
    assert lines[0].split("\t") == list(hs.COLUMNS)
    assert [line.split("\t")[0] for line in lines[1:]] == ["2026-10-04T19:59:00Z"]
