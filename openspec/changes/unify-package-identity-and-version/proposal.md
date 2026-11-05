# Proposal

## Why

Installation documentation names rdt-rambo, build metadata names locker-room-tolls-rdt, and the CLI only looks up the latter. Duplicated version literals also make releases inconsistent.

## What Changes

- **BREAKING**: Align newly built distribution metadata with the documented PyPI name `rdt-rambo`; document migration from the legacy distribution name.
- Retain the `rdt` import and `rdt`/`rdt-mcp` commands.
- Define the release version once and reuse it for package metadata and runtime reporting.
- Keep version lookup compatible with legacy installed metadata and source checkouts.
- Verify built-wheel installation away from the repository.

## Capabilities

### New Capabilities

- `package-identity`: Consistent installation identity and supported entry points.
- `package-version`: Reliable version reporting from installed packages and source.

### Modified Capabilities

None. OpenSpec has no existing capability specifications.

## Impact

Touches pyproject.toml, runtime version handling, README/CONTRIBUTING, packaging checks, and outdated package guidance in AGENTS.md. Publishing to PyPI is outside this change; package ownership and release credentials must be verified before a later publish. Coordinate wheel smoke checks with add-workflow-tests-and-ci.
