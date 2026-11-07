```{=latex}
\cleardoublepage\phantomsection
\addcontentsline{toc}{part}{Appendices}
\appendix
```

# Software architecture and design {#app-architecture}

Chapter 6 gave MiniDAQ its shape: four layers, ports owned by the application, a table-driven
state machine, a validated configuration and a control API. Thirty-one chapters later the shape
has held, and a great deal has been built inside it: a readout link, a coincidence sorter, a
list-mode writer, front-end boards and their slow control, a platform with a watchdog and signed
updates, a calibration, and an offline chain from corrections to DICOM. This appendix looks at the
whole architecture at once, the way a reviewer, an auditor or a new member of the team would. It
goes deeper than Chapter 6 in four directions:

- **what IEC 62304 expects of an architecture**, and where MiniDAQ's records meet each
  expectation;
- **the software items and their boundaries**: which items exist, why they are drawn where they
  are, what the processes and the layers do and do not separate, and where the SOUP sits;
- **the patterns and their tradeoffs**: each recurring design move, the decision records that
  chose it, what it cost and what would make the team choose differently;
- **how the architecture is kept true and how it is designed for change**: the checks that fail
  when the code and the description drift apart, and the versioned interfaces that let one part
  change without the others.

The appendix is a reference to read after the chapters, or alongside a chapter when you want the
whole picture around one part. It quotes the repository's own records: the architecture
description `docs/architecture/architecture.md`, the item list
`docs/architecture/software-items.json`, the layer rules `docs/architecture/layers.json`, the
SOUP list and the 32 decision records in `docs/adr/`. When a number or a rule appears here, it
comes from one of those files, and the checks that keep those files true are in the last
sections.

## What IEC 62304 asks of an architecture

The standard's development process has a separate activity for the architecture, between the
requirements and the detailed design. This section describes it in the book's words, as Chapter
13 did for the whole standard; it does not reproduce the standard's text, and the exact clauses,
and which of them apply to which safety class, are in the edition your organization works to
(read it; the amendment of 2015 changed several of them).

In outline, the architecture activity asks the manufacturer to:

1. **Turn the requirements into an architecture** that describes the software's structure and
   identifies its software items. An item is any part of the software that is identified for
   classification, verification and change: a whole system, a component or a single unit.
2. **Describe the interfaces** between the items, and between the items and the components
   outside the software: the hardware, the operating system and other software.
3. **State the functional and performance requirements of every SOUP item** that the
   architecture uses, and the hardware and software that each SOUP item needs in order to run
   correctly.
4. **Identify any segregation that a risk control relies on**, and state how the segregation is
   made effective.
5. **Verify the architecture**: that it implements the system and software requirements, that
   it supports the interfaces and the risk controls, and that it is consistent with the
   requirements and the items.

The detailed design activity that follows subdivides items into units. For an item of the highest
class it adds a design of every unit and of the interfaces between units, detailed enough to
implement, and a verification of that design. For a lower class the subdivision itself is enough.
This is why the boundary of an item matters so much: the class is decided per item, and the
class decides how much design, documentation and verification an item needs (Chapter 14).

What the standard does not ask for is just as important. It names no method, no notation, no
layering, no diagram style and no document layout. A manufacturer may describe the architecture
in text, in tables, in UML or in code, as long as the description identifies the items,
interfaces, SOUP and segregation, and as long as the description is verified and kept under
change control. MiniDAQ uses text and tables in Markdown, two Graphviz diagrams and three JSON
files that tools read, because tools can check JSON and reviewers can read tables. A company may
require something else (assumption: confirm with team which templates and notations your quality
system prescribes).

The map from these expectations to MiniDAQ's records:

| Expectation | Where MiniDAQ meets it | What checks it |
|---|---|---|
| Structure and items | `architecture.md` sections 4 and 5; `software-items.json` (22 items, 21 shipped) | `tools/check_items.py`: every source file in exactly one item |
| Interfaces between items | `architecture.md` section 5; the port headers in `minidaq/include/minidaq/control/ports.hpp` | Unit tests with fake ports; the layer check |
| External interfaces | `architecture.md` section 2; the format specifications in `docs/formats/`, the register map, ICD-FEB, the DICOM conformance of Chapter 35 | Format tests against independent readers; `docs.regmap` |
| SOUP requirements | `docs/regulatory/soup-list.md`, one table per SOUP item | `tools/check_soup.py` against the pins in `cmake/Dependencies.cmake` |
| Hardware and software SOUP needs | The same tables, and `platform/platform.json` | `tools/platform_check.py` at installation |
| Segregation | `architecture.md` section 10 | `check_items.py` rule 3 (same process, same class) |
| Verification of the architecture | `architecture.md` section 11; review of each ADR with its code | The checks above, run by `ctest` on every push |
| Change control | Document version and history; the change requests | `tools/design_file.py`, the commit policy (Chapter 36) |

## The software items and why they are drawn where they are

MiniDAQ's 22 items are listed in `software-items.json` with the files each owns, the process it
runs in, its class, the hazards it can contribute to and a rationale. The table in section 4 of
the architecture description repeats them for people. This section explains the reasoning behind
the boundaries, which the table states only one line at a time.

### Items follow responsibility, not files or layers

An item is the unit that is classified, verified and changed together, so its boundary should
enclose one responsibility that can fail in one way. The test for a good boundary is a question a
reviewer asks of every change: *which item does this change, and does the change stay inside it?*
When most changes stay inside one item, the boundary is right. When a typical change touches three
items, either the items are cut across a responsibility or one item depends on the internals of
another.

Three of MiniDAQ's boundaries show the rule at work.

- **The sorter, the merger and the energy filter are three items, although all three live in
  `processing/`.** Each decides something different about the data: which singles pair into a
  coincidence, in which order many boards' singles go downstream, and which singles have an energy
  worth keeping. Each has its own requirements (SRS-SORT, SRS-MERGE, the energy window rows), its
  own ground-truth tests and its own failure. Folding them into one `processing` item would make
  every change to the energy filter a change to the item that decides every coincidence. The item
  map draws them by path prefix (`processing/coincidence_sorter`, `processing/stream_merger`), and
  the longest prefix wins, so the rest of `processing/` falls to the `processing` item.
- **The item `hw` spans three layers.** The typed registers and the bus interface (`hw/`) are in
  the core layer; the reader of the hardware description (`config/hardware_config`) is in the
  application layer; the adapter that reports the slow control to the service (`control/hardware`)
  is in the adapters layer. They are one item because they are one responsibility: keeping the
  boards' bias right for their temperature and switching it off on a fault (hazard H-10 of the risk
  analysis). Layers and items answer different questions. A layer says what code may depend on
  what; an item says what is classified and changed together. Nothing requires them to coincide.
- **`sim` is an item of the shipped server, not a tool.** The simulated detector is linked into
  `minidaq_server`, and known anomaly MDQ-PR-009 records what that costs: code meant for tests runs
  in the process that acquires patient data, so it carries the server's class and its verification,
  and an acquisition configured with a simulated source would produce plausible but invented data
  (HZ-3). The run record names the source, so such data is identifiable. The anomaly's own
  resolution is the architectural one: a product build leaves the simulator out, or refuses it
  outside a service mode.

### Processes are the only segregation MiniDAQ claims

Section 10 of the architecture description is short and blunt: inside `minidaq_server` there is
no memory isolation between items, so a memory error in any of them can corrupt any other.
MiniDAQ therefore claims no segregation inside the process, and every item in it has the class of
the highest one. The item `metrics`, which only observes latencies, and the item `audit`, which
only records, would be class A on their own; they are developed and verified as class B, and their
rationales in the item list say so.

The rule that `check_items.py` enforces as its rule 3 (all items of one process share the highest
class there) is a statement about C++, not about MiniDAQ. One out-of-bounds write in a histogram
can overwrite a sorter's window; a use-after-free in the audit log can corrupt a batch in flight.
A language with memory safety, a separate address space or a hypervisor partition changes that
argument; a namespace, a library boundary or a code review does not.

The figure below shows the boundaries that do segregate: three processes, each an item of its own
or a group of items, and the interfaces that cross between them. Each crossing validates what
comes in.

```{.dot include="book/src/diagrams/app-boundaries.dot" caption="MiniDAQ's boundaries. A thick box is a process; the dashed boxes inside the server are its layers, which order dependencies but do not isolate memory. A dashed arrow crosses a process boundary through an interface that validates its input. The component shapes are SOUP." width="100%"}
```

- **`minidaq_ctl`** runs in its own process and reaches the server only through the control
  protocol, whose every request the server validates. Until Chapter 17 that let `ctl` be class A:
  a defect in the client could only send a wrong but valid command, which the server reports back.
  Since CR-0004 the client holds an operator token and must check the server's certificate before
  it sends it, so a defect in the client can hand a token to an impostor (HZ-4). Process isolation
  still separates its memory from the server's, but no longer limits what its failure can cause,
  and `ctl` became class B. Segregation lowers a class only when it bounds the consequence, not
  merely the memory.
- **`minidaq_update`** runs as root in its own process and shares nothing with the server but the
  files it installs, which the server cannot write (`ProtectSystem=strict` in the unit). The
  updater is installed by the platform image outside the two slots, so a defective update cannot
  replace the program that rolls it back (Chapter 25).
- **The offline chain** (corrections, reconstruction, analysis, DICOM export) runs after the
  acquisition, in other processes, from files. In this book it is a set of tools of class T3
  (TL-30 to TL-44), not items of the device, because MiniDAQ is a teaching DAQ and the images are
  never used for a diagnosis. In a scanner the same code is software of the device. Chapter 35's
  hazard HZ-5 (an image filed under the wrong patient) is serious, which would make the export a
  class C item unless a control outside the software is credited (assumption: confirm with team).

### What class C would add

No MiniDAQ item is class C, and the classification rules in `check_items.py` would refuse one in
the server process without raising every item there to C. If a risk analysis found a hazard that
only a class C item could carry, the architecture would have two choices.

1. **Raise the process.** Every item in `minidaq_server` becomes class C: a detailed design of
   every unit and every interface between units, its verification, and the other activities the
   standard reserves for that class. For a server of about 18,000 lines of C++ that is a large and
   permanent cost, paid by code that has nothing to do with the hazard.
2. **Segregate the item.** Move the class C responsibility into a process of its own, with an
   interface that validates everything it receives and a failure mode that the rest cannot
   corrupt. The bias control of the boards is the natural candidate in MiniDAQ: the slow control
   already runs on its own thread, owns the bias, reports through a port and is backed by the
   board's own hardware protection above 60 C (ADR 0017). Moving it to a process would cost an
   interprocess protocol and its tests, and would bound the class C work to one small program.

The second choice is the usual one in devices, and it is the reason a long-lived architecture
should keep its most dangerous responsibilities small, behind ports, and free of dependencies on
the rest. MiniDAQ kept that option open without needing it.

## The interfaces

An interface is where two parts of the software meet, or where the software meets something it
does not control. The architecture description lists both kinds; this section adds what they have
in common and the rules that keep them stable.

### Interfaces inside the server

The internal interfaces are C++ classes, and every one of them that crosses a layer is owned by
the layer that uses it. `DetectorPort`, `CoincidenceSinkPort`, `HardwarePort` and `AuditSink` are
declared by the application layer, in `control/ports.hpp`, and implemented by adapters. The core
does not know they exist; the service knows only the ports. Chapter 6 showed the declarations. The
contracts worth repeating here are the ones about threads and failure, because those are the
parts a compiler does not check:

| Interface | Called on | Must not | Reports failure by |
|---|---|---|---|
| `DetectorPort::read` | the source stage thread | block for long, allocate, throw | `fault()`, polled by the monitor thread |
| `CoincidenceSinkPort::write` | the writer stage thread | throw | `fault()`; `close()` returns an error |
| `CoincidenceSinkPort::close` | the service, once, after the stages drained | be called twice | an error string: the run ends in a fault |
| `HardwarePort` queries | control threads | touch the bus | `fault()` and `not_ready()` from the last cycle's copy |
| `AuditSink` | control threads only | be called from a stage | the audit write's own error, counted |
| `rt::Heartbeat::beat` | any loop, once per pass | wait | nothing: the watchdog reads its age |

Three rules run through the table. **The hot path never waits on the control plane**: a stage
thread calls only `read` or `write`, and everything else is polled from the monitor thread or the
control threads. **Failures are values, not exceptions, at a thread boundary**: a fault is a string
that the monitor reads, because an exception thrown on a stage thread has nowhere useful to go.
**Each call has one owner thread**, written in the header comment, so ThreadSanitizer and a reader
can check the rule against the code.

The hardware interface goes one level lower. A `RegisterBus` is the only way to reach a board,
and every implementation reports every failure in its return type:

```{.cpp include="minidaq/include/minidaq/hw/register.hpp" snippet="bus"}
```

The memory-mapped bus, the simulated board and the bus that a test makes hang are three
implementations of these two functions. The typed registers above them are generated from one
specification (`tools/regmap_gen.py`, TL-25), so a write to a read-only register is a compile
error, not a review finding.

### External interfaces and their versions

Every external interface that MiniDAQ owns carries a version, and every reader checks it. The
versions at this edition:

| Interface | Version | Rule for a reader |
|---|---|---|
| Control protocol (NDJSON over TCP) | API 2.4 | A request whose major version differs is refused with `unsupported_api`; the status fields are part of the API (ADR 0013) |
| Acquisition configuration | schema 1.4 | Its own major version and any minor up to its own; a newer minor is refused, not half understood; unknown keys are errors |
| Hardware description | schema 1.1 | As the configuration |
| Calibration table | format 1.0 | Version, CRC-32, scanner serial, expiry and the limits of a working detector, checked before use |
| Readout packets | MDQ-R1 | A sequence number per source; a bad packet is counted by reason, never silently dropped |
| List-mode files | MDQ-L1 | A versioned header with JSON metadata; CRC-32 per block header and payload |
| Firmware contract | ICD-FEB version 1 | The firmware's identity and version checked every slow-control cycle (ADR 0019) |
| Update bundles | Ed25519-signed manifest | Trusted only through the keys installed by the platform |
| DICOM export | the conformance of Chapter 35 | The archive's status per instance decides delivery |

Two habits make these versions useful rather than decorative. The first is that **a reader refuses
what it does not understand**: a configuration of a newer minor version is refused, because a
reader that skipped a key it did not know would run an acquisition with settings the operator did
not choose. The second is that **the version is in the data, not in the file name or the build**:
a list-mode file names its own format, and a response names its API, so a record read years later
can still be interpreted.

## Concurrency architecture

Concurrency is an architectural decision, not an implementation detail, because the threads decide
which data is shared, who may block whom, and what a failure on one thread does to the others.
MiniDAQ's server has a fixed set of threads, decided at start:

- **Five pipeline stages** (source, decode, sort, pair, write), joined by batched SPSC channels
  (ADR 0002), each optionally real-time from an `rt_profile` (Chapter 4).
- **The service's monitor**, every 20 ms: port faults, late singles, the end of the run, latency
  snapshots.
- **One list-mode I/O thread per run**, which writes blocks, calls fsync by policy and returns
  buffers to the writer stage (ADR 0012).
- **The slow control**, which owns the boards' bias and runs its cycle (ADR 0017).
- **The control server**, a `poll()` loop over up to eight clients.
- **The watchdog** under systemd, which pings only while every heartbeat is recent (ADR 0020).
- **The main thread**, which waits for a signal and shuts down in order.

The sharing rules are few and strict. Stage threads share nothing with each other except the
channels between neighbors, and nothing with the control plane except atomics: counters written by
one thread each with relaxed stores, histograms, the stop request and the heartbeats. Control
threads take the service's mutex; stage threads never do. No memory is allocated on a stage thread
after start, because every batch comes from a pool the channel allocated at construction and
returns through a second ring.

The channel's ring shows how small the shared surface is. The producer writes a slot and publishes
its index with a release store; the consumer reads the index with an acquire load before it reads
the slot; each side caches the other's index and reads the shared atomic only when the cache says
the ring looks full or empty. Nothing in the hot path needs sequential consistency, a lock or a
system call. A full pipeline appears as *no empty batch available* at the producer, which is the
one place where the drop policy acts and counts.

This architecture made three things checkable that would otherwise be arguments. ThreadSanitizer
runs every test with these threads (the `tsan` preset), and the stress run repeats the concurrent
tests a hundred times under it for each release; it found the lock-order inversion of Chapter 6,
between the state machine's two mutexes, before any test had hung. And the
watchdog can tell a hung server from a slow one because each loop that matters stamps a heartbeat:
the watchdog asks the threads whether they are alive instead of assuming it.

## SOUP boundaries

A SOUP item is software the project did not develop for the device and cannot fully verify: a
library, the operating system or a toolkit. The standard asks for its functional and performance
requirements and for what it needs to run; Chapter 7 wrote those down in `soup-list.md`. The
architecture's own contribution is to decide **where** each SOUP item is allowed, because the
boundary decides what a defect in it can reach.

| SOUP | Allowed in | Forbidden in | Why the boundary is there |
|---|---|---|---|
| nlohmann/json 3.12.0 | application, adapters, apps | core (`layers.json`) | Allocates and throws; parses untrusted input. Kept off the hot path, so a parser defect cannot alter a coincidence |
| OpenSSL 3 (platform) | `access`, `tls`, `update` (linked privately) | core and application, and every public header | Large and security critical; reaches the network. Confined to the items that need TLS and signatures |
| C++ and C libraries, kernel, systemd, GNU tar | everywhere; tar only in `update` | nowhere | The platform. Pinned as one definition (`platform/platform.json`) and checked at installation |
| GoogleTest, Google Benchmark | tests and benchmarks | the shipped programs | Never shipped; qualified as tools |
| pybind11 3.1.0 | the projector's Python module | the server | The offline chain only |
| pydicom, pynetdicom | the DICOM export's tests | the export itself | Independent oracles; nothing of them is needed to export |

The rule for the first two rows is not only documented but enforced. `layers.json` lists the
headers each layer may not include, and `tools/check_layers.py` fails the unit tests if a file in
the core includes `nlohmann/`, `openssl/` or a socket header:

```{.json include="docs/architecture/layers.json"}
```

Two consequences of drawing the boundaries this way show up in the records. A defect in the JSON
library can misread a configuration (HZ-3) or crash the control plane, but it cannot change the
data of a run in progress, which is why the SOUP entry for nlohmann/json names no hot-path
requirement. And a security advisory in OpenSSL concerns two items and the three programs that link
them, not the whole server; the vulnerability triage (threat model, section 8) can say which features the advisory touches
and whether MiniDAQ uses them, because the SOUP entry lists the features used and those not used.

The last boundary is the test oracle. A SOUP item used only by the tests, such as pydicom checking
the DICOM export's files, is not in the product but is part of the product's verification. Its
failure cannot harm a patient directly; it can let a defect through. That is why the export's own
strict reader checks the same files: measurements/ch35 records a sequence with its item tag in the
wrong byte order that pydicom read without a warning and the export's reader refused. Two
independent checks that disagree are worth more than one that is trusted.

## Patterns, and the decisions that chose them

The same few design moves recur through the book. Each was chosen in a decision record with the
options it rejected. This section names the pattern, where MiniDAQ uses it, and what it costs,
because a pattern without its cost is advice, and advice does not survive a change of requirements.

### Ports and adapters

The application owns interfaces for everything it needs from the outside world (a detector, a
sink, the hardware, an audit trail), and adapters implement them (Chapter 6). The service can be
tested with a backwards detector, a sink that fails on its third block and a board that overheats,
without hardware; a UDP receiver replaced the simulator in Chapter 9 without a change to the
service.

*Cost:* a virtual call per batch on the hot path, which batching makes rare, and one more class
per external thing. *Revisit when:* never for the control plane;
for the hot path only if a profile shows the call, and then by making the port a template
parameter, not by removing it.

### Batched, single-producer single-consumer channels (ADR 0002)

Each stage has exactly one producer and one consumer, and they exchange batches of a few thousand
items through pre-allocated pools. The decision rejected a mutex-protected queue (below the
throughput requirement, and a lock on the hot path invites priority inversion), a bounded MPMC
queue (pays for safety one producer does not need, and several consumers break ordering) and one
thread doing everything (no stage can be pinned, measured or isolated).

*Cost:* a stage cannot be parallelized by adding workers without a merger to restore the order,
and the batch size trades latency for throughput (`max_batch_delay_us` bounds the wait).
*Revisit when:* a stage cannot keep up on one core; then split it by sector into several
pipelines joined by the watermark merger of ADR 0010, which keeps each channel SPSC.

### An explicit state machine (ADR 0005)

States and events are enums, transitions are one `constexpr` table, and a small wrapper applies
events under a lock and notifies listeners outside it. A JSON copy of the table is compared with
the code by a test, so the diagram in the architecture description cannot drift. The rejected
options were flags spread over functions, the State pattern (each state local, the whole set
spread over classes) and a state machine library (SOUP and templates for five states).

*Cost:* actions are not in the table; the service implements them around it, so a reader looks in
two places. *Revisit when:* the machine grows guards that depend on data (for example a calibration
state that allows `start` only with a valid table); then the guard belongs in the service, and the
table stays a table.

### Validate at the boundary, refuse what is not understood

Every input from outside (configuration, hardware description, calibration table, control
requests, readout packets, update bundles, archive responses) is parsed by a reader that checks
types, ranges and versions and reports **every** error with its location, before anything acts on
it. An invalid configuration changes nothing; an unknown key is an error with a suggestion; a
newer minor version is refused. Inside the boundary the code works with validated types and does
not check again.

*Cost:* readers are long and their tests longer; a field added to a format needs a reader change,
a schema change and a test. *Revisit when:* never in a device. This is the pattern that the
fuzzers of Chapter 7 test hardest, and it is the reason they found crashes in the readers and not
in the code behind them.

### Count everything, drop only by policy

Every stage counts what it received, passed, filtered and dropped, and only the source may drop,
by a configured policy. The sink pushes back instead of dropping. The end-to-end check of Chapter
33 turns this into conservation equations over the counters, and a lost single becomes a failed
equation with a name. The UDP receiver goes further and asks the kernel for the drops it caused
itself (ADR 0018).

*Cost:* counters on every stage, relaxed atomics on separate cache lines, and status fields that
are part of the versioned API (ADR 0013), so a counter cannot be renamed freely. *Revisit when:*
never. A DAQ that loses data silently is the hazard HZ-1.

### Generate from one specification

The register map, the design file index and the SBOM are generated from one source each, and the
schema document of the configuration and the state diagram are compared with the code; either way
a test fails while a copy differs from its source. The typed registers (ADR 0017) are the strongest case: the compiler
refuses an access the specification forbids.

*Cost:* a generator is a tool to qualify (TL-25), and generated code has to be readable enough to
review. *Revisit when:* the firmware team already has a register tool; then generate from its
output instead of keeping a second specification.

### Own the small, buy the large

MiniDAQ wrote its own framing, property harness, flight recorder, register generator, list-mode
format and DICOM encoder, and bought JSON, TLS, the test framework, the benchmark library, the
binding generator and the numerical libraries. The rule, visible across ADRs 0003, 0004, 0012,
0014, 0015, 0016, 0017 and 0030, is that a part is written in house when it is small, central to
what the book teaches and testable byte for byte, and bought when it is large, security critical
or specialist. Every bought part is SOUP with requirements; every own part is code to maintain.

*Cost:* both columns have one. An own DICOM encoder is code a product would more likely replace
with a toolkit (ADR 0030 says so); an own property harness has fewer generators than RapidCheck.
*Revisit when:* the own part grows beyond what one engineer can review in an afternoon, or a
second product needs it.

### Durable before acknowledged

A list-mode file gets its final name only after its data and its directory are synced; a run is
complete only when the sink's `close` has stored the run record; a DICOM instance leaves the
outbox only on the archive's success status; an update switches slots only after the new slot is
verified and written. The pattern is the same each time: write to a temporary place, make it
durable, then make it visible in one atomic step, and let a crash at any point leave either the
old state or the new one.

*Cost:* fsync time, temporary files, journals and the tests that cut the power after every step
(Chapters 12 and 25). *Revisit when:* a measurement shows the fsync policy limits throughput; then
change the policy, not the pattern.

### Offline what can be offline (ADR 0022)

The corrections, the reconstruction, the analysis and the DICOM export run after the acquisition,
from the list-mode files and the run record. The server records; the physicists' tools compute;
the run record ties them together. A change of a correction method is a change of a tool, not of
the class B server, and the same data can be processed again with a better method.

*Cost:* no corrected image during the scan, and a run record that must carry everything the tools
need (the `corrections` object). *Revisit when:* a clinical workflow needs an image before the
patient leaves the table; then a reconstruction service beside the server, still fed by files or
a stream it cannot write back to, keeps the boundary.

## Tradeoffs at a glance

The table collects the main decisions with the alternative a reasonable team could have chosen,
what MiniDAQ's choice costs, and what evidence would reverse it. Reversing a decision is not a
failure; it is a new ADR that supersedes the old one, as ADR 0012 superseded ADR 0007.

| Decision | Chosen | Main alternative | Cost of the choice | What would reverse it |
|---|---|---|---|---|
| Stage hand-off (0002) | Batched SPSC rings | MPMC queue, workers per stage | One core per stage | A stage that cannot keep up on one core |
| Control transport (0003) | NDJSON over TCP | gRPC, REST | Own framing and server loop | Many clients in other languages, streaming needs |
| JSON (0004) | nlohmann/json | simdjson, Boost.JSON | Allocation, exceptions | JSON on the hot path (it must not be) |
| State machine (0005) | `constexpr` table | State pattern, library | Actions outside the table | Data-dependent guards in many states |
| Language level (0006) | C++20 and a shim | C++23 with GCC only | A small header to maintain | Both compilers' libraries ship `std::expected` |
| Readout link (0009) | UDP with sequence numbers | TCP, a dedicated link | Loss possible, made visible | A loss rate the counters show is too high |
| List mode (0012) | Own block format | HDF5, PETSIRD | A format to specify and keep | A reconstruction that reads a standard format |
| Control security (0014) | Tokens over TLS 1.3 | Mutual TLS, Unix sockets | Tokens to store and rotate | A site that runs its own certificate authority |
| Property tests (0015) | Own small harness | RapidCheck | Fewer generators | Many new properties per release |
| Crash evidence (0016) | Flight recorder and report | Crashpad | Own signal-safe code | A fleet large enough to need minidumps |
| Registers (0017) | Generated typed C++ | Hand constants, SystemRDL | A generator to qualify | The firmware team's own register tool |
| Receive path (0018) | Kernel sockets, full accounting | AF_XDP, DPDK | Copies and stack cost per packet | Measured drops at the socket at target rate |
| Updates (0020) | Signed bundles, A/B slots | Package manager | Two slots of disk | A platform with its own signed image updates |
| Corrections (0022) | Offline from list mode | In the server | No image during the scan | A workflow that needs one |
| Projector (0024) | C++ with pybind11 | numpy, Numba | Two languages in one tool | A reconstruction moved entirely to C++ or a GPU |
| DICOM (0030) | Own encoder, checked by toolkits | A toolkit as SOUP | Code to maintain | A product, which would likely choose the toolkit |

## Keeping the architecture true

An architecture description is a claim about the code. Claims drift. A file is added and belongs
to no item; an include crosses a layer; a decision record names a version the code no longer
uses; a diagram shows a state the table no longer has. MiniDAQ's answer is to make every claim
that a machine can check a test, and to leave to reviewers only the claims that need judgment.

| Claim | Check | When it runs |
|---|---|---|
| An include respects the layers and the forbidden headers | `tools/check_layers.py` (`architecture.layers`) | Every `ctest` run |
| Every source file is in exactly one item; classes follow the rules | `tools/check_items.py` (`architecture.items`) | Every `ctest` run |
| Every requirement names an item; the trace matrix is complete | `tools/trace_matrix.py`, `tools/req_lint.py` | Every `ctest` run |
| The state diagram equals the transition table | a unit test against `acquisition-states.json` | Every `ctest` run |
| The register map equals its specification | `docs.regmap` | Every `ctest` run |
| SOUP pins equal the SOUP list and the SBOM | `tools/check_soup.py`, `tools/make_sbom.py` | Every `ctest` run, every release |
| A controlled document that changed has a new version | `tools/design_file.py --since` | Release checks |
| A change of a requirement, a hazard or the item map names a change request | `tools/check_commits.py` (Chapter 36) | CI, from the policy's first commit |
| Where the changes concentrate; no file without an owner, no prefix without a file | `tools/survey.py` (Chapter 34) | On demand, at a release |

The last row is the one that looks forward. The survey of Chapter 34 counts the commits and changed lines per
item from the history, finds the file hotspots and checks the item map itself: product files that
no item claims, files two items claim, and prefixes that claim no file. Two items whose changes
always come together are a sign that the boundary between them is in the wrong place; an item
that never changes is either finished or unused. Neither is a
failure of a test, but both are inputs to the next architecture review.

What no check can do is decide whether the architecture is still the right one. That is the
review's job, and it has two triggers in MiniDAQ's process. Every ADR is reviewed with the code
that implements it, in the same change. And at each release, the architecture description, the
item list and the open issues in section 12 of the description are read again against what the
release changed, and the description's version and history record the result.

The reviews do find drift that the checks miss. Writing this appendix found two pieces. Section
12 of the architecture description listed "ADR 0001 to 0020" as its decisions, twelve records
behind, and its table of threads in section 6 had no row for the slow control's thread, which
Chapter 22 added. No test compared the range with the directory or the table with the threads the
code starts. Both fixes were a line each and a new version of the document (version 19), and the
lesson is general: a sentence that summarizes a list goes stale as soon as the list grows. A link
to the list, or a check, is better than a summary of it.

## Designing for change

A DAQ in a scanner lives for ten years or more. Its detectors are replaced by a new generation,
its operating system by a newer release, its compiler and libraries by versions that did not exist
when it shipped, and its team by people who did not write it. The architecture's job over that
time is to make each of those changes local. MiniDAQ's design prepared for several of them, and
the chapters exercised some.

- **A new detector or readout.** The detector is a port. Chapter 9 replaced the in-process
  simulator with a UDP receiver without changing the service; Chapter 22 added the boards behind a
  second port. A new front end with another packet format would add a decoder in `format/` and an
  adapter, and change no item above them.
- **A new acquisition setting.** The configuration is versioned and its reader refuses what it
  does not understand. Schemas 1.1 to 1.4 each added a section with defaults, and every file of an
  earlier minor version stayed valid. A change that removed or redefined a key would be a new
  major version, which old readers refuse by design.
- **A new client of the control API.** The API is versioned, the status fields are part of it,
  and `minidaq_ctl` is only the reference client. A new console needs the protocol document and a
  token; it does not need MiniDAQ's code.
- **A new compiler or standard library.** The `Expected` shim becomes an alias of
  `std::expected` when the library has it, so code written against it is already valid C++23.
  The workflow presets build with two compilers, and the hardened release build is checked by
  reading the binaries, not the flags.
- **A new platform release.** The platform is one definition (`platform/platform.json`), checked
  at installation; a new release is a new definition, a new SOUP review and a run of the platform
  tests, not a search through the code for assumptions about the system.
- **A new reconstruction or correction method.** The offline chain reads files and a run record.
  A better method is a new tool version, run again on the same data; the class B server does not
  change.
- **A new team.** The decisions are in the ADRs with their rejected options, the history of every
  controlled document is in the document, and every commit since the policy's first one names its
  change request when it changes a requirement. A new engineer can answer *why is it like this?*
  from the repository, which is the question that otherwise costs a team the most time.

The common thread is that each likely change has one place to happen and a check that notices when
it happens somewhere else. That is what an architecture is for in a regulated product: not a
diagram for the file, but a set of boundaries that make the next change cheap to make and cheap to
verify.

## Checklist for an architecture review

Use it on MiniDAQ at a release, or adapt it to your team's procedure (assumption: confirm with
team which review records your quality system requires).

1. Every item in the item list still has one responsibility, and the history shows no two items
   that always change together.
2. Every class follows from the worst hazard of the item and of its process; the rationale names
   the hazards.
3. Every crossing between processes validates its input, and every claimed segregation bounds
   the consequence of a failure, not only the memory.
4. Every SOUP item is used only where the layer rules allow it; its requirements list the features
   used; its anomaly review is current.
5. Every internal interface states its threads and its failure reporting; every external one its
   version and its reader's rule.
6. Every decision record that the release touched is current, or superseded by a new one.
7. The architecture description's version and history record what the release changed, and no
   summary in it (a version, a range, a count) is older than the thing it summarizes.
8. The open issues of section 12 of the description were read again, and each is still open,
   closed by a change request or accepted with a reason.
