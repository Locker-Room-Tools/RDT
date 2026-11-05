## Purpose

Give users and packaging tools one consistent distribution identity while retaining the established Python import and command names.

## ADDED Requirements

### Requirement: New distributions use the documented name

Newly built RDT distributions SHALL identify themselves as rdt-rambo and installation documentation SHALL use that name.

#### Scenario: Wheel metadata is inspected
- **WHEN** a maintainer builds an RDT wheel
- **THEN** its distribution metadata name is rdt-rambo
- **AND** documented installation commands use rdt-rambo

### Requirement: Public entry points remain available

Installing the wheel SHALL provide the rdt import and rdt command; installing with the mcp extra SHALL also provide a working rdt-mcp command with its dependencies.

#### Scenario: Installation outside the checkout
- **WHEN** the wheel with its mcp extra is installed into a clean environment outside the repository
- **THEN** importing rdt and running rdt --help succeed
- **AND** rdt-mcp completes an MCP initialization and preset-list request
- **AND** packaged locales and rendering templates are available

### Requirement: Legacy installation migration is documented

The project SHALL document replacement of locker-room-tolls-rdt installations without encouraging both distribution names to coexist.

#### Scenario: User has the legacy distribution
- **WHEN** the user follows the migration documentation
- **THEN** it explains removal of the legacy distribution and installation of rdt-rambo
- **AND** states that imports and command names remain unchanged
