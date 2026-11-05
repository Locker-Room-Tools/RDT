"""Public preview contracts: read-only operation, parity, and secret isolation."""
from __future__ import annotations

import json
import asyncio
from pathlib import Path
import subprocess
from typing import Any

import pytest
from typer.testing import CliRunner

from rdt import core
from rdt.cli import app
from rdt.mcp_server import rdt_add, rdt_init, rdt_remove
from rdt.preview import PreviewResult


def snapshot(root: Path) -> dict[str, bytes | None]:
    return {str(p.relative_to(root)): p.read_bytes() if p.is_file() else None
            for p in root.rglob("*")} if root.exists() else {}


@pytest.mark.parametrize("service", ["postgres", "nginx-proxy", "traefik", "pgadmin", "prometheus"])
def test_add_preview_never_writes_or_launches_processes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                       service: str) -> None:
    target = tmp_path / "missing" / "compose.yml"

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("Preview attempted a write, password generation, or external process")

    original_open = Path.open

    def readonly_open(path: Path, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
        if any(flag in mode for flag in "wax+"):
            forbidden()
        return original_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", forbidden)
    monkeypatch.setattr(Path, "open", readonly_open)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr("rdt.env_manager.generate_password", forbidden)
    result = core.add(service, target, hardcore=True, dry_run=True)
    assert isinstance(result, PreviewResult)
    assert result.operation == "add"
    assert not target.parent.exists()
    assert any(action.path == str(target.resolve()) and action.action == "create" for action in result.actions)


def test_init_preview_matches_created_paths_and_respects_force(tmp_path: Path) -> None:
    file = tmp_path / "nested" / "compose.yml"
    preview = core.init(file, dry_run=True)
    assert isinstance(preview, PreviewResult)
    assert not file.parent.exists()
    core.init(file)
    created_files = {a.path for a in preview.actions if a.kind != "directory" and a.action == "create"}
    assert created_files == {str(p.resolve()) for p in file.parent.iterdir() if p.is_file()}
    with pytest.raises(core.RdtError, match="already exists"):
        core.init(file, dry_run=True)
    before = snapshot(tmp_path)
    core.init(file, force=True, dry_run=True)
    assert snapshot(tmp_path) == before


def test_proxy_preview_and_execution_agree(tmp_path: Path) -> None:
    file = tmp_path / "compose.yml"
    result = core.add("nginx-proxy", file, port=9080, set_vars={"nginx_upstream": "backend:9000"}, dry_run=True)
    assert isinstance(result, PreviewResult)
    config_action = next(a for a in result.actions if a.path.endswith("nginx/nginx.conf"))
    assert "server backend:9000;" in config_action.diff
    assert "9080:80" in next(a.diff for a in result.actions if a.path == str(file))
    core.add("nginx-proxy", file, port=9080, set_vars={"nginx_upstream": "backend:9000"})
    assert "server backend:9000;" in (tmp_path / "nginx/nginx.conf").read_text()
    created = {a.path for a in result.actions if a.action == "create"}
    actual = {str(p.resolve()) for p in tmp_path.rglob("*")}
    assert created == actual


def test_preview_hides_known_credentials_and_env_values(tmp_path: Path) -> None:
    file = tmp_path / "compose.yml"
    core.add("postgres", file)
    secret = "Existing-Credential-Do-Not-Display"
    (tmp_path / ".env").write_text(f"POSTGRES_PASSWORD={secret}\nPRIVATE_TOKEN=private-token-value\n")
    with file.open("a") as stream:
        stream.write(f"x-private: {secret}\n")
    before = snapshot(tmp_path)
    result = core.add("mysql", file, hardcore=True, dry_run=True)
    serialized = json.dumps(result.as_dict())
    assert secret not in serialized
    assert "private-token-value" not in serialized
    assert "<redacted>" in serialized
    assert "<generated>" in serialized
    assert snapshot(tmp_path) == before


def test_add_preview_skips_existing_companion_file(tmp_path: Path) -> None:
    (tmp_path / "nginx").mkdir()
    config = tmp_path / "nginx/nginx.conf"
    config.write_text("user-owned configuration\n")
    result = core.add("nginx-proxy", tmp_path / "compose.yml", dry_run=True)
    action = next(a for a in result.actions if a.path == str(config))
    assert action.action == "skip"
    assert action.diff == ""
    assert config.read_text() == "user-owned configuration\n"


def test_add_preview_render_error_is_a_failure_without_outputs(tmp_path: Path,
                                                              monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*args: Any, **kwargs: Any) -> str:
        raise ValueError("simulated invalid render input")

    monkeypatch.setattr("rdt.artifacts.ArtifactPipeline._render", fail)
    with pytest.raises(core.RdtError, match="invalid render input"):
        core.add("nginx-proxy", tmp_path / "compose.yml", dry_run=True)
    assert snapshot(tmp_path) == {}


@pytest.mark.parametrize("cleanup", [False, True])
def test_remove_preview_preserves_state_and_predicts_cleanup(tmp_path: Path, cleanup: bool) -> None:
    file = tmp_path / "compose.yml"
    core.add("nginx-proxy", file)
    core.add("postgres", file)
    before = snapshot(tmp_path)
    result = core.remove("nginx-proxy", file, clean_artifacts=cleanup, clean_env=cleanup, dry_run=True)
    assert isinstance(result, PreviewResult)
    assert snapshot(tmp_path) == before
    deletion_paths = {a.path for a in result.actions if a.action == "delete"}
    config = tmp_path / "nginx/nginx.conf"
    assert (str(config) in deletion_paths) == cleanup
    core.remove("nginx-proxy", file, clean_artifacts=cleanup, clean_env=cleanup)
    assert config.exists() != cleanup
    assert "postgres:" in file.read_text()
    assert "nginx-proxy:" not in file.read_text()


def test_remove_preview_reports_orphaned_keys_and_dependents(tmp_path: Path) -> None:
    file = tmp_path / "compose.yml"
    core.add("postgres", file)
    core.add("pgadmin", file)
    before = snapshot(tmp_path)
    result = core.remove("postgres", file, clean_env=True, dry_run=True)
    assert result.warnings and "pgadmin" in result.warnings[0]
    env = next(a for a in result.actions if a.path == str(tmp_path / ".env"))
    assert any(item["key"] == "POSTGRES_PASSWORD" and item["action"] == "delete" for item in env.keys)
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("args", [["init"], ["add", "postgres"], ["remove", "postgres"]])
def test_cli_dry_run_is_noninteractive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                     args: list[str]) -> None:
    file = tmp_path / "compose.yml"
    if args[0] == "remove":
        core.add("postgres", file)
    before = snapshot(tmp_path)

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("Dry-run prompted for input")

    monkeypatch.setattr("rdt.cli.run_wizard", forbidden)
    monkeypatch.setattr("questionary.confirm", forbidden)
    result = CliRunner().invoke(app, [*args, "--file", str(file), "--dry-run"])
    assert result.exit_code == 0, result.output
    assert "Preview:" in result.output
    assert snapshot(tmp_path) == before


def test_cli_remove_preview_requires_service_without_prompting(tmp_path: Path) -> None:
    file = tmp_path / "compose.yml"
    core.add("postgres", file)
    result = CliRunner().invoke(app, ["remove", "--file", str(file), "--dry-run"])
    assert result.exit_code == 1
    assert "Specify a service" in result.output


def test_mcp_preview_returns_structured_plans(tmp_path: Path) -> None:
    root = str(tmp_path)
    initialized = rdt_init(project_dir=root, dry_run=True)
    added = rdt_add("postgres", project_dir=root, hardcore=True, dry_run=True)
    assert initialized["dry_run"] is True and initialized["operation"] == "init"
    assert added["status"] == "ok" and added["operation"] == "add"
    assert "env_vars" not in added
    assert snapshot(tmp_path) == {}
    core.add("postgres", tmp_path / "docker-compose.yml")
    before = snapshot(tmp_path)
    removed = rdt_remove("postgres", project_dir=root, clean_env=True, dry_run=True)
    assert removed["dry_run"] is True and removed["operation"] == "remove"
    assert snapshot(tmp_path) == before


def test_preview_locale_keys_match() -> None:
    locale_root = Path(__file__).parents[1] / "rdt/locales"
    english = json.loads((locale_root / "en.json").read_text())
    russian = json.loads((locale_root / "ru.json").read_text())
    assert {k for k in english if k.startswith("preview.")} == {k for k in russian if k.startswith("preview.")}


def test_stdio_mcp_preview_schemas_and_readonly_results(tmp_path: Path) -> None:
    import os
    import sys
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    existing = tmp_path / "existing"
    core.add("postgres", existing / "compose.yml")
    before = snapshot(tmp_path)

    async def exercise() -> None:
        env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1]))
        params = StdioServerParameters(command=sys.executable, args=["-m", "rdt.mcp_server"], env=env)
        async with stdio_client(params) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                await session.initialize()
                schemas = {tool.name: tool.inputSchema for tool in (await session.list_tools()).tools}
                for name in ("rdt_init", "rdt_add", "rdt_remove"):
                    assert schemas[name]["properties"]["dry_run"]["default"] is False
                calls = [
                    ("rdt_init", {"project_dir": str(tmp_path / "new-init")}),
                    ("rdt_add", {"service": "postgres", "hardcore": True,
                                 "project_dir": str(tmp_path / "new-add")}),
                    ("rdt_remove", {"service": "postgres", "project_dir": str(existing),
                                    "clean_env": True}),
                ]
                for name, arguments in calls:
                    response = await session.call_tool(name, {**arguments, "dry_run": True})
                    assert not response.isError
                    result = response.structuredContent or json.loads(response.content[0].text)
                    assert result["status"] == "ok" and result["dry_run"] is True
                    assert result["actions"]
                    assert "env_vars" not in result
                assert not (await session.call_tool("rdt_list", {})).isError

    asyncio.run(exercise())
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("operation", ["init", "remove"])
@pytest.mark.parametrize("environment", ["mapping", "list"])
def test_preview_redacts_secrets_from_original_compose(tmp_path: Path, operation: str, environment: str) -> None:
    file = tmp_path / "compose.yml"
    secret = "known-secret-9ee04c"
    assignment = (f"      POSTGRES_PASSWORD: {secret}\n" if environment == "mapping"
                  else f"      - POSTGRES_PASSWORD={secret}\n")
    file.write_text(f"services:\n  postgres:\n    image: {secret}\n    environment:\n" + assignment)
    before = file.read_bytes()
    result = (core.init(file, force=True, dry_run=True) if operation == "init"
              else core.remove("postgres", file, dry_run=True))
    serialized = json.dumps(result.as_dict())
    assert secret not in serialized
    assert "<redacted>" in serialized
    assert file.read_bytes() == before


def test_force_init_preview_accepts_invalid_compose(tmp_path: Path) -> None:
    file = tmp_path / "compose.yml"
    file.write_text("services: [invalid\n")
    result = core.init(file, force=True, dry_run=True)
    assert result.operation == "init"
    core.init(file, force=True)


def test_remove_without_matching_env_keys_preserves_bytes(tmp_path: Path) -> None:
    file = tmp_path / "compose.yml"
    core.add("postgres", file)
    env = tmp_path / ".env"
    original = b"OTHER=keep\n\n\n"
    env.write_bytes(original)
    preview = core.remove("postgres", file, clean_env=True, dry_run=True)
    assert next(a for a in preview.actions if a.path == str(env)).action == "skip"
    core.remove("postgres", file, clean_env=True)
    assert env.read_bytes() == original
