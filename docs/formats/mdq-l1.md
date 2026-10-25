# MDQ-L1: MiniDAQ list-mode file format, version 1.0

Status: Accepted (ADR 0012). Implementation: `minidaq/include/minidaq/format/list_mode.hpp`
(C++), with an independent reader in `measurements/ch12/crash.py` and
`exercises/ch12/e2_sinogram` (Python). Requirements: SRS-LMF-001 to 008 (format) and
SRS-OUT-001 to 009 (the writer).

The words MUST, MUST NOT, SHOULD and MAY are used as in RFC 2119.

## 1. Purpose and scope

An MDQ-L1 file holds the coincidences of one acquisition (a *run*), or one segment of it,
one record per coincidence or tag, in time order, with the metadata needed to interpret
them. It is the raw output of the DAQ. Sinograms, images and DICOM objects are derived
from it; it is not exchanged with clinical systems and holds no patient data (section 9).

Design goals, in order: no record is ever silently wrong (checksums); a crash or a
damaged sector costs only the blocks it touches; a writer sustains the sorter's peak rate
with one core; a reader needs nothing but this document; the format can grow without
breaking old readers.

## 2. Conventions

- All integers are little-endian. Signed integers are two's complement.
- Offsets and sizes are in bytes. Times are in picoseconds (ps) of the acquisition clock.
- CRC means CRC-32 as in ISO-HDLC, zlib, PNG and Ethernet: polynomial 0x04C11DB7,
  reflected input and output, initial value 0xFFFFFFFF, final XOR 0xFFFFFFFF. The CRC of
  the ASCII bytes `123456789` is 0xCBF43926.

## 3. File structure

A file is a file header followed by zero or more blocks:

```
file header | block 0 | block 1 | ... | block n-1 | closing block
```

### 3.1 File header

| Offset | Size | Field | Value |
|---:|---:|---|---|
| 0 | 8 | magic | `4D 44 51 4C 0D 0A 1A 0A` ("MDQL\r\n\x1a\n") |
| 8 | 2 | major | 1 |
| 10 | 2 | minor | 0 |
| 12 | 4 | header_bytes | 40 + pad8(metadata_bytes) |
| 16 | 4 | metadata_bytes | length m of the metadata, at most 1,048,576 |
| 20 | 4 | flags | 0 |
| 24 | 4 | record_bytes | 16 |
| 28 | 4 | reserved | 0 |
| 32 | m | metadata | UTF-8 JSON (section 6), then zero bytes up to pad8(m) |
| 32 + pad8(m) | 4 | header_crc | CRC of bytes 0 to 31 + pad8(m) |
| 36 + pad8(m) | 4 | reserved | 0 |

pad8(m) is m rounded up to a multiple of 8, so blocks start 8-byte aligned. The magic
contains a carriage return, a line feed and Ctrl-Z, as PNG's does, so that a transfer that
translates line endings or stops at end-of-text damages it visibly.

A reader MUST check, in this order: the magic; the major version (reject any other than
1); metadata_bytes and header_bytes (consistent and within the limit); the file holds
header_bytes bytes; header_crc; then flags, record_bytes, the reserved fields and the
padding (MUST be as above). The version comes before the sizes because a later major
version may place them elsewhere; the CRC comes before the remaining fields so that a
damaged header is reported as damaged rather than as a strange value. A reader MUST NOT
read past the end of the data at any step.

### 3.2 Block

| Offset | Size | Field | Value |
|---:|---:|---|---|
| 0 | 4 | magic | "MDQB" (`4D 44 51 42`) |
| 4 | 4 | sequence | 0 for the first block of every file, then +1 per block |
| 8 | 4 | record_count | n, 0 to 65,536 |
| 12 | 4 | flags | bit 0: end of run; bit 1: end of file; other bits 0 |
| 16 | 8 | base_time_ps | signed; the time of the block's first record, 0 if n = 0 |
| 24 | 4 | payload_crc | CRC of the n × 16 record bytes |
| 28 | 4 | header_crc | CRC of block bytes 0 to 27 |
| 32 | 16 n | records | section 4 |

A block is *intact* when its magic and header_crc are right, its fields are valid, all
16 n record bytes are present and payload_crc is right. Only the records of intact
blocks MAY be returned.

### 3.3 Closing block

Every file MUST end with a block of zero records, the *closing block*, with exactly one
of the flags set: end of run (the run ends with this file) or end of file (the run
continues in the file with the next segment number). Nothing follows a closing block. A
file without one was not completed (section 7).

## 4. Records

Every record is 16 bytes:

| Offset | Size | Field | Meaning |
|---:|---:|---|---|
| 0 | 4 | time_offset | unsigned ps after base_time_ps: the time of the earlier single |
| 4 | 2 | crystal_a | bits 0 to 14: crystal of the earlier single; bit 15: delayed |
| 6 | 2 | crystal_b | crystal of the later single |
| 8 | 4 | dt_ps | signed: time of the later single minus time of the earlier |
| 12 | 2 | energy_a | energy of the earlier single, in units of 1/32 keV |
| 14 | 2 | energy_b | energy of the later single, in units of 1/32 keV |

- Crystal ids are `ring × crystals_per_ring + transaxial index` (the geometry is in the
  metadata). Ids 0x7FFF and above are not crystals.
- A record with bit 15 of crystal_a set is a *delayed* coincidence: a pair found in the
  delayed window, which estimates the randoms. Its dt_ps includes the delay (the
  metadata's `records.delayed_window_ps`); a reader that bins it by time of flight
  removes the delay first.
- Energies are rounded to the nearest 1/32 keV. Energies below 0 are stored as 0 and
  energies that round above 65,535 units (2047.97 keV) as 65,535; a writer SHOULD count such clamps.
- Within a block, record times MUST NOT decrease, and every time_offset MUST fit in 32
  bits (4.29 ms).

### 4.1 Tags

A record with crystal_a = 0x7FFF (bit 15 clear) is a *tag*: crystal_b is its kind, dt_ps
its value, energy_a and energy_b are 0, and time_offset its time like any record.

| Kind | Name | Value |
|---:|---|---|
| 0 | (invalid) | |
| 1 | gate | the gate channel (a physiological trigger: ECG R wave, respiratory phase) |
| 2 | time_mark | the index of a periodic mark from the acquisition clock |
| 3 to 1023 | reserved for later versions of this document | |
| 1024 to 65535 | site-specific | |

A reader MUST skip tags of kinds it does not know.

## 5. Writing rules

- A writer closes a block, and starts the next, when it holds its maximum number of
  records, when the next record is more than 2^32 − 1 ps after the block's base time, or
  when the next record is earlier than the previous one (a *time reset*: a clock restart
  shows as a block whose base time is earlier than the last record of the block before).
- A writer SHOULD hand a block to storage no later than a bounded delay after its first
  record (MiniDAQ: 100 ms), so that a crash at low rates loses at most that much.
- Sequence numbers start at 0 in every file and increase by one per block, closing block
  included.

## 6. Metadata

The metadata is one JSON object. Version 1.0 defines these members; a reader MUST ignore
members it does not know, and a writer MAY add more.

| Member | Content |
|---|---|
| `format` | `"MDQ-L1"` |
| `software` | name and version of the writer, e.g. `"MiniDAQ 0.2.0"` |
| `created_utc` | ISO 8601 time at which the run started, from the DAQ computer's clock |
| `simulated` | `true` if the records come from a simulation, not from a detector |
| `file` | `{"segment": N, "run_name": "..."}` |
| `scanner` | model; `crystals_per_ring`, `crystal_rings`, `inner_radius_mm`, `axial_pitch_mm`; how crystal ids and angles are defined |
| `records` | `time_unit` (`"ps"`), `energy_lsb_kev` (0.03125), `delayed_window_ps`, `coincidence_window_ps` |
| `configuration` | the complete effective acquisition configuration (schema 1.3) |

The configuration is copied whole, not summarized, so that a file can be interpreted
without the machine that wrote it. Calibration tables are referenced by identifier and
version inside it rather than copied (assumption: confirm with team how NeuroLF
identifies calibration sets).

## 7. Files, rotation and crash safety

- A run is written as segments named `<prefix>-<run_name>-<NNNN>.mdql`, NNNN = 0000,
  0001, ... A writer starts a new segment before the current one would exceed its size
  limit (MiniDAQ: 1 GiB).
- A segment is written under the name `<...>.mdql.part`. After its closing block the
  writer makes it durable (fsync, unless configured not to), closes it, renames it to
  `<...>.mdql` without replacing an existing file, and makes the rename durable (fsync of
  the directory). Only then does it create the next segment.
- So a file named `.mdql` is complete. After a crash, a run is complete segments and at
  most one `.part`, the last; the `.part` is readable up to its last intact block. A
  recovery tool cuts it after that block, appends a closing block with the end-of-run
  flag and renames it (`exercises/ch12/e5_recovery`). A hole in the segment numbers, two
  `.part` files, or a damaged complete file are not crash states and need a person.
- After the run's last segment is complete, the writer stores the *run record*
  `<prefix>-<run_name>.run.json` the same way (`.part`, fsync, rename, fsync of the
  directory): `{"format": "MDQ-L1 run record", "run_name", "files": [...],
  "sink_counters": {...}, "run": {...}}`, where `run` is what the acquisition reported at
  the end of the run: the counters of the link (packets lost, reordered, stale), of every
  pipeline stage and the configuration. A file set without a run record ended in a crash
  or a fault; its counters are in the DAQ's log only.

## 8. Reading rules

- A reader walks blocks from header_bytes. On a block that is not intact it reports the
  offset and the reason. If only the payload CRC is wrong, the header is trusted and the
  reader skips exactly that block (its records are lost and counted). Otherwise it
  resynchronizes: it searches forward for the next "MDQB" whose header CRC is right.
- A sequence number other than the expected one means lost blocks; the difference
  (modulo 2^32) is counted as lost.
- A reader reports, for every file: intact blocks and records, blocks and records lost,
  bytes skipped, and whether the file ended with a closing block, and which.

## 9. What MDQ-L1 is not

- It is not an exchange format. Reconstruction tools read sinograms (Interfile headers)
  or their own list-mode formats, produced by converters; clinical systems receive DICOM
  images from the reconstruction.
- It holds no patient identity. The link between a run and a patient lives in the
  scanner's workflow software, by run name (assumption: confirm with team).
- It is not a guard against tampering. A CRC detects accidents; a file that must be shown
  unchanged needs a keyed MAC or a signature, which is outside version 1.0.

## 10. Versioning

- A change that a 1.0 reader can ignore safely (a new metadata member, a new tag kind
  from the reserved range, a flag bit a reader may ignore) increases the minor version.
  A 1.x reader reads every 1.y file.
- Any other change (a field moved, a new record size, a flag that changes meaning)
  increases the major version, and a reader MUST reject a major version it does not know.
- record_bytes is in the header so that a later major version can say so; version 1
  readers require 16.

## 11. Test vectors

- `fuzz/corpus/listmode/three_blocks.mdql`: three blocks written by an independent
  Python implementation; `test_list_mode.cpp` reads it (SRS-LMF-008).
- `exercises/ch12/e2_sinogram/tests/point_source.mdql`: 0.1 s of a point source written
  by `minidaq_sim --listmode`, 6,155 prompts and 12 delayeds.
