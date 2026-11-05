# Proposal

## Why

The passing test suite concentrates on artifacts and strategies while public core workflows, CLI error paths, MCP transport, and built-package installation receive limited coverage. There is no committed CI workflow to run these checks consistently.

## What Changes

- Add deterministic workflow tests for core operations, CLI behavior, and MCP request/response handling.
- Run pytest on Python 3.10 and 3.14 in pull-request and main-branch CI.
- Build distribution artifacts and smoke-test the wheel outside the checkout.
- Declare development test/build dependencies and document reproducible local commands.

## Capabilities

### New Capabilities

- `verification-pipeline`: Repeatable automated verification of public workflows and distributable artifacts.

### Modified Capabilities

None. OpenSpec has no existing capability specifications.

## Impact

Adds focused test modules, a CI workflow, development dependencies, and contributor documentation. Infrastructure is mocked and files live in temporary directories. This change does not publish packages or require Docker. Each other change owns tests for its new behavior; this change supplies baseline coverage and automation.
