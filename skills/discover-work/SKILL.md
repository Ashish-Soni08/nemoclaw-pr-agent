---
name: discover-work
description: "Find issues: Firecrawl Index, then live GitHub checks"
version: 0.1.0
license: MIT
metadata:
  hermes:
    tags: [pr-agent, discovery, firecrawl]
---

# Discover work

The Index finds; GitHub confirms; triage ranks. Design: `docs/discovery.md` in the agent repo.

The cron pre-step runs `pr-agent prestep-run`, which already did all of this and put the result in your context as `candidates`. Run it yourself only when that output is missing: `pr-agent discover`.

What the script does, so you can read its output:

1. Takes the next 3 topics and 2 issue shapes from `references/query-bank.yaml` and runs them against the Developer Index (Python repos, 200 to 30,000 stars, not archived, not forks). Hard credit caps: 100 per run, 25,000 per month, checked before each call.
2. Skips issues it has seen recently (`state/seen.tsv`).
3. Checks each hit live on GitHub, cheapest check first: repo alive and licensed, issue open, unlocked, unassigned, updated in 180 days, no open PR referencing it, no "I'm working on this" comment in 14 days. Older claims (14 to 30 days) are passed on as `ambiguous_claims` for you to judge.
4. For each survivor, one more Index query for merged PRs in that repo: a merged PR that names the issue means it's already fixed (dropped); the closest merged PRs come back as `precedent_prs`, examples of how this repo writes fixes and tests.
5. Runs **check-ai-policy** on each repo and drops repos that ban AI contributions or have no clear policy (see that skill).

Every query, credit, drop and keep is a ledger row, so a human can trace any candidate back to the query that found it and the GitHub fact that kept it.

You do not change the query bank, the caps or the filters. If discovery keeps returning nothing useful, log `pr-agent log skill.flag discover-work "<what you saw>"` for a human.
