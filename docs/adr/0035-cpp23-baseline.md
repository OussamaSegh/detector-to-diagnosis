# 0035. C++23 as the baseline, keeping the Expected alias for Clang

Date: 2026-11-15
Status: Accepted

## Context

ADR 0006, which this record supersedes, chose C++20 on both compilers, with `minidaq::Expected` as an alias of `std::expected`
where the library provides it and a small implementation otherwise; a `gcc-cxx23` preset tested
the alias. The roadmap for 2.0.0 asks for C++23 as the baseline, limited to what GCC 13 and Clang
18 with libstdc++ 13 accept (CR-0028). The question is what that baseline may use, and what
becomes of the shim.

## Options

1. **C++23 and `std::expected` everywhere, Clang with libc++.** Removes the shim; adds a second
   standard library to qualify, as ADR 0006 already found.
2. **C++23 and `std::expected` everywhere, GCC only.** Loses Clang's sanitizers and warnings.
3. **C++23 everywhere, `minidaq::Expected` kept**: an alias on GCC, the shim on Clang 18, whose
   libstdc++ 13 hides `<expected>` (it needs `__cpp_concepts >= 202002L`; Clang 18 defines
   201907L).
4. **Stay on C++20.**

## Decision

Option 3. Every build is C++23 (`CMAKE_CXX_STANDARD 23`, `cxx_std_23`). The GCC presets
(debug, release, hardened) compile `minidaq::Expected` as `std::expected` and the Clang presets
(clang-release, asan-ubsan, tsan) as the shim, so the six presets test both, and the
`gcc-cxx23` preset is retired; `release` replaces it in `ci/run_all.sh` and the CI matrix.

The baseline uses a C++23 feature only where GCC 13 and Clang 18 with libstdc++ 13 both have
it, and only where it replaces hand-made code: `std::to_underlying` for enumerations stored as
integers. It does not use `std::unreachable` on a value that comes from outside the program (a
register, a file, a datagram), because it would turn a bad value into undefined behaviour; the
switches keep their defined fallbacks (coding standard, rule 1). Explicit object parameters,
`std::print`, `std::ranges::to`, `std::mdspan` and modules are out: GCC 13 or libstdc++ 13
lacks them.

## Consequences

### Positive

- The book teaches the standard that new code is written in; readers on C++20 are told what
  each feature replaces (Chapter 1).
- One preset fewer, and both implementations of `Expected` still tested in every run.

### Negative

- The shim stays, with its tests, until the Clang baseline moves (Clang 19 defines the concepts
  macro that libstdc++ needs). Revisit with the next toolchain change.
- cppcheck 2.13 knows no C++23 and parses the sources as C++20 (`tools/static_analysis.sh`);
  clang-tidy 18 reads the C++23 compile commands. Code that only C++23 can parse would need a
  newer cppcheck first.
