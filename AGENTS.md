# AGENTS.md — RDT (Rambo Docker Tools)

## Commands

```bash
# Install for development (editable, from repo root)
pip install -e ".[mcp]"

# Run all tests (pytest auto-discovers tests/)
pytest

# Run a single test
pytest tests/test_artifact_pipeline.py::test_nginx_proxy_created

# Run with verbose output
pytest -v

# Build for PyPI
python -m build
```

**No linter, formatter, typechecker, or pre-commit config exists.** There is no Makefile, tox, nox, ruff config, mypy config, or CI workflows. Only `pytest` is used.

## Package Name Confusion (Critical)

| Purpose | Name |
|---|---|
| PyPI package (`pip install ...`) | `rdt-rambo` |
| `pyproject.toml` name (pip registration) | `locker-room-tolls-rdt` |
| Python import | `rdt` |
| CLI command | `rdt` |
| MCP server command | `rdt-mcp` |
| `importlib.metadata.version(...)` argument | `"locker-room-tolls-rdt"` |

**After `pip install -e .` from source**, the version lookup `version("locker-room-tolls-rdt")` works. After `pip install rdt-rambo` from PyPI it may fail (distribution metadata uses `Name: rdt-rambo`). If you need version at runtime, catch both or fall back to `rdt.__version__`.

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
| `wizard.py` | Interactive questionary prompts, smart mapping, `build_script_answers()` |
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

### `--version` Uses `importlib.metadata`, Not `rdt.__version__`
`rdt --version` calls `version("locker-room-tolls-rdt")`. `rdt/__init__.py` has a separate `__version__ = "2.1.1"` that is never read. Bump both when releasing.

### Smart Mapping in Script Mode
When running `rdt add <admin-tool> --yes`, smart mapping auto-links to the **first** candidate found — no user prompt. This is by design but can produce unexpected links if multiple candidates exist.

### `--hardcore` Mode
Generates random 24-char passwords via `secrets.choice()` for env vars whose names contain `PASSWORD`, `SECRET`, `PASS`, `KEY`, or `TOKEN`. Non-hardcore mode uses placeholder defaults (e.g., `POSTGRES_PASSWORD=postgres`).

### MCP Server
The `rdt-mcp` entry point exposes 7 tools: `rdt_init`, `rdt_add`, `rdt_remove`, `rdt_list`, `rdt_doctor`, `rdt_check`, `rdt_up`. It has its own `_resolve_file()` that mirrors the CLI's compose file resolution but handles `project_dir` as a separate parameter.

## Testing

- **Single test file:** `tests/test_artifact_pipeline.py` (70+ tests, ~1800 lines)
- Tests use `tmp_path` fixture — **no Docker required**
- Coverage is sparse: artifact pipeline, rollback, YAML serialization, smart mapping, strategies, templates are tested. `core.init()`, `core.remove()`, `core.up()`, `core.check()`, `core.doctor()`, `wizard.py`, `env_manager.py`, `port_utils.py`, `mcp_server.py`, `i18n.py`, and `cli.py` have **little to no test coverage**.
- One CLI integration test uses `typer.testing.CliRunner`
