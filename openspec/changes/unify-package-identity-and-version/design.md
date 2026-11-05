# Design

## Context

The documented public installation name is rdt-rambo. Editable local metadata currently uses locker-room-tolls-rdt, while CLI and __init__ carry separate version handling. See proposal.md for motivation.

## Goals / Non-Goals

Goals: make fresh installations internally consistent and retain runtime compatibility with legacy metadata.

Non-goals: publishing a release, renaming Python imports or commands, and uninstalling packages on the user's machine.

## Decisions

- Make rdt-rambo the canonical distribution name because it is already the documented public identity. Renaming documentation to the legacy typo would preserve an accidental identity. Document explicit uninstall/reinstall instructions so two distributions do not compete for the same console scripts.
- Keep a literal version in the lightweight rdt package version attribute and configure setuptools dynamic version metadata from it. Build isolation must not import CLI, MCP, or optional dependencies. Remove the independent pyproject version literal.
- Resolve runtime version through canonical installed metadata, then legacy metadata, then the source version attribute. Catch only missing-distribution metadata for fallback; preserve unrelated failures. Put lookup in one UI-independent helper.
- Build wheels and install them into a disposable environment outside the checkout, with PYTHONPATH cleared. Check metadata, command entry points, locales, and templates. No PyPI upload is part of validation.

## Risks / Trade-offs

- Old and new distributions installed together share files → document migration and test each installation identity separately.
- Canonical PyPI access is not proven by local builds → verify ownership before any future publishing workflow is enabled.
- Dynamic version discovery can accidentally import runtime dependencies → verify isolated builds and keep the version attribute lightweight.

## Migration Plan

Update metadata and lookup, document legacy installation replacement, build/install a wheel in isolation, and verify source fallback with metadata unavailable. A later release can publish only after ownership checks; this change performs no global installation.
