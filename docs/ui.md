# UI

Read-only viewer for the decision ledger. Every action the agent takes can be
looked up here, with the reason behind it. Mockup:
[NemoClaw Ledger Mockup](https://claude.ai/artifact/5bPLfB4GeKEHRyfRkQFdYZ) (sample data).

## Decided

| Topic | Decision |
| --- | --- |
| Data source | Ledger lives in a Hugging Face bucket (see [ledger/schema.md](../ledger/schema.md)) |
| Layout | One screen: health strip, daily funnel, then timeline and detail side by side |
| Repos tab | Kept: AI-policy verdict per repo with the quoted policy text |
| Health | Run records and heartbeats in the ledger, health strip on the page, stale-heartbeat alert |
| Stack | Next.js on Vercel |

## Screen

1. **Health strip**: last heartbeat, runs today, errors in the last 24 h, alert state.
   Turns red when the heartbeat is older than 30 minutes.
2. **Funnel**: one day's counts per stage with the main drop-off reason.
   Clicking a stage filters the timeline.
3. **Timeline**: every entry, newest first, filterable by stage and outcome
   (kept, skipped, acted).
4. **Detail**: the selected entry: reason, quoted evidence, steps, diff, test
   output, links to the issue and PR, and the raw ledger line.
5. **Repos tab**: every repo the policy check has seen, its verdict, the quoted
   text and where it came from.

## Data flow

```
agent (sandbox) --hf sync--> HF bucket --server fetch, HF read token--> Next.js on Vercel --> browser
```

- The browser never talks to the bucket or the agent host. Next.js server code
  reads the bucket with a read-only token kept in Vercel env vars.
- The OpenClaw Gateway and the Lambda host are never reachable from the UI.
- Pages revalidate on a short interval, so the page stays current without a
  database.

## Settings

Agent criteria (PRs per day, topics, star range, labels, autonomy, schedule)
live in a config file in this repo, so every change is a commit. The UI shows
the settings in effect for each run but does not edit them. Still **open**:
Ashish to confirm the config-file approach.

Fixed in code, not configurable: skip repos that ban AI contributions, AI
disclosure in every PR, the sandbox network allowlist, a hard ceiling on the
daily PR cap.

## Open

- UI packages to add on top of Next.js (Ashish choosing).
- Whether the bucket is private (server reads with a token) or public.
