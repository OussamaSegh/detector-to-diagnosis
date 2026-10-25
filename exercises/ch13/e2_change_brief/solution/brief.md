# Change brief: acquisition PC from Ubuntu 22.04 to Ubuntu 24.04

## Change

The acquisition PC's operating system moves from Ubuntu 22.04 LTS to 24.04 LTS, because
22.04's standard support ends in April 2027 and security updates must continue. The DAQ's
source code does not change, but everything below it does: kernel, C and C++ runtime
libraries, compiler, network drivers and the real-time settings.

## Software items affected

All of them run on the new platform, which is SOUP: the kernel (6.8 instead of 5.15), glibc,
libstdc++, the NIC driver and firmware, and the systemd units. The DAQ binaries are rebuilt
with a new compiler. The items with timing requirements are the readout receiver, the sorter
and the list-mode writer; the control API depends on the TLS library version.

## Software safety class

Unchanged by the platform itself, but the segregation argument that kept some items in a
lower class relied on process isolation and CPU pinning on the old kernel; it must be
re-checked on the new one.

## Risk

Re-run the ISO 14971 analysis for the hazards the platform can cause: silent packet loss
from a new driver or a smaller default receive buffer, latency spikes from a changed
scheduler, a changed fsync behavior losing data at power failure, and new vulnerabilities in
the libraries. Each hazard keeps its risk controls; the question is whether they are still
effective. New residual risks go to the risk file.

## Verification

Full regression on the new image, not only unit tests: the system tests at maximum count
rate, the latency and jitter measurements against the budget, the receive-buffer and
packet-loss tests, the crash and power-cut test of the writer, and a phantom scan compared
with the last released results. The SBOM is regenerated and scanned for vulnerabilities.

## EU

The device is certified under the MDR. A change to the platform that could affect safety or
performance must be assessed against the notified body's change notification procedure, and
the technical documentation (software description, SOUP, verification) is updated whether
or not the notified body must approve it first.

## US

Apply FDA's guidance "Deciding When to Submit a 510(k) for a Software Change to an Existing
Device" (2017): a change of operating system that could significantly affect safety or
effectiveness needs a new 510(k); otherwise it is documented in the design history with the
reasoning. Cybersecurity documentation (SBOM, risk) is updated either way.

## Switzerland

The device is placed on the Swiss market under its CE marking with a Swiss authorized
representative; the Swiss representative is informed of the change and keeps the updated
documentation available.

## Documents to update

SOUP list and SBOM, software architecture (platform section), risk management file,
verification reports, installation and service instructions, release notes and the version
history of the technical documentation.

## Decision

Proposed: go ahead after the regression passes. Owner: the DAQ lead prepares the impact
analysis; regulatory affairs decides whether the notified body and FDA must be involved
before release; the change control board approves.
