# Software architecture for a long-lived DAQ {#ch06}

::: box-why
You will lead the DAQ, so its structure is yours: which parts may depend on which, how an
operator controls it, what it records, and how it can change for ten years without becoming
untouchable. A PET scanner's acquisition software outlives several detector boards, operating
system versions and developers. Every one of those changes is cheap if hardware access,
processing and control are separated by stable interfaces, and expensive if they are not. In a
regulated product the structure is also a deliverable: the architecture must be described,
its interfaces identified and its decisions justified, and an auditor or a new colleague will
read that description before they read your code.
:::

**A day in the life.** It is a Thursday. The detector team asks whether a new firmware
version, with a different link protocol, can be tested on Monday. A clinical-site engineer
reports that a scan stopped when the operator's laptop went to sleep. And quality assurance
asks which configuration was used for last Thursday's phantom acquisition. In a DAQ where the
control client owns the acquisition, the receiver code is called directly by the sorter, and the
configuration lives in command-line flags, these are three investigations. In MiniDAQ after this
chapter they are three short answers. The new link is a new adapter behind `DetectorPort`,
tested with a simulator before the boards arrive. The scan cannot have stopped because of the
laptop: an acquisition belongs to the service, and a disconnect is only a line in the audit
trail. That same audit trail holds the complete effective configuration of every `configure`
command, with who sent it and when.

## Learning objectives {.unnumbered}

After this chapter you can:

1. Separate hardware access, processing and control into layers with rules a tool can check,
   and apply dependency inversion so that every hardware dependency can be simulated in a test.
2. Implement an acquisition state machine (idle, configured, running, stopping, fault) as one
   table, make illegal commands harmless, and keep it correct under concurrent events.
3. Design schema-validated, versioned configuration files whose errors tell the user exactly
   what is wrong and where.
4. Design a stable, versioned control API (configure, start, stop, status), compare gRPC,
   REST, ZeroMQ and a plain line protocol, and decide what happens when a client disconnects.
5. Add logging, telemetry and an audit trail that do not touch the hot path, record
   decisions as architecture decision records, and write an architecture description of the
   kind an IEC 62304 process asks for.

## Prerequisites and estimated time {.unnumbered}

Chapters 1 to 5, in particular the pipeline and its counters (Chapter 3) and the latency histograms
(Chapter 4). You need Graphviz (`dot`) for the diagrams and `nc` (netcat) to talk to the server by
hand. Reading: about 3 hours. Exercises: 9 to 12 hours. Milestone: 4 hours.

MiniDAQ grows a second library in this chapter. `minidaq_core` keeps the hot path: types,
formats, the pipeline, histograms, real-time settings and the simulator. The new
`minidaq_control` holds everything an operator touches: configuration, the state machine, the
acquisition service, the audit trail and the TCP control API. Two programs use it:
`minidaq_server` and the command-line client `minidaq_ctl`.

## Layers, ports and adapters

### The intuition

Architecture is the set of decisions that are expensive to change later. For a DAQ the most
expensive ones are about *dependencies*: which code knows about which. If the sorter calls the
network receiver directly, you cannot test the sorter without a network. If the acquisition
loop reads command-line flags, you cannot reconfigure it from a GUI. If the control server's
socket code is mixed with the start-up of the pipeline threads, a change in one breaks the
other.

The remedy is old and simple. Put code with the same reason to change together, give each
group a stable interface, and let dependencies point in one direction only: from the parts
that change often and depend on the outside world (devices, sockets, files, user interfaces)
towards the parts that hold the policy (what an acquisition is, which commands are allowed,
how faults end a run). Robert C. Martin calls this the dependency rule; Alistair Cockburn's
*ports and adapters* (also called hexagonal architecture) is the same idea drawn as a hexagon:
the application in the middle owns interfaces called *ports*, and *adapters* outside implement
them for a particular device, protocol or test.

### MiniDAQ's four layers

```{.dot include="book/src/diagrams/ch06-components.dot" caption="MiniDAQ's components after this chapter. An arrow means \"uses\". Every arrow points down or within a layer; the dashed arrow is a network connection, not a code dependency." width="100%"}
```

| Layer | What is in it | May use |
|---|---|---|
| core | types, packed format and decoder, pipeline and channels, histograms, real-time settings, simulator | core |
| application | acquisition service, state machine, configuration, ports | core, application |
| adapters | simulated detector, counting sink, audit file, control protocol, TCP server | core, application, adapters |
| apps | `minidaq_server`, `minidaq_ctl` and the Chapter 4 tools | everything |

The hot path stays in *core*, which knows nothing about JSON, sockets or operators. The
*application* layer is MiniDAQ's policy. *Adapters* are details that can be replaced: today the
detector is a simulator and the sink counts and discards; Chapter 9 adds a UDP receiver and
Chapter 12 a list-mode file writer, and neither change touches the application layer.
*Apps* wire everything together: they choose the adapters, parse command lines and handle
signals.

### Dependency inversion: ports owned by the application

The interesting arrows are the ones from adapters *up* to the application. The service needs
a detector, but it must not depend on a particular one. So the application layer defines what
it needs as an interface, and the adapters implement it:

```{.cpp include="minidaq/include/minidaq/control/ports.hpp" snippet="ports"}
```

This is the dependency inversion principle: high-level policy and low-level detail both depend
on an abstraction, and the abstraction belongs to the policy. The service creates its ports
through factories that someone else supplies, so the service's source code contains no
`#include` of any adapter. The application chooses the production adapters in one place:

```cpp
control::ServiceOptions opt = control::with_default_adapters();  // minidaq_server.cpp
```

and a test chooses its own. Three details of the port interface are deliberate. `read()` must
return immediately with 0 when nothing is available, because it runs on the source thread,
which also has to notice a stop request. `fault()` is polled from a monitor thread, never from
the hot path, so a device can report trouble without the pipeline knowing what a fault is. And
the factories run at every `start`, so each run gets a fresh detector whose clock and counters
start at zero.

Why virtual functions here, after Chapter 5 removed an indirect call from the sort? Because
the cost is paid once per *read* of up to a whole batch of words, not once per single. At the
boundary to hardware, the ability to swap implementations at run time is worth an indirect
branch per batch. Inside the per-event loops, concepts and templates remain the tool, as
Chapter 1 recommended.

### Worked example: testing the sorter without hardware

The question this chapter's check-yourself section asks first is: which component would you
simulate to test the sorter without hardware? The answer is the detector port, and nothing
else. The sorter, the pairing, the counters and the fault handling are all real; only the
words come from a test. Here is a detector, from MiniDAQ's own tests, that sends two full
batches with the second one *older* than the first:

```{.cpp include="minidaq/tests/unit/test_acquisition_service.cpp" from="class BackwardsDetector" to="};"}
```

The test configures the real service with it, starts a run, and expects the run to end in
the fault state with the message `sort: 512 singles arrived out of time order`. That one test
exercises the sort stage's late-single counter, the service's monitor, the state machine and
the status report, in 10 ms, on any laptop. Chapter 1 promised that out-of-order input would
raise a fault instead of silently producing coincidences; this test is where that promise
became checkable. Exercise 6.5 builds a general fault-injecting adapter on the same idea.

### Rules that a machine checks

A layer diagram in a document is a claim. Six months later someone adds one convenient
`#include` of an adapter into the service, the build passes, and the diagram is wrong. Two
mechanisms keep the claim true in MiniDAQ.

First, the libraries: `minidaq_core` does not link `nlohmann_json`, so a JSON include in core
code does not compile. Second, a small script, `tools/check_layers.py`, reads the layer
assignment from `docs/architecture/layers.json` and checks every `#include` in the library and
application sources. It runs as the unit test `architecture.layers`. Add an adapter include to
the service and a JSON include to a core header, and the test fails with:

```text
minidaq/include/minidaq/pipeline/backoff.hpp: core may not include <nlohmann/json.hpp>
minidaq/src/control/acquisition_service.cpp: application may not include adapters (minidaq/control/adapters.hpp)
check_layers: 51 files, 2 violation(s)
```

The first version of the service did contain that adapter include: it filled in the default
detector itself when none was given. Writing the layer rule down exposed it, and the fix,
`with_default_adapters()` in the adapter layer, made the service honest. Architecture rules
that nobody checks are usually already broken.

::: box-mistakes
- **Layers by technical type instead of by reason to change.** A "utils" layer, a "models"
  layer and a "managers" layer say nothing about what may change independently.
- **Interfaces with one implementation and no test double.** An interface pays for itself
  when a second implementation exists, and in a DAQ the test double is that second
  implementation. If nobody writes one, the interface is ceremony.
- **Leaking the adapter through the port.** A `DetectorPort` with a `socket_fd()` method, or
  a configuration struct with a `udp_port` field that the application reads, ties the policy to
  one transport. Keep transport details inside the adapter and its own configuration.
- **Virtual calls inside per-event loops.** Ports are for boundaries crossed once per batch.
- **Drawing the diagram and never checking it.** Put the rule in a file and fail the build.
:::

## The acquisition state machine

### The intuition

An acquisition is in one of a few states, and most dangerous bugs in instrument control
software are commands accepted in the wrong one: a reconfiguration while data is flowing,
a second start that leaks the first run's threads, a reset that hides a fault before anyone
has looked at it. Booleans such as `running_` and `configured_` invite those bugs, because
they allow combinations that make no sense ("running but not configured") and because the
rules end up spread over every command handler. An explicit state machine puts all the rules
in one place, where a reviewer, a tester and a risk analyst can read them.

### Five states, six events, one table

```{.dot include="docs/architecture/states.dot" caption="The acquisition state machine. Operators send configure, start, stop and reset; the system sends drained (all stages finished) and error (a device or the pipeline reported a fault)." width="100%"}
```

```{.cpp include="minidaq/include/minidaq/control/acquisition_state.hpp" snippet="table"}
```

The table is the single source of truth. `next_state(state, event)` searches it; a pair that
is not in it is an illegal transition, which changes nothing and produces the message
"cannot start in state idle". Two rows are design decisions worth stating aloud. There is no
`reset` from running: to abandon a run you stop it, the stages drain, and every single in
flight is counted before the state changes. And the only way out of fault is `reset`: a fault
stays visible in `status` until someone acknowledges it, so it cannot be overwritten by the
next `start` from a script that did not check.

Events have two origins. *Operator* events (configure, start, stop, reset) arrive from the
control API. *System* events arrive from inside: `drained` when every pipeline stage has
finished (a finite run that reached its `stop_after_s`, or a stopped run that has emptied its
channels), and `error` when a port reports a fault or the sort stage has seen out-of-order
singles. Modeling both kinds as events of the same machine is what makes "a fault during
stopping" or "the run ended while the operator was pressing stop" well-defined instead of a
race.

A machine-readable copy of the table, `docs/architecture/acquisition-states.json`, feeds the
diagram above and the documentation. A unit test fails if it differs from the code, and
Exercise 6.1's test fails if the drawing differs from the JSON. Three artifacts, one truth.

### Thread safety, and a deadlock ThreadSanitizer found

Commands arrive on the control server's thread and system events on the monitor thread, so the
machine must be thread-safe. The obvious implementation holds a mutex in `apply()`, changes the
state, and calls a listener (which writes the transition to the audit trail) before releasing
the mutex, so listener calls arrive in transition order.

The first version of MiniDAQ's machine did something close to that: it held the state mutex
while it took a second mutex that serialized listener calls. The listener, which belongs to the
service, read the state to publish it to waiting threads. Under the `tsan` preset the unit tests
did not hang, but ThreadSanitizer reported a *lock-order inversion* and failed the run: one path took the state
mutex and then the notification mutex, the listener path took them in the opposite order.
Nothing had hung, but two threads taking the two mutexes in opposite orders at the wrong moment
would have deadlocked the control plane. The fix keeps the order without ever
holding both locks:

```{.cpp include="minidaq/src/control/acquisition_state.cpp" snippet="apply"}
```

Each transition takes a ticket (a sequence number) while it holds the state lock, releases
the lock, and then waits on the notification mutex until all earlier tickets have been
served. Listener calls are therefore serialized and in order, the state lock is never held
during a listener call, and the two mutexes are never held in the state-then-notification
order. A listener may call `state()`, and a slow listener delays other listeners but never a
`status` request. The test suite for the machine runs 4 threads applying random events while
the listener reads the state, and checks that the recorded history is one consistent chain of
legal transitions. It runs under `tsan` in CI.

### The service around the machine

`AcquisitionService` owns the machine, the current configuration, the ports and the pipeline
of the current run. Its public face is four commands and a snapshot:

```{.cpp include="minidaq/include/minidaq/control/acquisition_service.hpp" snippet="commands"}
```

Each command takes the service mutex, checks the state, does its work, and only then applies
the event. `configure` validates everything, including reading the real-time profile file,
before the state changes, so an invalid configuration leaves the previous one in force:

```{.cpp include="minidaq/src/control/acquisition_service.cpp" snippet="configure"}
```

`start` creates fresh ports, builds the pipeline and starts it; a factory failure returns
`device_error` and stays in configured. `stop` only *requests* a stop and moves to stopping,
because draining takes time and a command must not block the control thread. The transition
back to configured comes later, from the monitor.

::: box-mistakes
- **State as booleans.** Two booleans have four combinations; the acquisition has five states
  and only twelve legal transitions. Make the impossible states unrepresentable.
- **Calling listeners or callbacks under the state lock.** Sooner or later a callback calls
  back in. Run callbacks after unlocking, and keep them ordered with a ticket or a queue.
- **Letting `start` from fault mean "reset and start".** Convenience for scripts, and a way to
  lose the evidence of every fault. Require an explicit reset.
- **Blocking commands.** A `stop` that waits for the drain blocks every other client. Make the
  command change the state and let the system event finish the job.
- **A diagram that is not generated from, or checked against, the table.**
:::

## Configuration you can trust

### The intuition

A configuration file is an interface with the most careless client there is: a person with a
text editor at the end of a long day. Every way it can be wrong will happen. A misspelled key
(`pair_fracton`) that is silently ignored means the default is used and nobody notices until
the data looks odd. A rate of `2e9` that is accepted means a stage that cannot keep up. A file
written for a newer version, read by an older program, means half the settings are
understood. The rule for a long-lived instrument is: *reject anything you do not fully
understand, explain exactly why, and record what you accepted.*

### Validation that reports everything

MiniDAQ's configuration is JSON with comments allowed (`parse_config` passes
`ignore_comments = true` to the parser, because operators annotate files). The reader walks the
document with a small helper that checks presence, type and range of each value and records an
error, with the value's location as a JSON Pointer (RFC 6901), instead of stopping at the first
problem. This is the part of the helper that reads a number:

```{.cpp include="minidaq/src/config/acquisition_config.cpp" snippet="reader_number"}
```

The helper also remembers every key it was asked for, so `finish()` can report each key nobody
asked for as unknown, with a suggestion when an expected key is within an edit distance of 2.
Here is what a server says to a file with five mistakes, captured from `minidaq_ctl configure
bad.json`:

```text
/schema_version: written for a newer MiniDAQ (1.1 > 1.0)
/source/rate_hz: must be between 1.0 and 1000000000.0
/source/pair_fracton: unknown key (did you mean "pair_fraction"?)
/pipeline/batch_size: must be between 1 and 1048576
/pipeline/overflow: must be one of "block", "drop"
```

All five at once, each with its path, so the operator fixes the file in one pass. The same
errors come back over the control API as a `details` array of `{path, message}` objects, so a
GUI can highlight the fields.

### Versioning the format

Every file states the version of the format it was written for, as `MAJOR.MINOR`:

```{.cpp include="minidaq/src/config/acquisition_config.cpp" snippet="version"}
```

The rules follow from what each kind of change means for an old reader. Adding an optional key
with a default is a *minor* change: a file without the key means what it always meant. A
program that reads 1.0 must refuse a 1.1 file, though, because the file may rely on the new
key, and ignoring it would silently change the acquisition. Renaming or removing a key, or
changing a unit, is a *major* change: the program refuses other major versions outright, and a
conversion tool or a documented manual migration moves old files forward. Because unknown keys
are errors, a minor-version mismatch cannot slip through as "an unknown key nobody noticed".

### The schema document, and keeping it honest

People and other tools (an editor, a GUI, a Python script that generates configurations) need
the format as a document. `docs/architecture/acquisition-config.schema.json` is a JSON Schema
(draft 2020-12) of version 1.0. Two descriptions of the same format will drift apart unless
something compares them, so the unit test `Config.SchemaDocumentAgreesWithTheReader` reads the
schema and, for every property, checks that the reader knows the key, accepts every enum
value and rejects others, and accepts the minimum and maximum and rejects values just outside
them. The C++ reader stays the authority; the test makes the document trustworthy.

Finally, `status` reports the *effective* configuration, every default filled in, and the audit
trail stores it at every `configure`. That answers the quality-assurance question from the start
of the chapter without anyone having kept a copy of the file.

::: box-mistakes
- **Ignoring unknown keys "for forward compatibility".** In a control file that is how typos
  become defaults. Forward compatibility comes from version numbers, not from silence.
- **Stopping at the first error.** The user fixes one, runs again, finds the next. Report all.
- **Errors without a location.** "invalid value" in a 200-line file is a puzzle.
- **Validating in the middle of applying.** Validate everything first, then apply, so a bad
  file never leaves the system half-configured.
- **A schema document that no test reads.** It will describe a format that no longer exists.
:::

## A control API that lasts

### The intuition

The control API is the contract between MiniDAQ and everything that drives it: the operator
console, scripts, the test harness, and later systems you have not met yet. It changes more
slowly than any code behind it, so its design is mostly about *change*: how a new command is
added without breaking old clients, how an old server answers a new client, and what neither
side may ever assume.

### Choosing a transport

| | gRPC | REST/JSON over HTTP | ZeroMQ | Newline-delimited JSON over TCP |
|---|---|---|---|---|
| Interface definition | Protocol Buffers, generated code | OpenAPI (optional) | none (you define messages) | none (you define messages) |
| Streaming telemetry | built in | needs SSE or WebSocket | PUB/SUB sockets | poll `status` |
| Dependencies to qualify | gRPC, protobuf, abseil and their build | an HTTP server library | libzmq | none beyond the JSON library |
| Debug by hand | `grpcurl` | `curl` | small script | `nc` |
| Security (TLS, auth) | built in | built in with HTTPS | CURVE mechanism | build or tunnel it yourself |

There is no universally right answer. For a single acquisition PC whose clients run on the
same machine, MiniDAQ chose the last column (ADR 0003, `docs/adr/0003-control-protocol.md`): one request per line, one response per line, no new dependency, readable in
logs and testable with `nc`. The message handling is independent of the transport, so moving
to gRPC or HTTP later replaces the server, not the service or its tests. If the scanner's
architecture puts the operator console on another computer, the security requirements of
Chapter 17 (authentication, encryption) weigh heavily towards a transport that has them built
in.

### The protocol

A session, recorded against `minidaq_server` (responses shortened only where marked):

```text
-> {"api": "1.0", "id": 1, "cmd": "hello"}
<- {"api":"1.0","commands":["hello","configure","start","stop","reset","status"],
    "id":1,"ok":true,"server":"minidaq 0.1.0-dev"}    (line break added)
-> {"api": "1.0", "id": 2, "cmd": "start"}
<- {"api":"1.0","error":{"code":"illegal_transition","message":"cannot start in state idle"},"id":2,"ok":false,"state":"idle"}
-> {"api": "1.0", "id": 3, "cmd": "configure", "config": {"schema_version": "1.0", "source": {"rate_hz": 1e6}}}
<- {"api":"1.0","id":3,"ok":true,"state":"configured"}
-> {"api": "1.0", "id": 4, "cmd": "start"}
<- {"api":"1.0","id":4,"ok":true,"state":"running"}
-> {"api": "2.0", "id": 5, "cmd": "status"}
<- {"api":"1.0","error":{"code":"unsupported_api","message":"this server speaks API 1.0"},"id":5,"ok":false,"state":"running"}
```

This session was recorded with API 1.0. Since Chapter 17 the server speaks API 2.0, in which a
client authenticates with an `auth` command before anything but `hello`; `minidaq_ctl` does
that for you, so the commands of this chapter work unchanged.

The compatibility rules are few and strict. Every response carries the server's `api`
version. A request whose major version differs is refused. Unknown fields in a request are
ignored, so a newer client may send fields an older server does not know, and new response
fields and new commands appear only in minor versions, so an older client never meets a
response it cannot parse. The request's `id` is echoed unchanged. Every response says `ok`;
responses to commands and errors also carry the state after the command; and every error has
a fixed, documented `code` that programs branch on and a `message` that people read. Codes are part of the contract; messages are not.

Note the asymmetry with the configuration file, where unknown keys are errors. A request is a
message between programs, written by code that is versioned and tested, and tolerance there
lets clients and servers be upgraded independently. A configuration is written by a person,
and tolerance there hides mistakes.

### Framing and the server

TCP delivers bytes, not messages: one `recv()` can hold half a request or three of them. The
`LineFramer` turns a byte stream into lines and refuses lines longer than 64 KiB, after which
the connection is closed, since there is no safe way to find the start of the next request:

```{.cpp include="minidaq/include/minidaq/control/control_protocol.hpp" snippet="framer"}
```

`handle_request` turns one line into one response and never throws: a malformed request gets a
`bad_request` response. The server is one thread with `poll()` over the listening socket, up to
8 clients and an `eventfd` that wakes it for shutdown. It binds to 127.0.0.1 unless told
otherwise, because the protocol has no authentication yet. The control plane is a few requests
per second; a thread per client, or an asynchronous framework, would add complexity and no
benefit.

### What happens when the client disconnects

This is the second check-yourself question of this chapter, and the answer is a design decision,
not an accident of the code. In MiniDAQ, **nothing happens to the acquisition**. The run
belongs to the service, not to the connection that started it. The server records the
disconnect in the audit trail and closes the socket; the pipeline keeps running, and any other
client, or the same operator reconnecting, sees it in `status` and can stop it. Continuing the
session above with a second client after the first one disconnected:

```text
-> {"api": "1.0", "id": 1, "cmd": "status"}
<- {"api":"1.0","id":1,"ok":true,"status":{...,"state":"running",...}}    (shortened)
-> {"api": "1.0", "id": 2, "cmd": "stop"}
<- {"api":"1.0","id":2,"ok":true,"state":"stopping"}
```

The alternative, stopping on disconnect, is sometimes right: a motion controller that keeps
moving when its operator vanishes is dangerous. If a risk analysis concludes that an
unattended acquisition is a hazard, the right design is still not "stop when the TCP
connection drops", because connections drop for harmless reasons. It is an explicit *lease*: a
client holds the run by sending a heartbeat, and the service stops when the lease expires,
which is visible, configurable and testable.

::: box-mistakes
- **Tying the run to the session.** A sleeping laptop stops a patient scan.
- **No version in the messages.** The first incompatible change then needs a flag day.
- **Rejecting unknown request fields.** Old servers then refuse every new client.
- **Error strings as the contract.** Clients that parse messages break when someone fixes a
  typo. Give every error a code.
- **One read, one message.** Works on a quiet localhost and fails under load or over a WAN.
  Frame the stream, and fuzz the framer (Chapter 7).
- **Listening on all interfaces by default** with no authentication.
:::

## Logging, telemetry and audit without touching the hot path

### The intuition

A DAQ needs three kinds of output that are often confused. *Telemetry* answers "how is it
doing right now?": rates, drops, queue depths, latencies, for dashboards and alarms.
*Diagnostic logs* answer "what happened before it broke?", for developers. An *audit trail*
answers "who did what, when, and with what result?", for operators, quality assurance and
investigations. They have different readers, retention and integrity requirements, and none of
them may slow down the stages that process 10 million singles a second.

### What MiniDAQ records, and where

| Output | Written by | How | Read through |
|---|---|---|---|
| Stage counters (in, out, dropped, filtered, batches, stalls) | each stage, its own counters | relaxed atomic increments (Chapter 3) | `status` |
| Latency histograms, cumulative | each stage, its own histogram | single-writer `record()` (Chapter 4) | `status` `latency_ns` |
| Latency over the last interval | monitor thread | snapshot of bucket counts once per second | `status` `recent_latency_ns` |
| Late singles | sort stage | one relaxed counter | `status`, and a fault |
| Commands, transitions, faults, connections | control threads and monitor | audit records, appended and flushed | the audit file |

The stages never format text, take a lock or make a system call to report anything. They
increment counters and record into histograms, which other threads read. The *monitor thread* of
the service, which wakes every 20 ms, turns those numbers into events: a port fault or a late
single becomes an `error` event and an audit record, a finished pipeline becomes `drained`,
and once per second it copies the histogram buckets so that `status` can report the last
interval.

```{.cpp include="minidaq/src/control/acquisition_service.cpp" snippet="monitor"}
```

The interval percentiles are what Exercise 4.3 built, now part of the library: two snapshots
of the bucket counts, subtracted. The cumulative histogram is never reset, because a reset would
race with its single writer.

```{.cpp include="minidaq/include/minidaq/metrics/histogram_interval.hpp" snippet="interval"}
```

### The audit trail

Each record is one JSON object per line (the JSON Lines convention): time in UTC with
milliseconds, who (a TCP peer, `service`, `signal`), action, detail and whether it succeeded.
The session above produced this trail (`configure` detail shortened):

```text
{"action":"listen","detail":"127.0.0.1:7712","ok":true,"time":"2026-10-24T14:55:08.084Z","who":"server"}
{"action":"connect","detail":"","ok":true,"time":"2026-10-24T14:55:08.609Z","who":"tcp:127.0.0.1:60772"}
{"action":"start","detail":"rejected: cannot start in state idle","ok":false,"time":"2026-10-24T14:55:08.610Z","who":"tcp:127.0.0.1:60772"}
{"action":"configure","detail":"{...}","ok":true,"time":"2026-10-24T14:55:08.610Z","who":"tcp:127.0.0.1:60772"}
{"action":"transition","detail":"idle -> configured (configure)","ok":true,"time":"2026-10-24T14:55:08.610Z","who":"service"}
{"action":"start","detail":"run 1, simulated detector, 1e+06 singles/s, seed 1","ok":true,"time":"2026-10-24T14:55:08.627Z","who":"tcp:127.0.0.1:60772"}
{"action":"transition","detail":"configured -> running (start)","ok":true,"time":"2026-10-24T14:55:08.627Z","who":"service"}
{"action":"disconnect","detail":"","ok":true,"time":"2026-10-24T14:55:08.627Z","who":"tcp:127.0.0.1:60772"}
{"action":"connect","detail":"","ok":true,"time":"2026-10-24T14:55:09.127Z","who":"tcp:127.0.0.1:60776"}
{"action":"stop","detail":"run 1","ok":true,"time":"2026-10-24T14:55:09.128Z","who":"tcp:127.0.0.1:60776"}
{"action":"transition","detail":"running -> stopping (stop)","ok":true,"time":"2026-10-24T14:55:09.128Z","who":"service"}
{"action":"run_ended","detail":"run 1","ok":true,"time":"2026-10-24T14:55:09.131Z","who":"service"}
{"action":"transition","detail":"stopping -> configured (drained)","ok":true,"time":"2026-10-24T14:55:09.131Z","who":"service"}
```

Rejected commands are recorded too: "someone tried to start while idle" is useful when you
reconstruct an incident. Each record is flushed as it is written, so a crash loses at most the
line being written; with the `sync` option each record is also passed to `fsync`, which is
slower and makes the record survive a power failure. "Who" is only a TCP address today. A real
audit trail needs an authenticated user, a protected file and a retention rule, which come
with the cybersecurity and QMS chapters (17 and 16).

::: box-mistakes
- **`printf` or a logger call in a stage loop.** Formatting, locks and `write()` turn into
  latency spikes at the worst moment. Count in the stage; report from another thread.
- **Resetting a histogram that a stage writes.** Subtract snapshots instead.
- **Telemetry only as text logs.** Numbers that a program must parse back out of prose are
  telemetry done wrong. Expose them as data.
- **An audit trail that only records successes.** Rejections and faults are the interesting
  part.
- **Local time without a zone in records.** Use UTC with an explicit `Z`.
:::

## Decisions and the architecture description

### Architecture decision records

Code shows what the system does; it rarely shows why it does not do something else. An
*architecture decision record* (ADR), as proposed by Michael Nygard in 2011, is a short file per
decision with the context, the options, the decision and its consequences, numbered and never
rewritten: a changed decision gets a new record that supersedes the old one. MiniDAQ keeps them
in `docs/adr/`, and this chapter wrote the first seven:

| Number | Decision | Status |
|---|---|---|
| 0001 | Record architecture decisions, and the format | Accepted |
| 0002 | Batched SPSC channels between stages (with Chapter 3's measurements) | Accepted |
| 0003 | Control protocol: NDJSON over TCP; the service owns the run | Accepted |
| 0004 | nlohmann/json, in the control plane only | Accepted |
| 0005 | A table-driven acquisition state machine | Accepted |
| 0006 | C++20 with a `std::expected` shim (Chapter 1) | Accepted |
| 0007 | List-mode file format | Proposed |

The most valuable section is *Options*. A record with one option is a description, not a
decision; listing the alternatives you rejected, and why, is what stops the next team from
re-running the same discussion, or lets them see that the context has changed and the decision
should too. The *Negative consequences* section is a close second: a decision without a cost
was not a decision. ADR 0006 is an example of a consequence turned into a check: because two
implementations of `Expected` sit behind one name, a new CI preset, `gcc-cxx23`, builds and
tests everything in C++23 with `std::expected`, beside the C++20 presets that use the shim.

Exercise 6.3 writes a linter for the format; MiniDAQ's own records pass it in every CI run.
Record 0007 is *Proposed* on purpose: writing down an undecided question with its options is
how you keep it from being decided by whoever writes the first line of a file writer.

### The architecture description

`docs/architecture/architecture.md` is version 1 of MiniDAQ's architecture description. Its
structure follows what an IEC 62304 software development process asks of an architecture
(software items, their interfaces, SOUP, segregation, verification), without reproducing the
standard, which you should read in your organization's licensed copy:

1. purpose and scope, and what is not yet covered;
2. context: every external interface (detector, data consumer, control clients, configuration
   files, audit trail, operating system);
3. the requirements that shape the architecture, and where each is met;
4. software items and layers, with the component diagram and the layer rule;
5. interfaces between items, with their contracts (threads, blocking, errors);
6. dynamic behavior: threads, the state machine, the life of a run, fault handling;
7. configuration;
8. observability;
9. SOUP, with what is required of each item;
10. segregation, and what is *not* claimed;
11. how the architecture is verified;
12. decisions and open issues.

Section 10 deserves a second look. In a regulated product, separating software items so that a
failure in one cannot affect another can be part of a risk control, and then the separation
must be real and justified. MiniDAQ's layers are separated at build time (libraries and the
include check) and its clients by process boundaries, but the control plane and the pipeline
share one address space. The document says so plainly instead of implying a segregation that
does not exist. Section 11 lists, for each architectural claim, the test that verifies it.
Both habits will matter when Chapter 14 builds the full IEC 62304 file.

::: box-mistakes
- **ADRs written after the fact, to justify a decision already in the code.** Write them in
  the same change, so review can still change the decision.
- **Editing an accepted ADR.** Supersede it; history is the point.
- **An architecture document that describes the intended system.** Describe the one in the
  repository, and list the gaps as open issues.
- **Claiming segregation you cannot justify.**
:::

::: box-regulated
Architecture is where software design meets the regulatory file, and auditors read it closely.

- **The architecture is a design output.** An IEC 62304 process expects the architecture to be
  documented, its software items and interfaces (including to SOUP) identified, and the
  documentation verified against the requirements. Review records of this document and of the
  ADRs are part of the evidence; review them like code, in the same change.
- **SOUP needs requirements.** For each third-party item, state what you require of it
  (function and performance) and what it requires (platform, other items), and keep its exact
  version and anomaly list under configuration management (Chapters 7 and 14).
- **Segregation is a claim to justify.** If the risk analysis relies on one item being unable
  to affect another, the architecture must show how, and verification must test it (Chapter 15).
- **The control API is an interface with requirements.** Its commands, states, errors and
  compatibility rules are specified, versioned and verified like any other requirement, and a
  breaking change is a change request with impact analysis.
- **Audit trails may become records.** If the product's quality system or a customer treats
  acquisition logs as records, retention, integrity and access control follow (Chapter 16), and
  so do electronic-record rules in some markets (verify: which apply to your company's
  products and markets).
:::

::: box-askteam
1. Is there an architecture description of the current DAQ software, which version is current,
   and who reviews changes to it? Are decisions recorded anywhere (ADRs, design reviews, wiki)?
2. How is the acquisition controlled today (GUI, script, protocol)? Which transport and message
   format, is the API versioned, and which clients depend on it?
3. What happens to a running acquisition when the operator console crashes or loses its
   network connection? Is that behavior specified, and was it ever tested?
4. Which acquisition states exist, and are fault states acknowledged explicitly? Where are the
   allowed transitions written down?
5. How are acquisition configurations validated, versioned and stored with the data, and can
   QA reconstruct the exact settings of any past acquisition?
:::

## Exercises {.unnumbered}

**Exercise 6.1 (E): Draw the MiniDAQ component diagram and its acquisition state machine.**
*Goal:* the two diagrams a newcomer needs, as Graphviz files that a test compares with the
code. *Starter:* `exercises/ch06/e1_diagrams/` (two incomplete `.dot` files). *Acceptance:*
`tests/test_diagrams.py` passes: the state edges equal `docs/architecture/acquisition-states.json`;
at least 12 components, each with a layer class, every layer present, the important components
named; every edge goes to a layer its source may use (the rule in `layers.json`); no isolated
component; both files render with `dot`. *Time:* 90 minutes.

**Exercise 6.2 (M): Implement the state machine with illegal-transition tests.** *Goal:* a
state machine built from a written specification that adds a calibrating state to MiniDAQ's,
correct for all 42 state/event pairs and under concurrent events. *Starter:*
`exercises/ch06/e2_state_machine/`. *Acceptance:* `tests/test_state_machine.cpp` passes: every
pair against an independent copy of the specification; illegal events change nothing and give
the exact message; listener calls once per transition, in order; a listener that reads the
state does not deadlock (watchdog); 4 threads sending 80,000 random events leave one consistent
history. Run it under `tsan` too. *Time:* 2 hours.

**Exercise 6.3 (M): Write three ADRs: queue choice, file format, control protocol.** *Goal:*
three decision records in the format of ADR 0001, and a linter that keeps every future record in
that format. *Starter:* `exercises/ch06/e3_adrs/` (Python, with 0001 in `starter/adr/`).
*Acceptance:* `tests/test_adr_lint.py` passes: the linter accepts a good record and reports each
kind of defect (file name, title and number, date, status, missing, empty or misordered
sections, fewer than two options, missing consequences, numbering gaps and duplicates,
"Superseded by" a missing record); your three records pass the linter and their titles cover the
three topics. *Time:* 3 hours.

**Exercise 6.4 (M, extra): Framing a binary protocol.** *Goal:* a reader for length-prefixed
frames that survives every chunking of the stream, refuses hostile lengths from the header
alone, and costs time linear in the bytes received. *Starter:*
`exercises/ch06/e4_frame_reader/`. *Acceptance:* `tests/test_frame_reader.cpp` passes:
big-endian encoding, one byte at a time, many and empty frames per read, 2,000 random frames
through random chunk sizes, too-large lengths including 0xFFFFFFFF, and 1,000,000 frames in
one read taking less than 8 times as long as 250,000. *Time:* 2 hours.

**Exercise 6.5 (H, extra): Inject faults through the detector port.** *Goal:* an adapter that
wraps any `DetectorPort` and makes it fail like real readout (link down, corrupted words, a
stall, out-of-order data), and end-to-end tests of MiniDAQ's reaction with the real service.
*Starter:* `exercises/ch06/e5_fault_injection/`. *Acceptance:*
`tests/test_fault_injection.cpp` passes: a clean run completes; link down faults the run with
your message and needs a reset; exactly the corrupted words are filtered by decode; a 60 ms
stall loses nothing and shows as at least 50 ms of end-to-end latency; reordered data faults the
run as out of time order. *Time:* 3 hours.

## MiniDAQ milestone: control API, state machine and architecture document v1 {.unnumbered}

::: box-milestone
**Goal.** MiniDAQ is controlled through a versioned API by a service that owns the acquisition,
follows an explicit state machine, validates its configuration, records an audit trail and
reports counters and latencies while it runs. Its architecture is described, its decisions are
recorded, and its layering is checked by a test. **Start:** tag `ch05`. **End:** tag `ch06`.
:::

1. Add `minidaq/include/minidaq/config/acquisition_config.hpp` and its source: the configuration
   model, `parse_config` with all errors and JSON Pointer paths, schema versions, `to_json` and
   `to_pipeline_config`. Add nlohmann/json 3.11.3 to `cmake/Dependencies.cmake`, pinned by hash.
2. Add `minidaq/include/minidaq/control/`: `acquisition_state.hpp` (table and thread-safe
   machine), `ports.hpp`, `audit.hpp`, `acquisition_service.hpp`, and the adapters
   (`adapters.hpp`, `audit_log.hpp`, `control_protocol.hpp`, `control_server.hpp`), built as
   the `minidaq_control` library. `minidaq_core` must not link the JSON library.
3. Add `minidaq/include/minidaq/metrics/histogram_interval.hpp`, and in the service, fault the
   run on late singles and report `recent_latency_ns`.
4. Add the applications `minidaq_server` and `minidaq_ctl`, and `minidaq/configs/default.json`
   and `short-run.json`.
5. Add four unit test files (for the state machine, the configuration, the service, and the
   protocol and server: `test_acquisition_state.cpp`, `test_config.cpp`,
   `test_acquisition_service.cpp`, `test_control_protocol.cpp`) and the interval test in
   `test_latency_histogram.cpp`.
6. Add `docs/architecture/` (`architecture.md`, `components.dot`, `states.dot`,
   `acquisition-states.json`, `acquisition-config.schema.json`, `layers.json`), `docs/adr/`
   (0001 to 0007 and an index), and `tools/check_layers.py` as the test `architecture.layers`.
7. Add the `gcc-cxx23` preset to `CMakePresets.json`, `ci/run_all.sh` and the CI matrix.

**Definition of done.** `ci/run_all.sh` is green on all five presets (debug, clang-release,
gcc-cxx23, asan-ubsan, tsan), and the control tests pass ten times in a row under `tsan`
(`ctest --preset tsan -R "AcquisitionState|AcquisitionService|ControlServer" --repeat
until-fail:10`). By hand: start `minidaq_server --audit audit.jsonl`, run `minidaq_ctl
configure minidaq/configs/short-run.json`, `minidaq_ctl start` and `minidaq_ctl wait configured
5`; the audit trail shows the configuration, both transitions and the end of the run. A
configuration with a misspelled key is rejected with a suggestion. Every ADR passes the Exercise
6.3 linter. Tag `ch06`.

## Check yourself {.unnumbered}

1. Which component would you simulate to test the sorter without hardware? What exactly would
   the simulation have to provide, and what would you assert?
2. What happens to an acquisition if the control client disconnects? Why is that a design
   decision, and how would you implement the opposite behavior safely if a risk analysis
   required it?
3. State the dependency rule. Which arrow in MiniDAQ's component diagram does dependency
   inversion turn around, and what does that buy in testing?
4. Why does the acquisition state machine have no `reset` from running and no way out of fault
   except `reset`? What would go wrong with each of those transitions?
5. A listener called under the state machine's lock reads the state. Describe the deadlock, and
   explain how the ticket scheme avoids it while keeping listener calls in order.
6. Why are unknown keys errors in a configuration file but ignored in a control request? Give
   the failure each rule prevents.
7. A program that reads configuration schema 1.0 receives a 1.1 file. What does it do, and why
   not "ignore what you do not understand"? What kind of change requires 2.0?
8. Why is the cumulative latency histogram never reset, and how does `status` still report the
   last second?
9. Name three things that make the audit trail useful in an investigation, and two things it
   still lacks before it could serve as a regulated record.
10. What are the sections of an ADR, and which two carry the most value? Why is ADR 0007
    "Proposed"?
11. What does MiniDAQ's architecture description claim about segregation, and what does it
    explicitly not claim? Why does that distinction matter in a regulated product?
12. Compare gRPC and newline-delimited JSON over TCP for a control API on one PC and for an
    operator console on another computer.

## Summary {.unnumbered}

- Architecture is about dependencies. MiniDAQ has four layers (core, application, adapters,
  apps); dependencies point inwards, and `tools/check_layers.py` fails the tests when an
  include breaks the rule.
- The application owns its ports (`DetectorPort`, `CoincidenceSinkPort`, `AuditSink`), and
  adapters implement them. Every hardware dependency can therefore be simulated: one scripted
  detector tests the sorter's fault handling in 10 ms.
- Acquisition control is one table of 12 transitions over 5 states and 6 events. Illegal
  commands change nothing; faults need an explicit reset; a run is stopped and drained, never
  reset away.
- Listener calls stay ordered without holding the state lock (tickets); ThreadSanitizer found
  the lock-order inversion of the first version.
- Configurations are validated completely before use, report every error with its JSON Pointer,
  reject unknown keys with suggestions, carry a `MAJOR.MINOR` version, and are recorded in
  effective form. A test keeps the JSON Schema document in agreement with the reader.
- The control API is versioned NDJSON over TCP with strict compatibility rules and error codes.
  The service, not the client session, owns the acquisition: a disconnect changes nothing.
- The hot path only counts and records; a monitor thread turns counters into faults, state
  changes, interval latencies and audit records.
- ADRs record each decision with its options and costs; the architecture description states
  items, interfaces, SOUP, segregation and verification, including what it does not claim.

## Further reading {.unnumbered}

- Robert C. Martin, *Clean Architecture: A Craftsman's Guide to Software Structure and Design*,
  Prentice Hall, 2017. The dependency rule, component principles and boundaries.
- John Ousterhout, *A Philosophy of Software Design*, second edition, Yaknyam Press, 2021. Deep
  modules, information hiding, and defining errors out of existence.
- Alistair Cockburn, "Hexagonal Architecture" (ports and adapters), 2005,
  <https://alistair.cockburn.us/hexagonal-architecture/>.
- Michael Nygard, "Documenting Architecture Decisions", 2011,
  <https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions>, and the
  community collection at <https://adr.github.io/>.
- Martin Kleppmann, *Designing Data-Intensive Applications*, O'Reilly, 2017, chapter 4
  ("Encoding and Evolution"): forward and backward compatibility of data formats and APIs.
- JSON Schema, draft 2020-12, <https://json-schema.org/specification>; RFC 6901, JSON
  Pointer; JSON Lines, <https://jsonlines.org/>.
- gRPC documentation, <https://grpc.io/docs/>; Pieter Hintjens, *ZeroMQ: Messaging for Many
  Applications*, O'Reilly, 2013, and the guide at <https://zguide.zeromq.org/>.
- Erich Gamma, Richard Helm, Ralph Johnson and John Vlissides, *Design Patterns*,
  Addison-Wesley, 1994: the State and Decorator patterns (Exercise 6.5's adapter is a decorator).
