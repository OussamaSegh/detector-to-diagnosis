#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Chapter 25 measurements: minidaq_server under a service manager, and the signed updater.

1. Start to READY. The script plays systemd's part: it binds the notification socket, starts
   minidaq_server with NOTIFY_SOCKET and WATCHDOG_USEC set as systemd sets them, and times the
   READY=1 message from the start of the process.
2. The watchdog. With the unit's WatchdogSec=10s, the gaps between WATCHDOG=1 pings of a healthy
   server; then, with a simulated board whose register bus hangs on the first access, when the
   server says it is unhealthy, when its last ping came, and when systemd would act (the last
   ping plus WatchdogSec), all from the start of the process.
3. The updater. A bundle of the release build's programs, built and signed with
   tools/make_update.py and a key made for this run, installed into an empty root, installed
   again as a second version (a trial), rolled back, and confirmed; each command timed.
4. System calls. strace -f -c over a short synthetic run, and the calls it saw that the unit's
   SystemCallFilter (@system-service minus @privileged) would refuse.
5. Exposure. systemd-analyze security --offline=true for the shipped unit and for the same
   unit with only its first ten lines of [Service] (no hardening).

    python3 measurements/ch25/service_and_update.py build/release/minidaq/apps > measurements/ch25/service_and_update.txt
"""
import json
import os
import pathlib
import platform
import re
import shutil
import signal
import socket
import statistics
import subprocess
import sys
import tempfile
import time

APPS = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "build/release/minidaq/apps")
ROOT = pathlib.Path(__file__).resolve().parents[2]
REPEATS = 5
WATCHDOG_S = 10.0  # the unit's WatchdogSec


class Manager:
    """The service manager's end of the notification socket (sd_notify(3))."""

    def __init__(self):
        self.name = f"@minidaq-ch25-{os.getpid()}-{time.monotonic_ns()}"
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.sock.bind("\0" + self.name[1:])
        self.sock.settimeout(0.05)
        self.messages = []  # (seconds since the process started, text)

    def receive(self, start, seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            try:
                data = self.sock.recv(4096)
            except socket.timeout:
                continue
            self.messages.append((time.monotonic() - start, data.decode()))

    def close(self):
        self.sock.close()


def server(tmp, manager, hardware=None, extra=()):
    env = dict(os.environ, NOTIFY_SOCKET=manager.name, WATCHDOG_USEC=str(int(WATCHDOG_S * 1e6)),
               MINIDAQ_RUNTIME_DIR=str(tmp))
    args = [str(APPS / "minidaq_server"), "--port", "0", "--audit", str(tmp / "audit.jsonl"), *extra]
    if hardware:
        path = tmp / "hardware.json"
        path.write_text(json.dumps(hardware))
        args += ["--hardware", str(path)]
    start = time.monotonic()
    proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
    return proc, start


def stop(proc, sig=signal.SIGTERM):
    proc.send_signal(sig)
    proc.wait(30)


def ms(seconds):
    return f"{seconds * 1000:.0f}"


def start_to_ready():
    print("## 1. Start to READY\n")
    times = []
    for _ in range(REPEATS):
        with tempfile.TemporaryDirectory(prefix="minidaq-ch25-") as d:
            manager = Manager()
            proc, start = server(pathlib.Path(d), manager,
                                 {"schema_version": "1.1", "backend": "simulated", "boards": [{"slot": 0}]})
            while not any(m.startswith("READY=1") for _, m in manager.messages):
                manager.receive(start, 0.1)
                if time.monotonic() - start > 30:
                    raise SystemExit("no READY within 30 s")
            times.append(next(t for t, m in manager.messages if m.startswith("READY=1")))
            stop(proc)
            manager.close()
    print(f"{REPEATS} starts with one simulated board: READY after {ms(min(times))} / "
          f"{ms(statistics.median(times))} / {ms(max(times))} ms (min / median / max) from the start "
          f"of the process.\n")


def watchdog():
    print(f"## 2. The watchdog (WatchdogSec={WATCHDOG_S:.0f}s)\n")
    with tempfile.TemporaryDirectory(prefix="minidaq-ch25-") as d:
        manager = Manager()
        proc, start = server(pathlib.Path(d), manager,
                             {"schema_version": "1.1", "backend": "simulated", "boards": [{"slot": 0}]})
        manager.receive(start, 32)
        stop(proc)
        pings = [t for t, m in manager.messages if m == "WATCHDOG=1"]
        gaps = [b - a for a, b in zip(pings, pings[1:])]
        print(f"Healthy server, 32 s: {len(pings)} pings, gaps {min(gaps):.2f} / {max(gaps):.2f} s "
              f"(min / max); systemd asks for one within every {WATCHDOG_S:.0f} s.\n")
        manager.close()

    print("| Run | Unhealthy at, s | Last ping at, s | systemd acts at, s | Status the server sent |")
    print("|---|---:|---:|---:|---|")
    for run in range(1, 4):
        with tempfile.TemporaryDirectory(prefix="minidaq-ch25-") as d:
            manager = Manager()
            proc, start = server(pathlib.Path(d), manager, {
                "schema_version": "1.1", "backend": "simulated", "boards": [{"slot": 0, "fault": "hung_bus"}]},
                extra=("--crash-report", str(pathlib.Path(d) / "crash.txt")))
            manager.receive(start, 25)
            unhealthy = [(t, m) for t, m in manager.messages if m.startswith("STATUS=unhealthy")]
            pings = [t for t, m in manager.messages if m == "WATCHDOG=1"]
            last = max(pings) if pings else 0.0  # no ping at all: systemd counts from READY
            ready = next(t for t, m in manager.messages if m.startswith("READY=1"))
            acts = max(last, ready) + WATCHDOG_S
            text = unhealthy[0][1].removeprefix("STATUS=") if unhealthy else "none"
            when = f"{unhealthy[0][0]:.2f}" if unhealthy else "n/a"
            print(f"| {run} | {when} | {last:.2f} | {acts:.2f} | {text} |")
            stop(proc, signal.SIGABRT)  # what systemd sends then (WatchdogSignal=)
            manager.close()
    print()


def updater():
    print("## 3. The updater\n")
    update = APPS / "minidaq_update"
    with tempfile.TemporaryDirectory(prefix="minidaq-ch25-") as d:
        tmp = pathlib.Path(d)
        key = tmp / "release.key"  # made for this run only, deleted with it
        subprocess.run(["openssl", "genpkey", "-algorithm", "ed25519", "-out", key], check=True)
        (tmp / "keys").mkdir()
        subprocess.run(["openssl", "pkey", "-in", key, "-pubout", "-out", tmp / "keys" / "release.pem"], check=True)
        (tmp / "platform-id").write_text("minidaq-platform-1\n")
        (tmp / "opt").mkdir()

        def bundle(version):
            stage = tmp / f"stage-{version}"
            (stage / "bin").mkdir(parents=True)
            for name in ("minidaq_server", "minidaq_ctl", "minidaq_update"):
                shutil.copy2(APPS / name, stage / "bin" / name)
            out = tmp / f"bundle-{version}"
            subprocess.run([sys.executable, ROOT / "tools" / "make_update.py", "--stage", stage, "--version", version,
                            "--commit", "0000000", "--platform", "minidaq-platform-1", "--key", key, "--out", out],
                           check=True, capture_output=True, env=dict(os.environ, SOURCE_DATE_EPOCH="1700000000"))
            return out

        def timed(*args):
            t = time.monotonic()
            r = subprocess.run([update, *args, "--root", tmp / "opt"], capture_output=True, text=True)
            return time.monotonic() - t, r.returncode

        install = ("--keys", tmp / "keys", "--platform-file", tmp / "platform-id")
        first, second = bundle("0.5.0"), bundle("0.5.1")
        size = sum(f.stat().st_size for f in first.iterdir())
        unpacked = sum(f.stat().st_size for f in (tmp / "stage-0.5.0" / "bin").iterdir())
        print(f"Bundle: {size / 1e6:.1f} MB ({unpacked / 1e6:.1f} MB unpacked, three programs).\n")
        print("| Command | Time, ms | Exit status |")
        print("|---|---:|---:|")
        for label, args in (("install 0.5.0 into an empty root", ("install", first, *install)),
                            ("install 0.5.1 as a trial", ("install", second, *install)),
                            ("rollback to 0.5.0", ("rollback",)),
                            ("rollback again (nothing to do)", ("rollback",)),
                            ("install 0.5.1 again", ("install", second, *install)),
                            ("confirm", ("confirm",))):
            t, rc = timed(*args)
            print(f"| {label} | {ms(t)} | {rc} |")
        print()


def syscalls():
    print("## 4. System calls of a run against the unit's filter\n")
    if not shutil.which("strace") or not shutil.which("systemd-analyze"):
        print("strace or systemd-analyze is not installed: skipped.\n")
        return
    def group(name, seen=None):
        """The system calls of a systemd syscall group, with the groups it includes expanded."""
        seen = seen if seen is not None else set()
        out = subprocess.run(["systemd-analyze", "--no-pager", "syscall-filter", name], capture_output=True,
                             text=True).stdout
        calls = set()
        for line in out.splitlines()[1:]:
            word = re.sub(r"\x1b\[[0-9;]*m", "", line).strip()
            if word.startswith("@") and word not in seen:
                seen.add(word)
                calls |= group(word, seen)
            elif re.fullmatch(r"[a-z_0-9]+", word):
                calls.add(word)
        return calls

    allowed, privileged = group("@system-service"), group("@privileged")
    with tempfile.TemporaryDirectory(prefix="minidaq-ch25-") as d:
        tmp = pathlib.Path(d)
        log = tmp / "strace.txt"
        manager = Manager()
        env = dict(os.environ, MINIDAQ_RUNTIME_DIR=str(tmp), NOTIFY_SOCKET=manager.name)
        proc = subprocess.Popen(["strace", "-f", "-c", "-o", str(log), str(APPS / "minidaq_server"), "--port", "0",
                                 "--audit", str(tmp / "audit.jsonl")],
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
        port, end = None, time.monotonic() + 30
        while port is None:
            if time.monotonic() > end or proc.poll() is not None:
                raise SystemExit("minidaq_server under strace did not report its port")
            m = re.search(r"control API on [\d.]+:(\d+) \(", proc.stdout.readline())
            port = int(m.group(1)) if m else None
        ctl = [str(APPS / "minidaq_ctl"), "--port", str(port)]
        cenv = dict(os.environ, MINIDAQ_RUNTIME_DIR=str(tmp))
        for cmd in (["configure", str(ROOT / "minidaq/configs/short-run.json")], ["start"],
                    ["wait", "configured", "30"], ["status"]):
            subprocess.run(ctl + cmd, capture_output=True, env=cenv, check=False)
        # The server, not strace, gets the SIGTERM a stop sends; its output is drained meanwhile.
        child = subprocess.run(["pgrep", "-P", str(proc.pid)], capture_output=True, text=True).stdout.split()
        os.kill(int(child[0]), signal.SIGTERM)
        proc.communicate(timeout=30)
        manager.close()
        seen = set()
        for line in log.read_text().splitlines():
            parts = line.split()
            if parts and re.fullmatch(r"[a-z_0-9]+", parts[-1]) and parts[-1] not in ("syscall", "total"):
                seen.add(parts[-1])
    refused = sorted(s for s in seen if s not in allowed or s in privileged)
    print(f"A two-second synthetic run with configure, start, wait and status made {len(seen)} different "
          f"system calls: {', '.join(sorted(seen))}.\n")
    print(f"Refused by @system-service minus @privileged: {', '.join(refused) if refused else 'none'}.\n")


def exposure():
    print("## 5. systemd-analyze security --offline=true\n")
    if not shutil.which("systemd-analyze"):
        print("systemd-analyze is not installed: skipped.\n")
        return
    unit = (ROOT / "packaging/systemd/minidaq.service").read_text()
    head, service = unit.split("[Service]\n")
    service, install = service.split("[Install]\n")
    plain = head + "[Service]\n" + "\n".join(
        line for line in service.splitlines()
        if line.split("=")[0] in ("Type", "NotifyAccess", "WatchdogSec", "Restart", "RestartSec", "ExecStart")
        or line.startswith("    ")) + "\n[Install]\n" + install
    with tempfile.TemporaryDirectory(prefix="minidaq-ch25-") as d:
        rows = []
        for label, text in (("without hardening", plain), ("as shipped", unit)):
            path = pathlib.Path(d) / "minidaq.service"
            path.write_text(text)
            out = subprocess.run(["systemd-analyze", "security", "--offline=true", "--no-pager", str(path)],
                                 capture_output=True, text=True)
            m = re.search(r"Overall exposure level for \S+: ([\d.]+) (\S+)", out.stdout + out.stderr)
            rows.append((label, m.group(1) if m else "?", m.group(2) if m else "?"))
    print("| Unit | Exposure (0 to 10, lower is better) | Rating |")
    print("|---|---:|---|")
    for row in rows:
        print("| " + " | ".join(row) + " |")
    print()


def main():
    version = subprocess.run(["systemd-analyze", "--version"], capture_output=True, text=True).stdout.split("\n")[0]
    print(f"Machine: {platform.machine()}, {os.cpu_count()} CPUs, Linux {platform.release()}; "
          f"{version or 'no systemd-analyze'}. Programs: {APPS}.\n")
    start_to_ready()
    watchdog()
    updater()
    syscalls()
    exposure()


if __name__ == "__main__":
    main()
