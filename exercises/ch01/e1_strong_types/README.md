# Exercise 1.1 (E): Strong types for picoseconds and keV

**Goal.** Write `Picoseconds` and `KeV` types that refuse to mix in arithmetic
at compile time, cost nothing at run time, and still allow the operations a DAQ
needs (add and subtract same-unit values, scale by a number, compare).

**Time.** 30 to 45 minutes.

**Starter.** `starter/units.hpp`: both types are plain aliases (`using Picoseconds = std::int64_t;`),
so everything mixes. Replace them with a tagged wrapper.

**Acceptance tests** (`tests/test_units.cpp`):
- `Picoseconds + Picoseconds` and `KeV - KeV` compile and give the right value.
- `Picoseconds + KeV`, `Picoseconds + int64_t` and implicit `int64_t -> Picoseconds` do not compile
  (checked with `std::is_invocable_v` / `std::is_convertible_v`, so the starter builds and the test fails).
- `sizeof(Picoseconds) == sizeof(std::int64_t)` and both types are trivially copyable.
- Comparison operators work; `Picoseconds / Picoseconds` gives a plain number.

**Run.** `ctest --preset debug -L starter -R e1_strong_types` (configure with `-DMINIDAQ_BUILD_STARTERS=ON`).
