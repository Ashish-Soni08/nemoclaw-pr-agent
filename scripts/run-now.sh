#!/usr/bin/env bash
# Trigger the main cron job once, now (for the demo or a first test), and print each ledger
# row as the agent writes it until the run logs run.end. Ctrl+C stops watching, not the run.
source "$(dirname "$0")/_lib.sh"
JOB="${1:-pr-agent-run}"
LEDGER=/sandbox/.pr-agent/ledger/decisions.tsv
# nemohermes prints "Active gateway set" on every call; keep only the command's own output.
sx() { nemohermes "$SANDBOX" exec -- "$@" 2>&1 | grep -v 'Active gateway' || true; }

id="$(sx python3 -c "import json;print(next(j['id'] for j in json.load(open('/sandbox/.hermes/cron/jobs.json'))['jobs'] if j.get('name')=='$JOB'))" | tail -1)"
seen="$(sx bash -c "wc -l < $LEDGER 2>/dev/null || echo 0" | tail -1)"
log="$(mktemp)"

say "Starting $JOB ($id) at $(date -u +%H:%M) UTC"
echo "Discovery and policy checks take a minute or two, triage a few more. If the agent takes an issue,"
echo "the fix, the tests and the self-review gate can take 30 to 60 minutes. Each step prints below."
echo "Ctrl+C stops watching; the run keeps going (scripts/status.sh shows it later)."
echo
nemohermes "$SANDBOX" exec -- hermes cron run "$id" >"$log" 2>&1 &
pid=$!

t0=$SECONDS; last_row=$SECONDS; last_tick=$SECONDS; ended=0
while (( ! ended )); do
  sleep 15
  rows="$(sx bash -c "tail -n +$((seen + 1)) $LEDGER 2>/dev/null")"
  if [[ -n "$rows" ]]; then
    while IFS=$'\t' read -r ts _run phase subject decision why _evidence _result; do
      seen=$((seen + 1))
      printf '%s  %-17s %-34s %s: %s\n' "${ts:11:8}" "$phase" "${subject:0:34}" "$decision" "${why:0:100}"
      [[ "$phase" == run.end ]] && ended=1
    done <<<"$rows"
    last_row=$SECONDS; last_tick=$SECONDS
  elif (( SECONDS - last_tick >= 60 )); then
    printf '          ... still working (%dm elapsed, last step %dm ago)\n' $(((SECONDS - t0) / 60)) $(((SECONDS - last_row) / 60))
    last_tick=$SECONDS
  fi
  if (( ! ended )) && ! kill -0 "$pid" 2>/dev/null && (( SECONDS - last_row > 180 )); then
    echo "The job returned but the run logged no run.end. Hermes said:"
    grep -v 'Active gateway' "$log" | tail -20
    break
  fi
done

wait "$pid" 2>/dev/null || true
rm -f "$log"
say "Finished in $(((SECONDS - t0) / 60)) min. Delivery:"
status="$(sx hermes cron list | grep -A10 "Name: *$JOB\$")"
if grep -q 'Delivery failed' <<<"$status"; then
  grep 'Delivery failed' <<<"$status"
  echo "Send /sethome to your bot in Telegram, then run this again."
else
  grep -E 'Deliver:|Last run:' <<<"$status"
fi
