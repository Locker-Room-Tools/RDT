## Purpose

Report the correct RDT version consistently for canonical installations, legacy distributions, and development source checkouts.

## ADDED Requirements

### Requirement: Release version has one authoritative value

Build metadata and runtime version reporting SHALL derive their release version from one authoritative source value.

#### Scenario: Release version changes
- **WHEN** the authoritative release version is updated and a wheel is built
- **THEN** wheel metadata, rdt.__version__, and rdt --version report that release version
- **AND** no second release-version literal requires editing

### Requirement: Version reporting handles supported installation modes

Version reporting SHALL prefer rdt-rambo metadata, fall back to locker-room-tolls-rdt metadata when canonical metadata is absent, and use the source version when neither distribution is installed.

#### Scenario: Canonical installation
- **WHEN** only rdt-rambo metadata is available
- **THEN** rdt --version reports its version without an exception

#### Scenario: Legacy installation
- **WHEN** only locker-room-tolls-rdt metadata is available
- **THEN** rdt --version reports its version without an exception

#### Scenario: Source checkout without distribution metadata
- **WHEN** neither supported distribution has installed metadata
- **THEN** rdt --version reports the source version without a missing-package traceback
