# Design

Working design for the NemoClaw PR agent. Decisions marked **open** wait on Ashish.

## Goal

A long-running agent that finds issues in AI, data-science and data-analysis
repositories where AI-assisted contributions are welcome, fixes them inside a
sandbox and opens pull requests. Every decision it makes is recorded so a human
can see what it did and why.

Built for the NVIDIA Berlin Claw Agent Challenge (submissions close 2026-10-02).

## Stack

| Layer | Choice |
| --- | --- |
| Runtime | NemoClaw: OpenClaw running inside an OpenShell sandbox |
| Model | Nemotron through NVIDIA Build hosted endpoints |
| Host | Lambda Cloud instance (no local model, so no GPU work) |
| Repo discovery and context | Firecrawl Developer Index, GitHub REST API |
| Chat | Telegram (OpenClaw channel) plus the built-in OpenClaw Control UI |
| Record of work | Ledger in a Hugging Face bucket, read by a Next.js UI on Vercel ([ui.md](ui.md)) |

Structure follows NVIDIA's community recipes, mainly
[PR Test Case Assistant](https://github.com/NVIDIA/nemoclaw-community/tree/main/examples/recipes/nvidia/pr-test-case-assistant)
(OpenClaw in NemoClaw against public GitHub). Anything copied from that repo
keeps its Apache-2.0 header.

## Pipeline

Each stage narrows the candidates and writes a ledger entry with its reason.

1. **discover-repos**: active repos matching the topics.
2. **check-ai-policy**: read CONTRIBUTING, PR templates and AI policy files;
   classify as `allows`, `allows-with-disclosure`, `bans` or `unclear`.
   Only the first two continue. Verdicts are cached per repo.
3. **triage-issues**: keep unassigned issues with no linked open PR and no
   "I'm working on this" comment; rank by clarity, maintainer confirmation
   and size.
4. **claim-issue**: when the repo asks contributors to claim issues, comment
   and wait for a maintainer. Issues open to anyone skip this step.
5. **fix-issue**: one sub-agent per issue. Clone in the sandbox, run the
   baseline tests, fix, add a test, re-run, open the PR with AI disclosure.
   Skip when the baseline does not build or pass.
6. **follow-up**: watch review comments on open PRs and respond.
7. **ledger**: structured record of every decision; daily summary.

## Guardrails

- Only repos whose policy allows AI-assisted contributions.
- Daily PR cap.
- Every PR states that it was written with an AI agent and links its ledger entry.
- Sandbox network allowlist: GitHub, Firecrawl, NVIDIA Build, PyPI, Hugging Face (ledger only).
- Deterministic steps (search, policy fetch, test runs) are scripts the agent
  calls, not model improvisation.

## Open decisions

- PR rules and what each PR must include (Ashish is researching).
- Topics, languages, repo size bounds, issue types, daily volume, PR account,
  follow-up autonomy, schedule. Proposed defaults are in the project thread.
