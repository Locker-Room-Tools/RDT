"""Public lifecycle and interface contracts without a Docker daemon."""

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from typer.testing import CliRunner

from rdt import core, mcp_server
from rdt.cli import app
from rdt.yaml_manager import load_compose


def test_project_lifecycle_preserves_unrelated_environment(tmp_path: Path) -> None:
    compose = tmp_path / "compose.yml"
    (tmp_path / ".env").write_text("KEEP_ME=value\n")
    core.init(compose)
    result = core.add("postgres", compose)
    assert result.service == "postgres"
    assert "postgres" in load_compose(compose)["services"]
    assert "POSTGRES_PASSWORD" in (tmp_path / ".env").read_text()
    removed = core.remove("postgres", compose, clean_env=True)
    assert removed.removed == "postgres"
    assert "postgres" not in load_compose(compose)["services"]
    assert (tmp_path / ".env").read_text().strip() == "KEEP_ME=value"
    with pytest.raises(core.RdtError):
        core.remove("postgres", compose)
    with pytest.raises(core.RdtError):
        core.init(compose)


def test_remove_cleans_generated_artifact(tmp_path: Path) -> None:
    compose = tmp_path / "compose.yml"
    core.init(compose)
    core.add("nginx-proxy", compose, set_vars={"nginx_upstream": "app:8000"})
    artifact = tmp_path / "nginx" / "nginx.conf"
    unrelated = tmp_path / "keep.txt"
    unrelated.write_text("keep")
    assert artifact.exists()
    core.remove("nginx-proxy", compose, clean_artifacts=True)
    assert not artifact.exists()
    assert unrelated.read_text() == "keep"


def test_check_and_up_propagate_process_outcomes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    compose = tmp_path / "compose.yml"
    core.init(compose)
    calls: list[list[str]] = []

    def fake_run(command: list[str], **kwargs: Any) -> SimpleNamespace:
        calls.append(command)
        return SimpleNamespace(returncode=1, stdout="", stderr="invalid config")

    monkeypatch.setattr(core.subprocess, "run", fake_run)
    checked = core.check(compose)
    assert not checked.valid and checked.error == "invalid config"
    started = core.up(compose, detach=False)
    assert started.returncode == 1
    assert calls == [["docker", "compose", "-f", str(compose), "config"],
                     ["docker", "compose", "-f", str(compose), "up"]]
    with pytest.raises(core.RdtError):
        core.check(tmp_path / "missing.yml")


def test_doctor_propagates_checks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    checks = [SimpleNamespace(name="docker", status="warn", message="unavailable", details=[])]
    monkeypatch.setattr(core, "run_all_checks", lambda file, root: checks)
    result = core.doctor(tmp_path / "compose.yml")
    assert result.summary == {"ok": 0, "warn": 1, "error": 0, "skip": 0}
    assert result.checks[0]["message"] == "unavailable"


def test_cli_exit_codes_and_default_compose_resolution(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    assert runner.invoke(app, ["add", "not-a-service", "--yes"]).exit_code == 1
    assert runner.invoke(app, ["init", "--file", "compose.yml"]).exit_code == 0
    assert runner.invoke(app, ["init"]).exit_code == 1
    assert not (tmp_path / "docker-compose.yml").exists()


def test_mcp_results_and_errors_use_project_directory(tmp_path: Path) -> None:
    result = mcp_server.rdt_init(file="compose.yml", project_dir=str(tmp_path))
    assert result["status"] == "ok"
    assert Path(result["file"]) == tmp_path / "compose.yml"
    assert mcp_server.rdt_init(project_dir=str(tmp_path))["status"] == "error"
    assert mcp_server.rdt_add("not-a-service", project_dir=str(tmp_path))["status"] == "error"
    assert any(p["name"] == "postgres" for p in mcp_server.rdt_list()["presets"])


def test_mcp_doctor_propagates_summary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    expected = core.DoctorResult(checks=[{"name": "docker", "status": "error"}], summary={"error": 1})
    monkeypatch.setattr(mcp_server, "doctor", lambda file: expected)
    assert mcp_server.rdt_doctor(project_dir=str(tmp_path)) == {
        "checks": expected.checks, "summary": expected.summary
    }
