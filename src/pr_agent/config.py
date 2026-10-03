"""Paths, settings and secrets. Settings live in YAML, secrets in the environment."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(os.environ.get("PR_AGENT_REPO", Path(__file__).resolve().parents[2]))


def load_env_file(path: Path) -> None:
    """Read KEY=value lines into os.environ without overriding what is already set."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


@dataclass
class Settings:
    home: Path
    agent: dict[str, Any]
    query_bank: dict[str, Any]

    @classmethod
    def load(cls) -> "Settings":
        home = Path(os.environ.get("PR_AGENT_HOME", Path.home() / ".pr-agent")).expanduser()
        load_env_file(home / "secrets.env")
        # Scheduled cron runs start from the Hermes gateway, which OpenShell doesn't give the
        # provider placeholders (only exec sessions get them); deploy.sh saves them here.
        load_env_file(home / "provider-env")
        agent_path = Path(os.environ.get("PR_AGENT_CONFIG", REPO_ROOT / "config" / "agent.yaml"))
        bank_path = Path(os.environ.get("PR_AGENT_QUERY_BANK", REPO_ROOT / "skills" / "discover-work" / "references" / "query-bank.yaml"))
        return cls(home=home, agent=_read_yaml(agent_path), query_bank=_read_yaml(bank_path))

    @cached_property
    def state_dir(self) -> Path:
        return _mkdir(self.home / "state")

    @cached_property
    def ledger_dir(self) -> Path:
        return _mkdir(self.home / "ledger")

    @cached_property
    def runs_dir(self) -> Path:
        return _mkdir(self.ledger_dir / "runs")

    @cached_property
    def workspaces_dir(self) -> Path:
        return _mkdir(self.home / "workspaces")

    @property
    def decisions_path(self) -> Path:
        return self.ledger_dir / "decisions.tsv"

    def limit(self, key: str, default: Any = None) -> Any:
        return self.agent.get("limits", {}).get(key, default)


class MissingSecret(RuntimeError):
    pass


def secret(name: str, required: bool = True) -> str:
    value = os.environ.get(name, "")
    if required and not value:
        raise MissingSecret(f"{name} is not set. See docs/runbook-lambda.md: secrets go in the OpenShell provider or $PR_AGENT_HOME/secrets.env, never in the repo or chat.")
    return value


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text()) or {}


def _mkdir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path
