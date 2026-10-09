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
- A maintainer declines, asks to wait, or someone else takes it → `pr-agent claim set <issue_id> declined --why "<quote>"`. Don't reply unless they asked you something. If the no is about AI contributions in general (not just this issue), also run `pr-agent policy <owner/repo> --block --why "<quote>" --evidence <comment url>`.
- You give it up yourself (the fix needs a CI workflow edit, goes past the 400-line cap, or the premise didn't hold) → `pr-agent claim set <issue_id> dropped --why "<reason>"`. Never record your own drop as `declined`: that status means a maintainer said no.
- A question from a maintainer → leave the claim `waiting` and flag it in the run summary so the human sees it. The agent doesn't post free-form issue comments.
- Expired (7 days, no reply) → `pr-agent claim set <issue_id> expired --why "no reply in 7 days"`.
- State `build` → we were told to build it without waiting (see below). If a maintainer replied, handle their reply as above first; a no still wins. Otherwise start a fix sub-agent with **fix-issue**. In the PR body's Why section, link your plan comment (`comment_url` in the claim) and say you opened the PR so they can judge the actual change.

## Building a claim without an answer

Under the build-directly default (Ashish, 2026-10-04 and 2026-10-09), every waiting claim in a repo that doesn't require a yes (`claim_required` false) moves to build on the next run, unless a maintainer has said no or asked to wait: `pr-agent claim set <issue_id> build --why "build-directly: repo doesn't require a yes"`. Never record that as `approved`: nobody said yes. `pr-agent pr open` refuses a `build` claim when the repo requires a yes.

Replies from non-maintainers don't count as approval.
