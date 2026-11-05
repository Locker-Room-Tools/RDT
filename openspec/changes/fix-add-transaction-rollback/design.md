# Design

## Context

The shared add path snapshots Compose and env files but writes them before its recovery branches. Artifact recovery only deletes successful creations. See proposal.md for motivation.

## Goals / Non-Goals

Goals: recover from handled write/render/scaffold failures across the entire add operation and explain incomplete recovery.

Non-goals: filesystem-wide ACID transactions, process-crash recovery, concurrent writer coordination, and transactional init/remove.

## Decisions

- Prepare and validate all planned writes before mutation. Journal each target before its first write, including existence, original bytes, and permission mode. A journal entry must exist even if a write fails halfway through. Merely extending the current successful-result list would miss partial writes.
- Put the complete mutation phase inside one exception boundary. Restore journaled files and remove newly created files in reverse order; remove only directories created by this operation and still empty. Attempt remaining recovery steps even after one fails.
- Use sibling temporary files and replacement for individual file writes where feasible, preserving existing permission modes. This limits truncation but does not replace cross-file recovery.
- Raise a domain error containing the initiating failure and recovery failures with affected paths. Successful recovery may report that changes were restored; incomplete recovery must never claim full restoration. Avoid logging file contents or credentials.
- Retain overwrite policies and compose-path resolution. Coordinate any reusable planning interface with add-dry-run-preview without requiring that change first.

## Risks / Trade-offs

- Recovery can also fail because of permissions or disk errors → best-effort recovery with actionable path diagnostics.
- In-memory snapshots consume space → scope snapshots to planned files; retain the current small-project usage model.
- Another process can modify a target during the operation → concurrent writers remain outside the guarantee and must be documented.

## Migration Plan

Add fault-injection regressions, implement journaling and recovery, then exercise the CLI and MCP add paths. Existing successful output remains compatible; errors become domain errors with recovery details. No persisted project migration is needed.
