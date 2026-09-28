# nemoclaw-pr-agent

Autonomous NemoClaw agent that finds AI and data-science issues where AI contributions are welcome, fixes them in a sandbox and opens PRs, with every decision logged. Built for the NVIDIA Berlin Claw Agent Challenge.

See [docs/design.md](docs/design.md) for the pipeline, stack and guardrails.

## Layout

| Path | Contents |
| --- | --- |
| `skills/` | One folder per agent skill |
| `policies/` | OpenShell sandbox policies |
| `scripts/` | Host-side setup and lifecycle scripts |
| `ledger/` | Decision ledger schema and helpers |
| `ui/` | Read-only ledger viewer |
| `.env.example` | Credentials the host needs |
