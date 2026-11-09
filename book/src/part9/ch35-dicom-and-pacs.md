# DICOM and PACS: getting the image to the hospital {#ch35}

::: box-why
An image that stays on the acquisition computer helps no one. A radiologist reads it in a viewer
that has never heard of your scanner, from an archive that stores the images of every scanner in
the hospital, under the patient and the study that the hospital's own systems created. The only
language all of them share is DICOM. The export is a small piece of code at the very end of the
chain, and it is where an image can be filed under the wrong patient, shown with the patient's
left on the wrong side, read with values ten thousand times too small, or lost on the way while
the console says "sent". None of these makes the image look wrong. This chapter writes the
export, byte by byte, and makes each of those mistakes fail a test.
:::

**A day in the life.** A PET scan finishes late on a Friday. The console exports the series and
starts sending it to the archive; halfway through, the archive's storage node restarts for a
planned update and drops the connection. The console shows a failure, and the technologist
presses "send again". The export, written years ago, gives every send fresh identifiers, so the
archive now holds two series of the same scan: the first with 112 of its 220 slices, the second
complete. On Monday the radiologist opens the study, and the viewer shows the first series, the
one with the earlier time. A small lesion in the lower slices is not in it. The software did what
each line of its code said. The export had no notion that sending the same image twice should
give the archive the same image, not two.

## Learning objectives {.unnumbered}

After this chapter you can:

1. Explain what DICOM defines (information objects, services, encodings, files and the network)
   and where an export fits among the hospital's systems.
2. Encode a DICOM data set by hand: tags, value representations, lengths, padding and order, and
   write a DICOM file with its meta information.
3. Build a PET Image series from a reconstructed image, with the attributes its modules require
   and the values a viewer needs to compute activity and position.
4. Store pixel values so that every reader gets them back within a known error, and place every
   pixel in the patient's coordinate system.
5. Choose identifiers so that a repeated export is the same series and a new reconstruction is a
   new one.
6. Send images with C-STORE over a DICOM association, and keep them until the archive has said it
   stored them.
7. Test an implementation of a standard against independent implementations, and know what such a
   test can and cannot show.

## Prerequisites and estimated time {.unnumbered}

Chapter 12 (the list-mode file and its run record), Chapter 15 (hazards and risk controls),
Chapters 28 and 30 (the reconstructed image and its figures of merit) and Chapter 33 (the chain
end to end, whose phantom image this chapter exports). Some Python and numpy. Reading: about 3
hours. Exercises: 6 hours. Milestone: 3 hours. If time is short, do Exercise 35.2.

## What leaves the scanner, and where it goes

DICOM (Digital Imaging and Communications in Medicine) is a standard published by NEMA in many
parts, revised several times a year and free to read. It defines four things that this chapter
uses:

- **Information objects.** An Information Object Definition (IOD) says what a kind of object
  holds: a CT image, a PET image, a structured report. An IOD is made of **modules**, groups of
  attributes such as Patient, General Study or Image Plane, each mandatory, conditional or
  optional for that IOD. Part 3 defines them.
- **Encodings.** How the attributes of an object become bytes: a data set of data elements, each
  with a tag, a value representation (VR), a length and a value; and the transfer syntaxes that
  fix the byte order and whether the VR is written. Parts 5 and 6.
- **Services.** What one system asks another to do with an object: store it (C-STORE), check that
  the other end answers (C-ECHO), find, move and get objects, commit to keeping them. A **SOP
  class** (service-object pair) is a service applied to an IOD: "PET Image Storage" is C-STORE of
  a PET Image object, and has a unique identifier of its own, 1.2.840.10008.5.1.4.1.1.128.
  Parts 4 and 7.
- **Files and the network.** A DICOM file (part 10) and the protocol that carries services over
  TCP (part 8).

Part 2 asks every product to publish a **conformance statement**: which SOP classes it supports,
as a user or provider of the service, with which transfer syntaxes and options. A hospital's
integration engineer reads it before connecting your scanner; your team writes it, and it is
worth reading another vendor's before writing your own.

Around the scanner, the hospital has a radiology information system (RIS) that schedules the
exam, a **picture archive and communication system** (PACS) that stores the images and serves
them to the viewers, and often a **modality worklist** server from which the scanner's console
fetches the scheduled patients and their identifiers, so that nobody types a patient ID twice.
IHE, an initiative of the users and vendors, describes how these systems work together in
profiles such as Scheduled Workflow, and runs connectathons where vendors test their products
against each other's.

This chapter's export does the last step only: it takes the image, the patient and study
identifiers that the console got from the worklist (the **order**), the acquisition's facts, and
sends a series to the archive. The code is `tools/dicom` with its command `tools/pacs.py` (tool
TL-44, SRS-DCM-001 to SRS-DCM-007, CR-0022, ADR 0030). It is a tool outside MiniDAQ's product, as
the reconstruction is: in a scanner it belongs to the console's software, which is where it would
be classified (the box at the end of the chapter comes back to that).

## A data set, byte by byte

A **data element** is a tag, a value representation, a length and a value. The tag is a pair of
16-bit numbers, the group and the element, written (0010,0020) for Patient ID. The VR says what
kind of value it is: PN a person's name, LO a long string, UI a unique identifier, DS a decimal
number written as text, US an unsigned 16-bit integer, SQ a sequence of nested data sets, OW a
run of 16-bit words, and about thirty more. The package's dictionary holds the tags it uses:

```{.python include="tools/dicom/dictionary.py" snippet="dictionary"}
```

A **transfer syntax** fixes how elements become bytes. The export writes Explicit VR Little
Endian (UID 1.2.840.10008.1.2.1): numbers in little-endian order, and each element carrying its
VR. There are two header forms, and the choice between them is the first thing a hand-written
encoder gets wrong:

```{.python include="tools/dicom/encode.py" snippet="encode_element"}
```

Most VRs get a 2-byte length. The VRs that can be long (OB, OW, SQ, UN, UT and a few others) get
two reserved bytes and a 4-byte length. Implicit VR Little Endian, the default syntax of the
standard and the one DIMSE commands always use, writes no VR at all; a reader takes it from its
dictionary, which is why a reader of an implicit data set with a private or unknown tag cannot
tell a string from a number.

Three rules apply to every value, and the writer enforces them rather than leaving them to the
caller:

- **Even length.** Every value has an even number of bytes. A UID is padded with a zero byte,
  other text with a space, binary with a zero.
- **Ascending order.** The elements of a data set are in ascending tag order. A reader that
  streams a file relies on it, and so does every tool that compares two files.
- **Limits per VR.** A short string (SH) holds 16 characters, a long string 64, a UID 64, a code
  string (CS) 16 capitals, digits, spaces and underscores, a person name 64 per component group.
  A backslash separates multiple values, so it cannot appear inside one.

The writer refuses a value that breaks a rule; it never truncates. That is the difference between
an encoder written for a demonstration and one written for patients. An accession number of 17
characters cut to 16 is another accession number, and the archive will file the series under it
without complaint. A patient name with an umlaut written in ASCII is a question mark or an
exception; the export writes Specific Character Set (0008,0005) ISO_IR 192 (UTF-8) so that it can
carry any name the hospital's systems hold, and the encoder refuses a name the declared set cannot
encode.

Numbers that are text deserve their own paragraph. A **Decimal String** (DS) is at most 16
characters. Whatever reads the file reads that text, not the number in your program:

```{.python include="tools/dicom/encode.py" snippet="format_ds"}
```

`%.16g` first, then fewer digits until it fits: a plain decimal keeps 15 or 16 significant
digits, a value with an exponent at least 10 (`-1.234567890e-09` is 16 characters). The obvious
alternative, six decimals with `f"{x:.6f}"`, is what most quick exporters write, and Exercise 35.1
shows where it ends: for the phantom image of Chapter 33, whose rescale slope is 1.43e-7, six
decimals write `0.000000`, and a viewer shows every pixel as zero.

A **DICOM file** wraps one data set:

```{.python include="tools/dicom/encode.py" snippet="write_file"}
```

A 128-byte preamble (zeros, here), the four characters `DICM`, and the file meta information,
group 0002: always Explicit VR Little Endian whatever the data set's syntax, led by its group
length, and naming the SOP class and instance of the object, the transfer syntax of the data set,
and the implementation that wrote it. A file without `DICM` at byte 128 is not a DICOM file, even
if it holds a data set; older systems wrote such files, and a reader that guesses accepts garbage.

The package also has a reader, and it is strict where the writer is strict: it refuses an odd
length, a length that runs past the end of its input, elements out of order, nesting deeper than
eight sequences and any transfer syntax but the two it knows (SRS-DCM-001). The reader sees bytes
from an archive and from the network, which the export does not control; a length field of four
billion is a test case, not a curiosity.

## The PET Image object

The PET Image IOD (part 3, section A.21) lists its modules. Those it makes mandatory are Patient,
General Study, General Series, PET Series, PET Isotope, NM/PET Patient Orientation, Frame of
Reference, General Equipment, General Acquisition, General Image, Image Plane, Image Pixel, PET
Image and SOP Common; PET Multi-gated Acquisition is required for a gated series, and the rest are
optional. Each attribute of a module has a **type**: type 1 must be present with a value, type 2
must be present but may be empty (the sender does not know the value), type 3 may be left out,
and types 1C and 2C are type 1 or 2 under a condition. The export keeps the attributes it must
write in two lists, and its check of a series uses the same lists:

```{.python include="tools/dicom/pet.py" snippet="required"}
```

A few of these carry the meaning of the image, and each is a decision someone must make with the
physicists:

- **Units** (0054,1001). Bq/mL (`BQML`) for an image calibrated to activity concentration; MiniDAQ
  has no dose calibration, so its images are proportional counts, `PROPCNTS`, one of the defined
  terms of the PET Series module. A viewer computes a standardized uptake value only from `BQML`;
  writing it for an uncalibrated image would let it compute a wrong one.
- **Corrected Image** (0028,0051). Which corrections were applied: `NORM`, `ATTN`, `SCAT`, `RAN`,
  `DECY` and others. Chapter 33's phantom has normalization, attenuation and randoms, and no
  scatter correction; the attribute says so.
- **Decay Correction** (0054,1102). The time to which the image is decay corrected: `START` of
  the acquisition, or `NONE`. The export refuses `START` without `DECY` among the corrections,
  and `DECY` without `START`, because the two describe one fact.
- **Series Type** (0054,1000). `STATIC\IMAGE` here: one frame, reconstructed (not reprojected).
  A dynamic or gated series needs more attributes and other image indices.
- **Frame Reference Time** (0054,1300) and the **decay factor**. The frame reference time is an
  offset in milliseconds from the series time; the export writes the time at which the activity
  equals its mean over the frame, ln(λT/(1 − e^−λT^))/λ, a little earlier than the middle of the
  frame. With decay correction, the Decay Factor (0054,1321) is λT/(1 − e^−λT^): for a frame as
  long as one half-life, 2 ln 2, about 1.386, which the tests check.
- **The radiopharmaceutical.** A sequence with the radionuclide as a coded entry, fluorine-18 as
  code 77004003 in SNOMED CT (scheme `SCT`, meaning `^18^Fluorine`), its half-life (6586.2 s), its
  positron fraction (0.9686, the DDEP value; NNDC gives 0.9673), and, when the console knows them,
  the injected activity and the injection time. Both physical values must match the scanner's own
  table, which the dose calibrator and the decay correction share.
- **Times.** DICOM dates and times carry no time zone unless the object says it: a TM of
  093000 is half past nine where the scanner is. The export takes the acquisition's start only
  with a UTC offset, and writes Timezone Offset From UTC (0008,0201). A series acquired the
  night clocks change, without it, has a decay correction one hour wrong.

The patient's orientation is coded too: recumbent, with the modifier supine, and head first or
feet first relative to the gantry, all as SNOMED CT codes that the tests compare with pydicom's
code dictionary. The codes matter less to a viewer than the geometry of the next section, but an
archive that checks them refuses a series whose codes it does not know.

## Values a reader gets back

The PET Image IOD stores pixels as 16-bit integers, bits allocated and stored both 16, and maps
them to values with a rescale slope and an intercept that, for PET, is always zero. The export
gives every slice its own slope:

```{.python include="tools/dicom/pet.py" snippet="quantize"}
```

Three choices are in those lines (SRS-DCM-003):

- **A slope per slice.** The slope maps the slice's largest value to the largest stored value.
  One slope for a whole volume is simpler and costs dearly where the activity is low: in a
  47-slice volume made from the phantom image with one slice ten times hotter, the median relative
  error inside the object is 1.8e-5 in every slice with a slope per slice, and 2.4e-4 in the cold
  slices with one slope for the volume, 14 times larger (`measurements/ch35/dicom.txt`, section 2).
- **Signed when needed.** An OSEM image has no negative values; a filtered backprojection does.
  Unsigned 16-bit pixels with a negative value wrap to a large positive one, which a viewer shows
  as a hot spot. The export writes Pixel Representation 1 (signed) for a slice with a negative
  value, and 0 otherwise.
- **The slope as written.** The stored values are divided by `float(slope_text)`, the number a
  reader will parse, not by the slope the program computed. With 16 characters the two differ by
  less than 5e-10 relatively, and the rule still matters: it makes "every value comes back within
  half a slope" a property of the code, for every slope, rather than a property of the slopes that
  happened to be tested. On the phantom image the largest error is 0.4999 of a slope, 7.6e-6 of
  the image's maximum (section 2).

A value that is not finite, a NaN from a division by a zero sensitivity or an infinity from an
overflow, has no 16-bit representation; the export refuses the image rather than write a zero or a
maximum in its place.

## Where the pixel is

Three attributes place a slice in the patient: Image Position (Patient), the position of the
center of the first pixel; Image Orientation (Patient), the direction cosines of a row and of a
column; and Pixel Spacing, the distance between rows and then between columns. They are in the
**patient coordinate system**: x to the patient's left, y to the patient's back (posterior), z to
the head, in millimeters, often called LPS. A viewer uses them to show the slice the right way up,
to put the patient's left on the right side of the screen as radiologists expect, to measure, and
to fuse the PET with a CT of the same frame of reference.

The reconstruction knows none of that. Its image is in MiniDAQ's gantry frame: x along a row, to
the right seen from the front of the gantry; y up; z along the axis, into the gantry. Between the
two frames is the patient's position on the bed, which the console knows:

```{.python include="tools/dicom/pet.py" snippet="geometry"}
```

For a patient on their back, head first into the gantry (HFS), the patient's left is on the right
seen from the front, the head goes in first and up is anterior: gantry (x, y, z) is LPS
(x, −y, z). Feet first (FFS), (−x, −y, −z). The export writes the rows top down, so that the
column direction points to the patient's back, the way every viewer expects an axial slice; the
first pixel is then the one at the left of the top row, and its position follows from the signs.
Any other patient position is refused (SRS-DCM-004): a prone patient needs the gantry frame and
the bed's direction confirmed by the people who built them, and a table of signs is not that
confirmation (assumption: confirm with team the gantry frame of your scanner and the positions it
supports).

The image index numbers the slices in the order of their position along the slices' normal, the
cross product of the two orientation vectors, for a static series the slice index itself. The
tests place one hot pixel off the axis, at gantry x = +19 mm and y = +29 mm in the third slice,
and require it at LPS (19, −29, z) for HFS and (−19, −29, −z) for FFS, computed from the three
attributes as a viewer computes it. On the phantom image the cylinder's centroid comes out at
(0.12, −0.30, 0) mm, within a sixth of a pixel of the axis (section 4).

What the tests do not use is as important as what they do. A centered object hides a sign error
in the position; square pixels hide the order of Pixel Spacing, which is rows first; a single
patient position hides the mapping. The tests use an off-axis point, both positions and, in
Exercise 35.2, pixels that are not square.

## Identifiers: which patient, which study, which object

Every object carries identifiers at four levels: the patient (Patient ID, with the name and birth
date as attributes of the patient), the study (Study Instance UID, and the accession number of the
order), the series (Series Instance UID) and the instance (SOP Instance UID). The archive files an
object by them. Two of the hazards of this chapter are about them.

**The patient and the study come from the order, unchanged.** The export never invents a patient
ID, never reuses the previous study's, never fills an empty one with a default, and never edits
what it is given (SRS-DCM-005). It refuses an order without a patient ID or a patient name, a study
UID that is not a valid UID, a birth date that is not a date, and a time without a UTC offset.
Every instance of a series is checked to carry the same patient, study, series and frame of
reference before the series is written. An order can still be wrong, if someone picks the wrong
patient from the worklist; the export cannot know that, and the risk file says which controls
outside the software cover it (H-15).

**The other identifiers are UIDs**, at most 64 characters of digits and dots, globally unique.
An organization usually registers a root and numbers below it; the root 2.25 lets anyone make a
UID from a UUID instead, "2.25." and the UUID as one decimal number (ITU-T X.667), 44 characters
at most. The usual way is a random UUID for every new object. The export does something else:

```{.python include="tools/dicom/uid.py" snippet="derived"}
```

The series UID is derived from the study UID and a SHA-256 digest of the image and all its
metadata; each instance UID from the series UID and the slice; the frame of reference from the
study and the acquisition. The same image with the same metadata gives the same UIDs on any
machine; any change, one pixel or the reconstruction's description, gives different ones. That is
what the day in the life lacked. A series sent again after a failure is the same series, and the
archive replaces each instance it already has instead of adding a second series; a new
reconstruction of the same scan is a new series and never replaces the old one.

## Sending: associations and C-STORE

DICOM's network protocol (part 8) runs on TCP. Before any service, the two sides make an
**association**: the sender (the service class user, SCU) sends an A-ASSOCIATE-RQ with its own AE
title and the archive's (application entity titles, up to 16 characters, which the archive uses
to decide whom it talks to), and a list of **presentation contexts**: for each SOP class it wants
to use, the transfer syntaxes it can send. The archive (the service class provider, SCP) answers
with an A-ASSOCIATE-AC that accepts or refuses each context and names the syntax it chose, and
its maximum PDU length; or with an A-ASSOCIATE-RJ, with a reason. Every header of the protocol is
big-endian; the data sets inside are little-endian. An implementation that gets one of those
wrong fails on the first association, which is the kind of failure to prefer.

```{.python include="tools/dicom/net.py" snippet="associate"}
```

The export proposes PET Image Storage and Verification, each with both Explicit and Implicit VR
Little Endian, and asks for a time limit on every read: an archive that stops answering must end
the attempt with an error, not hang the console.

A DIMSE message is a **command set** and, for C-STORE, the data set. The command is always in
Implicit VR Little Endian, in group 0000: the affected SOP class and instance, the command field
(C-STORE-RQ is 0x0001), a message ID, and Command Data Set Type, which says whether a data set
follows. Both travel in P-DATA-TF PDUs, cut into fragments that fit the archive's maximum:

```{.python include="tools/dicom/net.py" snippet="fragments"}
```

Each fragment is a PDV item: its length, the presentation context, and a control byte whose bit 0
says command or data set and bit 1 says last fragment. A receiver reassembles them, which is
Exercise 35.3, and the harder half of the protocol to get right.

```{.python include="tools/dicom/net.py" snippet="store"}
```

The archive answers with a C-STORE-RSP whose status is the only statement about the instance
that counts:

```{.python include="tools/dicom/net.py" snippet="status"}
```

Success is 0x0000. A warning (0xB000, coercion of data elements, is the common one) means the
archive stored the instance but changed something in it or did not check it; the export counts it
as sent and keeps the status in its journal, because someone may need to know which attribute the
archive rewrote. A failure in 0xA7xx means the archive is out of resources and is worth retrying
later; any other failure (0xA9xx, the data set does not match the SOP class; 0xCxxx, the archive
cannot understand it) will fail again the same way.

The first version of the export took 2.07 s to send the 47 slices of the measurement's volume on
loopback, 44 ms per instance (section 5, which repeats it with a maximum PDU of 16 KiB). The time
was not in the encoding. The sender wrote the command and the data set in separate small writes, the
operating system held the last small segment back until the previous one was acknowledged (Nagle's
algorithm), and the receiver delayed its acknowledgment for up to 40 ms hoping to combine it with an
answer. With TCP_NODELAY set on the socket, the same series takes 58 to 66 ms, 36 times less;
pynetdicom's own archive takes 158 to 171 ms for it. The test of the association now checks that the
option is set. On a hospital network, where the archive is a server across a switch, the ratio would
differ; the waiting would not.

## An outbox, not a send

A send that fails is normal operation: the archive is down for maintenance, out of space for a
minute, or refuses one object whose attribute it does not accept. What must never happen is that
an instance is reported as sent, or deleted, before the archive has said it stored it. The export
does not send from the reconstruction. It writes the series into an **outbox** and sends from
there:

```{.python include="tools/dicom/outbox.py" snippet="send"}
```

The outbox is three directories and a journal. An instance enters `pending/` when the series has
passed its checks; it moves to `sent/` only after a success or warning status for it; it stays in
`pending/` after a transient failure, a timeout, an abort or a network error; and it moves to
`failed/` after any other failure, for a person to look at, because sending it again will fail
again. Every attempt is a line in `journal.jsonl`, appended and never rewritten: when the
radiologist asks on Monday why the series arrived at 07:12 and not on Friday, the answer is there
(SRS-DCM-007).

The measurement aborts the association after 20 of 47 instances. The outbox keeps 27 pending and
reports the error. The console then exports the same image again, as the technologist in the day
in the life did, and sends. The second export puts all 47 instances back in `pending/`, and the
outbox sends all 47; the archive ends with 47 instances, not 67, because the second export carried
the same UIDs and the archive replaced the 20 it already had. The journal holds 68 lines: 20
stores, the abort, and 47 stores (section 6). Sending again what was already stored costs time,
not correctness; an outbox that skipped instances already in `sent/` would save the time.

What the outbox does not do is ask the archive whether it still has the images tomorrow. A
success status says the archive accepted the instance; DICOM's Storage Commitment service asks it
to take responsibility for keeping it, and a scanner that deletes its local copies relies on it.
The export does not implement it, and the risk file says so.

## Checking against someone else

A writer checked only by its own reader can share its mistakes: an encoder and a decoder written
by the same person, from the same misreading of the standard, agree perfectly. The tests of the
export therefore use two implementations it does not use itself (TL-45, approved as test-only
tools): **pydicom** reads every file the export writes and compares every attribute, and
**pynetdicom** is an archive the export sends to and a sender the export's test archive receives
from. They also check the dictionary: every tag's keyword and VR must agree with pydicom's, and
every code with pydicom's code dictionary. In CI's job python these tests cannot be skipped.

Two findings from that work belong in this chapter. The first came from the export's own reader.
Its first version wrote the tag of a sequence item as one 32-bit integer, so the bytes came out
`00 E0 FE FF` instead of `FE FF 00 E0`. pydicom read the file without a warning; the export's
strict reader refused it at once. An independent reader is lenient by design: it accepts what
real-world files contain, which is not always what the standard says. Independence finds
disagreements, not every violation, and the strict reader stays (section 7). A validator of the
IOD, such as D. Clunie's dciodvfy, checks still more; the export does not run one, and a product
would.

The second came from the lock file's audit (Chapter 31's `tools/lock_audit.py`). The first pin,
pydicom 3.0.1, had a published vulnerability on the day it was added, a path traversal through a
crafted DICOMDIR (CVE-2026-32711, listed under two advisory identifiers). The tests do not read
DICOMDIRs, and the audit refused the pin anyway: 3.0.2, which fixes it, is the one in the lock file.
A test-only dependency is still code that runs on the developers' machines and in CI with their
rights.

The independent checks have a limit worth stating plainly: two implementations that agree are
evidence that both read the standard the same way, not that the archive at your hospital will. A
scanner's export is tested against the archives and viewers it will meet, at IHE connectathons and
at the first sites, and its conformance statement says what was tested.

::: box-mistakes
- **Truncating a value to fit.** A shortened ID or accession number is another one; refuse it.
- **Six decimals for a slope.** A small slope becomes zero; write the most digits that fit in 16
  characters, and compute with the slope as written.
- **One slope for a volume.** Cold slices lose an order of magnitude of precision.
- **Unsigned pixels for an image with negative values.** They wrap into hot spots.
- **Rows bottom up with an orientation that says top down.** The image is mirrored in the patient
  and still looks plausible.
- **Testing geometry with a centered object and square pixels.** Both hide the mistakes that
  matter; use an off-axis point, non-square pixels and every supported position.
- **A time without its time zone.** Decay correction and the order of series depend on it.
- **Random UIDs on every send.** A resend becomes a second series.
- **Treating "the association closed" as "stored".** Only the archive's status for each instance
  says that; keep everything else.
- **Trusting one reader.** Your reader and an independent one, and still a validator.
:::

## What this leaves out

The export is the smallest useful one. A scanner's export adds the Enhanced PET IOD (multi-frame
objects with floating-point pixels), compressed transfer syntaxes, dynamic and gated series,
standardized uptake values and the dose calibration they need, the modality worklist and modality
performed procedure step services that bring the order and report the exam's progress, storage
commitment, query and retrieve, DICOM over TLS (part 15), de-identification for research and
service (the confidentiality profiles of part 15), raw data and list mode stored as DICOM objects
(often private), and a conformance statement. Each is a chapter in other books; O. Pianykh's
practical introduction is a good start, and the standard itself is more readable than its size
suggests.

::: box-regulated
- **Classification.** In a scanner the export is software of the medical device. A series filed
  under the wrong patient is a serious hazard (H-15, preliminary hazard HZ-5), which makes the
  item class C under IEC 62304 unless a control outside the software is credited, such as the
  archive's reconciliation of unmatched studies (assumption: confirm with team and Chapter 14's
  rules).
- **Risk controls.** H-15 to H-17 with RC-47 to RC-51: identifiers from the order only, UIDs
  derived from the content, values within half a slope, every pixel in its place for each
  supported position, and an outbox that keeps every instance until the archive has stored it.
- **Interfaces and conformance.** The DICOM conformance statement (part 2) is part of the
  product's documentation; the SOP classes and syntaxes it lists are the export's interface
  requirements.
- **Personal data and cybersecurity.** The export carries the patient's identity; MiniDAQ's own
  data does not. The threat model records the export as a gap (version 10): plain TCP, an archive
  identified only by its address and AE title, an outbox in its user's files. A product needs its
  own threat model and, under IEC 81001-5-1 and the security guidance of its markets, a reason for
  each of those choices.
- **SOUP and tools.** pydicom and pynetdicom are test tools (TL-45), pinned and audited; a product
  that used a DICOM toolkit in its export would list it as SOUP with its anomaly list.
- **Records.** CR-0022, ADR 0030, TL-44 and TL-45, SRS version 24 (SRS-DCM-001 to SRS-DCM-007),
  the risk file (H-15 to H-17), the threat model version 10, the SOUP list version 19,
  `measurements/ch35/`.
:::

::: box-askteam
1. Which DICOM objects does our scanner send, to which archives, and where is our conformance
   statement? When was it last compared with the code?
2. Where do the patient and study identifiers come from: the worklist, the operator, both? What
   happens when they disagree?
3. How are our UIDs made, and what happens to them when a series is sent again or reconstructed
   again?
4. What does the console do when the archive is down? Where are the unsent images, and who sees
   that they are waiting?
5. Do we use storage commitment before deleting local copies?
6. Which archives and viewers have we tested against, and which are we told the sites use?
7. Who decides the units, the corrections listed and the decay correction reference, and where is
   that recorded?
8. Is DICOM sent over TLS at our sites, and who manages the certificates?
:::

## Exercises {.unnumbered}

**Exercise 35.1 (E): A number a reader gets back.** *Goal:* write a slice's rescale slope as a
Decimal String and store its values so that a reader gets each back within half a slope.
*Starter:* `exercises/ch35/e1_decimal_string/starter/ds.py`, which writes six decimals and divides
by the slope it computed. *Acceptance:* `tests/test_ds.py` passes: every DS at most 16 characters
and within 5e-10 of its value, a slope of 1.4e-7 not zero, NaN and infinity refused; every stored
value times the written slope within half of it; an empty plane with a slope of 1. *Time:* 1
hour.

**Exercise 35.2 (M): Where is this pixel in the patient?** *Goal:* compute Image Position,
Image Orientation and Pixel Spacing for an exported slice, for head first and feet first.
*Starter:* `exercises/ch35/e2_image_plane/starter/plane.py`, which does not flip the rows, writes
Pixel Spacing in the wrong order and treats every position as head first. *Acceptance:*
`tests/test_plane.py` passes: an off-axis pixel at its LPS position for HFS and FFS with square and
non-square pixels; row spacing first; two perpendicular unit vectors with the columns to the back;
an unknown position refused. *Time:* 2 hours.

**Exercise 35.3 (H): Messages out of fragments.** *Goal:* reassemble DIMSE messages from P-DATA-TF
PDUs, as an archive does. *Starter:* `exercises/ch35/e3_pdata/starter/pdata.py`, which reads one
PDV per PDU and takes every fragment as complete. *Acceptance:* `tests/test_pdata.py` passes: a
message in one PDU, a data set across many, a command in two fragments, several PDVs in one PDU,
an echo then a store; a wrong PDU type, a PDV that does not fit, another context, fragments out of
order and input that ends mid-message all refused. *Time:* 3 hours.

## MiniDAQ milestone: the image reaches the archive {.unnumbered}

::: box-milestone
**Goal.** The phantom image of Chapter 33 leaves as a DICOM series that an independent reader
reads value for value, reaches an archive through an outbox that survives an abort, and cannot be
filed under a patient or study the order did not name. **Start:** tag `ch34`. **End:** tag `ch35`.
:::

1. Write change request CR-0022 and ADR 0030; add SRS-DCM-001 to SRS-DCM-007 (SRS version 24),
   H-15 to H-17 with RC-47 to RC-51 and the preliminary hazard HZ-5, TL-44 and TL-45; review the
   threat model (version 10) and the SOUP list (version 19).
2. Add `tools/dicom`, `tools/pacs.py`, their tests and the test `tools.dicom`; pin pydicom and
   pynetdicom in the lock file and require them in CI's job python.
3. Export and send the phantom image; keep the measurements in `measurements/ch35/`.
4. Add Exercises 35.1 to 35.3.

**Definition of done.** `tools.dicom` passes with its independent checks, and fails if
`MINIDAQ_DICOM_ORACLE_REQUIRED=1` and they cannot run; `docs.trace`, `docs.risk`, `docs.baseline`
(the seven requirements named by CR-0022) and the lock audit pass; every starter of the chapter
fails. Tag `ch35`.

## Check yourself {.unnumbered}

1. What is the difference between an IOD, a module, a SOP class and a transfer syntax?
2. Which VRs get a 4-byte length in Explicit VR Little Endian, and why does Implicit VR need a
   dictionary to be read?
3. Why does the writer refuse a value that is too long instead of truncating it?
4. What does a DS hold, and why compute the stored values with the slope as written?
5. Why a slope per slice? What did one slope for the volume cost on the measurement's volume?
6. What are types 1, 2 and 3 of an attribute? Give an example of each from the PET Image object.
7. How does a gantry position become a patient position for HFS and FFS, and why are the rows
   written top down?
8. Which test data hide geometry defects, and which expose them?
9. Why does the export derive its UIDs from the content? What would random UIDs do in the day in
   the life?
10. What is a presentation context, and what does the archive's maximum PDU length limit?
11. Which C-STORE statuses take an instance out of the outbox, which keep it, and which set it
    apart?
12. What did TCP_NODELAY change, and why?
13. What can a test against pydicom and pynetdicom show, and what can it not?
14. What would make the export class C in a scanner, and what could keep it class B?

## Summary {.unnumbered}

- DICOM defines information objects, their encoding, the services that move them, the file format
  and the network protocol; a scanner's export stores a series in the hospital's archive with
  C-STORE, and its conformance statement says what it supports.
- A data element is a tag, a VR, a length and a value; values have even lengths, elements ascend,
  and a value that breaks its VR is refused, never truncated.
- The PET Image object needs fourteen mandatory modules; units, corrections, decay correction,
  frame reference time, the radiopharmaceutical and the time zone carry the image's meaning.
- Each slice is stored as 16-bit integers with its own slope, an intercept of zero, signed when
  needed, computed with the slope as written: every value comes back within half a slope.
- Image Position, Image Orientation and Pixel Spacing place every pixel in the patient; the
  mapping from the gantry depends on the patient's position, and only off-axis, non-square test
  data shows it is right.
- Patient and study identifiers come from the order unchanged; UIDs derived from the content make a
  resend the same series and a new reconstruction a new one.
- Associations negotiate presentation contexts and a maximum PDU length; messages travel as
  fragments; only the archive's status for each instance says it is stored.
- An outbox keeps every instance until then, journals every attempt and sends only what is
  pending; an abort after 20 of 47 instances and a second export left the archive with 47.
- Independent implementations find disagreements, not every violation: pydicom read a misencoded
  item that the strict reader refused, and the lock audit replaced a pin with an advisory.

## Further reading {.unnumbered}

- NEMA, *Digital Imaging and Communications in Medicine (DICOM)*, PS3.1 to PS3.22, current
  edition, https://www.dicomstandard.org: parts 3 (the PET Image IOD, section A.21, and the PET
  modules, C.8.9), 5 (data structures and encoding), 6 (the data dictionary), 7 (message
  exchange), 8 (network communication) and 10 (the file format); part 2 on conformance statements
  and part 15 on security profiles.
- O. S. Pianykh, *Digital Imaging and Communications in Medicine (DICOM): A Practical
  Introduction and Survival Guide*, 2nd edition, Springer, 2012.
- IHE International, *IHE Radiology Technical Framework*, volume 1, the Scheduled Workflow
  profile, https://www.ihe.net.
- ITU-T Recommendation X.667, on UUIDs and their use as object identifiers under 2.25.
- J. Nagle, RFC 896, "Congestion Control in IP/TCP Internetworks", 1984; R. Braden (ed.), RFC
  1122, "Requirements for Internet Hosts: Communication Layers", 1989, on delayed acknowledgments.
- The pydicom and pynetdicom documentation, https://pydicom.github.io.
- IEC 81001-5-1:2021, *Health software and health IT systems safety, effectiveness and security:
  activities in the product life cycle*.
- ADR 0030 and CR-0022 in the repository; `measurements/ch35/README.md`.
