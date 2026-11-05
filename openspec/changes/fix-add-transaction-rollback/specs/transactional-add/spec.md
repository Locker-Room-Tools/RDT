## Purpose

Keep generated project files consistent when adding a service fails, and tell users when automatic recovery cannot fully restore their project.

## ADDED Requirements

### Requirement: Failed additions restore existing files

A failed service addition SHALL restore the original bytes and permission modes of every pre-existing file it changed, when the filesystem permits recovery.

#### Scenario: Environment write fails after Compose changes
- **GIVEN** a project with existing Compose and environment files
- **WHEN** adding a service fails while writing an environment file
- **THEN** Compose and all previously changed environment files match their original bytes and modes
- **AND** the addition reports failure

#### Scenario: Later artifact fails after an overwrite
- **GIVEN** an artifact selected for overwrite already contains user configuration
- **WHEN** a later artifact fails during the same addition
- **THEN** the overwritten artifact is restored to its original bytes and mode

### Requirement: Failed additions remove their new outputs

A failed addition SHALL remove new files it attempted to create and its newly created empty directories while preserving pre-existing and nonempty directories.

#### Scenario: First environment write fails in a new project
- **WHEN** an addition creates Compose and then fails writing its first environment file
- **THEN** no Compose or partial environment file created by that addition remains

#### Scenario: Recovery encounters a nonempty directory
- **GIVEN** a directory created by the addition contains a file outside its tracked outputs
- **WHEN** the addition fails and recovery runs
- **THEN** that directory and the untracked file are preserved

### Requirement: Incomplete recovery is explicit

Failed additions SHALL report the initiating error and all failed recovery paths without exposing file contents or claiming full recovery when any recovery step failed.

#### Scenario: One restoration fails
- **WHEN** a write fails and recovery cannot restore one of several changed files
- **THEN** recovery still attempts the remaining files
- **AND** the returned error identifies the original failure and the unrecovered path
- **AND** no generated credentials appear in the error
