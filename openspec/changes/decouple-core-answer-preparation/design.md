# Design

## Context

Core imports build_script_answers from wizard.py; the wizard imports questionary and Rich and creates a Console at import time. Existing strategies consume flexible answer mappings. See proposal.md for motivation.

## Goals / Non-Goals

Goals: isolate interactive concerns and make shared answer construction explicit without changing generated projects.

Non-goals: new architecture layers, replacing every answer dictionary, changing default credentials/smart mapping, and separating installation extras.

## Decisions

- Extract preparation into rdt/answers.py with dependencies limited to non-UI modules. Core and wizard both depend on that module. Audit other transitive core imports and defer or remove presentation imports where necessary. Do not merely move the UI import to a different shared file.
- Define a TypedDict-based contract for common prepared fields and annotate preparation signatures. Keep feature-specific extension keys supported and retain adapters where strategies expect mappings. A universal rigid dataclass would make preset-specific fields expensive to evolve.
- Preserve existing precedence: preset defaults, explicit supported options, smart mapping behavior, and final set_vars overrides according to the current implementation. Characterize behavior before moving it; do not normalize values differently in this refactor.
- Use subprocess import-isolation tests that reject imports of typer, questionary, and rich. Exercise core preset listing and noninteractive add as well as importing the MCP server, so lazy UI dependencies are detected during actual operations.
- Keep a lightweight compatibility re-export for build_script_answers in wizard.py if existing callers use it, with core importing only the new shared module.

## Risks / Trade-offs

- Strategy-specific keys can escape the common type contract → retain an explicit extension mapping and add typed fields incrementally.
- Moving helpers can change initialization order or defaults → compare resulting Compose, env keys, scaffolds, and artifact contents for representative presets.
- Import tests can accidentally use already-loaded modules → run them in a fresh subprocess with UI import blockers installed first.

## Migration Plan

Add characterization tests, extract and type preparation, switch callers, verify import isolation, and update architecture docs. Preserve current public CLI/MCP inputs and outputs; no user project migration is required.
