#!/usr/bin/env bash
# Hermes settings the agent needs. Run inside the sandbox after every NemoClaw rebuild
# (rebuilds regenerate config.yaml). Model ids come from config/agent.yaml's menu.
set -euo pipefail

FIX_MODEL="${PR_AGENT_FIX_MODEL:-Qwen/Qwen3-Coder-480B-A35B-Instruct}"

# Fix sub-agents run on the `fix` model through the same managed inference route.
hermes config set delegation.model "$FIX_MODEL"
hermes config set delegation.max_concurrent_children 2
hermes config set delegation.child_timeout_seconds 3600
# Cron runs delegate_task synchronously (nothing can come back after the turn ends), and Hermes
# cuts any tool call off at 420 s by default. Let it outlast the children it waits for.
hermes config set tools.concurrent_batch 3900
# A full run (triage, two fixes, gate, PR text) needs more than the managed default of 60 turns.
hermes config set agent.max_turns 200
# Let the terminal tool see the agent's own settings and credential placeholders.
hermes config set terminal.env_passthrough '["PR_AGENT_HOME","PR_AGENT_REPO","PRAGENT_GITHUB_TOKEN","PRAGENT_FIRECRAWL_KEY"]'
hermes config show | sed -n '/^delegation/,/^[a-z]/p' || true
