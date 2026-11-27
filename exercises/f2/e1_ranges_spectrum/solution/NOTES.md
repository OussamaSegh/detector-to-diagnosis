# Notes on the solution

**Views compose.** `in_window(lo, hi)` returns a range adaptor, a filter waiting for its input, so
`energies_in_window` and `photopeak_fraction` share it. The pipelines read left to right in the
order the data flows.

**Projections.** `std::views::transform(&Single::energy_kev)` uses a pointer to a member as the
function: views and the `std::ranges` algorithms call it through `std::invoke`.

**The feature-test macro.** `std::ranges::to` is in libstdc++ from GCC 14; the book's reference
compiler, GCC 13, does not have it. `<version>` defines `__cpp_lib_ranges_to_container` when it
does, so one header compiles on both. When MiniDAQ moves to a newer compiler (roadmap 3.0.0,
Theme N), the `#else` branch is deleted and nothing else changes.

**Edges.** Bins are half-open, `[lo + i w, lo + (i + 1) w)`, so every energy has exactly one bin,
and `hi` itself is outside. Floating-point division can produce `bins` for a value just below
`hi`; the clamp keeps it in the last bin.

**Cost.** A view does not allocate and does not copy the singles. The histogram loop compiles to
about what a hand-written loop compiles to at `-O2`; check it on Compiler Explorer.
