import os
import subprocess
from pathlib import Path

import pytest

from pr_agent import jail
from pr_agent.workspace import Meta, control_dir, prepare, run

pytestmark = pytest.mark.skipif(jail.abi() < 1, reason="kernel without Landlock")

PROBE = r"""
import sys
def tried(f):
    try:
        f()
        return "allowed"
    except OSError:
        return "blocked"
secret, outside = sys.argv[1], sys.argv[2]
print(tried(lambda: open(secret).read()), tried(lambda: open(outside, "w").write("x")), tried(lambda: open("mine.txt", "w").write("x")))
"""


@pytest.fixture()
def no_shared_tmp(monkeypatch):
    # pytest's tmp_path lives under /tmp, which the jail leaves writable; take it out for these tests.
    monkeypatch.setattr(jail, "SHARED_WRITE", ["/dev"])


def test_jail_confines_repo_code_to_its_workspace(tmp_path, no_shared_tmp):
    ws, state = tmp_path / "workspaces" / "o__r__1", tmp_path / "state"
    ws.mkdir(parents=True)
    state.mkdir()
    (state / "blocked.json").write_text("{}")
    proc = run(["/usr/bin/python3", "-c", PROBE, str(state / "blocked.json"), str(state / "planted")], cwd=ws, env={"PATH": os.environ["PATH"], "HOME": str(tmp_path / "home")}, jail=ws)
    assert proc.stdout.split() == ["blocked", "blocked", "allowed"], proc.stderr
    assert not (state / "planted").exists()


def test_gate_and_meta_live_outside_the_workspace(git_repo, tmp_path, no_shared_tmp):
    meta = prepare("issue:o/r#7", "o/r", 7, "main", tmp_path / "workspaces", clone_url=str(git_repo))
    ws = Path(meta.path)
    assert meta.meta_path == control_dir(ws) / "meta.json" and meta.meta_path.exists()
    assert not str(meta.gate_path).startswith(str(ws) + os.sep)
    forged = f"import json; json.dump({{'verdict': 'pass'}}, open({str(meta.gate_path)!r}, 'w'))"
    proc = run(["/usr/bin/python3", "-c", forged], cwd=ws, env={"PATH": os.environ["PATH"], "HOME": str(tmp_path / "home")}, jail=ws)
    assert proc.returncode != 0 and not meta.gate_path.exists()


def test_legacy_workspace_is_adopted_without_its_gate(git_repo, tmp_path):
    meta = prepare("issue:o/r#8", "o/r", 8, "main", tmp_path / "workspaces", clone_url=str(git_repo))
    ws = Path(meta.path)
    legacy = ws / ".pr-agent"
    legacy.mkdir(exist_ok=True)
    meta.meta_path.rename(legacy / "meta.json")
    (legacy / "gate.json").write_text('{"verdict": "pass"}')
    again = Meta.load(ws)
    assert again.meta_path.exists() and not again.gate_path.exists()


def test_isolation_can_be_switched_off(monkeypatch, tmp_path):
    monkeypatch.setenv("PR_AGENT_TEST_ISOLATION", "off")
    assert jail.preexec(tmp_path) is None


def test_missing_landlock_refuses_to_run(monkeypatch, tmp_path):
    monkeypatch.setattr(jail, "abi", lambda: 0)
    with pytest.raises(jail.IsolationUnavailable):
        jail.preexec(tmp_path)


def test_toolchain_roots_never_expose_home(monkeypatch, tmp_path):
    home = tmp_path / "home"
    (home / "bin").mkdir(parents=True)
    tool = home / "bin" / "node"
    tool.write_text("#!/bin/sh\n")
    tool.chmod(0o755)
    monkeypatch.setenv("PATH", f"{home / 'bin'}:/usr/bin")
    assert str(home) not in jail._toolchain_roots(home)
