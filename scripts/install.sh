#!/usr/bin/env bash
# Step 1 on a fresh Lambda VM: install NemoClaw with the Hermes agent, inference through
# the Hugging Face router, and the sandbox egress the agent needs.
# Usage: HF_TOKEN=... [TELEGRAM_BOT_TOKEN=... TELEGRAM_ALLOWED_IDS=...] scripts/install.sh
source "$(dirname "$0")/_lib.sh"
need_env HF_TOKEN "Hugging Face token with Inference Providers permission"
need docker "install Docker first; see docs/runbook-lambda.md"

# Onboarding settings (non-interactive): an OpenAI-compatible endpoint = the HF router.
export NEMOCLAW_AGENT=hermes
export NEMOCLAW_SANDBOX_NAME="$SANDBOX"
export NEMOCLAW_NON_INTERACTIVE=1
export NEMOCLAW_ACCEPT_THIRD_PARTY_SOFTWARE=1
export NEMOCLAW_PROVIDER=custom
export NEMOCLAW_ENDPOINT_URL=https://router.huggingface.co/v1
export NEMOCLAW_MODEL="$MAIN_MODEL"
export NEMOCLAW_CONTEXT_WINDOW="${NEMOCLAW_CONTEXT_WINDOW:-131072}"
export NEMOCLAW_WEB_SEARCH_PROVIDER=none
export COMPATIBLE_API_KEY="$HF_TOKEN"

if ! command -v nemohermes >/dev/null 2>&1; then
  say "Installing NemoClaw (Hermes agent)"
  curl -fsSL https://www.nvidia.com/nemoclaw.sh | bash
  export PATH="$HOME/.local/bin:$PATH"
fi

if ! nemohermes "$SANDBOX" status >/dev/null 2>&1; then
  say "Onboarding sandbox $SANDBOX with $MAIN_MODEL via router.huggingface.co"
  nemohermes onboard --non-interactive
fi
unset COMPATIBLE_API_KEY

say "Egress: PyPI (target repos' test deps) and read-only git clone"
nemohermes "$SANDBOX" policy add pypi --yes || echo "(policy already applied)"
nemohermes "$SANDBOX" policy add --from-file "$REPO_DIR/policies/presets/pr-agent-git.yaml" --yes || echo "(policy already applied)"
nemohermes "$SANDBOX" policy add --from-file "$REPO_DIR/policies/presets/pr-agent-api.yaml" --yes || echo "(policy already applied)"

if [[ -n "${TELEGRAM_BOT_TOKEN:-}" ]]; then
  need_env TELEGRAM_ALLOWED_IDS "your numeric Telegram user id, from @userinfobot"
  say "Telegram channel for run summaries"
  nemohermes "$SANDBOX" channels add telegram
  nemohermes "$SANDBOX" rebuild --yes
else
  echo "TELEGRAM_BOT_TOKEN not set: skipping Telegram. Re-run with it set to get run summaries."
fi

nemohermes "$SANDBOX" status
say "Next: scripts/setup-credentials.sh, then scripts/deploy.sh"
