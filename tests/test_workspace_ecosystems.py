import json

from pr_agent.workspace import detect_ecosystem, detect_test_cmd, node_pm


def make(ws, files):
    ws.mkdir(exist_ok=True)
    for name, body in files.items():
        (ws / name).write_text(body)
    return ws


def test_python_wins_in_mixed_repos(tmp_path):
    assert detect_ecosystem(make(tmp_path / "a", {"pyproject.toml": "", "package.json": "{}"})) == "python"
    assert detect_ecosystem(make(tmp_path / "b", {"package.json": "{}"})) == "node"
    assert detect_ecosystem(make(tmp_path / "c", {"README.md": ""})) == "python"


def test_node_package_manager_from_field_then_lockfile(tmp_path):
    ws = make(tmp_path / "w", {"package.json": json.dumps({"packageManager": "pnpm@9.1.0"}), "yarn.lock": ""})
    assert node_pm(ws) == "pnpm"
    (ws / "package.json").write_text("{}")
    assert node_pm(ws) == "yarn"
    (ws / "yarn.lock").unlink()
    (ws / "bun.lock").write_text("")
    assert node_pm(ws) == "bun"
    (ws / "bun.lock").unlink()
    assert node_pm(ws) == "npm"


def test_node_test_command(tmp_path):
    ws = make(tmp_path / "w", {"package.json": json.dumps({"scripts": {"test": "vitest run"}}), "pnpm-lock.yaml": ""})
    assert detect_test_cmd(ws, "node") == "npx --yes pnpm run test"
    (ws / "pnpm-lock.yaml").unlink()
    assert detect_test_cmd(ws, "node") == "npm test"
    (ws / "package.json").write_text(json.dumps({"scripts": {"test": 'echo "Error: no test specified" && exit 1'}}))
    assert detect_test_cmd(ws, "node") == ""
