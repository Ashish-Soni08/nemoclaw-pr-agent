# UI

Read-only dashboard for the agent's ledger, in `ui/`. Every decision the agent
makes can be looked up here with its reason, alongside what it is spending.
Mockup: [NemoClaw Ledger Mockup](https://claude.ai/artifact/5bPLfB4GeKEHRyfRkQFdYZ).

## Decided

| Topic | Decision |
| --- | --- |
| Data source | `ledger/decisions.tsv` and `ledger/spend.tsv` in a private Hugging Face dataset, read server-side with a read token |
| Layout | One screen: health strip, credits, daily funnel, then timeline and detail side by side |
| Repos tab | AI-policy verdict per repo with the policy text it rests on |
| Credits | One card per provider (Hugging Face, Lambda, Firecrawl): left, spend per day, run-out date, provider vs estimate |
| Stack | Next.js + shadcn/ui on Vercel |

## Data flow

```
agent (sandbox) --host cron, every 30 min--> private HF dataset --server fetch, HF read token--> Next.js on Vercel --> browser
```

- The browser never sees the token, the agent host or the OpenClaw Gateway.
- The page re-reads the dataset every 5 minutes and shows when its data is from.

See [ui/README.md](../ui/README.md) for env vars and how each number is computed.
