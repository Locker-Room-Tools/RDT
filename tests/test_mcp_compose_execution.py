import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from rdt import core


def test_capture_results_and_bounded_invalid_bytes(tmp_path: Path) -> None:
    script = "import sys; sys.stdout.buffer.write(b'x' * 70000 + b'\\xffEND'); sys.stderr.write('warning')"
    result = core._execute_captured([sys.executable, "-c", script], 5)
    assert result.status == "ok" and result.returncode == 0
    assert result.stdout.endswith("�END") and result.stdout_truncated
    assert len(result.stdout.encode()) <= 65536
    assert result.stderr == "warning" and not result.stderr_truncated
    failed = core._execute_captured([sys.executable, "-c", "import sys; sys.exit(7)"], 5)
    assert (failed.status, failed.code, failed.returncode) == ("error", "command_failed", 7)
    missing = core._execute_captured([str(tmp_path / "missing")], 5)
    assert (missing.code, missing.returncode) == ("executable_not_found", None)


@pytest.mark.parametrize("timeout", [0, -1, float("nan"), float("inf")])
def test_invalid_timeout_rejected_before_spawn(timeout: float) -> None:
    with patch("rdt.core.subprocess.Popen") as spawn:
        with pytest.raises(core.RdtError):
            core._execute_captured(["docker"], timeout)
        spawn.assert_not_called()


def test_timeout_kills_and_reaps_process() -> None:
    result = core._execute_captured([sys.executable, "-c", "import time; time.sleep(30)"], 0.1)
    assert result.code == "timeout" and result.returncode is not None
    assert "may already have changed" in result.message


@pytest.mark.skipif(os.name != "posix", reason="POSIX process groups")
def test_timeout_reaps_process_group() -> None:
    process = MagicMock(pid=12345, returncode=-9)
    process.wait.side_effect = [subprocess.TimeoutExpired(["docker"], 1), -9]
    with patch("rdt.core.subprocess.Popen", return_value=process), patch("rdt.core.os.killpg") as killpg:
        result = core._execute_captured(["docker"], 1)
    killpg.assert_called_once_with(12345, core.signal.SIGKILL)
    assert process.wait.call_args_list == [call(timeout=1), call()]
    assert result.code == "timeout"


def test_up_cli_streams_without_timeout(tmp_path: Path) -> None:
    compose = tmp_path / "compose.yml"
    compose.touch()
    with patch("rdt.core.subprocess.run", return_value=subprocess.CompletedProcess([], 0)) as run:
        result = core.up(compose, detach=False)
    assert result.returncode == 0
    run.assert_called_once_with(["docker", "compose", "-f", str(compose), "up"])


def test_stdio_mcp_compose_and_recovery(tmp_path: Path) -> None:
    pytest.importorskip("mcp")
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    compose = tmp_path / "compose.yml"
    compose.touch()
    docker = tmp_path / "docker"
    docker.write_text(f"#!{sys.executable}\nimport sys, time\n"
                      "print('docker stdout', flush=True)\n"
                      "print('docker stderr', file=sys.stderr, flush=True)\n"
                      "if 'config' in sys.argv: sys.exit(9)\n"
                      "if '-d' not in sys.argv: time.sleep(30)\n")
    docker.chmod(0o755)
    env = dict(os.environ, PATH=str(tmp_path))
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])

    async def exercise() -> None:
        params = StdioServerParameters(command=sys.executable, args=["-m", "rdt.mcp_server"], env=env)
        async with stdio_client(params) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                await session.initialize()
                schemas = {tool.name: tool.inputSchema for tool in (await session.list_tools()).tools}
                assert schemas["rdt_up"]["properties"]["timeout_seconds"]["default"] == 120
                async def call(name: str, **kwargs: object) -> dict:
                    response = await session.call_tool(name, kwargs)
                    assert not response.isError
                    return response.structuredContent or json.loads(response.content[0].text)

                args = {"file": str(compose)}
                ok = await call("rdt_up", **args)
                assert ok["status"] == "ok" and "docker stdout" in ok["stdout"]
                assert "docker stderr" in ok["stderr"]
                assert (await call("rdt_list"))
                failed = await call("rdt_check", **args)
                assert failed["code"] == "command_failed" and failed["returncode"] == 9
                assert (await call("rdt_list"))
                timed = await call("rdt_up", **args, detach=False, timeout_seconds=0.1)
                assert timed["code"] == "timeout" and "may already have changed" in timed["message"]
                assert (await call("rdt_list"))
                invalid = await call("rdt_up", **args, timeout_seconds=0)
                assert invalid["status"] == "error"
                docker.unlink()
                missing = await call("rdt_up", **args)
                assert missing["code"] == "executable_not_found"
                assert (await call("rdt_list"))

    asyncio.run(exercise())
