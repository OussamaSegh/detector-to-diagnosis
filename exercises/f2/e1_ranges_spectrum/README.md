# Exercise F2.1 (E): The spectrum with ranges and std::ranges::to

**Goal.** Compute three things from a batch of singles with C++20 views instead of loops: the
energies in a window, an energy histogram, and the fraction of singles in the photopeak. Collect
a view into a `std::vector` with C++23's `std::ranges::to` where your standard library has it,
and with the vector's iterator-pair constructor where it does not, chosen by the feature-test
macro `__cpp_lib_ranges_to_container`.

**Time.** 45 minutes.

**Acceptance tests** (`tests/test_spectrum.cpp`): the window keeps order; every in-range single
lands in exactly one bin; the histogram equals a loop on 20,000 random singles; a value at the
lower edge of a bin belongs to that bin, and `hi` is outside the range; the fraction is 0 for an
empty batch.

**Hint.** A view is lazy: `s | std::views::filter(f) | std::views::transform(g)` computes
nothing until you iterate it. A `filter_view` is not a sized range, so count it with
`std::ranges::distance`, and give the vector constructor a common range (`std::views::common`).
