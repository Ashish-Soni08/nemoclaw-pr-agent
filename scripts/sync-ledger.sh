#!/usr/bin/env bash
# Host-side, every 30 minutes from crontab: copy the ledger out of the sandbox and mirror it
# to the Hugging Face dataset the UI reads. The sandbox never holds an HF write token.
# crontab: */30 * * * * cd /home/ubuntu/nemoclaw-pr-agent && scripts/sync-ledger.sh >> ~/pr-agent-sync.log 2>&1
# HF_TOKEN and LEDGER_DATASET come from the environment or from ~/.pr-agent-sync.env (mode 600).
source "$(dirname "$0")/_lib.sh"
SYNC_ENV="${PR_AGENT_SYNC_ENV:-$HOME/.pr-agent-sync.env}"
if [[ -f "$SYNC_ENV" ]]; then set -a; source "$SYNC_ENV"; set +a; fi
need_env HF_TOKEN "token with write access to the ledger dataset"
need_env LEDGER_DATASET "e.g. your-hf-name/pr-agent-ledger"
MIRROR="${PR_AGENT_MIRROR:-$HOME/.pr-agent-mirror}"
mkdir -p "$MIRROR"
nemohermes "$SANDBOX" download /sandbox/.pr-agent/ledger "$MIRROR/ledger/"
# VM resource samples (scripts/host-sample.py, every minute) live host-side; ship them with the ledger.
[[ -f "$MIRROR/host.tsv" ]] && cp "$MIRROR/host.tsv" "$MIRROR/ledger/host.tsv"
# Ubuntu 24.04 blocks pip into the system Python (PEP 668), so use a venv next to the mirror.
[[ -x "$MIRROR/.venv/bin/python" ]] || python3 -m venv "$MIRROR/.venv"
"$MIRROR/.venv/bin/pip" install --quiet "huggingface_hub>=1.0" pyyaml
export PATH="$MIRROR/.venv/bin:$PATH"
PR_AGENT_HOME="$MIRROR" "$REPO_DIR/bin/pr-agent" ledger sync
