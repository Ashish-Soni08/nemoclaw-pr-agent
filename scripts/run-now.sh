#!/usr/bin/env bash
# Trigger the main cron job once, now (for the demo or a first test), and print each ledger
# row as the agent writes it until the run logs run.end. Ctrl+C stops watching, not the run.
source "$(dirname "$0")/_lib.sh"
JOB="${1:-pr-agent-run}"
LEDGER=/sandbox/.pr-agent/ledger/decisions.tsv
RUNLOG=/sandbox/.pr-agent/run-now.log
# nemohermes prints "Active gateway set" on every call; keep only the command's own output.
# Every nemohermes call holds a host lock until it returns, so the run itself is started
# detached inside the sandbox; otherwise the polling below (and status.sh) would wait on it.
sx() { nemohermes "$SANDBOX" exec -- "$@" 2>&1 | grep -v 'Active gateway' || true; }

id="$(sx python3 -c "import json;print(next(j['id'] for j in json.load(open('/sandbox/.hermes/cron/jobs.json'))['jobs'] if j.get('name')=='$JOB'))" | tail -1)"
seen="$(sx bash -c "wc -l < $LEDGER 2>/dev/null || echo 0" | tail -1)"

say "Starting $JOB ($id) at $(date -u +%H:%M) UTC"
echo "Discovery and policy checks take a minute or two, triage a few more. If the agent takes an issue,"
echo "the fix, the tests and the self-review gate can take 30 to 60 minutes. Each step prints below."
echo "Ctrl+C stops watching; the run keeps going (scripts/status.sh shows it later)."
echo
sx bash -c "setsid nohup hermes cron run $id >$RUNLOG 2>&1 </dev/null & echo started in the background"

t0=$SECONDS; last_row=$SECONDS; last_tick=$SECONDS; ended=0
while (( ! ended )); do
  sleep 15
  out="$(sx bash -c "tail -n +$((seen + 1)) $LEDGER 2>/dev/null; if pgrep -f '[h]ermes cron run $id' >/dev/null; then echo __RUNNING__; else echo __DONE__; fi")"
  running=0; grep -q '^__RUNNING__$' <<<"$out" && running=1
  rows="$(grep -v '^__RUNNING__$\|^__DONE__$' <<<"$out" || true)"
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
  if (( ! ended && ! running )) && (( SECONDS - last_row > 60 )); then
    echo "The job stopped without logging run.end. Hermes said:"
    sx tail -20 "$RUNLOG"
    break
  fi
done

say "Finished in $(((SECONDS - t0) / 60)) min. Delivery:"
status="$(sx hermes cron list | grep -A10 "Name: *$JOB\$" || true)"
if grep -q 'Delivery failed' <<<"$status"; then
  grep 'Delivery failed' <<<"$status"
  echo "Send /sethome to your bot in Telegram, then run this again."
else
  grep -E 'Deliver:|Last run:' <<<"$status"
fi
