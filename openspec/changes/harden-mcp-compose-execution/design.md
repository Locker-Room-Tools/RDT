# Design

## Context

The MCP server uses stdio and shares core.up with the CLI. Core currently launches Docker with inherited output and no timeout. Compose validation already uses a separate execution path; audit that path for the same MCP guarantees.

## Goals / Non-Goals

Goals: keep stdout protocol-clean, bound MCP command duration, and return consistent execution diagnostics.

Non-goals: container lifecycle monitoring, automatically undoing a partially started stack, and changing CLI attach behavior.

## Decisions

- Add a small execution policy to the core subprocess boundary: capture output and an optional timeout. MCP selects capture plus a 120-second default; CLI retains inherited streams and foreground lifetime. Avoid redirecting global Python stdout, which does not reliably isolate child-process file descriptors.
- Expose a positive `timeout_seconds` option for MCP Compose execution. Reject invalid values before spawning. Check and up use bounded execution; static preset listing does not spawn Docker.
- Use argument lists, never shell command interpolation. Capture and decode stdout/stderr with replacement for invalid bytes and include bounded diagnostic tails (at most 64 KiB per stream) in tool results.
- Successful results contain status=ok, command, returncode=0, stdout, stderr. Failures contain status=error and a stable error code: command_failed, executable_not_found, or timeout. Preserve command and returncode where available; do not invent a returncode for a process that never started.
- On timeout terminate and reap the launched Docker process. Report that containers may already have changed; do not retry or run compose down. Use process-group cleanup if needed to avoid orphaned CLI descendants.
- Keep the existing requirement for explicit user intent before starting a stack in tool guidance.

## Risks / Trade-offs

- Captured output can be large → cap returned diagnostic tails; test bounded result sizes.
- Docker can partially start containers before timeout → return an explicit partial-effects warning.
- MCP callers may rely on old result fields → retain command/returncode when meaningful and document additive fields and normalized errors.

## Migration Plan

Introduce execution/result support, adapt MCP, document fields and timeouts, and run a real stdio handshake against a fake Docker executable. Existing configured MCP commands remain valid.
