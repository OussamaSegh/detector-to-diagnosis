# How to use this book {.unnumbered #how-to-use}

This book teaches you to build the data acquisition software of a PET scanner in modern C++, and
to build it the way regulated medical device software must be built. It is practice-heavy: every
chapter grows MiniDAQ, a simulated PET data acquisition system with its own regulated software
file, and every code listing is compiled and tested from the companion repository.

## How a chapter is built {.unnumbered}

Every chapter has the same shape:

1. **Why it matters**, a short scene from the daily work, the learning objectives, and the
   prerequisites with an estimate of the reading, exercise and milestone time.
2. **Sections** that go from the intuition to a worked example. Boxes mark common mistakes, what
   changes in regulated work, and the questions worth asking your own team.
3. **Exercises**, marked E (easy), M (medium) or H (hard). Each has a goal, a starter, acceptance
   tests and a time estimate. Every starter fails its acceptance tests until you have done the
   work; the solutions manual and the repository hold a solution that passes them.
4. **A MiniDAQ milestone** with a definition of done.
5. **Check yourself** questions, a summary, and the references.

## Choosing your path {.unnumbered}

The time estimates add up to a lot of work, more than most readers will do in one pass. Two
paths through each chapter help:

- **The core path** is the reading and the milestone. It is what you need to follow the next
  chapters and to keep MiniDAQ complete.
- **The full path** adds every exercise. Do the exercises in the order the chapter lists them;
  several chapters say which ones to keep when time is short, and the ones marked H and the
  extras can wait.

If you read selectively, protect Parts I and II and Chapter 14 (IEC 62304): together they are
the data acquisition system, its C++ and the regulated life cycle that every other chapter
builds on. Keep a list of the exercises you skip. A real system you work on later is often the
best reason to come back to one.

Answer the Check yourself questions from memory a day or two after you read a chapter, and keep
a short learning log: the numbers you measured on your own machine, the questions you could not
answer, and what to revisit.

## The companion repository {.unnumbered}

Everything the book builds is in the companion repository,
<https://github.com/OussamaSegh/detector-to-diagnosis>. Each release of the book also comes with
a zip of the code at the same version on the download page,
<https://oussamasegh.github.io/detector-to-diagnosis/>. This section takes you from nothing to a
working MiniDAQ and your first exercise; do it before Chapter 1.

### What you need {.unnumbered}

MiniDAQ is Linux software: it uses Linux interfaces (real-time scheduling, CPU affinity, `eventfd`,
batched socket receives, the kernel's network counters, systemd), so it builds and runs on Linux
only. Ubuntu 24.04 is the reference, on x86-64 or on 64-bit ARM (aarch64): every command in the
book was run there. Another recent distribution works with its own package names. A virtual
machine works for everything; the one thing it changes is the timing measurements of Chapters 4,
5 and 23, whose numbers then include the hypervisor (the shapes of the results still show). On
Windows, use WSL2 with an Ubuntu 24.04 distribution. Plan for 4 GB of memory and 15 GB of disk.

**On a Mac with Apple silicon.** Work in an Ubuntu 24.04 virtual machine for 64-bit ARM, which runs
at native speed. Two free ways to get one:

- **OrbStack** (<https://orbstack.dev>, free for personal use at the time of writing): install it,
  then in the macOS terminal run `orb create ubuntu:noble minidaq` once, and `orb -m minidaq`
  each time to open a shell in the machine.
- **UTM** (<https://mac.getutm.app>): create a virtual machine with "Virtualize", Linux, and the
  Ubuntu 24.04 Server image for ARM64 from <https://ubuntu.com/download/server/arm>.

Give the machine at least 4 CPUs and 8 GB of memory if your Mac has it to spare, keep the
repository in the machine's own file system (your Linux home directory) rather than in a folder
shared with macOS, which builds much more slowly, and edit with any editor that can open files in
the machine (VS Code's remote extensions can). Then follow the Linux instructions below in the
machine's shell. What changes on ARM is small and the book points it out where it matters:

- The SIMD listings of Chapter 5 (AVX2 and AVX-512) are x86-64 instructions. On ARM, MiniDAQ uses
  its portable branchless filter instead, and the SIMD tests check that the fallback gives the
  same results; read the listings, and expect your own measurements to show the fallback.
- Exercise 4.5 reads the x86 time-stamp counter. On ARM its solution returns 0, as the exercise
  asks, and its two timing tests report themselves as skipped.
- The control-flow protection of the hardened build (Chapter 7, `-fcf-protection`, Intel CET)
  exists only on x86-64, so the hardening check does not ask for it on ARM.
- Inside a virtual machine, `perf` may not see the processor's hardware counters. If `perf stat`
  prints `<not supported>` for cycles, use the software event `-e cpu-clock`, which works
  everywhere.
- Every benchmark number in the book was measured on an x86-64 server. Yours will differ; compare
  the ratios and the shapes, not the absolute numbers.

Install the compilers and build tools once:

```bash
sudo apt-get install -y build-essential cmake ninja-build git python3 \
  clang-18 clang-tidy-18 libclang-rt-18-dev libssl-dev
```

A few chapters use one more tool, and say so in their prerequisites: `linux-tools-generic` for
`perf` (Chapter 5), `gdb` (Chapter 21), `iverilog` for the firmware listing (Chapter 24,
optional). Everything else, such as GoogleTest and nlohmann/json, is
downloaded by CMake at a pinned version the first time you configure.

### Get the code and build it {.unnumbered}

```bash
git clone https://github.com/OussamaSegh/detector-to-diagnosis.git
cd detector-to-diagnosis
cmake --preset debug                 # configure into build/debug
cmake --build --preset debug         # compile MiniDAQ, its tools and the tests
ctest --preset debug -LE starter     # run every test; all must pass
```

The first configure takes a few minutes because it fetches the dependencies; a full build takes a
few more. Other presets build the same code in other ways and are introduced where the book needs
them: `release` for measurements, `asan-ubsan` and `tsan` for the sanitizers (Chapters 2 and 3),
`coverage` (Chapter 18). `ci/run_all.sh` runs every configuration the continuous integration
runs, which is what you do before you call a change finished.

### Run MiniDAQ {.unnumbered}

The programs are in `build/debug/minidaq/apps/`, and each prints its usage when it is given
`--help`. A first session with the acquisition server and its command-line client, in two
terminals:

```bash
# terminal 1: the server, with an audit trail of every command
build/debug/minidaq/apps/minidaq_server --audit audit.jsonl

# terminal 2: configure a two-second run, start it, wait for its end, read the status
build/debug/minidaq/apps/minidaq_ctl configure minidaq/configs/short-run.json
build/debug/minidaq/apps/minidaq_ctl start
build/debug/minidaq/apps/minidaq_ctl wait configured 30
build/debug/minidaq/apps/minidaq_ctl status
```

The client finds the server's access token by itself (Chapter 17 explains how). Stop the server
with Ctrl+C. Do not worry if MiniDAQ is larger than the chapter you are reading: the repository's
main branch holds the finished system, and the chapter tags described next show it as it grows.

### Follow MiniDAQ chapter by chapter {.unnumbered}

The repository has one git tag per chapter: `ch00` is the empty starting point, and `chNN` is
the repository at the end of Chapter NN. To work on a chapter's milestone from the end of the
chapter before it, make a branch of your own at that tag:

```bash
git switch -c my-ch08 ch07     # Chapter 8's milestone, starting from the end of Chapter 7
# ... your work, with commits ...
git diff ch08 -- minidaq/      # compare with the book's milestone when you are done
```

Your branch keeps your work; `git switch main` brings back the finished system. Book releases are
tagged `book-vX.Y.Z`, and the code of a release matches the book of the same version.

### Do the exercises {.unnumbered}

Every exercise lives in `exercises/chNN/eM_name/` with four parts: `README.md` states the goal
and the acceptance criteria, `starter/` is where you work, `tests/` holds the acceptance tests,
and `solution/` holds a solution that passes them. The starters are not built by default, because
their tests fail until you have done the work. Build them in a directory of their own:

```bash
cmake --preset debug -B build/mine -DMINIDAQ_BUILD_STARTERS=ON
cmake --build build/mine
ctest --test-dir build/mine -L starter -R ch01/e1     # your work: red until it is done
ctest --test-dir build/mine -L solution -R ch01/e1    # the reference solution: always green
```

Edit the files in `starter/`, rebuild, and run the starter's tests again until they pass. The
tests are the acceptance criteria, so do not change them to make them pass. A few exercises
are written in Python or are measurements; their README says how to run them. The solutions
manual, a separate book, explains every solution: the key points, and the wrong answers people
commonly give. Read it after you have tried, not before.

### Measurements, documents and the book itself {.unnumbered}

Every number the book quotes from a measurement has its raw results and the script that produced
it under `measurements/chNN/`; run the script to measure your own machine, and expect different
numbers with the same shape. The architecture, the decision records and, from Part III, the
regulatory file are under `docs/`. The book and the solutions manual are built from `book/` with
`book/build.sh`; the repository README lists the packages that needs.

### When something does not work {.unnumbered}

- **A test fails on a fresh clone.** Check that you are on a tag or on `main` with no local
  changes (`git status`), then rebuild from scratch with `rm -rf build/debug`. If it still
  fails, the failure is worth reporting as an issue on the repository, with the output of
  `ctest --output-on-failure`.
- **Real-time settings are refused.** `SCHED_FIFO` and locked memory need permissions an
  ordinary user does not have; Chapter 4 explains which, and how to grant them.
- **The disk fills up.** Each preset has its own build directory; delete the ones you no longer
  use.
