"""check-ai-policy: does this repo accept AI-assisted pull requests?

The script reads the files and applies keyword rules. It returns the verdict
and the exact sentences it matched, so the model (and a human) can check the
call. A ban always wins over any other match.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .github import GitHub
from .state import read_json, write_json

POLICY_FILES = [
    "AI_POLICY.md",
    ".github/AI_POLICY.md",
    "docs/AI_POLICY.md",
    "CONTRIBUTING.md",
    ".github/CONTRIBUTING.md",
    "docs/CONTRIBUTING.md",
    "CONTRIBUTING.rst",
    "docs/contributing.md",
    "docs/source/contributing.rst",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/pull_request_template.md",
    "PULL_REQUEST_TEMPLATE.md",
]
AGENT_FILES = ["AGENTS.md", "CLAUDE.md", ".cursorrules", ".github/copilot-instructions.md", ".cursor/rules"]

AI = r"(?:\bai\b|a\.i\.|\bllms?\b|chatgpt|copilot|claude|language models?|machine[- ]generated|generated (?:code|content|contributions?|pull requests?)|automated (?:pull requests?|contributions?)|agents?\b)"
BAN = [
    re.compile(rf"(?:do not|don't|will not|won't|cannot|can't|does not|doesn't|no longer|not)\s+(?:\w+\s+){{0,3}}(?:accept|allow|permit|welcome|merge|review|want|tolerate|take)\w*[^.\n]{{0,80}}{AI}", re.I),
    # "No AI-generated code." as a sentence or list item of its own.
    re.compile(rf"(?:^|(?<=[.!?:] )|(?<=[-*] ))no\s+{AI}", re.I | re.M),
    re.compile(rf"(?:refrain from|avoid|please (?:do not|don't|never))\s+(?:\w+\s+){{0,2}}(?:submit|send|open|us|contribut)\w*[^.\n]{{0,60}}{AI}", re.I),
    re.compile(rf"{AI}[^.\n]{{0,80}}(?:not (?:be )?(?:accepted|allowed|permitted|welcome)|will be (?:closed|rejected)|(?:are|is) (?:prohibited|banned|forbidden))", re.I),
    re.compile(rf"(?:prohibit|ban|forbid|reject)\w*[^.\n]{{0,60}}{AI}", re.I),
]
DISCLOSE = [
    re.compile(rf"(?:disclose|disclosure|declare|mention|state|indicate|note|label|tell us)\w*[^.\n]{{0,80}}{AI}", re.I),
    re.compile(rf"{AI}[^.\n]{{0,80}}(?:must|should|need to) be (?:disclosed|declared|mentioned|noted|labell?ed)", re.I),
    re.compile(rf"{AI}[^.\n]{{0,60}}(?:mention|disclose|declare|note|state|label)\w*\s+(?:it|this|that)\b", re.I),
]
ALLOW = [
    re.compile(rf"{AI}[^.\n]{{0,60}}(?:contributions?|pull requests?|prs?|assistance|tools?)[^.\n]{{0,40}}(?:are|is) (?:welcome|accepted|allowed|fine|ok)", re.I),
    re.compile(rf"(?:welcome|accept|allow)\w*[^.\n]{{0,40}}{AI}[- ]?(?:assisted|generated|written)", re.I),
]
# Only a written rule that you must wait for a yes or an assignment before working counts
# (Ashish, 2026-10-09). "Comment on the issue to signal you're working on it" is a heads-up,
# not a gate: hermes-agent was wrongly gated by the old, looser patterns.
CLAIM = [
    re.compile(r"\bwait (?:for|until)\b[^.\n]{0,60}(?:maintainer|member|team|approv|confirm|assign|go[- ]ahead|green light)", re.I),
    re.compile(r"(?:get|be|ask to be|request to be|must be|need to be|until you are|once you are|after you(?:'ve| have)? been) (?:formally )?(?:assigned|approved)\b[^.\n]{0,60}(?:before|first|prior)", re.I),
    re.compile(r"(?:before|prior to) (?:you )?(?:start(?:ing)?|begin(?:ning)?|work(?:ing)? on|open(?:ing)?|submit(?:ting)?|creat(?:e|ing))[^.\n]{0,80}(?:get|be|wait for|need|must have|obtain|so (?:that )?(?:we|a maintainer|someone) can)[^.\n]{0,30}(?:assign|approv|confirm|agree)", re.I),
    re.compile(r"(?:after|once) you (?:get|have|receive)[^.\n]{0,30}(?:formal )?(?:approval|go[- ]ahead|confirmation|assign)", re.I),
    re.compile(r"(?:do not|don't|never|please don't) (?:open|submit|create|send)[^.\n]{0,40}(?:pull request|\bpr\b)[^.\n]{0,40}(?:without|until|before)[^.\n]{0,60}(?:assign|approv|discuss|agree|confirm)", re.I),
    re.compile(r"only (?:work on|pick up|take|open (?:prs|pull requests) for) issues[^.\n]{0,40}(?:assigned|approved|accepted|triaged)", re.I),
]

# Bump when the patterns change, so cached verdicts made under older rules are redone.
RULES = 2
VERDICTS = ("allows", "allows-with-disclosure", "bans", "unclear")


@dataclass
class PolicyVerdict:
    repo: str
    verdict: str
    claim_required: bool
    files: list[str]
    matches: list[str] = field(default_factory=list)
    checked_at: str = ""
    maintainer_evidence: str = ""
    rules: int = 0

    @property
    def continues(self) -> bool:
        return self.verdict in ("allows", "allows-with-disclosure")

    def permits(self, allow_unclear: bool = False) -> bool:
        """`continue_on_unclear_policy` lets the agent work where no policy is written down."""
        return self.continues or (allow_unclear and self.verdict == "unclear")


def _sentences(text: str, pattern: re.Pattern[str]) -> list[str]:
    out = []
    for m in pattern.finditer(text):
        start = max(text.rfind("\n", 0, m.start()), text.rfind(". ", 0, m.start())) + 1
        end_candidates = [i for i in (text.find("\n", m.end()), text.find(". ", m.end())) if i != -1]
        end = min(end_candidates) if end_candidates else len(text)
        out.append(text[start:end].strip()[:240])
    return out


def classify(texts: dict[str, str], agent_files: list[str]) -> tuple[str, bool, list[str]]:
    verdict, claim, matches = _classify(texts, agent_files)
    if claim:
        matches = matches + [f"claim: {s}" for s in claim_sentences("\n".join(texts.values()))[:2]]
    return verdict, claim, matches


def _classify(texts: dict[str, str], agent_files: list[str]) -> tuple[str, bool, list[str]]:
    joined = "\n".join(texts.values())
    bans = [s for p in BAN for s in _sentences(joined, p)]
    if bans:
        return "bans", _claim(joined), [f"ban: {s}" for s in bans[:3]]
    disclose = [s for p in DISCLOSE for s in _sentences(joined, p)]
    if disclose:
        return "allows-with-disclosure", _claim(joined), [f"disclose: {s}" for s in disclose[:3]]
    allow = [s for p in ALLOW for s in _sentences(joined, p)]
    if allow:
        return "allows", _claim(joined), [f"allow: {s}" for s in allow[:3]]
    if agent_files:
        return "allows", _claim(joined), [f"repo ships agent instructions: {', '.join(agent_files)}"]
    return "unclear", _claim(joined), []


def _claim(text: str) -> bool:
    return bool(claim_sentences(text))


def claim_sentences(text: str) -> list[str]:
    return [s for p in CLAIM for s in _sentences(text, p)]


def blocked(cache_dir: Path) -> dict[str, dict[str, str]]:
    return read_json(cache_dir / "blocked.json", {})


def is_blocked(cache_dir: Path, repo: str) -> dict[str, str] | None:
    """GitHub repo names are case-insensitive, so the block list is too."""
    return {k.lower(): v for k, v in blocked(cache_dir).items()}.get(repo.lower())


def block(cache_dir: Path, repo: str, why: str, evidence: str) -> None:
    """A maintainer said no to AI contributions. Permanent: no cache expiry or re-check undoes it."""
    repos = blocked(cache_dir)
    if not is_blocked(cache_dir, repo):
        repos[repo] = {"why": why, "evidence": evidence, "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        write_json(cache_dir / "blocked.json", repos)


def check(gh: GitHub, repo: str, cache_dir: Path, ttl_days: int = 30, refresh: bool = False) -> PolicyVerdict:
    stop = is_blocked(cache_dir, repo)
    if stop:
        return PolicyVerdict(repo, "bans", False, [], [f"maintainer said no: {stop['why']}"], stop["at"], stop["evidence"])
    cache = cache_dir / f"{repo.replace('/', '__')}.json"
    cached = read_json(cache, None)
    if cached and not refresh and cached.get("rules") == RULES:
        age = datetime.now(timezone.utc) - datetime.fromisoformat(cached["checked_at"])
        if age < timedelta(days=ttl_days):
            return PolicyVerdict(**cached)
    texts: dict[str, str] = {}
    for path in POLICY_FILES:
        text = gh.file_text(repo, path)
        if text:
            texts[path] = text
    for path in gh.list_dir(repo, ".github/PULL_REQUEST_TEMPLATE"):
        text = gh.file_text(repo, path)
        if text:
            texts[path] = text
    present_agent_files = [p for p in AGENT_FILES if gh.file_text(repo, p) is not None]
    verdict, claim, matches = classify(texts, present_agent_files)
    result = PolicyVerdict(repo, verdict, claim, sorted(texts) + present_agent_files, matches, datetime.now(timezone.utc).isoformat(timespec="seconds"), rules=RULES)
    write_json(cache, asdict(result))
    return result


def apply_maintainer_stance(verdict: PolicyVerdict, hits: list[dict[str, Any]], cache_dir: Path) -> PolicyVerdict:
    """For `unclear` repos: a maintainer rejecting AI PRs in past discussion turns it into `bans`."""
    for hit in hits:
        text = " ".join(p.get("text", "") for p in hit.get("passages", []))
        for p in BAN:
            found = _sentences(text, p)
            if found:
                verdict.verdict = "bans"
                verdict.maintainer_evidence = hit.get("url", "")
                verdict.matches.append(f"maintainer discussion: {found[0]}")
                write_json(cache_dir / f"{verdict.repo.replace('/', '__')}.json", asdict(verdict))
                block(cache_dir, verdict.repo, found[0], verdict.maintainer_evidence)
                return verdict
    return verdict
