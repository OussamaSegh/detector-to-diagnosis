# Exercise 1.5 (M, extra): A crystal geometry table built by the compiler

**Goal.** Write `ex::make_ring_table<N>(radius_mm)`, a `consteval` function that returns a
`std::array<ex::Point2, N>` with the centre of each of N crystals evenly spaced on a
ring (crystal i at angle (i + 0.5) * 2*pi/N). Use `minidaq::cmath::sincos`, because
`std::sin` is not `constexpr` in C++20. Then declare
`inline constexpr auto ring384 = ex::make_ring_table<384>(150.0);` and prove with
`static_assert` that the table exists at compile time.

**Time.** 45 minutes.

**Acceptance tests.** Every point lies on the circle within 1e-9 mm; neighbours are
2*pi*150/384 mm apart (within 1e-3, chord vs arc); point 0 is in the first quadrant;
`ex::ring384` is usable in a constant expression.
