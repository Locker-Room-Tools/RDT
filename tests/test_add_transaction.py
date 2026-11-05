from pathlib import Path

import pytest

from rdt import core


@pytest.mark.parametrize("writer", ["save_compose", "write_env", "write_env_example"])
@pytest.mark.parametrize("existing", [False, True])
def test_partial_write_is_rolled_back(tmp_path, monkeypatch, writer, existing):
    paths = [tmp_path / "docker-compose.yml", tmp_path / ".env", tmp_path / ".env.example"]
    if existing:
        paths[0].write_text("services: {}\n")
        for path in paths[1:]:
            path.write_bytes(b"original\n")
        for path in paths:
            path.chmod(0o640)
    before = {p: (p.read_bytes(), p.stat().st_mode & 0o777) for p in paths if p.exists()}

    def fail(path, *args, **kwargs):
        path.write_bytes(b"partial")
        raise OSError("injected write failure")

    monkeypatch.setattr(core, writer, fail)
    with pytest.raises(core.RdtError, match="injected write failure.*Changes restored"):
        core.add("postgres", paths[0])
    for path in paths:
        if path in before:
            assert (path.read_bytes(), path.stat().st_mode & 0o777) == before[path]
        else:
            assert not path.exists()


def test_recovery_continues_after_failure(tmp_path, monkeypatch):
    compose = tmp_path / "docker-compose.yml"
    compose.write_text("services: {}\n")
    original = compose.read_bytes()
    env = tmp_path / ".env"
    env.write_bytes(b"original")
    original_write = Path.write_bytes

    def fail_write(path, data):
        if path == env and data == b"original":
            raise OSError("restore denied")
        return original_write(path, data)

    def fail_example(path, *args):
        path.write_bytes(b"partial")
        raise OSError("injected failure")

    monkeypatch.setattr(Path, "write_bytes", fail_write)
    monkeypatch.setattr(core, "write_env_example", fail_example)
    with pytest.raises(core.RdtError) as error:
        core.add("postgres", compose)
    assert "injected failure" in str(error.value)
    assert "Recovery incomplete" in str(error.value)
    assert str(env) in str(error.value)
    assert compose.read_bytes() == original
    assert not (tmp_path / ".env.example").exists()


def test_overwritten_artifact_and_new_directories_are_recovered(tmp_path, monkeypatch):
    from dataclasses import replace
    from rdt.artifacts import ArtifactDef, ArtifactSourceType, DirectoryDef, OverwritePolicy

    artifact = tmp_path / "config" / "user.conf"
    artifact.parent.mkdir()
    artifact.write_bytes(b"user configuration\x00\xff")
    artifact.chmod(0o640)

    def fail_later(context):
        (context.project_root / "created" / "keep.txt").write_text("untracked")
        raise ValueError("later artifact failed")

    preset = replace(core.ALL_PRESETS["nginx-proxy"], artifacts=[
        ArtifactDef("config/user.conf", source_type=ArtifactSourceType.STATIC,
                    static_content="replacement", overwrite=OverwritePolicy.OVERWRITE),
        ArtifactDef("created/later.conf", source_type=ArtifactSourceType.PYTHON, renderer=fail_later),
    ], scaffolds=[DirectoryDef("created"), DirectoryDef("empty/nested")])
    monkeypatch.setitem(core.ALL_PRESETS, preset.name, preset)
    with pytest.raises(core.RdtError, match="later artifact failed.*Changes restored"):
        core.add(preset.name, tmp_path / "compose.yml")
    assert artifact.read_bytes() == b"user configuration\x00\xff"
    assert artifact.stat().st_mode & 0o777 == 0o640
    assert (tmp_path / "created" / "keep.txt").read_text() == "untracked"
    assert not (tmp_path / "empty").exists()
    assert not (tmp_path / "compose.yml").exists()


@pytest.mark.parametrize("client", ["cli", "mcp"])
@pytest.mark.parametrize("incomplete", [False, True])
def test_clients_report_recovery_outcome(tmp_path, monkeypatch, client, incomplete):
    from typer.testing import CliRunner
    from rdt.cli import app
    from rdt.mcp_server import rdt_add

    compose = tmp_path / "compose.yml"
    compose.write_bytes(b"services: {}\n")
    original = compose.read_bytes()
    write_bytes = Path.write_bytes

    def restore(path, content):
        if incomplete and path == compose and content == original:
            raise OSError("restore denied")
        return write_bytes(path, content)

    def fail_env(path, values):
        path.write_bytes(b"partial")
        raise OSError("injected environment failure")

    monkeypatch.setattr(Path, "write_bytes", restore)
    monkeypatch.setattr(core, "write_env", fail_env)
    if client == "cli":
        result = CliRunner().invoke(app, ["add", "postgres", "--yes", "--file", str(compose)])
        assert result.exit_code != 0
        message = result.output
    else:
        result = rdt_add("postgres", file="compose.yml", project_dir=str(tmp_path))
        assert result["status"] == "error"
        message = result["message"]
    assert "injected environment failure" in message
    assert ("Recovery incomplete" if incomplete else "Changes restored") in message
    if incomplete:
        assert compose.name in message
    else:
        assert compose.read_bytes() == original
    assert not (tmp_path / ".env").exists()


def test_atomic_write_failure_preserves_target_and_cleans_temp(tmp_path, monkeypatch):
    from rdt import file_utils

    target = tmp_path / "config"
    target.write_bytes(b"before")
    target.chmod(0o640)
    def fail_replace(source, destination):
        assert source.parent == destination.parent
        raise OSError("replace failed")
    monkeypatch.setattr(file_utils.os, "replace", fail_replace)
    with pytest.raises(OSError, match="replace failed"):
        file_utils.atomic_write(target, b"after")
    assert target.read_bytes() == b"before"
    assert target.stat().st_mode & 0o777 == 0o640
    assert list(tmp_path.iterdir()) == [target]


def test_recovery_redacts_generated_credentials(tmp_path, monkeypatch):
    monkeypatch.setattr(core, "get_env_values", lambda *args, **kwargs: {"PASSWORD": "unique-generated-secret"})
    def fail(path, values):
        raise OSError("cannot write " + values["PASSWORD"])
    monkeypatch.setattr(core, "write_env", fail)
    with pytest.raises(core.RdtError) as error:
        core.add("postgres", tmp_path / "compose.yml")
    assert "unique-generated-secret" not in str(error.value)
    assert "[redacted]" in str(error.value)
