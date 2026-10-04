#!/usr/bin/env bash
# Shared settings for the host-side scripts. Source it; don't run it.
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SANDBOX="${PR_AGENT_SANDBOX:-pr-agent}"
export PATH="$HOME/.local/bin:$PATH"   # nemohermes lives here; cron has a bare PATH
MAIN_MODEL="${PR_AGENT_MAIN_MODEL:-zai-org/GLM-5.3}"
SANDBOX_REPO=/sandbox/nemoclaw-pr-agent

say() { printf '\n==> %s\n' "$*"; }
need() { command -v "$1" >/dev/null 2>&1 || { echo "missing: $1 ($2)" >&2; exit 1; }; }
# OpenShell injects the provider placeholders (not the keys) only into exec sessions, so the
# Hermes gateway that fires scheduled cron jobs never has them. Save them where pr-agent reads
# them (Settings.load). Run after every credential change.
save_provider_placeholders() {
  nemohermes "$SANDBOX" exec -- sh -c 'mkdir -p /sandbox/.pr-agent && umask 077 && printf "PRAGENT_GITHUB_TOKEN=%s
PRAGENT_FIRECRAWL_KEY=%s
" "$PRAGENT_GITHUB_TOKEN" "$PRAGENT_FIRECRAWL_KEY" > /sandbox/.pr-agent/provider-env'
}
need_env() { [[ -n "${!1:-}" ]] || { echo "export $1 in this shell first ($2). Never write it into the repo." >&2; exit 1; }; }
