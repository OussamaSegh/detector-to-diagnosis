#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Soak test of minidaq_server (Chapter 19, SRS-SYS-003).

Runs one acquisition of the synthetic source at a fixed rate for a long time and samples, every
INTERVAL seconds, the server's resident memory (VmRSS from /proc) and its status: singles in,
drops, losses, faults and latency. A soak test looks for what only time shows: a slow leak, a
counter that wraps, a queue that grows, a latency that drifts.

    tools/soak.py build/release/minidaq/apps OUT [--minutes 30] [--rate 1e6] [--interval 10]

Writes OUT/samples.csv and OUT/summary.txt, and exits with 1 if the run had a loss or a fault,
or if its memory grew faster than --max-growth MiB per hour after the warm-up (--warmup minutes,
default 10). The growth is the slope of a least-squares line through the samples after the
warm-up, with its standard error, so a single page faulted in late does not count as a leak.

The latency is reported, not judged here: the summary counts the intervals whose 99th percentile
is above --latency-limit ms (default 10, SRS-PERF-022), and tools/acceptance.py judges the count
(ACC-04). Each sample also records the share of the machine's CPU time that the hypervisor took
for other guests in the interval (steal, from /proc/stat), so that a latency peak can be told
from a machine that was not running the server (CR-0025).

The finer measure of MDQ-PR-064: a second thread samples every second the machine's steal time
and, for each of the server's threads, the time it waited on a run queue (the second field of
/proc/PID/task/TID/schedstat). Each interval records the largest one-second steal and the largest
one-second run-queue wait of any thread, with that thread's name: a 30 ms stall that a 10 s
average over four CPUs hides is a 30 ms wait in one second of one thread.
"""
import argparse
import csv
import math
import os
import pathlib
import sys
import tempfile
import threading
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "minidaq/tests/system"))
import systest  # noqa: E402  (the system tests' helpers: Server, Ctl)


def rss_kib(pid):
    for line in pathlib.Path(f"/proc/{pid}/status").read_text().splitlines():
        if line.startswith("VmRSS:"):
            return int(line.split()[1])
    raise RuntimeError("no VmRSS")


# [snippet:slope]
def slope(xs, ys):
    """Least-squares slope of ys over xs, and its standard error."""
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    residual = sum((y - my - b * (x - mx)) ** 2 for x, y in zip(xs, ys))
    se = math.sqrt(residual / (n - 2) / sxx) if n > 2 else float("inf")
    return b, se
# [/snippet:slope]


def cpu_ticks():
    """The machine's CPU time so far, in ticks: (total, steal), from the first line of /proc/stat."""
    fields = [int(x) for x in pathlib.Path("/proc/stat").read_text().split("\n", 1)[0].split()[1:]]
    # user nice system idle iowait irq softirq steal [guest guest_nice]: guest time is already
    # counted in user and nice, so the total is the first eight fields.
    return sum(fields[:8]), (fields[7] if len(fields) > 7 else 0)


def steal_pct(before, after):
    total, steal = after[0] - before[0], after[1] - before[1]
    return round(100.0 * steal / total, 2) if total > 0 else 0.0


def thread_waits(pid):
    """Each thread's run-queue wait so far, in ns, and its name, from /proc/PID/task/*/schedstat."""
    out = {}
    for task in pathlib.Path(f"/proc/{pid}/task").iterdir():
        try:
            wait = int((task / "schedstat").read_text().split()[1])
            name = (task / "comm").read_text().strip()
        except (OSError, IndexError, ValueError):
            continue  # the thread ended between the listing and the read
        out[task.name] = (wait, name)
    return out


class PerSecond(threading.Thread):
    """Samples every second the steal time and the server's threads' run-queue waits (MDQ-PR-064),
    and keeps, until take() is called, the largest one-second value of each."""

    def __init__(self, pid):
        super().__init__(daemon=True)
        self.pid, self.lock, self.done = pid, threading.Lock(), threading.Event()
        self.steal_max, self.wait_max_ms, self.wait_thread = 0.0, 0.0, ""

    def run(self):
        ticks, waits = cpu_ticks(), thread_waits(self.pid)
        while not self.done.wait(1.0):
            try:
                now_ticks, now_waits = cpu_ticks(), thread_waits(self.pid)
            except OSError:
                return  # the server has ended
            steal = steal_pct(ticks, now_ticks)
            worst = max(((w - waits[t][0], n) for t, (w, n) in now_waits.items() if t in waits),
                        default=(0, ""))
            with self.lock:
                self.steal_max = max(self.steal_max, steal)
                if worst[0] / 1e6 > self.wait_max_ms:
                    self.wait_max_ms, self.wait_thread = worst[0] / 1e6, worst[1]
            ticks, waits = now_ticks, now_waits

    def take(self):
        with self.lock:
            out = (round(self.steal_max, 2), round(self.wait_max_ms, 3), self.wait_thread)
            self.steal_max, self.wait_max_ms, self.wait_thread = 0.0, 0.0, ""
        return out


def losses(status):
    stages = sum(s["dropped"] for s in status["stages"])
    return stages + status["late_singles"] + status["sink_counters"].get("blocks_dropped", 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("apps", type=pathlib.Path)
    ap.add_argument("out", type=pathlib.Path)
    ap.add_argument("--minutes", type=float, default=30.0)
    ap.add_argument("--rate", type=float, default=1e6)
    ap.add_argument("--interval", type=float, default=10.0)
    ap.add_argument("--warmup", type=float, default=10.0, help="minutes before the memory trend counts")
    ap.add_argument("--max-growth", type=float, default=1.0, help="MiB per hour")
    ap.add_argument("--latency-limit", type=float, default=10.0,
                    help="the 99th percentile an interval may reach, in ms (reported, not judged)")
    args = ap.parse_args()
    systest.APPS = args.apps.resolve()
    args.out.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="minidaq-soak-") as tmp:
        cfg = systest.write_json(pathlib.Path(tmp) / "soak.json", {
            "schema_version": "2.0", "description": "soak test",
            "source": {"type": "synthetic", "rate_hz": args.rate, "seed": 1, "stop_after_s": 0},
            "output": {"type": "none"}})
        rows = []
        with systest.Server(tmp) as server:
            ctl = systest.Ctl(server)
            ctl.ok("configure", str(cfg))
            ctl.ok("start")
            t0 = time.monotonic()
            ticks = cpu_ticks()
            per_second = PerSecond(server.proc.pid)
            per_second.start()
            end = t0 + args.minutes * 60
            while True:
                now = time.monotonic()
                st = ctl.status()
                # The recent window is missing until the run has completed its first interval.
                e2e = (st.get("recent_latency_ns") or {}).get("end_to_end") or {"p99": 0, "max": 0}
                ticks, before = cpu_ticks(), ticks
                steal_1s, wait_1s, wait_thread = per_second.take()
                rows.append({"t_s": round(now - t0, 1), "rss_kib": rss_kib(server.proc.pid),
                             "singles_in": st["sorter_counters"]["singles_in"], "losses": losses(st),
                             "state": st["state"], "fault": st["fault"] or "",
                             "p99_ms": round(e2e["p99"] / 1e6, 3), "max_ms": round(e2e["max"] / 1e6, 3),
                             "steal_pct": steal_pct(before, ticks), "steal_1s_max_pct": steal_1s,
                             "runq_wait_1s_max_ms": wait_1s, "runq_wait_thread": wait_thread})
                if st["state"] != "running" or now >= end:
                    break
                time.sleep(max(0.0, args.interval - (time.monotonic() - now)))  # sleep: device
            per_second.done.set()
            per_second.join()
            ctl.ok("stop")
            systest.eventually(lambda: ctl.status()["state"] == "configured", 60, "the end of the run")
            final = ctl.status()
            code = server.stop()

    with (args.out / "samples.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    after = [r for r in rows if r["t_s"] >= args.warmup * 60]
    problems = []
    if len(after) >= 3:
        b, se = slope([r["t_s"] / 3600 for r in after], [r["rss_kib"] / 1024 for r in after])
        growth = f"{b:+.3f} MiB/h (standard error {se:.3f}) over {len(after)} samples after {args.warmup:g} min"
        if b - 2 * se > args.max_growth:
            problems.append(f"memory grows {b:.3f} MiB/h, more than {args.max_growth} MiB/h")
    else:
        growth = "not measured: the run was shorter than the warm-up"
    lost = losses(final)
    if lost:
        problems.append(f"{lost} singles lost")
    if final["fault"] or any(r["fault"] for r in rows):
        problems.append(f"fault: {final['fault']}")
    if not final["integrity"]["complete"]:
        problems.append(f"incomplete: {final['integrity']['losses']}")
    if code != 0:
        problems.append(f"server exit status {code}")
    elapsed = rows[-1]["t_s"]
    # The first sample comes before the first interval has ended: it has no latency window.
    intervals = [r for r in rows if r["t_s"] >= args.interval]
    above = [r for r in intervals if r["p99_ms"] > args.latency_limit]
    steal = [r["steal_pct"] for r in intervals] or [0.0]
    singles = final["sorter_counters"]["singles_in"]
    lines = [
        f"soak: {args.rate:g} singles/s for {elapsed / 60:.1f} min, {len(rows)} samples every {args.interval:g} s",
        f"machine: {os.uname().nodename}, {os.cpu_count()} CPUs; programs {args.apps}",
        f"singles in: {singles} ({singles / elapsed:.0f}/s); losses {lost}; fault {final['fault']}; "
        f"complete {final['integrity']['complete']}",
        f"resident memory: first {rows[0]['rss_kib'] / 1024:.1f} MiB, last {rows[-1]['rss_kib'] / 1024:.1f} MiB, "
        f"max {max(r['rss_kib'] for r in rows) / 1024:.1f} MiB; trend {growth}",
        f"end-to-end latency over each interval: p99 max {max(r['p99_ms'] for r in rows):.2f} ms, "
        f"max {max(r['max_ms'] for r in rows):.2f} ms",
        f"intervals with p99 above {args.latency_limit:g} ms: {len(above)} of {len(intervals)}"
        + (" (at " + ", ".join(f"{r['t_s']:g} s" for r in above) + ")" if above else ""),
        f"steal time over each interval: max {max(steal):.2f}%, mean {sum(steal) / len(steal):.2f}%"
        + (", in the intervals above the limit: " + ", ".join(f"{r['steal_pct']:g}%" for r in above)
           if above else ""),
        f"per second (MDQ-PR-064): steal max {max(r['steal_1s_max_pct'] for r in intervals or rows):.2f}%, "
        f"run-queue wait of one thread max {max(r['runq_wait_1s_max_ms'] for r in intervals or rows):.2f} ms"
        + (", in the intervals above the limit: " + ", ".join(
            f"{r['runq_wait_1s_max_ms']:g} ms ({r['runq_wait_thread']}), steal {r['steal_1s_max_pct']:g}%"
            for r in above) if above else ""),
        "result: " + ("PASS" if not problems else "FAIL: " + "; ".join(problems)),
    ]
    (args.out / "summary.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
