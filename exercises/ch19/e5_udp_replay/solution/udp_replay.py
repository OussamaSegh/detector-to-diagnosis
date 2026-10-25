#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise 19.5 solution: record a readout link's datagrams, and replay them.

A recording of what a readout board sent turns a field problem into a test: the same datagrams,
in the same order and with the same gaps, can be sent to the DAQ again, on a developer's machine,
as often as needed, and every replay must give the same result. The capture format is MDQ-CAP1:

    magic   8 bytes   b"MDQCAP1\\n"
    record  12 bytes  <QI: arrival time in ns since the first datagram, payload length
            n bytes   the payload

    udp_replay.py record --port PORT OUT [--idle 1.0] [--timeout 10]
    udp_replay.py replay CAPTURE --port PORT [--host 127.0.0.1] [--speed 1.0]
"""
from __future__ import annotations

import argparse
import socket
import struct
import sys
import time

MAGIC = b"MDQCAP1\n"
RECORD = struct.Struct("<QI")
MAX_DATAGRAM = 65535


def record(sock, path, idle_s=1.0, timeout_s=10.0):
    """Writes the datagrams that arrive on the bound socket `sock` to `path`, until none has
    arrived for idle_s after the first. Fails if nothing arrives within timeout_s. Returns the
    number of datagrams."""
    sock.settimeout(timeout_s)
    count = 0
    first = None
    with open(path, "wb") as f:
        f.write(MAGIC)
        while True:
            try:
                data = sock.recv(MAX_DATAGRAM)
            except socket.timeout:
                if first is None:
                    raise TimeoutError(f"no datagram within {timeout_s} s") from None
                return count
            now = time.monotonic_ns()
            if first is None:
                first = now
                sock.settimeout(idle_s)
            f.write(RECORD.pack(now - first, len(data)))
            f.write(data)
            count += 1


def read_capture(path):
    """The (offset_ns, payload) records of a capture, in order. Raises ValueError on a file that
    is not a complete MDQ-CAP1 capture."""
    with open(path, "rb") as f:
        blob = f.read()
    if blob[:len(MAGIC)] != MAGIC:
        raise ValueError(f"{path}: not an MDQ-CAP1 capture")
    out, pos, last = [], len(MAGIC), 0
    while pos < len(blob):
        if pos + RECORD.size > len(blob):
            raise ValueError(f"{path}: truncated record header at byte {pos}")
        offset, length = RECORD.unpack_from(blob, pos)
        pos += RECORD.size
        if pos + length > len(blob):
            raise ValueError(f"{path}: truncated payload at byte {pos}")
        if offset < last:
            raise ValueError(f"{path}: time goes backward at byte {pos - RECORD.size}")
        out.append((offset, blob[pos:pos + length]))
        pos += length
        last = offset
    return out


# [snippet:replay]
def replay(path, host, port, speed=1.0):
    """Sends the capture's datagrams to host:port in order. speed 1 keeps the recorded gaps,
    speed 2 halves them, speed 0 sends as fast as the socket takes them. Returns the count."""
    records = read_capture(path)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        start = time.monotonic_ns()
        for offset, payload in records:
            if speed > 0:
                delay = (start + offset / speed - time.monotonic_ns()) / 1e9
                if delay > 0:
                    time.sleep(delay)  # sleep: device (the recorded schedule of the link)
            sock.sendto(payload, (host, port))
    return len(records)
# [/snippet:replay]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("record")
    r.add_argument("--port", type=int, required=True)
    r.add_argument("--bind", default="127.0.0.1")
    r.add_argument("--idle", type=float, default=1.0)
    r.add_argument("--timeout", type=float, default=10.0)
    r.add_argument("out")
    p = sub.add_parser("replay")
    p.add_argument("capture")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, required=True)
    p.add_argument("--speed", type=float, default=1.0)
    args = ap.parse_args(argv)
    if args.cmd == "record":
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 8 << 20)
            sock.bind((args.bind, args.port))
            n = record(sock, args.out, args.idle, args.timeout)
    else:
        n = replay(args.capture, args.host, args.port, args.speed)
    print(f"{n} datagrams")
    return 0


if __name__ == "__main__":
    sys.exit(main())
