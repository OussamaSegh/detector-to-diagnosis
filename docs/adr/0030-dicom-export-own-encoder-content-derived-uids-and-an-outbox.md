# 0030. The DICOM export: an own encoder checked by independent peers, UIDs derived from the content, and an outbox

Date: 2026-11-04
Status: Accepted

## Context

Chapter 35 takes MiniDAQ's reconstructed image to the hospital: a series of PET Image objects in
DICOM, sent to a picture archive (PACS) with the C-STORE service. Three things can go wrong that
matter to a patient: the series is filed under the wrong patient or study (H-15), its values or
positions are read differently from what the reconstruction made (H-16), or it does not arrive
whole (H-17). The export needs a DICOM encoder, a network client, unique identifiers and a way to
survive an archive that is down or refuses an object.

## Options

1. **The encoder and the network client.** A DICOM toolkit as SOUP (pydicom and pynetdicom in
   Python, DCMTK or GDCM in C++); or an own implementation of the small part of the standard the
   export uses (Explicit VR Little Endian, the PET Image IOD, the upper layer, C-ECHO and C-STORE),
   checked by a toolkit used only in the tests.
2. **The UIDs.** A registered root with a counter; random UIDs under 2.25 (UUID version 4); or
   UIDs under 2.25 derived from the content (UUID version 5 of the study UID, a digest of the
   image and all its metadata, and the slice).
3. **Delivery.** Send directly from the reconstruction and report the result; or a
   store-and-forward outbox on disk that keeps every instance until the archive's status for it
   is a success, with a journal of every attempt.
4. **The pixel encoding.** 32-bit floating point pixels (the Enhanced PET IOD); or 16-bit integers
   with a rescale slope per slice (the PET Image IOD, which every archive and viewer reads).

## Decision

- **An own encoder and client, checked by pydicom and pynetdicom in the tests** (option 1, the
  second). The part of the standard the export needs is small enough to write and to test byte
  for byte, and writing it is what the chapter teaches. A writer checked only by its own reader can
  share its mistakes, so the tests read every file with pydicom and send to and receive from
  pynetdicom (TL-45, approved by the user as test-only tools on 2026-11-04). Nothing of them
  ships or is needed to export.
- **UIDs derived from the content** (option 2, the third). An export that is repeated after a
  failed send gives the same UIDs, so the archive replaces and does not duplicate; a different
  image, or the same image with different metadata, gives different UIDs, so a new
  reconstruction never replaces an older one. The 2.25 root needs no registration.
- **An outbox** (option 3, the second). An archive that is down for maintenance, out of space or
  refusing an object is normal operation; only the archive's own status can take an instance out
  of the queue.
- **16-bit integers with a slope per slice** (option 4, the second), the stored values computed
  with the slope as written in the file.

## Consequences

### Positive

- Every byte the export writes is explained by a test, and two independent implementations agree
  on it.
- A repeated export or a resumed send cannot create a second copy of a series; the tests show one
  copy per instance after an interrupted send and a second export.
- The archive's failures are visible: what is pending, sent and failed, and why, in the journal.

### Negative

- An own implementation is code to maintain; a real product would more likely use a toolkit and
  treat it as SOUP, with its anomaly list reviewed at every release.
- The independent reader is not strict: pydicom 3.0.2 read without a warning a sequence whose item
  tag was written in the wrong byte order (measurements/ch35). The independent checks find
  disagreements, not every violation of the standard; the strict reader of this package and a
  validator of the IOD are still needed. The export does not run an IOD validator such as
  dciodvfy, which would be a new tool.
- Content-derived UIDs make two exports of identical content one series, even if someone wanted
  two; that is the intended behavior.
- Sending in the clear: the export does not use TLS (part 15). The export is outside the threat
  model's scope, as the reconstruction is; the threat model records it as a gap (section 7) for
  the console that would ship it.
