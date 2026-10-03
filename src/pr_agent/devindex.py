"""Firecrawl Developer Index client with a hard credit cap.

POST https://api.firecrawl.dev/v2/search/developer. 2 credits per 10 results,
rounded up. The cap is checked before every call, never after.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .http import Client, Response
from .state import CreditBook

BASE_URL = "https://api.firecrawl.dev"
ISSUE_ID = re.compile(r"^(issue|pull_request):([\w.-]+/[\w.-]+)#(\d+)$")


def credits_for(k: int) -> int:
    return 2 * math.ceil(k / 10)


def query_hash(body: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()[:12]


def parse_id(hit_id: str) -> tuple[str, str, int] | None:
    """`issue:owner/repo#12` -> ("issue", "owner/repo", 12)."""
    m = ISSUE_ID.match(hit_id or "")
    if not m:
        return None
    return m.group(1), m.group(2), int(m.group(3))


class CreditCapReached(RuntimeError):
    pass


class IndexUnavailable(RuntimeError):
    pass


@dataclass
class SearchResult:
    body: dict[str, Any]
    hits: list[dict[str, Any]]
    coverage: dict[str, Any]
    credits: int
    status: int
    query_hash: str
    skipped: str = ""


@dataclass
class DevIndex:
    client: Client
    book: CreditBook
    run: str
    max_per_run: int = 30
    max_per_month: int = 900
    _spent_here: int = field(default=0, init=False)

    @classmethod
    def create(cls, api_key: str, book: CreditBook, run: str, **caps: int) -> "DevIndex":
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        return cls(Client(BASE_URL, headers=headers, timeout=60), book, run, **caps)

    def month_spent(self) -> int:
        return self.book.spent(month=datetime.now(timezone.utc).strftime("%Y-%m"))

    @property
    def spent_this_run(self) -> int:
        # Read from the credit book, so separate pr-agent calls in one run share the backstop.
        # Outside a run (manual calls) there is no run id to key on, so count this process only.
        return self.book.spent(run=self.run) if self.run else self._spent_here

    def can_spend(self, k: int) -> bool:
        cost = credits_for(k)
        return self.spent_this_run + cost <= self.max_per_run and self.month_spent() + cost <= self.max_per_month

    def search(self, body: dict[str, Any]) -> SearchResult:
        k = int(body.get("k", 10))
        qh = query_hash(body)
        if not self.can_spend(k):
            raise CreditCapReached(f"run {self.spent_this_run}/{self.max_per_run}, month {self.month_spent()}/{self.max_per_month}")
        resp = self.client.request("POST", "/v2/search/developer", body, retry_on=(429,), backoff=(5, 20))
        if resp.status == 429:
            return SearchResult(body, [], {}, 0, 429, qh, skipped="rate limited after 2 retries")
        if not resp.ok:
            return SearchResult(body, [], {}, 0, resp.status, qh, skipped=_err(resp))
        cost = credits_for(k)
        self._spent_here += cost
        self.book.add(self.run, cost, qh)
        data = resp.json() or {}
        payload = data.get("data", data)
        hits = payload.get("results") or payload.get("hits") or []
        coverage = payload.get("coverage") or data.get("coverage") or {}
        return SearchResult(body, hits, coverage, cost, resp.status, qh)


def _err(resp: Response) -> str:
    return f"HTTP {resp.status}: {resp.body[:200].decode('utf-8', 'replace')}"
