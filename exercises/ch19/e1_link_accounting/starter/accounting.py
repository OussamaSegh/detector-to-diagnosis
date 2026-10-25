# SPDX-License-Identifier: MIT
"""Exercise 19.1 starter: accounting for every packet of a damaged readout stream.

minidaq_send reports what it sent and what it did to the stream on purpose:

    sent = {"packets": P, "singles": S, "lost": L, "delayed": D, "duplicated": U, "both": B}

P packets were cut from the stream; L were never sent, D were sent late (after packets with
higher sequence numbers), U were sent twice. B of them were both delayed and duplicated: the
copy was sent on time and the original late. The server's link counters (`detector_counters` in
its status) say what arrived and what the sequence tracker made of it.

check() returns the names of the identities that do not hold, empty when every packet is
accounted for. The README lists the names.
"""
from __future__ import annotations


def check(sent, link):
    failed = []
    if link["packets_delivered"] + link["packets_lost"] != sent["packets"]:
        failed.append("sequence")  # every sequence number is delivered or declared lost, once
    # TODO: reordered, lost, stale, received, datagrams, words, resyncs.
    return failed
