# Tasks

## 1. Reproducible local checks

- [ ] 1.1 Declare a development extra for pytest/build and document installation with the MCP extra; verify setup and pytest collection in a clean virtual environment.
- [ ] 1.2 Add focused core lifecycle/env tests with strict infrastructure mocks; verify generated state, unrelated-content preservation, path resolution, and domain failures without Docker.
- [ ] 1.3 Add CLI exit-code and MCP request/result baseline tests; verify invalid service inputs, diagnostic propagation, and preset listing in isolated temporary projects.

## 2. Automated source verification

- [ ] 2.1 Add a read-only pull-request/main workflow for Python 3.10 and 3.14; verify both matrix entries install declared tools and run pytest without Docker or credentials.
- [ ] 2.2 Document matrix versions and local equivalents in CONTRIBUTING.md; verify every documented command matches the workflow invocation.

## 3. Distribution verification

- [ ] 3.1 Add or reuse the isolated wheel smoke command from unify-package-identity-and-version; verify it clears source-path leakage and exercises entry points, locales, templates, and MCP initialization/list.
- [ ] 3.2 Add a CI job building sdist/wheel and invoking the smoke command; verify a deliberately omitted template makes the check fail in a disposable build and no publishing step exists.
- [ ] 3.3 Run the complete source suite and packaging checks locally; verify the new workflow reports failures instead of allowing them to continue silently.
