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

1. **Claims.** Handle each per **claim-issue** ("On a later run"). Approved ones and ones in state `build` go to a fix sub-agent with **fix-issue**, then the gate and **Opening a PR** as in a normal run. They still count against `limits.max_fixes_per_run`. Your other open PRs in the same repo don't hold them back until `limits.max_open_prs_per_repo` is reached (`pr-agent pr open` refuses at the cap); a gated fix parked earlier for the old one-PR cap is opened now.
2. **Watched repos.** `follow_up.watch` lists new, unassigned issues in a repo your owner pinned that asks contributors to wait for assignment (Kestra). For each, read it (`pr-agent issue <issue_id>`) and apply its `track` rules. If you'd take it, post the claim now per **claim-issue** (`pr-agent claim post`), asking to be assigned; don't build until assigned. Otherwise `pr-agent decide <issue_id> skip --why "<reason>"` so it isn't shown again.
3. **PR comments.** Run the **Babysit** playbook (threads-only) from **pr-agent-mode**. Every new comment ends in a reply, a pushed fix plus reply, or an ack with a reason.
4. **Merged or closed PRs.** `pr-agent` already logged a `pr.outcome` row when it saw the change. If a maintainer closed it with a reason, log that reason (`pr-agent log pr.note <issue-id> "close reason" --why "<their words>" --evidence <comment url>`). Don't reopen anything.
5. **Remember.** For each merged or closed PR, claim answer and review that asked for changes, decide whether it teaches you something about the repo, and save it per **Remembering what you learned** in **pr-agent-mode**.
6. End with `pr-agent summary run`, as in every run.
