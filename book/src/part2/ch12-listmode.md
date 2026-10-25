# List-mode data, sinograms and data management {#ch12}

::: box-why
Everything the DAQ does ends in a file. Reconstruction reads that file to make images,
calibration reads it to tune the detector, and the analysis framework reads it years later
to answer questions nobody asked at the time of the scan. A coincidence that is lost,
silently corrupted or stored without the settings that produced it cannot be recovered
by any later step. The file format and the code that writes it are therefore part of the
measurement, not plumbing. This chapter designs MiniDAQ's list-mode format, histograms it
into sinograms with the scanner's geometry, compares it with HDF5, Interfile and the formats
of reconstruction packages, and makes the writer fast and crash-safe. It ends at the
boundary where raw data meets patient data and DICOM.
:::

**A day in the life.** On Monday morning the physicist finds the acquisition PC
rebooted. During the weekend's twelve-hour decay test the building's power failed for a few
seconds, and the UPS did not hold the PC. Two questions arrive with the coffee. Is anything
left of the run? And can the first hour be split into one-minute frames for the dead-time
analysis? You open the data directory. Thirty-one segments end in `.mdql`; one ends in
`.mdql.part`, and there is no run record. You run the recovery tool. It finds that every
complete segment is intact, cuts the partial segment after its last good block, closes it
and renames it. It reports that the run ended in a crash, so its counters are in the DAQ's
log, not next to the data. The frames are the easy part. The data are in list mode, one
record per coincidence with its time, so a histogrammer can bin any minute of the run into
its own sinogram. Had the DAQ stored only one sinogram per run, the first hour could not be
split at all. By ten o'clock the physicist has the frames and you have a bug report about
the UPS. The lesson of this chapter: design the file for the day the power fails and for the
question nobody has asked yet.

## Learning objectives {.unnumbered}

After this chapter you can:

1. Design a compact, versioned list-mode format: choose the fields and their bit widths,
   protect headers and blocks with checksums, and write the rules that let the format grow
   without breaking old readers.
2. Convert list-mode data into sinograms with the scanner's geometry, including the
   Michelogram, single-slice rebinning (SSRB) and time-of-flight (TOF) bins, and explain
   what a sinogram throws away.
3. Compare custom binary files, HDF5, Interfile and the conventions of STIR and CASToR for
   storing PET data and its metadata, and justify a choice in an architecture decision.
4. Make a writer sustain the sorter's output rate on a real disk with a documented fsync
   policy, survive a crash with at most a stated loss, and recover after one.
5. Explain the DICOM objects of PET and where raw data and patient identity sit relative to
   them.

## Prerequisites and estimated time {.unnumbered}

Chapter 3 (the pipeline and its writer stage), Chapter 8 (lines of response, trues and
randoms), Chapter 10 (the sorter and its delayed window) and Chapter 11 (the throughput
budget). Exercise 12.2 and the figures use Python with matplotlib. Reading: about 3 hours.
Exercises: 15 hours. Milestone: 5 hours. In the 10-week schedule this chapter fills the first
half of week 5.

## Designing a list-mode record

### What a record must hold

A *list-mode* file stores every coincidence as it was detected, in time order. It is the
opposite of a histogram, which only stores how many events fell into each bin. A record
must hold what any later step might need about one event and nothing it can recompute.
For a coincidence that means:

- **When.** The time of the earlier single, so that frames, gates and decay correction can
  be applied later.
- **Where.** The two crystals, which fix the line of response (LOR).
- **The time difference.** The arrival times of the two photons differ by the time of
  flight, which localizes the annihilation along the LOR (Chapter 8).
- **The energies.** Scatter estimation and a later change of the energy window need them,
  and calibration (Chapter 26) is built on them.
- **The kind.** A prompt or a delayed coincidence (Chapter 10). The delayeds estimate the
  randoms and must never be counted as prompts.

A list-mode file also needs records that are not coincidences: *tags*. A physiological
gate (an ECG R wave, a respiratory phase) and a periodic time mark from the acquisition
clock are events in time, and the simplest place for them is the same stream, in time
order, so that a reader meets them where they happened.

What a record does not need is anything the acquisition's configuration already says. The
coincidence window, the energy window, the delay and the geometry are the same for every
event of a run. They belong in a header, written once.

### Bit widths

Each field gets the smallest width that cannot overflow in any acquisition the format must
hold. MiniDAQ's record, MDQ-L1, is 16 bytes:

| Bytes | Field | Width | Range and resolution |
|---|---|---|---|
| 0–3 | time offset | u32 ps | 4.29 ms after the block's base time |
| 4–5 | crystal a | 15 bits + delayed flag | 32,767 crystals |
| 6–7 | crystal b | u16 | 32,767 crystals |
| 8–11 | dt | i32 ps | ±2.1 ms |
| 12–13 | energy a | u16, 1/32 keV | 0 to 2047.97 keV |
| 14–15 | energy b | u16, 1/32 keV | 0 to 2047.97 keV |

Every width is a decision with an argument:

- **Time.** An absolute time in picoseconds needs 64 bits: 2^32^ ps is only 4.29 ms, and a
  run is hours long. Storing 64 bits in every record would cost 4 bytes more per event, a
  quarter of the record. Instead the time is split. Each block of records carries a 64-bit
  base time, and each record stores a 32-bit offset from it. A block closes when the next
  offset would not fit, so the price is one block header every 4.29 ms at low rates.
- **Crystals.** MiniDAQ's scanner has 384 × 48 = 18,432 crystals (Chapter 8). Fifteen bits
  hold 32,767, so the sixteenth bit of the first crystal field is free for the delayed flag,
  and the value 0x7FFF marks a tag. A scanner with more than 32,767 crystals needs a new
  major version of the format.
- **Time difference.** A signed 32-bit difference covers ±2.1 ms. The coincidence window is
  a few nanoseconds, and a delayed pair's difference includes the 100 ns delay. Sixteen
  bits (±32.8 ns) would almost do for this scanner, and would not survive a longer delay.
- **Energy.** A unit of 1/32 keV is far finer than the detector's energy resolution, 12% FWHM
  at 511 keV in MiniDAQ's simulator (Chapter 8), so quantization costs nothing measurable. Sixteen
  bits reach 2047.97 keV. The writer clamps anything outside and counts each clamp.

Sixteen bytes is also a power of two, so a record's offset is a shift, and a block of 4,096
records is exactly 64 KiB of payload.

### Blocks, headers and versions

A file is a header followed by blocks:

```
file header | block 0 | block 1 | ... | closing block
```

The **file header** starts with an 8-byte magic, `MDQL\r\n\x1a\n`. Like PNG's signature it
contains a carriage return, a line feed and the DOS end-of-file character, so a transfer that
translates line endings or stops at end-of-text damages it visibly. Then come the major and
minor version, the header's size, the size of the JSON metadata, the record size (16) and
reserved fields, the metadata itself, and a CRC-32 over everything before it.

Each **block** has a 32-byte header: the magic `MDQB`, a sequence number that starts at 0 in
every file, the record count, flags, the 64-bit base time, a CRC-32 of the records and a
CRC-32 of the block header itself. A file ends with an empty *closing block*. Its flags say
whether the run ends here or continues in the next file, so a reader can tell a complete
file from a truncated one without trusting its name.

The constants are in one place in the code:

```{.cpp include="minidaq/include/minidaq/format/list_mode.hpp" snippet="constants"}
```

A **version** is a promise about which readers can read a file. MDQ-L1 has two numbers. A
change that an old reader can safely ignore, such as a new metadata member or a new tag
kind, raises the minor version, and every 1.x reader reads every 1.y file. Any other
change raises the major version, and a reader must refuse a major version it does not know.
The order in which a reader checks the header follows from that promise:

```{.cpp include="minidaq/src/format/list_mode.cpp" snippet="parse_header"}
```

The version comes before the sizes, because a later major version may put them elsewhere.
The CRC comes before the remaining fields, so that a damaged header is reported as damaged
rather than as a strange value. And no step reads past the end of the data, which the
fuzz target `fuzz_listmode` checks on arbitrary input.

The complete specification, with the rules for writers and readers, is
`docs/formats/mdq-l1.md`. It is written so that a reader can be built from it alone. Two
independent implementations exist to prove that: a Python reader in
`measurements/ch12/crash.py`, and a Python writer that produced the test file
`fuzz/corpus/listmode/three_blocks.mdql`, which the C++ reader must read (SRS-LMF-008).

### Tags: gates and time marks

A tag is a record whose first crystal is 0x7FFF. Its second crystal field holds the tag's
kind, and its time difference field holds a value. Kind 1 is a physiological *gate* (the
value is the gate channel), and kind 2 is a *time mark* from the acquisition clock (the value
is its index). Kinds up to 1023 are reserved for this specification, and kinds from 1024
are free for site-specific use. A reader skips a kind it does not know, which is what lets a
minor version add kinds.

Gating is the reason tags live in the record stream rather than in a separate file. To
reconstruct the end-diastolic phase of a cardiac scan, the histogrammer needs, for each
coincidence, the time since the last R wave. Walking one time-ordered stream gives that
directly. Two files would have to be merged first, and every reader would have to merge them
the same way.

### Writing a block

The writer fills a block in a buffer that the sink owns, so each record is written once,
where the I/O thread will read it. Before each record it decides whether the record still
belongs in this block:

```{.cpp include="minidaq/src/format/list_mode.cpp" snippet="place"}
```

A block closes for three reasons. It is full. The next record is more than 2^32^ − 1 ps after
the block's base time. Or the next record is *earlier* than the previous one. The last case
is a time reset: a clock restart in the electronics, which the sorter of Chapter 10 would
already have reported. The format does not hide it. A reset shows as a block whose base time
is earlier than the last record of the block before it.

### A worked example: how much data?

The water cylinder of `measurements/ch12/sinogram.txt` (a uniform 80 mm cylinder of activity
in a 100 mm water phantom, 20 MBq) produced 470,024 prompts and 51,821 delayeds in 2 s:
261,000 records per second. At 16 bytes per record that is 4.2 MB/s, or 2.5 GB for a
ten-minute scan. The file of the 2 s run is 8,365,856 bytes. The records account for
8,349,520 of them, so headers and block headers cost 0.2%. At this rate a block closes on the
4.29 ms time limit with about 1,100 records, not on the 4,096-record limit. Higher rates
close blocks on the record count instead.

At its own limit of 70 M singles per second, the sorter of Chapter 10 produces about
2.7 M coincidences per second (0.039 coincidences per single in `bm_sorter`). That is
43 MB/s, the rate the writer must sustain with a margin. Exercise 11.5 assumed 16 bytes per
coincidence and a writer of 5 M per second. The record size is now confirmed, and the
writer's measured rate appears later in this chapter.

::: box-mistakes
- **64-bit absolute times in every record.** They cost a quarter of the file. A base time
  per block and 32-bit offsets give the same precision.
- **A format without a version.** The first change becomes a guessing game for every reader.
  Put the version first and say what each kind of change does to it.
- **Settings in the file name or a separate text file.** They get separated from the data.
  Put the whole effective configuration in the header.
- **Bit fields from a C++ struct written with `write()`.** Their layout, padding and byte
  order belong to one compiler on one machine. Write each field at a fixed offset, little
  endian, with explicit loads and stores (`minidaq/core/byte_io.hpp`).
- **One checksum for the whole file.** It tells you the file is damaged but not where, and
  it can only be checked once the file is complete. One CRC per block localizes damage to 64
  KiB and can be checked as the data stream in.
- **Delayed coincidences mixed with prompts and no flag.** The randoms estimate is lost, and
  every prompt sinogram is wrong by the randoms rate.
:::

## From lines of response to sinograms

### Lines of response and the sinogram

Every coincidence defines a line between two crystals, its line of response. In one ring of
N crystals there are N(N − 1)/2 such lines: 73,536 for N = 384. A *sinogram* sorts them by two
coordinates: the angle θ of the line's normal and its signed distance s from the scanner's
axis. A point source at (x~0~, y~0~) lies on all lines for which

s(θ) = x~0~ cos θ + y~0~ sin θ,

a sinusoid whose amplitude is the source's distance from the axis and whose phase is its
direction. That curve gives the sinogram its name. An object is a sum of points, so its
sinogram is a sum of sinusoids, and reconstruction (Chapter 28) inverts that sum. In
mathematical terms the sinogram is a sampled Radon transform of the activity, attenuated
and blurred by the detector.

### Indexing a ring

For crystals i < j on a ring, crystal k sitting at the angle (k + 0.5) · 2π/N, the line's
normal points at the angle (i + j + 1) π/N. Its distance from the axis depends only on the
difference j − i. Two integers therefore index a line: k = i + j + 1, twice the angle in
units of π/N, and d = j − i. A sinogram covers 180 degrees of angles, because a line seen
from the other side is the same line. When k ≥ N the angle is past 180 degrees, so the line
is folded back: its angle drops by 180 degrees (k − N) and its signed distance changes sign
(d becomes N − d). MiniDAQ's `lor_bin` does exactly that:

```{.cpp include="minidaq/include/minidaq/processing/sinogram.hpp" snippet="lorbin"}
```

Each view holds two adjacent angles, so there are N/2 = 192 views, and the radial index is
r = d − 192. Take crystals 200 and 383. Then k = 584, past 180 degrees, so k becomes 200 and
d = 183 becomes 384 − 183 = 201: view 100, r = 9. The test `EveryTransaxialLorHasItsOwnBin`
checks that all 73,536 lines of a ring land in 73,536 different bins (SRS-SNO-001).

The radial positions of the bins are not evenly spaced. A line with radial index r lies at
s = −R sin(πr/N) from the axis, where R = 150 mm is the ring's radius. Near the center the
spacing is πR/N = 1.23 mm; at r = 113 it has shrunk to 0.74 mm, and the line lies at
119.7 mm. Treating the bins as evenly spaced would put that line at 138.7 mm, 19 mm too far
out. Reconstruction either uses the true positions or resamples the sinogram to even
spacing, which is called *arc correction*. MiniDAQ's histogrammer writes the formula into the
sinogram's header and does not resample. It keeps bins up to the radius of the sorter's
field-of-view cut, 120 mm, which gives 2 × 113 + 1 = 227 radial bins.

### Michelograms, span and SSRB

A scanner has many rings: 48 in MiniDAQ, 2.45 mm apart. A coincidence between ring a and ring
b is an oblique line unless a = b. The *Michelogram* is a 48 × 48 table of counts by ring pair,
with ring a on one axis and ring b on the other. The diagonal holds the direct planes. A
fully 3D sinogram keeps every ring pair: 2,304 sinograms of 192 × 227 bins, 402 MB at 4 bytes
per bin.

Most reconstructions combine ring pairs to save memory and time. *Span* is the conventional
way to say how much. Neighboring ring differences are grouped into *segments*, and within a
segment ring pairs with the same a + b go into the same sinogram. Span 1 keeps every pair,
and larger spans group more ring differences per segment. A *maximum ring difference* drops
lines that are too oblique. The extreme is *single-slice rebinning* (SSRB): every line goes to
the direct plane halfway between its rings, slice a + b, so 48 rings give 95 slices 1.225 mm
apart. SSRB ignores the obliqueness of the line, which blurs the axial position the farther
the source is from the axis (verify: SSRB's axial error grows with radial distance and ring
difference; Daube-Witherspoon and Muehllehner, 1987). Better rebinning algorithms, such as
Fourier rebinning, belong to reconstruction (Chapter 28).

MiniDAQ's histogrammer does SSRB with a configurable maximum ring difference. It keeps the
full Michelogram as a separate table, counted before the ring-difference cut, so that a
reader can see what the cut removed.

### Time of flight

With a coincidence time resolution (CTR) of a few hundred picoseconds, the difference in
arrival times locates the annihilation along the line. With τ = t~a~ − t~b~, the annihilation
lies c|τ|/2 from the line's midpoint, toward the endpoint whose photon arrived first.
With c = 0.3 mm/ps, 1 ps of τ is 0.15 mm, and MiniDAQ's simulated CTR of 300 ps FWHM is a
45 mm uncertainty (Chapter 8). A TOF sinogram adds a third index, the TOF bin of τ.

Two details decide whether a TOF sinogram is right. First, the sign of τ depends on which end
of the line is a. That is fixed by the sinogram's convention, not by the order of the record:
when `lor_bin` folds a line past 180 degrees it swaps the ends, and `a_is_lower` tells the
histogrammer so. Second, a delayed pair's time difference includes the delay, which must be
removed before binning:

```{.cpp include="minidaq/src/processing/sinogram.cpp" snippet="locate"}
```

The bins have a configurable width and are centered on τ = 0: bin = ⌊(2τ + n·w) / 2w⌋ for n
bins of width w. The test `TimeOfFlightBinsLocateTheAnnihilationAlongTheLor` places annihilations
at random points along random lines and checks that each lands in the bin of its position
(SRS-SNO-004).

### A point source and a cylinder

Figure 12.1 shows two sinograms that MiniDAQ produced end to end: `minidaq_sim --listmode`
wrote list-mode files, and `minidaq_listmode sino` histogrammed them. The point source at
(40, −25) mm draws one sinusoid with an amplitude of 47 mm. The cylinder fills a band whose
width is its diameter, with a background of scattered and random coincidences outside it.
Its Michelogram is darker in two corners: the source is 100 mm long and the scanner 118 mm,
so the direct planes of the end rings see no activity, while the oblique lines between the
two ends cross the middle of the cylinder.

![Sinograms histogrammed from MiniDAQ list-mode files (`measurements/ch12/sinogram.py`). Left:
1 s of a 2 MBq point source at (40, −25) mm in air, one sinusoid. Middle: 2 s of 20 MBq in a
uniform cylinder of radius 80 mm inside a water cylinder of radius 100 mm. The radial axis is
labeled in millimeters because the bins are not evenly spaced. Right: the cylinder's
Michelogram, prompts by the rings of the two crystals, on a log scale.](src/img/ch12-sinogram.png){width=100%}

Fitting the sinusoid of a point source gives back its position, and that is how MiniDAQ found
a bias in its own geometry. A point at 100 mm comes back at 96.6 mm, and points at 20, 47 and
80 mm come back about 3.6% closer to the axis, too (Exercise 12.2). A shift would be the same
at every radius; this is a scale. The histogrammer places lines between the crystals' front
faces, at R = 150 mm. The simulator, however, records each photon at the depth in the crystal
where it interacted, 5.9 mm deep on average, which makes the effective radius about 156 mm.
Real scanners have the same effect, and their geometry files give an effective radius that
includes the mean depth of interaction (assumption: confirm with team what radius the
NeuroLF's reconstruction uses). MiniDAQ keeps the front-face radius and records it in the
sinogram's header. That makes the bias visible rather than hidden, and Exercise 12.2 asks you
to quantify it.

### Why keep list mode at all?

A sinogram has a fixed size. MiniDAQ's SSRB sinogram is 95 × 192 × 227 bins of 4 bytes,
16.6 MB, whatever the number of counts. List mode grows by 16 bytes per event, so it is larger
once a run has more than about a million coincidences, which takes the cylinder four seconds.
A ten-minute scan is 2.5 GB in list mode and still 16.6 MB as a sinogram. Why keep the large
form?

Because a sinogram has thrown away what nobody knew they would need:

- **Time.** Dynamic studies split a run into frames chosen after the scan. Kinetic modeling
  needs short frames early and long ones later. Motion correction needs to know when the
  patient moved.
- **Gates.** Cardiac and respiratory gating sort events by phase, which only the event times
  and the tags can give.
- **Energies and TOF.** A different energy window, a scatter estimate that uses energies, or a
  finer TOF binning all need the event-level values.
- **Corrections and calibrations that change.** A crystal map or timing calibration found
  wrong last month can be reapplied to list-mode data, not to a sinogram made with it.
- **Reconstruction from list mode.** Some reconstructions work event by event, with the exact
  crystal positions and TOF value of each event (Chapter 29).

A sinogram is a *product*, made for one reconstruction with one set of choices. List mode is
the *measurement*. A DAQ keeps the measurement, and the analysis decides how long.

::: box-mistakes
- **The view folded at 180 degrees without flipping the sign of s.** Half the lines land on
  their mirror image. The test that every line of a ring has its own bin catches it at once.
- **Radial bins treated as evenly spaced.** Images are stretched near the edge of the field
  of view. Write the positions or arc-correct, and say which in the header.
- **Delayed coincidences in the prompt sinogram.** The randoms are counted twice, once as
  data and once by the correction (Chapter 27). Bin them apart.
- **TOF bins computed from the record's order.** The sign of τ depends on the sinogram's
  endpoint convention, which changes when a line is folded.
- **A sinogram without its binning written down.** Span, maximum ring difference, arc
  correction, TOF bin width and the radius used are part of the data.
:::

### MiniDAQ's histogrammer

`processing::Histogrammer` bins coincidences into prompt and delayed SSRB sinograms, with
optional TOF bins, and counts what it could not bin: lines outside the field of view, beyond
the maximum ring difference, outside the TOF range, or with no angle (two crystals in the
same transaxial position). The core library does no I/O. `minidaq_listmode sino` reads the
files, fills the histogrammer and writes the sinograms as raw little-endian arrays with an
Interfile-style text header, which says what each axis means, which radius was used, and how
many events each cut removed. The header's keys follow the Interfile style, but they are
MiniDAQ's own: STIR and CASToR each define their own keys for the same information, and a
converter, not the DAQ, speaks their dialect. On the book's VM the histogrammer bins 37 M
coincidences per second on one core (`measurements/ch12/bm_listmode.txt`).

## File formats for PET data

### A custom binary format

A format of one's own is fastest to write and easiest to make crash-safe, because every
byte's purpose is known. It is also a commitment. Somebody must document it, version it,
test it, write a reader for every language that will use it, and keep all of that working
for as long as data in it exists. MDQ-L1 is such a format, with its specification, two
independent readers and a fuzz target. That is the minimum for a custom format.

### HDF5

HDF5 is a container for scientific data: a file holds *groups* (like directories),
*datasets* (typed n-dimensional arrays) and *attributes* (small named values attached to
either). A dataset can be *chunked* and *extendable*, so it can grow as data arrive, and
filters can compress each chunk. Python reads it with h5py, and MATLAB, ROOT and many
analysis tools read it too. For PET it is attractive for exactly what list mode lacks:
self-description. A file can hold the events as a compound dataset, the configuration as
attributes, and calibration tables as their own datasets, and a reader discovers all of it.

For the DAQ's raw stream, three properties need care. First, crash behavior. An HDF5 file
whose writer dies with its metadata cache unflushed may be unreadable. The library's
single-writer multiple-reader (SWMR) mode, available since version 1.10, is designed to keep
the file readable while it is written (verify: the crash guarantees of the version and
settings you would ship). Second, throughput depends on the chunk size, the compression and
the library's caches, and must be measured on the acquisition disk. Third, it is a large
library, which makes it SOUP under IEC 62304 (Chapter 14), with its own list of known
anomalies to evaluate. Many systems therefore write raw data in a simple format and convert
to HDF5 for analysis. That is MiniDAQ's position too.

### Interfile

Interfile is a convention from nuclear medicine for describing a raw binary array with a text
header of `key := value` lines, beginning with `!INTERFILE :=` (Todd-Pokropek and others,
1992). It says how to read the numbers: their type, byte order, dimensions and spacing. It
does not prescribe one meaning for PET projection data, so every package that uses it adds
keys of its own. STIR, for example, describes its projection data in Interfile headers with
its own keys for segments, views and TOF. Interfile is a good way to make a sinogram or an
image readable by a human and by a tool. MiniDAQ uses its style for the sinogram headers.

### The conventions of reconstruction packages

Two open-source packages define much of what reconstruction expects to read:

- **STIR** (Software for Tomographic Image Reconstruction) reads projection data with
  Interfile headers and list-mode data in several scanner-specific formats. Its scanner
  description (rings, crystals per ring, radius, depth of interaction) is the geometry a
  converter must match.
- **CASToR** (Customizable and Advanced Software for Tomographic Reconstruction) reads data
  files with a text header (`.cdh`) and binary events (`.cdf`), in list-mode or histogram
  form, and describes the scanner in a geometry file or a lookup table of crystal positions.
  Its list-mode events carry their time in milliseconds and a pair of crystal indices,
  optionally with correction factors and a TOF value (verify: against the current CASToR user
  guide).

A third effort is a standard rather than a package: PETSIRD, a PET raw data format from the
Emission Tomography Standardization Initiative, which defines list-mode events and scanner
geometry once for all tools (verify: its current version and status before relying on it).
A DAQ that writes its own format and converts to these keeps its acquisition path stable
while the conventions evolve. A DAQ that writes one of them directly saves the converter but
inherits every field the convention fixes. CASToR's millisecond times, for example, would lose
the picosecond timing, and none of these conventions carries the acquisition's configuration
as MiniDAQ needs it.

### What MiniDAQ chose

ADR 0012 records the decision. MiniDAQ writes MDQ-L1, and converters produce everything else:
the sinograms of `minidaq_listmode sino` today, and HDF5, STIR or PETSIRD files when a consumer
needs them. It supersedes ADR 0007, which deferred the choice until this chapter could measure
it. The record lists what the choice costs. The format is MiniDAQ's to maintain. Its CRC
protects against accidents, not tampering. And its writer's durability depends on an fsync
policy that the site must choose.

## Data integrity and crash safety

### What can go wrong

Between the sorter and a file that a physicist opens months later, the data can be damaged in
many ways:

- **Bit flips.** In RAM, in the disk's electronics, on the medium, in a network copy. Rare per
  bit and certain over petabytes.
- **Torn writes.** A crash or a fatal signal ends a write part of the way through. The file
  ends in half a block.
- **Lost writes.** A power loss discards data that the operating system had accepted but not
  yet written. The page cache can hold gigabytes.
- **Lies about durability.** A disk with a volatile write cache that does not honor flush
  requests, or a virtual disk that a host caches. The software did everything right and the
  data still vanish (verify: the acquisition disk's write-cache behavior with its vendor).
- **A full disk.** The write fails at hour three of a four-hour run.
- **Lost errors.** On Linux, a failed write-back is reported to the next fsync. In 2018 the
  PostgreSQL developers found that after such a failure the kernel could mark the pages clean,
  so a second fsync reported success although the data were never written. PostgreSQL now
  treats a failed fsync as fatal. The lesson applies to any writer: an fsync error is a fault,
  never something to retry.

Each failure needs a different defense. CRCs detect bit flips and torn writes. Durable
ordering limits what a power loss takes. Faults stop a run that cannot store its data, and
the record of the run says what happened.

### CRC-32

A cyclic redundancy check treats the data as a polynomial over GF(2) and stores the remainder
of its division by a fixed generator polynomial. MDQ-L1 uses the CRC-32 of Ethernet, zlib and
PNG: generator 0x04C11DB7, bits processed least significant first (so the code uses the
reversed constant 0xEDB88320), initial value and final XOR 0xFFFFFFFF. The CRC of the bytes
`123456789` is 0xCBF43926, the check value that every implementation of this CRC must
reproduce and the first test MiniDAQ's must pass (SRS-LMF-001).

What it detects is a theorem, not a hope. Every burst of up to 32 bits changes the CRC, and so
does every error of one or two bits in messages up to about 2^32^ bits. Every error of three
bits is detected only in messages up to 91,607 bits, so a 64 KiB block keeps the two-bit
guarantee but not the three-bit one (Koopman, 2002). Any other damage gets through with a
probability of about 2^−32^. Exercise 12.4 checks these properties with the CRC's linearity,
without trying every error pattern.

A CRC is computed byte by byte with one table of 256 entries, or eight bytes at a time with
eight tables, a method called *slicing-by-8*:

```{.cpp include="minidaq/src/core/crc32.cpp" snippet="update"}
```

On the book's VM the byte-at-a-time loop runs at 364 MiB/s and slicing-by-8 at 2.07 GiB/s, 5.8
times faster (`measurements/ch12/bm_listmode.txt`). At that speed the CRCs cost about 7 ns of
the 20 ns that encoding a record takes. Encoding with both CRCs runs at 49 M records per
second, and reading with both checks and decoding at 81 M per second, so integrity is cheap
enough to keep everywhere.

### Detecting and surviving damage

The reader walks the blocks and checks each one. If a block's header is intact and only its
payload CRC fails, the reader trusts the header's record count, skips exactly that block and
counts its records as lost. If the header itself is damaged, the record count cannot be
trusted, so the reader searches forward for the next `MDQB` whose header CRC is right.
Records can contain those four bytes by chance, but the 32-bit header CRC makes a false
match about as unlikely as a missed corruption. Sequence numbers reveal blocks that vanished
entirely. The test `OneCorruptByteCostsOneBlockAndNothingElse` flips a bit at 400 random places in a
file and checks each time that only the block it belongs to is lost (SRS-LMF-006).

A CRC protects against accidents, not against people. Anyone who edits a file can recompute
the CRC. With four free bytes they can even make the CRC come out as any value they like,
which Exercise 12.4 does. A file that must be shown unchanged needs a keyed MAC or a
signature (Chapter 17).

### The write path: page cache, fsync and rename

When `write()` returns, the data are in the kernel's page cache, not on the disk. The kernel
writes them back later, on its own schedule. A process crash loses nothing that `write()`
accepted, but a power loss can lose everything not yet written back. `fsync()` waits until a
file's data and metadata are on stable storage. It is the only way for a program to know that
they are, and it is slow, because it waits for the disk.

A new file's *name* is metadata of its directory, not of the file. The fsync(2) manual page
says so: making the file durable does not make its directory entry durable, which needs an
fsync of the directory. A rename is atomic: after a crash a file has either its old name or
its new one, never neither (verify: the guarantees of the file system you deploy on; Pillai
and others, 2014, catalog where file systems differ).

The sink combines these into one rule: *a file whose name ends in `.mdql` is complete.* It
writes each file as `.mdql.part`. After the closing block it calls fsync, closes the file,
renames it without replacing anything, and calls fsync on the directory. Only then does it
create the next file. The file operations are behind a small interface, so tests can replace
them with an in-memory disk that records the order of every call and fails on demand:

```{.cpp include="minidaq/include/minidaq/control/file_ops.hpp" snippet="fileops"}
```

```{.cpp include="minidaq/src/control/listmode_sink.cpp" snippet="finish_file"}
```

`rename_no_replace` uses `renameat2` with `RENAME_NOREPLACE`. Where that is not available, it
falls back to `link` followed by `unlink`. Either way an existing complete file is never
overwritten. The test `MakesEachFileDurableBeforeItsFinalName` checks the order of the calls
for each fsync policy (SRS-OUT-003).

### The sink: two threads and a pool

The pipeline's writer thread calls `write()` with batches of coincidences (Chapter 3). If it
waited for the disk, every fsync would stall the whole pipeline. So `ListModeSink` splits the
work. The writer thread only encodes, into block buffers taken from a fixed pool. Full blocks
go to the sink's own I/O thread, which writes them, calls fsync as the policy says, and
returns the buffers to the pool:

```{.cpp include="minidaq/src/control/listmode_sink.cpp" snippet="submit"}
```

Three properties follow from this design:

- **Backpressure, not loss.** When the disk is slower than the data, the pool runs dry and
  `write()` waits for a buffer. The pipeline's queues fill, and only the source decides what to
  drop, by the back-pressure or drop policy of Chapter 3. The sink never drops a coincidence while it is
  healthy, and it counts every wait (SRS-OUT-006).
- **Bounded staleness.** At low rates a block fills slowly. The writer hands a block off at
  most `max_block_delay` (100 ms) after its first record (SRS-OUT-007). A process crash
  therefore loses at most the block being filled and the blocks queued for the I/O thread,
  which the pool bounds to 4 MiB.
- **No allocation per block.** 64 buffers of 64 KiB, 4 MiB in all, are allocated once.

A failed write, fsync, close or rename makes the sink faulted. The service stops the run
(SRS-OUT-005), the file keeps its `.part` name because it is not known to be complete, and
later blocks are counted as dropped while their buffers still go back to the pool, so nothing
hangs. At the end of a run the service calls `close()`, which flushes the last block, writes
the closing block and makes everything durable. A run whose data did not reach stable storage
ends in a fault, not in a clean stop (SRS-CTL-013).

### The fsync policy

How often to call fsync is a trade between speed and what a power loss can take. The sink
offers three policies:

- **`none`.** The page cache decides. Fastest, and a power loss can take everything the kernel
  has not yet written back, which on this VM is up to 20% of RAM (the kernel's `dirty_ratio`).
- **`close`** (the default). One fsync per file, before the rename. A power loss can take the
  whole current file, up to 1 GiB, but never a file with the `.mdql` name.
- **`interval`.** Also an fsync every `fsync_every_blocks` blocks: at most that many blocks are
  at risk, 16 MiB with the default of 256.

The right policy is a measured choice, so `writer_throughput` measures it. It feeds the real
sink with synthetic coincidences on the real disk and reports the rate, the fsyncs and the
waits (`measurements/ch12/writer.py`). Figure 12.2 shows the medians on the book's VM.

![List-mode writer throughput per fsync policy on the book's VM: short runs of 320 MB, which
the page cache absorbs, and long runs of 3.2 GB, more than the kernel lets stay dirty. The
red line is the sorter's output at its own limit. Data:
`measurements/ch12/writer.txt`.](src/img/ch12-writer.png){width=100%}

The short runs measure the page cache more than the disk. Without fsync the sink writes
38 M coincidences per second, 609 MB/s, which is the encoder's speed plus a memory copy. With
one fsync at the end, 24 M per second: the fsync of 320 MB takes 285 ms, during which nothing
else happens. Frequent fsyncs (every 64 or 16 blocks) are *faster* on short runs, 36 M per
second, because each one is small and overlaps with encoding.

The long runs measure the disk. With any fsync policy the sink sustains 18.6 to 20.5 M
coincidences per second, about 300 MB/s, which is what this virtual disk delivers. Without
fsync it reaches 29 M per second only because part of the run is still in the page cache when
the clock stops. `dd` writing 3 GB with one fsync at the end gives the same picture: 278 MB/s
on the first run (verify: the second run reached 1.4 GB/s, which suggests the host caches the
virtual disk; measure on real hardware). With fsync every 16 blocks, the slowest fsync took
up to 75 ms and the writer waited for a buffer about 16,500 times per run. That is backpressure
doing its job, with nothing lost.

Against the sorter's 2.7 M per second, the slowest policy leaves a margin of seven. On this
machine the disk is not the first stage to saturate, and an `interval` policy that bounds
the loss to a few megabytes costs nothing that matters. On the acquisition PC the same
measurement must be repeated, on its disk, with a run longer than its page cache.

### Crash tests and recovery

A crash-safety claim needs a crash. `measurements/ch12/crash.py` starts the writer, kills it
with SIGKILL after a random 0.2 to 2 s, and reads every file it left with the independent Python
reader. In 20 of 20 trials every completed file was intact, there was at most one `.part`
file, and the records of all files together were exactly the first N coincidences the writer
had produced, with no gap and no duplicate. In 7 of the 20, the `.part` file ended in a
truncated block. A kill can cut a large `write()` short, so the reader's handling of a torn
tail is not a corner case.

SIGKILL ends the process, not the machine. What the process had passed to `write()` is in the
page cache and reaches the disk. A power loss can also lose what was not yet fsynced, which a
kill test cannot show (verify: with a power-cut rig or a block-layer fault injector such as
dm-log-writes). Until that test exists, the crash-safety claim holds for process crashes, and
the durability under power loss rests on the fsync policy and the file system's documented
behavior.

After a crash someone has to act on the `.part` name. Exercise 12.5 writes the recovery
tool. It cuts the partial file after its last intact block, appends a closing block that ends
the run, and renames it. It refuses to touch a run in a state that a crash alone cannot
produce: a missing segment, two partial files, or a damaged complete file. Those need a
person.

### The run record

Some facts about a run exist only at its end: how many packets the link lost (Chapter 9), how
many singles each stage dropped, how long the run lasted. The file header cannot hold them,
because it is written before the first record. So at the end of a run the sink stores a *run
record*, `<prefix>-<run>.run.json`, next to the segments. It is written and made durable like a
segment and holds the list of files, the sink's counters and the service's final status: the
configuration, the link counters and every stage's counts (SRS-OUT-010).

```{.cpp include="minidaq/src/control/listmode_sink.cpp" snippet="run_record"}
```

Together, the header and the run record let an analysis or a complaint investigation tell a
clean run from one with losses without the DAQ's logs. A run without a run record ended in a
crash or a fault, which is itself information. `minidaq_sim` uses the same mechanism to store
the truth behind simulated data: the activity, the seed and the numbers of trues, scatters
and randoms.

::: box-mistakes
- **Retrying a failed fsync.** The data may already be gone while the second call succeeds.
  Fault the run.
- **Renaming before fsync.** After a power loss the complete-looking name can point to an
  empty or partial file. Make the data durable, then the name, then the directory.
- **Writing the final name from the start.** Then nothing distinguishes a complete file from
  a crash's leftover.
- **Measuring the writer with runs that fit in the page cache.** The result is the speed of
  memory. Use runs longer than the kernel's dirty limit.
- **Dropping data in the writer when the disk is slow.** The loss is silent and in the wrong
  place. Push back to the source, where the overflow policy is decided and counted.
- **A recovery tool that "fixes" everything.** A hole in the segment numbers is not a crash.
  Report it and change nothing.
:::

## DICOM and the patient-data boundary

### DICOM for PET

Hospitals exchange images in DICOM. Its information object definitions (IODs, in part 3 of
the standard, PS3.3) say which attributes an object of each kind must carry. The *PET Image*
IOD (and the newer *Enhanced PET Image* IOD) describes reconstructed images. Several of its
attributes depend on data that only the DAQ has:

- **Timing.** The series and acquisition date and time, the frame reference time and the
  actual frame duration (0018,1242). Decay correction (0054,1102) states the reference time
  to which counts were corrected, and the decay factor (0054,1321) the correction applied.
- **The radiopharmaceutical.** The radiopharmaceutical information sequence (0054,0016) holds
  the radionuclide, its half-life (0018,1075), the injected dose (0018,1074) and the injection
  time (0018,1072).
- **Units and corrections.** Units (0054,1001), such as BQML for becquerels per milliliter,
  and *Corrected Image* (0028,0051), the list of corrections applied, such as decay,
  attenuation, scatter, randoms, normalization and dead time.

(Verify: the attribute tags, and which are required, against the edition of PS3.3 you
implement.) A standardized uptake value (SUV) computed by a viewer combines the image's
activity concentration with the patient's weight (0010,1030), the dose and the injection
time, decay corrected. An error in any of the DAQ's times reaches every SUV computed from the
images. That is why Chapter 8 insisted on a trustworthy acquisition start time. MiniDAQ
records `created_utc` from the DAQ computer's clock when the sink opens. A production system
must also relate the acquisition clock to UTC, for example with a time-mark tag at a known
UTC time from a synchronized clock (assumption: confirm with team how the NeuroLF ties its
acquisition clock to UTC).

### Where raw data fits

DICOM has room for raw data. The *Raw Data* IOD carries data whose content is defined by the
manufacturer, and vendors use it, or private attributes, to archive list-mode data and
sinograms next to the images (verify: how the NeuroLF archives raw data, if at all). Most of
the time, however, raw data never leave the scanner's own storage. Reconstruction reads them
there and sends DICOM images to the hospital's PACS, and the raw data are kept for a period
the site decides.

### The boundary

A list-mode file and a patient are linked by the scanner's workflow software: the modality
worklist gives the patient and the procedure, and the acquisition is started for them. MDQ-L1
deliberately holds no patient identity. A file is named by its run, its metadata says what
was measured and how, and the link from run to patient lives in one place that can be
protected, audited and erased. This is the *patient-data boundary*. Raw data outside it can be
copied to a physicist's workstation, attached to a bug report or used to test a new
reconstruction without disclosing health data. The DICOM images inside it carry the patient's
name, ID and birth date, and every copy of them is personal health data under the GDPR and
similar laws, which the security controls of Chapter 17 must protect.

The boundary has two consequences for the DAQ. First, the raw data must not leak identity by
the back door: no patient name in a file name, a comment field or a free-text description
(assumption: confirm with team what the NeuroLF's configuration descriptions may contain).
Second, simulated data must never pass for measured data. MDQ-L1's metadata has a `simulated`
flag, which is true for MiniDAQ's synthetic source and for `minidaq_sim`, so a simulated file
cannot be mistaken for a patient's.

::: box-regulated
The list-mode file is where the DAQ's requirements become evidence.

- **The format is a design output.** Its specification (`docs/formats/mdq-l1.md`) is an
  interface specification between the DAQ and every consumer, under document control. A change
  to it follows the versioning rules and goes through change control (IEC 62304, Chapter 14),
  with the readers that must be updated named in the change.
- **Integrity is a requirement with tests.** "No record is returned unless its block's CRC is
  correct", "one corrupt byte costs one block", "a complete file has a closing block" and the
  durability order are requirements (SRS-LMF-001 to 008, SRS-OUT-001 to 010), verified by unit
  tests, a fuzz target and a crash test. What a lost or corrupted block can do to a clinical
  result is a hazard for the risk analysis (ISO 14971, Chapter 15), and the CRCs, the fsync
  policy and the faults are its risk controls.
- **The fsync policy is a documented decision.** What a power loss can take with the shipped
  policy is stated, measured on the target hardware, and part of the device's documentation.
- **SOUP is a cost of the format choice.** A container library such as HDF5 would be SOUP with
  its own anomaly list. A custom format avoids that and takes on its own maintenance.
- **Records of the run.** The configuration in every header and the run record with its counters
  make each acquisition traceable to its settings and its losses, which complaint
  investigations and performance claims rely on (verify: what your quality system requires to
  be retained with raw data, and for how long).
- **Patient data stay inside the boundary.** Raw files carry no identity; the link to a patient
  is protected and audited, and DICOM export follows the device's DICOM conformance statement
  (PS3.2).
:::

::: box-askteam
1. What does the NeuroLF's list-mode record contain, how many bytes is it, and who reads it
   (reconstruction, calibration, the analysis framework)? Is there a written specification
   with versioning rules?
2. Are raw data kept after reconstruction, where, for how long, and who may access them? Are
   they ever archived in DICOM?
3. Which formats does the reconstruction read today (STIR, CASToR, an in-house format,
   PETSIRD), and who maintains the converters?
4. Which disk and file system does the acquisition PC write to, what fsync policy does the
   writer use, and what happens on a full disk or a power failure? Has a power-cut test been
   done?
5. How are runs linked to patients, how are simulated and phantom data marked, and how is the
   acquisition clock tied to UTC for decay correction?
:::

## Exercises {.unnumbered}

**Exercise 12.1 (M): A list-mode writer with versioning and block CRCs.** *Goal:* write and
read MDQ-L1 files from the specification alone, with a versioned header with its own CRC,
blocks protected by a payload CRC and a header CRC, and a reader that detects one corrupted
byte and skips exactly the damaged block. *Starter:* `exercises/ch12/e1_listmode_writer/` (a
CRC over the wrong bytes, time offsets from the wrong record, a reader that refuses files it
should read, and records believed without a check). *Acceptance:*
`tests/test_listmode_writer.cpp` passes: 2,000 coincidences over 20 ms come back exactly;
MiniDAQ's reader reads your file with no issue and your reader reads MiniDAQ's; for 20 random
bit flips in the payload of every block, exactly that block is reported and every other record
returned; minor version 7 is read, while major version 2 and a flipped metadata bit are
refused. Then flip a bit in a block header and explain in `NOTES.md` why a reader can skip a
damaged payload but must search past a damaged header. *Time:* 3 hours.

**Exercise 12.2 (M): From list mode to a sinogram, in Python.** *Goal:* histogram a list-mode
file into a 2D sinogram of 192 views and 227 radial bins, look at it, and get the point source
back from its sinusoid. *Starter:* `exercises/ch12/e2_sinogram/` (pure Python; the view past
180 degrees, the delayeds counted as prompts, and arc-corrected radial positions). *Acceptance:*
`tests/test_sino2d.py` passes: all 73,536 lines of a ring in different bins, at their true
distances; the 6,155 prompts of `point_source.mdql`, and not its 12 delayeds, binned exactly as
`minidaq_listmode sino` bins them; the fitted source within 2.5 mm of (40, −25) mm. Then fit
sources at five radii and explain in `NOTES.md` whether the error is a shift or a scale and what
in the detector model causes it. *Time:* 2 hours.

**Exercise 12.3 (H): A writer that keeps up with the sorter.** *Goal:* make a list-mode writer
sustain the sorter's rate on a disk whose fsync is slow, without giving up durability, and
document the fsync policy you would ship. *Starter:* `exercises/ch12/e3_writer_rate/` (a correct
sink that writes and fsyncs every block on the caller's thread). *Acceptance:*
`tests/test_fast_sink.cpp` passes on a simulated disk (20 µs per write, 20 ms per fsync):
500,000 coincidences in batches with `write()` costing at most 0.5 s more than encoding alone
and no more than two calls as slow as an fsync, the file exactly the input; for a trickle of
data, fewer than one fsync per three blocks and every byte covered by an fsync within 100 ms
plus one fsync plus 50 ms; a full disk reported as a fault, with nothing hanging. Then measure
your disk with `writer_throughput` for each policy and write your choice in `NOTES.md`. *Time:*
6 hours.

**Exercise 12.4 (E, extra): What the CRC can promise.** *Goal:* write the CRC-32 bit by bit and
with a table until it matches zlib, then measure what it detects and see what it does not.
*Starter:* `exercises/ch12/e4_crc/` (Python; a start value of 0, no final XOR, and the
polynomial written for a register that shifts the other way). *Acceptance:* `tests/test_mdq_crc.py`
passes: the check value 0xCBF43926 and agreement with `zlib.crc32`, also in pieces; the affine
property; every burst of up to 32 bits detected; no undetected two-bit error in 1 KiB, counted
in seconds although there are 33.5 million pairs; a 33-bit error shaped like the generator
missed. Then forge a message with a chosen CRC and explain in `NOTES.md` what that means for
tamper detection. *Time:* 1.5 hours.

**Exercise 12.5 (M, extra): After the crash.** *Goal:* write the tool that puts a directory of
list-mode files back in order after a crash, keeping every intact record and refusing what a
crash cannot explain. *Starter:* `exercises/ch12/e5_recovery/` (Python; a last block trusted by
its header alone, a closing block appended after the torn tail, and a missing segment not
noticed). *Acceptance:* `tests/test_recover.py` passes: a clean run left alone; a torn last
block cut and the run closed, idempotently; a block of the right length with zeroed records not
trusted; a closed but unrenamed file renamed once; a torn header removed; a missing segment, two
partial files and a damaged complete file reported with nothing changed; a dry run that changes
nothing. Then kill a real writer, recover its directory, and explain in `NOTES.md` which bytes
truncation destroys and when that would not be safe. *Time:* 2.5 hours.

## MiniDAQ milestone: a list-mode writer and a sinogram histogrammer {.unnumbered}

::: box-milestone
**Goal.** MiniDAQ stores its coincidences in versioned, checksummed list-mode files that
survive a crash, histograms them into sinograms with the scanner's geometry, and has a format
specification that a reader can be built from. **Start:** tag `ch11`. **End:** tag `ch12`.
:::

1. Add `core/crc32.hpp` (slicing-by-8 and a byte-at-a-time reference, SRS-LMF-001 and 002) and
   `core/byte_io.hpp` (the little-endian loads and stores, now shared with the readout packet).
2. Add `format/list_mode.hpp`: the header encoder and parser, `BlockWriter`, `parse_block`,
   `decode_record` and the resynchronizing `Reader`, with `test_list_mode.cpp` (SRS-LMF-003 to
   008), a fuzz target `fuzz_listmode` and its corpus.
3. Add `processing/sinogram.hpp`: `lor_bin`, the radial positions, `Histogrammer` with SSRB,
   TOF bins, delayeds and the Michelogram, and the Interfile-style header, with
   `test_sinogram.cpp` (SRS-SNO-001 to 005).
4. Add `control/file_ops.hpp` and `control/listmode_sink.hpp`: the two-thread sink with
   rotation, the fsync policies, the `.part` and rename protocol, faults and the run record, with
   `test_listmode_sink.cpp` (SRS-OUT-001 to 010). Give `CoincidenceSinkPort` `close()` and
   `counters()`, and make the service close the sink at the end of a run (SRS-CTL-013).
5. Raise the configuration schema to 1.3 with the `/output` section (SRS-CFG-012), select the
   sink with `output.type: "listmode"`, and give `minidaq_sim` the option `--listmode`.
6. Add `minidaq_listmode` (`info`, `verify`, `sino`), the benchmarks `bm_listmode` and
   `writer_throughput`, and the measurements `writer.py`, `crash.py` and `sinogram.py` with their
   results.
7. Write `docs/formats/mdq-l1.md` and ADR 0012, and mark ADR 0007 superseded.

**Definition of done.** `ci/run_all.sh` is green on all six presets; `tools/static_analysis.sh`
reports nothing; the fuzz target runs for 60 s without a finding; the Python reader reads every
file the C++ writer writes and the C++ reader reads the Python writer's file; the crash test
recovers every written record in 20 of 20 trials; the writer's sustained rate with fsync on the
target disk exceeds the sorter's output at its limit; each measurement is regenerated by one
command whose header names the machine. Tag `ch12`.

## Check yourself {.unnumbered}

1. Why keep list-mode data at all if sinograms are smaller? Name three analyses that need it.
2. What metadata must travel with every acquisition, and why in the file rather than next to
   it?
3. Why does MDQ-L1 store a 32-bit time offset per record and a 64-bit base time per block? What
   does that cost at low rates?
4. A reader finds a block whose header CRC is right and whose payload CRC is wrong. What does it
   do, and what does it do if the header CRC is wrong instead?
5. Which changes to MDQ-L1 raise the minor version, and which the major version? Why must a
   reader check the version before the sizes?
6. What does the fold at 180 degrees do to a line's view and to the sign of its radial
   position? What goes wrong in the sinogram if the sign is not flipped?
7. Why are MiniDAQ's radial bins not evenly spaced, and what is arc correction?
8. What is the Michelogram, what does SSRB do with it, and what does SSRB lose?
9. A delayed coincidence has a time difference of 100,250 ps with a 100 ns delay. Which TOF value
   does the histogrammer bin, and why?
10. Why is `.mdql.part` renamed to `.mdql` only after an fsync, and why is the directory synced
    after the rename?
11. The writer reaches 38 M coincidences per second without fsync on a short run and 19 M with
    fsync on a long one. Which number describes the disk, and why?
12. Why must a failed fsync fault the run instead of being retried?
13. A CRC detects every two-bit error in a block. Why is it still not a guard against
    tampering?
14. Where is the patient-data boundary for a PET scanner, and which side of it are MDQ-L1 files
    on?

## Summary {.unnumbered}

- List mode stores every coincidence with its time, crystals, time difference, energies and
  kind; a sinogram is a product made from it for one reconstruction, and cannot be split,
  gated or rebinned afterwards.
- MDQ-L1 packs a coincidence into 16 bytes by giving each block a 64-bit base time and each
  record a 32-bit offset; settings go in the header, once.
- Versioning is a promise: minor versions only add what old readers can ignore, and readers
  refuse an unknown major version, which they check first.
- A CRC-32 per block header and per payload localizes damage to one block; slicing-by-8 makes
  it cost 7 ns of the 20 ns per record.
- A sinogram indexes lines by angle and distance; MiniDAQ folds lines past 180 degrees, keeps
  the true, uneven radial positions, rebins axially with SSRB and keeps the Michelogram.
- TOF bins need the sinogram's endpoint convention and the delay removed from delayed pairs.
- HDF5, Interfile, STIR, CASToR and PETSIRD each serve readers well; the DAQ writes its own
  simple format and converts, as ADR 0012 records.
- Durability is an order: data, fsync, close, rename, directory fsync; a `.mdql` name means
  complete, and an fsync error is a fault.
- The two-thread sink pushes back instead of dropping; on the book's VM it sustains about
  19 M coincidences per second with fsync, seven times the sorter's output at its limit.
- Raw files carry no patient identity; the run record and the `simulated` flag make every run
  traceable and keep simulations from passing for measurements.

## Further reading {.unnumbered}

- P. Koopman, "32-bit cyclic redundancy codes for Internet applications", *Proceedings of the
  International Conference on Dependable Systems and Networks (DSN)*, 2002, 459–468 (verify:
  the page numbers).
- R. N. Williams, "A painless guide to CRC error detection algorithms", 1993, widely mirrored
  online: the clearest derivation of table-driven CRCs.
- M. E. Kounavis and F. L. Berry, "A systematic approach to building high performance
  software-based CRC generators", *Proceedings of the 10th IEEE Symposium on Computers and
  Communications (ISCC)*, 2005: slicing-by-8 (verify: the citation details).
- T. S. Pillai and others, "All file systems are not created equal: on the complexity of
  crafting crash-consistent applications", *Proceedings of the 11th USENIX Symposium on
  Operating Systems Design and Implementation (OSDI)*, 2014.
- The Linux manual pages fsync(2), rename(2) and renameat2(2); and the PostgreSQL wiki page
  "Fsync Errors" on the 2018 fsync failure handling (verify: the page's current title).
- M. E. Daube-Witherspoon and G. Muehllehner, "Treatment of axial data in three-dimensional
  PET", *Journal of Nuclear Medicine* 28 (1987) 1717–1724: single-slice rebinning.
- K. Thielemans and others, "STIR: software for tomographic image reconstruction release 2",
  *Physics in Medicine and Biology* 57 (2012) 867–883.
- T. Merlin and others, "CASToR: a generic data organization and processing code framework for
  multi-modal and multi-dimensional tomographic reconstruction", *Physics in Medicine and
  Biology* 63 (2018) 185005.
- A. Todd-Pokropek, T. D. Cradduck and F. Deconinck, "A file format for the exchange of nuclear
  medicine image data: a specification of Interfile version 3.3", *Nuclear Medicine
  Communications* 13 (1992) 673–699.
- The HDF Group, *HDF5 User's Guide*, and the documentation of single-writer multiple-reader
  (SWMR) mode.
- NEMA, *Digital Imaging and Communications in Medicine (DICOM)*, PS3.3 Information Object
  Definitions (the PET Image, Enhanced PET Image and Raw Data IODs) and PS3.2 Conformance.
