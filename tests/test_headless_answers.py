import subprocess
import sys

from typer.testing import CliRunner

from rdt import core
from rdt.answers import build_script_answers
from rdt.cli import app
from rdt.mcp_server import rdt_add
from rdt.presets.catalog import ALL_PRESETS


def test_import_and_add_with_ui_imports_blocked(tmp_path):
    code = """
import builtins
from pathlib import Path
real_import = builtins.__import__
def blocked(name, *args, **kwargs):
    if name.split(".")[0] in {"typer", "questionary", "rich"}:
        raise ImportError(name)
    return real_import(name, *args, **kwargs)
builtins.__import__ = blocked
from rdt import core, mcp_server
assert core.list_presets()
core.add("postgres", Path(__import__("sys").argv[1]) / "compose.yml")
"""
    result = subprocess.run([sys.executable, "-c", code, str(tmp_path)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_preparation_preserves_defaults_and_first_parent():
    postgres = build_script_answers(ALL_PRESETS["postgres"], None, None, [], False, [])
    assert postgres["port"] == ALL_PRESETS["postgres"].default_port
    assert postgres["volume_source"] == "postgres_data"
    answers = build_script_answers(ALL_PRESETS["pgadmin"], 1234, None, [], False, ["postgres", "postgres2"])
    assert answers["port"] == 1234
    assert answers["parent_service"] == "postgres"


def test_cli_and_mcp_create_equivalent_projects(tmp_path):
    cli_dir = tmp_path / "cli"
    mcp_dir = tmp_path / "mcp"
    cli_dir.mkdir()
    mcp_dir.mkdir()
    result = CliRunner().invoke(app, ["add", "nginx-proxy", "--yes", "--file", str(cli_dir / "compose.yml"), "--port", "8081", "--set", "nginx_server_name=example.test"])
    assert result.exit_code == 0, result.output
    response = rdt_add("nginx-proxy", project_dir=str(mcp_dir), file="compose.yml", port=8081, set_vars={"nginx_server_name": "example.test"})
    assert response["status"] == "ok", response
    for name in ("compose.yml", "nginx/nginx.conf"):
        assert (cli_dir / name).read_bytes() == (mcp_dir / name).read_bytes()
    assert "example.test" in (cli_dir / "nginx/nginx.conf").read_text()


def test_set_vars_overrides_explicit_port(tmp_path):
    core.add("postgres", tmp_path / "compose.yml", port=1234, set_vars={"port": "4321"})
    assert "4321:5432" in (tmp_path / "compose.yml").read_text()


def test_interactive_wizard_uses_selected_values(monkeypatch):
    from rdt import wizard

    monkeypatch.setattr(wizard, "_ask_port", lambda preset: 8088)
    monkeypatch.setattr(wizard, "_ask_container_name", lambda preset: "chosen")
    monkeypatch.setattr(wizard, "_ask_network", lambda: ("bridge", "shared"))
    monkeypatch.setattr(wizard, "_ask_expose_ports", lambda: True)
    monkeypatch.setattr(wizard, "_ask_healthcheck_params", lambda preset: {})
    monkeypatch.setattr(wizard, "_SERVICE_EXTRA_WIZARDS", {})
    answers = wizard.run_wizard(ALL_PRESETS["nginx-proxy"], [])
    assert answers["port"] == 8088
    assert answers["container_name"] == "chosen"
    assert answers["network_name"] == "shared"
    assert wizard.build_script_answers is build_script_answers


def test_database_and_admin_preparation_with_explicit_options():
    database = build_script_answers(
        ALL_PRESETS["postgres"], 15432, "custom_data", ["redis"], True, [],
        container_name="db1", no_ports=True, network="shared", hc_retries=9,
    )
    assert database["port"] == 15432
    assert database["volume_source"] == "custom_data"
    assert database["container_name"] == "db1"
    assert database["use_default_creds"] is False
    assert database["network_type"] == "external"
    assert database["network_name"] == "shared"
    assert database["expose_ports"] is False
    assert database["healthcheck_params"]["retries"] == 9
    assert database["depends_on"] == ["redis"]

    admin = build_script_answers(ALL_PRESETS["pgadmin"], None, None, [], False,
                                 ["postgres_b", "postgres_a"])
    assert admin["parent_service"] == "postgres_b"
    assert admin["smart_env"]["PGADMIN_DEFAULT_SERVER"] == "postgres_b"
    assert admin["depends_on"] == ["postgres_b"]
    proxy = build_script_answers(ALL_PRESETS["nginx-proxy"], None, None, [], False, [])
    assert proxy["nginx_upstream"] == "app:8000"
    assert proxy["nginx_server_name"] == "localhost"


def test_database_and_admin_cli_mcp_outputs_match(tmp_path):
    cli_dir = tmp_path / "cli"
    mcp_dir = tmp_path / "mcp"
    cli_dir.mkdir()
    mcp_dir.mkdir()
    runner = CliRunner()
    for service in ("postgres", "pgadmin"):
        result = runner.invoke(app, ["add", service, "--yes", "--file", str(cli_dir / "compose.yml")])
        assert result.exit_code == 0, result.output
        response = rdt_add(service, file="compose.yml", project_dir=str(mcp_dir))
        assert response["status"] == "ok", response
    for name in ("compose.yml", ".env", ".env.example"):
        assert (cli_dir / name).read_bytes() == (mcp_dir / name).read_bytes()
    compose = (cli_dir / "compose.yml").read_text()
    assert "PGADMIN_DEFAULT_SERVER: postgres" in compose
    assert "POSTGRES_PASSWORD" in (cli_dir / ".env").read_text()
