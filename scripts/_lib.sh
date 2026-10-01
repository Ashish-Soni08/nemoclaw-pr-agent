#!/usr/bin/env bash
# Shared settings for the host-side scripts. Source it; don't run it.
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SANDBOX="${PR_AGENT_SANDBOX:-pr-agent}"
export PATH="$HOME/.local/bin:$PATH"   # nemohermes lives here; cron has a bare PATH
MAIN_MODEL="${PR_AGENT_MAIN_MODEL:-nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-FP8}"
SANDBOX_REPO=/sandbox/nemoclaw-pr-agent

say() { printf '\n==> %s\n' "$*"; }
need() { command -v "$1" >/dev/null 2>&1 || { echo "missing: $1 ($2)" >&2; exit 1; }; }
need_env() { [[ -n "${!1:-}" ]] || { echo "export $1 in this shell first ($2). Never write it into the repo." >&2; exit 1; }; }
