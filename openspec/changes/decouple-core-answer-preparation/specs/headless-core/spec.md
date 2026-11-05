## Purpose

Let programmatic clients use RDT without initializing interactive presentation libraries while keeping parameter preparation consistent across CLI and MCP.

## ADDED Requirements

### Requirement: Programmatic operations do not require UI imports

Importing the shared core or MCP server and performing noninteractive preset listing and service addition SHALL NOT import Typer, questionary, or Rich or initialize a terminal UI.

#### Scenario: UI libraries are unavailable to the importer
- **GIVEN** a fresh Python process rejects imports of Typer, questionary, and Rich
- **WHEN** it imports the core and MCP server, lists presets, and adds a service noninteractively
- **THEN** the operations succeed without a prompt or terminal UI initialization

### Requirement: Shared inputs preserve generated behavior

Equivalent prepared inputs SHALL produce the same Compose service, environment keys, scaffolds, and artifact contents regardless of whether they originate from the CLI or MCP.

#### Scenario: Equivalent explicit service settings
- **WHEN** CLI and MCP add the same preset with equivalent explicit options to separate empty projects
- **THEN** their generated project content is equivalent apart from intentionally random credentials and project-root-dependent paths

### Requirement: Preparation preserves defaults and override precedence

Shared preparation SHALL preserve existing preset defaults, first-candidate script smart mapping, and supported explicit and set_vars override behavior.

#### Scenario: Script smart mapping has multiple candidates
- **GIVEN** several compatible parent services in the existing candidate order
- **WHEN** a noninteractive add does not specify a parent
- **THEN** it selects the same first candidate as before the refactor

#### Scenario: User overrides a prepared field
- **WHEN** a caller supplies a supported explicit option and a final set_vars override for that field
- **THEN** the final generated value follows the established set_vars precedence

### Requirement: Interactive use remains available

The CLI wizard SHALL continue to offer interactive prompts while sharing noninteractive preparation behavior with other clients.

#### Scenario: User adds a service interactively
- **WHEN** the user completes the wizard
- **THEN** the service is generated using the selected answers and existing prompt defaults
