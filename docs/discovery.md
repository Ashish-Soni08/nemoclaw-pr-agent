# Discovery: finding work with the Firecrawl Developer Index

Design for the build thread. Written 2026-10-01 from Firecrawl's docs
(docs.firecrawl.dev/features/developer and /api-reference/endpoint/developer-search).
The API could not be called from the design session (network blocked), so the
"verify at build" items at the end must be checked on the Lambda VM first.

## 1. The decision in one paragraph

Every run starts with Developer Index searches. They return **issues** (and
READMEs) from repos that match our filters, so the Index is both the repo source
and the issue source: the repo slug is inside every result id
(`issue:owner/repo#1234`). The Index does not return issue state, labels,
assignees or dates, so every hit is then checked live on the GitHub API before
it can become a candidate. The Index finds; GitHub confirms; triage ranks.
No GitHub search is used to find repos or issues.

## 2. What the Developer Index gives us

| Item | Detail |
|---|---|
| Endpoint | `POST https://api.firecrawl.dev/v2/search/developer` (GET also works) |
| Auth | `Authorization: Bearer $FIRECRAWL_API_KEY`. Keyless works at lower rate limits |
| Body | `query` (natural language, semantic search), `k` 1-100 (default 10), `types` of `issue`, `pull_request`, `readme`, `doc`, `passages` 1-5 |
| Repo filters | `language`, `topic` (one string), `license`, `min_stars`, `max_stars`, `archived`, `fork`, `repos` (list of slugs). Apply to issue/PR/readme types only |
| Result | `id` (`issue:owner/repo#N`), `type`, `url`, `title`, `passages[].text` (markdown) |
| Also returned | `coverage` per type (`ok`, `degraded`, `unavailable`, `skipped`), `repos[]` with `indexed` flags |
| Cost | 2 credits per 10 results, rounded up. Free plan 1,000 credits a month |
| Freshness | Most sources refreshed daily |
| Errors | 400 (bad filter combo, e.g. `repos` with only `doc`), 401, 429, 500 |
| Not given | Issue open/closed, labels, assignees, comment count, dates, stars of the hit |

The CLI (`firecrawl developer`) only exposes `--limit` and `--json`, and the MCP
tool hides credit accounting, so the agent calls the REST endpoint from a script.
That matches the repo rule that deterministic steps are scripts, not model
improvisation.

## 3. Where it sits in the agent

```
cron (Hermes) -> pr-agent-mode router
  -> discover-work      (this design: Index search + GitHub verify -> candidates.jsonl)
  -> check-ai-policy    (per new repo, cached)
  -> triage-issues      (Benny-style triage-issue-reports: take or skip, with reasons)
  -> claim-issue / fix-issue sub-agent (per lane)
```

Router line to add in `pr-agent-mode`: "Start of an autonomous run -> load
`discover-work`, then `check-ai-policy` for repos without a cached verdict, then
`triage-issues` on the candidates."

### Skill folder (pstack layout)

Rename the scaffold's `skills/discover-repos/` to `skills/discover-work/`,
since it now yields issues, not just repos.

```
skills/discover-work/
  SKILL.md                      # when to run, steps, what to log; tool skill (model-visible)
  references/query-bank.yaml    # the queries and filters below; editable without code changes
  scripts/devindex_search.py    # runs the query bank against the Index, enforces the credit cap
  scripts/verify_github.py      # live checks on each hit, writes candidates.jsonl
  scripts/seen.py               # read/write state/seen.tsv so runs don't repeat work
```

SKILL.md stays short: the agent runs the two scripts, reads the summary they
print, and only uses judgement on what the scripts can't decide (for example a
borderline "is anyone already working on this" comment).

## 4. One discovery run, step by step

### Step 1. Search the Index (devindex_search.py)

Run a rotating slice of the query bank. Each query is a POST with:

```json
{
  "query": "<from query bank>",
  "types": ["issue"],
  "k": 20,
  "passages": 2,
  "language": "Python",
  "topic": "<one focus topic this run>",
  "min_stars": 200,
  "max_stars": 30000,
  "archived": false,
  "fork": false
}
```

**Query bank** (`references/query-bank.yaml`), two axes:

- *Focus topics* (the AI and data-science filter): `machine-learning`,
  `deep-learning`, `data-science`, `llm`, `nlp`, `pandas`, `data-analysis`,
  `computer-vision`, `mlops`, `data-visualization`. The `topic` filter takes one
  value, so each query uses one topic. Each run takes the next 3 topics in the
  rotation (stored in `state/rotation.json`), so all topics are covered every
  few runs.
- *Issue shapes* (semantic queries that describe fixable work, bugs first):
  1. "bug report with steps to reproduce and a traceback, wrong result or exception"
  2. "regression after upgrading a dependency, error message included"
  3. "good first issue small fix, maintainers welcome contributions"
  4. "help wanted documented expected vs actual behaviour"

Per run: 3 topics x 2 shapes (the shapes also rotate) = 6 queries at k=20
= 24 credits. The star window avoids tiny dead repos and the giant ones where
newcomer PRs rarely land. Star bounds, language and k all live in the YAML.

Handling:
- `coverage.issue` is `degraded`: keep results, log it. `unavailable`: retry
  once after 30 s, then log and end the run with a Telegram notice. No fallback
  to GitHub search, because Ashish wants the Index used every time.
- 429: back off (5 s, 20 s), then skip that query and log it.
- Credit cap: the script refuses to spend more than `max_credits_per_run`
  (default 30) and `max_credits_per_month` (default 900, under the free 1,000),
  tracked in `state/firecrawl_credits.tsv`. Same idea as the HF usage guard.

Output: raw hits, deduped by `id`, with the matching passages and which query
found them.

### Step 2. Drop what we've already seen (seen.py)

`state/seen.tsv` keeps `issue_id, first_seen, last_stage, last_verdict, recheck_after`.
Skip any hit whose `recheck_after` is in the future (default 14 days after a
skip, never for issues we already claimed or opened a PR for). This keeps each
cron run idempotent (principle-make-operations-idempotent).

### Step 3. Verify live on GitHub (verify_github.py)

For each new hit, with `GITHUB_TOKEN`, cheapest checks first, stop at the first fail:

| Check | API call | Pass when |
|---|---|---|
| Repo alive | `GET /repos/{o}/{r}` (cached per run) | not archived, `has_issues`, pushed in last 60 days, has an OSI license |
| Issue open | `GET /repos/{o}/{r}/issues/{n}` | `state=open`, not a pull request, not locked, no assignee |
| Fresh | same | updated in last 180 days |
| No one on it | `GET .../issues/{n}/timeline` | no cross-referenced open PR; no "I'll take this / working on it" comment in the last 30 days (simple regex in the script; ambiguous ones flagged for the model) |
| Kind | labels + title | bug-like (bug, regression, error, crash) unless config widens issue scope |

Per-run cap of 40 hits verified keeps us well inside GitHub's 5,000 requests an hour.

### Step 4. Add Index-based signals (still discover-work)

For the survivors only (at most 8 per run), one more Index query each,
scoped to the repo:

```json
{"query": "<issue title>", "types": ["pull_request"], "repos": ["owner/repo"], "k": 10}
```

That costs 2 credits each (16 max) and gives two things:
- **Already fixed?** A merged PR whose passages describe the same fix means
  skip, with the PR URL as evidence.
- **Precedent.** The closest merged PRs are attached to the candidate as
  examples of how this repo likes fixes and tests written. fix-issue reads them.

To stay under the 30-credit run cap, step 1 drops to 5 queries on a run where
step 4 needs the room. The script plans the split before spending.

### Step 5. Write candidates.jsonl

One line per surviving issue, handed to check-ai-policy and triage:

```json
{
  "issue_id": "issue:owner/repo#1234",
  "url": "https://github.com/owner/repo/issues/1234",
  "repo": "owner/repo",
  "title": "...",
  "found_by": {"query": "...", "topic": "pandas"},
  "passages": ["..."],
  "github": {"labels": ["bug", "good first issue"], "comments": 3,
             "created_at": "...", "updated_at": "...", "stars": 1840},
  "precedent_prs": ["https://github.com/owner/repo/pull/1180"],
  "lane_hint": "go-directly"
}
```

`lane_hint`: `ask-first` when labelled needs-triage, needs-discussion, design,
RFC, proposal or question; otherwise `go-directly`. check-ai-policy overrides it to `ask-first` when the
repo's CONTRIBUTING asks contributors to claim issues, and drops the repo when
the policy bans AI contributions.

## 5. AI-policy check gets one Index assist

check-ai-policy still reads CONTRIBUTING, PR templates and AI policy files
from GitHub. For repos with no written policy (`unclear`), it spends one Index
query to look for the maintainers' stance in past discussion:

```json
{"query": "policy on AI generated or LLM written pull requests", "types": ["issue", "pull_request"], "repos": ["owner/repo"], "k": 10}
```

A maintainer comment rejecting AI PRs turns `unclear` into `bans`; anything
else stays `unclear` (unclear repos continue while `continue_on_unclear_policy` is on; see docs/design.md).
Verdicts are cached per repo, so this runs once per repo.

## 6. What gets logged (decisions.tsv via show-me-your-work)

Use show-me-your-work's columns. Rows discovery writes:

| Stage | Subject | Decision / result | Evidence |
|---|---|---|---|
| discover.query | the query + filters | N hits, credits spent, coverage | query hash, coverage object |
| discover.seen | issue id | skipped: seen on DATE | seen.tsv row |
| discover.verify | issue id | kept / dropped: reason (closed, assigned, open PR #, stale, archived repo...) | GitHub URL of the fact |
| discover.precedent | issue id | already fixed / precedent found / none | PR URLs |
| discover.summary | run id | hits, verified, candidates, credits used today and this month | candidates.jsonl path |

A human can read any candidate back to the exact query that found it and the
GitHub fact that kept or dropped it.

## 7. Config (in query-bank.yaml, not code)

```yaml
language: Python
min_stars: 200
max_stars: 30000
topics_per_run: 3
shapes_per_run: 2
k: 20
max_verify_per_run: 40
max_candidates_per_run: 8
max_credits_per_run: 30
max_credits_per_month: 900
recheck_after_days: 14
issue_scope: bugs   # open decision; widen to "bugs+small-features" if Ashish says so
```

Network allowlist needs `api.firecrawl.dev` (policies/ already plans "Firecrawl").
Key: `FIRECRAWL_API_KEY` from `.env` on the VM, already in `.env.example`.

## 8. Verify at build, before writing the skill

These come from the docs and could not be tested from here:
1. A real call from the VM returns issue hits with the filters above, and the
   `id` format is `issue:owner/repo#N` as documented.
2. Whether closed issues come back (expected yes; GitHub verify handles it either way).
3. The `topic` filter matches GitHub topic slugs exactly (try `pandas`, `llm`).
4. Credits charged match 2 per 10 results with a key; whether keyless calls spend credits.
5. Hit rate: how many of 120 hits per run survive GitHub verify. If it's under
   ~10%, raise k or loosen the star window before adding queries.
