# Exercise 1.3 (M): A parser that cannot be crashed

**Goal.** Implement
`ex::parse_single(std::span<const std::byte>) -> minidaq::Expected<ex::Single, ex::ParseError>`
for the 16-byte *raw16* record (little-endian `int64` time in ps, `uint32` crystal id,
`float32` energy in keV), then attack it with malformed input.

**Rules.** No exceptions, no allocation, never read outside the span, no
`reinterpret_cast` of the byte buffer (use `std::memcpy` or `std::bit_cast`). Reject:
short input, negative time, crystal id >= 18432, non-finite energy, energy outside
[0, 2000] keV.

**Time.** 60 to 90 minutes.

**Acceptance tests** (`tests/test_parse.cpp`):
- Round trip of valid records.
- Ten hand-written malformed inputs, each mapped to the right `ParseError`.
- A deterministic mutation "fuzz" loop: 200,000 random byte flips and truncations of
  valid records. The parser must never crash (run it under `asan-ubsan`) and every
  accepted record must satisfy the invariants.
