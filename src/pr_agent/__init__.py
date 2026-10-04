"""Deterministic tools the PR agent calls. The model decides; these scripts act."""

import os
import sys

__version__ = "0.1.0"

# The GitHub and Firecrawl keys are injected for this interpreter only. It may run pr-agent, and
# nothing else: a script of the agent's own that imports these modules would reach GitHub without
# the gate, the caps or the ledger (that happened on 2026-10-04). bin/pr-agent starts it with
# exactly LAUNCH; anything else that imports pr_agent under it is refused.
KEYED_PYTHON = "/sandbox/.pr-agent/bin/python"
LAUNCH = 'import sys; sys.path[:] = [p for p in sys.path if p not in ("", ".")]; sys.argv[0] = "pr-agent"; from pr_agent.cli import main; sys.exit(main())'


def _launched_by_pr_agent(executable: str, orig_argv: list[str]) -> bool:
    if os.path.realpath(executable) != KEYED_PYTHON:
        return True
    return orig_argv[1:3] == ["-c", LAUNCH]


if not _launched_by_pr_agent(sys.executable, list(getattr(sys, "orig_argv", []))):
    sys.stderr.write("pr_agent: refused. The key-injected interpreter only runs `pr-agent ...`. Don't call GitHub from your own scripts; "
                     "if a pr-agent command fails, log it with `pr-agent log tool.error` and drop the issue.\n")
    raise SystemExit(3)
