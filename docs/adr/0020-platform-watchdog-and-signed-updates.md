# 0020. A defined platform, a watchdog that sees inside the server, and signed updates into two slots with rollback

Date: 2026-10-26
Status: Accepted

## Context

Until Chapter 25, MiniDAQ ended where its programs ended. Four things on the installed system
were nobody's design:

- **The platform.** The C library, the C++ runtime, OpenSSL, the kernel and its settings are SOUP
  that the product's SBOM does not list (Chapter 7), and settings the earlier chapters depend on
  (`net.core.rmem_max` of Chapter 23, the isolated CPUs of Chapter 4's real-time profile, the
  device permissions of Chapter 22) were written in the book, not in anything installed.
- **Supervision.** A server that crashes is restarted by whoever notices. A server whose loop
  hangs, a register read that never returns or a lock never released, keeps running, keeps its
  port open and answers nothing, and only a person notices.
- **Privilege.** The real-time settings need privileges; the simplest way to get them is root.
- **Updates.** A new version is copied over the old one. A copy cut by a power failure leaves a
  mix of versions; a version that does not start leaves the scanner without one; and nothing
  stops a program that the manufacturer did not release from being installed (threat T-07).

## Options

For supervision:

1. **Restart on exit only** (`Restart=on-failure`). Simple; blind to a hang.
2. **A watchdog pinged by a timer thread.** Catches a dead process, which a restart already
   catches; the timer keeps pinging while every other thread hangs.
3. **A watchdog pinged only while the process's loops beat.** Each loop that matters (the
   acquisition service's monitor, the control server, the slow control) stamps a heartbeat on
   every pass; the ping is sent only while every stamp is recent.

For updates:

1. **A package manager (`apt`) with the distribution's signing.** Signed, well known; an
   interrupted installation is repaired by hand, there is no automatic return to the last good
   version, and the trust is in whoever can publish to the repository the PC uses.
2. **An update framework as SOUP** (RAUC, SWUpdate, Mender, OSTree). Full image updates, A/B
   partitions, rollback through the bootloader; the right tool for a whole image, and a large
   SOUP item with its own configuration to qualify.
3. **A small updater of MiniDAQ's own for MiniDAQ's own files.** Two directories ("slots") and a
   link that is switched atomically; an Ed25519-signed manifest; a trial that the service
   confirms when it comes up and that systemd's failure handling rolls back. A few hundred lines
   with OpenSSL, which MiniDAQ already uses.

## Decision

Supervision option 3; update option 3, for MiniDAQ's programs, while the platform below them is
an image with exact package versions (`platform/platform.json`) that changes only by change
request, and is updated by the site's image process (option 1 or 2 applies to that, chosen with
the platform team: assumption: confirm with team).

- `minidaq_server` runs under systemd as `Type=notify` (`packaging/systemd/minidaq.service`):
  READY once the control API listens, STOPPING at shutdown, and WATCHDOG=1 every half
  `WatchdogSec=` only while every heartbeat is recent (SRS-PLT-001, SRS-PLT-002, RC-32). The
  notification protocol is implemented in a few system calls (`control/service_manager`):
  systemd guarantees it to be stable and shows how to implement it without libsystemd, so it
  needs no new SOUP.
- A missed watchdog makes systemd send SIGABRT, which writes the crash report of Chapter 21 and
  a core dump, and restarts the server.
- The server runs as its own user without capabilities; `LimitRTPRIO=` and `LimitMEMLOCK=` give
  exactly what the real-time profiles need; the rest of the unit restricts the file system,
  devices, address families and system calls (`systemd-analyze security` exposure 1.7).
- `minidaq_update` (item update, class B) installs a bundle into the slot that is not running,
  verifies it (signature, then archive digest, then every file), records it as a trial and
  switches `current`; `confirm` runs after READY; three failed starts make the unit fail, and
  `OnFailure=` runs `rollback` (SRS-PLT-003 to SRS-PLT-007, SRS-PLT-010, SRS-PLT-011, RC-33,
  RC-34). It is installed by the image outside the slots, so that no update can break its own
  rollback.

## Consequences

### Positive

- A hung server is restarted within the watchdog interval plus the longest silence limit, with
  a crash report that shows where it hung (`measurements/ch25/`).
- An update that does not start costs three restarts and a rollback, not a site visit; a power
  cut during an update leaves a version that runs (tested after every step).
- Only software signed by the manufacturer's key, for this platform, and not older than the
  confirmed version, can be installed; T-07 moves from "environment" to "mitigated".
- The platform is written down and checked at installation (`tools/platform_check.py`), with
  an SBOM of its own: the SOUP below MiniDAQ is identified, as IEC 62304 asks.

### Negative

- A watchdog that is too tight restarts a server that was only busy; the silence limits (2 s,
  3 s, 5 s) are several periods of each loop, and a restart during a scan ends that scan. The
  limits are book-level numbers (assumption: confirm with team, against the longest command).
- `confirm` after READY confirms a version that starts, not one that acquires correctly; a
  version that fails only in a run is not rolled back automatically. A stricter confirmation
  (after a daily quality-control scan) is a later decision.
- The updater does not update the platform. Kernel, libraries and systemd change through the
  image process and a platform change request; until then their security fixes wait.
- The private signing key is now the most valuable secret of the product. How it is held, who
  may sign and how a key is retired are decisions for the manufacturer's security process
  (assumption: confirm with team); the updater accepts several keys so that a new key can be
  added before the old one is removed.
