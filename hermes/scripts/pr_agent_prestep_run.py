"""Cron pre-step for `pr-agent-run`: usage guard, discovery, policy. Last line is the wake gate."""

import os
import sys

sys.path.insert(0, os.path.join(os.environ.get("PR_AGENT_REPO", "/sandbox/nemoclaw-pr-agent"), "src"))

from pr_agent.cli import main  # noqa: E402

sys.exit(main(["prestep-run"]))
