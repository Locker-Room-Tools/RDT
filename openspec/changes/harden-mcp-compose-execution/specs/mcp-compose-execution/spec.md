## Purpose

Allow MCP clients to execute Docker Compose commands without contaminating protocol transport or waiting indefinitely for command completion.

## ADDED Requirements

### Requirement: Child output does not contaminate transport

MCP Compose calls SHALL return child stdout and stderr within tool results and SHALL NOT emit child output as raw MCP transport data.

#### Scenario: Docker writes to both output streams
- **WHEN** a Compose command writes ordinary text to stdout and stderr
- **THEN** the MCP connection remains valid
- **AND** its tool result contains the captured output
- **AND** a subsequent preset-list call succeeds on the same connection

### Requirement: Execution failures have structured results

MCP Compose calls SHALL distinguish success, nonzero exit, missing executable, and timeout with stable status and error codes, retaining command and returncode where available.

#### Scenario: Command exits unsuccessfully
- **WHEN** Compose exits with a nonzero code
- **THEN** the result has status error, code command_failed, the actual returncode, and diagnostic output

#### Scenario: Docker cannot be launched
- **WHEN** the Docker executable is unavailable
- **THEN** the result has status error and code executable_not_found
- **AND** the MCP server remains usable

### Requirement: MCP execution has a configurable deadline

MCP Compose execution SHALL default to a 120-second timeout, accept a positive timeout override, and terminate and reap the launched command when its deadline expires.

#### Scenario: Command exceeds its deadline
- **WHEN** Compose exceeds the configured deadline
- **THEN** the tool returns status error and code timeout after command cleanup
- **AND** warns that the stack may already have changed
- **AND** does not retry or stop containers automatically

#### Scenario: Timeout is invalid
- **WHEN** a caller supplies a nonpositive timeout
- **THEN** the request is rejected before Docker starts

### Requirement: Diagnostics have a bounded response size

Each returned stdout and stderr field SHALL contain at most the final 64 KiB of that stream and indicate truncation when output was omitted.

#### Scenario: Docker produces excessive output
- **WHEN** command output exceeds the response limit
- **THEN** the tool returns bounded diagnostic tails and a truncation indicator

### Requirement: CLI foreground execution remains interactive

CLI foreground startup SHALL continue streaming command output and SHALL NOT inherit the MCP default execution timeout.

#### Scenario: User attaches through the CLI
- **WHEN** a user starts Compose in foreground mode through the CLI
- **THEN** output streams to the terminal until the command ends or the user interrupts it
