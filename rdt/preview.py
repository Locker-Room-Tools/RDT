"""Read-only, secret-aware presentation of prepared project changes."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from difflib import unified_diff
from pathlib import Path
import re
from typing import Any, Literal

from rdt.env_manager import is_secret_key

Action = Literal["create", "update", "delete", "skip"]


@dataclass
class PreviewAction:
    path: str
    kind: Literal["file", "directory", "environment"]
    action: Action
    diff: str = ""
    keys: list[dict[str, str]] = field(default_factory=list)


@dataclass
class PreviewResult:
    operation: str
    project_root: str
    actions: list[PreviewAction] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {"status": "ok", "dry_run": True, **asdict(self)}


def env_entries(content: str) -> dict[str, str]:
    """Read simple env assignments using the same key rules as env writes."""
    entries: dict[str, str] = {}
    for line in content.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key, _, value = stripped.partition("=")
            entries[key.strip()] = value.strip().strip("\"'")
    return entries


def known_secrets(root: Path, *mappings: dict[str, Any]) -> set[str]:
    """Collect values classified as credentials without returning them to clients."""
    values: set[str] = set()

    def collect(mapping: dict[str, Any]) -> None:
        for key, value in mapping.items():
            if isinstance(value, dict):
                collect(value)
            elif is_secret_key(str(key)) and value is not None:
                text = str(value).strip().strip("\"'")
                if text and text not in {"<redacted>", "<generated>"} and not text.startswith("${"):
                    values.add(text)

    env_file = root / ".env"
    if env_file.is_file():
        collect(env_entries(env_file.read_text(encoding="utf-8")))
    for mapping in mappings:
        collect(mapping)
    return values


_CREDENTIAL_LINE = re.compile(
    r"(?im)^([^\n]*?(?:password|secret|token|api[_-]?key|private[_-]?key|passwd)"
    r"[^\s:=\n]*[\"']?\s*[:=]\s*)([^\n]+)$"
)


def redact(content: str, secrets: set[str]) -> str:
    """Hide known credential literals and credential-bearing assignment lines."""
    for secret in sorted(secrets, key=len, reverse=True):
        content = content.replace(secret, "<redacted>")
    return _CREDENTIAL_LINE.sub(
        lambda match: match.group(0) if re.fullmatch(r"[\"\']?\$\{[^}]+\}[\"\']?", match.group(2).strip())
        else match.group(1) + "<redacted>", content,
    )


class PreviewBuilder:
    """Build display-only plans. All methods only read the filesystem."""

    def __init__(self, operation: str, root: Path, secrets: set[str] | None = None) -> None:
        self.root = root.resolve()
        self.secrets = secrets or set()
        self.result = PreviewResult(operation=operation, project_root=str(self.root))
        self._directories: set[Path] = set()

    def directory(self, path: Path, *, include_existing: bool = True) -> None:
        path = path.resolve()
        if path in self._directories:
            return
        if not path.exists() and path.parent != path:
            self.directory(path.parent, include_existing=False)
        if path.exists() and not include_existing:
            return
        self._directories.add(path)
        self.result.actions.append(PreviewAction(
            path=str(path), kind="directory", action="skip" if path.exists() else "create",
        ))

    def file(self, path: Path, content: str | None, *, skip: bool = False) -> None:
        try:
            before = path.read_text(encoding="utf-8") if path.is_file() and not skip else ""
        except UnicodeDecodeError:
            before = "[binary content omitted]\n"
        exists = path.exists()
        if skip or (content is not None and exists and before == content):
            action: Action = "skip"
        elif content is None:
            action = "delete" if exists else "skip"
        else:
            action = "update" if exists else "create"
            self.directory(path.parent, include_existing=False)
        diff = ""
        if action != "skip":
            diff = "".join(unified_diff(
                redact(before, self.secrets).splitlines(keepends=True),
                redact(content or "", self.secrets).splitlines(keepends=True),
                fromfile=str(path) if exists else "/dev/null",
                tofile=str(path) if content is not None else "/dev/null",
            ))
        self.result.actions.append(PreviewAction(str(path.resolve()), "file", action, diff))

    def environment(self, path: Path, values: dict[str, str], *, remove: set[str] | None = None,
                    create_empty: bool = False) -> None:
        content = path.read_text(encoding="utf-8") if path.is_file() else ""
        existing = env_entries(content)
        keys = []
        for key in sorted(set(existing) | set(values)):
            action = "delete" if remove and key in remove and key in existing else (
                "create" if key in values and key not in existing else "skip"
            )
            entry = {"key": key, "action": action}
            if action == "create" and is_secret_key(key):
                entry["value"] = "<generated>" if values.get(key) == "<generated>" else "<redacted>"
            keys.append(entry)
        changed = any(item["action"] != "skip" for item in keys)
        action: Action = ("update" if path.exists() else "create") if changed or (
            create_empty and not path.exists()
        ) else "skip"
        if action == "create":
            self.directory(path.parent, include_existing=False)
        self.result.actions.append(PreviewAction(str(path.resolve()), "environment", action, keys=keys))

    def delete_path(self, path: Path) -> None:
        if path.is_dir():
            self.result.actions.append(PreviewAction(str(path.resolve()), "directory", "delete"))
        else:
            self.file(path, None)
