# Design

## Context

The repository uses pytest and one large test module. It has no CI or declared test extra. Python support starts at 3.10; 3.14 is the current locally exercised runtime.

## Goals / Non-Goals

Goals: verify supported public workflows automatically and catch packaging-only failures.

Non-goals: pursuing a numerical coverage target, requiring a Docker daemon, introducing a new test framework, and publishing releases.

## Decisions

- Keep pytest and add focused modules for core, CLI, MCP, and packaging. Do not reorganize the existing suite solely for appearance. Test resulting files and returned behavior rather than mirroring private implementation.
- Add a development extra containing pytest and build, with MCP test dependencies installed through the existing mcp extra. CI installs editable source for source tests; package smoke verification uses an isolated wheel installation.
- Cover init/add/remove success and failure, compose path resolution, check/up subprocess outcomes, doctor result propagation, env preservation and orphan cleanup, and CLI exit codes. Mock subprocess and network-facing infrastructure; use temporary directories for filesystem effects.
- Run source tests on Ubuntu for Python 3.10 and 3.14 on pull_request and pushes to main. Give the workflow read-only contents permissions and no release credentials.
- Build sdist and wheel in a packaging job. Install the wheel with its MCP extra into a fresh environment away from the checkout, clear PYTHONPATH, and check entry points, package data, rendering, and a real MCP handshake/list request. Reuse the packaging change's smoke command when available; avoid hard-coding the legacy distribution identity here.
- New behavior regressions stay in their owning changes: rollback fault injection, MCP timeout/transport, identity migration, import isolation, and dry-run. CI runs whichever tests exist on the branch.

## Risks / Trade-offs

- Mock-only tests cannot prove real Docker compatibility → keep the limitation explicit and leave optional Docker integration outside the required pipeline.
- Editable source can mask missing wheel data → use a separate environment and working directory for package verification.
- More tests can become brittle → assert public outcomes and use fake executables only where process transport behavior matters.

## Migration Plan

Declare tools and add baseline tests, run the suite locally, add the CI matrix and package job, and document exact commands. Repository checks may later be made branch-protection requirements by maintainers; changing hosted protection settings is outside this change.
