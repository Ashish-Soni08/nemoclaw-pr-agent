# Ledger schema

Draft v1. The agent writes, the UI reads. Stored in a public Hugging Face dataset
(`LEDGER_DATASET`), so every change is a commit anyone can inspect.

## Layout in the dataset

```
runs/2026-09-29/r-0929-a.jsonl           one line per entry, in order
runs/2026-09-29/r-0929-a.config.yaml     settings in effect for that run
artifacts/r-0929-a/e-0929-a-028/diff.patch
artifacts/r-0929-a/e-0929-a-028/tests.txt
health/heartbeat.json                    overwritten on every heartbeat
```

The agent only ever appends lines to a run file and never rewrites an earlier
line; the dataset's commit history shows if that rule was ever broken. The run
file is uploaded every few minutes during a run (one commit per upload) so the
UI can show a run in progress. Diffs and test logs are paths in the dataset.

## Entry

One JSON object per line. Fields not relevant to an entry are left out.

| Field | Type | Notes |
| --- | --- | --- |
| `v` | int | Schema version, `1` |
| `id` | string | `e-<run>-<seq>`, e.g. `e-0929-a-028` |
| `ts` | string | ISO 8601 UTC |
| `run_id` | string | e.g. `r-0929-a` |
| `kind` | enum | `decision`, `action`, `run`, `error` |
| `stage` | enum | `discover-repos`, `check-ai-policy`, `triage-issues`, `claim-issue`, `fix-issue`, `follow-up` |
| `outcome` | enum | `kept`, `skipped`, `acted` (for `decision` and `action`) |
| `summary` | string | One line shown in the timeline |
| `reason` | string | Why, in a full sentence a human can read |
| `subject` | object | `{ repo, issue, pr }`, each optional |
| `policy` | object | `{ verdict, source }`, verdict is `allows`, `allows-with-disclosure`, `bans`, `unclear` |
| `evidence` | array | `[{ kind, quote, source, url }]`, kind is `policy`, `comment`, `label`, `file` |
| `steps` | array | `[{ label, detail }]`, the chain shown in the detail view |
| `tests` | object | `{ baseline: { passed, failed }, after: { passed, failed } }` |
| `artifacts` | object | `{ diff, tests, pr_url, comment_url }`, dataset paths or URLs |
| `counts` | object | Funnel numbers, on `discover-repos` and `run` entries |
| `error` | object | `{ source, message, retried }` on `error` entries |

### Run entries

`kind: "run"` marks the start and end of a run:

```json
{"v":1,"id":"e-0929-a-000","ts":"2026-09-29T08:00:00Z","run_id":"r-0929-a","kind":"run","summary":"Run started","reason":"Scheduled 08:00 run","steps":[{"label":"config","detail":"r-0929-a.config.yaml"}]}
{"v":1,"id":"e-0929-a-040","ts":"2026-09-29T15:10:00Z","run_id":"r-0929-a","kind":"run","summary":"Run finished","reason":"PR cap reached","counts":{"repos":42,"policy_ok":17,"issues_kept":9,"claimed":4,"fixed":3,"prs":2}}
```

### Decision example

```json
{"v":1,"id":"e-0929-a-024","ts":"2026-09-29T12:15:00Z","run_id":"r-0929-a","kind":"decision","stage":"fix-issue","outcome":"skipped","summary":"Dropped vecstore-ai/embedkit#342","reason":"Baseline tests fail on main before any change, so a fix could not be verified.","subject":{"repo":"vecstore-ai/embedkit","issue":342},"tests":{"baseline":{"passed":112,"failed":3}}}
```

## Heartbeat

`health/heartbeat.json`, overwritten every 10 minutes while the agent is up:

```json
{"ts":"2026-09-29T14:52:00Z","run_id":"r-0929-a","stage":"follow-up","errors_24h":2}
```

The UI shows it as stale after 30 minutes. A scheduled GitHub Action checks the
same file and alerts on Telegram when it goes stale.
