---
name: before-and-after
description: "Visible changes only: base vs fix output for the PR"
version: 0.1.0
license: MIT
metadata:
  hermes:
    tags: [pr-agent, evidence, media]
---

# Before and after

Written for this agent (the michaelshimeles/skills version has no license, so nothing is copied from it).

Use it only when a reviewer would want to *see* the change: a plot, rendered HTML or notebook output, a CLI's printed text, an error message's wording. Skip it for logic, typing, docs and refactors; the test output is the evidence there. Either way, log why: `pr-agent log evidence.media <issue_id> "captured before/after" --why "<visible effect>"` or `"no media" --why "<no visible effect>"`.

## Capture

Write a tiny script in `<ws>/.pr-agent/show.py` that produces the visible output from the issue's own example. For plots, save a file instead of showing a window:

```python
import matplotlib
matplotlib.use("Agg")
...  # the issue's example
plt.savefig(OUT)  # OUT is passed in by the capture script
```

Then:

```
python3 ${HERMES_SKILL_DIR}/scripts/capture.py <ws> --script .pr-agent/show.py --kind png|txt|html
```

It runs the script on a clean checkout of the base commit and on your working tree with the same interpreter, saves both outputs under the ledger's `media/<issue-slug>/` folder (mirrored to the ledger dataset by the host), and prints a Markdown snippet. Paste the snippet after the four sections of the PR body.

## Rules

- Same input, same command, same interpreter on both sides. Only the code differs.
- The "before" must show the bug the issue describes. If it doesn't, your repro is wrong; go back to the playbook.
- Text output goes inline in the PR body (trimmed to what matters). Images are linked from the ledger dataset; if `ledger.public_url` isn't set (the dataset is private), describe the difference in words instead and keep the files in the ledger.
- Don't commit captures to the target repo.
