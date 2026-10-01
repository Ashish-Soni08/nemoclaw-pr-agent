#!/usr/bin/env bash
# Register the agent's cron jobs. Run inside the sandbox (scripts/deploy.sh does it).
# Idempotent: jobs are looked up by name in $HERMES_HOME/cron/jobs.json and edited in place.
set -euo pipefail

HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
REPO="${PR_AGENT_REPO:-/sandbox/nemoclaw-pr-agent}"
DELIVER="${PR_AGENT_DELIVER:-telegram}"
RUN_SCHEDULE="${PR_AGENT_RUN_SCHEDULE:-0 */4 * * *}"
FOLLOW_SCHEDULE="${PR_AGENT_FOLLOW_SCHEDULE:-30 */2 * * *}"
DIGEST_SCHEDULE="${PR_AGENT_DIGEST_SCHEDULE:-0 19 * * *}"

mkdir -p "$HERMES_HOME/scripts"
cp "$REPO"/hermes/scripts/*.py "$HERMES_HOME/scripts/"

job_id() {
  python3 - "$HERMES_HOME/cron/jobs.json" "$1" <<'PY'
import json, sys
try:
    jobs = json.load(open(sys.argv[1])).get("jobs", [])
except (OSError, ValueError):
    jobs = []
print(next((j["id"] for j in jobs if j.get("name") == sys.argv[2]), ""))
PY
}

upsert() {  # name schedule prompt script [extra flags...]
  local name="$1" schedule="$2" prompt="$3" script="$4"
  shift 4
  local existing
  existing="$(job_id "$name")"
  if [[ -n "$existing" ]]; then
    hermes cron edit "$existing" --schedule "$schedule" --prompt "$prompt" --name "$name" --deliver "$DELIVER" --script "$script" "$@"
    echo "updated $name ($existing)"
  else
    hermes cron create "$schedule" "$prompt" --name "$name" --deliver "$DELIVER" --script "$script" "$@"
    echo "created $name"
  fi
}

RUN_PROMPT="Autonomous PR agent run. The script output above has this run's id, the candidates that passed discovery and the AI-policy check, and any follow-up items. Load pr-agent-mode and follow the Autonomous run playbook: triage every candidate, claim or fix the ones you take (at most limits.max_fixes_per_run), run the self-review gate, open PRs only on a pass, and log every decision with pr-agent log. Your final response is delivered to Telegram: it must be the output of 'pr-agent summary run', plus at most two lines for a human."
FOLLOW_PROMPT="PR agent follow-up. The script output above lists new review comments on your PRs and maintainer replies to your claims. Load pr-agent-mode and the follow-up skill and handle every item. Your final response is delivered to Telegram: it must be the output of 'pr-agent summary run', plus at most two lines for a human."

upsert "pr-agent-run" "$RUN_SCHEDULE" "$RUN_PROMPT" "pr_agent_prestep_run.py" --skill pr-agent-mode
upsert "pr-agent-follow-up" "$FOLLOW_SCHEDULE" "$FOLLOW_PROMPT" "pr_agent_prestep_follow_up.py" --skill pr-agent-mode --skill follow-up

if [[ -z "$(job_id pr-agent-daily-digest)" ]]; then
  hermes cron create "$DIGEST_SCHEDULE" --no-agent --script pr_agent_daily_digest.py --name pr-agent-daily-digest --deliver "$DELIVER"
  echo "created pr-agent-daily-digest"
fi
hermes cron list
