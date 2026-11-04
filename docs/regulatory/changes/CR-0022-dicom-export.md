# CR-0022: The export of a reconstructed image to the hospital's archive in DICOM

| Field | Value |
|---|---|
| Status | approved |
| Requested | 2026-11-04, by the software lead |
| Source | improvement: DICOM and PACS integration (Chapter 35) |
| Decision | approved, 2026-11-04, software lead |
| Commits | none yet |

## Description

1. **The package** `tools/dicom` (TL-44): the encoding of data sets in Explicit VR Little Endian
   and Implicit VR Little Endian and the DICOM file format, with a strict reader; UIDs under the
   2.25 root, derived from the content; a PET Image series from a reconstructed image, the
   order of the study and the acquisition, with the checks a series must pass before it leaves;
   the DICOM upper layer and the C-ECHO and C-STORE services as a service class user; a storage
   service class provider for the tests, with faults to inject; and a store-and-forward outbox.
2. **The command** `tools/pacs.py`: export, send, echo, a test archive, and a dump of a file.
3. **Independent checks** in the tests: pydicom 3.0.2 and pynetdicom 3.0.4 (TL-45), pinned in
   `analysis/requirements.lock` and required in CI's job python (`MINIDAQ_DICOM_ORACLE_REQUIRED`).
   The user approved them as test-only tools on 2026-11-04. The first pin, pydicom 3.0.1, had two
   published advisories (a path traversal through a DICOMDIR, which the tests do not use), found
   by `tools/lock_audit.py` before the first commit; 3.0.2 has none.

## Reason

The chain of Chapter 33 ends with an image in a numpy file, which no hospital can read. A scanner
delivers its images to the archive in DICOM, and the step is where three hazards that the earlier
chapters could not have live: a series filed under the wrong patient or study (H-15), values or
positions that a viewer reads differently from what the reconstruction made (H-16), and a series
that does not arrive whole while it is reported as sent (H-17).

## Impact analysis

### Requirements

Added (SRS version 24): SRS-DCM-001 (the encoding and the strict reader), SRS-DCM-002 (the
series and its checks), SRS-DCM-003 (the pixel values), SRS-DCM-004 (the geometry), SRS-DCM-005
(the identifiers), SRS-DCM-006 (the network), SRS-DCM-007 (the outbox). None changed or
withdrawn. These seven are the differences from the requirements baseline that this request
names.

### Software items and safety class

No item of the product changes. The export is a tool (TL-44, class T3, as the reconstruction is):
its output is the image a reader reads. The preliminary hazard HZ-5 is added to the software
items with the severity "serious" of H-15; no shipped item has it, so no class changes
(`tools/check_items.py` passes). In a scanner's software the export would be an item of the
product, and HZ-5 would make it class C unless a control outside the software is credited
(assumption: confirm with team).

### Risk

New hazards H-15, H-16 and H-17 under HZ-5, with the risk controls RC-47 to RC-51; each is
acceptable after its controls (S3/P2, S3/P2, S2/P2). No other hazard or estimate changes.

### SOUP

None in the product. Two test-only tools (TL-45) in the lock file, whose vulnerabilities
`tools/lock_audit.py` checks in CI.

### Interfaces and data formats

New output: DICOM PET Image Storage objects (SOP class 1.2.840.10008.5.1.4.1.1.128) in files and
over the network (an association on TCP, C-ECHO and C-STORE). The export's conformance is
described in the chapter; a scanner states it in a DICOM conformance statement (part 2). The
product's interfaces do not change.

### Documents

The SRS, version 24; the risk file (H-15 to H-17, RC-47 to RC-51) and the software items (HZ-5);
the tool list (TL-44, TL-45) and `tools.md`; the threat model, version 10 (the export is outside
its scope and is recorded as a gap); ADR 0030; the trace matrix; the lock file; CI's job python;
the CHANGELOG.

### Regulatory

The intended use of MiniDAQ does not change: the export is a teaching tool outside the product,
as the reconstruction is. Software that sends images to an archive is part of a medical device's
software and handles personal health data, so a scanner's export comes with its own requirements
for data protection and cybersecurity (assumption: confirm with team).

## Verification

`tools/test_dicom.py` (the test `tools.dicom`): the encoding byte for byte
(Encoding.test_the_two_explicit_header_forms_and_the_implicit_one,
Encoding.test_the_reader_refuses_damaged_or_hostile_input), the series and its checks
(Series.test_the_check_finds_each_problem_a_series_can_have), the values
(Series.test_each_value_comes_back_within_half_a_slope), the geometry
(Series.test_a_pixel_lands_at_its_position_in_the_patient), the identifiers
(Series.test_an_order_that_cannot_file_the_series_is_refused,
Series.test_uids_are_valid_and_derived_from_the_content), the network
(Network.test_an_abort_and_a_silent_archive_end_the_association_with_an_error) and the outbox
(Outbox.test_an_interrupted_send_resumes_without_a_second_copy); the independent checks with
pydicom and pynetdicom (Encoding.test_independent_pydicom_reads_every_attribute_as_written,
Network.test_independent_store_to_pynetdicom_and_from_it); `docs.trace`, `docs.risk`,
`docs.baseline`; the whole ctest. The measurements of the phantom image's export are kept in
`measurements/ch35/`.

## Decision

Approved on 2026-11-04 by the software lead: a tool outside the product that carries the image the
rest of the way, with its three hazards analyzed and controlled, and test-only dependencies the
user approved.
