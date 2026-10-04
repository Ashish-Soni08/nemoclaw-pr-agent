"""Host-side VM resource samples for the dashboard: ledger/host.tsv, one row a minute.

Runs on the VM host (not in the sandbox) from cron, standard library only. The agent's share is
summed over the cgroups of its own processes (the sandbox and NemoClaw), never derived from the
machine total, so other work on the VM doesn't count against it.
"""

from __future__ import annotations

import csv
import json
import os
import re
import shutil
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

COLUMNS = ("ts", "run", "cpu_pct", "load1", "ram_used_gb", "ram_total_gb", "gpu_util_pct", "vram_used_gb", "vram_total_gb",
           "disk_used_gb", "disk_total_gb", "agent_cpu_cores", "agent_ram_gb", "agent_vram_gb", "agent_disk_gb")
KEEP = timedelta(days=7)
GB = 1024 ** 3
# Processes that make up the agent: the OpenShell/NemoClaw gateway and everything in the sandbox.
AGENT_PROCS = os.environ.get("PR_AGENT_PROC_PATTERN", r"openshell|nemoclaw|hermes|k3s|containerd-shim")
CGROUP_ROOT = Path("/sys/fs/cgroup")
# A run with no end row (a crashed session) stops counting as in progress after this long.
RUN_MAX = timedelta(hours=2)
RUN_QUIET = timedelta(minutes=45)
DISK_EVERY = timedelta(minutes=15)


def _num(v: float | None, places: int = 2) -> str:
    return "" if v is None else f"{v:.{places}f}"


def cpu_times(proc: Path = Path("/proc")) -> tuple[int, int]:
    """(busy, total) jiffies since boot, from the aggregate cpu line."""
    fields = [int(x) for x in (proc / "stat").read_text().splitlines()[0].split()[1:]]
    idle = fields[3] + (fields[4] if len(fields) > 4 else 0)
    return sum(fields) - idle, sum(fields)


def memory_gb(proc: Path = Path("/proc")) -> tuple[float, float]:
    info = {}
    for line in (proc / "meminfo").read_text().splitlines():
        key, _, rest = line.partition(":")
        info[key] = int(rest.split()[0]) * 1024
    total = info["MemTotal"]
    return (total - info.get("MemAvailable", info.get("MemFree", 0))) / GB, total / GB


def gpu() -> tuple[float | None, float | None, float | None]:
    """(utilization %, VRAM used GB, VRAM total GB) summed over GPUs, or Nones without nvidia-smi."""
    if not shutil.which("nvidia-smi"):
        return None, None, None
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=20, check=True).stdout
    except (OSError, subprocess.SubprocessError):
        return None, None, None
    rows = [[float(x) for x in line.split(",")] for line in out.strip().splitlines() if line.strip()]
    if not rows:
        return None, None, None
    return sum(r[0] for r in rows) / len(rows), sum(r[1] for r in rows) / 1024, sum(r[2] for r in rows) / 1024


def gpu_pids() -> dict[int, float]:
    """VRAM GB per process using a GPU."""
    if not shutil.which("nvidia-smi"):
        return {}
    try:
        out = subprocess.run(["nvidia-smi", "--query-compute-apps=pid,used_memory", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=20, check=True).stdout
    except (OSError, subprocess.SubprocessError):
        return {}
    pids = {}
    for line in out.strip().splitlines():
        pid, _, mem = line.partition(",")
        if pid.strip().isdigit():
            pids[int(pid)] = float(mem or 0) / 1024
    return pids


def _cgroup_of(pid: int, proc: Path) -> str | None:
    try:
        for line in (proc / str(pid) / "cgroup").read_text().splitlines():
            if line.startswith("0::"):
                return line[3:]
    except OSError:
        pass
    return None


def agent_cgroups(proc: Path = Path("/proc"), pattern: str = AGENT_PROCS) -> set[str]:
    """cgroup v2 paths holding the agent's processes, outermost only, never a user session or the root."""
    override = os.environ.get("PR_AGENT_CGROUPS")
    if override:
        return {c.strip() for c in override.split(",") if c.strip()}
    rx = re.compile(pattern)
    found = set()
    for d in proc.iterdir():
        if not d.name.isdigit():
            continue
        try:
            cmd = (d / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
        except OSError:
            continue
        if not rx.search(cmd):
            continue
        cg = _cgroup_of(int(d.name), proc)
        # A login session's scope also holds shells and editors, so it can't stand for the agent.
        if cg and cg not in ("/", "/init.scope") and "session-" not in cg:
            found.add(cg)
    return {c for c in found if not any(c != o and c.startswith(o.rstrip("/") + "/") for o in found)}


def _stat(path: Path, key: str) -> int:
    return int(next(line.split()[1] for line in path.read_text().splitlines() if line.startswith(key + " ")))


def cgroup_usage(cgroups: set[str], root: Path = CGROUP_ROOT) -> tuple[dict[str, int], int | None]:
    """(cpu usage µs per cgroup, memory bytes summed).

    Memory is anonymous memory only: memory.current also counts page cache, which for a container
    that clones repos is many GB the kernel hands back on demand, and isn't comparable to host used RAM.
    """
    usec: dict[str, int] = {}
    mem, seen = 0, False
    for cg in cgroups:
        d = root / cg.lstrip("/")
        try:
            usec[cg] = _stat(d / "cpu.stat", "usage_usec")
            mem += _stat(d / "memory.stat", "anon")
            seen = True
        except (OSError, StopIteration, ValueError):
            continue
    return usec, (mem if seen else None)


def cpu_cores(prev: dict[str, int], cur: dict[str, int], elapsed: float) -> float | None:
    """Cores used between two samples, over cgroups present in both (a cgroup that appears
    between samples would otherwise count its whole lifetime's CPU at once)."""
    common = [cg for cg in cur if cg in prev and cur[cg] >= prev[cg]]
    if not common or elapsed <= 0:
        return None
    return sum(cur[cg] - prev[cg] for cg in common) / 1e6 / elapsed


def cgroup_pids(cgroups: set[str], root: Path = CGROUP_ROOT) -> set[int]:
    pids = set()
    for cg in cgroups:
        for f in (root / cg.lstrip("/")).rglob("cgroup.procs"):
            try:
                pids |= {int(p) for p in f.read_text().split()}
            except (OSError, ValueError):
                continue
    return pids


def current_run(decisions: Path, now: datetime) -> str:
    """The run in progress per the ledger mirror, or "-"."""
    if not decisions.exists():
        return "-"
    started, ended, last = {}, set(), {}
    with decisions.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh, delimiter="\t", quoting=csv.QUOTE_NONE):
            run = r.get("run", "")
            last[run] = r.get("ts", "")
            if r.get("phase") == "start":
                started[run] = r.get("ts", "")
            elif r.get("phase") == "run.end":
                ended.add(run)
    live = [(ts, run) for run, ts in started.items() if run and run not in ended]
    for ts, run in sorted(live, reverse=True):
        try:
            age = now - datetime.fromisoformat(ts.replace("Z", "+00:00"))
            quiet = now - datetime.fromisoformat(last[run].replace("Z", "+00:00"))
        except ValueError:
            continue
        # A run that crashed never logs run.end; treat a long silence as over.
        if age <= RUN_MAX and quiet <= RUN_QUIET:
            return run
    return "-"


def agent_disk_gb(state: dict, now: datetime) -> float | None:
    """Size of the agent's workspaces, measured inside the sandbox at most every 15 minutes."""
    last = state.get("disk_at")
    if last and now - datetime.fromisoformat(last) < DISK_EVERY:
        return state.get("disk_gb")
    host_dir = os.environ.get("PR_AGENT_WORKSPACE_HOST_DIR")
    try:
        if host_dir:
            cmd = ["du", "-sb", host_dir]
        else:
            sandbox = os.environ.get("PR_AGENT_SANDBOX", "pr-agent")
            cmd = ["nemohermes", sandbox, "exec", "--", "du", "-sb", "/sandbox/.pr-agent/workspaces"]
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=120).stdout
        size = int(out.split()[0]) / GB
    except (OSError, subprocess.SubprocessError, ValueError, IndexError):
        size = state.get("disk_gb")
    state["disk_at"], state["disk_gb"] = now.isoformat(), size
    return size


def sample(state: dict, mirror: Path, now: datetime | None = None, proc: Path = Path("/proc")) -> dict[str, str]:
    now = now or datetime.now(timezone.utc)
    mono = time.monotonic()
    busy, total = cpu_times(proc)
    cgroups = agent_cgroups(proc)
    usec, agent_mem = cgroup_usage(cgroups)
    prev = state.get("prev")
    if not prev:  # first sample: measure over one second instead of the last minute
        time.sleep(1)
        prev = {"busy": busy, "total": total, "usec": usec, "mono": mono}
        busy, total = cpu_times(proc)
        usec, agent_mem = cgroup_usage(cgroups)
        mono = time.monotonic()
    dt_total = total - prev["total"]
    cpu_pct = 100 * (busy - prev["busy"]) / dt_total if dt_total > 0 else None
    elapsed = mono - prev["mono"]
    cores = cpu_cores(prev.get("usec") if isinstance(prev.get("usec"), dict) else {}, usec, elapsed)
    state["prev"] = {"busy": busy, "total": total, "usec": usec, "mono": mono}

    ram_used, ram_total = memory_gb(proc)
    util, vram_used, vram_total = gpu()
    by_pid = gpu_pids()
    agent_vram = None if vram_used is None else sum(v for p, v in by_pid.items() if p in cgroup_pids(cgroups)) if by_pid else 0.0
    du = shutil.disk_usage("/")
    load1 = float((proc / "loadavg").read_text().split()[0])
    row = {
        "ts": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "run": current_run(mirror / "ledger" / "decisions.tsv", now),
        "cpu_pct": _num(cpu_pct, 1), "load1": _num(load1), "ram_used_gb": _num(ram_used), "ram_total_gb": _num(ram_total),
        "gpu_util_pct": _num(util, 1), "vram_used_gb": _num(vram_used), "vram_total_gb": _num(vram_total),
        "disk_used_gb": _num(du.used / GB, 1), "disk_total_gb": _num(du.total / GB, 1),
        "agent_cpu_cores": _num(cores), "agent_ram_gb": _num(None if agent_mem is None else agent_mem / GB),
        "agent_vram_gb": _num(agent_vram), "agent_disk_gb": _num(agent_disk_gb(state, now), 3),
    }
    state["cgroups"] = sorted(cgroups)
    return row


def append_trimmed(path: Path, row: dict[str, str], now: datetime) -> None:
    """Add a row and keep only the last seven days, written atomically so a sync never reads half a file."""
    cutoff = (now - KEEP).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = []
    if path.exists():
        with path.open(encoding="utf-8") as fh:
            rows = [r for r in csv.DictReader(fh, delimiter="\t") if r.get("ts", "") >= cutoff]
    rows.append(row)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, delimiter="\t", lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    tmp.replace(path)


def main() -> int:
    mirror = Path(os.environ.get("PR_AGENT_MIRROR", Path.home() / ".pr-agent-mirror"))
    mirror.mkdir(parents=True, exist_ok=True)
    state_path = mirror / "host-sampler.json"
    try:
        state = json.loads(state_path.read_text())
    except (OSError, ValueError):
        state = {}
    now = datetime.now(timezone.utc)
    row = sample(state, mirror, now)
    append_trimmed(mirror / "host.tsv", row, now)
    state_path.write_text(json.dumps(state))
    if os.environ.get("PR_AGENT_SAMPLER_EXPLAIN"):
        print(json.dumps({"row": row, "agent_cgroups": state["cgroups"]}, indent=1))
    return 0
