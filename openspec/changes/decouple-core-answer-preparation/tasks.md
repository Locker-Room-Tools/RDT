# Tasks

## 1. Characterize preparation

- [ ] 1.1 Add behavior tests for defaults, smart-mapping candidate order, explicit options, and set_vars precedence; verify representative database, proxy, and admin-tool outputs before refactoring.

## 2. Extract the shared boundary

- [ ] 2.1 Move script preparation into a UI-independent module and add focused typed contracts/adapters; verify characterization tests preserve feature-specific extension fields and output.
- [ ] 2.2 Update core and wizard imports and audit transitive dependencies; verify a fresh subprocess blocking Typer/questionary/Rich can import core/MCP, list presets, and add a service.
- [ ] 2.3 Update architecture guidance and module documentation; verify it describes the actual import direction and retains interactive wizard usage.

## 3. Client compatibility

- [ ] 3.1 Add paired CLI/MCP generation checks and a mocked interactive wizard smoke test; verify equivalent options produce equivalent content without changing established prompts.
- [ ] 3.2 Run the full pytest suite and the import-isolation subprocess checks; verify no new runtime dependency or public command rename is introduced.
