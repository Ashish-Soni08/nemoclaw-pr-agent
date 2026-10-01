"""No-agent cron job: the day's digest, delivered to Telegram verbatim. Costs no tokens."""

import os
import sys

sys.path.insert(0, os.path.join(os.environ.get("PR_AGENT_REPO", "/sandbox/nemoclaw-pr-agent"), "src"))

from pr_agent.cli import main  # noqa: E402

sys.exit(main(["summary", "daily"]))
