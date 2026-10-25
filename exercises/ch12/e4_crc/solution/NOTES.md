# Exercise 12.4: notes on the solution

**The three differences.**

- *The start value.* zlib starts the register at 0xFFFFFFFF. With 0, leading zero
  bytes do not change the CRC: a block whose first records were zeroed by a bad
  sector would still check, as long as nothing else changed.
- *The final XOR.* zlib inverts the register at the end, so the CRC of nothing is 0
  and a run of trailing zeros is detected. Without it, the numbers simply differ from
  every other program's, and the CRC in pieces needs the same correction at the start
  (`crc ^= 0xFFFFFFFF` undoes the previous inversion).
- *The polynomial's bit order.* 0x04C11DB7 is the polynomial with x^31 in the most
  significant bit, for a register that shifts left. zlib processes each byte least
  significant bit first, so its register shifts right and the polynomial is written
  reversed: 0xEDB88320. The starter used the left-shift constant in a right-shift
  register, which is a valid CRC of a different polynomial: it passes the affine and
  burst tests and matches nobody.

**Counting without trying** (`undetected_two_bit_errors`). A pair of flips at bits i
and j goes unnoticed exactly when the changes s(i) and s(j) of the single flips are
equal. 8,192 CRCs of 1 KiB and a dictionary replace 33.5 million: under a second here.
No two of the 8,192 changes are equal, so every 2-bit error in a 1 KiB block is
detected. The same argument with three terms is how published tables of a
polynomial's "Hamming distance" by message length are computed, more cleverly; for
this polynomial see Koopman (DSN 2002), whose limit for all 3-bit errors is quoted in
`minidaq/include/minidaq/core/crc32.hpp`.

**Three terms, not two** (Then, by hand, 1). The start value and the final XOR make
the CRC affine, not linear: crc(m) = L(m) ^ k for a linear L and a constant k that
depends only on the length. With three terms the constant appears three times and is
left once, as on the left side; with two it cancels: crc(a ^ b) = crc(a) ^ crc(b) ^
crc(zeros of that length).

**Forging** (Then, by hand, 2). The CRC of prefix + w is affine in the 32 bits of w,
and the 32 by 32 matrix is invertible, so every target has exactly one w:

```python
import zlib

def forge(prefix, target):
    """Four bytes w such that zlib.crc32(prefix + w) == target."""
    base = zlib.crc32(prefix + bytes(4))
    cols = [zlib.crc32(prefix + (1 << i).to_bytes(4, "little")) ^ base for i in range(32)]
    basis = {}  # leading bit -> (effect on the CRC, the bits of w that make it)
    for i in range(32):
        eff, inp = cols[i], 1 << i
        for b in sorted(basis, reverse=True):
            if eff >> b & 1:
                eff ^= basis[b][0]
                inp ^= basis[b][1]
        if eff:
            basis[eff.bit_length() - 1] = (eff, inp)
    want, w = target ^ base, 0
    for b in sorted(basis, reverse=True):
        if want >> b & 1:
            want ^= basis[b][0]
            w ^= basis[b][1]
    return w.to_bytes(4, "little")
```

`forge(b"record payload that someone edited", 0xDEADBEEF)` is `73 1a 8c f7`, and the
CRC of the result is 0xDEADBEEF. Nobody even needs four free bytes: an edit anywhere
can be compensated in any four consecutive bytes, by the same algebra. A CRC detects accidents
(noise, a torn write, a bad sector), which is all MDQ-L1 asks of it. Proof that a file
was not changed needs a key the editor does not have: a keyed MAC such as HMAC-SHA-256
(RFC 2104, FIPS 198-1) or a digital signature over a hash of the file, and a decision
about who holds the key. In a regulated product that is a security requirement with
its own risk analysis (IEC 81001-5-1, Chapter 7), not a property of the file format.
