### Bug fix

Adapted from poteto-mode `playbooks/bug-fix.md` (cursor/plugins pstack, MIT). Cursor-only steps (`how`, `why`, `architect`, `/loop`, model routing) are replaced with inline steps.

**You own this fix. Plan, verify.** Be scientific. Every shipped line traces to runtime evidence. A change that "might help" is a hypothesis, not a fix, and does not ship. When evidence refutes a hypothesis, revert what it motivated.

1. **Reproduce it yourself** in the workspace, on the surface the issue names (a Python snippet, the CLI, a notebook cell, a rendered plot). Write the repro as a script or a failing test in the repo's own test layout, then run it: `pr-agent workspace test <ws> --cmd "<repro>" --label repro`. If it won't reproduce, tighten conditions (versions, dtypes, input sizes from the issue) before giving up. No repro means no fix: log `fix.abandoned` with what you tried and stop.
2. **Binary-search the cause** with the **systematic-debugging** skill. List candidate hypotheses, then rule them out with runtime evidence (prints, a debugger, bisecting the input or the git history). Confirm the surviving mechanism before writing the fix.
3. **Plan the fix.** Name the data shape and the one place it goes wrong. Choose the smallest change at the root cause (**principle-fix-root-causes**, **principle-laziness-protocol**). If the fix would cross several modules or change a public API, stop and switch to the Feature playbook's checks, or skip.
4. **Verify on the same surface.** The repro now passes, and the repo's own test suite still passes against the baseline (`pr-agent workspace test <ws> --label after`). A test that fails on the baseline too is not yours; note it. "Inconclusive" or wrong-surface is not a pass.
5. **Failing test first.** The regression test must fail without the fix and pass with it (**principle-sequence-verifiable-units**, **principle-test-behavior-not-implementation**). Check it by stashing the fix and running the test once.
6. **Visible effect?** Use **before-and-after** for rendered output. Otherwise the Verification section cites the failing-then-passing test output.
7. Hand back to the parent for **self-review-gate**, then **Opening a PR**.

**Report:** what was broken, root cause with `file:line`, the fix, failing-then-passing output verbatim, baseline vs after test totals.
