"""Assertions run inside the disposable wheel environment."""

import asyncio
from importlib.metadata import distribution
from pathlib import Path
import subprocess
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import rdt
from rdt.core import add, init
from rdt.i18n import available_langs


async def check_mcp() -> None:
    command = str(Path(sys.executable).parent / "rdt-mcp")
    async with stdio_client(StdioServerParameters(command=command)) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            result = await session.call_tool("rdt_list", {})
            assert not result.isError
            assert "postgres" in str(result.content).lower()


def main() -> None:
    metadata = distribution("rdt-rambo")
    assert metadata.metadata["Name"] == "rdt-rambo"
    assert metadata.version == rdt.__version__
    cli = Path(sys.executable).parent / "rdt"
    assert metadata.version in subprocess.check_output([str(cli), "--version"], text=True)
    assert {"en", "ru"} <= set(available_langs())
    compose = Path.cwd() / "compose.yml"
    init(compose)
    add("nginx-proxy", compose, set_vars={"nginx_upstream": "app:8000"})
    assert "app:8000" in (Path.cwd() / "nginx" / "nginx.conf").read_text()
    asyncio.run(check_mcp())


if __name__ == "__main__":
    main()
