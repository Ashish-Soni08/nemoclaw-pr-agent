"""Run one script on the base commit and on the working tree; save both outputs; print a Markdown snippet."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

SAFE = {"PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "MPLBACKEND"}

# The repo's script is untrusted, so it runs in pr-agent's jail (src/pr_agent/jail.py).
sys.path.insert(0, os.path.join(os.environ.get("PR_AGENT_REPO", "/sandbox/nemoclaw-pr-agent"), "src"))
from pr_agent import jail  # noqa: E402


def meta_of(ws: Path) -> dict:
    for path in (ws.parent / ".control" / ws.name / "meta.json", ws / ".pr-agent" / "meta.json"):
        if path.exists():
            return json.loads(path.read_text())
    raise SystemExit(f"{ws} is not a prepared workspace")


MAX_OUTPUT = 20 * 1024 * 1024


def safe_write(dest: Path, data: bytes) -> None:
    """Write a fresh regular file; never through a link someone left at that path."""
    dest.unlink(missing_ok=True)
    fd = os.open(dest, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644)
    with os.fdopen(fd, "wb") as fh:
        fh.write(data)


def copy_out(src: Path, dest: Path) -> bool:
    """Copy what the jailed script wrote, if it is a plain file. The script controls `src`,
    so a symlink there (to gate.json, a secrets file) must not be followed."""
    try:
        # O_NONBLOCK: a FIFO planted at `src` must not hang the open; it is then refused below.
        fd = os.open(src, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError:
        return False
    with os.fdopen(fd, "rb") as fh:
        if not stat.S_ISREG(os.fstat(fh.fileno()).st_mode):
            return False
        data = fh.read(MAX_OUTPUT + 1)
    if len(data) > MAX_OUTPUT:
        return False
    safe_write(dest, data)
    return True


def run_side(cwd: Path, script: Path, out: Path, python: str, ws: Path, writable: list[Path]) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k in SAFE}
    # Put this side's source first on the path, so the editable install of the fix doesn't leak into "before".
    paths = [str(cwd / "src")] if (cwd / "src").is_dir() else []
    env.update({"OUT": str(out), "MPLBACKEND": "Agg", "PYTHONPATH": os.pathsep.join(paths + [str(cwd)])})
    return subprocess.run([python, str(script)], cwd=cwd, env=env, capture_output=True, text=True, timeout=600, preexec_fn=jail.preexec(ws, writable))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("workspace")
    ap.add_argument("--script", required=True, help="path relative to the workspace")
    ap.add_argument("--kind", choices=["png", "txt", "html"], default="txt")
    a = ap.parse_args()

    ws = Path(a.workspace).resolve()
    meta = meta_of(ws)
    home = Path(os.environ.get("PR_AGENT_HOME", Path.home() / ".pr-agent"))
    slug = Path(meta["path"]).name
    media = home / "ledger" / "media" / slug
    media.mkdir(parents=True, exist_ok=True)
    venv_py = ws / ".venv-pr-agent" / "bin" / "python"
    python = str(venv_py) if venv_py.exists() else sys.executable
    script = ws / a.script

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp) / "base"
        subprocess.run(["git", "worktree", "add", "--detach", str(base), meta["base_sha"]], cwd=ws, check=True, capture_output=True)
        try:
            results = {}
            for side, cwd in (("before", base), ("after", ws)):
                # The script writes into a scratch dir of its own; only plain files are copied
                # into the ledger's media folder, which the jail can't write.
                scratch = Path(tmp) / f"out-{side}"
                scratch.mkdir()
                out = media / f"{side}.{a.kind}"
                proc = run_side(cwd, script, scratch / out.name, python, ws, [base, scratch])
                saved = copy_out(scratch / out.name, out)
                if a.kind == "txt" and not saved:
                    safe_write(out, (proc.stdout + proc.stderr).encode()[-MAX_OUTPUT:])
                    saved = True
                results[side] = {"exit": proc.returncode, "file": str(out), "exists": saved}
        finally:
            subprocess.run(["git", "worktree", "remove", "--force", str(base)], cwd=ws, capture_output=True)
            shutil.rmtree(base, ignore_errors=True)

    public = os.environ.get("PR_AGENT_LEDGER_PUBLIC_URL", "")
    if not public:
        try:
            from pr_agent.config import Settings

            public = Settings.load().agent.get("ledger", {}).get("public_url", "")
        except Exception:  # noqa: BLE001 - optional; the snippet falls back to words
            public = ""
    public = public.rstrip("/")
    lines = ["### Before and after", ""]
    if a.kind == "txt":
        for side in ("before", "after"):
            text = Path(results[side]["file"]).read_text()[-1500:]
            lines += [f"**{side.title()}** (`{a.script}`):", "```", text.rstrip(), "```", ""]
    elif public:
        for side in ("before", "after"):
            lines.append(f"**{side.title()}:** ![{side}]({public}/media/{slug}/{side}.{a.kind})")
    else:
        lines.append(f"Captured to the ledger: media/{slug}/before.{a.kind}, after.{a.kind} (no public URL configured; describe the difference in words).")
    print(json.dumps(results, indent=2))
    print("\n".join(lines))
    return 0 if all(r["exists"] for r in results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
