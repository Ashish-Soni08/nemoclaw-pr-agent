---
name: follow-up
description: "Follow-up job: review comments, replies to claims"
version: 0.1.0
license: MIT
metadata:
  hermes:
    tags: [pr-agent, follow-up, babysit]
---

# Follow up

The job's script output has `follow_up.prs` (new comments and state changes on your open PRs) and `follow_up.claims` (maintainer replies, assignments, expiries).

1. **Claims.** Handle each per **claim-issue** ("On a later run"). Approved ones and ones in state `build` go to a fix sub-agent with **fix-issue**, then the gate and **Opening a PR** as in a normal run. They still count against `limits.max_fixes_per_run`.
2. **PR comments.** Run the **Babysit** playbook (threads-only) from **pr-agent-mode**. Every new comment ends in a reply, a pushed fix plus reply, or an ack with a reason.
3. **Merged or closed PRs.** `pr-agent` already logged a `pr.outcome` row when it saw the change. If a maintainer closed it with a reason, log that reason (`pr-agent log pr.note <issue-id> "close reason" --why "<their words>" --evidence <comment url>`). Don't reopen anything.
4. **Remember.** For each merged or closed PR, claim answer and review that asked for changes, decide whether it teaches you something about the repo, and save it per **Remembering what you learned** in **pr-agent-mode**.
5. End with `pr-agent summary run`, as in every run.
