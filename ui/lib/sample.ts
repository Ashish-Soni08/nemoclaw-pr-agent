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
2026-10-01T14:49:12Z	lambda	29	hours	37.41	462.59	500	estimate:wall-clock since launch x hourly rate; nemoclaw-agent-challenge running since 2026-09-28 19:00 UTC
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
  "host.tsv": `ts	run	cpu_pct	load1	ram_used_gb	ram_total_gb	gpu_util_pct	vram_used_gb	vram_total_gb	disk_used_gb	disk_total_gb	agent_cpu_cores	agent_ram_gb	agent_vram_gb	agent_disk_gb
2026-10-01T09:43:00Z	r-1001-a	6.7	2.02	11.8	222	41	6.5	23	40.4	1400	1.72	2.4	6.5	5.8
2026-10-01T09:45:00Z	r-1001-a	8.5	2.56	11.8	222	16	6.1	23	40.4	1400	2.18	2.4	6.1	5.8
2026-10-01T09:47:00Z	r-1001-a	8.4	2.52	9.7	222	19	6.1	23	40.4	1400	2.14	2.3	6.1	5.8
2026-10-01T09:49:00Z	r-1001-a	6.4	1.93	9.8	222	15	5.8	23	40.4	1400	1.64	2.5	5.8	5.8
2026-10-01T09:51:00Z	r-1001-a	7.6	2.28	9.4	222	21	6.5	23	40.4	1400	1.94	2.4	6.5	5.8
2026-10-01T09:53:00Z	r-1001-a	3.8	1.13	9.6	222	15	6.5	23	40.4	1400	0.96	2.1	6.5	5.8
2026-10-01T09:55:00Z	r-1001-a	8.9	2.67	11.9	222	46	5.8	23	40.4	1400	2.27	2.3	5.8	5.8
2026-10-01T09:57:00Z	r-1001-a	7.1	2.12	11.1	222	22	6.6	23	40.4	1400	1.80	2.6	6.6	5.8
2026-10-01T09:59:00Z	r-1001-a	8.4	2.51	9.5	222	25	5.9	23	40.4	1400	2.13	2.1	5.9	5.8
2026-10-01T10:01:00Z	r-1001-a	3.4	1.02	9.0	222	26	6.2	23	40.4	1400	0.86	2.4	6.2	5.8
2026-10-01T10:03:00Z	r-1001-a	5.0	1.51	10.4	222	26	6.5	23	40.4	1400	1.28	2.2	6.5	5.8
2026-10-01T10:05:00Z	r-1001-a	5.9	1.77	11.9	222	40	5.6	23	40.4	1400	1.50	2.0	5.6	5.8
2026-10-01T10:07:00Z	r-1001-a	7.5	2.25	11.4	222	45	5.5	23	40.4	1400	1.91	2.2	5.5	5.8
2026-10-01T10:09:00Z	r-1001-a	6.5	1.94	9.5	222	15	5.6	23	40.4	1400	1.65	2.6	5.6	5.8
2026-10-01T10:11:00Z	r-1001-a	4.2	1.25	11.8	222	41	6.6	23	40.4	1400	1.07	2.2	6.6	5.8
2026-10-01T10:13:00Z	r-1001-a	5.1	1.54	9.3	222	33	6.4	23	40.4	1400	1.31	2.4	6.4	5.8
2026-10-01T10:15:00Z	r-1001-a	7.8	2.34	11.8	222	45	5.5	23	40.4	1400	1.98	2.1	5.5	5.8
2026-10-01T10:17:00Z	r-1001-a	5.0	1.51	10.0	222	36	6.6	23	40.5	1400	1.29	2.6	6.6	5.8
2026-10-01T10:19:00Z	r-1001-a	6.3	1.88	9.5	222	26	5.9	23	40.5	1400	1.60	2.0	5.9	5.8
2026-10-01T10:21:00Z	r-1001-a	3.9	1.17	9.5	222	39	6.7	23	40.5	1400	0.99	2.0	6.7	5.8
2026-10-01T10:23:00Z	r-1001-a	8.9	2.68	9.7	222	34	6.0	23	40.5	1400	2.27	2.4	6.0	5.8
2026-10-01T10:25:00Z	r-1001-a	8.0	2.39	9.2	222	31	6.0	23	40.5	1400	2.03	2.5	6.0	5.8
2026-10-01T10:27:00Z	r-1001-a	3.2	0.96	9.4	222	32	6.5	23	40.5	1400	0.82	2.4	6.5	5.8
2026-10-01T10:29:00Z	r-1001-a	8.7	2.61	9.3	222	37	6.4	23	40.5	1400	2.22	2.3	6.4	5.8
2026-10-01T10:31:00Z	r-1001-a	3.9	1.17	10.4	222	45	5.9	23	40.5	1400	0.99	2.6	5.9	5.8
2026-10-01T10:33:00Z	r-1001-a	8.1	2.43	10.5	222	49	6.0	23	40.5	1400	2.07	2.4	6.0	5.8
2026-10-01T10:35:00Z	r-1001-a	5.9	1.76	9.4	222	25	6.0	23	40.5	1400	1.50	2.2	6.0	5.9
2026-10-01T10:37:00Z	r-1001-a	8.9	2.68	10.5	222	49	6.3	23	40.5	1400	2.28	2.2	6.3	5.9
2026-10-01T10:39:00Z	r-1001-a	3.5	1.06	11.6	222	25	6.4	23	40.5	1400	0.90	2.2	6.4	5.9
2026-10-01T10:41:00Z	r-1001-a	7.7	2.31	11.0	222	42	6.3	23	40.5	1400	1.97	2.5	6.3	5.9
2026-10-01T10:43:00Z	r-1001-a	5.2	1.55	10.5	222	40	5.8	23	40.5	1400	1.32	2.5	5.8	5.9
2026-10-01T10:45:00Z	r-1001-a	7.1	2.14	10.9	222	25	6.6	23	40.5	1400	1.82	2.3	6.6	5.9
2026-10-01T10:47:00Z	r-1001-a	3.1	0.92	11.0	222	34	5.8	23	40.5	1400	0.78	2.3	5.8	5.9
2026-10-01T10:49:00Z	r-1001-a	7.9	2.37	10.0	222	38	6.5	23	40.5	1400	2.01	2.4	6.5	5.9
2026-10-01T10:51:00Z	r-1001-a	7.4	2.23	11.5	222	44	5.9	23	40.5	1400	1.89	2.5	5.9	5.9
2026-10-01T10:53:00Z	r-1001-a	7.1	2.14	10.6	222	49	6.6	23	40.5	1400	1.82	2.3	6.6	5.9
2026-10-01T10:55:00Z	r-1001-a	4.0	1.20	10.4	222	44	6.6	23	40.5	1400	1.02	2.4	6.6	5.9
2026-10-01T10:57:00Z	r-1001-a	7.3	2.20	11.3	222	41	5.7	23	40.5	1400	1.87	2.3	5.7	5.9
2026-10-01T10:59:00Z	r-1001-a	7.0	2.10	11.3	222	30	6.2	23	40.5	1400	1.78	2.4	6.2	5.9
2026-10-01T11:01:00Z	r-1001-a	7.3	2.20	10.3	222	16	5.7	23	40.5	1400	1.87	2.4	5.7	5.9
2026-10-01T11:03:00Z	r-1001-a	4.3	1.29	9.1	222	39	6.3	23	40.5	1400	1.10	2.3	6.3	5.9
2026-10-01T11:05:00Z	r-1001-a	4.4	1.31	10.0	222	17	5.7	23	40.5	1400	1.11	2.1	5.7	5.9
2026-10-01T11:07:00Z	r-1001-a	4.2	1.25	10.1	222	16	6.1	23	40.5	1400	1.06	2.4	6.1	5.9
2026-10-01T11:09:00Z	r-1001-a	6.5	1.96	9.0	222	23	6.6	23	40.5	1400	1.67	2.2	6.6	5.9
2026-10-01T11:11:00Z	r-1001-a	4.7	1.40	11.5	222	29	5.6	23	40.5	1400	1.19	2.2	5.6	5.9
2026-10-01T11:13:00Z	r-1001-a	3.2	0.96	10.6	222	36	5.6	23	40.5	1400	0.82	2.2	5.6	5.9
2026-10-01T11:15:00Z	r-1001-a	6.5	1.95	10.3	222	49	6.5	23	40.5	1400	1.65	2.5	6.5	5.9
2026-10-01T11:17:00Z	r-1001-a	6.9	2.06	10.8	222	28	5.7	23	40.5	1400	1.75	2.3	5.7	5.9
2026-10-01T11:19:00Z	r-1001-a	8.7	2.62	10.1	222	49	6.2	23	40.5	1400	2.23	2.5	6.2	5.9
2026-10-01T11:21:00Z	r-1001-a	3.0	0.90	10.8	222	19	6.2	23	40.5	1400	0.77	2.1	6.2	5.9
2026-10-01T11:23:00Z	r-1001-a	6.8	2.03	10.3	222	46	6.0	23	40.5	1400	1.73	2.1	6.0	5.9
2026-10-01T11:25:00Z	r-1001-a	4.7	1.42	11.9	222	49	6.0	23	40.6	1400	1.21	2.5	6.0	5.9
2026-10-01T11:27:00Z	r-1001-a	6.6	1.97	10.5	222	24	6.7	23	40.6	1400	1.68	2.2	6.7	5.9
2026-10-01T11:29:00Z	r-1001-a	4.9	1.47	9.9	222	49	6.1	23	40.6	1400	1.25	2.3	6.1	5.9
2026-10-01T11:31:00Z	r-1001-a	3.7	1.12	9.9	222	37	6.0	23	40.6	1400	0.95	2.5	6.0	5.9
2026-10-01T11:33:00Z	r-1001-a	8.0	2.39	9.8	222	15	6.1	23	40.6	1400	2.03	2.6	6.1	5.9
2026-10-01T11:35:00Z	r-1001-a	7.7	2.31	9.5	222	24	5.8	23	40.6	1400	1.96	2.6	5.8	5.9
2026-10-01T11:37:00Z	r-1001-a	4.8	1.43	10.9	222	36	6.1	23	40.6	1400	1.21	2.4	6.1	5.9
2026-10-01T11:39:00Z	r-1001-a	7.5	2.24	9.9	222	19	6.4	23	40.6	1400	1.90	2.3	6.4	5.9
2026-10-01T11:41:00Z	r-1001-a	5.0	1.51	10.4	222	25	6.1	23	40.6	1400	1.28	2.2	6.1	5.9
2026-10-01T11:43:00Z	r-1001-a	7.5	2.24	9.8	222	36	5.5	23	40.6	1400	1.90	2.3	5.5	5.9
2026-10-01T11:45:00Z	r-1001-a	8.5	2.55	9.0	222	46	6.2	23	40.6	1400	2.17	2.5	6.2	5.9
2026-10-01T11:47:00Z	r-1001-a	5.6	1.67	10.9	222	35	6.3	23	40.6	1400	1.42	2.3	6.3	5.9
2026-10-01T11:49:00Z	r-1001-a	8.5	2.54	11.6	222	28	6.0	23	40.6	1400	2.16	2.1	6.0	5.9
2026-10-01T11:51:00Z	r-1001-a	4.8	1.43	11.5	222	44	5.6	23	40.6	1400	1.22	2.4	5.6	5.9
2026-10-01T11:53:00Z	r-1001-a	5.6	1.68	11.7	222	25	6.4	23	40.6	1400	1.43	2.1	6.4	5.9
2026-10-01T11:55:00Z	r-1001-a	5.9	1.76	10.0	222	34	6.1	23	40.6	1400	1.50	2.1	6.1	5.9
2026-10-01T11:57:00Z	r-1001-a	6.5	1.95	9.7	222	43	5.6	23	40.6	1400	1.66	2.5	5.6	5.9
2026-10-01T11:59:00Z	r-1001-a	7.8	2.33	11.2	222	38	5.5	23	40.6	1400	1.98	2.6	5.5	5.9
2026-10-01T12:01:00Z	r-1001-a	9.0	2.70	11.5	222	40	5.6	23	40.6	1400	2.29	2.1	5.6	5.9
2026-10-01T12:03:00Z	r-1001-a	6.9	2.06	9.4	222	48	6.4	23	40.6	1400	1.75	2.2	6.4	5.9
2026-10-01T12:05:00Z	r-1001-a	8.5	2.55	10.2	222	20	6.2	23	40.6	1400	2.17	2.1	6.2	5.9
2026-10-01T12:07:00Z	r-1001-a	6.7	2.02	10.1	222	17	5.6	23	40.6	1400	1.72	2.0	5.6	5.9
2026-10-01T12:09:00Z	r-1001-a	3.3	1.00	11.6	222	35	6.4	23	40.6	1400	0.85	2.1	6.4	5.9
2026-10-01T12:11:00Z	r-1001-a	5.6	1.68	10.5	222	26	6.2	23	40.6	1400	1.43	2.6	6.2	5.9
2026-10-01T12:13:00Z	r-1001-a	5.2	1.57	9.5	222	17	6.3	23	40.6	1400	1.34	2.4	6.3	6.0
2026-10-01T12:15:00Z	r-1001-a	6.0	1.81	10.9	222	47	6.2	23	40.6	1400	1.54	2.2	6.2	6.0
2026-10-01T12:17:00Z	r-1001-a	6.3	1.89	10.6	222	24	6.4	23	40.6	1400	1.61	2.1	6.4	6.0
2026-10-01T12:19:00Z	r-1001-a	4.4	1.32	9.5	222	28	6.4	23	40.6	1400	1.12	2.4	6.4	6.0
2026-10-01T12:21:00Z	r-1001-a	6.9	2.08	9.3	222	18	6.3	23	40.6	1400	1.77	2.1	6.3	6.0
2026-10-01T12:23:00Z	-	1.1	0.32	7.6	222	0	0.4	23	40.2	1400	0.05	0.9	0.0	6.0
2026-10-01T12:25:00Z	-	1.0	0.30	7.5	222	0	0.4	23	40.2	1400	0.05	0.9	0.0	6.0
2026-10-01T12:27:00Z	-	0.6	0.19	7.2	222	1	0.4	23	40.2	1400	0.05	0.9	0.0	6.0
2026-10-01T12:29:00Z	-	0.7	0.22	7.5	222	1	0.4	23	40.2	1400	0.05	0.9	0.0	6.0
2026-10-01T12:31:00Z	-	0.8	0.23	7.6	222	0	0.4	23	40.3	1400	0.05	0.9	0.0	6.0
2026-10-01T12:33:00Z	-	1.1	0.34	7.3	222	1	0.4	23	40.3	1400	0.05	0.9	0.0	6.0
2026-10-01T12:35:00Z	-	1.1	0.33	7.3	222	1	0.4	23	40.3	1400	0.05	0.9	0.0	6.0
2026-10-01T12:37:00Z	-	0.9	0.26	7.3	222	1	0.4	23	40.3	1400	0.05	0.9	0.0	6.0
2026-10-01T12:39:00Z	-	0.9	0.27	7.5	222	0	0.4	23	40.3	1400	0.05	0.9	0.0	6.0
2026-10-01T12:41:00Z	-	1.1	0.34	7.4	222	1	0.4	23	40.3	1400	0.05	0.9	0.0	6.0
2026-10-01T12:43:00Z	-	1.3	0.38	7.4	222	1	0.4	23	40.3	1400	0.05	0.9	0.0	6.0
2026-10-01T12:45:00Z	-	1.1	0.32	7.4	222	1	0.4	23	40.3	1400	0.05	0.9	0.0	6.0
2026-10-01T12:47:00Z	-	0.7	0.20	7.3	222	0	0.4	23	40.3	1400	0.05	0.9	0.0	6.0
2026-10-01T12:49:00Z	-	0.6	0.19	7.4	222	1	0.4	23	40.3	1400	0.05	0.9	0.0	6.0
2026-10-01T12:51:00Z	-	1.2	0.36	7.4	222	0	0.4	23	40.3	1400	0.05	0.9	0.0	6.0
2026-10-01T12:53:00Z	-	1.3	0.39	7.4	222	1	0.4	23	40.3	1400	0.05	0.9	0.0	6.0
2026-10-01T12:55:00Z	-	1.0	0.29	7.3	222	0	0.4	23	40.3	1400	0.05	0.9	0.0	6.0
2026-10-01T12:57:00Z	-	0.7	0.22	7.4	222	1	0.4	23	40.3	1400	0.05	0.9	0.0	6.0
2026-10-01T12:59:00Z	-	1.3	0.39	7.3	222	0	0.4	23	40.3	1400	0.05	0.9	0.0	6.0
2026-10-01T13:01:00Z	-	0.8	0.25	7.3	222	0	0.4	23	40.3	1400	0.05	0.9	0.0	6.0
2026-10-01T13:03:00Z	-	0.8	0.24	7.2	222	1	0.4	23	40.3	1400	0.05	0.9	0.0	6.0
2026-10-01T13:05:00Z	-	1.3	0.40	7.6	222	1	0.4	23	40.3	1400	0.05	0.9	0.0	6.0
2026-10-01T13:07:00Z	-	1.2	0.35	7.4	222	1	0.4	23	40.3	1400	0.05	0.9	0.0	6.0
2026-10-01T13:09:00Z	-	1.4	0.41	7.5	222	0	0.4	23	40.3	1400	0.05	0.9	0.0	6.0
2026-10-01T13:11:00Z	-	0.8	0.25	7.5	222	1	0.4	23	40.3	1400	0.05	0.9	0.0	6.0
2026-10-01T13:13:00Z	-	0.7	0.22	7.2	222	0	0.4	23	40.3	1400	0.05	0.9	0.0	6.0
2026-10-01T13:15:00Z	-	0.8	0.24	7.4	222	0	0.4	23	40.3	1400	0.05	0.9	0.0	6.0
2026-10-01T13:17:00Z	-	1.4	0.41	7.3	222	1	0.4	23	40.3	1400	0.05	0.9	0.0	6.0
2026-10-01T13:19:00Z	-	1.0	0.29	7.5	222	0	0.4	23	40.3	1400	0.05	0.9	0.0	6.0
2026-10-01T13:21:00Z	-	1.2	0.35	7.3	222	0	0.4	23	40.3	1400	0.05	0.9	0.0	6.0
2026-10-01T13:23:00Z	-	1.1	0.34	7.5	222	1	0.4	23	40.3	1400	0.05	0.9	0.0	6.0
2026-10-01T13:25:00Z	-	0.9	0.28	7.2	222	1	0.4	23	40.3	1400	0.05	0.9	0.0	6.0
2026-10-01T13:27:00Z	-	0.6	0.19	7.4	222	1	0.4	23	40.3	1400	0.05	0.9	0.0	6.0
2026-10-01T13:29:00Z	-	0.6	0.19	7.6	222	1	0.4	23	40.3	1400	0.05	0.9	0.0	6.0
2026-10-01T13:31:00Z	-	1.0	0.30	7.2	222	1	0.4	23	40.3	1400	0.05	0.9	0.0	6.0
2026-10-01T13:33:00Z	-	0.7	0.20	7.4	222	1	0.4	23	40.3	1400	0.05	0.9	0.0	6.0
2026-10-01T13:35:00Z	-	1.3	0.40	7.3	222	0	0.4	23	40.3	1400	0.05	0.9	0.0	6.0
2026-10-01T13:37:00Z	-	0.6	0.19	7.2	222	1	0.4	23	40.4	1400	0.05	0.9	0.0	6.0
2026-10-01T13:39:00Z	-	0.8	0.24	7.3	222	1	0.4	23	40.4	1400	0.05	0.9	0.0	6.0
2026-10-01T13:41:00Z	-	0.6	0.19	7.6	222	0	0.4	23	40.4	1400	0.05	0.9	0.0	6.0
2026-10-01T13:43:00Z	-	0.7	0.22	7.4	222	1	0.4	23	40.4	1400	0.05	0.9	0.0	6.0
2026-10-01T13:45:00Z	-	1.0	0.31	7.3	222	0	0.4	23	40.4	1400	0.05	0.9	0.0	6.0
2026-10-01T13:47:00Z	-	0.7	0.21	7.6	222	1	0.4	23	40.4	1400	0.05	0.9	0.0	6.0
2026-10-01T13:49:00Z	-	1.1	0.32	7.3	222	1	0.4	23	40.4	1400	0.05	0.9	0.0	6.0
2026-10-01T13:51:00Z	-	0.6	0.18	7.4	222	1	0.4	23	40.4	1400	0.05	0.9	0.0	6.0
2026-10-01T13:53:00Z	-	1.1	0.32	7.5	222	1	0.4	23	40.4	1400	0.05	0.9	0.0	6.0
2026-10-01T13:55:00Z	-	1.2	0.35	7.3	222	1	0.4	23	40.4	1400	0.05	0.9	0.0	6.1
2026-10-01T13:57:00Z	-	1.0	0.29	7.3	222	1	0.4	23	40.4	1400	0.05	0.9	0.0	6.1
2026-10-01T13:59:00Z	-	0.7	0.21	7.2	222	0	0.4	23	40.4	1400	0.05	0.9	0.0	6.1
2026-10-01T14:01:00Z	r-1001-b	7.6	2.29	9.4	222	44	5.9	23	40.8	1400	1.95	2.0	5.9	6.1
2026-10-01T14:03:00Z	r-1001-b	4.5	1.34	10.7	222	18	6.0	23	40.8	1400	1.14	2.1	6.0	6.1
2026-10-01T14:05:00Z	r-1001-b	3.4	1.01	9.6	222	40	5.6	23	40.8	1400	0.86	2.2	5.6	6.1
2026-10-01T14:07:00Z	r-1001-b	5.2	1.57	9.9	222	18	6.0	23	40.8	1400	1.34	2.5	6.0	6.1
2026-10-01T14:09:00Z	r-1001-b	6.3	1.90	11.3	222	46	6.3	23	40.8	1400	1.62	2.3	6.3	6.1
2026-10-01T14:11:00Z	r-1001-b	5.7	1.70	11.9	222	44	6.3	23	40.8	1400	1.44	2.4	6.3	6.1
2026-10-01T14:13:00Z	r-1001-b	7.2	2.16	10.1	222	24	6.5	23	40.8	1400	1.84	2.1	6.5	6.1
2026-10-01T14:15:00Z	r-1001-b	3.4	1.02	11.0	222	21	5.8	23	40.8	1400	0.87	2.2	5.8	6.1
2026-10-01T14:17:00Z	r-1001-b	3.4	1.01	9.1	222	42	6.2	23	40.8	1400	0.86	2.0	6.2	6.1
2026-10-01T14:19:00Z	r-1001-b	3.8	1.13	11.8	222	28	6.5	23	40.8	1400	0.96	2.4	6.5	6.1
2026-10-01T14:21:00Z	r-1001-b	4.4	1.32	10.0	222	30	5.9	23	40.8	1400	1.12	2.0	5.9	6.1
2026-10-01T14:23:00Z	r-1001-b	6.5	1.95	9.3	222	44	6.4	23	40.8	1400	1.66	2.3	6.4	6.1
2026-10-01T14:25:00Z	r-1001-b	4.0	1.21	11.8	222	40	6.0	23	40.8	1400	1.03	2.5	6.0	6.1
2026-10-01T14:27:00Z	r-1001-b	3.7	1.11	10.4	222	26	6.6	23	40.8	1400	0.95	2.3	6.6	6.1
2026-10-01T14:29:00Z	r-1001-b	5.6	1.69	10.6	222	42	6.6	23	40.8	1400	1.44	2.6	6.6	6.1
2026-10-01T14:31:00Z	r-1001-b	6.6	1.97	10.3	222	19	6.5	23	40.8	1400	1.68	2.0	6.5	6.1
2026-10-01T14:33:00Z	r-1001-b	8.9	2.66	10.4	222	16	6.2	23	40.8	1400	2.26	2.5	6.2	6.1
2026-10-01T14:35:00Z	r-1001-b	5.4	1.61	9.6	222	23	5.8	23	40.8	1400	1.37	2.3	5.8	6.1
2026-10-01T14:37:00Z	r-1001-b	5.1	1.54	10.1	222	41	5.8	23	40.8	1400	1.31	2.1	5.8	6.1
2026-10-01T14:39:00Z	r-1001-b	8.9	2.67	10.9	222	44	6.5	23	40.8	1400	2.27	2.2	6.5	6.1
2026-10-01T14:41:00Z	r-1001-b	3.9	1.16	9.1	222	44	6.1	23	40.8	1400	0.98	2.1	6.1	6.1
2026-10-01T14:43:00Z	r-1001-b	3.6	1.08	9.6	222	40	6.6	23	40.9	1400	0.92	2.5	6.6	6.1
2026-10-01T14:45:00Z	r-1001-b	4.9	1.48	10.9	222	39	6.5	23	40.9	1400	1.26	2.5	6.5	6.1
2026-10-01T14:47:00Z	r-1001-b	5.3	1.58	10.8	222	15	6.1	23	40.9	1400	1.34	2.1	6.1	6.1
2026-10-01T14:49:00Z	r-1001-b	5.3	1.60	9.9	222	26	5.5	23	40.9	1400	1.36	2.2	5.5	6.1
2026-10-01T14:51:00Z	r-1001-b	5.9	1.76	11.9	222	40	6.0	23	40.9	1400	1.49	2.5	6.0	6.1
2026-10-01T14:53:00Z	r-1001-b	8.5	2.56	10.6	222	39	6.3	23	40.9	1400	2.18	2.5	6.3	6.1
2026-10-01T14:55:00Z	r-1001-b	5.2	1.55	10.6	222	36	6.3	23	40.9	1400	1.32	2.2	6.3	6.1
2026-10-01T14:57:00Z	r-1001-b	3.5	1.04	10.7	222	18	5.9	23	40.9	1400	0.88	2.5	5.9	6.1
2026-10-01T14:59:00Z	r-1001-b	7.3	2.19	9.8	222	26	6.6	23	40.9	1400	1.86	2.4	6.6	6.1
2026-10-01T15:01:00Z	r-1001-b	3.4	1.03	11.9	222	41	6.3	23	40.9	1400	0.88	2.5	6.3	6.1
2026-10-01T15:03:00Z	r-1001-b	7.1	2.14	10.8	222	44	6.4	23	40.9	1400	1.82	2.1	6.4	6.1
2026-10-01T15:05:00Z	r-1001-b	6.1	1.83	11.9	222	46	5.8	23	40.9	1400	1.56	2.3	5.8	6.1
2026-10-01T15:07:00Z	r-1001-b	5.4	1.61	9.5	222	15	6.0	23	40.9	1400	1.37	2.4	6.0	6.1
2026-10-01T15:09:00Z	r-1001-b	8.4	2.52	10.2	222	47	6.2	23	40.9	1400	2.14	2.1	6.2	6.1
2026-10-01T15:11:00Z	r-1001-b	7.1	2.14	10.1	222	34	6.4	23	40.9	1400	1.82	2.5	6.4	6.1
2026-10-01T15:13:00Z	r-1001-b	4.3	1.28	10.9	222	26	5.8	23	40.9	1400	1.09	2.5	5.8	6.1
2026-10-01T15:15:00Z	r-1001-b	4.0	1.20	9.7	222	37	6.4	23	40.9	1400	1.02	2.0	6.4	6.1
2026-10-01T15:17:00Z	r-1001-b	6.4	1.92	11.2	222	44	6.6	23	40.9	1400	1.63	2.3	6.6	6.1
2026-10-01T15:19:00Z	r-1001-b	5.6	1.67	9.9	222	34	6.6	23	40.9	1400	1.42	2.2	6.6	6.1
2026-10-01T15:21:00Z	r-1001-b	6.6	1.99	9.1	222	49	5.7	23	40.9	1400	1.69	2.1	5.7	6.1
2026-10-01T15:23:00Z	r-1001-b	6.4	1.91	9.6	222	36	5.7	23	40.9	1400	1.63	2.4	5.7	6.1
2026-10-01T15:25:00Z	r-1001-b	6.9	2.06	9.2	222	39	6.4	23	40.9	1400	1.75	2.3	6.4	6.1
2026-10-01T15:27:00Z	r-1001-b	8.0	2.40	11.6	222	49	5.9	23	40.9	1400	2.04	2.4	5.9	6.1
2026-10-01T15:29:00Z	r-1001-b	8.6	2.57	11.5	222	23	6.3	23	40.9	1400	2.18	2.3	6.3	6.1
2026-10-01T15:31:00Z	r-1001-b	3.6	1.08	9.3	222	22	5.7	23	40.9	1400	0.92	2.1	5.7	6.1
2026-10-01T15:33:00Z	r-1001-b	6.7	2.01	11.2	222	19	6.4	23	40.9	1400	1.71	2.5	6.4	6.1
2026-10-01T15:35:00Z	r-1001-b	7.8	2.35	11.9	222	40	6.6	23	40.9	1400	1.99	2.4	6.6	6.2
2026-10-01T15:37:00Z	r-1001-b	8.8	2.64	9.2	222	19	5.6	23	40.9	1400	2.24	2.1	5.6	6.2
2026-10-01T15:39:00Z	r-1001-b	5.2	1.57	11.2	222	31	6.3	23	40.9	1400	1.34	2.1	6.3	6.2
2026-10-01T15:41:00Z	r-1001-b	5.4	1.63	9.4	222	34	6.0	23	40.9	1400	1.38	2.4	6.0	6.2
2026-10-01T15:43:00Z	r-1001-b	5.2	1.57	11.9	222	39	6.1	23	40.9	1400	1.34	2.6	6.1	6.2
`,
};
