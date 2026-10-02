"""Run one script on the base commit and on the working tree; save both outputs; print a Markdown snippet."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SAFE = {"PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "MPLBACKEND"}


def run_side(cwd: Path, script: Path, out: Path, python: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k in SAFE}
    # Put this side's source first on the path, so the editable install of the fix doesn't leak into "before".
    paths = [str(cwd / "src")] if (cwd / "src").is_dir() else []
    env.update({"OUT": str(out), "MPLBACKEND": "Agg", "PYTHONPATH": os.pathsep.join(paths + [str(cwd)])})
    return subprocess.run([python, str(script)], cwd=cwd, env=env, capture_output=True, text=True, timeout=600)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("workspace")
    ap.add_argument("--script", required=True, help="path relative to the workspace")
    ap.add_argument("--kind", choices=["png", "txt", "html"], default="txt")
    a = ap.parse_args()

    ws = Path(a.workspace).resolve()
    meta = json.loads((ws / ".pr-agent" / "meta.json").read_text())
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
                out = media / f"{side}.{a.kind}"
                proc = run_side(cwd, script, out, python)
                if a.kind == "txt" and not out.exists():
                    out.write_text(proc.stdout + proc.stderr)
                results[side] = {"exit": proc.returncode, "file": str(out), "exists": out.exists()}
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
