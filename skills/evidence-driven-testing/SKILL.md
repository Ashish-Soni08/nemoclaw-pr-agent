---
name: evidence-driven-testing
description: "Prove a fix with checkable evidence; name what's untested"
version: 0.1.0
license: MIT
metadata:
  hermes:
    tags: [pr-agent, evidence, verification]
---

# Evidence-driven testing

Written for this agent (the michaelshimeles/skills version has no license, so nothing is copied from it). Pairs with **principle-prove-it-works**.

A claim in the PR's Verification section is only as good as the evidence next to it. This sandbox is headless, so the evidence is command output, numbers and files, not screen recordings.

## Steps

1. **Name the claim.** One sentence: "`read_csv` on an empty file now returns a frame with the requested dtypes."
2. **Name the check that would fail if the claim were false.** Usually the regression test. If the claim is about behavior a test can't reach (a warning's text, output formatting, timing), write a short script that prints exactly the thing.
3. **Run it on the base commit and on the fix.** Use `pr-agent workspace test <ws> --cmd "<check>" --label repro` on both sides (never run repo code straight from the terminal) (stash the fix for the base run, or use **before-and-after**'s capture script). Keep both outputs; the ledger rows point at the log files.
4. **Measure, don't describe.** For performance, report the median of at least 5 runs with the unit and the command. For memory, peak bytes from `tracemalloc`. For accuracy, the metric on the issue's own data.
5. **State the gaps.** What you could not run here (GPU paths, other OSes, optional dependencies not installed) goes in Verification as "Not run: ...". Never imply coverage you don't have.
6. **Cite it.** Verification lists each run path with its outcome, verbatim where short.

Log one `evidence` row per claim with the log path as evidence.
