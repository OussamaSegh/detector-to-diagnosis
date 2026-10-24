# 0006. C++20 with a std::expected shim

Date: 2026-10-24
Status: Accepted

## Context

MiniDAQ reports expected errors as values (Chapter 1). `std::expected` is the standard way
to do that, but it is a C++23 library feature. GCC 13 with `-std=c++23` provides it. Clang 17
and 18 used with libstdc++ 13, the default on Ubuntu, do not: the header is guarded by a
feature-test macro for concepts that those Clang versions do not define. We build and test
with both compilers, because each finds bugs the other misses.

## Options

1. **C++23 and GCC only.** Use `std::expected` directly; lose Clang's sanitizers and
   warnings from CI.
2. **C++23 with libc++ for Clang builds.** Works, but two standard libraries double the
   configurations to qualify, and ABI mixing with system packages becomes a risk.
3. **A third-party `expected`** (for example tl::expected). Proven code; one more SOUP item
   whose API differs slightly from the standard one.
4. **C++20 everywhere, plus a small `minidaq::Expected`** that is an alias of
   `std::expected` when the library provides it and a minimal implementation otherwise.

## Decision

Option 4. The language standard is C++20 on every compiler. `minidaq/core/expected.hpp`
provides `Expected`, `Unexpected` and the subset of operations we use, and becomes an alias
of `std::expected` when `__cpp_lib_expected` is defined. Code must use only operations that
exist in `std::expected` with the same meaning.

## Consequences

### Positive

- Both compilers, all sanitizers, one standard library.
- Moving to C++23 later deletes the shim without changing call sites.

### Negative

- We own a small piece of vocabulary code and its tests.
- Two implementations behind one name, so the tests must run against both: the `gcc-cxx23`
  preset (GCC, C++23, `std::expected`) is part of `ci/run_all.sh` and the CI matrix, beside
  the C++20 presets that use the shim. Revisit when the toolchain baseline changes.
