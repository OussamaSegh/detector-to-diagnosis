#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Chapter 24 measurements: how long a stop takes when it waits for the boards, and what a run
record says when a board's FIFO overflowed or its link stalled.

For each scenario: start minidaq_server with a hardware description of two simulated boards,
wait until both are ready, configure a synthetic source without an end, start, run for a while,
read what the second board's output FIFO holds, stop, and time the stop until the service is
back in the state "configured", from the server's audit trail (millisecond timestamps). The first board always has a link much
faster than its events; the second board's rates are the scenario's. The slow control's period
is 100 ms, its default.

    python3 measurements/ch24/run_sequence.py build/release/minidaq/apps > measurements/ch24/run_sequence.txt
"""
import datetime
import json
import os
import subprocess
import sys
import tempfile
import time

APPS = sys.argv[1] if len(sys.argv) > 1 else "build/release/minidaq/apps"
CTL_PORT = 7714
REPEATS = 5

SCENARIOS = [
    # name, second board's settings, run seconds, drain timeout ms; None: no hardware at all
    ("no hardware", None, 1.0, 2000),
    ("link 50 times faster than the events", {"fill_words_per_s": 20000, "drain_words_per_s": 1e6}, 1.0, 2000),
    ("backlog of 2,000 words", {"fill_words_per_s": 27000, "drain_words_per_s": 25000}, 1.0, 2000),
    ("FIFO overflows", {"fill_words_per_s": 50000, "drain_words_per_s": 25000}, 1.0, 2000),
    ("link stalled", {"fault": "stalled_link"}, 1.0, 500),
]


def ctl(*args):
    out = subprocess.run([f"{APPS}/minidaq_ctl", "--port", str(CTL_PORT), *args], capture_output=True, text=True,
                         check=False)
    try:
        reply = json.loads(out.stdout)
    except json.JSONDecodeError:
        return {}  # the server is not listening yet
    return reply.get("status", reply)


def wait_until(predicate, seconds):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if predicate():
            return True
        time.sleep(0.02)  # polling a server in another process
    return False


def stop_ms(audit_path):
    """From the last stop command to the next transition into "configured", in the audit trail."""
    def t(r):
        return datetime.datetime.fromisoformat(r["time"].replace("Z", "+00:00"))
    records = [json.loads(line) for line in open(audit_path) if line.strip()]
    stop = max(i for i, r in enumerate(records) if r["action"] == "stop" and r["ok"])
    end = next(r for r in records[stop:] if r["action"] == "transition" and "-> configured" in r["detail"])
    return (t(end) - t(records[stop])).total_seconds() * 1000


def run(name, board, run_s, drain_ms):
    audit = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False)
    audit.close()
    files = [audit.name]
    args = [f"{APPS}/minidaq_server", "--port", str(CTL_PORT), "--audit", audit.name]
    if board is not None:
        hw = {"schema_version": "1.1", "backend": "simulated", "bias": {"ramp_v_per_s": 100.0},
              "run": {"drain_timeout_ms": drain_ms},
              "boards": [{"slot": 0}, dict({"slot": 1}, **board)]}
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(hw, f)
        files.append(f.name)
        args += ["--hardware", f.name]
    cfg = {"schema_version": "1.1", "description": name,
           "source": {"type": "synthetic", "rate_hz": 1e6, "seed": 1}}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(cfg, f)
    files.append(f.name)
    server = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    results = []
    try:
        if not wait_until(lambda: ctl("status").get("state") is not None, 5):
            sys.exit("the server did not answer")
        if board is not None and not wait_until(lambda: ctl("status")["hardware"]["ready"], 10):
            sys.exit(f"{name}: the boards did not become ready")
        for _ in range(REPEATS):
            if not ctl("configure", files[-1]).get("ok", True):
                sys.exit(f"{name}: configure failed")
            if not ctl("start").get("ok", True):
                sys.exit(f"{name}: start failed")
            time.sleep(run_s)  # the run itself
            before = ctl("status")
            ctl("stop")
            subprocess.run([f"{APPS}/minidaq_ctl", "--port", str(CTL_PORT), "wait", "configured", "10"],
                           capture_output=True, check=True)
            took_ms = stop_ms(audit.name)
            after = ctl("status")
            hw = after["hardware"]
            results.append({
                "stop_ms": took_ms,
                "fifo_at_stop": before["hardware"]["boards"][1]["fifo_words"] if hw else None,
                "overflows": hw["boards"][1]["fifo_overflows"] if hw else None,
                "drain_timeouts": hw["drain_timeouts"] if hw else None,
                "complete": after["integrity"]["complete"],
                "losses": [l["counter"] for l in after["integrity"]["losses"]],
            })
    finally:
        server.terminate()
        server.wait()
        for f in files:
            os.unlink(f)
    return results


def main():
    print(f"Each scenario: {REPEATS} runs of 1 s; the slow control's period is 100 ms.")
    print()
    print("| Scenario | Stop to configured, ms (min / median / max) | Board 1 FIFO at stop, words |"
          " FIFO overflows | Drain timeouts | Complete |")
    print("|---|---:|---:|---:|---:|---|")
    for name, board, run_s, drain_ms in SCENARIOS:
        rs = run(name, board, run_s, drain_ms)
        stops = sorted(r["stop_ms"] for r in rs)
        fifo = sorted(r["fifo_at_stop"] for r in rs) if board is not None else None
        overflows = sorted(r["overflows"] for r in rs) if board is not None else None
        drains = sum(r["drain_timeouts"] for r in rs) if board is not None else None
        complete = sum(r["complete"] for r in rs)

        def span(v):
            return "n/a" if v is None else (f"{v[0]:,}" if v[0] == v[-1] else f"{v[0]:,} to {v[-1]:,}")

        print(f"| {name} | {stops[0]:.0f} / {stops[len(stops) // 2]:.0f} / {stops[-1]:.0f} | {span(fifo)} |"
              f" {span(overflows)} | {'n/a' if drains is None else drains} | {complete} of {len(rs)} |")
        losses = sorted({l for r in rs for l in r["losses"]})
        print(f"<!-- {name}: losses {json.dumps(losses)} -->")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
