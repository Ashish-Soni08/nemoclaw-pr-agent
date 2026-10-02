### Feature

Adapted from poteto-mode `playbooks/feature.md` (cursor/plugins pstack, MIT). Subagent fan-out, `architect`, `arena` and `interrogate` are replaced with inline steps; a fix sub-agent owns the whole diff.

**You own the design. Plan, verify.** Only for small enhancements the issue asks for, where a maintainer has agreed on the behavior (in the issue or by the claim reply). Anything bigger is a skip.

1. Read the subsystem the feature touches and write down how it works today in three to five lines.
2. **Name the data shape first** and how it is organized (a table or registry over branching, a typed model over repeated shape assumptions). Follow the API the maintainer agreed to word for word.
3. Throughput checkpoint, four lines: blocking first steps; independent workstreams (usually `n/a: one sub-agent, one diff`); shared mutable state; smallest safe decomposition.
4. Write the tests for the new behavior first, from the issue's examples, then the code (**principle-sequence-verifiable-units**, **principle-test-behavior-not-implementation**).
5. Verify on the matching surface: the new tests pass, the repo's suite matches the baseline. Docs and changelog follow the repo's own conventions (precedent PRs show them).
6. If the feature has a visible effect, run **before-and-after**.
7. Hand back for **self-review-gate**, then **Opening a PR**.

**Report:** what you built, the data shape and why, the checkpoint, open decisions for the maintainer.
