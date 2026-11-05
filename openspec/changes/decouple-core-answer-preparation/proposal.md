# Proposal

## Why

The shared core imports script-answer preparation from the interactive wizard, loading questionary and Rich transitively. Loose answer dictionaries also make it easy for CLI and MCP parameter handling to drift.

## What Changes

- Extract script-answer preparation into a UI-independent shared module.
- Remove eager UI dependencies from the core/MCP import path.
- Introduce a focused typed answer contract at the preparation boundary while retaining compatible adapters for existing dictionaries.
- Preserve default values, smart mapping, overrides, and generated output across entry points.

## Capabilities

### New Capabilities

- `headless-core`: UI-independent programmatic access with consistent parameter preparation across clients.

### Modified Capabilities

None. OpenSpec has no existing capability specifications.

## Impact

Touches core, wizard, shared answer preparation, strategy input annotations/adapters where needed, and developer architecture documentation. CLI packages remain installed as today; changing packaging extras is outside scope. This is an internal refactor with a new explicit import-isolation contract, not a redesign of all strategies.
