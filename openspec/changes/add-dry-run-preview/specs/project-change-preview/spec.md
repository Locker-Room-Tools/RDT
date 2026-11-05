## Purpose

Let users and MCP clients inspect planned project mutations, including companion configuration and cleanup, before deciding to execute the ordinary command.

## ADDED Requirements

### Requirement: Mutation commands support opt-in preview

CLI init/add/remove SHALL accept --dry-run, and corresponding MCP tools SHALL accept dry_run defaulting to false. Preview SHALL use noninteractive defaults and explicit options without prompting.

#### Scenario: Service addition is previewed
- **WHEN** a user runs rdt add postgres --dry-run
- **THEN** the command returns a preview using script-mode defaults without configuration prompts

#### Scenario: Existing caller does not request preview
- **WHEN** a CLI or MCP caller omits the preview option
- **THEN** the command retains its ordinary mutation behavior

### Requirement: Preview leaves project state unchanged

Preview SHALL NOT create, modify, or delete files or directories, write application configuration, or launch Docker.

#### Scenario: Preview targets a directory that does not exist
- **WHEN** a user previews initialization at a new target path
- **THEN** the preview describes the intended outputs without creating the target directory

#### Scenario: Removal includes cleanup
- **GIVEN** existing Compose, env files, and companion configuration
- **WHEN** removal is previewed with environment and artifact cleanup enabled
- **THEN** all existing file bytes and directory contents remain unchanged
- **AND** no external process is launched

### Requirement: Preview describes all selected changes

Preview SHALL report create/update/delete/skip actions for Compose, env keys, companion files, and scaffolds affected by the requested operation, with text diffs for changed Compose/config files and structured MCP output.

#### Scenario: Proxy addition requires a companion config
- **WHEN** a proxy addition is previewed
- **THEN** the preview includes the Compose change, companion config content diff, and required directory actions

#### Scenario: Cleanup options are absent
- **WHEN** removal is previewed without cleanup options
- **THEN** unrelated env variables and companion files are not listed for deletion

### Requirement: Preview applies ordinary validation

Preview SHALL apply the same input validation, overwrite policies, path resolution, and dependency warnings as ordinary execution and SHALL report invalid plans as failures.

#### Scenario: Initialization conflicts with an existing file
- **WHEN** initialization is previewed for an existing Compose file without force
- **THEN** the operation reports the same conflict as ordinary initialization and changes nothing

#### Scenario: Required render input is invalid
- **WHEN** an addition cannot render its required companion configuration
- **THEN** preview returns an error instead of a successful incomplete plan

### Requirement: Preview protects known credential values

Preview SHALL show env key actions without env values, replace known credential values in displayed diffs with redaction markers, and use stable placeholders for newly generated credentials.

#### Scenario: Hardcore credentials would be generated
- **WHEN** a service addition is previewed in hardcore mode
- **THEN** the preview contains credential placeholders rather than generated passwords
- **AND** existing env values are not returned

#### Scenario: A known credential appears in a config
- **GIVEN** a rendered config or existing Compose field contains a credential known to RDT
- **WHEN** its diff is displayed or returned through MCP
- **THEN** the credential value is redacted

### Requirement: Preview and execution agree for unchanged inputs

For unchanged project state and options, ordinary execution SHALL make the paths, actions, and nonsecret content changes described by preview. Execution SHALL recompute from current state rather than applying a saved preview.

#### Scenario: User executes after reviewing a preview
- **WHEN** the same command runs without dry-run against unchanged inputs
- **THEN** its resulting nonsecret changes match the preview
- **AND** real generated credentials replace preview placeholders where required
