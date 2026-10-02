### Perf issue

Adapted from poteto-mode `playbooks/perf-issue.md` (cursor/plugins pstack, MIT).

**You own the measurement story.** Tie every fix to a measurement. Don't read source instead of measuring.

1. **Baseline.** Build a benchmark from the issue's own case (sizes, dtypes, call pattern). Run it at least 5 times and record the median with its unit: `pr-agent workspace test <ws> --cmd "<bench>" --label baseline-perf`.
2. **Ground hypotheses in a profile** (`python -m cProfile -o out.prof`, `py-spy` if installed). Use the strategy families as idea generators only when the profile shows their signal: elimination, divide and conquer, caching (name what invalidates it), indirection, batching, lazy evaluation, scheduling.
3. **One change, one measurement.** Keep it only if the median moves past noise and the test suite stays green (**principle-sequence-verifiable-units**).
4. **Compare** before and after with the same harness and inputs. "Inconclusive" is not a pass.
5. **Cite one number** in the PR's Verification as `before → after` with its unit, plus the benchmark command.
6. Hand back for **self-review-gate**, then **Opening a PR**.

**Report:** baseline, after, delta, the benchmark command, the profile path.
