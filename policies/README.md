# policies

OpenShell egress for the agent's sandbox. Everything else stays blocked.

| What | How it's allowed | Credential |
| --- | --- | --- |
| Model inference (Hugging Face router) | NemoClaw's managed `inference.local` route, set at onboarding | HF token held by the OpenShell gateway |
| GitHub API (fork, push via Git Data API, PRs, comments) | `provider-profiles/pr-agent-github.yaml` | injected at egress; sandbox sees a placeholder |
| Firecrawl Developer Index | `provider-profiles/pr-agent-firecrawl.yaml` | injected at egress |
| `git clone` of public repos | `presets/pr-agent-git.yaml` (fetch only) | none |
| PyPI (installing a target repo's test deps) | built-in `pypi` preset | none |
| Telegram (run summaries) | `nemohermes <sandbox> channels add telegram` applies its own preset | bot token held by the gateway |

The Hugging Face ledger dataset is written from the host (`scripts/sync-ledger.sh`), so the sandbox never holds a write token for it.
