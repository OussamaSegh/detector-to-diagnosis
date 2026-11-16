# CR-0030: Control API 3.0 and acquisition configuration schema 2.0

| Field | Value |
|---|---|
| Status | implemented |
| Requested | 2026-11-16, by the software lead |
| Source | improvement; roadmap 2.0.0, theme B (interface clean-up held for a major version) |
| Decision | approved, 2026-11-16, under the software lead's standing delegation of 2026-11-15 |
| Commits | 5543f5f (control API 3.0, configuration schema 2.0, the migration tool) and the commit that records this |

## Description

A review of every name of the control API (each field of `hello`, `status`, `diagnostics` and
the error replies, taken from a running server) and of the three configuration schemas
(acquisition 1.4, hardware 1.1, calibration table 1.0) found these inconsistencies. The change
fixes them in one breaking version, so that clients and files change once:

**Control API 3.0** (`api_version` "3.0"):

1. `status.hardware.describe` becomes `description`: every other field is a noun, and
   `detector` and `sink` hold descriptions under their own names.
2. `status.hardware.boards[].temperature` (the level: normal, warning, alarm) becomes
   `temperature_level`, beside `temperature_c`, so that a reader cannot take one for the other.
3. `status.sorter` becomes `sorter_counters`, like `detector_counters` and `sink_counters`.
4. Every request names the API it was written for (`"api": "3.0"`). A request without `api`,
   or with a major version other than 3, is refused with `unsupported_api` and a message that
   names the migration note. In 2.x a request without `api` was accepted: a 2.x client that
   omitted it would now read renamed fields without noticing.

**Acquisition configuration schema 2.0** (`schema_version` "2.0"):

5. `source.type` is required. In 1.x it defaulted to `synthetic`, so a file that forgot the
   source made the server invent data (hazard H-06; a product build refuses it since CR-0029).
6. `stop_after_s` moves into `source`: it applies only to the synthetic source.
7. `pipeline.coincidence_window_ps` becomes `sorter.window_ps`: the window is the sorter's, with
   its delay and energy window.
8. `output.max_file_mb` becomes `output.max_file_mib`: the sink multiplies by 2^20.
9. `rt_profile` becomes `rt_profile_file`, like `calibration.file` and the hardware
   description's `temperature_file`.
10. A file with `schema_version` 1.x is refused with a message that names the migration tool.

**The simulator's command line:** `minidaq_sim --centre` and the `centre_mm` of its source
description become `--center` and `center_mm` (the book's spelling everywhere else), and the
option `--max-file-mb` of `minidaq_sim` and of the benchmark `writer_throughput` becomes
`--max-file-mib`, like the configuration key of item 8.

**Unchanged after review:** the hardware description (1.1) and the calibration table (1.0),
whose names are consistent and carry their units; the list-mode format MDQ-L1 and the readout
formats, which are data formats with their own versions, not part of this change.

**Migration:** `tools/migrate_config.py` turns a 1.x acquisition configuration into 2.0
(including `source.type: synthetic` made explicit where 1.x defaulted to it), and
`docs/migration-2.0.md` lists every rename for clients of the API.

## Reason

Each of these names has made a reader stop or guess: a verb among nouns, a level that reads like
a temperature, a counter group without the suffix of the others, a unit that is not the one
used, a field that belongs to another section. Each could be fixed in a minor version only with
an alias kept forever. The roadmap holds them for the one major version, so that the interface of
2.0 is the one the book can teach without footnotes. Item 5 also removes a default that pointed
at the simulator.

## Impact analysis

### Requirements

Changed: SRS-CTL-022 (a request without `api` is refused too, and the refusal of a version names
the migration note) and SRS-CFG-001 (every key has a default except the source type). Added:
SRS-CFG-013 (no source is assumed), SRS-CFG-014 (a 1.x configuration is refused with the
migration pointer) and SRS-CFG-015 (the migration tool's result validates and keeps every
value).
No row of SRS-CTL, SRS-HW or SRS-OUT names a renamed field, so their texts stand; their tests
read the new names. Verification repeated: every SRS-CTL and SRS-CFG requirement, the system
tests and the golden runs (whose run records contain the effective configuration).

### Software items and safety class

Items `protocol`, `config`, `service` (the status fields), `output` (the effective configuration
in the run record), `hw` (the board fields of the status), and the tools that read the status or
write configurations (`tools/soak.py`, `tools/e2e.py`, the calibration and QC tools, the system
tests). No class changes.

### Risk

H-04 (acquisition settings other than intended): renaming fields can make an old file mean
something else. Control: a 1.x file is refused outright, not read with defaults; the migration
tool is tested on every configuration in the repository and its output validated. H-06 is
reduced further by item 5.

### SOUP

None.

### Interfaces and data formats

Breaking, by design: the control API 3.0 and the acquisition configuration 2.0, with the
integrity verdict's loss counter `/sorter/out_of_order`, now `/sorter_counters/out_of_order`.
The run record and the list-mode metadata copy the effective configuration, so those written by
2.0 have the new names. No tool reads a renamed field of a copied configuration (searched: the
verify, QC, calibration, reconstruction and end-to-end tools read the corrections block, whose
`coincidence_window_ps` is a data-format key that does not change), so records written earlier
stay readable. The golden run's record holds the data, not the configuration: it passes
unchanged with the converted configuration, which shows that the conversion keeps the run.

### Documents

SRS (version 33), the architecture description (version 25: external interfaces, configuration,
observability) and its schema file `acquisition-config.schema.json`, ADR 0036, the migration note
`docs/migration-2.0.md`, the tool list (TL-49), the MDQ-L1 format description (what its
metadata copies), the CHANGELOG and the release notes of 2.0. The control API has no interface
control document of its own; ADR 0003, ADR 0013 and the architecture description are its
description. The book: Chapters 6, 9, 10, 16, 17 and 21 show the new forms, re-recorded against
the 3.0 server, and the figures and text use "center".

### Regulatory

The intended use does not change. The change alters interfaces of a class B program; it is
verified by the full release checks, and the release notes name it as breaking.

## Verification

Tests: `ControlProtocol.VersioningAndMalformedInput`,
`ControlProtocol.StatusFieldsMatchTheApiVersion`, `Config.TheSourceIsNeverADefault`,
`Config.AVersion1FileIsRefusedWithTheWayToConvertIt`,
`Config.RenamedFieldsAreUnknownInTheirOldPlaces`,
`Conversion.test_every_1x_configuration_converts_into_a_valid_2_0_document`; and the checks below.

- Unit tests of the protocol (a 2.x request and a request without `api` are refused with
  `unsupported_api`; the status fields match `status_fields` for 3.0) and of the configuration
  (a 1.x file is refused with the pointer; each renamed field in its new place; `source.type`
  required).
- `tools/test_migrate_config.py`: every 1.x configuration in the repository migrates to a file
  that validates and gives the same effective configuration.
- The six presets, the product preset, the system tests and the golden runs; the exercises and
  solutions; the release checks at 2.0.0-rc.

## Decision

Approved on 2026-11-16 by the coordinator under the software lead's standing delegation of
2026-11-15, as proposed, with two conditions: `tools/migrate_config.py` is tested on every 1.x
configuration in the repository and the book, and each converted file validates against schema
2.0; every book listing, exercise and solution that shows a request or a configuration changes in
the same change, and a test checks that no 2.x request and no 1.x configuration remains in the
book.
