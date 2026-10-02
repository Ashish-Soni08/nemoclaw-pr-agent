# ledger

The agent's record lives in `$PR_AGENT_HOME/ledger/` inside the sandbox (`/sandbox/.pr-agent/ledger`) and is mirrored to a Hugging Face dataset (under `ledger/`) by `scripts/sync-ledger.sh`.

| File | Shape |
| --- | --- |
| `decisions.tsv` | `ts run phase subject decision why evidence result`, one row per decision, append-only. Written by `pr-agent log` and every `pr-agent` command. Cells are single-line; a leading `= + - @` gets a quote so spreadsheets never run it (a bare `-` means none and stays as is) |
| `spend.tsv` | `ts provider used unit cost_usd remaining limit source`, one row per provider (huggingface, firecrawl, lambda) per run summary. `source` says whether a number is from the provider's API or an estimate |
| `tokens.tsv` | `ts run subject step model tokens_in tokens_out cost_usd`, one row per (subject, step, model) at the end of each run, from Hermes' session records. Sessions can't be tied to an issue yet, so rows are run-wide: subject `-`, step the cron job (`pr-agent-run`, `pr-agent-follow-up`) |
| `run_config.tsv` | `run key value`, written when a run starts: `config` (`config/agent.yaml @ <short sha>`), `model.triage`, `model.fix`, `model.gate`, `model.summary`, `firecrawl.per_run_credits`, `schedule` |
| `lessons.tsv` | `id ts run scope lesson source evidence status`: what the agent learned from its own outcomes (`pr-agent lesson add`). `scope` is `owner/repo` or `*`; `status` is `active`, `retired` (pushed out by newer ones: 25 global, 10 per repo) or `dropped` (by a human, `pr-agent lesson drop <id>`). Active lessons go into every run's context. |
| `runs/<run>/candidates.jsonl` | What discovery handed to triage in that run |
| `media/<issue>/` | Before and after captures |

Phases you'll see: `start`, `discover.query|seen|verify|precedent|summary`, `policy`, `triage`, `claim.*`, `fix.*`, `gate`, `pr.opened|refused|outcome` (`pr.outcome` is written by `pr-agent pr updates` and the follow-up pre-step when a PR is first seen merged or closed: subject = the `pr.opened` row's issue id, result `merged` or `closed`), `follow-up.*`, `guard`, `lesson.add|drop`, `skill.flag`, `security.injection`, `run.end`.
