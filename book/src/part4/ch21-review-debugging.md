# Code review, debugging and incident analysis {#ch21}

::: box-why
Chapters 18 to 20 built evidence that MiniDAQ does what its requirements say. This chapter is
about the two moments when that evidence is not enough: before a change is merged, when only a
person reading it can see what the tests do not test, and after something has failed, when the
question is no longer "does it work" but "what happened". A DAQ lead does both every week. You
review the changes of others, and the review is a verification record that an auditor reads. You
get the call when a site says the acquisition stopped, and you have whatever the system kept: a
log, a counter, a core dump, or nothing. IEC 62304 asks that problems be investigated for their
cause and that the investigation be recorded, and ISO 13485 asks that corrective action remove
the cause, not the symptom. Both depend on data that has to exist before the failure. This
chapter teaches review with a checklist, debugging from a core dump with the right build,
a flight recorder that keeps the last events of every thread, a crash report written by the
dying process, root cause analysis written into the problem report, and the search for the change
that broke something. MiniDAQ gets all of them, and the first crash report it wrote found a
defect of its own.
:::

**A day in the life.** It is 7:50 on a Thursday. The service engineer forwards a message from a
site: last night's research acquisition ended after 41 minutes instead of 60, and the server had
to be restarted. There is no core dump, because the service manager on that PC discards them. The
journal has the server's last line, `minidaq_server: control API on 127.0.0.1:7700`, from the
evening before, and then nothing. The list-mode files end in the middle of a block. You have
three questions: what the server did in its last seconds, which build was running, and where it
died. You can answer none of them, and the only way forward is to ask the site to run the same
protocol again with core dumps on and wait. A week later the same thing happens at a second site,
this time with a core. You open it with the program on your laptop and get a stack through the
sorter that makes no sense, until you notice that the site runs 2.3.1 and your laptop has 2.3.2.
By the evening you have the right build and a stack that does make sense, and you write in the
problem report what you wish the server had kept. The rest of this chapter is that list.

## Learning objectives {.unnumbered}

After this chapter you can:

1. Review a change with a checklist, find the defects that tests do not find, and write findings
   that an author can act on and an auditor can read.
2. Open a core dump with the build that produced it, check that the build IDs match, and read
   the signal, the stacks of all threads and the state of the faulting frame.
3. Design an always-on flight recorder for a real-time process: per-thread rings, a seqlock per
   slot, a snapshot without locks, and a measured cost per event.
4. Write a crash handler that uses only async-signal-safe calls, reports what an investigator
   needs, and still lets the process die of its signal so that the core dump is made.
5. Write a root cause analysis into a problem report: the chain of causes from the symptom, the
   cause, its category, and why the defect escaped the checks that should have found it.
6. Find the change that introduced a defect with `git bisect run`, also through commits that
   cannot be tested, and reconstruct an incident from monitoring data.

## Prerequisites and estimated time {.unnumbered}

Chapter 3 (atomics and memory order), Chapter 4 (the real-time process), Chapter 7 (sanitizers and
hardening), Chapter 16 (problem reports and CAPA), Chapter 19 (system tests) and Chapter 20 (the
shipped build, its debug information and build ID). Reading: about 3 hours. Exercises: 4 to 6 hours.
Milestone: 4 hours. If time is short, do Exercises 21.1, 21.2 and 21.5 and leave 21.3 for later.

## Reviewing a change

### The intuition

Tests check what their author thought of. A review checks the rest: whether the change does what
its description says, whether its error paths leave the state as it was, whether two threads can
meet in it, whether the test would fail without the change. Studies of code review in industry
find that reviewers spend much of their time on readability and design and find fewer defects
than expected (Bacchelli and Bird, in the further reading); the defects they do find are often
the ones no test could have found, because nobody thought of the case. A checklist does not make
you smarter. It makes you look at the places where defects of a known kind live, in an order, and
it makes the review a record: what was checked, what was found, what was decided.

Read a change in this order. The description first: if you cannot say in one sentence what the
change does and why, the author has more work to do before you start. Then the interface (the
header, the protocol, the file format), because that is what other code will depend on. Then the
implementation, then the tests. For each part, the checklist asks its questions.

### MiniDAQ's checklist

MiniDAQ's code review checklist (`docs/code-review-checklist.md`) has seven sections. Sections 1
to 6 are questions, section 7 is how a finding is written:

1. **Before the code.** The description says what and why; a change to a requirement, a risk
   control, a class, a SOUP item, an interface or a format names its approved change request; the
   change is one thing.
2. **Correctness.** Every error path, boundary values, units and types, input from outside, and
   ownership and lifetime.
3. **Concurrency.** For each shared variable, which threads write and read it and what orders the
   accesses; a comment for every relaxed or acquire/release atomic; nothing the pipeline waits on
   can block for a time nobody bounded.
4. **Tests.** The test fails without the change; it names its requirement; it waits for
   conditions, not for times; a skip says where and why.
5. **The regulated parts.** The trace holds, a class B branch is covered or accepted, a new tool
   is in the tool list, changed controlled documents get a new version.
6. **Diagnosability.** If this code fails in the field, what will the investigator see?
7. **Writing a finding.** One problem, one place, a severity, what you observed and why it
   matters, and a suggestion if you have one.

The compilers, clang-tidy, cppcheck and the sanitizers check what a machine can check, so the
checklist does not repeat them: it starts where they stop. Section 6 is new in this chapter, and
the rest of the chapter explains why it is there.

### A worked review

Exercise 21.1 gives you a change to review: a rate meter for the readout link, packets per second
over the last 16 seconds. The description says that the receive thread calls `add()` and the
control thread `rate()` and `label()`. It compiles without warnings and its unit test passes.
The header keeps the counts in `std::array<std::uint64_t, kSeconds> counts_` with `kSeconds`
equal to 16, the latest second in an `std::atomic<std::uint64_t> latest_s_`, and the window in a
plain `window_`. Here is the implementation:

```cpp
void RateMeter::add(std::uint64_t now_s, std::uint64_t packets) noexcept {
  const std::uint64_t last = latest_s_.load(std::memory_order_relaxed);
  for (std::uint64_t s = last + 1; s <= now_s; ++s) {
    counts_[s % kSeconds] = 0;  // seconds without packets
  }
  counts_[now_s % kSeconds] += packets;
  total_ += packets;
  latest_s_.store(now_s, std::memory_order_relaxed);
}

double RateMeter::rate() const noexcept {
  std::uint64_t sum = 0;
  for (std::size_t i = 0; i <= window_; ++i) {
    sum += counts_[i];
  }
  return static_cast<double>(sum) / static_cast<double>(window_);
}

std::string_view RateMeter::label() const {
  char buf[32];
  std::snprintf(buf, sizeof buf, "link 0: %.1e/s", rate());
  return std::string{buf};
}

bool RateMeter::set_window(std::uint64_t seconds) {
  window_ = seconds;
  if (seconds == 0 || seconds > kSeconds) {
    return false;
  }
  return true;
}
```

Go through the sections. Section 3 asks, for `counts_`: which threads write it, which read it,
and what orders the accesses? The description answers the first two (the receive thread writes,
the control thread reads) and nothing answers the third. `latest_s_` is an atomic, which makes
the code look as if someone thought about threads, but its relaxed store orders nothing, and
`counts_` is a plain array. That is a data race, undefined behavior, and the most serious
finding, because no test will find it: the unit test runs on one thread. Section 2.2 asks for
boundary values: the loop of `rate()` runs while `i <= window_`, so with the default window of 16
it reads `counts_[16]`, one past the array; and it sums slots 0 to 16, which are not the last 16
seconds, since the slots are indexed by the second modulo 16. Section 2.5, lifetime: `label()`
returns a view of a `std::string` that is destroyed at the end of the return statement. Section
2.1, error paths: `set_window()` stores the value before it checks it, so a refused 0 still becomes
the window and `rate()` divides by zero. Section 2.2 again, for the initial state: `latest_s_`
starts at 0, and the first call with a real time, about 1.8 billion seconds since 1970, runs the
clearing loop 1.8 billion times on the receive thread. Section 4 finds a test that sleeps for a
second (for nothing: `add()` takes the time as an argument), checks only `rate() > 0`, which the
off-by-one passes, and names no requirement.

Each finding is written as section 7 says. For the race:

```text
blocker, concurrency, rate_meter.cpp, add() (line 63 of change.diff): counts_ and total_ are
written by the receive thread and read by rate() on the control thread with no lock and no
atomics: a data race, undefined behavior, and torn or stale sums. The relaxed store of latest_s_
orders nothing. Suggestion: a mutex, or atomic slots with a comment on what each memory order
pairs with; your call.
```

The finding says what and why, and it suggests without insisting. The author decides how to fix
it, and you check the fix. What you do not do is rewrite the code in the review, or list ten
remarks about names that bury the three blockers. A blocker or major finding is resolved before
the merge, by a fix or by an answer you accept; the resolution is recorded with the review. In a
team that is the pull request. In MiniDAQ, a single-author project, the commit message carries
`Review: change control checklist, items 1 to 6` and the review is the author's own, which
Chapter 16's audit already named as a place where a one-person project cannot conform.

### Reviewing real-time and safety-relevant code

Two kinds of code in a DAQ deserve more than the checklist's general questions.

**Code on the hot path.** For every function a pipeline stage calls per batch, ask what it can
block on and for how long: a lock held by a thread that does I/O, an allocation that falls
through to `mmap`, a log line that takes a lock in the C library, a page fault on memory that was
never touched. The answer is in the code or in a comment, and if it is "I don't know", that is a
finding. Chapter 4's rules (no allocation, no system call, no unbounded wait after start) become
review questions.

**Code that a risk control relies on.** Chapter 15 tied risk controls to requirements and tests.
A change to such code (the integrity verdict, the loss counters, the stop on a fault) gets a
second reviewer with the risk file open, and the review asks whether the control still works
when the change fails: what happens to the verdict if this new code throws, returns early or is
never called?

::: box-mistakes
- **Reviewing the diff, not the change.** A diff shows lines; the defect is often in a line that
  did not change, such as a caller that now gets a new error. Open the files around the diff.
- **Approving what you did not understand.** "Looks good" on code you could not explain is not a
  review. Ask, as a question finding: it costs the author a sentence.
- **Style instead of substance.** Twenty remarks about names and one about a race leave the
  author fixing names. Put blockers first, and leave style to the formatter and the linter.
- **The test that cannot fail.** A test that passes before and after the fix proves nothing about
  the fix. Ask for the failing run (checklist item 4.1).
- **Reviewing in one sitting for two hours.** Attention fades; review in blocks of an hour or less,
  and split a change that is too big to review into changes that are not.
:::

## Reading a crash

### The intuition

A crash in the field is a fact about one build at one moment. The evidence of record is the core
dump: the memory of the process and the registers of every thread at the moment it died. It is
also the evidence most often missing, because the system was not set up to keep it, and the most
often misread, because it was opened with another build. Three steps make it useful: keep it,
open it with the right build, and read it in an order.

### Keeping cores

When a process dies of a signal whose default action dumps core (SIGSEGV, SIGBUS, SIGFPE, SIGILL,
SIGABRT, among others), the kernel writes a core if the process's `RLIMIT_CORE` allows it and
`kernel.core_pattern` says where. The pattern is either a file name, relative to the process's
working directory or absolute, or a pipe to a program (`|/usr/lib/systemd/systemd-coredump ...`
on systems that use systemd's collector, a pipe to apport on Ubuntu desktops). On the reference
machine it is the plain name `core`, and the hard limit is unlimited. An acquisition PC's setting
is part of its installation, like the receive buffer of Chapter 20 (verify: what the acquisition
PC's image sets, and how long it keeps cores). A service manager decides the limit for the
programs it starts: under systemd, `LimitCORE=` in the unit file.

A core holds everything in the process's memory. For MiniDAQ that includes the control tokens'
digests and, in a product, possibly data that relates to a patient. Where cores are kept, who may
read them and how they leave the site are questions for the quality system and the data
protection officer, not for the developer alone (assumption: confirm with team).

### The right build

A core says which files the process had mapped, but not which build of them. Opened with another
build of the same program, gdb shows stacks that look plausible and are wrong: the addresses
point into other functions. Chapter 20 gave every shipped program a build ID, a hash the linker
writes into a note of the ELF file, and kept the debug information in a separate file with the
same ID. The core holds the first page of every mapped ELF file, where the note is, so the build
ID can be read from the core itself. `tools/core_build_id.py` does that without gdb:

```{.python include="tools/core_build_id.py" snippet="build_id"}
```

It finds the program's mapping in the core's `NT_FILE` note, reads the ELF header and the program
headers from the core's memory, corrects for the address at which the program was loaded, and
returns the `GNU` build ID note. `tools/postmortem.sh` refuses to go on when the IDs of the core,
the program and the debug file are not one and the same:

```{.bash include="tools/postmortem.sh" snippet="check"}
```

Then it runs gdb in batch mode with the commands of a first look:

```{.bash include="tools/postmortem.sh" snippet="gdb"}
```

### Reading it in an order

The order matters because each step tells you what to look for in the next.

1. **The signal.** `$_siginfo` holds the signal and its code. A positive `si_code` means the
   kernel raised it for a fault, and `si_addr` is the address that faulted: a small address is a
   null pointer plus an offset, an address just below a thread's stack is a stack overflow. A code
   of zero or less means another process or the program itself sent it (`kill`, `raise`,
   `abort`), and the address field means nothing.
2. **The crashing thread.** `bt` from the innermost frame. Look for the first frame in your own
   code, not in the C library.
3. **All threads.** `thread apply all bt`. A deadlock is two threads each waiting on what the
   other holds; a hang is a thread in a loop or a wait that never ends. Which threads exist also
   tells you which phase the program was in.
4. **The frame.** `frame N`, `info locals`, `print` of the variables that the code at that line
   uses. In an optimized build some are `<optimized out>`; the registers and the disassembly
   (`x/10i $pc`) still say what the instruction was doing.

To see what a real one looks like, start the debug build of the server, run a 0.5-second
acquisition and send the server SIGSEGV from outside, as the milestone's system test does with an
idle server. On the reference machine, the postmortem tool printed, shortened
(`measurements/ch21/crash-and-live-core.txt` has the full record):

```text
build ID in the core:       381db68009df56ebd612f8c26dcdb7522dfbf211
build ID of the program:    381db68009df56ebd612f8c26dcdb7522dfbf211
Program terminated with signal SIGSEGV, Segmentation fault.

== signal (si_code 0 or less: sent by kill, raise or abort, not a fault)
$1 = 11
$2 = -6
$3 = (void *) 0x78d5

== crashing thread
#0  __GI___sigtimedwait (...) at ../sysdeps/unix/sysv/linux/sigtimedwait.c:31
#1  __GI___sigwait (...) at ../sysdeps/unix/sysv/linux/sigwait.c:28
#2  main (argc=5, argv=0x7fff50049618) at minidaq/apps/minidaq_server.cpp:209
```

Read it in the order above. The code is −6, `SI_TKILL`: not a fault, a signal sent to one thread.
The "address" 0x78d5 is the sender's process ID, 30,933, which is the server itself. That is not
who sent the original signal. It is MiniDAQ's own crash handler, which re-raised the signal after
writing its report, as the next sections explain. The core shows the second delivery. The report
names the first sender, process 30,929, the test. A core and a report together say more than
either alone. The main thread was in `sigwait`, where the server waits for the signals that stop
it, and the other two threads were in a `poll` (the control server) and a condition variable
wait (the monitor): an idle server between commands, as expected.

### A live system, without stopping the acquisition

Sometimes the server has not crashed: it is running a patient scan and something looks wrong, a
rate that is too low or a state that does not change. Stopping it to look would lose the scan.
The tools then come in an order of how much they disturb:

1. **What the program reports.** `minidaq_ctl status` (counters, the integrity verdict so far) and
   `minidaq_ctl diagnostics` (the last events of every thread) read the server's own data; on the
   control thread they cost a snapshot (1.2 µs for 64 events, measured later in this chapter) and
   some JSON. This is what Section 6 of the checklist asks every change to think about: if this
   fails, what will the investigator see?
2. **What the kernel reports.** `/proc/PID/status` (memory, context switches), `/proc/PID/task/`
   (one directory per thread, with its state and CPU), `ss -u -m` (a socket's receive queue and
   drops), `perf top -p PID` (where the CPU time goes, by sampling). None of them stops the process.
3. **A core of the running process.** `gcore PID` writes a core and lets the process continue. It is
   not free: gdb attaches with `ptrace`, which stops every thread until the core is written. On the
   reference machine, `gcore` of the release server in the middle of an acquisition took 0.19 s and
   wrote a file of 484 MB for a process with 35 MB resident: gcore writes whole mappings. The run
   lost nothing (its integrity verdict stayed complete), but its source was the synthetic one; a
   real readout link does not wait, and a link that delivers more than about 22 MB/s fills a 4 MiB
   receive buffer in 0.19 s. Take a live core only when losing that much data is acceptable (the
   measurement is in `measurements/ch21/crash-and-live-core.txt`).
4. **A debugger attached to the process.** `gdb -p PID` stops every thread for as long as you look.
   During an acquisition, that is the end of the acquisition. Use it on a test system, or after
   the scan.

### When the core is not enough

Some failures leave a correct core of the wrong moment: the corruption happened long before the
crash, and the stack shows only where it was noticed. Two tools go further, at a cost.

**The sanitizers** of Chapter 7 catch the corruption where it happens. If a failure reproduces in
the test environment, run it under AddressSanitizer or ThreadSanitizer first; the report names
the access and the allocation.

**Record and replay** records a run of the program so that you can replay it in a debugger as
often as you like, also backwards: set a watchpoint on the corrupted variable and run in reverse
to the store that wrote it. On Linux the tool is rr (O'Callahan and others, in the further
reading). It needs the CPU's hardware performance counters, which virtual machines often do not
expose, and it knows the CPU models it supports. On the reference machine, a cloud VM, rr 5.7.0
stopped at once with `Intel CPU type 0xc06f0 unknown`. That is worth knowing before you plan an
investigation around it: try rr on the acquisition PC, a physical machine, before you need it
(verify: rr on the acquisition PC's CPU and kernel).

::: box-mistakes
- **No core, because nobody set it up.** Check `kernel.core_pattern` and the service's core limit
  on the acquisition PC now, not after the first crash.
- **The wrong build.** A core opened with another build gives plausible wrong stacks. Check the
  build ID every time; the postmortem tool refuses a mismatch.
- **Reading the first frame only.** The innermost frame is often in the C library. The cause is in
  your code, further out, or in another thread.
- **Trusting `si_addr` of a signal that was sent.** For `kill` and `abort` the field holds the
  sender's process ID, not an address.
- **Debugging the release build from the debug build's source lines.** Inlining and reordering
  make the optimized program's line numbers approximate. Use the shipped build's debug file and
  read the disassembly where it matters.
:::

## A flight recorder

### The intuition

A core shows the state at the end. It does not show what led there: which command came last,
which state the acquisition was in, whether the link had just lost packets. A log could say, but
a log written to disk is off at the level where it would have helped, costs a lock or a system
call per line on the threads that write it, and loses its last lines in a buffer when the process
crashes. A flight recorder is the answer aircraft found: record a small number of chosen events
all the time, in memory, overwrite the oldest, and read them after the fact. Its value is that it
is on the first time the failure happens.

The design questions are the ones of Chapter 3. Many threads record; any thread, including a
signal handler, may read at any time; a recording thread must never wait.

### MiniDAQ's recorder

ADR 0016 records the decision. Each thread that records gets a ring of 256 events of its own, one
of 32 rings in static memory, claimed with a compare-and-exchange on first use and given back when
the thread exits (a `thread_local` lease whose destructor releases it). A thread that finds no
free ring counts its events as dropped. Because only one thread writes a ring, a record needs no
lock and no read-modify-write:

```{.cpp include="minidaq/src/core/flight_recorder.cpp" snippet="record"}
```

Each slot is a seqlock. Event `n` (from 0) writes `2n + 1` into the slot's sequence word, then
the fields, then `2n + 2`. A reader copies the fields between two loads of the sequence word, and
keeps the event only if both loads say `2n + 2`: an odd value means the writer was in the middle
of it, and a different even value means a newer event overwrote it. The fields are relaxed
atomics, not plain integers, because a reader copies them while the writer may change them, and
a concurrent plain read and write is a data race in C++ even when the reader throws the value
away. The two fences carry the order: the release fence after the odd store keeps the field
stores after it, and the acquire fence before the second load keeps the field loads before it.
Boehm's paper in the further reading explains why this pattern, and not the textbook version with
plain fields, is correct in the C++ memory model.

A snapshot merges the rings from their newest events backwards. Each ring is in time order, so
the newest event overall is the newest head of some ring:

```{.cpp include="minidaq/src/core/flight_recorder.cpp" snippet="snapshot"}
```

It allocates nothing (the cursors are arrays on the stack), so a signal handler can call it, and
it costs at most `out.size()` × 32 slot reads.

### What it costs

SRS-DIAG-005 asks for at most 100 ns per event, without a lock, also with four threads recording.
`bm_flight_recorder` measured on the reference machine (release preset, three CPUs, medians of
five repetitions, `measurements/ch21/bm_flight_recorder.txt`):

| Benchmark | Real time | Per event |
|---|---|---|
| One thread recording | 32.7 ns | 32.7 ns |
| Four threads recording | 40.9 ns | 32.6 ns of CPU |
| One thread recording while another takes snapshots | 32.5 ns | 32.5 ns |
| Snapshot of 64 events | 1.22 µs | |
| Snapshot of 1024 events | 17.6 µs | |
| `clock_gettime(CLOCK_MONOTONIC)` alone | 27.8 ns | |

Most of an event is the clock: on this VM a monotonic clock read costs 27.8 ns, and the rest of
the record about 5 ns. A first version counted every event in one shared atomic counter with
`fetch_add` and did not align the rings to cache lines. It measured 38.1 ns with one thread and
213 ns with four: every record wrote the same cache line from four cores. Summing the rings' own
`next` counters when someone asks, and `alignas(64)` on each ring, brought four threads to
40.9 ns. The lesson of Chapter 3 again, found by measuring and not by reading: a counter that
every thread writes is a lock in disguise.

### What it records, and what not

SRS-DIAG-004 lists the events: every change of the acquisition state, every control command but
`hello` with its outcome (refusals included), the begin and the end of each run with its
completeness, each fault with its source (detector, sink, sorter), and each loss and
resynchronization of the readout link. An event is a code and two numbers, so it holds no names,
no tokens and no paths. Not recorded: anything per single, per batch or per packet. At 30 ns an
event, the data path could afford a few events a batch, but 256 events would then cover a few
milliseconds instead of minutes. A recorder that keeps everything keeps nothing for long.

The control API gives a running server's events to an observer, with `diagnostics` (control API
2.1, SRS-DIAG-003). Against a server that has just started, on the reference machine:

```bash
minidaq_ctl --port 44685 diagnostics 5
```

```json
{ "api": "2.1", "diagnostics": {
    "build_id": "381db68009df56ebd612f8c26dcdb7522dfbf211",
    "events": [
      { "a": 7, "b": 1, "code": "command", "ring": 0, "seq": 1, "t_ns": 61239173266387 } ],
    "recorder": { "dropped": 0, "recorded": 1, "torn": 0 },
    "server": "minidaq 0.4.0-dev" },
  "id": 1, "ok": true }
```

The one event is command 7, `auth`, with outcome 1: the client's own authentication, which the
server recorded before it answered `diagnostics`. The `diagnostics` command itself is recorded
after its snapshot, so it appears in the next one.

## A crash report

### What a signal handler may do

When the process faults, the kernel runs a handler if one is installed, on the faulting thread,
in the middle of whatever that thread was doing. The thread may hold the allocator's lock or be
halfway through a `printf`. So a handler may call only async-signal-safe functions: POSIX lists
them, and the Linux manual page `signal-safety(7)` repeats the list. `write`, `getpid`,
`sigaction` and `raise` are on it. `malloc`, `printf`, `std::string`, iostreams and
`dl_iterate_phdr` are not. A handler that calls them works in every test and deadlocks in the field
the first time the fault lands inside `malloc`.

MiniDAQ's handler therefore prepares everything before the fault and writes with `write(2)` from
a fixed buffer:

```{.cpp include="minidaq/src/rt/crash_report.cpp" snippet="handler"}
```

Four decisions are in those lines and in `install_crash_report()`:

- **An alternate stack.** A stack overflow faults because the stack is full, and a handler on the
  same stack would fault again at once. `sigaltstack` gives the handler 64 KiB of its own, and
  `SA_ONSTACK` uses it. The alternate stack serves the thread that installed it, the main thread,
  installed first in `main` before any other thread starts; a stack overflow in another thread
  ends the process with a core but without a report (ADR 0016 records this).
- **The default action restored first.** `SA_RESETHAND` puts the default action back before the
  handler runs, so a second fault, in the handler or in another thread, kills the process instead
  of recursing.
- **Only one writer.** The first thread to get there writes; the `exchange` on an atomic flag is
  lock-free and safe in a handler.
- **Die of the signal.** After the report, a fault returns from the handler, the instruction runs
  again, faults again and kills the process with its default action; a signal that was sent
  (`si_code` of zero or less) is raised once more. The process dies of the same signal, so the
  service manager sees the right exit status and the kernel writes the core. That second
  delivery is the `SI_TKILL` of the postmortem above.

The build ID is read with `dl_iterate_phdr` when the program starts, not in the handler, because
that function is not async-signal-safe.

### What the report says

The report is text, small enough to paste into a problem report, and it is what the night shift
at a site can send by e-mail:

```{.cpp include="minidaq/src/rt/crash_report.cpp" snippet="report"}
```

The server installs it first thing in `main`, writing to standard error, which the service
manager's journal keeps, or to the file of `--crash-report`:

```{.cpp include="minidaq/apps/minidaq_server.cpp" snippet="crash_report"}
```

The report of the crash above (the lines for commands 11 to 13, three more `status` polls, are
left out):

```text
MiniDAQ crash report
signal: SIGSEGV (11) sent by pid 30929
version: 0.4.0-dev
build-id: 381db68009df56ebd612f8c26dcdb7522dfbf211
pid: 30933 thread: 30933
flight recorder: last 18 events of 18 (dropped 0, torn 0)
t_ns ring seq code a b
61263570384535 0 1 command 7 1
61263570892897 0 2 state 0 1
61263570922348 0 3 command 1 1
61263574097291 0 4 command 7 1
61263601810914 0 5 run_begin 1 0
61263601819557 0 6 state 1 2
61263601855992 0 7 command 2 1
61263605406506 0 8 command 7 1
61263607053416 0 9 command 5 1
61263709134241 0 10 command 5 1
...
61264112923989 1 1 run_end 1 1
61264112926471 1 2 state 2 1
61264118455273 0 14 command 5 1
61264122911686 0 15 command 7 1
61264124215122 0 16 command 5 1
end of report
```

Read it like the core. The signal was sent by another process, so this is not a fault in MiniDAQ.
The build is a development build of 0.4.0 with a known build ID. Then the story, in order. Each
`minidaq_ctl` call is a new connection that authenticates first (`command 7`, outcome 1). The first
configures: the state goes from idle (0) to configured (1), and `configure` (`command 1`) is
recorded with its outcome after the change it made. The second starts: run 1 begins, the state
goes to running (2), and `start` (`command 2`) succeeds. The third is `minidaq_ctl wait`, which
polls `status` (`command 5`) every 100 ms. Run 1 ends complete (`run_end 1 1`) 511 ms after it
began, recorded on ring 1 by the thread that ran it, and the state returns to configured; the
wait's last poll sees it. A fourth client asks for the status, and then comes the signal. With
this report, the day in the life at the start of the chapter would have begun with the answers.

### The first report found a defect

The first time the report ran against a build of main, it said `version: 0.3.0`. The build was
not 0.3.0: that was the release, five chapters earlier. `VERSION` had never been moved to
`0.4.0-dev`, so every build of Part IV had reported the released version in `hello`, in every
list-mode file's software field and now in its crash report. A report from such a build would
have sent an investigator to the release's code. That is problem report MDQ-PR-024, and its root
cause is in the next section's terms a process defect: moving to the next development version was
a habit of the first chapter of each Part, not a step of the release procedure, and nothing
checked it. `tools/check_version.py` (CTest `docs.version`) now fails when `VERSION` is a release
version outside its release commit or a `-dev` version not later than the newest release record.
The same stale version had kept the SOUP check quiet, because the check asks for a known-anomaly
review dated for the current minor version; the reviews for 0.4 are now recorded.

::: box-regulated
What the regulated setting adds to this chapter's examples:

- A code review is a verification activity. IEC 62304 asks for software unit verification
  (clause 5.5) and leaves the methods to the development plan; where the plan names code review,
  it names the review's criteria (here the checklist), and the record shows who reviewed what,
  what was found and how it was resolved.
- Problem resolution (IEC 62304 clause 9) asks for an investigation of each problem, its cause
  where possible, an evaluation of its relevance to safety, and records. ISO 13485 clause 8.5.2
  asks that corrective action determine the cause and act on it. A root cause analysis is how the
  report shows that the cause and not the symptom was addressed.
- Diagnostic features in the product are part of the design: requirements (SRS-DIAG-001 to 005),
  an architecture decision (ADR 0016), tests, and a change request (CR-0007). What they record is
  reviewed for personal data and security: MiniDAQ's events hold numbers only, and `diagnostics`
  needs the observer role.
- Core dumps and logs from a site are records that may hold personal data. Their collection,
  storage and transfer follow the quality system and data protection rules, not a developer's
  habit.
- Post-market surveillance (Chapter 13) depends on what the field can report. A crash report that
  a site can send by e-mail and a build ID that names the exact build make a field report
  actionable.
:::

## Root cause analysis

### The intuition

The question after a fix is: why did this defect exist, and why did nothing catch it? The first
answer is rarely the last. "The counter was wrong" is a symptom; "the function decided from the
sequence number alone" is a mechanism; "the counter was implemented from half of its definition"
is a cause you can act on everywhere, not only in that function. The *five whys* technique, from
Toyota's production system, asks "why" until the answer is something the organization controls.
Five is not a rule; stop when the next "why" leaves your control or stops changing what you do.

Two more questions turn an analysis into an action. Which category is the cause in:
requirements, design, code, test, tool, environment or process? That decides who acts. And why
did it escape: which check should have found it, and why did that check not see it? The escape is
often the more useful answer, because fixing the check finds the next defect of the same kind.

### MDQ-PR-019, written up

Chapter 19's system test found MDQ-PR-019: under load, the readout's `packets_reordered` counter
was one or two too high. Here is its root cause as `docs/regulatory/problem-reports.json` records
it:

1. *Why was the counter too high?* A late copy of a packet that was still held was counted as
   reordered.
2. *Why was it counted?* `SequenceTracker::offer()` decided "reordered" from the sequence number
   alone, before it checked whether the packet was a copy of one already held.
3. *Why did it decide from the sequence number alone?* The counter's definition, "arrived after
   a higher sequence number, and was still used", was written in the documentation, but the code
   tested only its first half.
4. *Why did no test notice?* No unit test combined delay with duplication while a packet was
   held; the case needs a gap and a copy at once.

**Cause:** a counter implemented from half of its definition, with no test of the combination of
faults that tells the halves apart. **Category:** code. **Escape:** the unit tests injected one
fault at a time; the system test with a loaded machine was the first to hold packets long enough
for both faults to meet.

The fourth answer points at a class of tests, not one test: for every counter with a definition
of the form "A and B", a test that has A without B. The review checklist now asks for it (item
4.5). That is what acting on the cause looks like: a change to how the next counter is reviewed.

Since this chapter, every closed problem report from MDQ-PR-019 on has a root cause with at least
two whys, a cause, a category from the list above and an escape, and `tools/anomalies.py` fails
the documentation tests when one is missing:

```{.python include="tools/anomalies.py" snippet="root_cause"}
```

Reports before MDQ-PR-019 were closed before the rule existed and are left as they were; the
development plan says so. A rule that applies from a date is honest; one that silently rewrites
old records is not.

### Not a person

A root cause is never "the developer made a mistake". People make mistakes at a steady rate; the
question is why the system let this one through. "The developer forgot to update VERSION" ends
the analysis with nothing to do but to be careful. "Moving to the next version was a step that no
procedure named and no check enforced" ends it with a check. Blameless analysis is not kindness,
it is accuracy: the cause you can act on is in the process.

## Finding the change

### Bisecting

When something worked in one version and fails in a later one, and you have a test that shows the
failure, `git bisect` finds the first commit that fails by testing the commit halfway between a good
and a bad one, again and again: about the base-2 logarithm of the number of commits, seven tests for
a hundred commits. `git bisect run CHECK` automates it. The check's exit status is the verdict: 0
good, 1 to 127 bad, except 125, which means "this commit cannot be tested, skip it".

The 125 matters more than it looks. A history has commits that do not build: a refactoring split
over two commits, a dependency that is no longer available, a test that was broken for an
unrelated reason. A check that calls them bad moves the search before them and blames the wrong
commit. A check that skips them lets bisect test a neighbor. When skipped commits sit right before
the defect, bisect cannot decide among them, and its log (`git bisect log`) ends with one line
`# possible first bad commit:` for each candidate; the honest result is that list, and the next
step is to read those diffs. Exercise 21.5 builds a check that does this:

```{.python include="exercises/ch21/e5_bisect/solution/bisect_tool.py" snippet="check"}
```

Its first version failed for a reason that had nothing to do with bisect, and it is worth the
detour. Every commit of the test repository had an `app.py` of the same size, and git checked them
out within the same second. Python's bytecode cache decides whether a `.pyc` is current by the
source's modification time and size, so it ran the bytecode of an earlier commit, and every commit
looked good. The check now runs Python with `-B`. Any check that uses a build output must start
from a clean state, or bisect searches the cache instead of the history. For MiniDAQ, that means
a check that configures a fresh build directory, builds only the target it needs, runs only the
test that shows the defect, and returns 125 for a build that fails.

Its second version passed on the reference machine and failed on every GitHub runner. It read the
messages that `git bisect run` prints, "is the first bad commit" and "The first bad commit could be
any of:", and with the runners' git 2.55 it found neither. The third version read `git bisect log`
instead, on the theory that the log is the record bisect keeps for tools, and it failed in exactly
the same way. That theory was a guess, and the fix was pushed without the evidence to test it. The
fourth version made the tool fail loudly when it found nothing, with what git had printed, and the
next CI run showed the cause at once: git 2.55 writes `# first 'bad' commit:` in the log, with the
term in quotes, because bisect lets you rename "good" and "bad". The tool now accepts both forms,
and a test parses a log of each so that the reference machine checks both. Three lessons, in
order of cost: a text format written by another program is an interface only if it is documented
as one, and even then test it with every version you run; a tool that finds nothing must say so
with its evidence instead of returning an empty answer; and a fix for a failure you cannot
reproduce is a hypothesis until the failing environment confirms it.

### Diagnosing from data

Not every failure has a commit to find. A slowdown at a site is a fact about the machine, the
load and the code together, and the evidence is what the monitoring kept. Exercise 21.4 gives you
the status snapshots of a pipeline in which one stage slowed down, polled about once a second, and
asks which stage it was. The trap is that a slow stage slows the others: the stages after it
starve at once, and the stages before it slow when the queue in front of it is full. In the
exercise's model, with the writer slowed to 30% of its capacity at 30 s, the writer's rate falls
at 31 s, the pair stage's at 37 s, the sort stage's at 42 s, the decoder's at 48 s and the
source's at 53 s, and the source begins to drop data at 52 s. Someone who looks at 55 s sees every
stage slow and data lost, and the stage that is losing data, the source, is the one that did
nothing wrong. The order of the onsets is the evidence, and to read it you need rates computed
from the real time between snapshots, a baseline from before the incident, and the queue depths.

A first version of the exercise's solution broke ties the wrong way. When two stages slowed in the
same interval, it blamed the one downstream. With snapshots one second apart the case never arose,
so no test saw it; with snapshots two seconds apart the slow stage and the stage it starves fall
into the same interval, and the rule blamed the starved one. The test with coarse polling was
added when the rule was corrected. A diagnosis rule is code, and its edge cases need tests like
any other code's.

::: box-askteam
1. Who reviews a change to the DAQ, how many reviewers does a change need, and is there a written
   checklist? Which changes need a second reviewer from risk or quality?
2. Where is the review recorded, and what does an auditor look at to see it?
3. How are core dumps kept on the acquisition PCs (`core_pattern`, the service's core limit), for
   how long, who may read them, and how does one leave a site?
4. Are the debug files of every released build kept, with their build IDs, so that a core from
   any version in the field can be opened? Who can find them?
5. Does the product have a flight recorder, a crash report or another way to see what happened
   before a failure? What do they record, and has anyone reviewed them for personal data?
6. What does a problem report's root cause analysis look like here, and who checks it? Is
   "human error" an accepted cause?
7. Does rr, or another record-and-replay tool, work on the acquisition PC's hardware?
:::

## Exercises {.unnumbered}

**Exercise 21.1 (M): Review a change with the checklist.** *Goal:* review a proposed rate meter
for the readout link with the code review checklist and write findings as its section 7 says.
*Starter:* `exercises/ch21/e1_review/` (the change in `tests/change.diff`, an empty list of
findings). *Acceptance:* `tests/test_review.py` passes: every finding is well formed, the three
seeded blockers are found and called blocker or major, five of the six seeded defects are found,
at most two blocker or major findings point at nothing. Then answer in `NOTES.md` which section
found the most serious defect and why the unit test never would. *Time:* 45 minutes.

**Exercise 21.2 (E): A crash from the field, from the core dump.** *Goal:* find why a recursive
parser dies on a configuration file from a site, from its core dump, and make the input an error.
*Starter:* `exercises/ch21/e2_postmortem/starter/group_parser.cpp`. *Acceptance:*
`tests/test_group_parser.cpp` passes: a group nested deeper than 64 is an error with its byte
offset, and the field capture of 16,777,216 opening braces gives that error instead of SIGSEGV.
Then answer in `NOTES.md` why 1 MiB of braces crashes the debug build and not the release build.
*Time:* 30 minutes.

**Exercise 21.3 (H): A flight recorder that never shows half an event.** *Goal:* write a ring of
64 events for one writer with a seqlock per slot, and a snapshot that any thread can take at any
time. *Starter:* `exercises/ch21/e3_flight_recorder/starter/` (the class, without the sequence
word). *Acceptance:* `tests/test_tiny_recorder.cpp` passes, also in the `tsan` preset: events in
order, the last 64 after a wrap, a stress test with thousands of snapshots during writes and no
torn event. Then answer in `NOTES.md` why the fields are relaxed atomics and what the reader's fence
prevents. *Time:* 90 minutes.

**Exercise 21.4 (M): What went wrong first.** *Goal:* from the status snapshots of a simulated
incident, find the stage that slowed first and when, and when data loss began. *Starter:*
`exercises/ch21/e4_incident_data/starter/incident.py` (four functions). *Acceptance:*
`tests/test_incident.py` passes: rates over the real time, restarts and missed snapshots, the slow
stage whichever it is, also with coarse polling, and the order of the onsets. Then answer in
`NOTES.md` what you ask for before you agree with an operator's diagnosis. *Time:* 60 minutes.

**Exercise 21.5 (E): Bisect a regression through commits that do not build.** *Goal:* find the
first bad commit with `git bisect run` in a history with untestable commits, and report the
candidates when bisect cannot decide. *Starter:* `exercises/ch21/e5_bisect/starter/bisect_tool.py`.
*Acceptance:* `tests/test_bisect.py` passes: untestable commits are skipped, not blamed; three
candidates when they sit next to the defect; the log of an older and a newer git both parse; the
repository is left as it was. Then answer in
`NOTES.md` what makes a MiniDAQ commit untestable and how the check keeps a skip from hiding a real
failure. *Time:* 30 minutes.

## MiniDAQ milestone: a server that says what happened {.unnumbered}

::: box-milestone
**Goal.** A running server shows its last events to an observer; a crashing server writes a
report that names the signal, the build and its last events, and still dies of the signal with a
core dump; a core is opened only with its own build; reviews follow a controlled checklist; every
problem report from MDQ-PR-019 on has a root cause.
**Start:** tag `ch20`. **End:** tag `ch21`.
:::

1. Write change request CR-0007 and ADR 0016 before the code; add SRS-DIAG-001 to 005 (SRS
   version 9) and let an observer use `diagnostics` (SRS-SEC-003).
2. Add `minidaq/core/flight_recorder` with its unit tests, including the concurrency test under
   ThreadSanitizer, and `bm_flight_recorder`; record the measurement in `measurements/ch21/`.
3. Record the events of SRS-DIAG-004 in the acquisition service, the control protocol and the UDP
   detector, with a test for each.
4. Add `minidaq/rt/crash_report` with its tests (two death tests, which the sanitizer presets
   skip because the sanitizers handle these signals themselves), install it first in
   `minidaq_server`, and add `--crash-report FILE`.
5. Add `diagnostics` to the control protocol (API 2.1) and to `minidaq_ctl`, and the system test
   that reads a running server's events and crashes a server to check its report and its core.
6. Add `tools/core_build_id.py` and `tools/postmortem.sh` with their tests, and the tool list
   entry for them.
7. Write the code review checklist as a controlled document and reference it from the design
   file; add root causes to MDQ-PR-019 to 023 and the check in `tools/anomalies.py`.
8. Fix MDQ-PR-024: `VERSION` to `0.4.0-dev`, `tools/check_version.py` with its tests, the SOUP
   reviews for 0.4.
9. Add Exercises 21.1 to 21.5.

**Definition of done.** `ci/run_all.sh` is green on all six presets and static analysis reports
nothing; every GitHub job is green on the tagged commit; `bm_flight_recorder` meets SRS-DIAG-005;
the system test's crash leaves a report with the sender, the version and the run's events;
MDQ-PR-024 is closed; every starter of the chapter fails. Tag `ch21`.

## Check yourself {.unnumbered}

1. In what order do you read a change, and why the interface before the implementation?
2. Which defects does a review find that tests do not? Give one example from Exercise 21.1 and
   say why its unit test could not find it.
3. Write a finding for a test that sleeps for two seconds before it checks a counter. What
   severity, and why?
4. What decides whether the kernel writes a core, and where it goes? Name two settings and where
   they are set for a service.
5. Why can a core opened with another build of the same program show plausible, wrong stacks?
   How does the build ID prevent it?
6. A core shows `si_code` −6 and an address that is a small number. What happened, and what does
   MiniDAQ's crash report add?
7. Why does each thread of the flight recorder write its own ring? What did a shared counter
   cost, and why?
8. Why are the fields of a seqlock slot relaxed atomics rather than plain integers? Which fence
   orders what?
9. Name four things a signal handler must not do, and say what MiniDAQ's handler does instead.
10. Why does the crash handler re-raise the signal instead of calling `_exit`?
11. What are the parts of a root cause in MiniDAQ's problem reports, and why is "the escape" often
    the most useful one?
12. Why is "human error" not a root cause?
13. What does exit status 125 mean to `git bisect run`, and what goes wrong if the check returns 1
    for a commit that does not build?
14. In a pipeline with bounded queues, which stages slow down after one stage does, and in what
    order? Why is the stage that loses data rarely the cause?

## Summary {.unnumbered}

- A review checks what tests cannot: concurrency, error paths, boundaries, lifetimes and the
  tests themselves. A checklist directs the reading and makes the review a record; a finding is
  one problem, with a severity, what was seen and why it matters.
- A core dump is the evidence of record of a crash, if the system keeps it and it is opened with
  its own build. The build ID in the core and in the program must match; `tools/postmortem.sh`
  checks it and reads the signal, every thread's stack and the faulting frame.
- MiniDAQ's flight recorder keeps the last 256 events of each thread in memory, always on: a
  seqlock per slot, a snapshot without locks or allocation, about 33 ns an event, most of it the
  clock. A shared counter made it 213 ns with four threads.
- `diagnostics` (control API 2.1) shows a running server's events to an observer; the events hold
  codes and numbers only.
- The crash report is written by the dying process with async-signal-safe calls only, on an
  alternate stack, and the process still dies of its signal so that the core is written. A core
  and a report together say more than either.
- The first crash report found MDQ-PR-024: every build of Part IV called itself 0.3.0. A check
  now ties the version to the commit.
- A root cause is a chain of whys, a cause in a category the organization controls, and an escape:
  why the checks did not find it. Every problem report from MDQ-PR-019 on has one, checked by the
  documentation tests.
- `git bisect run` finds the first bad commit in about log2(n) steps; exit status 125 skips what
  cannot be tested, and candidates are reported, not guessed. A check starts from a clean state.
- In a pipeline, the order of the slowdowns is the evidence: the stages after a slow stage starve
  at once, the ones before it slow when its queue is full.

## Further reading {.unnumbered}

- IEC 62304:2006+A1:2015, *Medical device software: Software life cycle processes*, clause 5.5
  (software unit implementation and verification) and clause 9 (software problem resolution
  process).
- ISO 13485:2016, *Medical devices: Quality management systems*, clause 8.5.2 (corrective
  action).
- A. Bacchelli and C. Bird, "Expectations, outcomes, and challenges of modern code review",
  *Proceedings of the 35th International Conference on Software Engineering (ICSE)*, 2013.
- Google, *Engineering Practices Documentation: How to do a code review*,
  <https://google.github.io/eng-practices/>.
- A. Zeller, *Why Programs Fail: A Guide to Systematic Debugging*, 2nd edition, Morgan Kaufmann,
  2009.
- *Debugging with GDB*, the GNU debugger's manual, <https://sourceware.org/gdb/documentation/>:
  core files, `$_siginfo`, and separate debug files found by build ID.
- Linux manual pages `core(5)`, `signal-safety(7)` and `sigaltstack(2)`, man7.org.
- H.-J. Boehm, "Can seqlocks get along with programming language memory models?", *Proceedings of
  the 2012 ACM SIGPLAN Workshop on Memory Systems Performance and Correctness (MSPC)*, 2012.
- R. O'Callahan, C. Jones, N. Froyd, K. Huey, A. Noll and N. Partush, "Engineering record and
  replay for deployability", *Proceedings of the 2017 USENIX Annual Technical Conference*, 2017
  (the design of rr).
- The git documentation, `git-bisect(1)`, git-scm.com/docs/git-bisect: `bisect run` and the
  meaning of exit status 125.
