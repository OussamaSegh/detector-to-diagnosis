# Exercise 7.5: notes on the solution

The starter shows four classic failures of "just use strtod":

- It accepts what the grammar forbids: `" 10ms"` (leading space), `"+5ms"`,
  `"1e3ms"`, `"inf s"`, `"0x10ms"`; `strtod` is a C-locale number parser with
  its own, larger grammar.
- An unknown or missing unit silently means nanoseconds: `"10"`, `"10m"` and
  `"10sec"` all parse.
- Overflow is undefined behavior: converting a `double` larger than
  `INT64_MAX` to `long long` is undefined, and in practice gives a garbage value.
- Rounding: `4.1` is not exactly representable in binary floating point, and
  `4.1 * 1e9` is 4099999999.9999995; the cast truncates it to 4,099,999,999 ns,
  one nanosecond short. (`0.1 * 1e9` happens to round to exactly 100,000,000,
  which is why a test with only round values does not find this.)

The solution parses digits with integer arithmetic only, checks every
multiplication and addition against `INT64_MAX` before doing it, and requires
the unit to be the rest of the string exactly. The overflow tests sit on both
sides of the boundary (`9223372036854775807ns` accepted, one more rejected),
because a test that only tries an absurdly large number does not show that
the check is in the right place.
