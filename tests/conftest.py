from __future__ import annotations

import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from fakes import FakeTransport, client
from pr_agent.github import GitHub

NOW = datetime.now(timezone.utc)


def iso(days_ago: float) -> str:
    return (NOW - timedelta(days=days_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")


def repo_json(full: str, **over: Any) -> dict[str, Any]:
    base = {
        "full_name": full, "archived": False, "disabled": False, "has_issues": True, "pushed_at": iso(3),
        "license": {"spdx_id": "MIT"}, "stargazers_count": 1500, "default_branch": "main",
    }
    return base | over


def issue_json(full: str, n: int, **over: Any) -> dict[str, Any]:
    base = {
        "number": n, "title": f"Crash in thing {n}", "state": "open", "locked": False, "assignees": [], "assignee": None,
        "labels": [{"name": "bug"}], "created_at": iso(20), "updated_at": iso(2), "comments": 1,
        "html_url": f"https://github.com/{full}/issues/{n}", "body": "Steps to reproduce...", "user": {"login": "reporter"},
    }
    return base | over


@pytest.fixture()
def fake() -> FakeTransport:
    return FakeTransport()


@pytest.fixture()
def gh(fake: FakeTransport) -> GitHub:
    return GitHub(client("https://api.github.com", fake), sleep=lambda s: None)


@pytest.fixture()
def git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "upstream"
    repo.mkdir()
    run = lambda *a: subprocess.run(a, cwd=repo, check=True, capture_output=True)  # noqa: E731
    run("git", "init", "-q", "-b", "main")
    run("git", "config", "user.email", "t@example.com")
    run("git", "config", "user.name", "t")
    (repo / "pkg.py").write_text("def add(a, b):\n    return a - b\n")
    (repo / "tests").mkdir()
    (repo / "tests" / "test_pkg.py").write_text("from pkg import add\n\ndef test_add():\n    assert add(2, 3) == 5\n")
    run("git", "add", "-A")
    run("git", "commit", "-qm", "init")
    return repo
