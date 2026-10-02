"""Cron pre-step for `pr-agent-run`: usage guard, discovery, policy. Last line is the wake gate."""

import os
import sys

_default = "/sandbox/nemoclaw-pr-agent" if os.path.isdir("/sandbox/nemoclaw-pr-agent") else os.path.expanduser("~/nemoclaw-pr-agent")
sys.path.insert(0, os.path.join(os.environ.get("PR_AGENT_REPO", _default), "src"))

from pr_agent.cli import main  # noqa: E402

sys.exit(main(["prestep-run"]))
