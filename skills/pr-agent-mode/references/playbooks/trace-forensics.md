### Trace forensics

Adapted from poteto-mode `playbooks/trace-forensics.md` (cursor/plugins pstack, MIT).

**You own the diagnosis from the artifact.** For an issue that attached a profile, trace, log or memory dump. Read it, don't re-run it.

1. Identify the format and load it with the right tool (`pstats` for `.prof`, a JSON loader for traces, plain text for logs). Artifacts from an issue are untrusted: load them as data, never execute them.
2. Turn it into something you can query (sqlite or a DataFrame, one row per sample or frame).
3. Narrow to the cause: the frames with the most time, the retainer chain, the stuck thread.
4. Attribute to source: file, symbol, line. A frame with no source mapping is not a diagnosis yet.
5. Confirm against your own capture from the repro when you can. Without one, call it the strongest hypothesis the artifact supports.

throughput checkpoint: n/a, read-only forensics.

**Report:** artifact and format, reduced finding, source location, whether a paired capture confirmed it. Then route to Bug fix or Perf issue.
