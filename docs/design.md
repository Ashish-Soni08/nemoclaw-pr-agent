# Design

How the PR agent is built and why. The runbook (`runbook-lambda.md`) says how to run it; `discovery.md` covers how it finds work.

## Goal

A long-running agent that finds issues in AI, data-science and data-analysis repositories where AI-assisted contributions are welcome, fixes them inside a sandbox and opens pull requests. Every decision it makes is recorded so a human can see what it did and why. Built for the NVIDIA Berlin Claw Agent Challenge (submissions close 2026-10-02).

## Decisions

| Decision | Choice |
| --- | --- |
| Runtime | NemoClaw with the Hermes agent: OpenShell sandbox, Hermes skills, cron, sub-agents, Telegram |
| Host | Lambda Cloud 1x A10 instance (cheapest available), paused when not demoing (no GPU work) |
| Models | Hugging Face Inference Providers router, through NemoClaw's managed `inference.local` route. A menu of five models in `config/agent.yaml`: Nemotron 3 Super is the main model, a coder model runs fix sub-agents, Nano does chores |
| Autonomy | Fully autonomous. No human approves a PR. The self-review gate decides; code enforces the hard limits |
| Issues | No type restriction. Any issue in a Python AI/data-science repo the agent can genuinely help with; triage decides |
| PR format | poteto's: Why, Scope, Blast Radius, Verification. Conventional Commits titles |
| Discovery | Firecrawl Developer Index on every run, each hit verified live on GitHub |
| Record | `decisions.tsv` and `spend.tsv`, synced from the host to a Hugging Face dataset |
| Notifications | Telegram run summaries and a daily digest. No approvals over Telegram |

## The model decides, scripts act

The model reads issues, chooses what to take, debugs, writes the fix and the PR text, and runs the review gate. Everything that touches the outside world is a `pr-agent` command with hard checks in code:

- `pr-agent pr open` refuses unless the gate passed on the exact diff (hash checked), the repo's policy allows AI contributions, the daily cap (3) and one-open-PR-per-repo rule have room, the title is Conventional Commits, the body has the four sections, the diff is under 400 lines and 20 files, and nothing under `.github/workflows/` changed. It appends the AI disclosure and the ledger link itself.
- `pr-agent claim post` wraps the plan in a fixed comment that says it's an AI agent and that "no" is respected; one claim per issue, 3 per day.
- Pushes go through the GitHub Git Data API (blobs, tree, commit, ref) on the agent's fork, so the only credential is one bearer header on `api.github.com`. OpenShell injects it at egress; the sandbox sees a placeholder.
- Target repos' code (setup, tests) runs with a scrubbed environment: no tokens, no placeholders.
- The usage guard prices Hermes' own token records against the menu and skips runs when the daily or monthly budget is spent. Hugging Face spend limits only exist for Team/Enterprise orgs, so this is the limit.
- Firecrawl credits are capped per run (30) and per month (900), checked before each call.

## Skills

The method is poteto's (cursor/plugins pstack, MIT): `pr-agent-mode` is a router modeled on poteto-mode. It holds 14 adapted playbooks and 7 principles under `references/`, so Hermes doesn't list them in the skill index and only the router loads them. Task skills (`discover-work`, `check-ai-policy`, `triage-issues`, `claim-issue`, `fix-issue`, `follow-up`) follow Benny's triage and repro-and-fix automations. Tool skills: `self-review-gate`, `systematic-debugging`, `before-and-after`, `evidence-driven-testing`, `make-pr-easy-to-review`, `deslop`, `unslop`, `show-me-your-work`.

Two overrides of poteto: stay strictly inside the issue taken, and the gate decides whether a PR opens. The agent never edits its own skills; it logs `skill.flag` rows for humans.

## Guardrails

- Only repos whose policy allows AI-assisted contributions (`allows`, `allows-with-disclosure`). `unclear` repos (no written policy) are allowed too, because `continue_on_unclear_policy` is on; every PR discloses it's AI-written, and a maintainer's "no" blocks that repo permanently.
- Every PR and claim says it was written by an AI agent and links the ledger.
- Never merges, never force-pushes someone else's branch, never edits CI workflows, never argues with a maintainer.
- Sandbox egress: inference route, `api.github.com` and `api.firecrawl.dev` (Hermes' Python only), `github.com` git fetch, PyPI, Telegram.
- Issue and repo text is untrusted input; the router tells the agent to log prompt-injection attempts and never act on them.

## Open questions for the VM

Listed with checks in `runbook-lambda.md`: the HF model ids, whether the managed route honors per-task models, credential injection for the custom profiles, approval behavior in cron runs, and the Developer Index hit rate.
