#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Chapter 9 measurements: minidaq_send -> UDP loopback -> minidaq_server.

For each scenario: configure the server with a UDP source, start a run, send
one simulated second with minidaq_send, wait until the pipeline is idle, and
record the sender's report and the server's link and stage counters.

    python3 measurements/ch09/udp_runs.py build/release/minidaq/apps > measurements/ch09/udp_runs.txt
"""
import json
import os
import subprocess
import sys
import tempfile
import time

APPS = sys.argv[1] if len(sys.argv) > 1 else "build/release/minidaq/apps"
CTL_PORT = 7711
UDP_PORT = 7702

SCENARIOS = [
    # name, sender options, udp settings
    ("real time, clean link", ["--activity", "2e6", "--speed", "1"], {}),
    ("real time, injected faults", ["--activity", "2e6", "--speed", "1", "--loss", "0.001", "--reorder", "0.001",
                                    "--duplicate", "0.0005"], {}),
    ("same faults, 5 ms hold", ["--activity", "2e6", "--speed", "1", "--loss", "0.001", "--reorder", "0.001",
                                "--duplicate", "0.0005"], {"max_hold_us": 5000}),
    ("as fast as possible, 4 MiB buffer", ["--activity", "5e6", "--speed", "0"], {}),
    ("as fast as possible, 64 KiB buffer", ["--activity", "5e6", "--speed", "0"], {"receive_buffer_bytes": 65536}),
    ("as fast as possible, 32 words/packet", ["--activity", "5e6", "--speed", "0", "--words-per-packet", "32"], {}),
]


def ctl(*args):
    out = subprocess.run([f"{APPS}/minidaq_ctl", "--port", str(CTL_PORT), *args], capture_output=True, text=True,
                         check=False)
    reply = json.loads(out.stdout)
    return reply.get("status", reply)


def main():
    server = subprocess.Popen([f"{APPS}/minidaq_server", "--port", str(CTL_PORT)], stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL)
    time.sleep(0.5)
    try:
        for name, send_args, udp in SCENARIOS:
            settings = {"address": "127.0.0.1", "port": UDP_PORT, "receive_buffer_bytes": 8 << 20, **udp}
            cfg = {"schema_version": "1.1", "description": name, "source": {"type": "udp", "udp": settings}}
            with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
                json.dump(cfg, f)
            r = ctl("configure", f.name)
            os.unlink(f.name)
            if not r.get("ok", True):
                sys.exit(f"configure failed: {r}")
            r = ctl("start")
            if not r.get("ok", True):
                sys.exit(f"start failed: {r}")
            sent = subprocess.run([f"{APPS}/minidaq_send", "--port", str(UDP_PORT), "--seconds", "1", "--seed", "4",
                                   *send_args], capture_output=True, text=True, check=True).stdout
            # Wait until the pipeline has taken everything the socket holds.
            last = -1
            for _ in range(100):
                time.sleep(0.1)
                st = ctl("status")
                words = st["detector_counters"]["words_delivered"]
                if words == last:
                    break
                last = words
            time.sleep(0.2)  # let gaps expire
            st = ctl("status")
            ctl("stop")
            subprocess.run([f"{APPS}/minidaq_ctl", "--port", str(CTL_PORT), "wait", "configured", "5"],
                           capture_output=True, check=True)
            c = st["detector_counters"]
            stages = {s["name"]: s for s in st["stages"]}
            print(f"== {name}")
            print("   sender: " + " | ".join(line.strip() for line in sent.strip().splitlines()))
            print(f"   receiver: {st['detector']}")
            print(f"   datagrams {c['datagrams']}, delivered {c['packets_delivered']}, lost {c['packets_lost']}, "
                  f"reordered {c['packets_reordered']}, stale {c['packets_stale']}, words {c['words_delivered']}")
            print(f"   decode out {stages['decode']['out']}, late singles {st['late_singles']}, fault {st['fault']}")
            sys.stdout.flush()
    finally:
        server.terminate()
        server.wait()


if __name__ == "__main__":
    main()
