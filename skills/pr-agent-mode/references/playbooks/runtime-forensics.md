### Runtime forensics

Adapted from poteto-mode `playbooks/runtime-forensics.md` (cursor/plugins pstack, MIT). CDP steps are replaced with Python tooling.

**You own the diagnosis. Instrument the live process, don't theorize from source.** The deliverable is a cited diagnosis that feeds Bug fix or Perf issue, not a fix.

1. Capture the live signal from the repro: a CPU profile (`cProfile`, `py-spy dump`) for a spin, `tracemalloc` snapshots for a leak, logging at the boundary for wrong state.
2. Reduce it to the smoking gun: the hot function, the growing allocation site, the line where state goes wrong. Keep big artifacts in files under `<ws>/.pr-agent/` and summarize them.
3. Prove the mechanism cheaply before believing it: patch the suspect line in place and rerun the repro.
4. Map it to source: file, symbol, line.

throughput checkpoint: n/a, read-only forensics.

**Report:** the signal, the reduced finding, how you proved it, the source location, artifact paths. Then route to Bug fix or Perf issue.
