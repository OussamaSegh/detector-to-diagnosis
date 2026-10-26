# The embedded Linux platform: services, watchdogs and updates {#ch25}

::: box-why
A scanner's acquisition PC is not a developer's workstation. It boots unattended in a hospital, runs
for months without anyone logging in, loses power when someone trips over a cable, and is updated by
a service engineer with a laptop and half an hour between two patients. Everything below MiniDAQ
(the kernel, the C library, OpenSSL, the service manager) is software of unknown provenance that
your device file must identify, and everything around it (how it starts, what restarts it, what it
may touch, how a new version gets there) is design that nobody has written down until someone does.
This chapter writes it down. You will define the platform with exact versions and check an installed
system against it, run MiniDAQ as a systemd service that tells the service manager when it is ready
and keeps a watchdog fed only while its loops are really alive, take away every privilege the server
does not need, and build an updater that installs only signed versions, into a second slot, as a
trial that is rolled back if it does not start, and that leaves a working system after a power cut
at any step.
:::

**A day in the life.** On Monday morning a site reports that the scanner "lost" a patient's
acquisition on Friday evening. The run record says the run started and then nothing: no end, no
fault. The server's process was still alive on Monday, its port open, and every command timed out.
The crash-report file was empty, because nothing had crashed. A thread dump shows the slow-control
thread blocked in a register read that never returned, holding the lock that every status command
waits for. Over the weekend you also learn how the site was updated a month ago: a service engineer
copied the new programs over the old ones from a USB stick, and the copy was interrupted once by a
power cut, after which "it worked again" when the engineer copied it a second time. By the end of
the week the platform under MiniDAQ has a definition with exact package versions and a check that
runs at installation, the server tells systemd when it is ready and stops feeding its watchdog when
a loop stops beating, and new versions arrive as signed bundles that install into a slot that is not
running and roll back by themselves when they fail to start.

## Learning objectives {.unnumbered}

After this chapter you can:

1. Explain what a controlled platform is, how a general-purpose distribution with pinned versions
   and a built image (Yocto, Buildroot) each get one, and define and check a platform with exact
   versions and its own SBOM.
2. Run a server as a systemd service with readiness notification, restarts and start limits, and
   implement the notification protocol without a library.
3. Design a watchdog that detects a hung loop, not only a dead process, choose its limits, and
   connect it to a crash report and a restart.
4. Reduce a service's privileges to what it needs, check the result with `systemd-analyze security`,
   and verify a system-call filter against the calls the program makes.
5. Design an update mechanism with signed bundles, A/B slots, a trial that is confirmed or rolled
   back, and a repair after a power cut at any step, and test it by cutting power after every write.
6. Place updates and the platform in a regulated life cycle: SOUP, installation qualification,
   maintenance and the regulators' expectations for cybersecurity updates.

## Prerequisites and estimated time {.unnumbered}

Chapter 4 (real-time profiles and their privileges), Chapter 7 (SBOM and SOUP), Chapter 14
(maintenance and configuration management in IEC 62304), Chapter 17 (threat model, TLS, tokens),
Chapter 21 (crash reports) and Chapter 22 (device permissions). You need a Linux machine with
systemd for the commands in this chapter; a container without systemd runs the tests but not the
units. Reading: about 3 hours. Exercises: 3 to 4 hours. Milestone: 5 hours. If time is short, do
Exercises 25.1 and 25.3.

## The platform is part of the device

### What is below MiniDAQ

Run `ldd` on `minidaq_server` and you see part of the answer: the C library, the C++ standard
library and its runtime support, and OpenSSL's `libssl` and `libcrypto`. The rest does not show up
in `ldd`: the kernel that implements every system call, its command line (the isolated CPUs of
Chapter 4), its settings (the socket buffer limit of Chapter 23), the device permissions of Chapter
22, systemd, which starts and supervises the server, and `tar`, which the updater uses. Each of
these is software your device depends on and did not develop. IEC 62304 calls such items SOUP and
asks you to identify each one with its version, to state the functional and performance requirements
it must meet, and to evaluate its published anomalies (Chapters 7 and 14). The product SBOM of
Chapter 7 lists what MiniDAQ is built from; it does not list the platform it runs on, because the
build does not know it.

The consequence is easy to state and easy to miss: two acquisition PCs that run the same MiniDAQ
version on different C libraries or kernels are, for verification purposes, two different systems.
Every test you run is evidence about the combination it ran on.

### Two ways to a controlled platform

There are two common ways to make the platform a defined thing.

- **A general-purpose distribution with pinned versions.** Start from a long-term release (MiniDAQ
  uses Ubuntu 24.04), install exactly the package versions you verified, turn off automatic updates,
  and capture the result as an image that installation copies onto every PC. You get the
  distribution's security team, its backported fixes and its documentation; you inherit its size (a
  server installation holds hundreds of packages) and its release rhythm.
- **An image built from source** with a build system such as the Yocto Project or Buildroot. You
  choose every package, its version and its configuration, and the build produces a root file system
  that contains nothing else, often read-only. You get a small, fully known system and an SBOM
  straight from the build; you take on the work of following security fixes yourself, or of buying
  that work from a vendor.

Embedded products with their own boards usually take the second road; PC-based systems such as a
scanner's acquisition computer often take the first. Either way, the decision belongs in an ADR, and
the result must be a definition you can check, not a description of how someone once installed a
machine.

### The platform definition

MiniDAQ's platform is a file in the repository, `platform/platform.json`, which names the base
distribution, the kernel series and its command line, every package MiniDAQ depends on with its
exact version, the kernel settings, the service's user and the files the image installs:

```{.json include="platform/platform.json" from="\"id\":" to="\"sysctl\""}
```

The identifier `minidaq-platform-1` matters as much as the versions. An update bundle names the
platform it was built and verified for, the updater compares it with `/etc/minidaq/platform-id`, and
a bundle for another platform is refused. A change to anything in the definition is a platform
change: a change request, the SOUP review of Chapter 14 for each new version, and a new identifier.

The definition is only useful if something checks it. `tools/platform_check.py` collects the facts
of a running system (`/etc/os-release`, `uname`, `/proc/cmdline`, `dpkg-query`, `sysctl`, the
installed files) into a JSON file, and compares them with the definition:

```{.python include="tools/platform_check.py" snippet="check"}
```

Every difference is a finding with a sentence that says what was expected; the installation
qualification (IQ) records the facts and the empty list of findings (SRS-PLT-009). The facts file is
kept, so that a later question ("which OpenSSL did site 14 run in March?") has an answer. The same
tool writes the platform's own SBOM in CycloneDX, with a `pkg:deb` package URL for each package, so
that a vulnerability scanner can match the distribution's advisories, which know about its
backported fixes.

### Settings that were only in the book

Earlier chapters asked for settings that nothing installed: the socket buffer limit of Chapter 23,
the CPUs isolated for Chapter 4's real-time profile, the device permissions of Chapter 22's register
windows, and a user for the server. Each is now a file under `packaging/` that the image installs,
listed in the definition with its digest, so the platform check finds a file that someone edited on
site:

| File | What it sets | Chapter |
|---|---|---|
| `sysctl/90-minidaq.conf` | `net.core.rmem_max = 4194304` | 23 |
| `udev/90-minidaq-feb.rules` | group `minidaq` may map the boards' UIO devices | 22 |
| `sysusers/minidaq.conf` | the system user and group `minidaq` | this one |
| `systemd/minidaq.service` | the service, its watchdog and its privileges | this one |
| `systemd/minidaq-rollback.service` | the return to the last confirmed version | this one |
| kernel command line | `isolcpus=1-3 nohz_full=1-3` | 4 |

## Running as a service

### What systemd does for a service

On almost every Linux distribution, the first process (PID 1) is systemd, and a long-running program
is a *service* described by a *unit file*. The unit says how to start the program, as which user,
with which privileges, when it counts as started, and what to do when it fails. Three properties
matter most for a medical device:

- **Readiness.** With `Type=notify`, systemd considers the service started only when the program
  sends `READY=1`. Units ordered after it, and a person watching `systemctl status`, then know that
  the server really accepts commands, not only that its process exists.
- **Restarts with a limit.** `Restart=on-failure` starts the program again when it exits with an
  error or is killed by a signal. `StartLimitBurst=` and `StartLimitIntervalSec=` stop the restarts
  after a number of failures within an interval; the unit then enters the failed state, and
  `OnFailure=` starts another unit. That is the hook for an automatic rollback.
- **The watchdog.** With `WatchdogSec=`, the program must send `WATCHDOG=1` at least once per
  interval. If it does not, systemd kills it with the signal of `WatchdogSignal=`, `SIGABRT` by
  default, and the restart policy applies.

MiniDAQ's unit uses all three:

```{.ini include="packaging/systemd/minidaq.service" from="[Service]" to="ExecStartPost="}
```

`LoadCredential=` deserves a sentence. The TLS key and the token hashes of Chapter 17 stay readable
by root only on disk; systemd copies them, for this service only, into a private directory whose
path it passes as `%d`. The server never needs permission to read `/etc/minidaq/tls/server.key`
itself, so a compromised server can read the copy it was given and nothing else under
`/etc/minidaq/tls/`.

### The notification protocol

The messages travel as datagrams on a Unix socket whose address systemd puts in the environment
variable `NOTIFY_SOCKET`. libsystemd offers `sd_notify()`, but systemd documents the protocol as
stable and shows how to implement it in a few lines without the library. MiniDAQ does that, which
keeps libsystemd out of its SOUP list:

```{.cpp include="minidaq/src/control/service_manager.cpp" snippet="notify"}
```

An address that starts with `@` is in the abstract namespace: no file, and the length passed to
`sendto` must count exactly the bytes of the name, which is why the code computes it instead of
using `sizeof(addr)`. A new socket for every message is what `sd_notify()` does too; the messages
are rare, and no descriptor stays open for a child process to inherit.

The watchdog's interval also arrives in the environment, as `WATCHDOG_USEC`, and possibly with
`WATCHDOG_PID`, the process the watchdog is meant for:

```{.cpp include="minidaq/src/control/service_manager.cpp" snippet="environment"}
```

A value that does not parse is an error, and the server refuses to start: a unit and a program that
disagree about the protocol should be found at installation, not by running without a watchdog.
Exercise 25.1 asks you to write these rules yourself and to explain each one.

`READY=1` is sent after the control API listens, not when `main` starts (SRS-PLT-001). Measured on
the development machine, with one simulated board, it arrives 5 to 9 ms after the process starts
(`measurements/ch25/service_and_update.txt`). At shutdown the server sends `STOPPING=1` with the
signal that caused it, which shows up in `systemctl status` and the journal.

## A watchdog that sees inside the process

### Why a timer is not enough

The obvious way to feed a watchdog is a thread that sends `WATCHDOG=1` every few seconds. It catches
a process that has died, which the restart policy catches anyway. It does not catch the failure of
this chapter's opening: a thread blocked forever while the others, including the timer, go on. A
watchdog is only as good as the evidence behind each ping. MiniDAQ's ping means "every loop that
matters has made progress recently".

### Heartbeats

Each loop that matters owns a heartbeat, a time stamp that it updates on every pass. Reading and
writing it must never block and never take a lock that a hung thread could hold, so it is one atomic
integer:

```{.cpp include="minidaq/include/minidaq/rt/health.hpp" snippet="heartbeat"}
```

The release store and the acquire load make the time stamp a value that the reader sees whole;
nothing else is published through it, so no stronger ordering is needed. A health monitor knows
which heartbeats to watch and how long each may be silent:

```{.cpp include="minidaq/include/minidaq/rt/health.hpp" snippet="monitor"}
```

Three loops beat: the acquisition service's monitor (every 20 ms by default, may be silent for 2 s),
the control server's poll loop (at least every 100 ms, 5 s) and, with hardware, the slow control
(every 100 ms by default, 3 s). The limits are many periods long on purpose: a loop that is busy for
a second is not hung, and a watchdog that kills a busy server during a scan does more harm than the
hang it guards against. The longest legitimate pause decides each limit; the values in MiniDAQ are
book-level numbers (assumption: confirm with team, against the slowest command and the slowest board
operation).

### The watchdog thread

The thread pings at half the interval, as systemd recommends, and only while no heartbeat is silent.
When the health changes, it tells systemd in a `STATUS=` line and writes an audit record, so that
the reason is on file before anything kills the process:

```{.cpp include="minidaq/src/control/service_manager.cpp" snippet="run"}
```

The server wires it up after its control API listens, and only then sends `READY=1`:

```{.cpp include="minidaq/apps/minidaq_server.cpp" snippet="watchdog"}
```

`FakeBoard` gained a fault that reproduces the opening's failure, `hung_bus`: the first register
access blocks for a minute. The measurement starts the server under a stand-in for systemd with
`WatchdogSec=10s` and that fault:

| What happens | Seconds after the start |
|---|---:|
| `READY=1` and the first ping | 0.01 |
| slow control silent for its 3 s limit | 3 |
| the watchdog thread's next check: `STATUS=unhealthy: slow control never beat`, no ping | 5.01 |
| systemd's deadline: the last ping plus `WatchdogSec` | 10.01 |

A healthy server sent a ping every 5.00 s for 32 s in the same measurement. In general, a hang is
acted on at most `WatchdogSec` after the last ping, and the last ping comes at most one silence
limit after the hang began, so the bound is the interval plus the longest silence limit: 15 s here.
A shorter interval detects sooner and raises the risk of killing a server that was only slow; on a
scanner, where a restart ends the scan in progress, 10 s is a reasonable start (assumption: confirm
with team).

### After the watchdog fires

What follows is the crash path you already have. systemd sends `SIGABRT`; the handler of Chapter 21
writes the crash report with every thread's stack, which shows the slow-control thread in the
register read; the kernel writes a core dump if the site allows it; and `Restart=on-failure` starts
the server again 2 s later. If the board is still hung, the slow control will not beat in the new
process either, the watchdog fires again, and after the third failure within five minutes the unit
fails and stays failed: an endless restart loop would hide the problem and fill the disk with core
dumps.

The service-level watchdog has a limit of its own: it cannot catch a hung systemd or a hung kernel.
For those, systemd can feed the PC's hardware watchdog (`RuntimeWatchdogSec=` in `system.conf`),
which resets the machine when systemd itself stops. Whether the acquisition PC has one, and whether
a reset is the right reaction during a scan, is a platform decision (assumption: confirm with team).

## Least privilege for a service

### What the server needs

Chapter 4's real-time profile asks for `SCHED_FIFO` priorities and locked memory. The easiest way to
get them is to run as root, which also gives the server every other power on the machine: one bug in
the parser of the control API and an attacker owns the PC (threat T-07). The unit takes the opposite
approach: the server runs as the user `minidaq`, with no capabilities at all, and gets exactly what
the profiles need through resource limits (`LimitRTPRIO=80`, `LimitMEMLOCK=infinity`), which an
unprivileged process may use up to the limit.

The rest of the unit removes what the server does not use:

```{.ini include="packaging/systemd/minidaq.service" from="User=minidaq" to="SystemCallErrorNumber="}
```

Read it in groups. The file system is read-only except for the server's state and runtime
directories (`ProtectSystem=strict`, `StateDirectory=`, `RuntimeDirectory=`), and `/home` is
invisible. Devices are closed except the UIO register windows of the boards. The kernel's tunables,
modules, logs, clock and control groups are out of reach. Only three address families exist: IP,
Unix sockets and netlink, the last because `getifaddrs` uses it to find the readout interface
(Chapter 23). No new privileges may be gained through a setuid program, memory may not be both
writable and executable, and system calls outside the systemd group `@system-service` or inside
`@privileged` fail with `EPERM`.

`RestrictRealtime=yes` is missing on purpose, and the comment says why: it would refuse exactly the
`SCHED_FIFO` the profile needs. Every directive that a hardening checklist recommends and the unit
leaves out should have such a comment.

### Measuring the result

`systemd-analyze security` scores a unit's exposure from 0 (nothing exposed) to 10. With
`--offline=true` it reads the unit file instead of a running service, so it works on a build
machine. The measurement records the score; on every build, the test `packaging.units` checks
that the unit keeps its central directives (no capabilities, no new privileges, a read-only
system) and that `systemd-analyze verify` accepts it:

| Unit | Exposure | Rating |
|---|---:|---|
| the same service without its hardening lines | 9.4 | UNSAFE |
| `minidaq.service` as shipped | 1.7 | OK |

A score is a summary, not a proof. The more useful check is whether the system-call filter refuses
something the server needs, which would show up as an `EPERM` in some rarely used path months later.
The measurement runs a configure, start, wait and status sequence under `strace -f -c` and compares
the calls it made with the filter: 45 different system calls, none refused. That covers the
synthetic source only; a run with UDP input and list-mode files adds `recvmmsg`, `fsync` and the
scheduling calls of the real-time profile, which are all in `@system-service`. Running the system
tests of each mode against the installed unit, as part of the installation qualification, is how to
cover the paths a short measurement does not take.

## Updates that can be rolled back

### What can go wrong

An update replaces software that works with software that should work better. Each of the ways it
can fail must leave a scanner that acquires:

| Failure | What must happen |
|---|---|
| The power fails halfway through | a version that was checked runs after the restart |
| The new version does not start | the old version runs again, without a person |
| The new version starts and has a defect | a person can return to the old version in seconds |
| The bundle was damaged in transit | it is refused before anything changes |
| The bundle was not made by the manufacturer | it is refused before anything changes |
| The bundle is for another platform | it is refused |
| The bundle is an older version | it is refused unless a person asks for a downgrade |
| Two updates run at once | the second one is refused |

Copying files over the running version fails most of these. Package managers handle several, not the
power cut halfway through (a half-installed package needs a person), not the return to the old
version without a person, and their trust is in whoever can publish to the repository the PC reads.
MiniDAQ's updater handles MiniDAQ's own files; the platform below is updated as an image by the
platform's own process (ADR 0020).

### A signed bundle

A bundle is three files in a directory: the archive `minidaq-X.Y.Z.tar.gz`, the manifest
`update.json`, and its signature `update.json.sig`. The manifest names the archive with its size and
SHA-256 digest, and says what the bundle is:

```{.cpp include="minidaq/include/minidaq/update/bundle.hpp" snippet="manifest"}
```

The release side builds the archive reproducibly: members sorted, owner 0, modes 0755 or 0644, every
time and the gzip header set from `SOURCE_DATE_EPOCH`, and a `MANIFEST.sha256` inside listing every
file's digest. The same stage gives the same bytes, so the archive can be compared with the SBOM and
the build record later (Chapter 20).

```{.python include="tools/make_update.py" snippet="archive"}
```

The manifest is then signed with Ed25519 (RFC 8032), whose signatures are 64 bytes, whose
verification needs no choice of hash or padding, and which OpenSSL 3, already in the platform,
provides:

```{.python include="tools/make_update.py" snippet="sign"}
```

On the acquisition PC, the updater verifies the signature before it parses a single byte of the
manifest, with each public key in `/etc/minidaq/update-keys/` in turn; only Ed25519 keys count:

```{.cpp include="minidaq/src/update/bundle.cpp" snippet="verify"}
```

Then the manifest's product and platform are compared with the PC's, its version with the confirmed
one (Exercise 25.2 is the comparison done fully by the rules of Semantic Versioning), and the
archive's size and digest with the manifest's. Only then is anything written. Several keys are
accepted so that a new key can be installed before the old one is retired; the private key belongs
to the release process, in a hardware security module or on an offline machine, never in the
repository or on a PC (assumption: confirm with team how the key is held and who may sign).

### Two slots and a link

The installed system under `/opt/minidaq` has two directories for versions, `slots/a` and `slots/b`,
and a symbolic link `current` that points to one of them. The unit starts
`/opt/minidaq/current/bin/minidaq_server`. A state file records which slot holds the last confirmed
version and which, if any, holds a trial:

```{.cpp include="minidaq/include/minidaq/update/slots.hpp" snippet="state"}
```

Switching versions is replacing the link, and `rename(2)` replaces it atomically: at every instant,
`current` exists and points to one slot or the other.

```{.cpp include="minidaq/src/update/slots.cpp" snippet="switch"}
```

The `fsync` of the directory after the rename is what makes the switch survive a power cut: without
it, the rename may still be only in memory when the power fails.

### Install, confirm, roll back

An installation extracts into the slot that does not run, checks every file, records the new version
as a trial and switches:

```{.cpp include="minidaq/src/update/slots.cpp" snippet="install"}
```

`confirm` makes the trial the good version; `rollback` switches back and forgets the trial:

```{.cpp include="minidaq/src/update/slots.cpp" snippet="confirm"}
```

The unit does the rest. `ExecStartPost=+/usr/lib/minidaq/minidaq_update confirm` runs once the
server has sent `READY=1`, so a version that comes up is confirmed and stays after a reboot. A
version that does not come up fails three times; the unit fails; `OnFailure=` starts
`minidaq-rollback.service`, which rolls back and starts the server again on the good version. If the
failing version is already the confirmed one, `rollback` has nothing to do and exits with status 3
(SRS-PLT-010), the rollback unit fails, and the system waits for a person instead of looping. The
updater itself is installed by the image outside the slots, so no update can break the way back.

"Comes up" is a weak definition of "works". A version that starts and then acquires wrong data is
confirmed all the same. A stricter confirmation, after a daily quality-control scan for instance, is
a later design decision that ADR 0020 records as open.

The measured cost is small: installing a bundle of the three programs (0.7 MB, 1.7 MB unpacked) took
54 to 60 ms, a rollback and a confirmation 5 ms each. The time a site cares about is the server's
restart, a few milliseconds to `READY`, and the minutes of the service engineer's procedure around
it.

### Surviving a power cut

The order of the writes is the design. Every write must leave the disk in a state from which the
system starts and runs a version that was checked, and the program that starts next must know what
each interrupted operation left behind:

- **Install: verify, extract, check, record, switch.** A cut before the record leaves a slot that
  nothing points to. A cut between the record and the switch leaves a recorded trial that is not
  current; the next start discards it, and the old version runs.
- **Rollback: switch, then record.** A cut between the two leaves a recorded trial that is not
  current, which the next start discards: the rollback completes itself. The other order could leave
  the failed version running with nothing saying it is a trial.
- **Confirm: one atomic write** of the state file, written to a temporary name, synced and renamed.

`open()`, which every command runs first, does that repair:

```{.cpp include="minidaq/src/update/slots.cpp" snippet="open"}
```

The unit test `Update.APowerCutAfterAnyStepLeavesAVersionThatRuns` gives the store a hook that is
called after each step and throws, simulating the power failure there; it does that after every step
of an install and a rollback, opens the store again and checks that `current` names a slot whose
files verify (SRS-PLT-007). Exercise 25.3 asks you to find the orders yourself, on a model of the
disk small enough to cut after every single write.

### Extracting without trusting the archive

A signed archive is trusted to contain what the release tool put in it, but `tar` is a powerful
program and an archive is a list of instructions for it: member names with `..`, absolute paths,
symbolic links, device files, setuid bits, owners. The updater calls `tar` as a child process, with
an absolute path, a clean environment and options that drop owners and permissions, after listing
the members and refusing any name outside the slot:

```{.cpp include="minidaq/src/update/slots.cpp" snippet="spawn"}
```

`posix_spawn` with an environment that holds only `LC_ALL=C` means that no `PATH`, `LD_PRELOAD` or
locale of the caller reaches `tar`, and that its listing of member names is in a known format. After
extraction, every file in the slot is compared with the archive's `MANIFEST.sha256`: nothing
missing, nothing extra, no link, no special file, every digest equal (SRS-PLT-004). Exercise 25.4 is
that check.

### Image updates and their frameworks

MiniDAQ's updater changes only MiniDAQ's files. Updating the platform (kernel, libraries, systemd)
raises the same problems at a larger scale, and established open-source frameworks solve them: RAUC,
SWUpdate and Mender install whole root file systems into A/B partitions and let the bootloader fall
back to the old partition when the new one does not boot; OSTree keeps versioned file-system trees
and switches between them at boot. All of them sign their bundles, and all of them become SOUP of
the platform. With a secure-boot chain (firmware verifies the bootloader, the bootloader the kernel,
the kernel the root file system), the signature check moves from a program into the hardware's root
of trust, which is the strongest form and the most work to set up. Which of these the platform uses
is the platform team's decision (assumption: confirm with team); MiniDAQ's design must not depend on
it, which is why its own updater only touches `/opt/minidaq`.

::: box-regulated
- **The platform is SOUP.** IEC 62304 asks you to identify every SOUP item by name, manufacturer and
  version, and to evaluate its anomaly lists; the platform definition and its SBOM are that
  identification for everything below MiniDAQ. A platform change goes through the same change
  control and SOUP review as a library upgrade (Chapter 14).
- **Installation is a verified activity.** An installation qualification records that the installed
  system matches its definition: the platform check's facts and findings, the unit files' digests,
  the user and its permissions. Many manufacturers run the system tests against the installed unit
  as part of it.
- **Updates are maintenance.** IEC 62304's software maintenance process covers how released changes
  reach installed devices, and ISO 13485 asks for control of servicing. The signed bundle, its SBOM,
  the platform it is for, the confirmation and the rollback history (`history.jsonl`) are the
  records.
- **Regulators expect updatability.** In the United States, section 524B of the Federal Food, Drug,
  and Cosmetic Act requires manufacturers of cyber devices to provide postmarket updates and
  patches, and the FDA's premarket cybersecurity guidance (2023) expects the submission to describe
  how software is updated and how the updates are authenticated. The EU's MDR, in Annex I section
  17, requires software to be developed and manufactured according to the state of the art, taking
  into account information security among other principles. A device without an authenticated update
  path is hard to defend in either market (verify: the current guidance text before you cite it).
- **The signing key is part of the design.** Who holds it, how it is protected and how it is
  replaced belong in the security risk management file and the threat model (T-39 to T-53 in
  MiniDAQ's), not only in an operations note.
:::

::: box-mistakes
- **Feeding the watchdog from a timer.** It proves that the timer runs. Ping only when the loops you
  depend on have beaten.
- **Silence limits as short as the loop's period.** A busy second kills a healthy server in the
  middle of a scan. Measure the longest legitimate pause first.
- **Restarting forever.** A fault that survives a restart will survive the next one. Limit the
  restarts and leave the unit failed for a person.
- **Running as root to get real-time priorities.** Resource limits give exactly the priorities and
  locked memory the profile needs, without capabilities.
- **Copying the new version over the running one.** A power cut leaves a mix, and there is no way
  back. Install beside it and switch atomically.
- **Switching before checking, or recording a rollback before switching.** Each order leaves a
  window in which the running version is not the one the state describes. Write the order down and
  cut the power after every step in a test.
- **Parsing before verifying.** Code that parses an unsigned manifest runs on attacker-controlled
  input. Verify the signature over the raw bytes first.
- **Trusting what the archive says about itself.** Refuse members outside the slot, drop owners and
  permissions, and compare the extracted tree with the signed list.
:::

::: box-askteam
1. How is the acquisition PC's platform defined, who may change it, and how does an installed PC
   prove that it matches?
2. Which process is the scanner's software running as, with which privileges, and which of them does
   it need?
3. What supervises the acquisition software, how would it notice a hung thread, and what happens
   then?
4. How does a new version reach an installed scanner, who signs it, and how is the signing key
   protected?
5. What happens if the power fails during an update, and when did someone last test that?
6. How does a site return to the previous version, how long does it take, and who may do it?
7. How are the platform's security fixes evaluated and delivered, and how long do they take to reach
   a site?
:::

## Exercises {.unnumbered}

**Exercise 25.1 (E): What systemd asks of a service.** *Goal:* read the watchdog settings from
`WATCHDOG_USEC` and `WATCHDOG_PID` with every rule of the protocol, and split a notification
datagram into its assignments. *Starter:* `exercises/ch25/e1_watchdog_env/starter/watchdog_env.cpp`.
*Acceptance:* `tests/test_watchdog_env.cpp` passes: no variable, the ping period, a watchdog for
another process, malformed numbers, and messages with empty values, equals signs and bad keys. Then
answer in `NOTES.md` why a service pings at half the interval and why a malformed value should stop
the start. *Time:* 30 minutes.

**Exercise 25.2 (M): Which version is newer.** *Goal:* parse versions and compare their precedence
exactly as Semantic Versioning 2.0.0 defines it. *Starter:*
`exercises/ch25/e2_semver/starter/semver.cpp`. *Acceptance:* `tests/test_semver.cpp` passes: the
parts, sixteen versions the specification forbids, the example chain of its section 11, numbers that
string comparison gets wrong, and build metadata. Then answer in `NOTES.md` where MiniDAQ's simpler
comparison goes wrong and which rule keeps it safe. *Time:* 45 minutes.

**Exercise 25.3 (H): Survive a power cut at any step.** *Goal:* install, confirm and roll back on a
model of the disk so that a power failure after any write leaves a system that starts a checked
version, and repair what each cut leaves. *Starter:*
`exercises/ch25/e3_power_cut/starter/ab_slots.cpp`. *Acceptance:* `tests/test_ab_slots.cpp` passes:
each operation cut after every write, nothing to do, and alternating slots. Then answer in
`NOTES.md` why install and rollback order their last two writes in opposite ways. *Time:* 90
minutes.

**Exercise 25.4 (M): Check an unpacked tree against its manifest.** *Goal:* compare a directory with
its `MANIFEST.sha256` in both directions, without following links, and refuse listed paths that
leave the tree. *Starter:* `exercises/ch25/e4_verify_tree/starter/verify_tree.cpp`. *Acceptance:*
`tests/test_verify_tree.cpp` passes: an intact tree, changed, missing and added files, links and a
FIFO, paths outside the tree and duplicates, and malformed lines. Then answer in `NOTES.md` what
this check catches that the archive's signed digest does not. *Time:* 60 minutes.

## MiniDAQ milestone: a platform, a watchdog and signed updates {.unnumbered}

::: box-milestone
**Goal.** MiniDAQ runs on a defined platform as a hardened systemd service whose watchdog sees a
hung loop, and new versions arrive as signed bundles that install into a second slot as a trial,
roll back by themselves when they do not start, and survive a power cut at any step. **Start:** tag
`ch24`. **End:** tag `ch25`.
:::

1. Write change request CR-0011 and ADR 0020; add SRS-PLT-001 to SRS-PLT-011 (SRS version 14), risk
   controls RC-32 and RC-33 (H-05) and RC-34 (H-08), and the update elements and threats T-39 to
   T-53 to the threat model (version 3); update the architecture description (version 11), the SOUP
   list (version 8) and the tool list.
2. Add `rt::Heartbeat` and `rt::HealthMonitor`, beat in the acquisition service's monitor, the
   control server and the slow control, and give `FakeBoard` the fault `hung_bus`.
3. Add `control::ServiceManagerLink` and `control::Watchdog`, and in `minidaq_server` the watch
   list, the watchdog, `READY` after the control API listens and `STOPPING` at shutdown.
4. Add the item `update` (`bundle`, `slots`) and the program `minidaq_update`, the release tool
   `tools/make_update.py`, and their tests, including the power cut after every step.
5. Add `platform/platform.json`, `tools/platform_check.py`, the files under `packaging/` and their
   check `tools/check_units.py`, and the installation document `docs/platform/installation.md`.
6. Add the measurement `measurements/ch25/service_and_update.py` and Exercises 25.1 to 25.4.

**Definition of done.** `ci/run_all.sh` is green on all six presets and static analysis reports
nothing; the trace matrix shows SRS-PLT-001 to SRS-PLT-011 verified; `systemd-analyze security
--offline=true` rates the unit "OK"; the system-call filter refuses nothing the measurement's run
made; every starter of the chapter fails. Tag `ch25`.

## Check yourself {.unnumbered}

1. Name five pieces of software below MiniDAQ that `ldd` does not show, and say why each one matters
   to the device's behavior.
2. What does a general-purpose distribution with pinned versions give you that a Yocto image does
   not, and the other way round?
3. Why does the update bundle name a platform, and what should happen when it names another one?
4. With `Type=notify`, when does systemd consider the service started? Why does MiniDAQ send
   `READY=1` after the control API listens and not at the start of `main`?
5. A watchdog thread that pings every 5 s whatever happens: which failures does it catch, and which
   does it miss?
6. The slow control may be silent for 3 s and `WatchdogSec` is 10 s. A register read hangs at time
   t. What is the latest time systemd acts, and what does it do?
7. Why are the silence limits several times each loop's period? What would a limit equal to the
   period cause during a scan?
8. How does the server get `SCHED_FIFO` priorities without root or any capability?
9. The unit has no `RestrictRealtime=yes`. Why not, and what should be next to every recommended
   directive a unit leaves out?
10. Why does the updater verify the signature before it parses the manifest?
11. An install records the trial and then switches; a rollback switches and then records. Explain
    both orders with a power cut between the two writes.
12. What does `rename(2)` guarantee about `current`, and what does the `fsync` of the directory add?
13. The archive's digest was verified before extraction. Why compare every extracted file with
    `MANIFEST.sha256` as well?
14. A new version starts, is confirmed, and its first scan writes corrupt data. What happens
    automatically, what does a person have to do, and what design change would catch it?

## Summary {.unnumbered}

- The platform below MiniDAQ (kernel, C and C++ libraries, OpenSSL, systemd, `tar`, kernel settings)
  is SOUP and part of what you verify. `platform/platform.json` defines it with exact versions and
  an identifier; `tools/platform_check.py` checks an installed system against it and writes its
  SBOM.
- Settings that earlier chapters only described (socket buffers, isolated CPUs, device permissions,
  the service user) are now installed files, listed with their digests.
- The server runs as a `Type=notify` systemd service: `READY=1` once the control API listens,
  restarts on failure, three failures within five minutes and the unit fails and starts the rollback
  unit. The notification protocol takes a few system calls and no library.
- The watchdog pings at half `WatchdogSec` only while every watched loop has beaten within its limit
  (2 s, 3 s, 5 s). A hung register read was reported unhealthy after 5 s and would be killed 10 s
  after the last ping, with `SIGABRT` and a crash report that shows where it hung.
- The server runs as its own user without capabilities; resource limits give it the real-time
  priorities and locked memory it needs. The hardening lowers `systemd-analyze security`'s exposure
  from 9.4 to 1.7, and the system-call filter refused none of the 45 calls a run made.
- Updates are signed bundles: a reproducible archive, a manifest with its digest, an Ed25519
  signature verified before anything is parsed. They install into the slot that does not run, are
  checked file by file, run as a trial that `confirm` keeps and a failed start rolls back, and
  refuse other platforms and older versions.
- The order of the writes is the design: install records before it switches, rollback switches
  before it records, and `open()` repairs what any cut leaves; a test cuts the power after every
  step. Installing took about 60 ms and a rollback 5 ms.
- Updates are maintenance in IEC 62304's sense and an explicit expectation of regulators; the
  signing key and its handling belong in the threat model and the security risk management file.

## Further reading {.unnumbered}

- The systemd manual pages `systemd.service(5)`, `systemd.exec(5)`, `systemd.unit(5)`,
  `systemd.kill(5)` and `sd_notify(3)`, at freedesktop.org: the reference for every directive and
  message used in this chapter, including the stable notification protocol and its standalone
  implementation.
- L. Poettering, the "systemd for Administrators" series of blog posts (0pointer.de), in particular
  the parts on watchdogs and on securing services: the reasoning behind the features, from their
  author.
- The Yocto Project documentation (docs.yoctoproject.org) and the Buildroot manual (buildroot.org):
  how an embedded Linux image is built from source, with its license and SBOM output.
- RAUC (rauc.io), SWUpdate (sbabic.github.io/swupdate), Mender (mender.io) and OSTree
  (ostreedev.github.io/ostree): open-source A/B and image update frameworks, each with its design
  documentation.
- The Update Framework (theupdateframework.io) and J. Samuel, N. Mathewson, J. Cappos and R.
  Dingledine, "Survivable Key Compromise in Software Update Systems", ACM CCS 2010: the attacks on
  update systems and a design that survives the theft of a signing key.
- S. Josefsson and I. Liusvaara, "Edwards-Curve Digital Signature Algorithm (EdDSA)", RFC 8032,
  2017: the signature scheme of the bundles.
- T. Preston-Werner, *Semantic Versioning 2.0.0* (semver.org): the version precedence rules of
  Exercise 25.2.
- FDA, *Cybersecurity in Medical Devices: Quality System Considerations and Content of Premarket
  Submissions*, final guidance, 2023, and section 524B of the Federal Food, Drug, and Cosmetic Act:
  what a submission must say about updates and patches.
- IEC 62304:2006+A1:2015, clause 6 (software maintenance process) and clause 8 (configuration
  management, including SOUP identification); IEC 81001-5-1:2021 for security activities across the
  product life cycle, including the delivery of updates.
