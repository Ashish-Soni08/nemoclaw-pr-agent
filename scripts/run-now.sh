#!/usr/bin/env bash
# Trigger the main cron job once, now (for the demo or a first test).
source "$(dirname "$0")/_lib.sh"
JOB="${1:-pr-agent-run}"
id="$(nemohermes "$SANDBOX" exec -- python3 -c "import json;print(next(j['id'] for j in json.load(open('/sandbox/.hermes/cron/jobs.json'))['jobs'] if j.get('name')=='$JOB'))")"
nemohermes "$SANDBOX" exec -- hermes cron run "$id"
echo "Triggered $JOB ($id). Follow it with: scripts/status.sh"
