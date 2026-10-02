"""Fake HTTP transport: routes (method, url substring) to canned JSON and records every call."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable

from pr_agent.http import Client, Response

Handler = Callable[[str, str, Any], tuple[int, Any]]


@dataclass
class FakeTransport:
    routes: list[tuple[str, str, Any]] = field(default_factory=list)
    calls: list[tuple[str, str, Any]] = field(default_factory=list)

    def add(self, method: str, path: str, result: Any, status: int = 200) -> "FakeTransport":
        """`result` is JSON, or a callable (method, url, body) -> (status, json). Later routes win."""
        self.routes.insert(0, (method, path, result if callable(result) else (status, result)))
        return self

    def __call__(self, method: str, url: str, headers: dict[str, str], data: bytes | None, timeout: float) -> Response:
        body = json.loads(data) if data else None
        self.calls.append((method, url, body))
        for m, path, result in self.routes:
            if m == method and _match(path, url):
                status, payload = result(method, url, body) if callable(result) else result
                return Response(status, json.dumps(payload).encode())
        return Response(404, b'{"message": "Not Found"}')

    def called(self, method: str, fragment: str) -> list[Any]:
        return [b for m, u, b in self.calls if m == method and fragment in u]


def _match(path: str, url: str) -> bool:
    target = url.split("://", 1)[-1].split("/", 1)[-1]
    target = "/" + target
    if path.endswith("*"):
        return target.startswith(path[:-1])
    return target.split("?")[0] == path or target == path


def client(base: str, fake: FakeTransport) -> Client:
    return Client(base, transport=fake, sleep=lambda s: None)
