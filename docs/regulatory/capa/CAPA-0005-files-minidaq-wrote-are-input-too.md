# CAPA-0005: Files MiniDAQ wrote itself, read without the checks of untrusted input

| Field | Value |
|---|---|
| Status | implemented |
| Opened | 2026-11-16, by the software lead (internal audit before release 2.0.0) |
| Source | MDQ-PR-071; at the audit, MDQ-PR-074, MDQ-PR-075 and MDQ-PR-076 |
| Owner | software lead |
| Effectiveness check | release 2.1.0 |

## Problem

The maintenance plan (section 6) asks for a CAPA evaluation when a problem reaches a release by
the same cause as an earlier one. MDQ-PR-071 reached release 1.3.0: `verify_signed_run` read a
signed run record's fields with nlohmann accessors that throw on another type, the cause that
CAPA-0003 had removed from the control protocol in 0.4.0. Its root cause was that a signed
record was treated as trusted. The internal audit of 2026-11-16 read every JSON parser in
`minidaq/src` and `minidaq/apps` against rule 3 of the coding standard and found two more of the
same kind, both released since early versions and both reached only by a file changed after it
was written: the update store's `state.json` (MDQ-PR-074) and the delayed window in a list-mode
file's metadata (MDQ-PR-075).

## Investigation

`grep -rn "json::parse" minidaq/src minidaq/apps` lists 13 places. Each was classified by where
its text comes from and whether a fuzz target feeds it (rule 3.4):

| Parser | Source of the text | Fuzz target before | Defect |
|---|---|---|---|
| `config/acquisition_config.cpp` | a person's configuration | `fuzz_config` | none |
| `config/calibration_file.cpp` | the calibration procedure | `fuzz_calibration` | none |
| `control/control_protocol.cpp` | a client | `fuzz_protocol` | none |
| `config/hardware_config.cpp` | a site's hardware description | none | none found |
| `update/bundle.cpp`, the manifest | a bundle, signed | none | none found |
| `update/slots.cpp`, `state.json` | minidaq_update itself | none | MDQ-PR-074 |
| `control/access.cpp`, the token file | a site's administrator | none | none found |
| `control/listmode_sink.cpp:230` | the run record the server is writing | not a reader of a file | none |
| `control/listmode_sink.cpp:492`, `verify_signed_run` | a signed run record | none | MDQ-PR-071, fixed in 1.3.0's review |
| `apps/minidaq_listmode.cpp:117` | list-mode metadata, printed only | `fuzz_listmode` reads the header | none |
| `apps/minidaq_listmode.cpp:199` | list-mode metadata, one field read | none for the field | MDQ-PR-075 |
| `apps/minidaq_ctl.cpp`, two places | the server's response; a person's configuration, sent on | not a reader the server trusts | none |

The five readers without a fuzz target were all of files that a person or MiniDAQ's own programs
write: none of them was a socket or a configuration, the two kinds that Chapter 7 named when the
rule was written.

## Root cause

Rule 3 named the inputs that cross the process boundary as configuration files, control requests,
paths, arguments and detector data. Files that MiniDAQ wrote and reads again were not named, and
each reader was written for the files its writer makes. Rule 3.4 asks for a fuzz target per parser
of external input, so those parsers had none, and nothing fed them a field of another type.
CAPA-0003's correction was a test of one parser's fields; it did not change what counts as
external input.

## Correction

MDQ-PR-074, MDQ-PR-075 and MDQ-PR-076 are fixed, each with a test that failed before the fix.
MDQ-PR-071 was fixed by the review of 1.3.0.

## Corrective action

- Coding standard version 9, rule 3: a file that MiniDAQ's own programs wrote earlier and read
  again (run records, signed or not, list-mode metadata, the update store's state) is untrusted
  input; rule 3.4 says that a reader of a JSON file joins `fuzz_documents` as a mode of its own.
- `fuzz/fuzz_documents.cpp`, a fuzz target with five modes chosen by the first byte: the hardware
  description, an update manifest, the token file, a signed run record (signed with a key the
  target makes at start-up, so that the input reaches the fields, as MDQ-PR-071 needed) and the
  update store's `state.json`. Its seeds hold the inputs of MDQ-PR-071 and MDQ-PR-074. It runs in
  CI's `fuzz-smoke` job, as every target in `fuzz/CMakeLists.txt` does, and for ten minutes in
  the release checks (`tools/release_checks.sh`, part 4).

## Preventive action

The Python readers of the same files were read too. `verify_run` in
`analysis/src/minidaq_analysis/signature.py` was corrected with MDQ-PR-071 and turns a field of
another type into a `SignatureError`. The QC report's reader of the metadata,
`analysis/src/minidaq_analysis/report.py`, was not: a list as the delayed window ended the tool
with a traceback (MDQ-PR-076), now a `FormatError` that the tool reports. A reader added later is
caught by review against rule 3.4.

## Verification of the actions

`fuzz_documents` ends with the exception of MDQ-PR-074 on its seed `state-mdq-pr-074` when built on
the code before the fix (checked), and runs clean after it; a 60-second campaign from the seeds ran
101,480 inputs with 3,134 edges covered and no crash. `Update.OpenRefusesAStoreItCannotTrust`,
`tools.listmode` and
`test_report.py::test_metadata_with_a_field_of_another_type_is_an_error_not_a_crash` failed before
their fixes and pass after them. No requirement or risk control is weakened: each fix refuses or
falls back where the code before stopped with an exception.

## Effectiveness check

Criterion: the fuzz-smoke job runs `fuzz_documents` on every change, the release checks of 2.1.0
run it for ten minutes without a crash, and no problem report between this CAPA and release
2.1.0 has the cause "a field of a file MiniDAQ reads was read without checking its type". Due:
release 2.1.0.

## Closure

Open until the effectiveness check.
