"""Install and exercise a built wheel in an isolated temporary environment."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import venv


def main() -> None:
    wheel = Path(sys.argv[1]).resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix="rdt-wheel-smoke-") as temp:
        root = Path(temp)
        env_dir = root / "venv"
        venv.create(env_dir, with_pip=True)
        scripts = env_dir / ("Scripts" if os.name == "nt" else "bin")
        python = scripts / ("python.exe" if os.name == "nt" else "python")
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        subprocess.run([str(python), "-m", "pip", "install", f"{wheel}[mcp]"], cwd=root, env=env, check=True)
        for command in ("--help", "--version"):
            subprocess.run([str(scripts / "rdt"), command], cwd=root, env=env, check=True)
        subprocess.run([str(python), "-I", str(Path(__file__).with_name("wheel_probe.py"))], cwd=root, env=env, check=True)


if __name__ == "__main__":
    main()
