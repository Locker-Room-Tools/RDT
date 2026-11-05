# Proposal

## Why

Docker Compose launched through MCP inherits the server's stdout, which is also the stdio protocol channel. Missing executables and unbounded execution can also prevent callers from receiving actionable results.

## What Changes

- Capture Docker output for MCP calls and return it as structured tool data.
- Bound MCP Compose execution with a configurable positive timeout, defaulting to 120 seconds.
- Normalize missing-executable, timeout, and nonzero-exit outcomes.
- Preserve normal CLI foreground streaming and never automatically retry a start operation.

## Capabilities

### New Capabilities

- `mcp-compose-execution`: Protocol-safe, bounded Compose execution with structured diagnostics.

### Modified Capabilities

None. OpenSpec has no existing capability specifications.

## Impact

Touches `rdt/core.py`, `rdt/mcp_server.py`, command result types, MCP documentation, and subprocess tests. The MCP up result gains status and output fields while retaining command and returncode when available. CLI behavior remains compatible. No Docker daemon is required for regression tests.
