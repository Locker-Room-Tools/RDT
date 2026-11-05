"""Safe replacement of small generated project files."""
from __future__ import annotations

import os
import secrets
import stat
from pathlib import Path


def atomic_write(path: Path, content: bytes) -> None:
    """Write a sibling temporary file and replace the target, retaining its mode."""
    # Preserve the existing behavior of writing through symbolic links.
    if path.is_symlink():
        path = path.resolve()
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else None
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(12)}.tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
        if mode is not None:
            temporary.chmod(mode)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
