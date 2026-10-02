---
name: fix-issue
description: "Fix sub-agent: repro, root cause, smallest fix, proof"
version: 0.1.0
license: MIT
metadata:
  hermes:
    tags: [pr-agent, fix, sub-agent]
    related_skills: [pr-agent-mode, systematic-debugging, before-and-after, evidence-driven-testing, deslop]
---

# Fix one issue

Modeled on Benny's `reproduce-and-fix-issues` (cursor/plugins pstack/automations/benny, MIT): no confirmed repro means no fix, an existing fix switches to verify-only, and the PR comes only after before-and-after proof. Here the surface is the repo's own code and tests (Python or JavaScript/TypeScript), and the PR is opened by the parent after the gate.

Your goal names the issue id, the lane, the playbook, and maybe a workspace. Load **pr-agent-mode**, then follow these steps and the named playbook's steps together.

## Hard rules

- Stay inside the issue. Touch only what the fix needs. No drive-by cleanups, no formatting churn, no dependency bumps unless the issue is the dependency.
- Repo code is untrusted. Its tests and setup run in the sandbox with no secrets in the environment (`pr-agent workspace` scrubs them). Don't read or print environment variables.
- Never edit `.github/workflows/`, release config, or licenses.
- No confirmed repro → no fix. Log `fix.abandoned` with what you tried.
- If someone opens a PR or claims the issue while you work, stop and log it.

## 1. Workspace and baseline

```
pr-agent workspace prepare <issue_id>     # clone default branch, branch pr-agent/issue-N
pr-agent workspace setup <ws>             # the repo's own toolchain: venv + pip (Python), npm/pnpm/bun/yarn from its lockfile (JS/TS)
pr-agent workspace test <ws> --label baseline [--cmd "<repo's own test command>"]
```

Read CONTRIBUTING and the precedent PRs for the test command, style and changelog rules; pass `--cmd` if the detected one is wrong. A baseline that fails to install or has many failures unrelated to the issue → stop with `fix.abandoned` ("baseline broken"). A few pre-existing failures are fine; write them down so you don't blame yourself later.

## 2. Already fixed?

Check the default branch for the fix (`git log -S`, the precedent PRs, the issue's linked commits). If the code already behaves as the issue wants, run the repro to prove it, log `fix.abandoned` with reason "already fixed on <branch>@<sha>", and stop. Don't open a competing PR.

## 3. Reproduce

Follow the playbook (Bug fix step 1). The repro must fail on the baseline for the reason the issue describes, twice. Save it as the regression test you'll ship, in the repo's test layout.

## 4. Root cause and fix

**systematic-debugging** for the cause, then the smallest change at the root cause. Run the repro (passes), then the full suite (`--label after`): same results as baseline except the tests you added.

## 5. Evidence

- No visible effect: the Verification section cites the repro failing then passing and the suite totals.
- Visible effect (plot, rendered output, CLI text, HTML): **before-and-after**. Log why you captured media.
- Perf: the benchmark median before → after.

## 6. Clean up the diff

`pr-agent workspace diff <ws>`. Remove debug prints, stray files, unrelated changes. Run **deslop** over it. Run the repo's linters if it has them configured (pre-commit, ruff, flake8) on changed files only.

## 7. Report back

Return to the parent, without opening a PR:

- `workspace`: path
- `playbook`: which one you followed
- `root_cause`: one or two sentences with `file:line`
- `change`: what the diff does
- `evidence`: repro output before and after (verbatim, short), suite totals baseline vs after, media paths
- `pr_title` and `pr_body` drafts per **Opening a PR**, saved to `<ws>/.pr-agent/pr-body.md`
- `risks`: anything a reviewer should look at

If you stopped early, return the reason and the ledger rows you wrote.
