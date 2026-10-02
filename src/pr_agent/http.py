"""Small JSON-over-HTTP client. Tests swap `Transport` for a fake."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Response:
    status: int
    body: bytes
    headers: dict[str, str] = field(default_factory=dict)

    def json(self) -> Any:
        return json.loads(self.body or b"null")

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300


Transport = Callable[[str, str, dict[str, str], bytes | None, float], Response]


def urllib_transport(method: str, url: str, headers: dict[str, str], data: bytes | None, timeout: float) -> Response:
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return Response(resp.status, resp.read(), {k.lower(): v for k, v in resp.headers.items()})
    except urllib.error.HTTPError as err:
        return Response(err.code, err.read(), {k.lower(): v for k, v in (err.headers or {}).items()})


class HttpError(RuntimeError):
    def __init__(self, response: Response, url: str):
        snippet = response.body[:300].decode("utf-8", "replace")
        super().__init__(f"HTTP {response.status} for {url}: {snippet}")
        self.response = response


@dataclass
class Client:
    base_url: str
    headers: dict[str, str] = field(default_factory=dict)
    transport: Transport = urllib_transport
    timeout: float = 30.0
    sleep: Callable[[float], None] = time.sleep

    def request(self, method: str, path: str, body: Any = None, *, retry_on: tuple[int, ...] = (), backoff: tuple[float, ...] = ()) -> Response:
        url = path if path.startswith("http") else self.base_url.rstrip("/") + "/" + path.lstrip("/")
        headers = {"Accept": "application/json", **self.headers}
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        resp = self.transport(method, url, headers, data, self.timeout)
        for delay in backoff:
            if resp.status not in retry_on:
                break
            self.sleep(delay)
            resp = self.transport(method, url, headers, data, self.timeout)
        return resp

    def get_json(self, path: str) -> Any:
        resp = self.request("GET", path)
        if not resp.ok:
            raise HttpError(resp, path)
        return resp.json()
