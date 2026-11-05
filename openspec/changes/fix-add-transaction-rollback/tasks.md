# Tasks

## 1. Recover the complete write phase

- [x] 1.1 Add fault-injection regressions for new and existing projects failing at Compose, env, and env-example writes; verify they expose current partial-state failures.
- [x] 1.2 Journal targets before mutation and wrap all add writes in recovery; verify the fault-injection tests restore original bytes and modes or remove new partial files.
- [x] 1.3 Recover overwritten artifacts and operation-owned empty scaffolds; verify a later artifact failure restores user configuration and preserves untracked files.

## 2. Report recovery outcomes

- [x] 2.1 Preserve the initiating exception and collect recovery failures as domain diagnostics; verify one failed restoration does not prevent remaining recovery steps or leak credentials.
- [x] 2.2 Document recovery guarantees and limits in English and Russian scripting guides; add both locale keys for any new translated messages and verify key parity.

## 3. Integration

- [x] 3.1 Verify CLI and MCP additions surface complete and incomplete recovery outcomes using temporary projects and mocked filesystem failures; run the full pytest suite without Docker.
