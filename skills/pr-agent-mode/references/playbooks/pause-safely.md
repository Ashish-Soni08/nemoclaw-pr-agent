### Pause safely

Adapted from poteto-mode `playbooks/pause-safely.md` (cursor/plugins pstack, MIT).

**You own a clean stop.** Use it when the turn budget is nearly spent, a time limit is close, or the guard says the budget is gone.

1. Stop at a safe boundary. Finish or back out of the current step; start nothing new.
2. Take no irreversible action to pause: no PR, no claim, no comment that wasn't already going out.
3. Make the work durable. The workspace keeps the diff on disk; commit it locally with a `wip:` message (`git -C <ws> commit -am "wip: <step>"`).
4. Write the resume note to `<ws>/.pr-agent/resume.md`: intent, what is verified, the next step, gotchas. Log a `pause` row pointing at it.
5. End the run with the summary as usual.
