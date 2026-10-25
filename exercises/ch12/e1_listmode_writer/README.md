# Exercise 12.1 (M): A list-mode writer with versioning and block CRCs

**Goal.** Write and read MDQ-L1 list-mode files from the specification
(`docs/formats/mdq-l1.md`), without `minidaq::listmode`: a versioned file header with
its own CRC, blocks of 16-byte records each protected by a payload CRC and a header CRC,
and a reader that detects a single corrupted byte, skips exactly the damaged block and
keeps everything else. Your files must be readable by MiniDAQ's reader, and MiniDAQ's
files by yours. This is the plan's "implement a list-mode writer with header versioning
and CRC32 per block; corrupt one byte and detect it".

**Time.** 3 hours.

**Starter.** `starter/listmode_writer.cpp` builds and is complete except for four
mistakes, each marked with a TODO near the place it lives (not on the wrong line itself):
one CRC covers the wrong bytes, the time offsets are taken from the wrong record, the
reader refuses files it should read, and it believes records without checking them. You
may use `minidaq::crc32` and `minidaq::load_le`/`store_le`, nothing from
`minidaq/format/list_mode.hpp`. One test, reading a file written by MiniDAQ, already
passes: the decoding of records is right.

**Acceptance** (`tests/test_listmode_writer.cpp`):
- Round trip: 2,000 coincidences over 20 ms (prompts and delayeds) come back exactly, so
  blocks must end on the 32-bit time offset (4.29 ms) as well as on the record count.
- `minidaq::listmode::Reader` reads your file with no issue, the same coincidences, and
  the end-of-run block; your reader reads a file written by `BlockWriter`, skipping its tag.
- For 20 random single-bit flips in the payload of every block, the reader reports that
  block, and only that block, in `bad_blocks`, and returns every other record and no
  record that was never written.
- A minor version of 7 is read; a major version of 2, and a flipped bit in the
  metadata, make `header_ok` false.

**Then, by hand.** Flip one bit in a block *header* instead. What does your reader do,
and what does MiniDAQ's (`minidaq_listmode info` on the file)? Why can a reader skip a
block whose payload is damaged but not, without searching, one whose header is? Answer
in `NOTES.md`.

**Hints.** The specification says which bytes each CRC covers; write the CRC after the
bytes it covers. A 32-bit offset from what? Think of a 10-minute run. The version rule
is in the specification's first section: what may a minor version add?
