"""Cron pre-step for `pr-agent-follow-up`: wakes the agent only when a PR or claim has news."""

import os
import sys

_default = "/sandbox/nemoclaw-pr-agent" if os.path.isdir("/sandbox/nemoclaw-pr-agent") else os.path.expanduser("~/nemoclaw-pr-agent")
_launcher = os.path.join(os.environ.get("PR_AGENT_REPO", _default), "bin", "pr-agent")
# exec the launcher rather than importing pr_agent here: it picks the interpreter the
# sandbox injects credentials for, which Hermes' own Python is not.
sys.stdout.flush()
os.execv(_launcher, [_launcher, "prestep-follow-up"])
