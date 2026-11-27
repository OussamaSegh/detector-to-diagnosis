# Exercise F2.4 (A): A view that dangles

**Goal.** Audit the recorded change in `CHANGE.md`: a coding assistant added two functions that
return views (`std::span`, `std::string_view`) "because they do not copy", and said the code
compiles without warnings. Write your findings in `REVIEW.md`, each with an input that shows it,
then fix `starter/spectrum.hpp`.

**Time.** 30 minutes.

**Acceptance tests** (`tests/test_spectrum.cpp`):
- `peak_region` returns a span that points into the spectrum's own storage (checked by address,
  so the test never reads a dangling view);
- `peak_region` rejects a region outside the spectrum;
- `label()` returns an owning `std::string`.

Under the `asan-ubsan` preset, a test that read through the starter's views would stop with
`heap-use-after-free`; these tests do not need it.

**What to look for.** For every view a function returns, ask: what does it point at, and does
that live longer than the view? Then check the transcript's two claims ("does not copy", "no
warnings") against the code.
