# Proposal

## Why

Users cannot inspect the combined Compose, environment, scaffold, and companion-file effects of an operation before it writes to disk. Artifact planning already provides part of the foundation for a shared preview.

## What Changes

- Add --dry-run to CLI init/add/remove and dry_run to corresponding MCP tools.
- Produce a shared plan describing create/update/delete/skip actions, text diffs, and env-key changes.
- Validate and render without writing project files or running Docker.
- Redact known secrets and use placeholders for credentials that would be generated.
- Keep ordinary mutation commands as the way to apply changes; no saved-plan execution is introduced.

## Capabilities

### New Capabilities

- `project-change-preview`: Side-effect-free, secret-aware previews of project mutations for CLI and MCP clients.

### Modified Capabilities

None. OpenSpec has no existing capability specifications.

## Impact

Touches core planning, artifact/scaffold planners, env planning, CLI/MCP parameters, result types, localization, and usage guides. Reuse the transaction change's file-operation boundary where present. Prefer implementation after fix-add-transaction-rollback and decouple-core-answer-preparation so preview and apply share preparation without duplicating it.
