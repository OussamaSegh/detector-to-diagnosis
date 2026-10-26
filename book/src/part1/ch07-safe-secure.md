# Safe and secure C++ {#ch07}

::: box-why
A PET scanner's acquisition PC reads bytes from detector boards, accepts commands over a
network, and writes data that a physician will look at. Each of those is an input that can be
wrong: a board with a firmware bug, a misconfigured client, a disk that fills up, and
sometimes an attacker. In C++ a wrong input can become undefined behavior, and undefined
behavior can become a wrong image, a crashed scan or a compromised machine. Regulators now ask
for more than good intentions. Medical device cybersecurity standards and premarket guidance
expect a secure development process with evidence: a coding standard and how it is enforced,
static analysis and what was done with its findings, testing of inputs, and a list of every
third-party component in the product. This chapter builds that evidence for MiniDAQ, and on the
way it finds real bugs in code that passed every test of the first six chapters.
:::

**A day in the life.** It is your second month. A field engineer reports that a scanner's
acquisition service stopped during a calibration run; the service log ends in the middle of a
line. Two hours later a security questionnaire arrives from a hospital's IT department: which
open-source components does the acquisition software contain, in which versions, and how do
you learn about their vulnerabilities? In a code base without the work of this chapter, the
first question is a long debugging session and the second is an afternoon of reading build
files. In MiniDAQ after this chapter the crash reproduces in seconds, because the
configuration it was given is a fuzzing input like thousands of others and the fuzzer had
already found the class of bug. The audit trail would not have ended silently either: a
failed write is now counted and reported. The questionnaire is answered by attaching the
SBOM that every build produces, validated against the CycloneDX schema, and pointing to the
SOUP list that says how each component's known anomalies are reviewed.

## Learning objectives {.unnumbered}

After this chapter you can:

1. Explain what a secure coding standard (SEI CERT C and C++, MISRA C++:2023, the C++ Core
   Guidelines) is for, distinguish a guideline violation from a defect, and write rules that
   a machine enforces.
2. Set up static analysis (compiler warnings, clang-tidy, cppcheck, CodeQL) with a curated
   configuration, triage the first run of findings, and keep a suppression policy that a
   reviewer can audit.
3. Write libFuzzer targets with properties, not only crash detection, for the parsers that
   handle untrusted input; run campaigns; and turn every crash into a regression test.
4. Harden builds (stack protector, `_FORTIFY_SOURCE`, library assertions, PIE, full RELRO,
   non-executable stack, CET), verify the result in the binary, and measure what it costs.
5. Pin dependencies, generate and validate a CycloneDX SBOM, and keep a SOUP list with
   requirements and an anomaly review.

## Prerequisites and estimated time {.unnumbered}

Chapters 1 to 6, in particular undefined behavior and the sanitizers (Chapter 1), the packed
decoder (Chapter 2) and the control plane (Chapter 6). You need Clang 18 with libFuzzer
(`libclang-rt-18-dev` on Ubuntu), `clang-tidy-18`, `cppcheck`, `readelf` (binutils) and Python 3
with `jsonschema`. Reading: about 3 hours. Exercises: 8 to 10 hours, plus an hour of unattended
fuzzing. Milestone: 4 hours. In the 10-week schedule at the front of the book, this chapter is
in week 6, with Chapters 16, 17 and 18.

## Coding standards in regulated software

### The intuition

A coding standard is a list of things not to do and things to always do, each with a reason.
C++ needs one more than most languages, because so many of its mistakes compile, run, pass the
tests and then fail in the field: a signed overflow, a read past the end of a buffer, an
ignored error code, a number parsed from text that was not a number. The useful standards are
built from collected experience of exactly those failures.

Three are relevant to you. The **SEI CERT C and C++ coding standards** are rule sets from
Carnegie Mellon's Software Engineering Institute, focused on security; each rule has an
identifier (ERR34-C, CON33-C), an explanation, compliant and noncompliant examples, and a risk
assessment. **MISRA C++:2023**, from the MISRA consortium, targets C++17 in critical systems;
it absorbed the AUTOSAR C++14 guidelines and is common in automotive and medical work where a
restrictive, decidable subset is wanted. The **C++ Core Guidelines**, edited by Bjarne
Stroustrup and Herb Sutter, are a modern-C++ style guide (rule identifiers like R.11 and
C.21) with a strong position on ownership and types. MISRA's text is licensed and not
reproduced here or in MiniDAQ; CERT and the Core Guidelines are free to read online.

None of them is a law. What a regulated process needs is that *you* chose a standard (or a
subset, or your own rules derived from them), that you can say why, that it is applied to
every change, and that you can show how you know it was applied. That last part decides
whether the standard is worth anything: a rule that only a reviewer's memory enforces will be
broken within a month.

### A guideline violation is not a defect

A *defect* is code that does the wrong thing. A *guideline violation* is code that matches a
pattern that often does the wrong thing. Most violations are not defects, and many defects
violate no guideline. The distinction matters in two directions. A process that treats every
violation as a defect drowns in false alarms and teaches people to suppress findings
mechanically. A process that treats only demonstrated defects as worth fixing waits for the
field to demonstrate them. The working compromise is to fix violations that are cheap to fix
even when you are not sure they are defects, and to suppress the rest one by one, with a
reason that a reviewer can check.

### MiniDAQ's coding standard

`docs/coding-standard.md` is MiniDAQ's standard. It is short: seven sections (language and
build, errors, untrusted input, resources and types, concurrency, the hot path, suppressions)
and about thirty rules. Each rule says why it exists and what enforces it: a compiler warning,
a clang-tidy check, cppcheck, a sanitizer, a test, or "review" when nothing better exists. It
cites CERT and Core Guidelines rules by identifier only.

One rule shows the style. Untrusted input must be parsed strictly and completely: "a number is
valid only if the whole text is a number of the target type within its range". The rule exists
because of CERT ERR34-C ("detect errors when converting a string to a number"), clang-tidy
enforces it with `cert-err34-c`, and MiniDAQ provides the function that makes following it
easy:

```{.cpp include="minidaq/include/minidaq/core/parse_number.hpp" snippet="parse_number"}
```

`std::from_chars` is the right primitive: it does not depend on the locale, does not skip
leading spaces, reports range errors, and tells you where it stopped, so a trailing `"ms"` or
a stray `"O"` is caught by `ptr != end`. For floating-point types it also accepts `inf` and
`nan`, which almost no configuration wants, hence the `isfinite` check. A unit test
(`test_parse_number.cpp`) pins down what is rejected: `"7OO"`, `"65536"` for a `uint16_t`,
`" 1"`, `"1 "`, `"+1"`, `"inf"`, `"1e999"`.

### Worked example: three ways to misread a port number

Before this chapter, `minidaq_server` read its port like this:

```cpp
port = static_cast<std::uint16_t>(std::atoi(v));
```

That line passed review, and all tests, for six chapters. `std::atoi` returns 0 for text that
is not a number and stops at the first character that is not a digit; the cast then wraps
anything above 65535. So `--port 7OO` (letter O) listens on port 7, `--port 70000` listens on
port 4464, and `--port abc` listens on port 0, which the kernel replaces with a random free
port. The server then prints the port it actually got, so a careful operator might notice;
a start script that connects to 7700 would only report that the server is unreachable. The
fix is the rule above:

```cpp
if (!parse_into<std::uint16_t>(v, port, 0, 65535)) {  // 0: any free port (tests use it)
  std::fprintf(stderr, "--port: \"%s\" is not a port number (0 to 65535)\n", v);
  return 2;
}
```

The same pattern was in `minidaq_ctl` (`--port`, and the `wait` timeout parsed with
`std::atof`), `minidaq_jitter` and `minidaq_latency`. None of these is a hot path and none
faces the network directly, which is exactly why nobody had looked. Static analysis looks
everywhere.

::: box-mistakes
- **Adopting a whole standard without reading it.** Hundreds of rules nobody understands get
  suppressed in bulk. Start from a subset you can enforce, and grow it.
- **Rules without reasons.** A rule people do not understand is followed literally where it
  does not matter and worked around where it does.
- **Rules without enforcement.** If no tool checks a rule, write down who checks it, when,
  and where the record is; otherwise drop the rule.
- **Treating the standard as the goal.** Zero violations is a means. The goal is fewer
  defects reaching the field, and tests remain the main way to find them.
:::

## Static analysis and suppression policy

### The intuition

Static analysis reads code without running it and reports patterns that are often wrong. It
ranges from the compiler's warnings, through *linters* that match patterns in the syntax tree
(clang-tidy, cppcheck), to *semantic* analyzers that follow values through paths in a program
(the Clang Static Analyzer inside clang-tidy, CodeQL). Each finds things the others miss, and
all of them report things that are fine. The engineering is in choosing what to run, deciding
what to do with each finding, and keeping the result at zero so that a new finding is news.

MiniDAQ runs four layers:

| Layer | Tool | Runs | What it finds best |
|---|---|---|---|
| Compiler | GCC 13 and Clang 18 with `-Wall -Wextra -Wpedantic -Wconversion -Wsign-conversion -Wshadow -Wold-style-cast -Wformat=2` and more, as errors | every build | conversions, shadowing, format strings, unused results |
| Linter and path analysis | clang-tidy 18 with a curated `.clang-tidy` | CI job `static-analysis`, `tools/static_analysis.sh` | CERT and Core Guidelines patterns, ownership, concurrency hazards, unchecked optionals |
| Second linter | cppcheck 2.13 | same job | a different parser and different heuristics; cheap |
| Semantic queries | CodeQL (`security-and-quality` queries) | CI workflow `codeql.yml`, weekly and on pull requests | data flow from inputs to dangerous sinks |

The sanitizers of Chapter 1 (AddressSanitizer, UndefinedBehaviorSanitizer, ThreadSanitizer)
are the dynamic counterpart: they see only paths that run, but what they report is real. Fuzzing,
later in this chapter, makes more paths run.

### A curated configuration

clang-tidy has several hundred checks, some contradicting others. "Enable everything" gives
thousands of findings and a team that ignores them. MiniDAQ's `.clang-tidy` enables whole
families that fit a safety-critical C++ code base (`bugprone-*`, `cert-*`,
`clang-analyzer-*`, `concurrency-*`, `cppcoreguidelines-*`, `misc-*`, `modernize-*`,
`performance-*`, `portability-*` and a dozen `readability` checks) and then disables, by
name, the checks that do not fit. Every exclusion has a reason in the file, next to it:

```{.yaml include=".clang-tidy" from="# Reasons for the exclusions above:" to="vfprintf. Their failures"}
```

`WarningsAsErrors: '*'` makes every finding fail the run, and `HeaderFilterRegex` restricts
reports to MiniDAQ's own headers, so third-party headers do not count.

### Triage of the first run

The first run over `minidaq/src` and `minidaq/apps` (18 translation units, about 5 minutes on
the 4-vCPU build machine with `-j 1`) reported 175 distinct findings:

| Check | Findings | Decision |
|---|---|---|
| `cppcoreguidelines-pro-type-vararg` | 32 | Disabled: `printf` output in the tools and `open`/`fcntl`; `-Wformat=2` checks the format strings. |
| `cppcoreguidelines-pro-type-union-access` | 26 | Suppressed in one region: the union in the `Expected` shim (Chapter 1) is guarded by `has_value_`; and one line where glibc declares `rusage` fields in unions. |
| `cert-err33-c` (unchecked return value) | 25 | Mixed: `fprintf` to the terminal removed from the checked list with a reason; `fwrite`, `fflush`, `fclose` and `snprintf` checked, or discarded with `(void)` and a reason. One was a real bug (below). |
| `cppcoreguidelines-pro-bounds-array-to-pointer-decay` | 13 | Disabled: `char` buffers handed to C APIs. |
| `cppcoreguidelines-special-member-functions` | 11 | Fixed: classes that deleted copying now also delete moving, explicitly. |
| `cert-err34-c` (`atoi`, `atof`, `atol`) | 11 | Fixed with `parse_number`. Real bugs. |
| `bugprone-assignment-in-if-condition` | 9 | Fixed: the stage loops' `(in = ch.receive())` became two plain statements. |
| `performance-unnecessary-value-param` | 7 | Fixed: `std::stop_token` and `PipelineConfig` by `const&`. |
| `cppcoreguidelines-pro-type-reinterpret-cast` | 7 | Suppressed with reasons: `sockaddr` casts behind one helper, SIMD loads in one region. |
| `readability-redundant-member-init` | 6 | Disabled: `time{}` tells the reader "zero" and stays right if the type changes. |
| `concurrency-mt-unsafe` | 6 | Fixed: `std::strerror` replaced by `std::system_category().message()`. |
| 12 other checks | 22 | 17 fixed, 5 suppressed with reasons. |

The second run, after the fixes, reported five new findings: an ownership report on the
`fclose` inside a deleter written during the fixes, three padding reports on the pipeline's
channels, which MiniDAQ pads on purpose against false sharing (that check is now disabled with
that reason), and a shift that the Clang Static Analyzer could not prove safe (below).
Path-sensitive checks can report differently after nearby code changes, which is one more
reason to run the whole set every time. The third run reported zero. The gate is
`tools/static_analysis.sh`, which runs clang-tidy and cppcheck and fails if either reports
anything:

```{.bash include="tools/static_analysis.sh" snippet="tidy"}
```

A gate needs to be tested like any other check: running the script with a fake clang-tidy
that prints one finding, and with one that fails without output, makes it exit 1 both times.

### Real bugs behind the findings

Most findings were style. These were not:

- **Ports and durations parsed with `atoi` and `atof`** in all four programs, as shown above.
- **An audit trail that lost records silently.** `JsonLinesAuditLog::append` ignored the
  results of `fwrite` and `fflush`. On a full disk every record after that point was lost,
  and nothing said so. `cert-err33-c` pointed at the lines; the fix is to check every call,
  count failures, and let the owner react. `minidaq_server` now reports the count and exits
  with status 1 if any record was lost. A test makes the disk full on demand: `/dev/full`
  accepts `open` and fails every write with `ENOSPC`.

```{.cpp include="minidaq/src/control/audit_log.cpp" snippet="append"}
```

- **A crash in `minidaq_ctl` on an unexpected response.** `bugprone-exception-escape`
  reported that `main` could throw. Following that lead found the line that reads the state,
  `response["status"].value(...)`, which throws `type_error` if the server's response has no
  `status` object, for example an error response from a newer server. The client now
  uses a JSON Pointer with a default, rejects any response that is not an object, and `main`
  catches what remains and exits with status 2.
- **Unchecked system calls in the control server.** Not reported by any check, but found
  while fixing the neighboring `cert-err33-c` findings: `eventfd` and `getsockname` results
  were not checked. Without the eventfd, `stop()` would wait up to a second for `poll` to
  time out. Reading the code around a finding is part of triage.
- **A shift the analyzer could not prove safe.** The latency histogram's constructor accepted
  any `sub_bucket_bits`; a value of 64 or more makes `1 << sub_bits` undefined. No caller
  passes such a value, but nothing prevented it. The constructor now clamps it to 1 to 20, and
  the analyzer's remaining report, which cannot see the constructor's invariant, is suppressed
  over the index functions with that reason.

cppcheck, run after clang-tidy was clean, reported 25 more findings. Sixteen said that
`Expected`'s converting constructors are not `explicit`, which is the point of the type
(suppressed for that file); six were style (`useStlAlgorithm`, suppressed globally with a
reason); one was a parser failure on the compile-time crystal table (suppressed for that
file); and two were real if small: local variables `clients` and `epoch` that shadowed member
functions of the same class. They were renamed. Two tools with different parsers find different things, and the second costs 4
seconds.

### Suppressions a reviewer can audit

A suppression is a decision, so it needs the same three things as any decision: what, where,
and why. MiniDAQ's policy (section 7 of the coding standard) allows three forms, from narrowest
to widest: a `NOLINT(check): reason` on one line, a `NOLINTBEGIN(check)` / `NOLINTEND`
region with the reason above it, and a disabled check in `.clang-tidy` with the reason in the
comment block. A bare `NOLINT` without a check name is not allowed, because it also hides the
findings of checks added next year. The cppcheck equivalent is
`tools/cppcheck-suppressions.txt`, one entry per suppression, each with a comment.

Two of MiniDAQ's suppressions show where judgment comes in. `cert-dcl58-cpp` flags the
`std::hash` specialization for `StrongId` as a modification of namespace `std`. The C++
standard explicitly allows specializing standard templates for program-defined types, and
clang-tidy 18 accepts a full specialization but flags a partial one, as a three-line test file
shows. That is a false positive, suppressed with a one-line explanation. `cert-err33-c`'s list
of checked functions, on the other hand, was edited to drop `fprintf`, `fputs` and `fputc`.
That hides real findings too: in Exercise 7.1 the same exclusion hides an ignored `fputc`
result on a file, which is a bug. Every suppression trades noise for blindness somewhere, and
review has to cover what it hides.

### CodeQL

CodeQL compiles the code under observation, builds a database of the program, and runs queries
over it, for example "data from `recv` reaches the size argument of `memcpy` without a bounds
check". It complements clang-tidy, which looks at one translation unit at a time.
`.github/workflows/codeql.yml` runs the `security-and-quality` query suite for C and C++ on
pushes to `main`, pull requests and once a week, and the results appear in the repository's
code scanning alerts. verify: this workflow was not executed in the book's build environment,
which has no GitHub runner; check its first run and triage its findings the same way.

::: box-mistakes
- **Turning on everything at once and suppressing the result in bulk.** A baseline of 2,000
  suppressed findings is a list nobody reads. Curate first, then fix to zero.
- **A bare `NOLINT`, or `// NOLINT` without a reason.** It hides every future check on that
  line and tells the reviewer nothing.
- **Running the analyzer only on changed files.** A header change can create findings in
  files that did not change. Run the whole set in CI; it takes minutes.
- **Fixing the finding, not the bug.** Casting a return value to `void` silences
  `cert-err33-c`. Only checking it fixes the audit trail.
- **Trusting a clean run.** Zero findings means zero *matched patterns*. The unchecked
  `eventfd` above was found by a person reading around a finding.
:::

## Fuzzing parsers and network inputs

### The intuition

A unit test checks the inputs you thought of. A fuzzer generates the inputs you did not.
Coverage-guided fuzzers like libFuzzer start from a few example inputs (the *seed corpus*),
mutate them (flip bits, insert bytes, splice two inputs), run the code under test on each
mutation, and keep every mutation that reaches code no earlier input reached. Over millions of
executions per minute the corpus grows into the shapes your parser understands, and then
beyond them. Built with AddressSanitizer and UndefinedBehaviorSanitizer, every out-of-bounds
read, use after free and signed overflow on the way becomes a crash with a report and a saved
input.

Fuzz every function that takes bytes or text from outside the process. In MiniDAQ that is the
packed-word decoder (bytes from a detector board), the 16-byte raw format of Chapter 2, the
configuration reader (files) and the control protocol (requests from the network). In the
scanner it will also be the UDP receiver of Chapter 9 and the list-mode reader of Chapter 12.

### A fuzz target with properties

A fuzz target is a function libFuzzer calls with each input. "Does not crash" is the weakest
useful property; a good target also checks what must be true for every input. Here is
MiniDAQ's decoder target:

```{.cpp include="fuzz/fuzz_decoder.cpp" snippet="target"}
```

It uses the first input byte to choose a chunk size, so the fuzzer also explores how bytes
arrive. It checks that every word is accounted for (decoded or counted as invalid), that every
decoded single is in range and encodes back to the same word, and that decoding the bytes in
chunks gives exactly the same singles as decoding the words in one call. That last property
compares two code paths through the decoder, and any difference is a bug even if neither path
crashes. The other targets follow the same pattern: `fuzz_raw16` checks the serialize round
trip; `fuzz_config` checks that a rejected configuration always says why and that an accepted
one survives `to_json` followed by `parse_config` unchanged; `fuzz_protocol` feeds bytes
through the line framer into `handle_request` and checks that every response is one line of
JSON with `api` and a boolean `ok`.

The targets live in `fuzz/` and build with the `fuzz` preset (Clang, `-fsanitize=fuzzer-no-link`
on all code so that the library's branches are instrumented, plus AddressSanitizer and
UndefinedBehaviorSanitizer). Each also becomes a 20-second CTest run from its seed corpus,
labeled `fuzz`, which CI runs for 60 seconds per target.

### Worked example: `6e688`

The first time the configuration target ran, as a 20-second CTest smoke run, it crashed within
seconds. The input was five characters, `6e688`, a number too large for a `double`.
nlohmann/json reports that as `json::out_of_range` (error 406), not as `json::parse_error`, and
`parse_config` caught only `parse_error`. The exception escaped, and a configuration file or a
control request containing a huge number terminated the program. A unit test would have needed
someone to think of exactly that case; the fuzzer needed seconds.

The fix catches the base class `json::exception`. The input went into the seed corpus
(`fuzz/corpus/config/regress-number-overflow`) so that every later fuzz run starts from it, and
into a unit test so that the bug cannot return unnoticed even where nobody fuzzes:

```{.cpp include="minidaq/tests/unit/test_config.cpp" from="TEST(Config, NumberOverflowIsAnErrorNotACrash)" to="=}"}
```

This is the workflow for every fuzzer crash: minimize the input (`-minimize_crash=1`), fix the
code, add the input to the corpus and to a unit test, and record the anomaly. Here it is also
recorded in the SOUP list, because it is a property of a third-party component that MiniDAQ
must handle.

### Campaigns

The CI smoke run catches regressions; finding new bugs takes longer runs. After the fix, the
three main targets ran on the 4-vCPU build machine, starting from the seed corpus (Clang
18.1.3, AddressSanitizer and UndefinedBehaviorSanitizer, `-timeout=5 -rss_limit_mb=2048`):
the configuration target for 30 minutes, then the decoder and the protocol for an hour each,
in parallel, each pinned to its own vCPU.

| Target, duration | Executions | Per second | Coverage, start to end | Corpus at end | Crashes |
|---------------------|-------------|---------|-------------|------------------|---------|
| Configuration, 30 min | 13,457,603 | 7,472 | 976 to 1,756 | 2,222 inputs, 503 KB | 0 |
| Decoder, 60 min | 102,580,804 | 28,486 | 83 to 101 | 85 inputs, 25 KB | 0 |
| Control protocol, 60 min | 3,432,666 | 953 | 1,468 to 2,412 | 3,605 inputs, 635 KB | 0 |


Coverage is libFuzzer's `cov:`, the number of instrumented edges reached. Summaries of the
logs are in `measurements/ch07/fuzz/`.

No crash in any of them. That is evidence, not proof: the decoder is small and its coverage
stopped growing after 7,755 executions, which suggests the fuzzer reached everything
reachable; the protocol and configuration targets were still finding new paths in their last
minutes. Report a campaign
with its numbers (duration, executions, coverage, corpus) and with what it does not cover:
here, for example, the server's socket handling, which no target feeds.

### Inputs that are not bytes

Untrusted input is not only a buffer. The `configure` command accepts a path to a real-time
profile, and before this chapter the service opened it with an `std::ifstream` and read it to
the end. A control client could name `/dev/zero` and the control thread would read until memory
ran out; it could name a FIFO and the thread would block forever. The fix opens the file
first, then asks every question of the open descriptor rather than of the name, which another
process could change in between (a time-of-check to time-of-use race, CERT FIO45-C):

```{.cpp include="minidaq/src/control/acquisition_service.cpp" snippet="read_small_file"}
```

The test `ProfilePathMustBeASmallRegularFile` tries `/dev/zero`, a directory and a missing
file. Exercise 7.4 adds symbolic links, FIFOs and world-writable files.

::: box-mistakes
- **A target that only checks for crashes.** Add the properties you can state: round trips,
  two implementations that must agree, counts that must add up.
- **Fuzzing without sanitizers.** Most memory errors do not crash. Exercise 7.2 shows five
  out-of-bounds reads that pass silently in a normal build.
- **Throwing away the crash input.** It is the best regression test you will ever get.
- **Fuzzing once.** Code changes. Keep a short run in CI and the corpus in the repository,
  and run long campaigns before releases.
- **Fuzzing the easy parser and not the dangerous one.** Start where bytes from outside the
  process first meet your code.
:::

## Compiler and linker hardening

### The intuition

Hardening flags do not make code correct. They make some classes of memory error harder to
exploit, or turn them into an immediate, clean stop instead of silent corruption. A stack
canary stops a function from returning through an overwritten return address. `_FORTIFY_SOURCE`
replaces `memcpy` and friends with versions that check the destination size when the compiler
knows it. Library assertions check `operator[]` on standard containers. Position-independent
executables let the kernel load the program at a random address. Read-only relocations stop an
attacker from redirecting calls through the global offset table. For a medical device, the
second effect is often the more important one: a defect that stops the acquisition with a
clear message is a much better failure than one that writes a wrong value into the data.

### The flags

`cmake/Hardening.cmake` applies them to every target when `MINIDAQ_HARDENING` is on (preset
`hardened`), because an unhardened object linked into a hardened program is the weak point:

```{.cmake include="cmake/Hardening.cmake" snippet="flags"}
```

| Flag | What it does | When it acts |
|---|---|---|
| `-fstack-protector-strong` | A random canary between local arrays and the return address, checked before returning | A linear stack buffer overflow; aborts at function return |
| `-fstack-clash-protection` | Touches each page of a large stack allocation in order | Stops a huge allocation from jumping over the guard page into other memory |
| `-D_FORTIFY_SOURCE=3` | `memcpy`, `strcpy`, `snprintf` and others become checked versions when the object size is known, including sizes known only at run time (level 3) | Overflow through a libc call; needs optimization |
| `-D_GLIBCXX_ASSERTIONS` | Bounds and precondition checks in libstdc++: `vector::operator[]`, `span::operator[]`, `front()` on an empty container, and more | Out-of-bounds access through standard containers; aborts at once |
| `-fPIE`, `-pie` | Position-independent executable | Address randomization of the program itself |
| `-z relro -z now` | Relocations resolved at start, then the table made read-only | Overwriting function pointers in the GOT |
| `-z noexecstack` | Non-executable stack | Code injected on the stack cannot run |
| `-fcf-protection=full` | Intel CET markings: indirect-branch tracking and shadow stack | Return- and jump-oriented programming, on CPUs and kernels that enforce CET |

### Check the binary, not the flags

A flag in a CMake file is a wish. Another file can override it, a toolchain can ignore it, and
one object compiled without it can remove a property like CET from the whole program.
`tools/check_hardening.py` reads the ELF files instead:

```{.python include="tools/check_hardening.py" snippet="checks"}
```

The `hardened` preset runs it as the test `build.hardening` on the five shipped programs. It
requires PIE, RELRO, immediate binding, a non-executable stack and, on x86-64, both CET
properties; it reports, but does not require, a canary and fortified calls, because a program
with no arrays on the stack legitimately has no canary.

Running it on the other presets is instructive. On the build machine (Ubuntu 24.04, GCC 13.3),
the plain `release` preset already passes: Ubuntu's GCC enables the stack protector, stack-clash
protection, `_FORTIFY_SOURCE`, PIE, RELRO, immediate binding and CET by default. The
`clang-release` preset fails: Ubuntu's Clang 18 enables PIE and RELRO but not immediate
binding, canaries, fortification or CET. The same source, two compilers from the same
distribution, two different security properties. That is why `Hardening.cmake` states every
flag explicitly instead of relying on the toolchain's defaults, and why the check reads the
binary.

### What it costs

Hardening is cheap in principle and occasionally expensive in a hot loop, so measure it on
the code you ship. Three GCC 13.3 builds of the same source, all `-O2`, on the 4-vCPU Xeon
VM at 2.3 GHz used throughout Part I: *none* (every protection switched off explicitly,
including the distribution defaults: `-fno-stack-protector -fno-stack-clash-protection
-fcf-protection=none -U_FORTIFY_SOURCE -fno-pie -no-pie -z lazy -z norelro`), *distro*
(the `release` preset, which inherits Ubuntu's defaults) and *hardened* (the `hardened`
preset). Five rounds, the three builds interleaved within each round so that drifts in the
VM hit all three alike; the table gives the median of five and, in brackets, the change
against *none*.

| Benchmark | none | distro | hardened |
|---|---|---|---|
| Decode 4,194,304 packed words (µs) | 15,126 | 16,051 [+6%] | 15,366 [+2%] |
| Energy filter, 4,096 singles, branchless (µs) | 4.47 | 4.47 [0%] | 4.58 [+3%] |
| Energy filter, 4,096 singles, AVX2 (µs) | 5.07 | 4.47 [−12%] | 4.41 [−13%] |
| Sort 4,096 singles, `std::sort` with a lambda (µs) | 30.6 | 30.2 [−1%] | 35.9 [+18%] |
| Histogram `record()` (ns) | 3.14 | 2.68 [−14%] | 3.29 [+5%] |
| Whole pipeline, batches of 4,096 (ms per run) | 97.6 | 97.3 [0%] | 88.4 [−9%] |

Most of these differences are inside the noise of this VM: the spread between the five runs
of one build is often 10% (the AVX2 filter on *none* ranged from 4.5 to 6.9 µs), and a
"hardened" pipeline that runs 9% faster is not an effect of hardening. One result is
outside the noise: the sort, where the fastest hardened run was slower than the slowest
unhardened one. A fourth build with only `-D_GLIBCXX_ASSERTIONS` added to the `release`
preset reproduced it (median 34.5 µs against 31.7 µs in a second set of five runs), so the
cost comes from the library's precondition checks, not from the compiler and linker flags.
Even there, the hardened sort costs about 36 µs per batch of 4,096 singles, 8.8 ns per
single: against the performance budget's 100 ns per single at 10 M singles/s and 33 ns at
30 M singles/s (`docs/performance-budget.md`, both rates assumption: confirm with team), the
margin is 11x and 3.8x, and the whole pipeline shows no measurable cost. verify: on the target hardware, where the noise is lower and the
cost may differ.

### Decision

ADR 0008 records the decision: shipped builds use the `hardened` preset; performance claims in
this book and in the performance budget are measured on it from now on, or say that they were
not; the cost is re-measured when the hot path changes. Whether `_GLIBCXX_ASSERTIONS` stays on
in the hot loops is a decision the measurements above support for MiniDAQ today, and that the
performance gate of Chapter 5 will revisit if it stops being true.

::: box-mistakes
- **Assuming the distribution's defaults.** They differ between GCC and Clang, between
  distributions, and between releases. State the flags.
- **Checking the flags instead of the binary.** One static library built without CET removes
  CET from the whole program; only the binary shows it.
- **`_FORTIFY_SOURCE` in a debug build.** It needs optimization and does nothing at `-O0`
  (GCC warns about it).
- **Treating hardening as a fix.** A canary that aborts the program has found a bug. Fix the
  bug; the canary is for the one you did not find.
- **Disabling hardening for speed without measuring.** Measure first; the cost is often
  inside the noise.
:::

## Dependency hygiene: pinned versions and the SBOM

### The intuition

Every third-party component in your product is code you ship and did not write. You need to
know exactly which version of it you shipped, be able to rebuild that exact version, find out
when a vulnerability is reported in it, and decide what that means for your product. In medical
device terms each such component is SOUP (software of unknown provenance), and a software bill
of materials (SBOM) is the machine-readable list of it.

### Pinning

`cmake/Dependencies.cmake` pins each dependency so that every build of a given MiniDAQ version
uses byte-identical sources: GoogleTest and Google Benchmark by full git commit hash (a tag can
be moved; a commit cannot), nlohmann/json by the SHA-256 of its release archive. A build
cannot silently pick up a new version, and an upgrade is a visible change in review.

### Generating the SBOM

`tools/make_sbom.py` reads the pins from `cmake/Dependencies.cmake` and writes a CycloneDX 1.5
JSON document. Facts the build file does not contain, such as the license and whether a
component ships, come from a table in the script:

```{.python include="tools/make_sbom.py" snippet="known"}
```

The script refuses to run if a dependency in the build file has no entry in the table. So a
new dependency cannot reach a release without someone stating its license and scope, and
`tools.sbom`, a unit test, fails until they do. GoogleTest and Google Benchmark are listed
with `"scope": "excluded"`: they are in the repository but not in the shipped programs.

Three properties make the SBOM trustworthy:

- **It is generated, not written.** It comes from the same file that the build uses, so it
  cannot drift from what was built.
- **It is validated.** `--validate` checks it against the CycloneDX 1.5 JSON schema, vendored
  in `tools/sbom/schemas/` with its source, license and hashes, so validation works offline
  and against a fixed schema. Feeding it a wrong `scope` and an invalid SPDX license id
  makes validation fail with both errors named, as it should.
- **It is reproducible.** With `SOURCE_DATE_EPOCH` set, two runs give byte-identical files,
  and the serial number is derived from the content. A release can be checked against its
  SBOM later.

The platform (the C++ runtime, the C library, the kernel) is not in this SBOM, because the
repository does not pin it; the target system does. Chapter 25 adds the platform definition,
and a product SBOM then has to cover both.

### The SOUP list

The SBOM says *what* is in the product. `docs/regulatory/soup-list.md` says *why* and *with
which requirements*: for nlohmann/json, the only SOUP item in the shipped programs, it records
the exact identification, supplier, license, which MiniDAQ items use it, why it was chosen
(ADR 0004), the functional and performance requirements MiniDAQ places on it, how MiniDAQ
verifies its use, the anomaly found by fuzzing, and the procedure and record of the
known-anomaly review. The development-only items (test and benchmark frameworks, the schemas,
the compilers and analyzers) are listed separately with lighter records, because a defect in
them can hide a defect in MiniDAQ even though they do not ship.

::: box-mistakes
- **Pinning by tag or branch.** Tags can be moved and branches always move. Pin commits or
  archive hashes.
- **A hand-written SBOM.** It is wrong by the second release. Generate it from the build.
- **Leaving out components that "are only headers".** Header-only libraries are compiled into
  your binary; they are in the product.
- **An SBOM without a process.** A list of components is useful only if someone checks it
  against vulnerability reports, on a schedule and on demand, and records the result.
:::

::: box-regulated
Security is now part of medical device safety, and both the standards and the regulators ask
for evidence of it across the life cycle.

- **A secure development process.** IEC 81001-5-1 (health software security activities in the
  product life cycle) expects, among other things, secure coding practices, security
  verification including static analysis and testing of inputs, and management of third-party
  components. The coding standard, the static analysis gate and its suppression records, the
  fuzz targets and campaign reports of this chapter are that evidence for MiniDAQ.
  verify: which edition and which parts your notified body and your company's QMS reference.
- **SBOM.** In the United States, section 524B of the Federal Food, Drug, and Cosmetic Act
  requires manufacturers of "cyber devices" to provide an SBOM in premarket submissions,
  including commercial, open-source and off-the-shelf components, and FDA's premarket
  cybersecurity guidance describes what it expects alongside it. In the EU, the MDR's general
  safety and performance requirements on IT security and MDCG 2019-16 guide the same work.
  verify: whether your scanner is a cyber device in the 524B sense and which markets apply
  (assumption: confirm with team).
- **SOUP.** IEC 62304 expects each SOUP item to be identified, its requirements stated, and
  its known anomalies evaluated (Chapter 14). The SBOM and the SOUP list are two views of the
  same pins and must agree.
- **Tool confidence.** Static analyzers, fuzzers and compilers produce evidence; how much you
  must show about the tools themselves is the subject of tool qualification (Chapter 20).
- **This chapter is not a security risk assessment.** Threat modeling and security risk
  management (Chapter 17) decide which controls the product needs. The practices here are
  necessary for most products and sufficient for none.
:::

::: box-askteam
1. Which coding standard does the DAQ team follow (CERT, MISRA C++:2023, an in-house set)?
   Where are the deviations recorded, and which tools enforce it in CI?
2. Which static analyzers run today, on which code, and what is the policy for suppressions?
   Is there a baseline of accepted findings, and who reviews it?
3. Are the parsers of detector data, configuration and network commands fuzzed? Where are the
   corpora, and how are crashes tracked?
4. Which hardening flags do release builds use, and is the result checked in the binary? Has
   anyone measured their cost on the acquisition path?
5. How is the SBOM produced for submissions and for customers, who monitors vulnerability
   reports for the components in it, and how fast must a relevant one be assessed?
:::

## Exercises {.unnumbered}

**Exercise 7.1 (M): Enable clang-tidy with a curated check set and get a legacy file to zero
findings.** *Goal:* triage every clang-tidy finding in a small piece of legacy code (option
parsing and a record file), fix each one without an unjustified suppression, and make the
behavior tests pass, which catch bugs that clang-tidy does not report. *Starter:*
`exercises/ch07/e1_tidy_zero/` (15 findings with MiniDAQ's `.clang-tidy`). *Acceptance:*
`tests/tidy_clean.py` reports 0 findings (CTest `ch07/e1_tidy_zero/<variant>/clang-tidy`);
`tests/test_legacy_tool.cpp` passes: strict, all-or-nothing option parsing, a full disk
reported by `close()`, no crash when the file did not open; every `NOLINT` names its check
and gives a reason. *Time:* 2 hours. MiniDAQ itself is at zero: run `tools/static_analysis.sh`
after every change you make in this chapter.

**Exercise 7.2 (M): Fuzz a packet parser, then fuzz the single decoder for one hour.**
*Goal:* write a libFuzzer target with properties for a readout packet parser, fix every crash
it finds, keep each crash input as a regression test; then run `fuzz_decoder` for one hour and
report the campaign. *Starter:* `exercises/ch07/e2_fuzz_packets/` (a parser that trusts its
header). *Acceptance:* `tests/test_packet.cpp` passes, including every input in
`tests/crashers/`; the CTest `ch07/e2_fuzz_packets/<variant>/fuzz` passes; your notes give
duration, executions, executions per second, coverage and corpus size of the decoder run, any
crash and its fix, and what the run does not show. *Time:* 2 hours plus one hour of fuzzing.

**Exercise 7.3 (E): Generate an SBOM (CycloneDX) for MiniDAQ, then review a change to it.**
*Goal:* generate and validate MiniDAQ's SBOM and explain its fields; then write `sbom_diff.py`,
which lists added and removed components and changes of version, license, scope and hash
between two SBOMs. *Starter:* `exercises/ch07/e3_sbom_diff/` (Python). *Acceptance:*
`tests/test_sbom_diff.py` passes against the real SBOM: identical SBOMs give no changes, an
upgrade is one version change (not a removal and an addition), the other kinds of change are
reported, the exit status is 0 or 1. *Time:* 1 hour.

**Exercise 7.4 (M, extra): Read a file whose name you did not choose.** *Goal:* a function
`read_untrusted_file(path, max_bytes)` that cannot be made to block, to read forever, or
to follow a planted symbolic link. *Starter:* `exercises/ch07/e4_untrusted_path/`.
*Acceptance:* `tests/test_untrusted_file.cpp` passes: small files read, the size limit exact,
`/dev/zero` and directories rejected (the `/dev/zero` case runs in a child process with a
memory limit and a deadline), a symbolic link and a world-writable file rejected, a FIFO
rejected within 2 seconds, every error naming the path. *Time:* 1.5 hours.

**Exercise 7.5 (E, extra): A strict duration parser.** *Goal:* `parse_duration("250ms")` that
accepts exactly the documented grammar, computes exact nanoseconds with integer arithmetic,
and refuses to overflow. *Starter:* `exercises/ch07/e5_strict_duration/` (a `strtod` version).
*Acceptance:* `tests/test_duration.cpp` passes: five units, exact fractions (`4.1s` is
4,100,000,000 ns, which the starter gets wrong by one), sixteen malformed inputs rejected,
overflow rejected exactly at the boundary. *Time:* 1 hour.

## MiniDAQ milestone: static analysis, fuzzing and SBOM in CI {.unnumbered}

::: box-milestone
**Goal.** Every change to MiniDAQ is checked by curated static analysis at zero findings, its
untrusted-input parsers are fuzzed in CI, release builds are hardened and verified in the
binary, and every build can produce a validated SBOM that agrees with a SOUP list.
**Start:** tag `ch06`. **End:** tag `ch07`.
:::

1. Add `.clang-tidy`, `tools/cppcheck-suppressions.txt` and `tools/static_analysis.sh`, and fix
   or suppress (with reasons) every finding in `minidaq/src` and `minidaq/apps`. Add
   `minidaq/include/minidaq/core/parse_number.hpp` with `test_parse_number.cpp`, and replace
   every `atoi`, `atof` and `atol`.
2. Make the audit trail report lost records (`failed_writes()`), with `test_audit_log.cpp`
   using `/dev/full`, and make `minidaq_server` exit with status 1 if any were lost.
3. Add `fuzz/` with the four targets, their seed corpora and CTest smoke runs; the
   `MINIDAQ_BUILD_FUZZERS` option and the `fuzz` preset. Fix what they find, with regression
   tests (`Config.NumberOverflowIsAnErrorNotACrash`).
4. Read the `rt_profile` file through the descriptor checks of `read_small_file`, with
   `ProfilePathMustBeASmallRegularFile`.
5. Add `cmake/Hardening.cmake`, the `MINIDAQ_HARDENING` option, the `hardened` preset and
   `tools/check_hardening.py` as the test `build.hardening`; ADR 0008.
6. Add `tools/make_sbom.py`, the vendored schemas in `tools/sbom/schemas/` and the test
   `tools.sbom`; `docs/regulatory/soup-list.md` and `docs/coding-standard.md`.
7. Extend `.github/workflows/ci.yml` with the `hardened` preset and the jobs
   `static-analysis`, `fuzz-smoke` and `sbom`, and add `.github/workflows/codeql.yml`.

**Definition of done.** `ci/run_all.sh` is green on all six presets (debug, clang-release,
gcc-cxx23, hardened, asan-ubsan, tsan), `ctest --preset fuzz -L fuzz` passes, and
`tools/static_analysis.sh` reports nothing. `build.hardening` passes on the `hardened` preset.
`tools/make_sbom.py --validate` passes and two runs with the same `SOURCE_DATE_EPOCH` give
identical files. A one-hour `fuzz_decoder` campaign and a one-hour `fuzz_protocol` campaign
ran without a crash, and their numbers are recorded in `fuzz/README.md`. Tag `ch07`.

## Check yourself {.unnumbered}

1. What is the difference between a coding guideline violation and a defect? Give one example
   of each from this chapter that is not also the other.
2. Why does a medical device need an SBOM? Who uses it, for what, and when?
3. `std::atoi("70000")` stored in a `std::uint16_t`: what value results, and why would the
   server not report an error? Which two things does `parse_number` check that `atoi` does not?
4. Name three forms of suppression in MiniDAQ's policy, from narrowest to widest. Why is a
   bare `// NOLINT` not allowed?
5. Removing `fputc` from `cert-err33-c`'s list removed noise from MiniDAQ. What did it hide in
   Exercise 7.1, and what should catch that instead?
6. What properties does `fuzz_decoder` check besides "does not crash"? Why is comparing chunked
   and unchunked decoding a strong property?
7. Why did `parse_config("6e688")` terminate the program, and what four things were done after
   the fuzzer found it?
8. Why must `read_small_file` check the file through the descriptor (`fstat`) rather than the
   name (`stat`)? What do `O_NONBLOCK` and the `max + 1` read protect against?
9. Your release build passes `check_hardening.py` with GCC but not with Clang, from the same
   distribution. What does that tell you, and what do you change?
10. What does `-D_GLIBCXX_ASSERTIONS` do, and what did it cost on MiniDAQ's hot path? How would
    you decide whether to keep it?
11. Why is the SBOM generated from `cmake/Dependencies.cmake` instead of written by hand, and
    what makes `make_sbom.py` refuse to run?
12. Why are GoogleTest and Google Benchmark in the SOUP list at all, and why with lighter
    records than nlohmann/json?
13. A one-hour fuzz campaign ran without a crash. What exactly can you claim, and what can you
    not?

## Summary {.unnumbered}

- A coding standard is useful when every rule has a reason and something enforces it.
  `docs/coding-standard.md` cites CERT and Core Guidelines rules by identifier and names the
  check, test or review behind each rule.
- clang-tidy with a curated configuration reported 175 findings on code that passed six
  chapters of tests; triage fixed most, disabled three checks and suppressed the rest line by
  line, each with a reason. Behind them were real bugs: ports parsed with `atoi`, an audit
  trail that lost records silently, a client that crashed on an unexpected response.
- cppcheck, run second, found two more things in 4 seconds. Different tools, different
  findings; `tools/static_analysis.sh` gates on both.
- libFuzzer targets with properties cover the decoder, the raw format, the configuration
  reader and the control protocol. The configuration target found a crash (`6e688`) in
  seconds; the fix, the corpus entry and a unit test followed.
- Untrusted input includes file names: open first, check the descriptor, limit the size.
- Hardening flags are stated explicitly in `cmake/Hardening.cmake` and checked in the binary,
  because GCC and Clang from the same distribution differ. Their measured cost on MiniDAQ's
  hot path is in this chapter and in ADR 0008.
- Dependencies are pinned by commit or hash; the CycloneDX SBOM is generated from the pins,
  validated against the schema, and reproducible; the SOUP list states requirements and the
  anomaly review.

## Further reading {.unnumbered}

- SEI CERT C++ Coding Standard and SEI CERT C Coding Standard, Software Engineering Institute,
  Carnegie Mellon University, <https://wiki.sei.cmu.edu/confluence/display/seccode>.
- MISRA C++:2023, *Guidelines for the use of C++17 in critical systems*, MISRA, 2023
  (licensed; <https://misra.org.uk/>).
- Bjarne Stroustrup and Herb Sutter (editors), *C++ Core Guidelines*,
  <https://isocpp.github.io/CppCoreGuidelines/>.
- clang-tidy documentation, <https://clang.llvm.org/extra/clang-tidy/>; Cppcheck manual,
  <https://cppcheck.sourceforge.io/>; CodeQL documentation, <https://codeql.github.com/docs/>.
- libFuzzer documentation, <https://llvm.org/docs/LibFuzzer.html>; Andreas Zeller, Rahul
  Gopinath, Marcel Böhme, Gordon Fraser and Christian Holler, *The Fuzzing Book*,
  <https://www.fuzzingbook.org/>.
- OpenSSF, *Compiler Options Hardening Guide for C and C++*,
  <https://best.openssf.org/Compiler-Hardening-Guides/Compiler-Options-Hardening-Guide-for-C-and-C++.html>.
- CycloneDX specification, <https://cyclonedx.org/specification/overview/>; NTIA, *The Minimum
  Elements for a Software Bill of Materials (SBOM)*, 2021.
- IEC 81001-5-1:2021, *Health software and health IT systems safety, effectiveness and
  security, Part 5-1: Security, Activities in the product life cycle*.
- FDA, *Cybersecurity in Medical Devices: Quality System Considerations and Content of
  Premarket Submissions* (guidance; verify: the current revision); MDCG 2019-16, *Guidance on
  Cybersecurity for medical devices*.
