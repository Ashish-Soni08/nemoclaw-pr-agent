# nemoclaw-pr-agent

An autonomous open-source contributor that runs inside NVIDIA NemoClaw. It finds issues where AI contributions are welcome, fixes them in a sandbox, opens pull requests, and logs every decision it makes.

## The challenge

Built for the **NVIDIA Berlin Claw Agent Challenge**: build a long-running agent on NemoClaw that does useful work on its own, not a chatbot that waits for prompts. Submissions closed on 2026-10-02.

## What we built

A Hermes agent in a NemoClaw sandbox on a Lambda Cloud VM. It works on a schedule with no human approval step:

- **Every 4 hours** it searches the Firecrawl Developer Index for open issues in AI and data-science repos, checks each one live on GitHub (open, unassigned, nobody on it, not already fixed), and reads the repo's AI-contribution policy.
- **It triages every candidate** as take or skip and writes down why. Repos that ask contributors to check in first get a plan comment ("ask-first"); the rest get a fix straight away ("go-directly").
- **A fix sub-agent** clones the repo, installs its dependencies, reproduces the problem, fixes it and runs the tests. A self-review gate (a correctness pass and a security pass on the exact diff) decides whether the PR opens.
- **Every 2 hours** a follow-up job answers review comments on its PRs and picks up maintainer replies to its plans.
- **Telegram** gets a summary after each run and a daily digest. Every decision, token and dollar goes into an append-only ledger that syncs to a Hugging Face dataset every 5 minutes and feeds the dashboard in `ui/`.

Example from the first day: 120 issues found, 40 still open on GitHub, 7 candidates, 1 taken ([NVIDIA-NeMo/Gym#2236](https://github.com/NVIDIA-NeMo/Gym/issues/2236), a docs-drift issue with 3 live findings). The agent posted its plan and is waiting for a maintainer before it opens the PR.

## Why we built it

Maintainers are drowning in low-effort AI pull requests. This agent tries to be the opposite: it reads each project's rules before touching anything, skips issues a maintainer has closed to outside help, asks first where the project wants that, shows its evidence, and stops cleanly when it is blocked instead of retrying. Developers get continuous, careful open-source contributions without babysitting an agent; maintainers get PRs that respect how their project works.

## What it is allowed to do

The sandbox blocks all network traffic except the hosts below. Keys never enter the sandbox: the OpenShell gateway adds them to requests as they leave, and only for the agent's own Python binary, so the code of the projects it works on never sees them.

| Access | Host | Who can use it | Why |
| --- | --- | --- | --- |
| Models | Hugging Face router via NemoClaw's `inference.local` | Hermes | Thinking, triage, fixes, review |
| GitHub API | `api.github.com` | `pr-agent` CLI only | Fork, commit through the Git Data API, open PRs, comment |
| Git clone | `github.com` (read-only) | `git` | Clone public repos |
| Firecrawl | `api.firecrawl.dev` | `pr-agent` CLI only | Find issues |
| PyPI | `pypi.org`, `files.pythonhosted.org` | pip in project venvs | Install a Python repo's dependencies |
| npm registry | `registry.npmjs.org`, `registry.yarnpkg.com` | node, npm, yarn, pnpm, bun | Install a JS/TS repo's dependencies |
| Telegram | Bot API | Hermes gateway | Summaries and digest |

| Credential | Scope | Where it lives |
| --- | --- | --- |
| GitHub token | Classic, `public_repo` only | OpenShell gateway, injected at egress |
| Firecrawl key | Developer Index | OpenShell gateway, injected at egress |
| Hugging Face token | Inference | OpenShell gateway |
| Hugging Face write token | The ledger dataset | Host only (`~/.pr-agent-sync.env`); the sandbox never has it |
| Telegram bot token | One bot | Hermes gateway |

Hard limits are enforced in code, not prompts (`src/pr_agent/publish.py`): a PR only opens if the gate passed on that exact diff and the repo's AI policy allows it; one open PR per repo; at most 400 changed lines and 20 files; it never edits `.github/workflows/` and never merges. Every PR and comment says it was written by an AI agent.

## Languages

Discovery rotates through Python, JavaScript and TypeScript.

| Language | Package managers | What the agent does |
| --- | --- | --- |
| Python | pip (a fresh venv per repo) | Installs the project and its test extras, runs pytest before and after the fix |
| JavaScript | npm, pnpm, bun, yarn (picked from `packageManager` or the lockfile) | Installs dependencies, runs the repo's `test` script before and after the fix |
| TypeScript | Same as JavaScript | Same as JavaScript |
| Anything else | None | Docs-only fixes |

## How the instructions keep it on track

The agent's behaviour comes from Hermes skills in `skills/`. The router, `pr-agent-mode`, is adapted from poteto-mode (MIT) and holds 14 playbooks and 7 principles.

| Instructions | What they make the agent do |
| --- | --- |
| `SOUL.md` | Who it is: an autonomous contributor that respects maintainers and goes through `pr-agent` for every outside action |
| `pr-agent-mode` (router) | Picks the right playbook for each situation: autonomous run, investigation, fix, babysit, pause safely |
| `discover-work`, `check-ai-policy` | Find issues and read each repo's AI policy; a ban is final, a maintainer's "no" blocks the repo |
| `triage-issues` | A take or skip with a written reason for every candidate, and the ask-first or go-directly lane |
| `claim-issue` | A short plan comment for ask-first repos; no work until a maintainer says yes |
| `fix-issue`, `systematic-debugging`, `evidence-driven-testing` | Reproduce first, fix the root cause, prove it with tests |
| `self-review-gate` | A correctness pass and a security pass on the exact diff; the PR opens only on a pass |
| `follow-up` | Answer review comments, pick up claim replies, record PR outcomes |
| `show-me-your-work` | Log every decision with its evidence, so a human can audit the run |
| Hermes memory | After a PR outcome, review or claim answer, save a short fact about the repo for next time (also logged as a `lesson` row) |

The agent never edits its own skills. If one gives wrong guidance it logs a `skill.flag` row and a human changes it, so a malicious issue or comment can't rewrite its rules.

## Models

All models run through the Hugging Face Inference Providers router. Prices are USD per 1M tokens (input / output) from `config/agent.yaml`.

| Job | Model | Price | What it does |
| --- | --- | --- | --- |
| Main | GLM-5.3 (`zai-org/GLM-5.3`) | 1.40 / 4.40 (Baseten) | Every cron run: triage, sending work to sub-agents, PR text |
| Fix | Qwen3 Coder 480B (`Qwen/Qwen3-Coder-480B-A35B-Instruct`) | 0.38 / 1.55 | One sub-agent per issue: repro, fix, tests |
| Fix backup | Kimi K3 (`moonshotai/Kimi-K3`) | 2.70 / 13.50 | Used if Qwen3 Coder isn't available |
| Review | DeepSeek V4.1 Flash + GLM-5.3 | 0.20 / 0.60 (DeepSeek) | The two-pass self-review, by a different model family than the fixer |
| Chores | GLM-5.3 Flash (`zai-org/GLM-5.3-Flash`) | 0.15 / 0.50 | Summarizing context, titles |

Nemotron 3 Ultra was the planned main model, but it failed NemoClaw onboarding (HTTP 400 on Chat Completions), so GLM-5.3 took over. Ultra stays on the candidate list with Kimi K2.7 Code, MiniMax M3, MiMo Pro, Qwen3.8 and Inkling. The agent can't use a model outside this menu.

A usage guard prices every run against this menu and stops the agent once the monthly budget ($400) is spent.

**Runs on:** [Hugging Face](https://huggingface.co) (models and the ledger dataset) · [Lambda](https://lambda.ai) (the VM) · [Firecrawl](https://www.firecrawl.dev) (issue discovery)

## Watching it work: the ledger

Nobody approves the agent's PRs before they open, so a human has to be able to check its work afterwards. Every decision it makes (each issue found, each policy check, each take or skip and why, each test run, gate verdict and PR) is one row in an append-only ledger with a reason and a link to the evidence. Tokens and spend go in the same ledger. The VM syncs it to a private Hugging Face dataset every 5 minutes, and a read-only dashboard shows it. That way you can see what the agent did, why, and what it cost, without ever exposing the VM or the sandbox.

**Dashboard:** [nemoclaw-pr-agent-ledger.vercel.app](https://nemoclaw-pr-agent-ledger.vercel.app)

## Demo video

[Watch the demo (about 90 s)](docs/media/demo.mp4): the agent's real first day, from issue discovery to the plan posted on NVIDIA-NeMo/Gym#2236.

To run it yourself, follow [docs/runbook-lambda.md](docs/runbook-lambda.md): `scripts/install.sh`, `scripts/setup-credentials.sh`, `scripts/deploy.sh`, `scripts/run-now.sh`.

## License

MIT. Third-party skills keep their own MIT notices in `skills/THIRD_PARTY_NOTICES.md`.
