# Exercise 2.4 (H): Design a 64-bit packed single

**Goal.** Design and implement a 64-bit word that carries crystal id, coarse time, fine time
and energy, with `pack`/`unpack` and `encode(Single)`/`decode(word)` functions, and prove
it with round-trip property tests. Use the layout of MiniDAQ's MDQ-P1 format (Chapter 2) or
justify your own in `DESIGN.md`: number of crystals, time resolution, wrap period and energy
range must all be stated.

**Time.** 2 hours.

**Acceptance tests** (`tests/test_word.cpp`):
- Fields never overlap; all-ones fields produce an all-ones word.
- 200,000 random singles round-trip: crystal exact, energy within half an LSB, time within one
  LSB after truncation (and modulo the wrap period).
- Endianness: `to_bytes()` produces little-endian bytes regardless of host order.
