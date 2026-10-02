"""No-agent cron job: the day's digest, delivered to Telegram verbatim. Costs no tokens."""

import os
import sys

_default = "/sandbox/nemoclaw-pr-agent" if os.path.isdir("/sandbox/nemoclaw-pr-agent") else os.path.expanduser("~/nemoclaw-pr-agent")
sys.path.insert(0, os.path.join(os.environ.get("PR_AGENT_REPO", _default), "src"))

from pr_agent.cli import main  # noqa: E402

sys.exit(main(["summary", "daily"]))
