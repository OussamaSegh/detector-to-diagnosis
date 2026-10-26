#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Chapter 23 measurements: where the packets of a burst go, by receive buffer size.

For each scenario: configure minidaq_server with a UDP source, start a run, send one simulated
second with minidaq_send over the loopback interface, wait until the pipeline is idle, and
record the sender's count and the receiver's counters: delivered, lost (sequence gaps), socket
drops (the kernel's count for MiniDAQ's socket) and the host's RcvbufErrors since the run began.
Every packet sent must be delivered or dropped at the socket; the loss that the sequence numbers
show is smaller when the last packets of the burst were the ones dropped.

    python3 measurements/ch23/drop_accounting.py build/release/minidaq/apps > measurements/ch23/drop_accounting.txt
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import time

APPS = sys.argv[1] if len(sys.argv) > 1 else "build/release/minidaq/apps"
CTL_PORT = 7712
UDP_PORT = 7703

KIB = 1024
SCENARIOS = [
    # name, sender options, receive buffer requested
    ("real time, 2 MBq, 64 KiB", ["--activity", "2e6", "--speed", "1"], 64 * KIB),
    ("burst, 5 MBq, 64 KiB", ["--activity", "5e6", "--speed", "0"], 64 * KIB),
    ("burst, 5 MBq, 256 KiB", ["--activity", "5e6", "--speed", "0"], 256 * KIB),
    ("burst, 5 MBq, 1 MiB", ["--activity", "5e6", "--speed", "0"], 1024 * KIB),
    ("burst, 5 MBq, 4 MiB", ["--activity", "5e6", "--speed", "0"], 4096 * KIB),
    ("burst, 5 MBq, 1024 words, 1 MiB", ["--activity", "5e6", "--speed", "0", "--words-per-packet", "1024"],
     1024 * KIB),
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
    print("| Scenario | Buffer granted | Sent | Delivered | Lost (gaps) | Socket drops | Host RcvbufErrors |"
          " Delivered + drops |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|")
    try:
        for name, send_args, buffer in SCENARIOS:
            settings = {"address": "127.0.0.1", "port": UDP_PORT, "receive_buffer_bytes": buffer}
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
            n_sent = int(re.search(r"sent (\d+) datagrams", sent).group(1))
            rate = re.search(r"in ([0-9.]+) s: (\d+) packets/s", sent)
            print(f"| {name} | {c['receive_buffer_bytes']:,} | {n_sent:,} | {c['packets_delivered']:,} |"
                  f" {c['packets_lost']:,} | {c['socket_drops']:,} | {c.get('host_udp_rcvbuf_errors', 'n/a'):,} |"
                  f" {c['packets_delivered'] + c['socket_drops']:,} |")
            print(f"<!-- {name}: sender {rate.group(2)} packets/s over {rate.group(1)} s; integrity "
                  f"{json.dumps(st['integrity']['losses'])} -->")
            sys.stdout.flush()
    finally:
        server.terminate()
        server.wait()


if __name__ == "__main__":
    main()
