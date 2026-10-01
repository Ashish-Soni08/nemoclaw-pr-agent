#!/usr/bin/env bash
# Step 3 (and after every change or rebuild): copy the agent into the sandbox, install its
# skills and SOUL.md, apply the Hermes settings, register the cron jobs, restart the gateway.
# Idempotent.
source "$(dirname "$0")/_lib.sh"
need nemohermes "run scripts/install.sh first"

say "Uploading the repo to $SANDBOX_REPO"
nemohermes "$SANDBOX" exec -- rm -rf "$SANDBOX_REPO"
nemohermes "$SANDBOX" upload "$REPO_DIR" /sandbox/
nemohermes "$SANDBOX" exec -- bash -c "test -x $SANDBOX_REPO/bin/pr-agent && mkdir -p /sandbox/.local/bin && ln -sf $SANDBOX_REPO/bin/pr-agent /sandbox/.local/bin/pr-agent"

say "Installing skills"
for dir in "$REPO_DIR"/skills/*/; do
  nemohermes "$SANDBOX" skill install "$dir"
done
nemohermes "$SANDBOX" skill list

say "SOUL.md, Hermes settings, cron jobs"
nemohermes "$SANDBOX" exec -- cp "$SANDBOX_REPO/hermes/SOUL.md" /sandbox/.hermes/SOUL.md
nemohermes "$SANDBOX" exec -- bash "$SANDBOX_REPO/hermes/apply-config.sh"
nemohermes "$SANDBOX" exec -- bash "$SANDBOX_REPO/hermes/register-jobs.sh"
nemohermes "$SANDBOX" gateway restart

say "Smoke test inside the sandbox"
nemohermes "$SANDBOX" exec -- "$SANDBOX_REPO/bin/pr-agent" guard
nemohermes "$SANDBOX" exec -- "$SANDBOX_REPO/bin/pr-agent" policy huggingface/transformers
say "Deployed. Trigger a run now with: scripts/run-now.sh"
