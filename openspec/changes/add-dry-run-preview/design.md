# Design

## Context

Artifacts and scaffolds already expose plans, but Compose/env writing and removal cleanup do not share a complete project plan. CLI and MCP both call the core. See proposal.md for motivation.

## Goals / Non-Goals

Goals: a shared preview of init/add/remove with the same validation and target selection as ordinary execution.

Non-goals: previewing compose up, saved executable plans, applying stale previews, and guaranteeing detection of arbitrary user-authored secrets unknown to RDT.

## Decisions

- Introduce a small project-operation plan containing ordered file/directory actions, warnings, and display data. Reuse existing artifact/scaffold plans and ordinary command preparation; avoid a parallel implementation of generation rules.
- CLI --dry-run and MCP dry_run are opt-in and default false. Init respects force, add respects overwrite policy and smart mapping, and remove respects clean_env/clean_artifacts. Preview rejects the same invalid inputs and conflicts as apply.
- Preview resolves paths and reads existing files, renders candidates in memory, and never creates target directories, temporary files, snapshots, locks, or configuration files. It never launches Docker or prompts for service configuration; interactive CLI dry-run uses the same defaults/options as script mode.
- Return a structured MCP plan with operation, project root, ordered actions, warnings, and valid/error status. CLI renders paths, action labels, unified text diffs for Compose/configs, and env-key actions. Directories have action summaries, not file diffs.
- Never include env values in preview output. Redact known existing credential values and credential-bearing fields in displayed Compose/config diffs. Represent newly generated credentials with stable placeholders; use the same secret classification as ordinary credential generation. The display representation is separate from apply content.
- An ordinary execution recomputes its plan from current state and generates real random credentials. Preview equivalence means identical paths, actions, and nonsecret changes for unchanged input/state; credential placeholders are not promised as literal future values.
- Implement after transactional add and headless preparation when possible. Keep this change's capability separate: it owns preview behavior, not transaction guarantees or package/CI work.

## Risks / Trade-offs

- Existing helpers can create directories implicitly → enforce a read-only filesystem test harness across all preview paths.
- Rendering can expose secrets beyond env files → test explicit credentials and known values in config/Compose diffs; document limits for arbitrary unknown user-authored secrets.
- Inputs can change after preview → recompute on execution and document that preview is not a reservation.

## Migration Plan

Extract shared planning, add core preview results, expose CLI/MCP flags, add both locale keys for new UI text, and document examples. Existing calls keep mutating by default. No persisted state migration or new dependency is needed.
