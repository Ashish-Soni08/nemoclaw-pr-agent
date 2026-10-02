# nemoclaw-pr-agent

Autonomous NemoClaw agent that finds open-source issues where AI contributions are welcome, fixes them in a sandbox and opens PRs, with every decision logged. Built for the NVIDIA Berlin Claw Agent Challenge.

It runs on a schedule with no human approval step. A self-review gate (a correctness pass and a security pass, run in parallel on the exact diff) decides whether a PR opens, and hard checks in code enforce the rest: the repo's AI policy, daily caps, one open PR per repo, no CI edits, never merge. Telegram gets a summary after every run.

## How a run works

```
Hermes cron (every 4h, inside the NemoClaw sandbox)
  pre-step script (no tokens spent)
    usage guard          -> skip the run if the model budget is spent
    discover-work        -> Firecrawl Developer Index, 5-6 queries, credit-capped
                            -> live GitHub checks: open, unassigned, nobody on it, not already fixed
    check-ai-policy      -> CONTRIBUTING / AI policy / maintainer discussion; bans are final
  agent (Nemotron 3 Ultra via the Hugging Face router)
    pr-agent-mode router -> triage-issues: take or skip, with a reason, for every candidate
                         -> ask-first lane: claim-issue (comment a plan, wait for a maintainer)
                         -> go-directly lane: fix sub-agent (fix-issue + poteto playbooks)
                         -> self-review-gate (thermo-nuclear-review || security-review)
                         -> pr-agent pr open (refuses unless the gate passed on this diff)
    final response       -> pr-agent summary run -> Telegram
follow-up cron (every 2h): review comments on its PRs, maintainer replies to its claims
```

Everything the agent decides lands in `decisions.tsv` (one row per decision: what, why, evidence), and per-provider spend in `spend.tsv`. Both sync to a Hugging Face dataset for the UI.

## Layout

| Path | Contents |
| --- | --- |
| `skills/` | Hermes skills, one folder each. `pr-agent-mode` is the router; its `references/` hold the 14 playbooks and 7 principles adapted from poteto-mode. See `skills/THIRD_PARTY_NOTICES.md` |
| `src/pr_agent/` | The `pr-agent` CLI: discovery, GitHub, policy, workspace, publish checks, ledger, usage guard, spend, summaries |
| `bin/pr-agent` | Runs the CLI from the checkout |
| `config/agent.yaml` | Caps, model menu with prices, budgets |
| `hermes/` | `SOUL.md`, cron job registration, Hermes settings, cron pre-step scripts |
| `policies/` | OpenShell egress preset and credential-injection provider profiles |
| `scripts/` | Host-side install, credentials, deploy, run, status, ledger sync |
| `docs/` | `runbook-lambda.md` (start here), `design.md`, `discovery.md` |
| `tests/` | Offline tests with a fake GitHub and Index |

## Run it

Follow [docs/runbook-lambda.md](docs/runbook-lambda.md): `scripts/install.sh`, `scripts/setup-credentials.sh`, `scripts/deploy.sh`, `scripts/run-now.sh`.

## Develop

```bash
python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'
.venv/bin/pytest -q
```

## License

MIT. Third-party skills keep their own MIT notices in `skills/THIRD_PARTY_NOTICES.md`.
