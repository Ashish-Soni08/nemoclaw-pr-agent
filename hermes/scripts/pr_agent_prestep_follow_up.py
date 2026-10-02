"""Cron pre-step for `pr-agent-follow-up`: wakes the agent only when a PR or claim has news."""

import os
import sys

_default = "/sandbox/nemoclaw-pr-agent" if os.path.isdir("/sandbox/nemoclaw-pr-agent") else os.path.expanduser("~/nemoclaw-pr-agent")
sys.path.insert(0, os.path.join(os.environ.get("PR_AGENT_REPO", _default), "src"))

from pr_agent.cli import main  # noqa: E402

sys.exit(main(["prestep-follow-up"]))
