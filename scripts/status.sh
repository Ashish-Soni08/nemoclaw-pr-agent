#!/usr/bin/env bash
# What is the agent doing? Cron state, the last ledger rows, spend.
source "$(dirname "$0")/_lib.sh"
nemohermes "$SANDBOX" status
nemohermes "$SANDBOX" exec -- hermes cron list
nemohermes "$SANDBOX" exec -- "$SANDBOX_REPO/bin/pr-agent" ledger show --tail "${1:-25}"
nemohermes "$SANDBOX" exec -- "$SANDBOX_REPO/bin/pr-agent" guard
