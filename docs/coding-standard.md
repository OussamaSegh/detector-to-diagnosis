# MiniDAQ coding standard

Version 4 (MiniDAQ 0.4.0-dev, release 0.4.0). Status: draft for review.

A coding standard is useful when each rule has a reason and a machine checks
it wherever a machine can. Every rule below says why it exists and what
enforces it: a compiler warning (`cmake/Warnings.cmake`, all warnings are
errors), a clang-tidy check (`.clang-tidy`), cppcheck, a sanitizer, a test, or
review. Rules that only review can enforce are marked *review*.

Rule identifiers in brackets refer to published rule sets: SEI CERT C and C++
(for example ERR34-C) and the C++ Core Guidelines (for example R.11). This
document cites them by identifier only; read the rule sets themselves for
their text. MiniDAQ does not claim conformance to any of them.

## 1. Language and build

1. C++20, also built as C++23 (`gcc-cxx23` preset). No compiler extensions
   (`CMAKE_CXX_EXTENSIONS OFF`). *Enforced:* CMake, both compilers in CI.
2. The code compiles without warnings under GCC and Clang with the flags in
   `cmake/Warnings.cmake`, including `-Wconversion -Wsign-conversion
   -Wold-style-cast -Wshadow -Wformat=2`. *Enforced:* `-Werror`.
3. Shipped builds use the hardened preset (ADR 0008). *Enforced:*
   `build.hardening` test reads the binaries.

## 2. Errors

1. On the hot path (`minidaq_core`) functions report failure through return
   values (`Expected`, counts, `std::error_code`), never exceptions, because a
   stage thread that throws terminates the process. *Enforced:* review;
   `bugprone-exception-escape`.
2. In the control plane, exceptions from libraries (the JSON library,
   `std::bad_alloc`) are caught at the boundary that turns them into a result:
   the configuration reader, `handle_request`, `main`. *Enforced:* the fuzz
   targets; `bugprone-exception-escape` on `main`.
3. A return value that reports failure is checked, or discarded with `(void)`
   and a comment that says why that is safe [CERT ERR33-C]. MiniDAQ's own
   such functions are `[[nodiscard]]`. *Enforced:* `cert-err33-c`
   (the configured function list is in `.clang-tidy`), and the compilers'
   warnings for a discarded `[[nodiscard]]` result.
4. A lost record or sample is counted, never silent: dropped items, filtered
   items, late singles, failed audit writes. *Enforced:* tests that make each
   failure happen (`/dev/full` for the audit trail).

## 3. Untrusted input

Everything that crosses the process boundary is untrusted: configuration
files, control requests, file paths named in them, command-line arguments,
detector data.

1. Parse strictly and completely. A number is valid only if the whole text is
   a number of the target type within its range: `minidaq::parse_number`,
   never `atoi`, `atof` or unchecked `strtol` [CERT ERR34-C]. *Enforced:*
   `cert-err34-c`.
2. Every input has a size limit, checked before the input is used: 64 KiB per
   control request, 64 KiB per profile file. *Enforced:* tests; fuzz targets.
3. A path from a client is opened first and checked through the open
   descriptor (regular file, size), not checked and then opened, which leaves
   a window for the file to be swapped [CERT FIO45-C]. *Enforced:* review;
   test `ProfilePathMustBeASmallRegularFile`.
4. Each parser of external input has a fuzz target that runs in CI.
   *Enforced:* `fuzz/`, CI job `fuzz-smoke`.
5. A value from an untrusted JSON document is read after its type is
   checked (`find` or `contains`, then `is_string()` and the like), never
   with `value(key, default)` or `get<T>()` alone, which throw on another
   type. A long-running process never lets a JSON exception escape a request;
   a one-shot tool may, if `main` reports it and exits with an error
   (CAPA-0003). *Enforced:* test `ControlProtocol.EveryFieldOfEveryTypeIsAnswered`
   (every field of a request with every JSON type; review adds each new
   field to it); fuzz targets.

## 4. Resources and types

1. Resources are owned by objects (RAII); no `new`/`delete` outside a smart
   pointer or container [R.11]. C handles (`FILE*`, descriptors) get an owning
   wrapper or a destructor. *Enforced:* `cppcoreguidelines-owning-memory`.
2. Rule of zero where possible; otherwise declare all five special members
   [C.21]. *Enforced:* `cppcoreguidelines-special-member-functions`.
3. Quantities carry units in their type (`Picoseconds`, `KeV`) and ids are
   not numbers (`CrystalId`) (Chapter 1). *Enforced:* the type system.
4. No casts that the compiler cannot check, except `reinterpret_cast` at C API
   boundaries (sockets, SIMD intrinsics), each marked with a reason.
   *Enforced:* `cppcoreguidelines-pro-type-reinterpret-cast`,
   `-Wold-style-cast`.

## 5. Concurrency

1. Stage threads never take a lock; they share only atomics and the channels
   between stages (Chapters 2 and 3). *Enforced:* review; ThreadSanitizer.
2. Every atomic operation that is not `seq_cst` states its memory order and,
   in a comment, what it synchronizes with. *Enforced:* review.
3. A callback is never called with a lock held that the callback could need
   (the state machine's listener, Chapter 6). *Enforced:* test
   `ListenerSeesEveryTransitionAndMayReadTheState`; ThreadSanitizer.
4. No functions that are not thread-safe (`strerror`, `localtime`, `getenv`
   after threads start) [CON33-C]. Use `std::system_category().message()`,
   `gmtime_r`. *Enforced:* `concurrency-mt-unsafe`.
5. A test never sleeps for a fixed time and then asserts that something has
   happened: it waits for the condition, with a deadline long enough that only
   a hang reaches it (`test_support::eventually`, `minidaq/tests/unit/eventually.hpp`).
   A sleep in a test states its reason, `// sleep: poll`, `minimum`, `device`
   or `hides only`, and a test of a timing requirement asserts the requirement,
   not the speed of the machine it runs on. A test that fails at random teaches
   people to rerun it, which hides the day it fails for a reason (CAPA-0001).
   *Enforced:* test `tests.waits`; the stress run of CAPA-0001.
6. A test that starts threads and then checks what they did first waits until
   each of them has started its work (a `std::latch` or `std::barrier`), and
   does not assume that a thread runs before the next statement of the thread
   that created it (MDQ-PR-028, CAPA-0001). *Enforced:* review (checklist item
   4.6); the coverage build of the release checks, which starts threads slowly.

## 6. The hot path

1. No allocation after `start()` (Chapter 2). *Enforced:* test binary
   `minidaq_alloc_tests` counts allocations.
2. No logging, no system calls other than those a stage exists for, no
   unbounded loops without a stop check. *Enforced:* review; latency tests.
3. Performance claims come with a benchmark that states machine, compiler
   and flags. *Enforced:* review; `tools/perf_gate.py`.

## 7. Suppressions

A finding of a tool is fixed, or suppressed at the narrowest scope with a
reason a reviewer can check:

- one line: `// NOLINT(check-name): reason` or `NOLINTNEXTLINE`,
- a region: `NOLINTBEGIN(check-name)` / `NOLINTEND`, with the reason above it,
- a whole check: disabled in `.clang-tidy` with the reason in the comment
  block there; for cppcheck, an entry in `tools/cppcheck-suppressions.txt`.

A suppression without a reason is a review finding. `tools/static_analysis.sh`
must report nothing before a change is merged.

## Changes

| Version | Change |
|---|---|
| 1 | First version (Chapter 7). |
| 2 | Rule 5.5 on waiting in tests (CAPA-0001), and this history (Chapter 16). |
| 3 | Rule 3.5 on reading untrusted JSON (CAPA-0003, problem report MDQ-PR-013). |
| 4 | Rule 5.6 on tests that start threads (CAPA-0001, problem report MDQ-PR-028). |
