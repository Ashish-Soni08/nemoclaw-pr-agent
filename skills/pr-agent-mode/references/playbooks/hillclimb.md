### Hillclimb

Adapted from poteto-mode `playbooks/hillclimb.md` (cursor/plugins pstack, MIT). Subagent fan-out and worktrees are dropped; one sub-agent runs the loop in its workspace.

**You own the metric and the experiment's integrity.** For an issue that asks to push one measurable thing (speed, memory, accuracy on a fixed eval) toward a target. A one-off fix is Bug fix or Perf issue.

1. Pick the case from the issue that reproduces the complaint. Fix one metric, its direction, and a stop predicate that pairs a target with a minimum number of attempts.
2. Build the measurement command, check it separates an easy case from the target case, then freeze it. Record the baseline (median of N) and a green test run.
3. Keep an attempt log in the ledger: one `pr-agent log hillclimb.attempt` row per attempt with hypothesis, change, before, after, kept or reverted.
4. Ground each hypothesis in a specific mechanism, not "try caching".
5. Loop: one change, measure, run the tests, keep only if the metric moves past noise and tests stay green; otherwise revert fully.
6. On a plateau, change category or try a more radical idea before stopping. Correctness and simplicity beat the number.
7. Stop at the predicate, or when the remaining ideas aren't worth their cost. Never relax the predicate.
8. Hand back for **self-review-gate**, then **Opening a PR** with the accepted changes.

**Report:** metric and target, baseline to final with percent delta, attempts kept vs reverted, the best next idea.
