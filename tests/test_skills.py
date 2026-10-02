"""Structure checks for the skills, so a broken path or index entry fails here, not in a cron run."""

import re
from pathlib import Path

import yaml

SKILLS = Path(__file__).resolve().parents[1] / "skills"
COPIED_AS_IS = {"deslop", "make-pr-easy-to-review", "show-me-your-work", "systematic-debugging", "unslop"}
INDEX_LIMIT = 60  # Hermes truncates descriptions past this in the skill index (agent/skill_utils.py)


def frontmatter(path: Path) -> dict:
    return yaml.safe_load(path.read_text().split("---")[1])


def test_every_skill_has_name_matching_folder_and_short_description():
    for skill_md in SKILLS.glob("*/SKILL.md"):
        fm = frontmatter(skill_md)
        assert fm["name"] == skill_md.parent.name, skill_md
        assert fm["description"], skill_md
        if skill_md.parent.name not in COPIED_AS_IS:
            assert len(fm["description"]) <= INDEX_LIMIT, skill_md


def test_router_points_at_files_that_exist():
    router = (SKILLS / "pr-agent-mode" / "SKILL.md").read_text()
    playbooks = set(re.findall(r"\(`([a-z-]+\.md)`\)", router))
    assert len(playbooks) == 14
    for name in playbooks:
        assert (SKILLS / "pr-agent-mode" / "references" / "playbooks" / name).exists(), name
    principles = set(re.findall(r"\*\*(principle-[a-z-]+)\.\*\*", router))
    assert len(principles) == 7
    for name in principles:
        assert (SKILLS / "pr-agent-mode" / "references" / "principles" / f"{name}.md").exists(), name


def test_skills_named_in_router_exist():
    router = (SKILLS / "pr-agent-mode" / "SKILL.md").read_text()
    named = set(re.findall(r"\*\*([a-z]+(?:-[a-z]+)+)\*\*", router)) - {n for n in re.findall(r"principle-[a-z-]+", router)}
    folders = {p.name for p in SKILLS.iterdir() if p.is_dir()}
    missing = {n for n in named if not n.startswith("principle-")} - folders
    assert not missing, missing


def test_pr_agent_commands_in_skills_exist():
    from pr_agent.cli import build_parser

    sub = next(a for a in build_parser()._actions if a.dest == "cmd")
    commands = set(sub.choices)
    used = set()
    for md in SKILLS.rglob("*.md"):
        used |= set(re.findall(r"`pr-agent ([a-z-]+)", md.read_text()))
    assert used, "no pr-agent commands referenced"
    assert used <= commands, used - commands
