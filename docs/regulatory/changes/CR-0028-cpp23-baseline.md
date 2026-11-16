# CR-0028: C++23 as the language baseline

| Field | Value |
|---|---|
| Status | implemented |
| Requested | 2026-11-15, by the software lead |
| Source | improvement; roadmap 2.0.0, theme B, answer 4 |
| Decision | approved, 2026-11-15, under the software lead's standing delegation of 2026-11-15 |
| Commits | 95c3af2 (the C++23 baseline) and the commit that records this |

## Description

MiniDAQ is written in C++20 and also built as C++23 by one CI preset, `gcc-cxx23`. The change
makes C++23 the language standard of every build, limited to what GCC 13 and Clang 18 with the
GNU standard library 13 both accept:

1. **The standard.** `CMAKE_CXX_STANDARD` becomes 23 and `minidaq_core` requires `cxx_std_23`.
   Every preset builds C++23; a C++20 build is no longer supported.
2. **`Expected` stays, as an alias where it can.** GCC 13 with libstdc++ 13 provides
   `std::expected`, and `minidaq::Expected` is then an alias of it. Clang 18 with the same
   library does not: libstdc++ guards `<expected>` on `__cpp_concepts >= 202002L`, and Clang 18
   defines 201907L, so in `-std=c++23` the header is empty and `__cpp_lib_expected` undefined
   (checked on the build machine, 2026-11-15). The shim of ADR 0006 therefore stays for Clang
   builds. Call sites do not change.
3. **The presets.** With C++23 everywhere, the GCC presets (debug, release, hardened) use
   `std::expected` and the Clang presets (clang-release, asan-ubsan, tsan) use the shim, so
   every run of the six presets tests both implementations. The `gcc-cxx23` preset, whose only
   purpose was that second implementation, is retired; the `release` preset (GCC, Release)
   takes its place in `ci/run_all.sh`, the CI matrix and the release record's list.
4. **The features used.** C++23 features replace hand-made code where both compilers accept
   them: `std::to_underlying` for the enumerations written to traces and the flight recorder.
   `std::unreachable` is not used in the product: the switches over enumerations end in a
   defined fallback because the value can come from outside (a register, a file, a datagram), and
   `std::unreachable` would turn such a value into undefined behaviour. `if consteval` and the
   multidimensional subscript operator are shown in Part I's text; MiniDAQ has no function that
   asks whether it is evaluated at compile time, and no multidimensional container without
   `std::mdspan`, which libstdc++ 13 lacks. Explicit object parameters, `std::print`,
   `std::ranges::to` and modules are not used: GCC 13 or libstdc++ 13 lacks them.
5. **The book.** Chapter 1 says what each feature replaces, for readers on C++20 or C++17;
   Chapters 6, 7, 20 and 32 and the presets figure follow the retired preset.

## Reason

C++20 was chosen in 2026-10 (ADR 0006) because one of the two compilers could not use
`std::expected`. The language features of C++23 that GCC 13 and Clang 18 share are enough for
MiniDAQ, and the book should teach the standard that new projects start with (roadmap 2.0.0,
answer 4). Keeping
C++20 keeps a preset that duplicates the release build, and keeps readers from features they
will meet at work. What does not change is the reason for the shim: Clang 18 with libstdc++ 13
still lacks `std::expected`, so the roadmap's wish to show `std::expected` directly in Part I is
met for GCC only, and the text says why.

## Impact analysis

### Requirements

None added, changed or withdrawn. Every requirement's verification is repeated, because every
program is compiled again under another standard: the six presets, the static analysis, the
starters, the stress run, the fuzzing and the performance gate of the release checks.

### Software items and safety class

All items are recompiled; the source changes are in `core` (the enumeration conversions) and
the build files. No class or segregation changes.

### Risk

No hazard, risk control or estimate changes. A change of language standard can change the
meaning of existing code (for example overload resolution or implicit moves in return
statements, P2266); the controls are the full test suite under both compilers and the
sanitizers, the static analysis with zero findings, and the performance gate against 1.3.0. The
choice not to use `std::unreachable` on values from outside the program is a risk control
against undefined behaviour, recorded in the coding standard.

### SOUP

No SOUP item is added, removed or upgraded. The compilers and the standard library are the same
(GCC 13.3, Clang 18, libstdc++ 13); GoogleTest, nlohmann/json and Google Benchmark build in C++23
already (the `gcc-cxx23` preset). The SOUP list records the language standard they are built
with.

### Interfaces and data formats

None. The control protocol, the configuration schema, the readout format and the list-mode
format are unchanged. The ABI of the libraries is not an interface of the product.

### Documents

The software development plan (section 4: C++23), the coding standard (rule 1, and a rule for
`std::unreachable`), the tool list (TL-01 and TL-02: the presets that use each compiler), ADR
0035, which supersedes ADR 0006, and the ADR index.

### Regulatory

The intended use and the safety-relevant functions do not change. A change of language standard
is a change of the development environment, verified by the full release checks; not a
significant change.

## Verification

Tests: `Expected.IsStdExpectedWhereverTheLibraryHasIt`,
`ReleaseRecord.test_the_current_rules_ask_for_the_current_presets`; and the checks below.

- A trial build on 2026-11-15, before this request: `clang-release` with
  `-DCMAKE_CXX_STANDARD=23`, no warnings (warnings are errors), 953 of 953 tests passed. The
  `gcc-cxx23` preset has passed in every CI run since release 0.1.
- After the change: the six presets and their tests (`ci/run_all.sh`), the static analysis, the
  exercise starters and solutions, the documentation tests, the CI on GitHub, and at the next
  release the complete release checks, with the performance gate against 1.3.0.
- A test that the build uses C++23 (`__cplusplus > 202002L`: GCC 13 reports 202100L for
  `-std=c++23`, Clang 18 reports 202302L) and that `minidaq::Expected` is
  `std::expected` exactly when `__cpp_lib_expected` is defined.

## Decision

Approved on 2026-11-15 by the coordinator under the software lead's standing delegation of
2026-11-15, as proposed, with one condition: Part I shows `std::expected` itself, says plainly
where it is available (GCC 13 with libstdc++ 13) and where it is not (Clang 18 with libstdc++
13), and explains why `minidaq::Expected` is an alias there and a shim here.
