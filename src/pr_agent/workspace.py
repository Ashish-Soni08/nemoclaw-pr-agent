"""Per-issue working copy: clone, detect the test command, run the baseline, read the diff.

Repository content is untrusted. Everything here runs inside the OpenShell
sandbox, with a time limit, and never with a credential in the environment.
"""

from __future__ import annotations

import hashlib
import os
import shlex
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .state import read_json, write_json

SAFE_ENV_KEYS = {"PATH", "HOME", "LANG", "LC_ALL", "TERM", "TMPDIR", "PIP_INDEX_URL", "PIP_CACHE_DIR", "HTTPS_PROXY", "HTTP_PROXY", "NO_PROXY", "SSL_CERT_FILE", "REQUESTS_CA_BUNDLE"}


def scrubbed_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    """Repo code (tests, setup.py) gets no tokens, keys or placeholders."""
    env = {k: v for k, v in os.environ.items() if k in SAFE_ENV_KEYS}
    env.update(extra or {})
    return env


def slug(issue_id: str) -> str:
    # issue:owner/repo#12 -> owner__repo__12
    body = issue_id.split(":", 1)[-1]
    repo, _, num = body.partition("#")
    return f"{repo.replace('/', '__')}__{num}"


@dataclass
class Meta:
    issue_id: str
    repo: str
    number: int
    path: str
    base_branch: str
    base_sha: str
    branch: str
    test_cmd: str = ""
    baseline: dict[str, Any] | None = None

    @property
    def meta_path(self) -> Path:
        return Path(self.path) / ".pr-agent" / "meta.json"

    def save(self) -> None:
        write_json(self.meta_path, asdict(self))

    @classmethod
    def load(cls, ws: Path) -> "Meta":
        data = read_json(ws / ".pr-agent" / "meta.json", None)
        if data is None:
            raise SystemExit(f"{ws} is not a prepared workspace (no .pr-agent/meta.json)")
        return cls(**data)


def run(cmd: list[str] | str, cwd: Path, timeout: int = 900, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd, cwd=cwd, timeout=timeout, env=env if env is not None else scrubbed_env(), shell=isinstance(cmd, str),
        capture_output=True, text=True, check=False,
    )


def prepare(issue_id: str, repo: str, number: int, base_branch: str, root: Path, clone_url: str | None = None) -> Meta:
    ws = root / slug(issue_id)
    if (ws / ".pr-agent" / "meta.json").exists():
        return Meta.load(ws)
    url = clone_url or f"https://github.com/{repo}.git"
    ws.parent.mkdir(parents=True, exist_ok=True)
    proc = run(["git", "clone", "--depth", "50", "--branch", base_branch, url, str(ws)], cwd=root, timeout=600, env=scrubbed_env({"GIT_TERMINAL_PROMPT": "0"}))
    if proc.returncode != 0:
        raise RuntimeError(f"git clone failed: {proc.stderr[-500:]}")
    sha = run(["git", "rev-parse", "HEAD"], cwd=ws).stdout.strip()
    branch = f"pr-agent/issue-{number}"
    run(["git", "checkout", "-b", branch], cwd=ws)
    run(["git", "config", "user.name", "nemoclaw-pr-agent"], cwd=ws)
    run(["git", "config", "user.email", "pr-agent@users.noreply.github.com"], cwd=ws)
    exclude = ws / ".git" / "info" / "exclude"
    exclude.parent.mkdir(parents=True, exist_ok=True)
    with exclude.open("a") as fh:
        fh.write("\n.pr-agent/\n.venv-pr-agent/\n")
    meta = Meta(issue_id, repo, number, str(ws), base_branch, sha, branch, test_cmd=detect_test_cmd(ws))
    meta.save()
    return meta


def detect_test_cmd(ws: Path) -> str:
    """Best guess at the repo's own test command. The model may override it with evidence."""
    py = ".venv-pr-agent/bin/python"
    files = {p.name for p in ws.iterdir()}
    if "noxfile.py" in files and "tox.ini" not in files and not (ws / "tests").exists():
        return "nox -s tests"
    if (ws / "tests").exists() or (ws / "test").exists() or "pytest.ini" in files or "conftest.py" in files:
        return f"{py} -m pytest -x -q"
    for cfg in ("pyproject.toml", "setup.cfg", "tox.ini"):
        if cfg in files and "pytest" in (ws / cfg).read_text(errors="ignore"):
            return f"{py} -m pytest -x -q"
    return ""


def setup_env(ws: Path, timeout: int = 1200) -> dict[str, Any]:
    """Venv plus an editable install with whatever test extras exist."""
    started = time.monotonic()
    venv = ws / ".venv-pr-agent"
    proc = run(["python3", "-m", "venv", str(venv)], cwd=ws, timeout=300)
    if proc.returncode != 0:
        return {"installed": False, "error": proc.stderr[-300:], "seconds": round(time.monotonic() - started, 1)}
    pip = [str(venv / "bin" / "python"), "-m", "pip", "install", "-q"]
    run(pip + ["--upgrade", "pip"], cwd=ws, timeout=timeout)
    installed = False
    for extras in ("[test,tests,dev]", "[test]", "[tests]", "[dev]", ""):
        proc = run(pip + ["-e", f".{extras}"], cwd=ws, timeout=timeout)
        if proc.returncode == 0:
            installed = True
            break
    for req in ("requirements-dev.txt", "requirements-test.txt", "test-requirements.txt", "requirements/test.txt"):
        if (ws / req).exists():
            run(pip + ["-r", req], cwd=ws, timeout=timeout)
    run(pip + ["pytest"], cwd=ws, timeout=timeout)
    return {"installed": installed, "seconds": round(time.monotonic() - started, 1)}


def run_tests(ws: Path, cmd: str, timeout: int = 1800) -> dict[str, Any]:
    started = time.monotonic()
    try:
        proc = run(shlex.split(cmd), cwd=ws, timeout=timeout)
        code, out = proc.returncode, (proc.stdout + proc.stderr)
    except subprocess.TimeoutExpired:
        code, out = -1, f"timed out after {timeout}s"
    tail = "\n".join(out.strip().splitlines()[-15:])
    log = ws / ".pr-agent" / f"tests-{int(time.time())}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(out)
    return {"cmd": cmd, "exit": code, "passed": code == 0, "tail": tail, "log": str(log), "seconds": round(time.monotonic() - started, 1)}


def changed_files(ws: Path, base_sha: str) -> dict[str, bytes | None]:
    """Working tree vs base: path -> new bytes, or None for a deletion. Untracked files count."""
    run(["git", "add", "-A", "--", ".", ":!.pr-agent", ":!.venv-pr-agent"], cwd=ws)
    proc = run(["git", "diff", "--cached", "--name-status", "--no-renames", base_sha], cwd=ws)
    changes: dict[str, bytes | None] = {}
    for line in proc.stdout.splitlines():
        status, _, path = line.partition("\t")
        if not path:
            continue
        changes[path] = None if status.startswith("D") else (ws / path).read_bytes()
    return changes


def diff_text(ws: Path, base_sha: str) -> str:
    run(["git", "add", "-A", "--", ".", ":!.pr-agent", ":!.venv-pr-agent"], cwd=ws)
    return run(["git", "diff", "--cached", base_sha], cwd=ws).stdout


def diff_hash(ws: Path, base_sha: str) -> str:
    return hashlib.sha256(diff_text(ws, base_sha).encode()).hexdigest()[:16]
