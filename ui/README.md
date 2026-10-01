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

Without `LEDGER_DATASET` the page shows the sample ledger in `lib/sample/` and says so in the header.

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
