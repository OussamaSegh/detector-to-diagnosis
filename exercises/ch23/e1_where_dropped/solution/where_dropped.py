# SPDX-License-Identifier: MIT
"""Exercise 23.1: where did the datagrams go? A drop report from two readings of the host's
counters, taken before and after a run."""

LAYERS = ("nic", "backlog", "udp_buffers", "socket")


def parse_snmp_udp(text):
    """The Udp counters of /proc/net/snmp as a dict of name to value, found by column name."""
    names = None
    for line in text.splitlines():
        if not line.startswith("Udp:"):
            continue
        fields = line.split()[1:]
        if names is None:
            names = fields
            continue
        if len(fields) != len(names):
            raise ValueError("the Udp lines have different lengths")
        return {n: int(v) for n, v in zip(names, fields)}
    raise ValueError("no Udp lines")


def parse_softnet(text):
    """/proc/net/softnet_stat summed over the CPUs: processed, dropped, time_squeeze."""
    total = {"processed": 0, "dropped": 0, "time_squeeze": 0}
    cpus = 0
    for line in text.splitlines():
        f = line.split()
        if not f:
            continue
        if len(f) < 3:
            raise ValueError(f"short softnet line: {line!r}")
        for key, value in zip(("processed", "dropped", "time_squeeze"), f[:3]):
            total[key] += int(value, 16)
        cpus += 1
    if cpus == 0:
        raise ValueError("no CPUs")
    return total


def socket_drops(text, inode):
    """The drops column of the /proc/net/udp line of the socket with this inode, or None."""
    for line in text.splitlines():
        f = line.split()
        if len(f) >= 13 and f[0] != "sl" and f[9] == str(inode):
            return int(f[12])
    return None


def _wrap32(now, before):
    return (now - before) % (1 << 32)


def report(before, after, inode):
    """Drops between two snapshots, by layer in the order a datagram meets them.

    A snapshot is a dict with the texts of "snmp", "softnet" and "udp" and, optionally, "nic": a
    dict of the interface's statistics (rx_missed_errors, rx_fifo_errors, rx_dropped). The result
    has one entry per layer (None when a snapshot lacks it), "other_sockets" (buffer drops of the
    host's other sockets) and "verdict": the first layer with drops, or "none".
    """
    out = {}
    if "nic" in before and "nic" in after:
        out["nic"] = sum(after["nic"][k] - before["nic"][k]
                         for k in ("rx_missed_errors", "rx_fifo_errors", "rx_dropped"))
    else:
        out["nic"] = None
    sb, sa = parse_softnet(before["softnet"]), parse_softnet(after["softnet"])
    out["backlog"] = _wrap32(sa["dropped"], sb["dropped"])
    ub, ua = parse_snmp_udp(before["snmp"]), parse_snmp_udp(after["snmp"])
    out["udp_buffers"] = ua["RcvbufErrors"] - ub["RcvbufErrors"]
    db, da = socket_drops(before["udp"], inode), socket_drops(after["udp"], inode)
    out["socket"] = None if db is None or da is None else _wrap32(da, db)
    out["other_sockets"] = None if out["socket"] is None else max(0, out["udp_buffers"] - out["socket"])
    out["verdict"] = next((layer for layer in LAYERS if out[layer]), "none")
    return out
