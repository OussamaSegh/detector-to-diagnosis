#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Checks MiniDAQ's systemd units (Chapter 25, ADR 0020): the rules the design depends on, then
systemd's own verification and exposure score where systemd-analyze is installed.

Usage: tools/check_units.py REPO_ROOT

The rules are the ones a later edit could break without any test noticing: the server is
Type=notify with a watchdog and restarts; a failure goes to the rollback unit; it runs as its own
user with no capabilities; the resource limit for real-time priorities covers the highest priority
of every real-time profile in minidaq/profiles/ (so that a profile never fails on the installed
system), and RestrictRealtime= does not forbid them; the confirmation runs only after READY.
systemd-analyze verify needs the programs to exist, so it runs on a copy of the units whose
program paths point to empty stand-ins.
"""
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile


def directives(path):
    """{name: [values]} of a unit file, with continuation lines joined."""
    out = {}
    text = re.sub(r"\\\n\s*", " ", path.read_text())
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(("#", ";", "[")) or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out.setdefault(k.strip(), []).append(v.strip())
    return out


def max_rt_priority(profiles):
    top = 0
    for conf in profiles.glob("*.conf"):
        for m in re.finditer(r"^\s*\w+\.priority\s*=\s*(\d+)", conf.read_text(), re.M):
            top = max(top, int(m.group(1)))
    return top


# [snippet:rules]
def check_rules(root):
    unit = directives(root / "packaging/systemd/minidaq.service")
    rollback = directives(root / "packaging/systemd/minidaq-rollback.service")
    errors = []

    def one(name):
        values = unit.get(name, [])
        return values[-1] if values else None

    def need(name, wanted, why):
        if one(name) != wanted:
            errors.append(f"minidaq.service: {name}={one(name)!r}, must be {wanted!r} ({why})")

    need("Type", "notify", "READY only once the control API listens, SRS-PLT-001")
    need("Restart", "on-failure", "a crash or a missed watchdog restarts it")
    need("OnFailure", "minidaq-rollback.service", "a trial that cannot start is rolled back, SRS-PLT-006")
    need("NoNewPrivileges", "yes", "least privilege, Chapter 17")
    need("CapabilityBoundingSet", "", "no capabilities: real-time comes from resource limits")
    need("ProtectSystem", "strict", "the slots and /etc are read-only to the server")
    if not one("WatchdogSec") or one("WatchdogSec") in ("0", "infinity"):
        errors.append("minidaq.service: WatchdogSec= must be set (SRS-PLT-002)")
    if one("User") in (None, "root", "0"):
        errors.append("minidaq.service: User= must be the service's own user, not root")
    if one("RestrictRealtime") == "yes":
        errors.append("minidaq.service: RestrictRealtime=yes forbids the SCHED_FIFO stages of Chapter 4")
    top = max_rt_priority(root / "minidaq/profiles")
    limit = one("LimitRTPRIO")
    if limit is None or not limit.isdigit() or int(limit) < top:
        errors.append(f"minidaq.service: LimitRTPRIO={limit} is below priority {top} of a real-time profile")
    if one("LimitMEMLOCK") != "infinity":
        errors.append("minidaq.service: LimitMEMLOCK=infinity, or lock_memory of a profile fails")
    if not any("minidaq_update confirm" in v and v.startswith("+") for v in unit.get("ExecStartPost", [])):
        errors.append("minidaq.service: ExecStartPost=+.../minidaq_update confirm (after READY, privileged)")
    if not any("minidaq_update rollback" in v for v in rollback.get("ExecStart", [])):
        errors.append("minidaq-rollback.service: ExecStart= must run minidaq_update rollback")
    if rollback.get("Type", [None])[-1] != "oneshot":
        errors.append("minidaq-rollback.service: Type=oneshot, so that its ExecStartPost= runs only on success")
    return errors
# [/snippet:rules]


def systemd_verify(root):
    """systemd-analyze verify on copies of the units with stand-in programs; [] when it passes."""
    analyze = shutil.which("systemd-analyze")
    if analyze is None:
        print("check_units: systemd-analyze not found; systemd's own verification skipped")
        return []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        copies = []
        for unit in sorted((root / "packaging/systemd").glob("*.service")):
            text = unit.read_text()
            for program in sorted(set(re.findall(r"(/(?:opt|usr/lib)/minidaq/\S+)", text))):
                stand_in = tmp / "bin" / pathlib.PurePosixPath(program).name
                stand_in.parent.mkdir(exist_ok=True)
                stand_in.write_text("#!/bin/sh\n")
                stand_in.chmod(0o755)
                text = text.replace(program, str(stand_in))
            copy = tmp / unit.name
            copy.write_text(text)
            copies.append(copy)
        r = subprocess.run([analyze, "verify", *map(str, copies)], capture_output=True, text=True)
        # Messages about units of the build machine itself are not ours.
        lines = [line for line in (r.stdout + r.stderr).splitlines() if str(tmp) in line or "minidaq" in line]
        return lines if r.returncode != 0 or lines else []


def main():
    root = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parent.parent
    errors = check_rules(root) + systemd_verify(root)
    for e in errors:
        print(f"check_units: {e}")
    if not errors:
        print("check_units: the units follow the rules")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
