#!/usr/bin/env bash
# Step 3 (and after every change or rebuild): copy the agent into the sandbox, install its
# skills and SOUL.md, apply the Hermes settings, register the cron jobs, restart the gateway.
# Idempotent.
source "$(dirname "$0")/_lib.sh"
need nemohermes "run scripts/install.sh first"

say "Uploading the repo to $SANDBOX_REPO"
# Only what git would commit (tracked plus untracked-but-not-ignored files) and .git, for
# the commit id in run_config. Ignored files such as a local .env with real keys stay out:
# other people's test code runs in the sandbox and could read them.
stage="$(mktemp -d)"
trap 'rm -rf "$stage"' EXIT
mkdir "$stage/$(basename "$SANDBOX_REPO")"
{ git -C "$REPO_DIR" ls-files -z -co --exclude-standard; printf '.git\0'; } \
  | tar -C "$REPO_DIR" --null -T - -cf - | tar -C "$stage/$(basename "$SANDBOX_REPO")" -xf -
nemohermes "$SANDBOX" exec -- rm -rf "$SANDBOX_REPO"
nemohermes "$SANDBOX" upload "$stage/$(basename "$SANDBOX_REPO")" /sandbox/
nemohermes "$SANDBOX" exec -- bash -c "test -x $SANDBOX_REPO/bin/pr-agent && mkdir -p /sandbox/.local/bin && ln -sf $SANDBOX_REPO/bin/pr-agent /sandbox/.local/bin/pr-agent"

say "Private interpreter for pr-agent (the only binary the GitHub and Firecrawl keys are injected for)"
nemohermes "$SANDBOX" exec -- bash -c 'mkdir -p /sandbox/.pr-agent/bin && cp -f "$(readlink -f "$(command -v python3)")" /sandbox/.pr-agent/bin/python && PYTHONPATH="$(python3 -c "import sys; print(\":\".join(p for p in sys.path[1:] if p))")" /sandbox/.pr-agent/bin/python -c "import ssl, yaml; print(\"interpreter ok\")"'

say "Provider placeholders for scheduled runs"
save_provider_placeholders

say "Installing skills"
for dir in "$REPO_DIR"/skills/*/; do
  name="$(basename "$dir")"
  # skill install refuses to replace a skill a previous deploy installed, so drop ours first.
  nemohermes "$SANDBOX" exec -- rm -rf "/sandbox/.hermes/skills/$name"
  # The old copy is already gone, so a failed install must fail the deploy, not pass silently.
  nemohermes "$SANDBOX" skill install "$dir"
done
nemohermes "$SANDBOX" skill list

say "SOUL.md, Hermes settings, cron jobs"
nemohermes "$SANDBOX" exec -- cp "$SANDBOX_REPO/hermes/SOUL.md" /sandbox/.hermes/SOUL.md
nemohermes "$SANDBOX" exec -- bash "$SANDBOX_REPO/hermes/apply-config.sh"
# Summaries go to Telegram only once the channel is set up (install.sh with TELEGRAM_BOT_TOKEN);
# a job whose delivery target isn't connected refuses to run, so the default is local.
nemohermes "$SANDBOX" exec -- env PR_AGENT_DELIVER="${PR_AGENT_DELIVER:-local}" bash "$SANDBOX_REPO/hermes/register-jobs.sh"
# The restart's health check can give up before Telegram finishes connecting (~10 s);
# the gateway still comes up, so fall back to a status check instead of failing the deploy.
nemohermes "$SANDBOX" gateway restart || { sleep 15; nemohermes "$SANDBOX" status; }

say "Smoke test inside the sandbox"
nemohermes "$SANDBOX" exec -- "$SANDBOX_REPO/bin/pr-agent" guard
nemohermes "$SANDBOX" exec -- "$SANDBOX_REPO/bin/pr-agent" policy huggingface/transformers
say "Deployed. Trigger a run now with: scripts/run-now.sh"
