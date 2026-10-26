#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Chapter 23 measurements: how many datagrams a UDP receive buffer holds.

For each datagram size and requested buffer, send 5,000 datagrams over the loopback interface to a
socket that nobody reads, then count how many it queued. The kernel charges each datagram its
"truesize" (the payload's allocation plus the socket buffer's own structure) against twice the
granted SO_RCVBUF, so the bytes charged per datagram are 2 x granted / queued.

    python3 measurements/ch23/buffer_footprint.py > measurements/ch23/buffer_footprint.txt
"""
import os
import platform
import socket

print(f"# kernel {platform.release()}, loopback, net.core.rmem_max "
      f"{open('/proc/sys/net/core/rmem_max').read().strip()}")
print("| Datagram | Buffer granted | Datagrams queued | Bytes charged per datagram |")
print("|---:|---:|---:|---:|")
for size in (1472, 8208):
    for requested in (64 << 10, 256 << 10, 1 << 20, 4 << 20):
        rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        rx.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, requested)
        rx.bind(("127.0.0.1", 0))
        granted = rx.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF) // 2
        tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        payload = os.urandom(size)
        for _ in range(5000):
            tx.sendto(payload, rx.getsockname())
        rx.setblocking(False)
        queued = 0
        try:
            while True:
                rx.recv(65536)
                queued += 1
        except BlockingIOError:
            pass
        print(f"| {size:,} B | {granted:,} B | {queued:,} | {2 * granted / queued:,.0f} B |")
        rx.close()
        tx.close()
