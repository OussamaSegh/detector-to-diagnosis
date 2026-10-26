# CR-0011: The platform definition, a health-gated watchdog, and signed updates with rollback

| Field | Value |
|---|---|
| Status | approved |
| Requested | 2026-10-26, by the software lead with the service organization |
| Source | design review of the installed system: the platform under MiniDAQ was not identified (SOUP, Chapter 7), a hung server kept running unnoticed (H-05), a new version was copied over the old one without a way back, and installed software was the platform's to protect (threat T-07) |
| Decision | approved, 2026-10-26, software lead, risk manager and security expert |
| Commits | pending |

## Description

The platform under MiniDAQ is defined with exact versions in `platform/platform.json`
(minidaq-platform-1) and checked at installation by `tools/platform_check.py`, which also writes
the platform's SBOM. The server runs under systemd as a notify service
(`packaging/systemd/minidaq.service`): it sends READY when its control API listens, STOPPING at
shutdown, and pings the watchdog only while its loops beat (`rt/health`, `control/service_manager`,
new item `platform`). It runs as its own user without capabilities, with resource limits for
the real-time profiles, and with the file system, devices, address families and system calls
restricted. `minidaq_update` (new item `update`, its own process) installs Ed25519-signed bundles
into the slot that is not running, as a trial that is confirmed after READY and rolled back by
`minidaq-rollback.service` when the server fails to start; `tools/make_update.py` builds and signs
the bundles on the release side. The simulated board gains the fault `hung_bus`, to test the
watchdog. An installation document (INST, version 1) describes installation, updates and the
installation qualification.

## Reason

A server whose loop hangs keeps the scanner unusable until a person notices (H-05). An update
that does not start, or is cut by a power failure, leaves no version that runs (H-05). Software
that the manufacturer did not release can be installed and then controls the acquisition (H-08,
T-07). The platform's libraries and kernel are SOUP that must be identified (IEC 62304, 8.1.2).

## Impact analysis

### Requirements

New: SRS-PLT-001 to SRS-PLT-011 (SRS version 14). No existing requirement changes. Verification
repeated: SRS-HW-001 to SRS-HW-015 (the slow control's cycle and the simulated board change),
SRS-CTL-040 to SRS-CTL-044 (the server program's start and shutdown).

### Software items and safety class

New: `platform` (class B, in the server) and `update` (class B, its own process, as root).
Changed: rt, hw, service, protocol, server, all class B: a heartbeat stamped once per pass of each
loop, which costs one clock read. No class or segregation changes inside the server; the updater
is segregated by its process and by the file permissions (architecture, section 10).

### Risk

H-05 gains RC-32 (the health-gated watchdog) and RC-33 (trial, rollback, power-cut safety). H-08
gains RC-34 (only signed bundles for this platform, not older than the confirmed version, every
file checked). Residual: a hang during a scan still ends that scan; a version that starts but fails
only in a run is not rolled back automatically (ADR 0020, consequences).

### SOUP

No new library. OpenSSL (already SOUP) is used for Ed25519 and SHA-256 too. systemd, GNU tar and
the platform's libraries are identified with exact versions in the platform definition and its
SBOM; the SOUP list refers to it.

### Interfaces and data formats

New interfaces: the sd_notify protocol to systemd (out), and the update bundle (manifest format
`minidaq-update 1`, Ed25519 signature, tar.gz archive with MANIFEST.sha256). The hardware
description 1.1 accepts the simulated fault `hung_bus`. The control API, the data formats and the
configuration do not change.

### Documents

ADR 0020 (new) and the ADR index; INST, version 1 (new); the SRS, version 14; the trace matrix;
the risk file (RC-32 to RC-34); the threat model, version 3 (elements release, bundle, updater,
slots; T-39 to T-53; T-07 mitigated); the architecture description, version 11; the software
items and layers; the design file (clause 7.5.3); the tool list (the updater's tools); the
CHANGELOG.

### Regulatory

The intended use does not change. The release notes of 0.5.0 name the platform it was verified
on; the accompanying documentation gains the installation document. The signing key's custody is
a decision of the manufacturer's security process (assumption: confirm with team), and an update
mechanism with cryptographic verification is the kind of control premarket cybersecurity
guidance asks a manufacturer to describe.

## Verification

Unit tests of the heartbeats and the watchdog (Health.ALoopIsHealthyWhileItBeatsAndGetsItsLimitToStart,
Health.EveryLoopCountsAndABeatFromBeforeTheWatchDoesNotUseUpTheLimit,
Health.TheSlowControlBeatsOncePerCycleAndAHungBusStopsIt,
ServiceManager.WithoutANotifySocketEveryCallDoesNothing, ServiceManager.ReadsTheEnvironmentAsSdNotifyDoes,
ServiceManager.SendsReadyStatusAndStoppingAsOneDatagramEach,
ServiceManager.TheWatchdogPingsOnlyWhileEveryLoopBeats) and of the updater
(UpdateVersion.OrdersReleasesAndTheirPreReleases, UpdateManifest.EveryFieldIsRequiredAndTheArchiveIsAPlainName,
Update.OnlyASignatureByATrustedEd25519KeyIsAccepted, Update.InstallsATrialThatIsConfirmedOrRolledBack,
Update.RefusesWhatTheSignatureDoesNotVouchFor, Update.RefusesAnArchiveThatWritesOutsideItsSlot,
Update.APowerCutAfterAnyStepLeavesAVersionThatRuns, Update.OneProcessAtATime); the system tests
`system.platform`; the tool tests `tools.make_update`, `tools.platform_check` and
`packaging.units`; the measurements in `measurements/ch25/`; all presets of `ci/run_all.sh` and the
static analysis.

## Decision

Approved on 2026-10-26 by the software lead, the risk manager and the security expert: new risk
controls for existing hazards, two new class B items with their own verification, no new SOUP
library, and no change to the control API or the data formats.
