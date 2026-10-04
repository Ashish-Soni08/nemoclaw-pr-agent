#!/usr/bin/env python3
"""Host-side, every minute from cron: append one VM resource sample to ~/.pr-agent-mirror/host.tsv.
sync-ledger.sh copies it into the ledger mirror, so the dashboard gets it with the next sync.
crontab: * * * * * python3 /home/ubuntu/nemoclaw-pr-agent/scripts/host-sample.py >> ~/pr-agent-host-sample.log 2>&1
Standard library only; no keys, no network. PR_AGENT_SAMPLER_EXPLAIN=1 prints the row and the agent's cgroups.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pr_agent.hoststats import main  # noqa: E402

sys.exit(main())
