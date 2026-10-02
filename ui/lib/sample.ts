// Sample ledger shown when LEDGER_DATASET is unset. Bundled as code so it loads
// regardless of the server's working directory.
export const SAMPLE: Record<string, string> = {
  "decisions.tsv": `ts	run	phase	subject	decision	why	evidence	result
2026-09-29T08:00:02Z	r-0929-a	start	r-0929-a	started scheduled run	cron tick	host=lambda-a10	open
2026-09-29T08:00:09Z	r-0929-a	guard	usage	skipped run	Firecrawl per-run backstop already reached by a retry loop	state.db	skipped
2026-09-29T14:00:03Z	r-0929-b	start	r-0929-b	started scheduled run	cron tick	host=lambda-a10	open
2026-09-29T14:01:11Z	r-0929-b	discover.query	ml bugs good first issue	searched issues	topic=ml	q=77aa	ok
2026-09-29T14:02:40Z	r-0929-b	discover.verify	plotwise/plotwise#80	kept	live GitHub check	https://github.com/plotwise/plotwise/issues/80	kept
2026-09-29T14:03:55Z	r-0929-b	fix.workspace	plotwise/plotwise#80	prepared workspace	base main@19ac0b2e4d	/sandbox/work/plotwise-80	ready
2026-09-30T08:00:04Z	r-0930-a	start	r-0930-a	started scheduled run	cron tick	host=lambda-a10	open
2026-09-30T08:01:12Z	r-0930-a	discover.query	ml bugs good first issue	searched issues	topic=ml	q=4f1a	ok
2026-09-30T08:03:40Z	r-0930-a	discover.verify	tabular-labs/frameframe#1188	kept	live GitHub check	https://github.com/tabular-labs/frameframe/issues/1188	kept
2026-09-30T08:03:52Z	r-0930-a	discover.verify	quantlab/qframe#501	dropped: claimed	live GitHub check	https://github.com/quantlab/qframe/issues/501	dropped
2026-09-30T08:04:10Z	r-0930-a	discover.verify	vecstore-ai/embedkit#331	dropped: has open PR	live GitHub check	https://github.com/vecstore-ai/embedkit/pull/335	dropped
2026-09-30T08:05:02Z	r-0930-a	policy	tabular-labs/frameframe	AI policy allows-with-disclosure	disclose: AI-assisted pull requests are welcome if the description says which tool was used.	CONTRIBUTING.md	allows-with-disclosure
2026-09-30T08:06:30Z	r-0930-a	triage	tabular-labs/frameframe#1188	take (bug; bug-fix)	Maintainer confirmed the bug and described the expected output; small, one function.	https://github.com/tabular-labs/frameframe/issues/1188	take
2026-09-30T08:40:00Z	r-0930-a	fix.workspace	tabular-labs/frameframe#1188	prepared workspace	base main@a91c0e33f2	/sandbox/work/frameframe-1188	ready
2026-09-30T08:44:10Z	r-0930-a	fix.test.baseline	tabular-labs/frameframe#1188	ran pytest -q	baseline run	57 passed in 41s	exit 0
2026-09-30T09:20:31Z	r-0930-a	fix.test.after	tabular-labs/frameframe#1188	ran pytest -q	after run	58 passed in 43s (+1 test_read_csv_empty_header)	exit 0
2026-09-30T09:22:02Z	r-0930-a	gate	tabular-labs/frameframe#1188	self-review gate pass	diff is minimal, new test covers the reported input	diff 7c21e0	pass
2026-09-30T09:23:15Z	r-0930-a	pr.opened	tabular-labs/frameframe#1188	opened tabular-labs/frameframe#1207	self-review gate passed on this diff	https://github.com/tabular-labs/frameframe/pull/1207	open
2026-09-30T09:24:00Z	r-0930-a	run.end	r-0930-a	sent run summary	end of run	telegram	done
2026-10-01T08:00:03Z	r-1001-a	start	r-1001-a	started scheduled run	cron tick	host=lambda-a10	open
2026-10-01T08:01:20Z	r-1001-a	discover.query	pandas dtype bug	searched issues	topic=data	q=9b22	ok
2026-10-01T08:01:58Z	r-1001-a	discover.query	jupyter widget regression	searched issues	topic=notebooks	q=1c07	ok
2026-10-01T08:02:30Z	r-1001-a	discover.query	plotting axis label	skipped query	keep 6 credits for precedent checks	topic=viz	skipped
2026-10-01T08:04:11Z	r-1001-a	discover.verify	plotwise/plotwise#88	kept	live GitHub check	https://github.com/plotwise/plotwise/issues/88	kept
2026-10-01T08:04:20Z	r-1001-a	discover.verify	vecstore-ai/embedkit#342	kept	live GitHub check	https://github.com/vecstore-ai/embedkit/issues/342	kept
2026-10-01T08:04:31Z	r-1001-a	discover.verify	neuronote/neuronote#77	kept	live GitHub check	https://github.com/neuronote/neuronote/issues/77	kept
2026-10-01T08:04:40Z	r-1001-a	discover.verify	gridstat/gridstat#14	dropped: closed	live GitHub check	https://github.com/gridstat/gridstat/issues/14	dropped
2026-10-01T08:04:49Z	r-1001-a	discover.verify	quantlab/qframe#512	dropped: assigned	live GitHub check	https://github.com/quantlab/qframe/issues/512	dropped
2026-10-01T08:05:02Z	r-1001-a	discover.seen	tabular-labs/frameframe#1188	skipped: seen on 2026-09-30	take	state/seen.tsv	skipped
2026-10-01T08:06:10Z	r-1001-a	discover.precedent	vecstore-ai/embedkit#342	2 precedent PRs	examples of how this repo writes fixes	https://github.com/vecstore-ai/embedkit/pull/301 https://github.com/vecstore-ai/embedkit/pull/318	precedent found
2026-10-01T08:06:44Z	r-1001-a	discover.summary	r-1001-a	9 hits, 3 kept	2 dropped on GitHub check, 1 already seen	runs/r-1001-a/candidates.jsonl	3 candidates
2026-10-01T08:07:30Z	r-1001-a	policy	plotwise/plotwise	AI policy allows	allow: We welcome contributions from humans and tools alike.	CONTRIBUTING.md	allows
2026-10-01T08:07:52Z	r-1001-a	policy	vecstore-ai/embedkit	AI policy allows	allow: No restrictions on tooling; all PRs must pass CI.	CONTRIBUTING.md	allows
2026-10-01T08:08:15Z	r-1001-a	policy	neuronote/neuronote	AI policy bans	ban: We do not accept pull requests generated by AI tools.	AI_POLICY.md	bans
2026-10-01T08:08:40Z	r-1001-a	policy	quantlab/qframe	AI policy unclear	no AI policy text found	CONTRIBUTING.md, .github/PULL_REQUEST_TEMPLATE.md	unclear
2026-10-01T08:10:02Z	r-1001-a	triage	neuronote/neuronote#77	skip (-; -)	Repo policy bans AI-generated contributions.	https://github.com/neuronote/neuronote/issues/77	skip
2026-10-01T08:10:40Z	r-1001-a	triage	plotwise/plotwise#88	take (docs; bug-fix)	Clear repro and a maintainer reply; repo asks contributors to claim first.	https://github.com/plotwise/plotwise/issues/88	take
2026-10-01T08:11:15Z	r-1001-a	triage	vecstore-ai/embedkit#342	take (bug; bug-fix)	Clear repro steps, small scope, two precedent fixes to follow.	https://github.com/vecstore-ai/embedkit/issues/342	take
2026-10-01T08:12:00Z	r-1001-a	claim.posted	plotwise/plotwise#88	asked maintainers to take the issue	repo expects contributors to ask first	https://github.com/plotwise/plotwise/issues/88#issuecomment-2391	waiting
2026-10-01T08:30:12Z	r-1001-a	fix.workspace	vecstore-ai/embedkit#342	prepared workspace	base main@3d0b9a1c77	/sandbox/work/embedkit-342	ready
2026-10-01T08:36:40Z	r-1001-a	fix.setup	vecstore-ai/embedkit#342	installed the project	installed=True	/sandbox/work/embedkit-342	ok
2026-10-01T08:41:55Z	r-1001-a	fix.test.baseline	vecstore-ai/embedkit#342	ran pytest -q	baseline run	112 passed, 3 failed (test_faiss_backend)	exit 1
2026-10-01T08:42:30Z	r-1001-a	fix.abandoned	vecstore-ai/embedkit#342	dropped the fix	Baseline tests fail on main before any change, so a fix could not be verified.	3 failures in test_faiss_backend	abandoned
2026-10-01T10:41:07Z	r-1001-a	discover.error	r-1001-a	retried HF router call	TimeoutError: inference router did not answer in 60s		error
2026-10-01T12:03:22Z	r-1001-a	follow-up.reply	tabular-labs/frameframe#1207	replied on tabular-labs/frameframe#1207	Thanks, added a test for the empty-input case you asked about.	https://github.com/tabular-labs/frameframe/pull/1207#issuecomment-88213	posted
2026-10-01T12:20:45Z	r-1001-a	follow-up.push	tabular-labs/frameframe#1207	pushed review fixes	test: cover empty header input	a3f91c0	pushed
2026-10-01T12:21:30Z	r-1001-a	run.end	r-1001-a	sent run summary	end of run	telegram	done
2026-10-01T14:00:02Z	r-1001-b	start	r-1001-b	started scheduled run	cron tick	host=lambda-a10	open
2026-10-01T14:00:40Z	r-1001-b	discover.query	sklearn pipeline warning	searched issues	topic=ml	q=e310	ok
2026-10-01T14:01:30Z	r-1001-b	discover.verify	tabular-labs/frameframe#1215	kept	live GitHub check	https://github.com/tabular-labs/frameframe/issues/1215	kept
2026-10-01T14:02:05Z	r-1001-b	triage	tabular-labs/frameframe#1215	take (bug; bug-fix)	Unassigned, maintainer labelled good-first-issue with the expected fix.	https://github.com/tabular-labs/frameframe/issues/1215	take
2026-10-01T14:20:10Z	r-1001-b	fix.test.baseline	tabular-labs/frameframe#1215	ran pytest -q	baseline run	58 passed in 42s	exit 0
2026-10-01T14:46:55Z	r-1001-b	fix.test.after	tabular-labs/frameframe#1215	ran pytest -q	after run	60 passed in 44s (+2)	exit 0
2026-10-01T14:48:01Z	r-1001-b	gate	tabular-labs/frameframe#1215	self-review gate pass	change limited to the dtype check; tests cover both paths	diff 91be04	pass
2026-10-01T14:49:12Z	r-1001-b	pr.opened	tabular-labs/frameframe#1215	opened tabular-labs/frameframe#1219	self-review gate passed on this diff	https://github.com/tabular-labs/frameframe/pull/1219	open
2026-10-01T15:05:40Z	r-1001-b	pr.outcome	tabular-labs/frameframe#1188	merged tabular-labs/frameframe#1207	maintainer merged after review	https://github.com/tabular-labs/frameframe/pull/1207	merged
2026-10-01T15:20:10Z	r-1001-b	triage	gridstat/gridstat#21	take (bug; bug-fix)	Repro in the issue; fix touches one function.	https://github.com/gridstat/gridstat/issues/21	take
2026-10-01T15:41:30Z	r-1001-b	fix.test.after	gridstat/gridstat#21	ran pytest -q	after run	41 passed in 12s	exit 0
2026-10-01T15:43:02Z	r-1001-b	gate	gridstat/gridstat#21	self-review gate fail	diff also reformats 3 unrelated files; the new test does not fail before the fix	diff 5aa0c2	fail
2026-10-01T15:43:20Z	r-1001-b	pr.refused	gridstat/gridstat#21	did not open PR	self-review gate failed	/sandbox/work/gridstat-21	refused
`,
  "spend.tsv": `ts	provider	used	unit	cost_usd	remaining	limit	source
2026-09-25T20:00:00Z	huggingface	2.1	usd	2.1	397.9	400	estimate:hermes-state.db x menu prices (month to date)
2026-09-25T20:00:00Z	firecrawl	180	credits	0	69820	70000	local:firecrawl_credits.tsv (month to date)
2026-09-25T20:00:00Z	lambda	0	hours	0	500	500	estimate:uptime x hourly rate (all boots)
2026-09-26T20:00:00Z	huggingface	6.85	usd	6.85	393.15	400	estimate:hermes-state.db x menu prices (month to date)
2026-09-26T20:00:00Z	firecrawl	610	credits	0	69390	70000	local:firecrawl_credits.tsv (month to date)
2026-09-26T20:00:00Z	lambda	0	hours	0	500	500	estimate:uptime x hourly rate (all boots)
2026-09-27T20:00:00Z	huggingface	13.4	usd	13.4	386.6	400	estimate:hermes-state.db x menu prices (month to date)
2026-09-27T20:00:00Z	firecrawl	1020	credits	0	68980	70000	local:firecrawl_credits.tsv (month to date)
2026-09-27T20:00:00Z	lambda	0	hours	0	500	500	estimate:uptime x hourly rate (all boots)
2026-09-28T20:00:00Z	huggingface	19	usd	19	381	400	estimate:hermes-state.db x menu prices (month to date)
2026-09-28T20:00:00Z	firecrawl	1490	credits	0	68510	70000	local:firecrawl_credits.tsv (month to date)
2026-09-28T20:00:00Z	lambda	1	hours	1.29	498.71	500	estimate:uptime x hourly rate (all boots)
2026-09-29T20:00:00Z	huggingface	29.2	usd	29.2	370.8	400	estimate:hermes-state.db x menu prices (month to date)
2026-09-29T20:00:00Z	firecrawl	2210	credits	0	67790	70000	local:firecrawl_credits.tsv (month to date)
2026-09-29T20:00:00Z	lambda	9.5	hours	12.255	487.745	500	estimate:uptime x hourly rate (all boots)
2026-09-30T09:24:00Z	huggingface	38.6	usd	38.6	361.4	400	estimate:hermes-state.db x menu prices (month to date)
2026-09-30T09:24:00Z	firecrawl	2840	credits	0	67160	70000	local:firecrawl_credits.tsv (month to date)
2026-09-30T09:24:00Z	lambda	17	hours	21.93	478.07	500	estimate:uptime x hourly rate (all boots)
2026-10-01T12:21:30Z	huggingface	4.05	usd	4.05	395.95	400	estimate:hermes-state.db x menu prices (month to date)
2026-10-01T12:21:30Z	firecrawl	520	credits	0	69480	70000	api:/v2/team/credit-usage (remaining); local (used)
2026-10-01T12:21:30Z	lambda	26.5	hours	34.185	465.815	500	estimate:uptime x hourly rate (all boots)
2026-10-01T14:49:12Z	huggingface	6.45	usd	6.45	393.55	400	estimate:hermes-state.db x menu prices (month to date)
2026-10-01T14:49:12Z	firecrawl	830	credits	0	69170	70000	api:/v2/team/credit-usage (remaining); local (used)
2026-10-01T14:49:12Z	lambda	29	hours	37.41	462.59	500	estimate:uptime x hourly rate (all boots)
`,
  "tokens.tsv": `ts	run	subject	step	model	tokens_in	tokens_out	cost_usd
2026-09-29T14:03:55Z	r-0929-b	plotwise/plotwise#80	triage	nvidia/Nemotron-Super-49B	182400	9100	0.21
2026-09-30T08:06:30Z	r-0930-a	tabular-labs/frameframe#1188	triage	nvidia/Nemotron-Super-49B	52000	3000	0.06
2026-09-30T09:20:31Z	r-0930-a	tabular-labs/frameframe#1188	fix	Qwen/Qwen3-Coder-30B	1400000	80000	1.53
2026-09-30T09:22:02Z	r-0930-a	tabular-labs/frameframe#1188	gate	nvidia/Nemotron-Super-49B	200000	10000	0.24
2026-09-30T09:24:00Z	r-0930-a	-	discover	nvidia/Nemotron-Super-49B	1168000	48000	1.32
2026-09-30T09:24:00Z	r-0930-a	-	summary	nvidia/Nemotron-Nano-9B	640000	22000	0.11
2026-10-01T08:11:15Z	r-1001-a	vecstore-ai/embedkit#342	triage	nvidia/Nemotron-Super-49B	58000	3000	0.07
2026-10-01T08:42:30Z	r-1001-a	vecstore-ai/embedkit#342	fix	Qwen/Qwen3-Coder-30B	610000	31000	0.64
2026-10-01T12:21:30Z	r-1001-a	-	discover	nvidia/Nemotron-Super-49B	1122000	44000	1.27
2026-10-01T12:21:30Z	r-1001-a	-	follow-up	Qwen/Qwen3-Coder-30B	1150000	60000	1.22
2026-10-01T12:21:30Z	r-1001-a	-	summary	nvidia/Nemotron-Nano-9B	820000	30000	0.14
2026-10-01T14:02:05Z	r-1001-b	tabular-labs/frameframe#1215	triage	nvidia/Nemotron-Super-49B	60000	2000	0.07
2026-10-01T14:46:55Z	r-1001-b	tabular-labs/frameframe#1215	fix	Qwen/Qwen3-Coder-30B	1150000	60000	1.21
2026-10-01T14:48:01Z	r-1001-b	tabular-labs/frameframe#1215	gate	nvidia/Nemotron-Super-49B	172000	8000	0.21
2026-10-01T15:20:10Z	r-1001-b	gridstat/gridstat#21	triage	nvidia/Nemotron-Super-49B	46000	2000	0.05
2026-10-01T15:41:30Z	r-1001-b	gridstat/gridstat#21	fix	Qwen/Qwen3-Coder-30B	900000	44000	0.96
2026-10-01T15:43:02Z	r-1001-b	gridstat/gridstat#21	gate	nvidia/Nemotron-Super-49B	144000	6000	0.17
2026-10-01T15:43:20Z	r-1001-b	-	discover	nvidia/Nemotron-Super-49B	538000	22000	0.59
2026-10-01T15:43:20Z	r-1001-b	-	summary	nvidia/Nemotron-Nano-9B	410000	15000	0.07
`,
  "run_config.tsv": `run	key	value
r-0929-a	config	config/agent.yaml @ 1cdac1f
r-0929-a	model.triage	nvidia/Nemotron-Super-49B
r-0929-a	model.fix	Qwen/Qwen3-Coder-30B
r-0929-a	model.gate	nvidia/Nemotron-Super-49B
r-0929-a	model.summary	nvidia/Nemotron-Nano-9B
r-0929-a	firecrawl.per_run_credits	1000
r-0929-a	schedule	every 6 h
r-0929-b	config	config/agent.yaml @ 1cdac1f
r-0929-b	model.triage	nvidia/Nemotron-Super-49B
r-0929-b	model.fix	Qwen/Qwen3-Coder-30B
r-0929-b	model.gate	nvidia/Nemotron-Super-49B
r-0929-b	model.summary	nvidia/Nemotron-Nano-9B
r-0929-b	firecrawl.per_run_credits	1000
r-0929-b	schedule	every 6 h
r-0930-a	config	config/agent.yaml @ 1cdac1f
r-0930-a	model.triage	nvidia/Nemotron-Super-49B
r-0930-a	model.fix	Qwen/Qwen3-Coder-30B
r-0930-a	model.gate	nvidia/Nemotron-Super-49B
r-0930-a	model.summary	nvidia/Nemotron-Nano-9B
r-0930-a	firecrawl.per_run_credits	1000
r-0930-a	schedule	every 6 h
r-1001-a	config	config/agent.yaml @ 9dcc1c7
r-1001-a	model.triage	nvidia/Nemotron-Super-49B
r-1001-a	model.fix	Qwen/Qwen3-Coder-30B
r-1001-a	model.gate	nvidia/Nemotron-Super-49B
r-1001-a	model.summary	nvidia/Nemotron-Nano-9B
r-1001-a	firecrawl.per_run_credits	1000
r-1001-a	schedule	every 6 h
r-1001-b	config	config/agent.yaml @ 9dcc1c7
r-1001-b	model.triage	nvidia/Nemotron-Super-49B
r-1001-b	model.fix	Qwen/Qwen3-Coder-30B
r-1001-b	model.gate	nvidia/Nemotron-Super-49B
r-1001-b	model.summary	nvidia/Nemotron-Nano-9B
r-1001-b	firecrawl.per_run_credits	1000
r-1001-b	schedule	every 6 h
`,
};
