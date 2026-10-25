# 0012. MDQ-L1, a custom block format for list-mode data, written by a two-thread sink

Date: 2026-10-25
Status: Accepted

## Context

ADR 0007 left the list-mode format open until Chapter 12 could measure the options. The
format holds the raw output of every acquisition: reconstruction, calibration and the
analysis framework read it for years after the scan. The requirements, from Chapter 12:

- Rate: whatever the sorter can produce. At its own limit, 70 M singles per second
  (Chapters 10 and 11), that is about 2.7 M coincidences per second; the writer must keep
  up with a margin on the acquisition disk, using at most one core.
- Integrity: a damaged record is detected, never returned; a damaged sector costs the
  blocks it touches and nothing after them.
- Crash safety: after a process crash or a power loss, everything up to the last durable
  block can be read, and a complete file can be told from an incomplete one by its name.
- Metadata: the configuration, the geometry, the software version and the delayed window
  travel inside every file.
- Readable from C++ and Python with nothing but a written specification.

## Options

1. **A custom block format (MDQ-L1)**: a versioned header with JSON metadata, then
   blocks of fixed 16-byte records, each block with its own sequence number and CRC-32s
   over header and payload, written by a sink that encodes in the pipeline's writer
   thread and does the I/O in a thread of its own.
2. **HDF5**, with the records as a chunked, extendable compound dataset and the metadata
   as attributes. Self-describing and widely read (h5py, MATLAB, ROOT). A large SOUP item
   (IEC 62304) whose file stays consistent after a crash only in single-writer
   multiple-reader mode or with careful flushing (verify: for the HDF5 version in question),
   and whose write rate depends on chunk size, compression and the library's caches.
3. **An existing list-mode convention**: the format of a reconstruction package (CASToR's
   list-mode data files, STIR's supported scanner formats) or the emerging PETSIRD
   specification of the Emission Tomography Standardization Initiative. Reconstruction
   would read the DAQ's output directly, but each convention fixes fields the DAQ does not
   control (CASToR stores event times in milliseconds; verify: in its current user guide), carries none of the acquisition's
   configuration, or is not yet stable (verify: PETSIRD's current status).

## Decision

Option 1. The format is specified in `docs/formats/mdq-l1.md` and implemented in
`minidaq/format/list_mode.hpp`; the writer is `control::ListModeSink`, selected by the
configuration section `/output` (schema 1.3, `type: "listmode"`).

- Records are 16 bytes: 32-bit time offsets from a 64-bit block base time, two 15-bit
  crystal ids with a delayed flag, a signed 32-bit time difference, and energies in
  1/32 keV. Tags (gates, time marks) share the record stream.
- Blocks hold up to 4,096 records by default (64 KiB) and close when full, when a time
  offset would overflow (4.29 ms) or on a time reset; a block is handed to the disk at
  most 100 ms after its first record.
- Files are written as `.part`, made durable and renamed; runs rotate at 1 GiB; every file
  ends with a closing block saying whether the run continues.
- The fsync policy is configurable (`none`, `close`, `interval`); the default is `close`.
- Converters, not the DAQ, produce the formats of reconstruction tools: `minidaq_listmode
  sino` writes sinograms with an Interfile header. HDF5 and PETSIRD converters can be
  added later without touching the acquisition path.

ADR 0007 is superseded.

## Consequences

### Positive

- Measured on the book's VM (`measurements/ch12/writer.txt`): 18.6 to 20.5 M coincidences
  per second sustained over 3.2 GB with fsync (policies `close` and `interval`), and
  23 to 38 M per second on short runs, against the sorter's 2.7 M at its limit: a margin
  of seven at the worst.
- Encoding costs 20 ns per record on one core, CRCs included (`bm_listmode`: 49 M
  records per second, `measurements/ch12/bm_listmode.txt`); slicing-by-8 CRC-32 runs at
  2.07 GiB/s, 7 ns per record, so integrity is about a third of the encoding cost.
- 20 of 20 `kill -9` trials (`measurements/ch12/crash.txt`) recovered every record that
  was written, in order, with an independent Python reader; complete files were always
  intact and the `.part` file was readable up to its last complete block.
- One corrupted byte costs exactly one block; the reader resynchronizes on the next
  intact block header (SRS-LMF-006). The fuzz target `fuzz_listmode` exercises the reader
  on arbitrary input.
- No new SOUP: the format needs the standard library and the JSON library already used.

### Negative

- The format is ours to document, version, test and convert from, for as long as data in
  it exists. Every reconstruction or analysis tool needs a converter.
- The CRC detects accidents, not tampering; integrity against deliberate change needs a
  keyed MAC or signatures, which version 1.0 does not have.
- Writes are not durable until fsynced: with the default policy, a power loss can lose
  the whole current file (up to 1 GiB) even though a process crash loses nothing. Sites
  that need a bound use `interval` (at most `fsync_every_blocks` blocks at risk), at a
  measured cost.
- Kill tests show what survives a process crash only. Behavior under power loss depends
  on the file system and the disk's write cache and is not yet tested (verify: with a
  power-cut rig or a block-layer fault injector).
- Energies are quantized to 1/32 keV and clamped at 2,048 keV; crystal ids are limited to
  32,767, enough for 384 × 48 crystals and not for a scanner twice as large in both
  directions. Both are fixed for major version 1.
