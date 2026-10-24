# Exercise 7.5 (E): A strict duration parser

**Goal.** Configuration files contain durations: `"interval": "250ms"`. The starter
parses them with `strtod`, which accepts far more than the grammar allows and
silently turns errors into numbers. Write `parse_duration` so that it accepts
exactly the grammar in `duration.hpp` and nothing else.

**Time.** 1 hour.

**Acceptance** (`tests/test_duration.cpp`): the five units; exact fractions (`0.1s` is
exactly 100 ms; `1.5ns` is rejected); leading zeros allowed; spaces, signs,
exponents, hex, `inf`, `nan`, a missing or unknown unit, and anything after the unit
rejected; overflow of `std::chrono::nanoseconds` rejected, not wrapped, at the exact
boundary.

**Hints.** What does `4.1 * 1e9` give in `double`, and what does the cast to an integer do with it? Check for overflow before each multiplication and addition, not after.
