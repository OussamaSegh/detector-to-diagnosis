# SPDX-License-Identifier: MIT
"""Exercise 19.1 solution: accounting for every packet of a damaged readout stream.

minidaq_send reports what it sent and what it did to the stream on purpose:

    sent = {"packets": P, "singles": S, "lost": L, "delayed": D, "duplicated": U, "both": B}

P packets were cut from the stream; L were never sent, D were sent late (after packets with
higher sequence numbers), U were sent twice. B of them were both delayed and duplicated: the
copy was sent on time and the original late. The server's link counters (`detector_counters` in
its status) say what arrived and what the sequence tracker made of it. A delayed packet is
either put back in order (packets_reordered) or arrives after its gap was given up: then its
sequence number was counted lost, and the packet itself is stale when it comes, like a duplicate.
A packet that was delayed and duplicated had its copy on time, so its late original is a
duplicate, never too late.

check() returns the names of the identities that do not hold, empty when every packet is
accounted for.
"""
from __future__ import annotations


# [snippet:check]
def check(sent, link):
    too_late = sent["delayed"] - sent["both"] - link["packets_reordered"]
    failed = []
    if not 0 <= link["packets_reordered"] <= sent["delayed"] - sent["both"]:
        failed.append("reordered")  # only a delayed packet can come back out of order
    if link["packets_delivered"] + link["packets_lost"] != sent["packets"]:
        failed.append("sequence")  # every sequence number is delivered or declared lost, once
    if link["packets_lost"] != sent["lost"] + too_late:
        failed.append("lost")
    if link["packets_stale"] != sent["duplicated"] + too_late:
        failed.append("stale")
    if link["packets_received"] != link["packets_delivered"] + link["packets_stale"]:
        failed.append("received")  # a packet that arrived was used or dropped as stale
    if link["datagrams"] != sent["packets"] - sent["lost"] + sent["duplicated"]:
        failed.append("datagrams")  # what was put on the wire arrived (loopback loses nothing)
    if link["packets_lost"] == 0 and link["words_delivered"] != sent["singles"]:
        failed.append("words")  # without a loss, every single arrived
    if link["sequence_resyncs"] != 0:
        failed.append("resyncs")  # one sender, one numbering: a resync means a count is wrong
    return failed
# [/snippet:check]
