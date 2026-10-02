### Multi-phase plan

Adapted from poteto-mode `playbooks/multi-phase-plan.md` (cursor/plugins pstack, MIT). The program machinery (owners, swarm lanes, `/goal`, ticks, stacks) is dropped: this agent ships one PR per issue and never merges. What stays is the discipline of cutting work into verified units.

**You own the plan, not the code.** Use when the fix for one issue is too big for one PR under the caps.

1. If the change is one or two files with an obvious approach, skip the plan. Say so and go back to Bug fix or Feature.
2. Cut the work into phases where each phase is one landable change with its own evidence (**principle-sequence-verifiable-units**). Phase one must be useful on its own.
3. For each phase write: the change, the files, the test that proves it, and what it unblocks. Write it to `<ws>/.pr-agent/plan.md`.
4. Ship phase one only, through the normal fix, gate and PR steps. Put the remaining phases in the PR body under `## Scope` as follow-ups for the maintainer to decide on.
5. Log a `plan` row with the plan path. The agent does not open the later phases unless a maintainer asks for them on the PR.

**Verification.** Tests alone are not sufficient. A phase is verified only when its repro passes and the repo's suite matches the baseline (**principle-prove-it-works**).
