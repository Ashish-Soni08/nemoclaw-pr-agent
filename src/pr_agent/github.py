"""GitHub REST calls. Every write goes through api.github.com, including the push.

Pushing with the Git Data API (blobs, tree, commit, ref) instead of `git push`
means the only credential is one bearer header on api.github.com. Inside the
NemoClaw sandbox that header holds a placeholder that OpenShell swaps for the
real token at egress, so the model never sees the token.
"""

from __future__ import annotations

import base64
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from .http import Client, HttpError

API = "https://api.github.com"
SEARCH_GAP_S = 3.0


class Held(RuntimeError):
    """The owner put the agent on hold: no writes to GitHub until they lift it."""


@dataclass
class GitHub:
    client: Client
    sleep: Callable[[float], None] = time.sleep
    # Returns why writes are on hold, or "". Checked before every write, so a hold set mid-run
    # stops the next PR, push or comment even inside a run that's already going.
    hold: Callable[[], str] | None = None
    _repo_cache: dict[str, dict[str, Any]] = field(default_factory=dict)
    _login: str | None = None
    _last_search: float = 0.0
    clock: Callable[[], float] = time.monotonic

    @classmethod
    def create(cls, token: str) -> "GitHub":
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "nemoclaw-pr-agent"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return cls(Client(API, headers=headers))

    # Reads

    def login(self) -> str:
        if self._login is None:
            self._login = self.client.get_json("/user")["login"]
        return self._login

    def repo(self, full: str) -> dict[str, Any]:
        if full not in self._repo_cache:
            self._repo_cache[full] = self.client.get_json(f"/repos/{full}")
        return self._repo_cache[full]

    def issue(self, full: str, number: int) -> dict[str, Any]:
        return self.client.get_json(f"/repos/{full}/issues/{number}")

    def timeline(self, full: str, number: int) -> list[dict[str, Any]]:
        return self.client.get_json(f"/repos/{full}/issues/{number}/timeline?per_page=100")

    def comments(self, full: str, number: int, since: str | None = None) -> list[dict[str, Any]]:
        from urllib.parse import quote

        q = f"?per_page=100&since={quote(since)}" if since else "?per_page=100"
        return self.client.get_json(f"/repos/{full}/issues/{number}/comments{q}")

    def file_text(self, full: str, path: str, ref: str | None = None) -> str | None:
        q = f"?ref={ref}" if ref else ""
        resp = self.client.request("GET", f"/repos/{full}/contents/{path}{q}")
        if resp.status == 404:
            return None
        if not resp.ok:
            raise HttpError(resp, path)
        data = resp.json()
        if isinstance(data, list) or data.get("encoding") != "base64":
            return None
        return base64.b64decode(data["content"]).decode("utf-8", "replace")

    def list_dir(self, full: str, path: str) -> list[str]:
        resp = self.client.request("GET", f"/repos/{full}/contents/{path}")
        if not resp.ok:
            return []
        data = resp.json()
        return [item["path"] for item in data] if isinstance(data, list) else []

    def search_issues(self, q: str, per_page: int = 50, sort: str = "") -> list[dict[str, Any]]:
        from urllib.parse import quote

        order = f"&sort={sort}&order=desc" if sort else ""
        path = f"/search/issues?q={quote(q)}&per_page={per_page}{order}"
        # GitHub's secondary (burst) limit refuses back-to-back searches with a 403, which used to
        # fail the second pinned repo every run. Space searches out and wait once when it happens.
        for attempt in range(2):
            wait = SEARCH_GAP_S - (self.clock() - self._last_search)
            if wait > 0:
                self.sleep(wait)
            resp = self.client.request("GET", path)
            self._last_search = self.clock()
            if resp.ok:
                return resp.json().get("items", [])
            limited = resp.status in (403, 429) and b"rate limit" in resp.body.lower()
            if not limited or attempt:
                raise HttpError(resp, path)
            self.sleep(float(resp.headers.get("retry-after") or 60))
        return []

    def pr_review_comments(self, full: str, number: int) -> list[dict[str, Any]]:
        return self.client.get_json(f"/repos/{full}/pulls/{number}/comments?per_page=100")

    def pr_reviews(self, full: str, number: int) -> list[dict[str, Any]]:
        resp = self.client.request("GET", f"/repos/{full}/pulls/{number}/reviews?per_page=100")
        return resp.json() if resp.ok and isinstance(resp.json(), list) else []

    def pr(self, full: str, number: int) -> dict[str, Any]:
        return self.client.get_json(f"/repos/{full}/pulls/{number}")

    # Writes

    def _post(self, path: str, body: dict[str, Any], method: str = "POST") -> dict[str, Any]:
        if self.hold and (why := self.hold()):
            raise Held(why)
        resp = self.client.request(method, path, body)
        if not resp.ok:
            raise HttpError(resp, path)
        return resp.json()

    def ensure_fork(self, upstream: str, wait_s: float = 60) -> str:
        """Fork once; reuse it on later runs. Returns `login/name`."""
        name = upstream.split("/")[1]
        fork = f"{self.login()}/{name}"
        resp = self.client.request("GET", f"/repos/{fork}")
        if resp.ok and resp.json().get("fork") and (resp.json().get("parent") or {}).get("full_name") == upstream:
            return fork
        created = self._post(f"/repos/{upstream}/forks", {"default_branch_only": True})
        fork = created["full_name"]
        deadline = time.monotonic() + wait_s
        while time.monotonic() < deadline:
            if self.client.request("GET", f"/repos/{fork}/git/ref/heads/{created['default_branch']}").ok:
                return fork
            self.sleep(3)
        raise RuntimeError(f"fork {fork} not ready after {wait_s}s")

    def sync_fork(self, fork: str, branch: str) -> None:
        if self.hold and (why := self.hold()):
            raise Held(why)
        # Best effort: a fork that can't fast-forward is caught by the push's base check.
        self.client.request("POST", f"/repos/{fork}/merge-upstream", {"branch": branch})

    def branch_head(self, repo: str, branch: str) -> str:
        return self.client.get_json(f"/repos/{repo}/git/ref/heads/{branch}")["object"]["sha"]

    def compare(self, repo: str, base: str, head: str) -> dict[str, Any]:
        return self.client.get_json(f"/repos/{repo}/compare/{base}...{head}")

    def push_files(self, repo: str, branch: str, parent: str, changes: dict[str, bytes | None], message: str, signoff: dict[str, str] | None = None) -> str:
        """Commit `changes` on top of `parent` and point `branch` at it. None deletes a path.

        `signoff` ({name, email}): the owner's DCO sign-off, for repos he listed in config. The commit
        is authored in his name and carries his Signed-off-by line, as the DCO check expects."""
        base_commit = self.client.get_json(f"/repos/{repo}/git/commits/{parent}")
        tree = []
        for path, content in sorted(changes.items()):
            if content is None:
                tree.append({"path": path, "mode": "100644", "type": "blob", "sha": None})
                continue
            blob = self._post(f"/repos/{repo}/git/blobs", {"content": base64.b64encode(content).decode(), "encoding": "base64"})
            tree.append({"path": path, "mode": getattr(content, "mode", "100644"), "type": "blob", "sha": blob["sha"]})
        new_tree = self._post(f"/repos/{repo}/git/trees", {"base_tree": base_commit["tree"]["sha"], "tree": tree})
        body: dict[str, Any] = {"message": message, "tree": new_tree["sha"], "parents": [parent]}
        if signoff:
            who = {"name": signoff["name"], "email": signoff["email"]}
            body |= {"message": f"{message.rstrip()}\n\nSigned-off-by: {who['name']} <{who['email']}>", "author": who, "committer": who}
        commit = self._post(f"/repos/{repo}/git/commits", body)
        ref = self.client.request("GET", f"/repos/{repo}/git/ref/heads/{branch}")
        if ref.ok:
            self._post(f"/repos/{repo}/git/refs/heads/{branch}", {"sha": commit["sha"], "force": True}, method="PATCH")
        else:
            self._post(f"/repos/{repo}/git/refs", {"ref": f"refs/heads/{branch}", "sha": commit["sha"]})
        return commit["sha"]

    def open_pr(self, upstream: str, head: str, base: str, title: str, body: str, draft: bool) -> dict[str, Any]:
        return self._post(f"/repos/{upstream}/pulls", {"title": title, "head": head, "base": base, "body": body, "draft": draft, "maintainer_can_modify": True})

    def comment(self, full: str, number: int, body: str) -> dict[str, Any]:
        return self._post(f"/repos/{full}/issues/{number}/comments", {"body": body})

    def reply_review_comment(self, full: str, pr_number: int, comment_id: int, body: str) -> dict[str, Any]:
        return self._post(f"/repos/{full}/pulls/{pr_number}/comments/{comment_id}/replies", {"body": body})
