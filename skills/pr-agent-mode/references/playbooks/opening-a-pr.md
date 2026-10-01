### Opening a PR

Adapted from poteto-mode `playbooks/opening-a-pr.md` (cursor/plugins pstack, MIT). Changes for this agent: no worktrees, stacks, Graphite or Origin; one PR per issue through `pr-agent pr open`; the self-review gate runs before this playbook, and the script refuses to open without it.

**Preconditions (the script checks them all):** gate passed on this exact diff; repo policy is `allows` or `allows-with-disclosure`; caps have room; no other open PR from you in this repo; no `.github/workflows/` edits.

**Commits.** The script pushes one commit with your title as its subject. Keep the diff to the issue.

**Text.** Write the title and body with **make-pr-easy-to-review** for structure, then run **unslop** on them. Follow the repo's PR template headings if it has one, keeping the four sections below inside it. Use one word for each action, keep articles, plain verbs.

**Title.** Conventional Commits: `type(scope): subject`, type one of `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`; scope is the changed area; short imperative subject; name a real symbol when one carries the change; no trailing period. Example: `fix(io): keep dtype when read_csv gets an empty file`.

**Body.** A briefing, not a lab notebook. Sections in order, drop one only when it has nothing to say:

- `## Why`. Intent and approach in one or two short paragraphs. Link the issue.
- `## Scope`. Bullets of real symbols and paths. Say what is out of scope when the boundary matters (things you noticed but did not touch go here).
- `## Blast Radius`. One to three sentences: who or what the change touches and why it is safe or risky.
- `## Verification`. Each real run path and its outcome: the repro failing then passing, the test suite totals before and after. For perf, one number as `before → after` with its unit.

Then attach screenshots or numbers when they prove a claim (from **before-and-after**). No `## Summary` or `## Test plan`, no SHAs, no file-by-file lists. The script appends the AI disclosure, `Fixes <issue>` and the ledger link; don't write your own.

**Open it.** Write the body to `<ws>/.pr-agent/pr-body.md`, then `pr-agent pr open <ws> --title "<title>" --body-file <ws>/.pr-agent/pr-body.md`. If it prints `refused`, the reason is already in the ledger. Fix what it names if that is in your control (title, body); otherwise move on.

**Babysit.** Opening a PR does not start a babysit in the same run. The `pr-agent-follow-up` job picks up review comments later.
