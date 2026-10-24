# 0008. Hardened release builds

Date: 2026-10-24
Status: Accepted

## Context

MiniDAQ parses bytes from detector boards, configuration files and network clients
(Chapter 7). A memory error in that code may be exploitable, and in an acquisition it may
also corrupt data silently. Compilers and linkers offer protections that make many memory
errors stop the program at once, or make them much harder to exploit. Which of them a build
gets by default depends on the toolchain: on the build machine (Ubuntu 24.04), GCC 13.3
enables most of them and Clang 18 enables few (`tools/check_hardening.py` on the `release`
and `clang-release` presets). The hot path has a performance budget (Chapter 5), so the cost
must be known.

## Options

1. **Rely on the toolchain's defaults.** No work; the protection depends on which compiler
   and distribution built the binary, and nobody checks.
2. **State the protections in the build, except those that touch the hot path**
   (`_GLIBCXX_ASSERTIONS`). No hot-path cost; out-of-bounds accesses through standard
   containers stay silent.
3. **State all of them in the build and check the binary.** A small, measured cost in some
   loops; the same protections with every compiler.

## Decision

Option 3. `cmake/Hardening.cmake` applies `-fstack-protector-strong`,
`-fstack-clash-protection`, `-D_FORTIFY_SOURCE=3` (optimized builds), `-D_GLIBCXX_ASSERTIONS`,
PIE, full RELRO, a non-executable stack and, on x86-64, `-fcf-protection=full`, to every
target when `MINIDAQ_HARDENING` is on. The `hardened` preset is what ships. The test
`build.hardening` reads the shipped binaries and fails if PIE, RELRO, immediate binding, a
non-executable stack or the CET properties are missing.

Measured cost (Chapter 7, `measurements/ch07/`): no difference outside the noise for decode,
energy filter, histogram and the whole pipeline; 8 to 18% for `std::sort` of a 4,096-single
batch, caused by `_GLIBCXX_ASSERTIONS`, leaving a margin of 3.8x at 30 M singles/s.

## Consequences

### Positive

- The same protections whatever the compiler, verified in the binary on every CI run.
- Out-of-bounds accesses through standard containers stop the program with a message
  instead of corrupting data.

### Negative

- The sort stage is measurably slower. If the performance gate (Chapter 5) shows the margin
  shrinking below 2x, revisit `_GLIBCXX_ASSERTIONS` for that stage first, with this ADR
  superseded by a new one.
- Performance numbers measured before Chapter 7 are from unhardened builds; the performance
  budget says so.
- CET markings protect only on CPUs and kernels that enforce them (verify: the acquisition
  PC's CPU, kernel and C library).
