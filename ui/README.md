# ui

Read-only dashboard for the agent's ledger: health, credits, the daily funnel, every decision with its reason, and each repo's AI-policy verdict. Next.js + shadcn/ui, deployed on Vercel.

It reads two files the agent mirrors to a private Hugging Face dataset (see [ledger/README.md](../ledger/README.md)):

- `ledger/decisions.tsv`: `ts run phase subject decision why evidence result`
- `ledger/spend.tsv`: `ts provider used unit cost_usd remaining limit source`

It never talks to the agent host or the OpenClaw Gateway.

## Run

```bash
npm install
npm run dev
```

Without `LEDGER_DATASET` the page shows the sample ledger in `lib/sample.ts` and says so in the header.

| Env var | Purpose |
| --- | --- |
| `LEDGER_DATASET` | Dataset id, e.g. `ashish-soni08/pr-agent-ledger` (files under `ledger/`) |
| `HF_TOKEN` | Read-only token for that dataset. Server-side only; never exposed to the browser |

The page re-reads the dataset every 5 minutes. The host mirrors the ledger every 30 minutes, so the page can be up to 35 minutes behind; the header and each credits card show when their data is from.

## Where things come from

All numbers are computed in `lib/derive.ts` from those two files:

- **Health**: the newest rows. A `start` row without `run.end` means a run is in progress (or crashed); `guard` with result `skipped` means the budget stopped it.
- **Credits**: the latest `spend.tsv` row per provider; spend per day is the change in the running total.
- **Spend and output over time**: those per-day amounts plus `pr.opened` rows per day, grouped by day, month or year.
- **Funnel**: for the latest day, counts of `discover.verify`, `policy`, `triage`, `claim.*`/`fix.*` and `pr.opened` rows for the day.
- **Repos**: the latest `policy` row per repo.
- **Runs tab**: one row per `run` id. Found = `discover.verify` rows, attempted = issues with `fix.*` rows, passed gate = `gate` rows with result `pass`, merged/closed = `pr.outcome` rows (matched to the run's `pr.opened` by issue). State: `guard`+`skipped` is stopped by budget, `run.end` is finished, otherwise stalled (or failed, if it logged an error) once the newest row is 2 hours old.
- **Gate rejections**: `gate` rows whose result isn't `pass`, plus `pr.refused` rows, with the `why` as the reason.
- **Agent resources**: from `ledger/host.tsv` (one sample a minute from a sampler on the VM), only the agent's own CPU cores, memory and workspace storage, with the last 6 hours and runs shaded. Machine-wide columns in the file are not sent to the page. It arrives with the ledger sync, so it runs a few minutes behind; the page never talks to the VM.
- **Run drill-down**: click a run for the settings it started with (`ledger/run_config.tsv`) and, per issue it worked on, which model did each step with tokens and cost (`ledger/tokens.tsv`).
- **Tokens by model**: sums of `ledger/tokens.tsv`.

Two more files the agent writes (claude/build-pr-agent-nvg8ss). Today every `tokens.tsv` row is run-wide (`subject` is `-`, `step` is the cron job), so the drill-down shows it as "Whole run"; per-issue rows show up as soon as the agent can attribute them:

| File | Columns | Written |
| --- | --- | --- |
| `tokens.tsv` | `ts run subject step model tokens_in tokens_out cost_usd` | end of each run, one row per (subject, step, model); `subject` is the issue id or `-` for run-wide work like discovery |
| `run_config.tsv` | `run key value` | at run start: `config` (file @ commit), `model.triage`, `model.fix`, `model.gate`, `model.summary`, limits, `schedule` |
