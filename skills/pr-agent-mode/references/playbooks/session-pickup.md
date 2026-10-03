### Session pickup

Adapted from poteto-mode `playbooks/session-pickup.md` (cursor/plugins pstack, MIT). The trail is this agent's own ledger, not Cursor transcripts.

**You own the resume point. Read the prior trail, don't redo it.**

1. **Locate the trail.** `pr-agent ledger show --tail 80`, and the previous run id from its `start` row. Read the last rows first, then scan back for decisions.
2. **Reconstruct state.** Taken issues, their workspaces (`pr-agent workspace info <ws>`), gate verdicts (in `pr-agent workspace info <ws>` and the `gate` ledger rows), open PRs and claims (`pr-agent pr updates`, `pr-agent claim updates`). The trail is authoritative; don't re-derive it.
3. **Diff done vs pending.** Name the resume point. Don't re-run a repro that a row already proved.
4. **Route** the remaining work to its playbook.
5. **Verify inherited claims** on the real artifact before building on them (**principle-prove-it-works**). A gate verdict is only valid if the diff hash still matches; the script checks this.

Log a `pickup` row naming the previous run and the resume point.
