"""
RDT Core — business logic without CLI dependencies (Rich / Typer / questionary).

Used by the MCP server and available to any other client.
All functions accept typed parameters and return dataclass results.
Errors are raised as RdtError.
"""
from __future__ import annotations

import math
import os
import signal
import subprocess
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rdt.presets.catalog import ALL_PRESETS
from rdt.strategies.base import NETWORK_NAME
from rdt.strategies.factory import get_strategy
from rdt.yaml_manager import (
    load_compose, save_compose, make_base_compose, inject_service,
    get_existing_services, get_services_with_healthcheck,
    get_dependents, remove_service,
)
from rdt.env_manager import (
    get_env_values, write_env, write_env_example,
    find_orphaned_vars, remove_vars_from_env_file,
)
from rdt.answers import build_script_answers
from rdt.artifacts import (
    ArtifactContext, ArtifactPipeline, ArtifactResult,
    ScaffoldPipeline, ScaffoldResult,
)
from rdt.doctor import run_all_checks

# ─────────────────────────────────────────────────────────────────────────────
# Exception
# ─────────────────────────────────────────────────────────────────────────────

class RdtError(Exception):
    """RDT business-logic error."""


# ─────────────────────────────────────────────────────────────────────────────
# Result types
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class InitResult:
    file: str
    created: list[str]


@dataclass
class AddResult:
    service: str
    port: int
    env_vars: dict[str, str]
    artifacts_created: list[str]
    hints: list[str]


@dataclass
class RemoveResult:
    removed: str
    removed_volumes: list[str]
    cleaned_env_vars: list[str]
    cleaned_files: list[str]
    dependents_warned: list[str]


@dataclass
class PresetInfo:
    name: str
    display_name: str
    category: str
    image: str
    default_port: int
    container_port: int
    has_healthcheck: bool


@dataclass
class DoctorResult:
    checks: list[dict[str, Any]]
    summary: dict[str, int]


@dataclass
class ComposeCheckResult:
    valid: bool
    error: str | None = None
    config: str | None = None


@dataclass
class UpResult:
    command: str
    returncode: int


@dataclass
class ExecutionResult:
    status: str
    command: str
    returncode: int | None = None
    stdout: str = ""
    stderr: str = ""
    stdout_truncated: bool = False
    stderr_truncated: bool = False
    code: str | None = None
    message: str | None = None


_DIAGNOSTIC_LIMIT = 64 * 1024


def _diagnostic_tail(stream: Any) -> tuple[str, bool]:
    size = stream.seek(0, os.SEEK_END)
    stream.seek(max(0, size - _DIAGNOSTIC_LIMIT))
    decoded = stream.read().decode("utf-8", errors="replace")
    encoded = decoded.encode("utf-8")
    truncated = size > _DIAGNOSTIC_LIMIT or len(encoded) > _DIAGNOSTIC_LIMIT
    return encoded[-_DIAGNOSTIC_LIMIT:].decode("utf-8", errors="ignore"), truncated


def _execute_captured(cmd: list[str], timeout_seconds: float) -> ExecutionResult:
    """Run a bounded subprocess without exposing child streams to MCP transport."""
    if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
        raise RdtError("timeout_seconds must be a positive finite number")
    command = " ".join(cmd)
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        try:
            process = subprocess.Popen(
                cmd, stdout=stdout, stderr=stderr, start_new_session=(os.name == "posix"),
            )
        except FileNotFoundError:
            return ExecutionResult(status="error", command=command, code="executable_not_found",
                                   message="Docker executable not found")
        timed_out = False
        try:
            process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            if os.name == "posix":
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            else:
                process.kill()
            process.wait()
        out, out_truncated = _diagnostic_tail(stdout)
        err, err_truncated = _diagnostic_tail(stderr)
    code = "timeout" if timed_out else "command_failed" if process.returncode else None
    return ExecutionResult(
        status="error" if code else "ok", command=command, returncode=process.returncode,
        stdout=out, stderr=err, stdout_truncated=out_truncated, stderr_truncated=err_truncated,
        code=code, message="The stack may already have changed." if timed_out else None,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────────────────────────────────────

def _resolve_root(file: Path) -> Path:
    """Resolve the project root in the same way as the CLI."""
    return file.parent.resolve()


def _get_artifact_paths(service_name: str, project_root: Path) -> list[Path]:
    preset = ALL_PRESETS.get(service_name)
    if preset is None or not preset.artifacts:
        return []
    return [
        project_root / a.relative_path
        for a in preset.artifacts
        if (project_root / a.relative_path).exists()
    ]


# ─────────────────────────────────────────────────────────────────────────────
# core_init
# ─────────────────────────────────────────────────────────────────────────────

def init(file: Path, force: bool = False) -> InitResult:
    """Create base docker-compose.yml, .env, and .env.example files."""
    if file.exists() and not force:
        raise RdtError(f"File already exists: {file}. Use force=True to overwrite.")

    project_root = _resolve_root(file)
    env_file = project_root / ".env"
    env_example = project_root / ".env.example"

    data = make_base_compose()
    save_compose(file, data)

    created = [str(file)]
    if not env_file.exists():
        env_file.touch()
        created.append(str(env_file))
    if not env_example.exists():
        env_example.touch()
        created.append(str(env_example))

    return InitResult(file=str(file), created=created)


# ─────────────────────────────────────────────────────────────────────────────
# add / add_from_answers / _apply_add
# ─────────────────────────────────────────────────────────────────────────────

def add(
    service: str,
    file: Path,
    *,
    port: int | None = None,
    volume: str | None = None,
    depends_on: list[str] | None = None,
    hardcore: bool = False,
    no_ports: bool = False,
    network: str | None = None,
    container_name: str | None = None,
    hc_interval: str | None = None,
    hc_timeout: str | None = None,
    hc_retries: int | None = None,
    hc_start_period: str | None = None,
    set_vars: dict[str, str] | None = None,
) -> AddResult:
    """Add a service to docker-compose.yml in script/MCP mode."""
    service = service.lower()
    preset = ALL_PRESETS.get(service)
    if preset is None:
        raise RdtError(
            f"Unknown service: '{service}'. "
            f"Available: {', '.join(sorted(ALL_PRESETS.keys()))}"
        )

    if file.exists():
        data = load_compose(file)
        existing = get_existing_services(data)
        svc_with_hc = get_services_with_healthcheck(data)
    else:
        existing = []
        svc_with_hc = set()

    if preset.name in existing:
        raise RdtError(f"Service '{preset.name}' already exists in {file}.")

    answers = build_script_answers(
        preset=preset,
        port=port,
        volume=volume,
        depends_on=depends_on or [],
        hardcore=hardcore,
        existing_services=existing,
        container_name=container_name,
        no_ports=no_ports,
        network=network,
        hc_interval=hc_interval,
        hc_timeout=hc_timeout,
        hc_retries=hc_retries,
        hc_start_period=hc_start_period,
    )
    if set_vars:
        answers.update(set_vars)
    answers["services_with_healthcheck"] = svc_with_hc

    return _apply_add(preset, answers, file, hardcore=hardcore)


def add_from_answers(
    service: str,
    answers: dict[str, Any],
    file: Path,
    hardcore: bool = False,
) -> AddResult:
    """Add a service using a prepared answers dict from CLI wizard mode."""
    service = service.lower()
    preset = ALL_PRESETS.get(service)
    if preset is None:
        raise RdtError(
            f"Unknown service: '{service}'. "
            f"Available: {', '.join(sorted(ALL_PRESETS.keys()))}"
        )

    if file.exists():
        existing = get_existing_services(load_compose(file))
        if preset.name in existing:
            raise RdtError(f"Service '{preset.name}' already exists in {file}.")

    return _apply_add(preset, answers, file, hardcore=hardcore)


def _apply_add(
    preset: Any,
    answers: dict[str, Any],
    file: Path,
    hardcore: bool,
) -> AddResult:
    """Apply answers to compose/env/artifacts through the shared apply path."""
    svc_key = preset.name
    project_root = _resolve_root(file)
    env_file = project_root / ".env"
    env_example = project_root / ".env.example"

    # Compose data in memory.
    if file.exists():
        data = load_compose(file)
        compose_was_new = False
    else:
        net_cfg: dict = {
            "type": answers.get("network_type", "bridge"),
            "name": answers.get("network_name", NETWORK_NAME),
        }
        data = make_base_compose(network_config=net_cfg)
        compose_was_new = True

    env_values = get_env_values(
        preset.default_env,
        hardcore=hardcore or not answers.get("use_default_creds", True),
    )

    strategy = get_strategy(preset, answers)
    service_def = strategy.build()

    net_cfg = {
        "type": answers.get("network_type", "bridge"),
        "name": answers.get("network_name", NETWORK_NAME),
    }
    data = inject_service(data, svc_key, service_def, network_config=net_cfg)

    # Scaffold plan
    scaffold_pipeline: ScaffoldPipeline | None = None
    scaffold_plans = []
    if preset.scaffolds:
        scaffold_pipeline = ScaffoldPipeline(preset.scaffolds, project_root)
        scaffold_plans = scaffold_pipeline.plan()

    # Artifact plan
    pipeline: ArtifactPipeline | None = None
    artifact_plans = []
    if preset.artifacts:
        artifact_ctx = ArtifactContext(
            service_name=svc_key,
            answers=answers,
            env_values=env_values,
            project_root=project_root,
            compose_file=file.resolve(),
            preset=preset,
            smart_env=answers.get("smart_env", {}),
            depends_on=answers.get("depends_on", []),
            parent_service=answers.get("parent_service"),
            service_def=service_def,
        )
        pipeline = ArtifactPipeline(preset.artifacts, artifact_ctx)
        issues = pipeline.preflight()
        if issues:
            raise RdtError(
                "Preflight check failed: "
                + "; ".join(f"{i.artifact_path}: {i.reason}" for i in issues)
            )
        artifact_plans = pipeline.plan()

    # Snapshot all planned targets before the first mutation, including targets
    # whose writes may fail partway through.
    targets = [file, env_file, env_example]
    targets.extend(p.target for p in artifact_plans if p.action in ("create", "overwrite"))
    journal: dict[Path, tuple[bytes, int] | None] = {}
    directories: set[Path] = set()
    for target in targets:
        if target not in journal:
            journal[target] = (target.read_bytes(), stat.S_IMODE(target.stat().st_mode)) if target.exists() else None
        parent = target.parent
        while not parent.exists():
            directories.add(parent)
            parent = parent.parent
    for plan in scaffold_plans:
        parent = plan.target
        while not parent.exists():
            directories.add(parent)
            parent = parent.parent

    scaffold_results: list[ScaffoldResult] = []
    artifact_results: list[ArtifactResult] = []
    try:
        save_compose(file, data)
        write_env(env_file, env_values)
        write_env_example(env_example, env_values)
        if scaffold_pipeline is not None:
            scaffold_results = scaffold_pipeline.apply(scaffold_plans)
            failures = [r for r in scaffold_results if r.has_error]
            if failures:
                raise RuntimeError("Scaffold error: " + "; ".join(f"{r.path}: {r.error}" for r in failures))
        if pipeline is not None:
            artifact_results = pipeline.apply(artifact_plans)
            failures = [r for r in artifact_results if r.has_error]
            if failures:
                raise RuntimeError("Artifact error: " + "; ".join(f"{r.path}: {r.error}" for r in failures))
    except Exception as exc:
        recovery_errors = []
        for path, snapshot in reversed(list(journal.items())):
            try:
                if snapshot is None:
                    path.unlink(missing_ok=True)
                else:
                    content, mode = snapshot
                    path.write_bytes(content)
                    path.chmod(mode)
            except Exception as recovery_exc:
                recovery_errors.append(f"{path}: {type(recovery_exc).__name__}")
        for directory in sorted(directories, key=lambda p: len(p.parts), reverse=True):
            try:
                if directory.is_dir() and not any(directory.iterdir()):
                    directory.rmdir()
            except Exception as recovery_exc:
                recovery_errors.append(f"{directory}: {type(recovery_exc).__name__}")
        reason = str(exc)
        for value in env_values.values():
            if value:
                reason = reason.replace(str(value), "[redacted]")
        outcome = ("Recovery incomplete: " + "; ".join(recovery_errors)
                   if recovery_errors else "Changes restored.")
        raise RdtError(f"Add failed: {reason}. {outcome}") from exc

    return AddResult(
        service=svc_key,
        port=answers.get("port", preset.default_port),
        env_vars=env_values,
        artifacts_created=[str(r.path) for r in artifact_results if r.status == "created"],
        hints=[h.message for h in preset.bootstrap_hints],
    )


# ─────────────────────────────────────────────────────────────────────────────
# _rollback (internal)
# ─────────────────────────────────────────────────────────────────────────────

def _rollback(
    compose_file: Path,
    compose_was_new: bool,
    compose_snapshot: str | None,
    env_file: Path,
    env_existed: bool,
    env_snapshot: str | None,
    env_example: Path,
    env_ex_existed: bool,
    env_ex_snapshot: str | None,
    scaffold_results: list[ScaffoldResult],
    artifact_results: list[ArtifactResult],
) -> None:
    """Best-effort rollback after an apply error."""
    try:
        if compose_was_new:
            if compose_file.exists():
                compose_file.unlink()
        elif compose_snapshot is not None:
            compose_file.write_text(compose_snapshot, encoding="utf-8")
    except Exception:
        pass

    for path, existed, snapshot in [
        (env_file, env_existed, env_snapshot),
        (env_example, env_ex_existed, env_ex_snapshot),
    ]:
        try:
            if not existed:
                if path.exists():
                    path.unlink()
            elif snapshot is not None:
                path.write_text(snapshot, encoding="utf-8")
        except Exception:
            pass

    for r in artifact_results:
        if r.status == "created":
            try:
                if r.path.exists():
                    r.path.unlink()
            except Exception:
                pass

    for r in scaffold_results:
        if r.status == "created":
            try:
                if r.path.exists() and r.path.is_dir() and not any(r.path.iterdir()):
                    r.path.rmdir()
            except Exception:
                pass


# ─────────────────────────────────────────────────────────────────────────────
# core_remove
# ─────────────────────────────────────────────────────────────────────────────

def remove(
    service: str,
    file: Path,
    *,
    clean_env: bool = False,
    clean_artifacts: bool = False,
) -> RemoveResult:
    """Remove a service from docker-compose.yml."""
    if not file.exists():
        raise RdtError(f"Compose file not found: {file}")

    project_root = _resolve_root(file)
    env_file = project_root / ".env"
    env_example = project_root / ".env.example"

    data = load_compose(file)
    existing = get_existing_services(data)
    service = service.lower()

    if service not in existing:
        raise RdtError(
            f"Service '{service}' not found in {file}. "
            f"Available: {', '.join(existing)}"
        )

    dependents = get_dependents(data, service)
    orphaned_vars = find_orphaned_vars(data, service) if clean_env else set()
    artifact_paths = _get_artifact_paths(service, project_root) if clean_artifacts else []

    data, removed_volumes = remove_service(data, service)
    save_compose(file, data)

    cleaned_vars: list[str] = []
    if clean_env and orphaned_vars:
        count = remove_vars_from_env_file(env_file, orphaned_vars)
        remove_vars_from_env_file(env_example, orphaned_vars)
        cleaned_vars = sorted(orphaned_vars) if count else []

    cleaned_files: list[str] = []
    if clean_artifacts and artifact_paths:
        import shutil
        for p in artifact_paths:
            try:
                if p.exists():
                    if p.is_file():
                        p.unlink()
                    else:
                        shutil.rmtree(p)
                    cleaned_files.append(str(p))
            except Exception:
                pass

    return RemoveResult(
        removed=service,
        removed_volumes=list(removed_volumes),
        cleaned_env_vars=cleaned_vars,
        cleaned_files=cleaned_files,
        dependents_warned=dependents,
    )


# ─────────────────────────────────────────────────────────────────────────────
# core_list
# ─────────────────────────────────────────────────────────────────────────────

def list_presets(category: str | None = None) -> list[PresetInfo]:
    """Return the list of available presets."""
    result = []
    for preset in ALL_PRESETS.values():
        if category and preset.category.lower() != category.lower():
            continue
        result.append(PresetInfo(
            name=preset.name,
            display_name=preset.display_name,
            category=preset.category,
            image=preset.image,
            default_port=preset.default_port,
            container_port=preset.container_port,
            has_healthcheck=preset.healthcheck is not None,
        ))
    return result


# ─────────────────────────────────────────────────────────────────────────────
# core_doctor
# ─────────────────────────────────────────────────────────────────────────────

def doctor(file: Path) -> DoctorResult:
    """Run full project diagnostics."""
    project_root = _resolve_root(file)
    results = run_all_checks(file, project_root)

    checks = [
        {
            "name": r.name,
            "status": r.status,
            "message": r.message,
            "details": r.details,
        }
        for r in results
    ]
    summary = {
        "ok":    sum(1 for r in results if r.status == "ok"),
        "warn":  sum(1 for r in results if r.status == "warn"),
        "error": sum(1 for r in results if r.status == "error"),
        "skip":  sum(1 for r in results if r.status == "skip"),
    }
    return DoctorResult(checks=checks, summary=summary)


# ─────────────────────────────────────────────────────────────────────────────
# core_check
# ─────────────────────────────────────────────────────────────────────────────

def check(file: Path, verbose: bool = False, *, timeout_seconds: float | None = None) -> ComposeCheckResult | ExecutionResult:
    """Validate docker-compose.yml through docker compose config."""
    if not file.exists():
        raise RdtError(f"Compose file not found: {file}")

    if timeout_seconds is not None:
        return _execute_captured(["docker", "compose", "-f", str(file), "config"], timeout_seconds)

    result = subprocess.run(
        ["docker", "compose", "-f", str(file), "config"],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        return ComposeCheckResult(
            valid=True,
            config=result.stdout.strip() if verbose else None,
        )
    return ComposeCheckResult(valid=False, error=result.stderr.strip() or result.stdout.strip())


# ─────────────────────────────────────────────────────────────────────────────
# core_up
# ─────────────────────────────────────────────────────────────────────────────

def up(file: Path, detach: bool = True, *, timeout_seconds: float | None = None) -> UpResult | ExecutionResult:
    """Run docker compose up."""
    if not file.exists():
        raise RdtError(f"Compose file not found: {file}")

    cmd = ["docker", "compose", "-f", str(file), "up"]
    if detach:
        cmd.append("-d")

    if timeout_seconds is not None:
        return _execute_captured(cmd, timeout_seconds)
    result = subprocess.run(cmd)
    return UpResult(command=" ".join(cmd), returncode=result.returncode)
