# Tasks

## 1. Canonical identity

- [x] 1.1 Set the canonical distribution name to rdt-rambo while retaining entry points; build a wheel and verify its Name metadata and script declarations.
- [x] 1.2 Update installation/release guidance and AGENTS.md with legacy migration instructions; verify examples consistently use the canonical name and retain old metadata only for compatibility explanations.

## 2. Version reporting

- [x] 2.1 Configure build metadata from one lightweight version attribute and introduce shared runtime lookup; verify canonical, legacy, dual-metadata precedence, and source-only cases through targeted tests.
- [x] 2.2 Update CLI version reporting and release instructions; verify rdt --version matches built-wheel metadata and a version bump requires one source edit.

## 3. Isolated packaging verification

- [x] 3.1 Add a reusable wheel smoke check that installs outside the checkout with PYTHONPATH cleared; verify CLI help/version, locale access, template rendering, and MCP initialization/list with the mcp extra.
- [x] 3.2 Run isolated build and smoke checks plus pytest; record that no global package migration or PyPI upload is performed and share the check command with the CI change.
