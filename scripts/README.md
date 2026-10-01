# scripts

Host-side lifecycle for the Lambda VM, following the NemoClaw community recipe layout. Run them in order; each is safe to re-run. Full walkthrough: [docs/runbook-lambda.md](../docs/runbook-lambda.md).

| Script | Does |
| --- | --- |
| `install.sh` | Installs NemoClaw (Hermes), onboards the sandbox with the Hugging Face router as inference, adds PyPI and git-clone egress, adds Telegram |
| `setup-credentials.sh` | Registers the GitHub and Firecrawl keys with the OpenShell gateway and attaches them to the sandbox |
| `deploy.sh` | Uploads this repo, installs the skills and SOUL.md, applies Hermes settings, registers cron jobs |
| `run-now.sh` | Triggers a run immediately |
| `status.sh` | Cron state, last ledger rows, spend |
| `sync-ledger.sh` | Copies the ledger out and mirrors it to the Hugging Face dataset (host crontab) |
