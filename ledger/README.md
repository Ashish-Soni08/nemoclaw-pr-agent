# ledger

The agent's record lives in `$PR_AGENT_HOME/ledger/` inside the sandbox (`/sandbox/.pr-agent/ledger`) and is mirrored to a Hugging Face dataset (under `ledger/`) by `scripts/sync-ledger.sh`.

| File | Shape |
| --- | --- |
| `decisions.tsv` | `ts run phase subject decision why evidence result`, one row per decision, append-only. Written by `pr-agent log` and every `pr-agent` command. Cells are single-line; a leading `= + - @` gets a quote so spreadsheets never run it |
| `spend.tsv` | `ts provider used unit cost_usd remaining limit source`, one row per provider (huggingface, firecrawl, lambda) per run summary. `source` says whether a number is from the provider's API or an estimate |
| `runs/<run>/candidates.jsonl` | What discovery handed to triage in that run |
| `media/<issue>/` | Before and after captures |

Phases you'll see: `start`, `discover.query|seen|verify|precedent|summary`, `policy`, `triage`, `claim.*`, `fix.*`, `gate`, `pr.opened|refused|outcome`, `follow-up.*`, `guard`, `skill.flag`, `security.injection`, `run.end`.
