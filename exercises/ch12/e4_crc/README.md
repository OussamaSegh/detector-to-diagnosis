# Exercise 12.4 (E): What the CRC can promise, in Python

**Goal.** Write the CRC-32 that guards every MDQ-L1 header and block, bit by bit and
with a table, until it gives zlib's numbers; then measure what it detects and see what
it does not. The format's claim that "a damaged block is found" is only as good as
this function and your understanding of it. Pure Python, no numpy.

**Time.** 1.5 hours.

**Starter.** `starter/mdq_crc.py` follows a textbook's description of a CRC and has
three differences from the CRC-32 of zlib, Ethernet and PNG: the start value of the
register, what happens at the end, and how the polynomial is written for a register
that shifts right. `undetected_two_bit_errors` is yours to write.

**Acceptance** (`tests/test_mdq_crc.py`):
- `crc32_bitwise` and `crc32_table` give `0xCBF43926` for `b"123456789"` (the check
  value) and agree with `zlib.crc32` on random messages, also when the CRC is computed
  in pieces: `crc(b, crc(a)) == crc(a + b)`.
- The CRC is affine: for messages of one length, `crc(a ^ b ^ c) == crc(a) ^ crc(b) ^
  crc(c)`.
- Every burst of up to 32 bits in a 64-byte message changes the CRC.
- `undetected_two_bit_errors(1024)` is 0, and takes seconds: there are 33.5 million
  pairs of bits in 1 KiB, too many to try one by one in Python.
- A 33-bit error shaped like the generator polynomial is not detected.

On the starter, the affine and burst tests pass (a wrong CRC can still be a CRC);
the other five fail.

**Then, by hand.**
1. Why does the affine property need three terms, not two? What would `crc(a ^ b)`
   be?
2. A colleague proposes the CRC as a check that nobody edited a list-mode file. Write
   `forge(prefix, target)`: four bytes that, appended to `prefix`, give the CRC
   `target`. What does this say about the CRC as a guard against tampering, and what
   would you use instead? Answer in `NOTES.md`.

**Hints.** zlib starts the register at all ones and inverts it at the end; a register
that shifts right processes the least significant bit first and needs the polynomial
with its bits reversed. For the count: by the affine property, the change two flips
make is the XOR of the changes each makes alone.
