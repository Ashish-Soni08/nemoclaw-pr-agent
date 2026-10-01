---
name: check-ai-policy
description: "Does a repo accept AI PRs? Check before claim, fix or PR"
version: 0.1.0
license: MIT
metadata:
  hermes:
    tags: [pr-agent, policy, consent]
---

# Check AI policy

Run `pr-agent policy <owner/repo>`. It reads AI_POLICY, CONTRIBUTING and PR template files plus agent instruction files (AGENTS.md, CLAUDE.md, copilot instructions), matches policy sentences, and caches the verdict for 30 days.

Verdicts:

| Verdict | Meaning | Continue? |
|---|---|---|
| `allows` | Explicit welcome, or the repo ships instructions for coding agents | yes |
| `allows-with-disclosure` | AI help is fine if disclosed | yes (every PR discloses anyway) |
| `bans` | Policy text, or a maintainer in past issues/PRs, rejects AI contributions | never |
| `unclear` | No written policy, no maintainer stance found | yes while `continue_on_unclear_policy` is true in config/agent.yaml (it is) |

For `unclear` repos the script spends one Index query on past discussion ("policy on AI generated or LLM written pull requests"); a maintainer rejecting AI PRs turns it into `bans`.

`claim_required: true` means CONTRIBUTING asks contributors to comment or get assigned before starting. That forces the **claim-issue** lane.

Your job is to read the `matches` the script returns and confirm them. If the matched sentence plainly means something else (it bans AI *features* in the product, not AI-written PRs), log `pr-agent log policy.override <repo> "<verdict you'd give>" --why "<sentence>"` and treat the repo as `unclear`. You can only make a verdict stricter, never looser. A ban is final for this agent.
