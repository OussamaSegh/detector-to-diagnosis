# Installation, updates and installation qualification of MiniDAQ

Version 1 (MiniDAQ 0.5.0-dev). Status: draft for review.
Document ID: INST. Owner: the software lead; the service organization reviews every version.

This document says how MiniDAQ is installed on the acquisition PC, how it is updated and rolled
back, and how an installation is qualified. It is written for the person who builds the platform
image and for the field engineer who installs and updates a scanner. The design behind it is
[ADR 0020](../adr/0020-platform-watchdog-and-signed-updates.md); the platform it assumes is
[`platform/platform.json`](../../platform/platform.json). Statements marked "assumption: confirm
with team" are the ones a manufacturer's service and security processes must settle.

## 1. What the platform image contains

| Path on the PC | What | Owner and mode | Source |
|---|---|---|---|
| packages of `platform.json` | Ubuntu 24.04 with exact package versions, no unattended upgrades | root | the image process (assumption: confirm with team) |
| kernel command line | `isolcpus=1-3 nohz_full=1-3`, the CPUs of the real-time profile (Chapter 4) | root | the boot loader's configuration |
| `/etc/sysctl.d/90-minidaq.conf` | `net.core.rmem_max = 4194304` (Chapter 23) | root, 0644 | `packaging/sysctl/` |
| `/usr/lib/sysusers.d/minidaq.conf` | the user and group `minidaq` | root, 0644 | `packaging/sysusers/` |
| `/etc/udev/rules.d/90-minidaq-feb.rules` | the boards' register windows for group `minidaq` (Chapter 22) | root, 0644 | `packaging/udev/` |
| `/etc/systemd/system/minidaq.service`, `minidaq-rollback.service` | the server under systemd, and its rollback | root, 0644 | `packaging/systemd/` |
| `/usr/lib/minidaq/minidaq_update` | the updater, outside the slots | root, 0755 | the release, built for this platform |
| `/etc/minidaq/platform-id` | `minidaq-platform-1` | root, 0644 | `platform.json` |
| `/etc/minidaq/update-keys/*.pem` | the manufacturer's Ed25519 public keys | root, 0644 | the manufacturer's key process |
| `/etc/minidaq/minidaq.env`, `hardware.json`, `tls/server.crt` | site settings | root, 0644 | the site's installation record |
| `/etc/minidaq/tls/server.key`, `tokens.json` | secrets, given to the service as credentials | root, 0600 | made at installation |
| `/opt/minidaq/slots/a`, `/opt/minidaq/slots/b`, `/opt/minidaq/current` | the two slots and the link to the running one | root, 0755 | `minidaq_update` |
| `/var/lib/minidaq` | data, audit trail, crash reports | `minidaq`, 0750 | systemd (`StateDirectory=`) |

The server runs as `minidaq` with no capabilities. The private signing key is never on the PC.

## 2. First installation

1. Install the image, then the site files of section 1 (settings, certificate, key, tokens).
2. Install the first version: `minidaq_update install BUNDLE_DIR`. The first version is confirmed
   at once; there is nothing to go back to.
3. `systemctl enable --now minidaq.service`.
4. Qualify the installation (section 5).

## 3. Updating MiniDAQ

An update replaces the programs, never the site files or the data.

1. Check that no acquisition is running: `minidaq_ctl status` shows the state `idle` or
   `configured`. An update restarts the server, and a restart ends a run.
2. Install: `minidaq_update install BUNDLE_DIR`. It verifies the signature, the platform, the
   version and every file before it changes anything; a refusal says why and leaves the running
   version as it was. Nothing that runs has changed yet.
3. Restart: `systemctl restart minidaq.service`. The new version runs as a trial.
4. When the server reports READY, systemd runs `minidaq_update confirm`, and the new version is
   the confirmed one. `minidaq_update status` shows it under `good`.
5. Repeat the operational checks of section 5, step 4.

If the new version fails to start three times within five minutes, systemd runs
`minidaq-rollback.service`: the confirmed version is made current again and the server is
started. The history of every operation is in `/opt/minidaq/history.jsonl`.

A downgrade is a deliberate decision, for example to return to a version after a field problem:
`minidaq_update install BUNDLE_DIR --allow-older`, recorded with its reason in the service
record (assumption: confirm with team who may decide it).

## 4. When something goes wrong

| What you see | What it means | What to do |
|---|---|---|
| `install refused: ... does not verify` | The bundle is not signed by a trusted key, or was changed | Get the bundle again from the manufacturer; never add a key to make it pass |
| `install refused: ... for the platform` | The bundle was built for another platform | Get the bundle for this platform, or update the platform first |
| `version X is installed and not confirmed` | A trial is pending | Restart the service so that it is confirmed, or `minidaq_update rollback` |
| `minidaq-rollback.service` failed, exit status 3 | The confirmed version itself fails to start | Read the journal and the crash reports in `/var/lib/minidaq`; this is a field problem, not an update problem |
| `repaired: ...` when the updater starts | A power cut interrupted an operation; the updater finished or undid it | Nothing; the history records it |
| `state.json is damaged` | The update state cannot be read | Do not edit it; call the manufacturer's service (assumption: confirm with team) |
| `STATUS=unhealthy: ...` in `systemctl status minidaq` | A loop of the server stopped; systemd will restart it within the watchdog interval | Keep the crash report and the core dump for the problem report |

## 5. Installation qualification

Run after the first installation, after every platform change and after every update, and keep
the outputs with the installation record.

1. **The platform.** `tools/platform_check.py --collect facts.json --sbom platform.cdx.json`
   from the release's code: no DEVIATION. The facts file and the platform SBOM are records.
2. **The units.** `systemd-analyze security minidaq.service`: the exposure level is the one the
   release reports (1.8 for 0.5.0), or lower.
3. **The installed version.** `minidaq_update status`: `good` is the released version, `trial` is
   null. `minidaq_ctl hello` names the same version as
   the server's (`"server": "minidaq X.Y.Z"`).
4. **Operation.** `systemctl status minidaq.service` shows `active (running)` and the status
   `healthy` or `state idle`; a short run with the site's acquisition configuration completes
   with its integrity verdict `complete`; each board reports a firmware version the interface
   control document supports.

## 6. Changes

| Version | Change |
|---|---|
| 1 | First version (Chapter 25, CR-0011, ADR 0020). |
