# CR-0027: Signed run records, calibration tables and QC reports

| Field | Value |
|---|---|
| Status | approved |
| Requested | 2026-11-15, by the software lead |
| Source | threat model gaps T-27 (list-mode files and QC reports) and T-54 (calibration tables); roadmap 2.0.0, theme B |
| Decision | approved, 2026-11-15, under the software lead's standing delegation of 2026-11-15 |
| Commits | none yet |

## Description

What MiniDAQ produces and uses can be shown to be unchanged since the program that made it
signed it, with the Ed25519 signatures that already vouch for update bundles (ADR 0020).

1. **Run records.** With `minidaq_server --signing-key FILE`, an Ed25519 private key read once at
   start-up, the list-mode sink hashes every file as it writes it, lists each file's size and
   SHA-256 in the run record (`file_digests`, with the key's id in `signature`) and writes the
   Ed25519 signature of the record's exact bytes to `<record>.sig` (SRS-OUT-013). The data is
   never read a second time. Without the option, the record is as before.
2. **Verification of a run.** `control::verify_signed_run` and `minidaq_listmode verify-run --keys
   DIR RECORD` accept a run only if the record's signature verifies with a key of the trust store
   and every listed file has its recorded size and SHA-256 (SRS-OUT-014).
3. **Calibration tables.** `tools/calib --sign KEY` writes `<table>.sig`. With
   `minidaq_server --calibration-keys DIR`, `configure` refuses a table whose signature is missing
   or verifies with no key of DIR, before the table is parsed (SRS-CAL-008). Without the option,
   tables are checked as before.
4. **QC reports.** `minidaq-qc --keys DIR` makes no report of a run that does not verify
   (SRS-ANA-007); `minidaq-qc --sign KEY` signs `report.json`, `provenance.json` and `report.md`
   (SRS-ANA-008).
5. **One implementation.** Ed25519 and SHA-256 move from `update/bundle.cpp` into
   `control/signing.cpp` (library `minidaq_signing`, item `access`), which the update tool, the
   server and `minidaq_listmode` link. The Python side uses the `openssl` command line, as
   `tools/make_update.py` does.

## Reason

The CRC-32 of every list-mode block and of every calibration table detects damage, not a
deliberate change with a recomputed CRC (threat model, section 7). Whoever can write the run's
files can change a counter in the record that makes an incomplete run look complete, or change a
crystal's time offset within the limits, and nothing would show it; a QC report can be edited
after the fact. Without the change, the integrity of data and calibration rests only on the
file system's permissions, which the site provides.

## Impact analysis

### Requirements

Added: SRS-OUT-013, SRS-OUT-014, SRS-CAL-008, SRS-ANA-007, SRS-ANA-008 (SRS version 30).
Verification repeated: SRS-PLT-003 (the update tool's verification, moved), SRS-OUT-009 to
SRS-OUT-012 (the sink and its run record), SRS-CAL-001 to SRS-CAL-007, SRS-ANA-001 to
SRS-ANA-006.

### Software items and safety class

Items `access` (the new `control/signing`), `output` (the sink, the verification), `service` (a
calibration verifier port in `ServiceOptions`), `update` (calls the shared verification),
`server` (two options), and the tools `minidaq_listmode`, `tools/calib` and the analysis
package. No class changes. The acquisition threads are untouched: the hashing runs in the
sink's own I/O thread, and only with a key.

### Risk

The threats T-27 and T-54 gain a control that a site can switch on; their status stays
`mitigated`, with the gap of section 7 closed for a site that uses the keys. No hazard's
estimate changes: the integrity verdict of a run (RC-01) and the calibration's limits (RC-35,
RC-37) are as before, and the signature adds detection of a deliberate change after the fact.
New failure modes: a lost or unreadable key stops the server at start-up (it does not run
unsigned by surprise); a lost public key makes runs or tables fail verification, loudly. Key
management is the site's (assumption: confirm with team), as for update keys.

### SOUP

OpenSSL: Ed25519 signing (`EVP_DigestSign`), private keys from PEM. The SOUP list, version 26.
No new SOUP item and no new dependency.

### Interfaces and data formats

The run record gains two keys, `file_digests` and `signature`, only when signing (additive; the
analysis package and every reader ignore keys they do not use). New files `<record>.sig`,
`<table>.sig`, `<report file>.sig`. Two server options, one `minidaq_listmode` command, two
`minidaq-qc` options, one `tools/calib` option. The control API does not change.

### Documents

The SRS, version 30; the threat model, version 15 (T-27, T-54, section 7); the SOUP list,
version 26; the architecture, version 22; ADR 0034; Chapter 25's section on signatures and notes
in Chapters 12, 26 and 31; the CHANGELOG.

### Regulatory

None: the intended use does not change. Signing is a security control a site can enable; the
default behavior is unchanged.

## Verification

Tests with keys made by each test, none kept in the repository: `Signing.SignsAndVerifiesWithTheKeysOfADirectory`,
`Signing.ASignedRunVerifiesUntilAFileOrItsRecordChanges` (a changed byte of a data file, a changed
record, a key the site did not install, a missing file, a missing signature),
`Signing.WithoutAKeyTheRunRecordIsAsBefore`,
`Signing.ACalibrationTableIsUsedOnlyWithASignatureATrustedKeyVerifies` (no signature, a wrong
key, a changed table), the update tests (`Update.*`), `Procedure.test_writes_a_table_that_matches_the_detector`,
`test_signature::test_a_signed_run_verifies_until_a_file_or_its_record_changes`,
`test_signature::test_the_qc_refuses_a_run_it_cannot_verify_and_signs_its_report`; a server run
with `--signing-key` whose record `minidaq_listmode verify-run` and the analysis package both
verified; the whole ctest; static analysis.

## Decision

Approved on 2026-11-15 under the standing delegation that the software lead gave on 2026-11-15
for the work towards 2.0.0, with one condition: no private key in the repository; every key is
made by the test that uses it.
