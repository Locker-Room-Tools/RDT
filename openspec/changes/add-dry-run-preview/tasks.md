# Tasks

## 1. Shared planning

- [x] 1.1 Extract common init/add/remove planning and reuse existing artifact/scaffold plans; verify action selection against ordinary execution for representative presets and cleanup modes.
- [x] 1.2 Add preview results and in-memory rendering with ordinary validation; verify errors, force/overwrite behavior, path resolution, and dependency warnings match mutation paths.
- [x] 1.3 Add filesystem/process guards for preview tests; verify existing and missing target directories remain unchanged and no Docker process or config write occurs.

## 2. Secret-aware presentation

- [x] 2.1 Generate ordered action summaries, text diffs, and env-key actions with credential redaction/placeholders; verify existing and newly generated credentials are absent from CLI/MCP output.
- [x] 2.2 Document preview limits and state-recomputation semantics in both scripting guides; verify examples distinguish placeholders from later generated values.

## 3. CLI and MCP

- [x] 3.1 Add noninteractive --dry-run to init/add/remove and dry_run to MCP counterparts with false defaults; verify CLI exit codes, MCP structured plans, and unchanged ordinary calls.
- [x] 3.2 Add preview UI messages to both locale files and document MCP examples; verify locale key parity and that preview help describes its scope.

## 4. Integration

- [x] 4.1 Compare preview and actual init/add/remove on paired temporary projects, normalizing only random credentials and roots; verify actions and nonsecret results agree.
- [x] 4.2 Run the full suite and OpenSpec validation; verify existing mutation behavior and transactional recovery remain intact.
