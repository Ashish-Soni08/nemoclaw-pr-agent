"""Cron pre-step for `pr-agent-follow-up`: wakes the agent only when a PR or claim has news."""

import os
import sys

sys.path.insert(0, os.path.join(os.environ.get("PR_AGENT_REPO", "/sandbox/nemoclaw-pr-agent"), "src"))

from pr_agent.cli import main  # noqa: E402

sys.exit(main(["prestep-follow-up"]))
