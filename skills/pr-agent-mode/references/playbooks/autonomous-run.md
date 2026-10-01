### Autonomous run

Adapted from poteto-mode `playbooks/autonomous-run.md` (cursor/plugins pstack, MIT). The wake mechanism is the Hermes cron job, not `/loop`. Override: mid-run discoveries in other people's repos are not yours to fix (stay inside the issue).

**You own the exit condition. Define done, then drive to it.**

1. **State the exit condition** as a checkable predicate before the first step, and log it (`pr-agent log run.goal <run> "<predicate>"`). Default: "every candidate has a take or skip row; every taken issue ends in an opened PR, a posted claim, or a logged reason it stopped; the summary is sent."
2. **Wake mechanism** is the cron job. Don't schedule anything yourself. One run handles at most `limits.max_fixes_per_run` fixes; the rest wait for the next tick.
3. **Each step makes the smallest change the evidence justifies**, verifies it, keeps it if it advanced the predicate, discards it if not (**principle-sequence-verifiable-units**).
4. **Stay inside the issue.** Broken tooling in your own pipeline (a `pr-agent` command failing, a skill giving wrong guidance) gets a `skill.flag` or `tool.error` row for a human, not a workaround that hides it.
5. **Checkpoint** every decision with `pr-agent log` (**show-me-your-work**).
6. **Stop** when the predicate holds, or when the turn budget is close (then **Pause safely**). A dead end is a valid stop: log it with evidence. Never relax the predicate to declare victory.

**Final response:** `pr-agent summary run` output (see the router's Ending a run).
