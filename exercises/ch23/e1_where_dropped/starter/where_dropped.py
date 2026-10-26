# SPDX-License-Identifier: MIT
"""Exercise 23.1: where did the datagrams go? A drop report from two readings of the host's
counters, taken before and after a run."""

LAYERS = ("nic", "backlog", "udp_buffers", "socket")


def parse_snmp_udp(text):
    """The Udp counters of /proc/net/snmp as a dict of name to value, found by column name."""
    # TODO: the first "Udp:" line has the names, the second the values. Raise ValueError when
    # there are no Udp lines or the two lines differ in length.
    raise NotImplementedError


def parse_softnet(text):
    """/proc/net/softnet_stat summed over the CPUs: processed, dropped, time_squeeze."""
    # TODO: one line per CPU, hexadecimal; the first three columns. Raise ValueError for a short
    # line or an empty file.
    raise NotImplementedError


def socket_drops(text, inode):
    """The drops column of the /proc/net/udp line of the socket with this inode, or None."""
    # TODO: the inode is the tenth field, the drops the thirteenth; skip the header line.
    raise NotImplementedError


def report(before, after, inode):
    """Drops between two snapshots, by layer in the order a datagram meets them.

    A snapshot is a dict with the texts of "snmp", "softnet" and "udp" and, optionally, "nic": a
    dict of the interface's statistics (rx_missed_errors, rx_fifo_errors, rx_dropped). The result
    has one entry per layer (None when a snapshot lacks it), "other_sockets" (buffer drops of the
    host's other sockets) and "verdict": the first layer with drops, or "none".
    """
    # TODO: subtract the readings; the softnet counters and the socket's drops are 32-bit and
    # wrap.
    raise NotImplementedError
