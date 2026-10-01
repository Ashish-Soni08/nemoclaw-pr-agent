# Runbook: run the agent on a Lambda VM

From a fresh Lambda instance to a scheduled agent that sends run summaries to Telegram. About 30 to 45 minutes, most of it the first NemoClaw build.

Items marked **VERIFY** could not be tested from the build session (NemoClaw, Firecrawl, the HF router and Telegram are all blocked there). Each says what to look for and what to do if it fails.

## 0. What you need

| Key | Where to get it | Used by |
| --- | --- | --- |
| `HF_TOKEN` | huggingface.co, Settings, Access Tokens. Fine-grained, with "Make calls to Inference Providers" and, under Repositories, "Write access to contents/settings of all repos under your personal namespace" (the ledger sync creates and writes the dataset) | Model inference, ledger sync |
| `GITHUB_TOKEN` | A fine-grained token on the account that will open PRs. Repository access: all repositories. Permissions: Contents, Pull requests, Issues: read and write; Administration: read and write (forking); Metadata: read | Forks, pushes through the API, PRs, comments |
| `FIRECRAWL_API_KEY` | firecrawl.dev dashboard | Developer Index |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_IDS` | @BotFather (`/newbot`), and your numeric id from @userinfobot | Run summaries |
| `LEDGER_DATASET` | A Hugging Face dataset repo name, e.g. `ashish-soni08/pr-agent-ledger`. The first sync creates it, private | The UI reads the ledger from here |

Export them in your SSH shell only when a step asks. Don't write them into files in the repo, and don't paste them in chat.

## 1. Launch the VM

Lambda Cloud console: launch the cheapest instance (1x V100, $0.79/h) with Ubuntu 24.04 (Lambda Stack). No GPU is used; the agent only needs CPU, 16 GB RAM and 40 GB disk. Add your SSH key, then:

```bash
ssh ubuntu@<ip>
sudo usermod -aG docker $USER && newgrp docker   # Lambda Stack ships Docker; this lets you run it without sudo
docker run --rm hello-world
node --version   # NemoClaw needs Node 22.19+; the installer sets it up if missing
git clone https://github.com/Ashish-Soni08/nemoclaw-pr-agent.git && cd nemoclaw-pr-agent
```

Pause the instance from the console when you're not demoing; `ledger/spend.tsv` tracks the hours against the $75.

## 2. Install NemoClaw with Hermes and the Hugging Face router

```bash
export HF_TOKEN=...            # once, in this shell
export TELEGRAM_BOT_TOKEN=... TELEGRAM_ALLOWED_IDS=...
scripts/install.sh
```

This onboards a sandbox called `pr-agent` with Nemotron 3 Super as the main model, served through `router.huggingface.co` as an OpenAI-compatible endpoint. The HF token goes to the OpenShell gateway; the sandbox talks to `inference.local` and never sees it.

**VERIFY (model id).** Before installing, check the router serves the menu: `python3 -m pip install --user pyyaml && HF_TOKEN=$HF_TOKEN bin/pr-agent models`. Every row should say `"served": true`. If the Super id isn't served, pick the served Nemotron id from `curl -s -H "Authorization: Bearer $HF_TOKEN" https://router.huggingface.co/v1/models | python3 -m json.tool | grep -i nemotron`, put it in `config/agent.yaml`, and export `PR_AGENT_MAIN_MODEL=<id>` before `install.sh`.

**VERIFY (per-task models).** Fix sub-agents use `delegation.model` (Qwen3.5 by default). If NemoClaw's managed route pins every request to the onboarded model, sub-agents silently run on Super too. Check after the first run with `nemohermes pr-agent exec -- sqlite3 /sandbox/.hermes/state.db "select model, count(*) from sessions group by 1"`. Either outcome works; the usage guard prices whatever ran.

**Telegram.** Message your bot once, then send `/sethome` in that chat so cron output has a home channel.

## 3. Register the GitHub and Firecrawl keys

```bash
export GITHUB_TOKEN=... FIRECRAWL_API_KEY=...
scripts/setup-credentials.sh
unset GITHUB_TOKEN FIRECRAWL_API_KEY
```

The keys become OpenShell providers, injected at egress for `api.github.com` and `api.firecrawl.dev` only, and only for Hermes' Python.

**VERIFY (credential injection).** This follows the pattern NemoClaw uses for Tavily and the chief-of-staff recipe uses for Slack, but no recipe does it for a custom GitHub profile. After step 4, the smoke test `pr-agent policy huggingface/transformers` must print a verdict. A 401 means the placeholder isn't being swapped: check `openshell sandbox provider list pr-agent`, and that `env | grep PRAGENT_` inside the sandbox shows placeholders. If injection can't be made to work in time, use the fallback in section 7.

**VERIFY (who gets the token).** The GitHub profile injects the token only for `/opt/hermes/.venv/bin/python`. Repo test suites run under a venv built from a Python interpreter too, so check OpenShell doesn't match them as the same binary: inside the sandbox, run `.venv-pr-agent/bin/python -c "import urllib.request; print(urllib.request.urlopen('https://api.github.com/user').status)"` from any prepared workspace under `/sandbox/.pr-agent/workspaces/`. It should fail (403 from the policy or 401 from GitHub). A 200 means other people's test code can act as the agent's GitHub account; give the token only the permissions it needs (Contents, Pull requests and Issues write; no Workflows, no Administration) and tell the build thread.

## 4. Deploy the agent

```bash
scripts/deploy.sh
```

Uploads the repo to `/sandbox/nemoclaw-pr-agent`, installs every skill folder, writes `SOUL.md`, sets Hermes options (`hermes/apply-config.sh`) and registers three cron jobs (`hermes/register-jobs.sh`):

| Job | Schedule (UTC) | What it does |
| --- | --- | --- |
| `pr-agent-run` | every 4 hours | Pre-step: usage guard, Developer Index discovery, GitHub checks, AI-policy checks. Then the agent triages, claims or fixes, runs the gate, opens PRs. Summary to Telegram. |
| `pr-agent-follow-up` | every 2 hours at :30 | Wakes only when a PR got comments or a claim got a reply. Summary to Telegram. |
| `pr-agent-daily-digest` | 19:00 | No model call. The day's numbers to Telegram. |

Change schedules with `PR_AGENT_RUN_SCHEDULE` etc. (see `hermes/register-jobs.sh`) and re-run `deploy.sh`.

**VERIFY (approvals).** NemoClaw's managed Hermes config uses manual approvals. Trigger one run (`scripts/run-now.sh`) and watch `scripts/status.sh`: if the run stalls waiting for an approval that nobody can give, cron runs can't finish. Whether to change that setting is your call; the sandbox policy and the hard checks in `pr-agent` (gate, caps, policy, no workflow edits) are what limit the agent either way.

**VERIFY (turn limit).** `apply-config.sh` raises `agent.max_turns` to 200. NemoClaw rebuilds regenerate `config.yaml`, so re-run `deploy.sh` after any `rebuild`.

## 5. First run

```bash
scripts/run-now.sh
scripts/status.sh 40
```

What a good first run looks like in the ledger: a `start` row; six or fewer `discover.query` rows with hit counts and `coverage ok`; `discover.verify` rows (most will say dropped, with a reason); `policy` rows; `triage` rows with take or skip and a reason for every candidate; then for taken issues `fix.*`, `gate`, and `pr.opened` or `pr.refused`; finally `run.end`. Telegram gets the summary.

**VERIFY (Developer Index).** From `docs/discovery.md` section 8: the first run shows whether hits come back as `issue:owner/repo#N`, whether the `topic` filter matches GitHub topics, and how many hits survive the GitHub checks. If fewer than about 1 in 10 survive, raise `k` or widen the star window in `skills/discover-work/references/query-bank.yaml` and redeploy.

**Repos with no written AI policy.** `continue_on_unclear_policy` is `true` (decided 2026-10-01), so the agent also works in repos that say nothing about AI contributions, which is most of them. Every PR and claim still says it was written by an AI agent. When a maintainer says no to AI contributions, the agent runs `pr-agent policy <repo> --block`, which marks the repo `bans` permanently (stored in `state/policy/blocked.json`; no cache expiry undoes it). To check what's blocked: `nemohermes pr-agent exec -- cat /sandbox/.pr-agent/state/policy/blocked.json`. Set the switch to `false` and redeploy to go back to explicit-policy repos only.

## 6. Ledger to the Hugging Face dataset (for the UI)

```bash
crontab -e
# add (one line):
*/30 * * * * cd $HOME/nemoclaw-pr-agent && HF_TOKEN=<token> LEDGER_DATASET=<you/pr-agent-ledger> scripts/sync-ledger.sh >> $HOME/pr-agent-sync.log 2>&1
```

The crontab holds the token in plain text on the VM, readable only by your user. If you'd rather not, run `scripts/sync-ledger.sh` by hand before demos. Each sync is one commit to the dataset. Files in the dataset:

- `ledger/decisions.tsv`: every decision (ts, run, phase, subject, decision, why, evidence, result)
- `ledger/spend.tsv`: per-provider spend snapshots (ts, provider, used, unit, cost_usd, remaining, limit, source) for Hugging Face, Firecrawl and Lambda
- `ledger/runs/<run>/candidates.jsonl`: what discovery handed to triage
- `ledger/media/<issue>/`: before and after captures

The dataset is created private, so only you (and the UI, with your token) can read it. To let maintainers follow the footer link in each PR, make the dataset public in its settings, set `ledger.public_url` in `config/agent.yaml` to `https://huggingface.co/datasets/<you>/pr-agent-ledger`, and redeploy.

## 7. Fallback: Hermes directly on the VM (no sandbox)

Use only if credential injection or the NemoClaw build blocks you before the deadline. You lose the OpenShell sandbox, so the agent runs other people's test suites directly on the VM; keep the VM for this agent only.

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
mkdir -p ~/.pr-agent && chmod 700 ~/.pr-agent
# ~/.pr-agent/secrets.env, mode 600: GITHUB_TOKEN=... and PRAGENT_FIRECRAWL_KEY=...
hermes config set model.provider huggingface
hermes config set model.default nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-FP8
# HF_TOKEN, TELEGRAM_BOT_TOKEN, TELEGRAM_ALLOWED_USERS in ~/.hermes/.env
cp -r skills/* ~/.hermes/skills/ && cp hermes/SOUL.md ~/.hermes/SOUL.md
mkdir -p ~/.local/bin && ln -sf $PWD/bin/pr-agent ~/.local/bin/pr-agent
PR_AGENT_REPO=$PWD bash hermes/apply-config.sh && PR_AGENT_REPO=$PWD bash hermes/register-jobs.sh
hermes gateway run   # in tmux; it ticks the cron jobs
```

## 8. Stop, pause, inspect

- Pause the agent: `nemohermes pr-agent exec -- hermes cron pause <job-id>` (ids from `hermes cron list`).
- Everything it did: `scripts/status.sh 200`, or the dataset.
- Spend right now: `nemohermes pr-agent exec -- /sandbox/nemoclaw-pr-agent/bin/pr-agent spend`.
- The agent never merges and never pushes to anyone else's branch. To withdraw a PR, close it on GitHub; the next follow-up logs the outcome.
