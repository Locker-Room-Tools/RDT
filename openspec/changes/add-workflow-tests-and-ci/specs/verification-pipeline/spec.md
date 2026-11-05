## Purpose

Provide repeatable automated evidence that public RDT workflows work on supported Python versions and that built packages can run independently of the source checkout.

## ADDED Requirements

### Requirement: Contributor verification is reproducible

The repository SHALL declare its test/build dependencies and document commands that install them and run the same required checks as CI.

#### Scenario: Fresh contributor environment
- **WHEN** a contributor follows the documented setup in a clean supported Python environment
- **THEN** pytest and distribution builds run without undeclared development packages

### Requirement: Public workflows have deterministic regression coverage

Required tests SHALL cover public core, CLI, and MCP success and failure outcomes using temporary files and simulated external processes, without a Docker daemon or live service dependency.

#### Scenario: Source suite runs without Docker
- **WHEN** the required suite runs on a machine without Docker installed
- **THEN** core file workflows, CLI errors, and MCP responses are verified without starting real containers

#### Scenario: Generated project lifecycle
- **WHEN** tests initialize a project, add a service, and remove it with optional cleanup
- **THEN** they assert resulting Compose/environment/configuration state and preservation of unrelated content

### Requirement: CI verifies supported Python boundaries

Pull requests and pushes to main SHALL run the required source suite on Python 3.10 and 3.14 and fail the workflow if either suite fails.

#### Scenario: Regression on one supported interpreter
- **WHEN** the suite fails on one matrix interpreter
- **THEN** the corresponding required verification job fails
- **AND** the failure is not hidden by success on the other interpreter

### Requirement: Built artifacts are exercised independently

CI SHALL build an sdist and wheel and verify wheel entry points, package data, rendering, and MCP initialization/list in a clean environment outside the source checkout.

#### Scenario: A required template is missing from the wheel
- **WHEN** source tests pass but a rendered preset needs a template absent from the wheel
- **THEN** the packaging smoke job fails

#### Scenario: Wheel is valid
- **WHEN** the wheel and its MCP extra are installed into the smoke environment
- **THEN** CLI help/version, locale access, template rendering, and MCP initialization/list succeed

### Requirement: Verification does not publish artifacts

The required CI workflow SHALL use read-only repository permissions and SHALL NOT upload distributions to a package registry.

#### Scenario: Pull-request verification
- **WHEN** CI verifies a pull request
- **THEN** it needs no publishing credentials and performs no registry upload
