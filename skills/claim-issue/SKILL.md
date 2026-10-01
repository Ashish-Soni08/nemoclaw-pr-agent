---
name: claim-issue
description: "Ask-first lane: post a plan, wait for a maintainer's yes"
version: 0.1.0
license: MIT
metadata:
  hermes:
    tags: [pr-agent, claim, ask-first]
---

# Claim an issue (ask-first lane)

1. Write a plan of two to four short lines: the cause you found (`file:line` when known), the change you'd make, the test you'd add. Plain words, no hype; run **unslop** on it.
2. Save it to a file and post it: `pr-agent claim post <issue_id> --plan-file <file>`. The script wraps it in a fixed comment that says you're an AI agent and that a "no" is respected, enforces one claim per issue and the daily cap, and logs it.
3. Stop work on that issue for this run. Nothing gets cloned or pushed until a maintainer says yes.

## On a later run (follow-up job)

`pr-agent claim updates` (already in the follow-up context) shows each waiting claim with maintainer replies and assignment.

- Assigned to you, or a maintainer (`association` OWNER, MEMBER or COLLABORATOR) clearly says go ahead → `pr-agent claim set <issue_id> approved --why "<quote>"`, then start a fix sub-agent with **fix-issue**.
- A maintainer declines, asks to wait, or someone else takes it → `pr-agent claim set <issue_id> declined --why "<quote>"`. Don't reply unless they asked you something.
- A question from a maintainer → leave the claim `waiting` and flag it in the run summary so the human sees it. The agent doesn't post free-form issue comments.
- Expired (7 days, no reply) → `pr-agent claim set <issue_id> expired --why "no reply in 7 days"`.

Replies from non-maintainers don't count as approval.
