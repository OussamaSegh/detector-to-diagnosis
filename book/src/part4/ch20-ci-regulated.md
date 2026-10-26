# Continuous integration for regulated software {#ch20}

::: box-why
By Chapter 19, MiniDAQ's evidence is made by machines: CI builds six configurations, runs some
six hundred tests, analyzes the code, fuzzes the parsers and scans the SBOM, and the release
checks add coverage, a soak and a signed test report. A reviewer who reads that evidence trusts
three things you have not yet shown: that each gate can fail, that the program the tests ran is
the program that ships, and that the tools which produced the evidence were fit for it. IEC 62304
asks for a development plan that names the tools and keeps them under configuration management,
ISO 13485 asks for the validation of software used in the quality system, and both ask that a
release can be repeated. This chapter turns MiniDAQ's pipeline into evidence that holds up: a
reproducible shipped build, a release package bound to its evidence by a hash, a tool list with
the reasons each tool is trusted, a self-test that shows every gate can fail, and a performance
gate that runs on the shared machines CI actually has.
:::

**A day in the life.** Monday morning, the 0.4 review is on Friday. CI is red on the commit you
pushed on Saturday, in two of six presets, and your machine says everything passes. The log says
`system.readout (Failed)` and nothing else: no assertion, no output, because the pipeline runs
`ctest` without `--output-on-failure`. You run the test twenty times on your machine; it passes
twenty times. You load all four CPUs and run it again; it passes. By noon you have compared what
you can see of the two machines, and one number differs: `net.core.rmem_max`, 4 MiB on yours,
212,992 bytes on GitHub's runners, Ubuntu's default. You set yours to the default and the test
fails every time, waiting 30 seconds for datagrams the kernel dropped before the server could read
them. The test measured the machine. The fix is three lines and a step in the workflow. The
problem report asks the harder question: the acquisition PC is installed with that setting, the
test depended on it, and no document said the test environment had to have it.

## Learning objectives {.unnumbered}

After this chapter you can:

1. Describe a CI pipeline as a set of gates, each with a claim, a pass criterion and a record,
   and decide which run on every change, which on a schedule and which before a release.
2. Show that a gate can fail, by planting known faults and checking that the gate fails for the
   planted reason and passes on correct code.
3. Make a C++ build reproducible, find what makes two builds differ, and check reproducibility by
   building twice in different places.
4. Package a release so that its programs, debug information, SBOM, build description and
   evidence are bound together by hashes, and verify a package.
5. Classify the tools of a pipeline by what a defect in them can do, and state proportionate
   reasons for confidence in each, as IEC 62304 and ISO 13485 expect.
6. Compare performance on a shared CI runner by interleaved A/B runs, and measure the false
   alarm rate of the comparison.

## Prerequisites and estimated time {.unnumbered}

Chapter 5 (benchmarks and the regression gate), Chapter 7 (static analysis, sanitizers,
hardening and the SBOM), Chapter 14 (the development plan), Chapter 16 (document control, change
requests and CAPA), Chapter 18 (coverage and mutation testing) and Chapter 19 (system tests and
the test report). Reading: about 3 hours. Exercises: 6 to 8 hours. Milestone: 4 hours. In the
10-week schedule at the front of the book, this chapter is in week 7, with Chapters 19 and 21 to
23; if time is short, do Exercises 20.1, 20.2 and 20.5 and leave the extras.

## A pipeline is a set of gates

### The intuition

A gate is a check that stops a change: the build with warnings as errors, the tests, the static
analysis, the document checks. Each gate makes a claim ("the change introduces no compiler
warning"), has a pass criterion that a machine can decide, and leaves a record that a person can
read later. A pipeline is the set of gates and the order in which they run. Its value for a
regulated product is not that it is automatic. It is that every change meets the same criteria,
and that the records show it did.

Three properties decide whether a gate's record is evidence:

- **The gate ran on the change.** A gate configured in a workflow that never starts leaves no
  record at all, and the absence of red looks like green. Chapter 14's MDQ-PR-014 was exactly
  that: the performance gate waited a whole Part for a runner that did not exist.
- **The gate can fail.** A static analyzer pointed at an empty directory, a comparison of a file
  with itself and a sanitizer that is not linked in all pass. A gate that has never been seen to
  fail has not been shown to work.
- **The gate tested what ships.** Tests run on a debug build say little about a release build
  made with other flags, on another day, from another checkout, unless you can show that the
  build is repeatable and the package is the build.

Most of this chapter is about the second and third property. The first is a matter of reading
the records: the release record of Chapter 14 cites the run of each check, not the
configuration.

### MiniDAQ's gates

The gates run at three rates. Fast gates run on every push; slow ones run on a schedule or when
the files they protect change; the slowest run before a release on the reference machine.

| Gate | Claim | Runs | Record |
|---|---|---|---|
| Build, six presets | no warning, two compilers, four configurations | each push | job log |
| Tests, six presets | all tests pass, no sanitizer report | each push | job log |
| Static analysis | clang-tidy and cppcheck report nothing | each push | job log |
| Tool versions | the runner's tools are those of the tool list | each push | job log |
| Reproducible build | two builds of the shipped programs are equal | each push | `repro.txt` |
| Fuzz, SBOM, scan, documents | Chapters 7, 16 and 17 | each push | logs, artifacts |
| Performance A/B | the change is not slower than its parent | code changes | `gate.txt` |
| Gate self-test | every gate above can fail | see below | `gate-selftest.md` |
| Release checks | coverage, soak, system test, fuzzing, stress, speed | release | one file each |
| Release package | it verifies and matches the one CI makes | each tag | two archives |

The per-push gates are the jobs of `ci.yml`; a failed test prints its output, and CI keeps
`repro.txt` for 90 days. The A/B comparison is `perf.yml`, which keeps the raw results with
`gate.txt`; the self-test is `gates.yml`. The release checks run on the reference machine
(`tools/release_checks.sh`) and write one file per check to `measurements/release-X.Y.Z/`; the
release package is the two archives and their SHA-256.

The order inside a run matters less than you might think, because GitHub runs the jobs in
parallel; what matters is that nothing merges or ships until every gate of its rate is green.
In a team that works through pull requests, branch protection makes the per-change gates
required checks, so a red or missing gate blocks the merge. MiniDAQ is pushed straight to
`main` by one developer, so the rule is the development plan's instead: nothing is tagged until
CI on the tagged commit is green (MDQ-PR-016).

### The environment is part of the test

The day-in-the-life failure is MiniDAQ's problem report MDQ-PR-020, and its lesson reaches
further than one test. Two readout system tests send their stream as fast as the sender can
(`minidaq_send --speed 0`), and the server asks the kernel for an 8 MiB receive buffer. The kernel
grants at most `net.core.rmem_max`, silently; the server reads back what it got and says so in its
detector description, as Chapter 9 made it do. On the reference machine that is 4 MiB and the
burst fits. On GitHub's runners it is 212,992 bytes; in the debug and tsan builds, which read the
socket more slowly, the kernel dropped datagrams of the burst, the server counted them as lost, and
the test waited for datagrams that would never come. Four presets passed and two failed, which
looked like a race in the code and was a property of the machine.

The correction has three parts, and each generalizes:

1. **The test checks its precondition.** Before it sends, the test reads the receive buffer the
   server was granted and fails at once if it is below 4 MiB, naming the setting:

   ```text
   AssertionError: the UDP receive buffer is 212992 B, the readout tests need at least 4194304 B:
   set net.core.rmem_max as on the acquisition PC (system test plan, section 3)
   ```

   It fails rather than skips, for the reason Chapter 19 gave for missing programs: a skipped
   test on the wrong machine is a test that silently never runs.
2. **The test plan states the environment.** The system test plan's section 3 now lists the
   setting, with its source: ADR 0009 makes `rmem_max` part of the acquisition PC's
   installation, so the test environment must have it too.
3. **CI makes its environment match, and keeps the evidence.** The test jobs set the value
   before they build:

   ```yaml
   - name: Tune the network stack as the acquisition PC is installed (ADR 0009)
     run: sudo sysctl -w net.core.rmem_max=4194304
   ```

   and `ctest` runs with `--output-on-failure`. Without it, the failing run's log held only the
   test's name. A CI log is a record; the output of a failed test is the part of it that
   explains the failure, and the only copy is the one the job prints.

::: box-mistakes
- **Retrying until green.** A rule that reruns a failed test hides every defect that fails less
  than always: a test that fails 30% of the time passes 97% of the time with two retries
  (Exercise 20.5). MDQ-PR-019 failed in one run of the coverage report before it was understood,
  and in every run under load; a retry would have kept it shipped.
- **A quarantine without an owner.** Taking a flaky test out of the gate is sometimes right, but
  only as a recorded decision: a problem report, who fixes it, by when, and the test still running
  and reporting.
- **`continue-on-error` on a gate.** A job that cannot fail the run is a report, not a gate. Say
  which it is, in the workflow and in the development plan.
- **Logs that do not explain.** A red job whose log does not say why costs a day of guessing. Print
  the output of failures, keep artifacts of what a failure leaves (crash inputs, reports), and
  keep them long enough to investigate.
- **An environment nobody wrote down.** If a test needs a kernel setting, a locale, a time zone
  or a free port range, the test plan says so and the test checks it.
:::

## Can each gate fail?

### The intuition

Chapter 18 measured tests by mutation: plant a defect and see whether a test fails. Chapter 19
gave the system tests negative controls: an impostor server that must be refused, a narrower
energy window that the comparison must find. The same idea applies to the pipeline. For each
gate, plant a fault it exists to catch and run it: it must fail, and fail for the planted reason.
Run it on the unchanged code first: it must pass, or a gate that fails on everything would
"catch" every fault.

That gives four outcomes, and the two in the middle are the interesting ones:

- **caught**: the gate passed on correct code and failed with the fault, with output that names
  the fault;
- **NOT CAUGHT**: the gate passed with the fault in place;
- **failed for another reason**: the gate failed, but its output does not name the planted fault.
  Something else broke on the way, perhaps the fault itself made the build fail before the
  analyzer ran, and the gate has not shown it can see what it claims to see;
- **fails on correct code**: the control failed, so the run says nothing about the fault.

### MiniDAQ's gate self-test

`tools/gate_selftest.py` checks out a commit into a temporary worktree, builds what the gates
need, and runs each fault in turn: it applies the fault's edits (each anchored on text that must
occur exactly once, so a fault cannot silently stop applying when the code moves), runs the gate,
restores the checkout and decides:

```{.python include="tools/gate_selftest.py" snippet="verdict"}
```

The faults are data. Here are four of the fifteen:

```python
    Fault("unit", "unit tests",
          "the slicing-by-8 CRC reads byte 6 twice instead of bytes 6 and 7",
          [(CRC, "t[0][byte_at(data, i + 7)]", "t[0][byte_at(data, i + 6)]")],
          ["sh", "-c",
           f"cmake --build {DEBUG} --target minidaq_unit_tests >/dev/null && "
           f"ctest --test-dir {DEBUG} -R '^Crc32[.]' --output-on-failure"],
          r"Crc32\.SlicingBy8MatchesTheBytewiseLoop\w* \.+\*+Failed"),
    Fault("tidy", "static analysis: clang-tidy", "a pointer initialized with 0",
          [(CRC, CRC_ANON,
            "[[maybe_unused]] const std::uint32_t* const kNoTable = 0;\n\n" + CRC_ANON)],
          ["tools/static_analysis.sh", TIDY], r"modernize-use-nullptr"),
    Fault("document", "document control",
          "a controlled document changed without a new version",
          [("docs/regulatory/verification/stp.md",
            "This plan says how", "This plan, changed, says how")],
          ["python3", "tools/design_file.py", ".", "--check", "--since", "HEAD"],
          r"stp\.md: changed since HEAD but still version"),
    Fault("tsan", "ThreadSanitizer", "two threads increment one int",
          [], ["sh", "-c", "clang++-18 -g -O1 -fsanitize=thread selftest/p.cpp -o selftest/p"
                           " && selftest/p"],
          r"data race", ...),
```

The faults cover the build (a warning in a library source), the unit tests (a defect in the
CRC's fast path), the system tests (the client exiting with 0 when the server refuses its
token), both analyzers, the layering rule, the trace matrix (a test that loses the tag of the
only requirement it verifies), the requirements' form, the SOUP list, document control, the
test-wait rule of CAPA-0001, the hardening check, the performance gate (the pipeline benchmark
20% slower in a copy of the baseline), and the two sanitizers. Its run on the reference machine:

| Fault | Gate | Control | With the fault | Verdict |
|---------|-------------------------|-------|-----------|-------|
| `warning` | build: warnings are errors | pass | fail | caught |
| `unit` | unit tests | pass | fail | caught |
| `system` | system tests | pass | fail | caught |
| `tidy` | static analysis: clang-tidy | pass | fail | caught |
| `cppcheck` | static analysis: cppcheck | pass | fail | caught |
| `layers` | architecture: layers | pass | fail | caught |
| `trace` | trace matrix | pass | fail | caught |
| `srs` | requirements in testable form | pass | fail | caught |
| `soup` | SOUP list | pass | fail | caught |
| `document` | document control | pass | fail | caught |
| `waits` | test waits (CAPA-0001) | pass | fail | caught |
| `hardening` | hardening of the shipped programs | pass | fail | caught |
| `perf` | performance regression gate | pass | fail | caught |
| `asan` | AddressSanitizer | pass | fail | caught |
| `tsan` | ThreadSanitizer | pass | fail | caught |

All 15 faults were caught for the planted reason, on commit `74a98ed` in 12 minutes
(`measurements/ch20/gate-selftest.md`).

Three details are worth copying.

- **Each expectation names the fault.** The `unit` fault must make *its* test fail, `Crc32.
  SlicingBy8MatchesTheBytewiseLoop...`, not just any test; the `tidy` fault must be reported as
  `modernize-use-nullptr`. While the self-test was written, the trace-matrix fault first reported
  a different problem: the self-test's own source contained the literal tag it plants, and the
  trace tool, which scans `tools/` too, counted the self-test as a test of SRS-CFG-001. The
  expectation caught that, and the tag is now spelled in two pieces.
- **The controls run.** For a gate that checks generated input, the control is a correct input
  of the same kind: a hardened program for the hardening check, the baseline compared with
  itself for the performance gate, a race-free program for ThreadSanitizer.
- **It is slow, so it runs when it matters.** It builds MiniDAQ and runs the static analysis
  three times, about 12 minutes on the reference machine. A gate's ability to fail
  changes when the gate, its tools or its inputs change, so the `gates` workflow runs when
  `tools/`, the CI, the analyzer configuration, the CMake modules or the regulatory files change,
  once a week for new tool versions on the runners, and for each release tag.

The self-test is itself a tool whose output is evidence, so it has tests of its own:
`tools/test_gate_selftest.py` checks the four verdicts and that every fault still applies to
exactly one place. Exercise 20.3 goes one step further and tests a self-test against broken
versions of its gate: a self-test with one fault per rule misses three of seven broken gates.

::: box-mistakes
- **A fault that tests nothing.** A fault whose edit no longer applies, because the code it
  anchors on moved, plants nothing and the gate passes; make a missing anchor an error.
- **Accepting any failure.** A planted fault that breaks the build makes every later gate fail
  "for another reason". Check what the failure says.
- **Faults only where it is easy.** One fault per gate shows that the gate runs. The edges of what
  it promises need faults of their own: the other file type, the limit just past the threshold,
  the case its pattern almost matches.
:::

## Reproducible builds

### The intuition

The development plan's release record says how a release was built, "so the build can be
repeated". Repeated is checkable only if two builds of the same commit can be compared, and that
needs them to be identical: if every build differs a little, a difference that matters (another
compiler, a modified dependency, a tampered build machine) hides among the ones that do not. A
build is reproducible when the same sources, the same toolchain and the same instructions give
the same bytes, on another day, in another directory, on another machine with the same tools.

Builds differ for a short list of reasons, and you will meet most of them in C++:

- **Paths.** `__FILE__` expands to the path the compiler was given, and CMake passes absolute
  paths; debug information records the compilation directory and every source and header file.
- **Time.** `__DATE__` and `__TIME__`, timestamps in archives, a build date the program prints.
- **Order.** Files listed from a directory in the order the file system returns them; a hash
  table's iteration order in a code generator.
- **The environment.** The locale, the time zone, the user name, the host name, the number of
  cores (when it decides how the work is split).
- **The toolchain.** Another compiler or linker version gives other code. That difference is not
  noise: it is a change of a tool whose output ships, and the build should record it.

### MiniDAQ's shipped build

The experiment is short. Check the same commit out twice, in two directories of different names
and lengths, build the release preset in each, and compare every program:

```text
same ./minidaq/apps/minidaq_server       same ./benchmarks/bm_pipeline
same ./minidaq/apps/minidaq_ctl          ...
DIFF ./minidaq/tests/minidaq_unit_tests  DIFF ./lib/libgtest.a
```

The shipped programs were already identical, because the release build has no debug
information and MiniDAQ's code does not use `__FILE__`; the test programs differ because
GoogleTest's assertions record `__FILE__`. Then add `-g`, which a shipped build should have,
because Chapter 21 debugs core dumps from the field with it, and the server differs too: its
debug information holds the checkout's absolute path 50 times. GCC and Clang can rewrite those
paths with `-ffile-prefix-map`, which covers `__FILE__` and the debug information at once:

```{.cmake include="cmake/Reproducible.cmake" snippet="maps"}
```

With both maps the two servers are identical again. The order of the two maps matters, and the
two compilers disagree about why: when both match a file in the build directory, GCC 13 uses the
last map given and Clang 18 the longest prefix. With the build directory's map second, both
choose it. You find such details by testing them, not by reading the manuals once.

The option `MINIDAQ_REPRODUCIBLE` is on in the `hardened` preset, the build that ships, which
now also has `-g`. It is off elsewhere, because two tools rely on absolute paths: the coverage
report maps profiles to files by their paths, and two exercise tests found their fixture
directories through `__FILE__`. Those now get the directory from a compile definition instead,
which is the honest way to say where a test's data lives.

`tools/repro_check.sh` makes the check repeatable. It adds two git worktrees of the commit in
directories of different names, configures the `hardened` preset in each with tests and
benchmarks off, builds the two shipped programs, packages each build with the release tool of
the next section, and compares the two archives byte for byte:

```{.bash include="tools/repro_check.sh" snippet="twice"}
```

The dependencies are fetched in each checkout, so their paths differ too. On the reference
machine:

```text
d36ea88d571d8bd1de18005dbc9e04530a92a83137929b0fc3304920...  first  minidaq-0.3.0-447cc4ac4713.tar
d36ea88d571d8bd1de18005dbc9e04530a92a83137929b0fc3304920...  second minidaq-0.3.0-447cc4ac4713.tar
identical: the product archive is reproducible
programs:
  minidaq_server   build ID fbac0e5e14d5136e331b90b76f78ce66deed4cdd  sha256 82557e6b6c46...
  minidaq_ctl      build ID 614b9137303f8fb7a6d4c00a412c323a69edd51a  sha256 0bed97367fce...
```

The check takes about a minute on the reference machine (`measurements/ch20/repro-local.txt`).
Its first run, here and on GitHub, failed after it had printed "identical": the line that lists
the programs was a Python one-liner inside single quotes whose escaped quotes reached Python
literally, and the script runs with `set -e`. In the same push the `perf` workflow stopped with
"Permission denied", because `tools/perf_ab.sh` had been committed without its executable bit.
Neither path had a test, because the tests called `tools/release_bundle.py` directly and nothing
ran the two scripts. Both are problem report MDQ-PR-021: the listing became a tested subcommand
of `release_bundle.py`, and the tool list check now fails for a script that is not executable.
A check's own output path needs a test too, and a new gate's first run is its first test.

CI runs the same check on every push (job `reproducible-build`) and keeps `repro.txt`. Its
programs, built on a GitHub runner from the same commit, compare with the reference machine's
like this:

| File | Reference machine | GitHub runner |
|---|---|---|
| `bin/minidaq_server` | `82557e6b6c46...` | `82557e6b6c46...` |
| `bin/minidaq_ctl` | `0bed97367fce...` | `0bed97367fce...` |
| `debug/minidaq_server.debug` | `5acb0afe71a1...` | `5acb0afe71a1...` |
| `debug/minidaq_ctl.debug` | `f3c7038ece42...` | `f3c7038ece42...` |
| `sbom/minidaq.cdx.json` | `43e10818551a...` | `43e10818551a...` |
| `BUILDINFO.json` | `8bcd75c63b96...` | `e0267aa94655...` |

That is commit `d1073fb` on both (`measurements/ch20/repro-local-d1073fb.txt` and
`repro-github-d1073fb.txt`). The programs and their debug files are the same bytes, built by
the same GCC 13.3.0, binutils 2.42 and glibc 2.39 on a different CPU. The archives differ in one
file, the one that says so: `BUILDINFO.json` records CMake 3.28.3, Ninja 1.11.1 and Python
3.13.17 on the reference machine, and CMake 3.31.6, Ninja 1.13.2 and Python 3.12.3 on the runner.
None of them is in the programs. That is the useful definition of reproducible for a release:
the same source and the same compiler give the same programs, and the record of the build says
which tools differed. A package that hid the difference would be identical and less honest.

::: box-mistakes
- **Removing debug information to make builds equal.** It works and costs you the core dumps of
  Chapter 21. Map the paths and split the debug information off instead.
- **`SOURCE_DATE_EPOCH` for a date nobody needs.** GCC honors it for `__DATE__`, but a build date
  in a program invites the belief that two builds of one commit differ. Print the version and the
  commit.
- **Comparing compressed archives.** Two gzip files of the same content differ when the zlib
  versions differ. Compare what you control, or the uncompressed archive.
- **Calling a difference noise.** A program that differs between two builds of one commit differs
  for a reason. Find it before you accept it.
:::

## The release package and its evidence

### Two archives, one hash

The development plan's section 8 asks for the release to be archived with its evidence. Until
now that meant a source zip, the book files and the SBOM next to a release record that cites
files in `measurements/`. `tools/release_bundle.py` makes the shipped part of it a package that a
reviewer, or an installer, can check:

- **The product archive**, `minidaq-VERSION-COMMIT.tar`: `bin/` with `minidaq_server` and
  `minidaq_ctl` without their debug information; `debug/` with the debug information of each, in
  its own file; `sbom/minidaq.cdx.json`; `BUILDINFO.json`, which records the version, the commit,
  the commit's time, the preset, the compiler flags, the options that change the programs, the
  commands to rebuild it, the version of each tool whose output is in it (compiler, CMake, Ninja,
  binutils, C library, OpenSSL, Python), and the build ID and SHA-256 of each program; and
  `MANIFEST.sha256`, one line per file in the format `sha256sum -c` reads.
- **The evidence archive**, `minidaq-VERSION-COMMIT-evidence.tar`: the output directory of
  `tools/release_checks.sh` for that commit, its own manifest, and `PRODUCT.sha256`, the hash of
  the product archive it is evidence for.

The product archive contains only what the commit and the toolchain determine: no build time, no
host name, no user. That is what makes it reproducible, and its SHA-256 becomes the identity of
the release, written into the evidence archive and the release record. The evidence archive is not
reproducible and does not need to be: it records one execution of the checks, with its dates and
its machine, and it points at the product by hash.

Splitting the debug information keeps the shipped programs small and the field's core dumps
debuggable:

```{.python include="tools/release_bundle.py" snippet="split"}
```

`--only-keep-debug` writes the debug sections to their own file; `--strip-debug` removes them
from the program, keeps the symbol table for readable stack traces, and adds a debug link, the
debug file's name with its CRC-32. The build ID, a hash the linker writes into every program,
is the same in the program and its debug file; a debugger finds the right debug file by either.
For MiniDAQ the server is 834 KB without its debug information and its debug file
18.2 MB; for the client the two are 275 KB and 4.9 MB. The product archive of commit `447cc4a`
is 24.2 MB, uncompressed, of which 23.1 MB are the debug files
(`measurements/ch20/package-contents.txt`).

The archive itself must be deterministic too. Python's `tarfile` records the owner, the file
times and the order in which you add files, so the tool sets all three:

```{.python include="tools/release_bundle.py" snippet="deterministic_tar"}
```

The archive is not compressed: two machines with different zlib versions compress the same
bytes differently, and the identity of a release should not depend on that.

### Verification

`release_bundle.py verify` checks a product archive against itself and, given the evidence
archive, the evidence against the product:

- every file is in the manifest with its SHA-256, and nothing is missing or added;
- the archive is named after the version and commit in `BUILDINFO.json`;
- each program has the SHA-256 that `BUILDINFO.json` records, the same build ID as its debug
  file, a debug link that names that file with the right CRC, and no debug information;
- the evidence names this product's SHA-256, holds the required records, ran on this commit with
  a clean tree, has every release check passed and a passing system test report.

A manifest inside the archive protects against damage, not against someone who changes a file
and its manifest line together; the product's hash, recorded outside the archive in the release
record and the evidence, closes that gap (Exercise 20.1). `tools/test_release_bundle.py` packages
two small programs and damages the result in six ways: a changed byte, an added file, a missing
SBOM, the two debug files swapped with the manifest "repaired" to match, evidence of another
product, and evidence of a dirty tree, a failed check or without a test report. Each must be
refused. The swapped debug files are the instructive case: the manifest is consistent, and only
the build IDs show that the debug information belongs to another program.

## Confidence in tools

### What the standards ask

IEC 62304 asks the development plan to name the tools, methods and standards of development
(clause 5.1.4) and to put the supporting items that can affect the software under configuration
management (clause 5.1.10) (verify: clause numbers against the 2015 amendment). ISO 13485:2016
asks for documented procedures to validate software used in the quality management system,
proportionate to the risk of its use (clause 4.1.6), and for the validation of software used for
monitoring and measurement (clause 7.6). Neither prescribes how. ISO/TR 80002-2 gives guidance
for the validation of such software, and the FDA's guidance on computer software assurance for
production and quality system software argues for effort proportionate to risk, with
unscripted and scripted testing where each fits (verify: the current status of the FDA
guidance). IEC 61508, which is not a medical standard, gives the clearest vocabulary for
software tools, and MiniDAQ borrows its three classes:

- **T1**: the tool's output does not reach the product or the evidence, or a defect in it would
  be noticed by what follows (an editor, version control);
- **T2**: a verification tool; a defect in it can fail to reveal a defect, but cannot add one (a
  test framework, an analyzer, a coverage tool);
- **T3**: the tool's output is part of the product (a compiler, a linker, the build system).

The class says what a defect in the tool could do, and so how much confidence you need. It does
not say how to get it. For off-the-shelf tools, confidence comes mostly from use and from
redundancy: a compiler used for a whole distribution, two compilers that must both pass the same
tests, an analyzer whose findings are checked by hand. For in-house tools, which nobody else
uses, it comes from tests, as for any code, and from a demonstration that the tool reports a
failure when there is one.

### MiniDAQ's tool list

`docs/regulatory/verification/tools.json` lists 23 tools at the end of this chapter (Chapter 21
adds a 24th, the postmortem tools): three of class T3 (GCC, binutils, CMake with Ninja), eighteen
of class T2 and two of class T1 (git, and the AI assistant whose output enters the product only
through the same review and gates as any change; Part IX returns to it). For each it records the
use, what a defect would do, the reasons for confidence, the evidence in the repository, and
`shown_to_fail`: the self-test fault, test, path or problem report that shows the tool reporting
a failure. One entry:

```json
{"id": "TL-14",
 "name": "Performance gate (tools/perf_gate.py, tools/perf_suite.sh, Google Benchmark 1.9.1)",
 "kind": "in-house", "class": "T2", "version": "the commit",
 "use": "Fails a change that makes a gated benchmark significantly slower.",
 "failure": "A regression not reported; noise reported as a regression.",
 "confidence": [
  "Exercise 5.3's acceptance tests run against tools/perf_gate.py (test tools.perf_gate).",
  "The gate self-test plants a 20% slowdown; A/A runs measure the false alarm rate."],
 "evidence": ["exercises/ch05/e3_perf_gate/tests/test_perf_gate.py", "tools/gate_selftest.py"],
 "shown_to_fail": "perf"}
```

Writing the list found two gaps, which is what such a list is for. `tools/perf_gate.py` was "the
same code as the solution of Exercise 5.3", but only the solution was tested: the tool could have
drifted from it unnoticed. The exercise's acceptance tests now run against the tool too
(`tools.perf_gate`). And the release tool of the previous section had no tests at all until its
entry asked what showed it could fail.

`tools/check_tools.py` keeps the list honest. As the test `docs.tools` it checks that every T2
and T3 tool has reasons and evidence that exist, and that every `shown_to_fail` names something
real, and it regenerates the table `tools.md` that a reviewer reads. In CI it also compares the
installed versions with the recorded ones:

```{.python include="tools/check_tools.py" snippet="environment"}
```

A GitHub runner image is updated every week or two. When it brings a new compiler or analyzer,
that is a change to the tools, and this step fails until someone records the new version in the
tool list, which is the moment to ask whether anything else must be repeated. The patterns are as
strict as the use: the compiler's version exactly, CMake's at least the one the presets need.

::: box-regulated
What the regulated setting adds to this chapter's examples:

- The development plan names the tools and the pipeline's checks, and says which run on every
  change and which before a release. A check is evidence only when its run is cited.
- Tools whose output is in the product or is evidence are identified with their versions,
  controlled like the code, and assessed for the confidence their use needs; the assessment is a
  record (ISO 13485 clause 4.1.6). An in-house test tool is software, with tests and a review.
- A changed tool is a change: a new compiler, analyzer or runner image is recorded, and its
  effect on the evidence is assessed before the next release relies on it.
- The release can be repeated: the build is described completely, a second build gives the same
  product, and the release record holds the product's hash. The archive keeps product and
  evidence for the lifetime of the device plus the retention period of the quality system.
- A failure in CI is a finding like any other. It is investigated, and if its cause is in the
  test or its environment, that is a problem report too (MDQ-PR-020); "flaky" is not a cause.
- Cloud CI is a supplier's service. Its runners, images and retention of logs are part of what
  the quality system relies on, and a release's evidence is kept in the manufacturer's own
  archive, not only in the CI service.
:::

## Performance on shared machines

### Why the baseline gate cannot run in CI

Chapter 5's gate compares a run with a baseline recorded on the reference machine, and it holds
only there. A GitHub runner is a virtual machine on hardware you do not choose: the next job may
run on another CPU model, next to another tenant, at another clock speed. A baseline from the
reference machine says nothing about a runner, and a baseline from one runner says little about
the next. That is why the old `perf.yml` asked for a dedicated self-hosted runner, and why it never
ran (MDQ-PR-014).

What a single runner can do is compare two things on itself. `tools/perf_ab.sh` takes the build
of the change and the build of its parent, both made in the same job, and runs the gated
benchmarks of both, interleaved round by round:

```{.bash include="tools/perf_ab.sh" snippet="interleave"}
```

Each round runs two repetitions of each side, A then B in odd rounds and B then A in even ones,
so that a drift of the machine during the job (a neighbor that starts, a CPU that heats up)
affects both sides alike. The decision is Chapter 5's gate, unchanged: a benchmark regressed if
its median speed dropped by more than 5% and a one-sided Mann-Whitney test gives `p < 0.01`. The
`perf` workflow runs it on every push that changes code or the build, and keeps the raw results.

### How often does it cry wolf?

A gate on noisy machines must be judged by its false alarm rate: how often does it fail when
nothing changed? The answer is a measurement, an A/A comparison of a build with itself. On the
reference machine, 15 A/A jobs of the release build of `23c40ab` against itself, five rounds
each, raised one false alarm: `BM_HistogramRecord` 5.4% slower with `p = 0.0045`. In another job
the same benchmark came out 13.5% slower, with `p = 0.026`, which the gate let pass because the
evidence was too weak (`measurements/ch20/aa-local.txt`). One alarm in 15 jobs is a rate between
0.2% and 32%, the exact interval of Exercise 20.5: too few jobs to say more than "not rare
enough to ignore". The reference machine is itself a virtual machine, with the caveats of
Chapter 5.

On GitHub's runners (2 vCPUs each), three A/A jobs started by hand with the head
as base, and one A/B job of a push that changed no benchmarked code, raised no alarm. Their 23
median ratios all stayed within 3.2% of 1, and 19 of them within 1.0%: inside one job a runner
was steadier than the reference machine. Four clean jobs bound the false alarm rate only below 60%,
so the record grows with every push, and the rate is measured, not assumed.

The four jobs did not even measure the same things. The three started by hand listed six
benchmarks, the push job five: `BM_EnergyFilter/3/50/0/4096`, the AVX-512 kernel of Chapter 5,
was missing. The jobs had run on different CPUs, an AMD EPYC 9V74 with AVX-512 and an AMD EPYC
7763 without it, where the benchmark reports an error instead of a result, and the gate passed
over errored benchmarks in silence. Whether a change was checked for a regression of that kernel
depended on the machine the job happened to get, and nothing said so (MDQ-PR-023). The gate now
lists every benchmark that did not run, with its message, and `tools/perf_ab.sh` stops if the two
sides ran different benchmarks. Whether the AVX-512 kernel matters at all depends on the
acquisition PC's CPU (assumption: confirm with team).

Interleaving removes the bias a drifting machine adds, but not the spread: a machine that drifts
by 20% during the job widens each side's samples, and a rank test of two wide samples sees only
large changes. Exercise 20.4 simulates it. With 2% drift per run, running all of A and then all
of B gives a false alarm in every job and hides a real 10% regression in every job; interleaving
removes the false alarms but, compared unpaired, finds the regression in less than 1% of jobs; a
paired comparison of the two sides within each round finds it in every job, but needs at least
ten rounds, because a sign test of five rounds cannot reach a p-value below 1/32. Which of the two
is better on GitHub's runners is a question for measurement, and the A/A runs are the first half
of it.

The same holds for a speed test among the unit tests. Exercise 5.2's acceptance test asked for
at most 18 ns per single, a third of the starter's time on the reference machine, where the
solution takes about 13 ns. On a GitHub runner, while this chapter was written, it took 18.2 ns
and failed the `gcc-cxx23` job once; the next run passed. That is a flaky test, and as
Exercise 20.5 argues it got a problem report (MDQ-PR-022), not a retry. The test now times a
copy of the starter's algorithm in the same run and asks for a third of its time, which is what
the exercise meant from the start. A budget in nanoseconds is a claim about one machine.

It failed once more, a day later, in the `hardened` job: 14.49 ns against a budget of 14.43 ns,
the reference at 43.3 ns, a ratio of 2.99 (MDQ-PR-034). The comparison was right and the margin
was not: a solution three times faster on the reference machine is about three times faster on
a runner too, so a test that asks for exactly the goal fails by chance half the time it lands
there. The test now asks for twice the starter's speed, which leaves the solution a margin of
50% everywhere it has run and still fails the starter, and the exercise keeps three times as its
goal. A relative criterion needs a margin as much as an absolute one does.

The baseline gate on the reference machine stays where CAPA-0004 put it, in the release checks:
it is the one that compares against the performance budget. The A/B gate answers a different
question, "did this change make things slower", and answers it on every change instead of once a
release.

::: box-askteam
1. Which CI system does the team use, which runners (cloud or the team's own), and who may change
   the pipeline? Is the pipeline's configuration reviewed like code?
2. Which checks are required before a merge, and which only before a release? Where is that
   written down?
3. How are the tools of the build and the tests validated, and is there a tool list with
   versions? Who decides when a new compiler version may be used?
4. Is the shipped build reproducible, and has anyone checked? Which machine builds a release, and
   who has access to it?
5. What is the release package, how are its contents identified and signed, and where are the
   package and its evidence archived, for how long?
6. What does the team do with a test that fails now and then? Is there a quarantine, and how is
   it recorded?
7. How are debug symbols of released versions kept, so that a core dump from a site can be read?
:::

## Exercises {.unnumbered}

**Exercise 20.1 (E): A manifest that notices.** *Goal:* write the manifest of a release package
and its verification, reporting every changed, missing and added file at once. *Starter:*
`exercises/ch20/e1_manifest/` (three functions to write). *Acceptance:* `tests/test_manifest.py`
passes: `sha256sum -c` reads the manifest, the same files give the same bytes, each kind of
damage and several at once are found, malformed and escaping manifests are refused. Then answer
in `NOTES.md` what the manifest protects against and what not. *Time:* 45 minutes.

**Exercise 20.2 (M): Make a build reproducible.** *Goal:* make a small program's build give the
same bytes from two checkouts, built in different seconds, while it keeps its debug information
and its version. *Starter:* `exercises/ch20/e2_reproducible/starter/` (the clock, `__FILE__` and
debug paths each make the builds differ). *Acceptance:* `tests/test_reproducible.py` builds the
project twice and checks the output, the absence of build paths, the debug information and the
identity of the two programs. Then answer in `NOTES.md` why not `SOURCE_DATE_EPOCH`, and what a
debugger now needs. *Time:* 60 minutes.

**Exercise 20.3 (M): Test the gate, then test the test.** *Goal:* write a self-test for a small
source-file gate, and make it strong enough that none of seven broken versions of the gate passes
it. *Starter:* `exercises/ch20/e3_gate_selftest/` (the correct tree and the record of a fault).
*Acceptance:* `tests/test_selftest.py` passes: the real gate catches every fault for its reason,
the four verdicts, and every broken gate leaves a fault not caught. Then answer in `NOTES.md`
which broken gate your first faults missed. *Time:* 60 minutes.

**Exercise 20.4 (H, extra): A/B on a machine that drifts.** *Goal:* find out what the order of
benchmark runs does to a regression gate on a drifting machine, and build a paired comparison that
sees a regression through the drift. *Starter:* `exercises/ch20/e4_ab_drift/` (the machine's
model and the alarm rates). *Acceptance:* `tests/test_ab.py` passes: sequential runs raise false
alarms and hide a regression, interleaving removes the false alarms, pairing finds the regression
with ten rounds, five are too few. Then answer in `NOTES.md` what this says about
`tools/perf_ab.sh`. *Time:* 2 hours.

**Exercise 20.5 (M): How sure is "not flaky"?** *Goal:* put numbers on a flaky test: an exact
interval for its failure rate, the reruns needed to claim it is below 1%, whether a change made it
worse, and what retries hide. *Starter:* `exercises/ch20/e5_flaky_triage/` (the binomial
distribution). *Acceptance:* `tests/test_flaky.py` passes: hand-computed intervals, 299 reruns,
the MDQ-PR-019 comparison and the hiding probability of two retries. Then answer in `NOTES.md`
what one retry would have done to MDQ-PR-019. *Time:* 60 minutes.

## MiniDAQ milestone: a reproducible release and a pipeline shown to work {.unnumbered}

::: box-milestone
**Goal.** The shipped build is reproducible and checked on every push; a release is a product
archive bound to its evidence by a hash; every tool is in a tool list with the reasons it is
trusted and its version checked; every gate is shown to fail; performance is compared on CI's own
runners; the environment problem the system tests met in CI is corrected and recorded.
**Start:** tag `ch19`. **End:** tag `ch20`.
:::

1. Make the readout system tests check their receive buffer, set `rmem_max` in CI, run `ctest`
   with `--output-on-failure`, state the setting in the system test plan, and record MDQ-PR-020.
2. Add `MINIDAQ_REPRODUCIBLE` and `-g` to the `hardened` preset; replace the two uses of
   `__FILE__` in exercise tests with `MINIDAQ_EXERCISE_TESTS_DIR`.
3. Add `tools/release_bundle.py` with its tests and `tools/repro_check.sh`; run the check and
   record it in `measurements/ch20/`.
4. Write the tool list and `tools/check_tools.py`; register `docs.tools` and the version check in
   CI.
5. Add `tools/gate_selftest.py` with its tests and the `gates` workflow; run it and record the
   report.
6. Replace `perf.yml` with the A/B workflow and `tools/perf_ab.sh`; record A/A runs on the
   reference machine and on GitHub.
7. Write change request CR-0006 before the code is committed, and update the development plan to
   version 7, the SOUP list to version 5 and the design file (clause 4.1.6).
8. Add Exercises 20.1 to 20.5.

**Definition of done.** `ci/run_all.sh` is green on all six presets and static analysis reports
nothing; every GitHub job, including `reproducible-build` and the version check, is green on the
tagged commit; the gate self-test catches every fault; the two builds of `repro_check.sh` are
identical; MDQ-PR-020 to MDQ-PR-023 are closed; every starter of the chapter fails. Tag
`ch20`.

## Check yourself {.unnumbered}

1. What three properties must a gate's record have to be evidence? Give an example of a gate that
   lacked each.
2. A test passes on your machine and fails in CI. List what you compare first, and explain why
   "flaky" is not a cause.
3. Why does a test that depends on a kernel setting fail rather than skip when the setting is
   missing?
4. What are the four outcomes of a planted fault, and why does "failed for another reason" not
   count as caught?
5. Why run each gate on the unchanged code before planting the fault?
6. Name four sources of difference between two builds of the same commit, and the fix for each.
7. Why does `-g` make MiniDAQ's server differ between two checkouts, and how does
   `-ffile-prefix-map` fix it without losing the debug information?
8. What is in the product archive, and what is deliberately not in it? Why is it not compressed?
9. Why can a manifest inside an archive not show that the archive was tampered with, and what
   does?
10. What do the classes T1, T2 and T3 say about a tool, and what do they not say?
11. Why are in-house tools held to more evidence than a compiler?
12. A runner image brings a new clang-tidy. What happens in MiniDAQ's pipeline, and what should
    you decide before the next release?
13. Why can a baseline from the reference machine not gate performance on a cloud runner? What
    does interleaving fix, and what does it not?
14. A test failed 3 times in 100 runs. What can you say about its failure rate, and how many clean
    runs would show a fix brought it below 1%?

## Summary {.unnumbered}

- A pipeline is a set of gates with claims, pass criteria and records. Its records are evidence
  when the gate ran on the change, can fail, and tested what ships.
- The test environment is part of the test: a test checks its preconditions and fails when they
  are missing, the test plan states them, and CI prints the output of every failure
  (MDQ-PR-020).
- A gate is shown to work by planting a fault it must catch, checking that it fails for that
  reason, and that it passes on correct code; `tools/gate_selftest.py` does it for fifteen faults.
- A reproducible build gives the same bytes from the same sources and tools. For MiniDAQ the
  shipped programs differed only through paths in the debug information, and two prefix maps
  removed the difference; a GitHub runner then built the same programs, byte for byte.
- A new check is software too: on their first run the new jobs found two defects in themselves
  and one flaky exercise test, and a gap in the performance gate (MDQ-PR-021 to MDQ-PR-023).
- A release is a product archive that contains only what the commit and the tools determine,
  identified by its SHA-256, and an evidence archive bound to it by that hash; both are verified.
- Every tool whose output is in the product or is evidence is listed with its class, the reasons
  it is trusted and what shows it can fail, and its version is checked on every CI run.
- Performance is compared on shared runners by interleaved A/B runs of a change and its parent;
  the false alarm rate is measured, not assumed, and pairing the rounds pays when the machine
  drifts.
- Retries hide defects. A test that fails sometimes is a problem report with a measured failure
  rate, not a rerun.

## Further reading {.unnumbered}

- IEC 62304:2006+A1:2015, *Medical device software: Software life cycle processes*, clause 5.1
  (software development planning, including tools and supporting items) and clause 8
  (configuration management).
- ISO 13485:2016, *Medical devices: Quality management systems*, clauses 4.1.6 (validation of
  software used in the quality management system) and 7.6.
- ISO/TR 80002-2:2017, *Medical device software, Part 2: Validation of software for medical
  device quality systems*.
- FDA, *Computer Software Assurance for Production and Quality System Software*, guidance
  (verify: the final version and its date).
- IEC 61508-3:2010, *Functional safety of electrical/electronic/programmable electronic
  safety-related systems, Part 3: Software requirements*, subclause 7.4.4 (requirements for
  support tools), and IEC 61508-4, the definitions of the tool classes T1 to T3.
- The Reproducible Builds project, reproducible-builds.org: the definition of a reproducible
  build, the `SOURCE_DATE_EPOCH` specification, and the documentation of common causes.
- GCC manual, "Options for Debugging Your Program" and "Options Controlling the Preprocessor":
  `-ffile-prefix-map`, `-fdebug-prefix-map` and `-fmacro-prefix-map`, gcc.gnu.org.
- The GDB manual, "Debugging Information in Separate Files", and the GNU Binutils manual of
  `objcopy`, for the options `--only-keep-debug`, `--strip-debug` and `--add-gnu-debuglink`.
- Jez Humble and David Farley, *Continuous Delivery*, Addison-Wesley, 2010. The deployment
  pipeline, and why the binary that was tested must be the binary that is released.
- Titus Winters, Tom Manshreck and Hyrum Wright (editors), *Software Engineering at Google*,
  O'Reilly, 2020, chapter 23, "Continuous Integration": gates at different rates, and flaky
  tests.
- John Micco, "Flaky Tests at Google and How We Mitigate Them", Google Testing Blog, 2016.
