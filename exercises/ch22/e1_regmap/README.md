# Exercise 22.1 (M): Generate a register map

**Goal.** Write a generator that reads a board's register map from a TOML specification, refuses
a specification with the mistakes that happen in practice, and writes a C++ header of constants.
MiniDAQ's own generator (`tools/regmap_gen.py`) writes types; this one writes the constants that
most embedded code starts with, so that you see what the types add.

**Time.** 60 minutes.

**The specification.**

```toml
[map]
name = "demo"           # the C++ namespace

[[register]]
name = "control"
address = 0x008         # bytes; a multiple of 4
access = "rw"           # ro, rw, wo or rw1c
reset = 0x00000001      # optional, 0 by default
fields = [
  { name = "enable", lsb = 0, width = 1 },
  { name = "mode", lsb = 4, width = 3 },
]
```

**Starter.** `starter/regmap.py`: `SpecError`, `load(text)` and `header(spec)` to write.

**Tasks.**
1. `load(text)` parses the TOML (`tomllib`) and raises `SpecError` with the register's name in the
   message when an address is not a multiple of 4, two registers have the same address or name, the
   access is not one of the four, a field does not lie inside bits 0 to 31, two fields of a register
   overlap, or the reset value sets a bit outside every field. It returns the parsed dictionary.
2. `header(spec)` returns a C++ header: `#pragma once`, `#include <cstdint>`, and in
   `namespace <name>` for every register `inline constexpr std::uint32_t CONTROL_ADDR = 0x008;` and
   `CONTROL_RESET = 0x00000001;`, and for every field `CONTROL_MODE_SHIFT = 4;` and
   `CONTROL_MODE_MASK = 0x00000070;` (names in upper case, register then field; hexadecimal in
   upper case with the widths shown).

**Acceptance** (`ch22/e1_regmap/<variant>/unittest`): `tests/test_regmap.py` passes. When a C++
compiler is found (`CXX` or `c++`), one test compiles the generated header with a small program
that sets and reads fields in a fake block of registers, and runs it.

Then answer in `NOTES.md`: name two mistakes that a header of constants lets through and a type
per register catches at compile time.
