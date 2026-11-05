# AGENTS.md — RDT (Rambo Docker Tools)

## Commands

```bash
# Install for development (editable, from repo root)
pip install -e ".[dev,mcp]"

# Run all tests (pytest auto-discovers tests/)
pytest

# Run a single test
pytest tests/test_artifact_pipeline.py::test_nginx_proxy_created

# Run with verbose output
pytest -v

# Build for PyPI
python -m build
```

**No linter, formatter, typechecker, or pre-commit config exists.** Verification uses pytest and isolated package builds. `.github/workflows/verify.yml` runs source tests on Python 3.10 and 3.14 and a clean-wheel smoke check; it does not publish packages.

## Package Identity and Version

| Purpose | Name |
|---|---|
| Distribution (`pip install ...`) | `rdt-rambo` |
| Python import | `rdt` |
| CLI command | `rdt` |
| MCP server command | `rdt-mcp` |
| Legacy distribution (metadata fallback only) | `locker-room-tolls-rdt` |

Remove the legacy distribution before installing `rdt-rambo`; both share the
same import and commands. Runtime lookup prefers canonical metadata, then legacy
metadata, and finally `rdt.__version__` in a source checkout.

## Architecture

### Entry Points (pyproject.toml `[project.scripts]`)
- `rdt = "rdt.cli:app"` — Typer CLI
- `rdt-mcp = "rdt.mcp_server:main"` — MCP server (FastMCP stdio)

### Data Flow
```
cli.py  ──→  core.py  ──→  strategies/  ──→  yaml_manager.py
   │                          │
   │         wizard.py        └──→  env_manager.py
   │           (interactive        └──→  artifacts.py
   │            questionary)              (Jinja2 templates)
   │
   └── mcp_server.py  ──→  core.py  (same path, no UI deps)
```

`core.py` is the **shared kernel** — no Rich/Typer/questionary dependencies. Both CLI and MCP server call it. Core functions: `init`, `add`, `add_from_answers`, `remove`, `list_presets`, `doctor`, `check`, `up`.

### Key Module Responsibilities
| Module | Does |
|---|---|
| `cli.py` | 8 Typer commands, `--version`, `--help`, interactive menu |
| `core.py` | Pure business logic, orchestration, rollback |
| `wizard.py` | Interactive questionary prompts; compatibility re-export of `build_script_answers()` |
| `answers.py` | UI-independent script defaults, smart mapping, and `PreparedAnswers` contract |
| `preview.py` | Read-only change summaries, text diffs, env-key actions, and credential redaction |
| `file_utils.py` | Atomic sibling-file replacement preserving existing permission modes |
| `version.py` | Canonical/legacy distribution lookup with source version fallback |
| `strategies/` | Polymorphic builder classes (database, web_server, monitoring, admin_tool, traefik, base) |
| `yaml_manager.py` | ruamel.yaml read/write, healthcheck `test` inline-flow normalization |
| `env_manager.py` | `.env` / `.env.example` generation, random password generation |
| `artifacts.py` | ArtifactPipeline (Jinja2 → config files) and ScaffoldPipeline (directories) |
| `doctor.py` | 7 diagnostic checks for `rdt doctor` |
| `i18n.py` | Translation engine, `t()` function |
| `smart_mapping.py` | Auto-links admin/monitoring tools to parent services |
| `mcp_server.py` | 7 MCP tools wrapping core.py functions |

## i18n

- Locales: `rdt/locales/en.json`, `ru.json` (~210 keys each)
- Language resolution: `RDT_LANG` env var → `~/.rdt/config.json` → default `"en"`
- Every `t("key")` call **must** have a corresponding key in BOTH locale JSON files. Missing keys return the raw key string (no crash, but ugly).
- `rst lang set XX` creates `~/.rdt/config.json` with `{"lang": "XX"}`
- New language: drop `rdt/locales/<code>.json` with same keys as `en.json` — auto-detected

## Gotchas

### Compose File Auto-Detection
When `--file` is omitted (or is the literal default `docker-compose.yml`), `_resolve_cli_compose_file()` silently checks for `compose.yml`, `compose.yaml`, `docker-compose.yaml` in that order and uses the first one found. Passing `--file ./docker-compose.yml` or an absolute path **bypasses** this resolution.

### Healthcheck YAML Serialization
`yaml_manager.py` normalizes healthcheck `test` arrays to inline flow style (`test: [CMD-SHELL, ...]`). If you manually add block-style `test:`, `save_compose()` will convert it.

### Version Reporting
`rdt --version` uses the shared lookup in `rdt/version.py`. Update only
`rdt/__init__.py` when releasing; setuptools reads that version for metadata.

### Smart Mapping in Script Mode
When running `rdt add <admin-tool> --yes`, smart mapping auto-links to the **first** candidate found — no user prompt. This is by design but can produce unexpected links if multiple candidates exist.

### `--hardcore` Mode
Generates random 24-char passwords via `secrets.choice()` for env vars whose names contain `PASSWORD`, `SECRET`, `PASS`, `KEY`, or `TOKEN`. Non-hardcore mode uses placeholder defaults (e.g., `POSTGRES_PASSWORD=postgres`).

### MCP Server
The `rdt-mcp` entry point exposes 7 tools: `rdt_init`, `rdt_add`, `rdt_remove`, `rdt_list`, `rdt_doctor`, `rdt_check`, `rdt_up`. It has its own `_resolve_file()` that mirrors the CLI's compose file resolution but handles `project_dir` as a separate parameter.

## Testing

- `tests/test_artifact_pipeline.py`: original artifact, scaffold, strategy, template, mapping, and YAML tests.
- `tests/test_add_transaction.py`: fault injection, byte/mode recovery, atomic replacement, and dangling symlinks.
- `tests/test_headless_answers.py`: UI import isolation and preparation/output compatibility.
- `tests/test_mcp_compose_execution.py`: captured process results, deadlines, cleanup, stdin isolation, and real stdio MCP tests with fake Docker.
- `tests/test_preview.py`: read-only preview, secret redaction, CLI behavior, and real MCP schemas/results.
- `tests/test_public_workflows.py` and `tests/test_version.py`: public workflow baselines and distribution/version lookup.
- Tests use temporary files and simulated external processes; no Docker daemon is required.
- Run `python -m build`, then `python scripts/smoke_wheel.py dist/<wheel>.whl` for an isolated wheel installation check. This check needs dependency downloads.

## Project Mutation and MCP Behavior

- `init`, `add`, and `remove` support CLI `--dry-run` and MCP `dry_run=True`; previews never write project files or launch Docker and do not prompt.
- Preview env output shows key actions and credential placeholders, never env values. Known secrets are redacted from file diffs; arbitrary unknown user-authored secrets still need manual review before sharing.
- Add snapshots planned files before writing and performs best-effort rollback on handled errors. Incomplete recovery names paths; process crashes and concurrent writers remain outside the guarantee.
- MCP up/check capture child output, disconnect child stdin from the protocol, and use a positive `timeout_seconds` (default 120). Timeout cleanup does not undo container side effects.
- CLI foreground startup retains terminal streaming and has no MCP deadline.
