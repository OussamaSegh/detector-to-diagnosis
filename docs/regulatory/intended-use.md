# MiniDAQ: intended use

Version 3 (MiniDAQ 0.4.0-dev, release 0.4.0). Status: draft for review.

MiniDAQ is a learning project, not a medical device. This document is written as if MiniDAQ
were the data acquisition (DAQ) software of a dedicated brain PET scanner, so that the rest of
the regulatory file (requirements, risk analysis, verification) has something definite to
trace to. Where a statement belongs to the scanner rather than to its software, it says so.
Statements about your scanner are typical values for a brain PET scanner, not the manufacturer's
(assumption: confirm with team, against your scanner's instructions for use).

## Intended purpose

MiniDAQ is the data acquisition software of a positron emission tomography (PET) scanner
dedicated to imaging the human brain. It receives the time-stamped detections of the
scanner's detectors, forms coincidences, and stores them as list-mode data together with the
acquisition settings and the counts of everything it received, rejected or lost. The scanner's
reconstruction software turns these data into images of the distribution of a
radiopharmaceutical in the brain, which a qualified physician uses for diagnosis.

MiniDAQ itself produces no image, no measurement for the physician and no diagnostic
information. Its outputs are inputs to reconstruction, calibration and quality control.

## Intended users

- Technologists, who start and stop acquisitions through the scanner's workflow software, not
  through MiniDAQ directly.
- Service engineers and physicists, who configure acquisitions, read the status and the
  counters, and run quality control and calibration acquisitions.
- No patient operates or sees MiniDAQ.

## Patient population

That of the scanner: adults referred for a PET examination of the brain, for example in the
evaluation of cognitive impairment (assumption: confirm with team, from the scanner's
intended purpose). MiniDAQ processes no patient identity (see "Data").

## Use environment

The scanner's acquisition computer, inside the nuclear medicine or radiology department of a
hospital or imaging center. The readout electronics are connected over a dedicated network
that carries nothing else; the control interface is reachable only from the scanner's own
computers (assumption: confirm with team how your scanner's networks are separated).

## Principle of operation

The detectors send singles (a crystal, a time and an energy) over a readout link. MiniDAQ
checks every packet, puts the singles in time order, pairs them into prompt and
delayed coincidences with configured time, energy and geometry windows, and writes them to
list-mode files that are checksummed and crash-safe. Every stage counts what it passes,
rejects and loses, and the counts are stored with the run.

## Contraindications and limitations

- MiniDAQ has no contraindications of its own; those of the scanner and the radiopharmaceutical
  apply.
- Its count-rate capability is limited by the readout link and the sorter. Above the scanner's
  specified activity range, losses rise and are reported, not hidden.
- It does not correct the data for dead time, randoms, scatter, attenuation or decay; the
  reconstruction does, using the counters MiniDAQ records.

## Data

List-mode files carry a run name, never a patient's name, ID or birth date. The link between
a run and a patient is held by the scanner's workflow software. Simulated acquisitions are
marked as simulated in every file.

Every run record carries an integrity verdict (`integrity.complete`) with the counters of any
data lost on the way to the disk. Software that reconstructs or analyzes MiniDAQ's data checks
the verdict first, and treats a run whose verdict is not complete as incomplete (risk control
RC-05 in the [hazard analysis](risk/hazards.json)).

## What MiniDAQ is not

- Not standalone software: it runs only as part of the scanner, and its regulatory class is the
  scanner's ([regulatory context](regulatory-context.md)).
- Not a source of clinical decisions: it informs none directly.
- Not a medical device in this repository: everything here is an exercise.

## Document history

| Version | Change |
|---|---|
| 1 | First version (Chapter 13). |
| 2 | The integrity verdict that software reading MiniDAQ's data checks first (risk control RC-05, Chapter 15), and this history (Chapter 16). |
| 3 | Editorial, recorded at the release checks of 0.4.0 (MDQ-PR-030): the text names no manufacturer (the book is generic, commit e50a79e); the content is unchanged. |
