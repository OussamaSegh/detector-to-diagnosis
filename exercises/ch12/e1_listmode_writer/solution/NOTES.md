# Exercise 12.1: notes on the solution

**The four mistakes.**

- *The payload CRC covered the block header too.* It is stored inside that header, so
  it cannot cover itself; MiniDAQ's reader computes it over the records only and
  reported `bad_payload_crc` for every block of the starter's files. The header CRC is
  written last, over the 28 bytes before it, so it protects the payload CRC as well.
- *The time offsets were taken from the first record of the file.* After 2^32 ps
  (4.29 ms) the offset wraps and the times come back wrong. The base is the block's
  first record, and a block ends when the next offset would not fit: at 300,000
  coincidences per second a block holds about 1,300 records before its time span, not
  its record count, closes it.
- *The reader refused minor version 1.7.* Minor versions only add what an older reader
  may ignore (a new tag kind, a new metadata key); refusing them would make every
  addition break every installed reader. The major version is the one to refuse.
- *The reader did not check the payload CRC.* A flipped bit in a crystal number or a
  time then becomes a wrong coincidence in the image, silently. With the check, the
  block is reported and skipped, and the reader goes on: the block header is intact, so
  the next block is where the record count says.

**A damaged block header** ("Then, by hand"). This reader stops: the record count is no
longer trustworthy, so it does not know where the next block starts. MiniDAQ's reader
searches forward for the next "MDQB" whose header CRC is valid and resumes there,
reporting the damaged block and the gap in the sequence numbers. The search is safe
because a false match needs four magic bytes and a matching 32-bit CRC by chance.
