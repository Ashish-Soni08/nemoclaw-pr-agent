#!/usr/bin/env bash
# Host-side, every 30 minutes from crontab: copy the ledger out of the sandbox and mirror it
# to the Hugging Face bucket the UI reads. The sandbox never holds an HF write token.
# crontab: */30 * * * * cd /home/ubuntu/nemoclaw-pr-agent && HF_TOKEN=... LEDGER_BUCKET=... scripts/sync-ledger.sh >> ~/pr-agent-sync.log 2>&1
source "$(dirname "$0")/_lib.sh"
need_env HF_TOKEN "token with write access to the ledger bucket"
need_env LEDGER_BUCKET "e.g. your-hf-name/pr-agent-ledger"
MIRROR="${PR_AGENT_MIRROR:-$HOME/.pr-agent-mirror}"
mkdir -p "$MIRROR"
nemohermes "$SANDBOX" download /sandbox/.pr-agent/ledger "$MIRROR/"
python3 -m pip install --quiet --user "huggingface_hub>=1.0" pyyaml
PR_AGENT_HOME="$MIRROR" "$REPO_DIR/bin/pr-agent" ledger sync
