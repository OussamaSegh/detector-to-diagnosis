# 0013. The status object is part of the versioned control API

Date: 2026-10-25
Status: Accepted

## Context

ADR 0003 says that new fields are added to the control protocol only in minor versions, so that
a client can tell from `"api"` what a server offers. The rule was applied to commands and their
parameters, but not to the object that `status` returns: from Chapter 9 to Chapter 15 it gained
`detector_counters` (Chapter 9), `sorter` (Chapter 10), `sink_counters` (Chapter 12) and
`integrity` (Chapter 15), while every response still said `"api": "1.0"`. Nothing
broke, because clients ignore fields they do not know, but a client cannot tell whether a
missing `integrity` means an old server or a status it should not trust. Chapter 16's change
control found the gap (problem report MDQ-PR-012). The integrity verdict is a risk control
(RC-01), so its presence must be something a client can rely on.

## Options

1. **Version the status object with the API.** Version 1.1 names the top-level fields of the
   status that it guarantees; a new field means a new minor version. A test compares the fields
   of a real status with the list for the current version, so a field cannot be added silently.
2. **Give the status its own schema version.** A `status_version` field, independent of the
   API. More precise, but a second version number that clients must check, for an object that
   only this API returns.
3. **Declare the status free-form diagnostic data.** No versioning; clients that need a field
   check for it. Simple, but a risk control would then rest on a field that no contract
   promises.

## Decision

Option 1. The API becomes version 1.1, whose status has exactly the top-level fields listed in
`control_protocol.hpp` (`status_fields`); each is marked as always present or as present while
its part exists (a detector, a sink, a run). The test
`ControlProtocol.StatusFieldsMatchTheApiVersion` reads the status before, during and after an
acquisition, and fails if a status has a field that the list does not name, lacks a field marked
as always present, or if a listed field never appears. Version 1.0 clients keep working: the
major version is unchanged. Requirement SRS-CTL-033; change request CR-0003.

## Consequences

### Positive

- Adding a status field is a change request that bumps the minor version and the list, and the
  test makes forgetting either impossible.
- A client that relies on the integrity verdict, a risk control, checks for `"api"` 1.1 or
  later and can tell an old server from an incomplete status.

### Negative

- Fields inside the top-level objects (a new detector counter) are not versioned; counters are
  named by the port that reports them and are documented with the port, so a client must still
  treat an unknown counter as information and a missing one as unknown.
- The list duplicates what `status_locked()` builds: two places to change for one field, held
  together only by the test.
