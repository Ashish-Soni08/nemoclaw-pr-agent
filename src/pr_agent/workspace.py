"""Per-issue working copy: clone, detect the test command, run the baseline, read the diff.

Repository content is untrusted. Everything here runs inside the OpenShell
sandbox, with a time limit, and never with a credential in the environment.
"""

from __future__ import annotations

import hashlib
import json
import os
import shlex
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .state import read_json, write_json

SAFE_ENV_KEYS = {
    "PATH", "HOME", "LANG", "LC_ALL", "TERM", "TMPDIR", "PIP_INDEX_URL", "PIP_CACHE_DIR",
    "HTTPS_PROXY", "HTTP_PROXY", "NO_PROXY", "SSL_CERT_FILE", "REQUESTS_CA_BUNDLE",
    "NODE_EXTRA_CA_CERTS",
}
# Untracked build output that must never end up in a PR.
EXCLUDES = (".pr-agent/", ".venv-pr-agent/", "node_modules/")


def scrubbed_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    """Repo code (tests, setup.py, install scripts) gets no tokens, keys or placeholders."""
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
    ecosystem: str = "python"

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
        fh.write("\n" + "\n".join(EXCLUDES) + "\n")
    eco = detect_ecosystem(ws)
    meta = Meta(issue_id, repo, number, str(ws), base_branch, sha, branch, test_cmd=detect_test_cmd(ws, eco), ecosystem=eco)
    meta.save()
    return meta


def detect_ecosystem(ws: Path) -> str:
    """python or node, from the files at the repo root. Python wins in mixed repos (docs tooling)."""
    files = {p.name for p in ws.iterdir()}
    if files & {"pyproject.toml", "setup.py", "setup.cfg"}:
        return "python"
    if "package.json" in files:
        return "node"
    return "python"


def _package_json(ws: Path) -> dict[str, Any]:
    try:
        return json.loads((ws / "package.json").read_text())
    except (OSError, ValueError):
        return {}


def node_pm(ws: Path) -> str:
    """The package manager the repo uses: its packageManager field, else its lockfile, else npm."""
    declared = str(_package_json(ws).get("packageManager", "")).split("@", 1)[0]
    if declared in ("npm", "pnpm", "bun", "yarn"):
        return declared
    for lock, pm in (("pnpm-lock.yaml", "pnpm"), ("bun.lock", "bun"), ("bun.lockb", "bun"), ("yarn.lock", "yarn")):
        if (ws / lock).exists():
            return pm
    return "npm"


# How to invoke each package manager. The sandbox image ships node, npm, npx and yarn (classic);
# pnpm and bun come from the npm registry through npx, so no extra download hosts are needed.
PM_CMD = {"npm": "npm", "pnpm": "npx --yes pnpm", "bun": "npx --yes bun", "yarn": "yarn"}
NPM_DEFAULT_TEST = "no test specified"


def pm_command(ws: Path, pm: str) -> str:
    """How to invoke `pm` in this repo. Yarn 2+ (berry, pinned in packageManager) runs through corepack."""
    if pm == "yarn" and not str(_package_json(ws).get("packageManager", "yarn@1")).startswith("yarn@1"):
        return "corepack yarn"
    return PM_CMD[pm]


def detect_test_cmd(ws: Path, ecosystem: str = "python") -> str:
    """Best guess at the repo's own test command. The model may override it with evidence."""
    if ecosystem == "node":
        pm = node_pm(ws)
        test = str(_package_json(ws).get("scripts", {}).get("test", ""))
        if test and NPM_DEFAULT_TEST not in test:
            return f"{pm_command(ws, pm)} run test" if pm != "npm" else "npm test"
        return "npx --yes bun test" if pm == "bun" else ""
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


def setup_env(ws: Path, timeout: int = 1200, ecosystem: str = "") -> dict[str, Any]:
    """Install the repo's dependencies with its own toolchain, so its tests can run."""
    eco = ecosystem or detect_ecosystem(ws)
    if eco == "node":
        return _setup_node(ws, timeout)
    return _setup_python(ws, timeout)


def _setup_python(ws: Path, timeout: int) -> dict[str, Any]:
    """Venv plus an editable install with whatever test extras exist."""
    started = time.monotonic()
    venv = ws / ".venv-pr-agent"
    proc = run(["python3", "-m", "venv", str(venv)], cwd=ws, timeout=300)
    if proc.returncode != 0:
        return {"ecosystem": "python", "installed": False, "error": proc.stderr[-300:], "seconds": round(time.monotonic() - started, 1)}
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
    return {"ecosystem": "python", "installed": installed, "seconds": round(time.monotonic() - started, 1)}


def ensure_node() -> str:
    """Path to node. The NemoClaw sandbox image ships Node with npm, npx, yarn and corepack."""
    found = shutil.which("node", path=scrubbed_env().get("PATH"))
    if not found:
        raise RuntimeError("no node in the sandbox")
    return found


def _setup_node(ws: Path, timeout: int) -> dict[str, Any]:
    started = time.monotonic()
    out: dict[str, Any] = {"ecosystem": "node", "installed": False}
    try:
        out["node"] = ensure_node()
    except RuntimeError as err:
        return out | {"error": str(err), "seconds": round(time.monotonic() - started, 1)}
    pm = out["pm"] = node_pm(ws)
    base = shlex.split(pm_command(ws, pm))
    if pm == "npm":
        attempts = [["npm", "ci"], ["npm", "install"]] if (ws / "package-lock.json").exists() else [["npm", "install"]]
    else:
        attempts = [base + ["install", "--frozen-lockfile"], base + ["install"]]
    for cmd in attempts:
        proc = run(cmd, cwd=ws, timeout=timeout)
        if proc.returncode == 0:
            out["installed"] = True
            break
        out["error"] = proc.stderr[-300:]
    if out["installed"]:
        out.pop("error", None)
    return out | {"seconds": round(time.monotonic() - started, 1)}


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


class UnsafeChange(RuntimeError):
    """The working tree holds something the agent must never publish."""


class Blob(bytes):
    """File content headed for a PR, with the git mode it was staged with (100644 or 100755)."""

    mode: str = "100644"

    def __new__(cls, data: bytes, mode: str = "100644") -> "Blob":
        obj = super().__new__(cls, data)
        obj.mode = mode
        return obj


# Repo code can write .git/config and ~/.gitconfig. These keep the agent's own git calls
# from running its hooks or fsmonitor, and from reading its diff drivers or textconv
# filters, so the diff the gate sees is the diff that gets pushed.
GIT = ["git", "-c", "core.fsmonitor=false", "-c", "core.hooksPath=/dev/null", "-c", "core.quotePath=false"]


def git(args: list[str], ws: Path, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    env = scrubbed_env({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null"})
    return run(GIT + args, cwd=ws, timeout=timeout, env=env)


def stage_tree(ws: Path) -> str:
    """Stage everything (untracked files too, minus agent dirs) and return the tree id."""
    git(["add", "-A", "--", ".", ":!.pr-agent", ":!.venv-pr-agent"], ws)
    proc = git(["write-tree"], ws)
    if proc.returncode != 0:
        raise RuntimeError(f"git write-tree failed: {proc.stderr[-300:]}")
    return proc.stdout.strip()


def changed_files(ws: Path, base_sha: str, tree: str | None = None) -> dict[str, Blob | None]:
    """Tree vs base: path -> new bytes, or None for a deletion. Untracked files count.

    Content comes from git's own blobs in that exact tree, never by opening the path, so a
    symlink planted by repo code (say, to a secrets file) can't smuggle another file's bytes
    into a PR, and an edit made after the tree was staged can't either. Symlinks and
    submodules are refused outright.
    """
    tree = tree or stage_tree(ws)
    proc = git(["diff-tree", "-r", "-z", "--raw", "--no-renames", "--no-abbrev", base_sha, tree], ws)
    if proc.returncode != 0:
        raise RuntimeError(f"git diff-tree failed: {proc.stderr[-300:]}")
    fields = proc.stdout.split("\0")
    changes: dict[str, Blob | None] = {}
    for info, path in zip(fields[0::2], fields[1::2]):
        if not path:
            continue
        _old_mode, new_mode, _old_sha, new_sha, status = info.lstrip(":").split()
        if status.startswith("D"):
            changes[path] = None
            continue
        if new_mode in ("120000", "160000"):
            raise UnsafeChange(f"{path} is a {'symlink' if new_mode == '120000' else 'submodule'}; the agent never publishes those")
        blob = subprocess.run(GIT + ["cat-file", "blob", new_sha], cwd=ws, env=scrubbed_env({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null"}), capture_output=True, check=True, timeout=60)
        changes[path] = Blob(blob.stdout, "100755" if new_mode == "100755" else "100644")
    return changes


def diff_lines(ws: Path, base_sha: str, tree: str | None = None) -> int:
    """Added plus deleted lines, renames counted in full. Binary files are refused."""
    tree = tree or stage_tree(ws)
    proc = git(["diff-tree", "-r", "-z", "--numstat", "--no-renames", "--no-ext-diff", "--no-textconv", base_sha, tree], ws)
    total = 0
    for rec in proc.stdout.split("\0"):
        if not rec.strip():
            continue
        added, deleted, path = rec.split("\t", 2)
        if added == "-" or deleted == "-":
            raise UnsafeChange(f"{path} is a binary file; the agent only publishes text changes")
        total += int(added) + int(deleted)
    return total


def diff_text(ws: Path, base_sha: str, tree: str | None = None) -> str:
    """The patch the self-review gate reads, built from the same tree that gets pushed."""
    tree = tree or stage_tree(ws)
    return git(["diff-tree", "-r", "-p", "--no-renames", "--no-ext-diff", "--no-textconv", base_sha, tree], ws).stdout


def diff_hash(ws: Path, base_sha: str, tree: str | None = None) -> str:
    """Binds a gate verdict to one exact change: the base commit plus the staged tree id."""
    tree = tree or stage_tree(ws)
    return hashlib.sha256(f"{base_sha}:{tree}".encode()).hexdigest()[:16]
