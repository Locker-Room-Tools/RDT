# Proposal

## Why

Adding a service can fail while writing environment files after Compose has already changed. Current recovery also cannot restore overwritten artifacts and silently ignores recovery failures.

## What Changes

- Treat all files and scaffolds modified by one add operation as a single recoverable operation.
- Restore existing files and remove newly created files when any write fails.
- Preserve the original failure and report any paths that could not be recovered.
- Cover early write failures and overwritten artifact recovery with regression tests.

## Capabilities

### New Capabilities

- `transactional-add`: Consistent project files after a failed service addition, with explicit recovery diagnostics.

### Modified Capabilities

None. OpenSpec has no existing capability specifications.

## Impact

Changes `rdt/core.py`, artifact and scaffold application, and file-writing helpers as needed. CLI and MCP share the corrected behavior. Scope is service addition; transactional init/remove and crash recovery are separate work. No new runtime dependency is required.
