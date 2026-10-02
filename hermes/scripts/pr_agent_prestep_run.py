"""Cron pre-step for `pr-agent-run`: usage guard, discovery, policy. Last line is the wake gate."""

import os
import sys

_default = "/sandbox/nemoclaw-pr-agent" if os.path.isdir("/sandbox/nemoclaw-pr-agent") else os.path.expanduser("~/nemoclaw-pr-agent")
_launcher = os.path.join(os.environ.get("PR_AGENT_REPO", _default), "bin", "pr-agent")
# exec the launcher rather than importing pr_agent here: it picks the interpreter the
# sandbox injects credentials for, which Hermes' own Python is not.
sys.stdout.flush()
os.execv(_launcher, [_launcher, "prestep-run"])
