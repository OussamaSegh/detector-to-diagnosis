#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Chapter 26 measurements: the calibration procedure on minidaq_sim's uncalibrated detector.

The detector: every crystal with its own gain (10% spread), a SiPM that saturates (E_sat 1500 keV)
and its own channel delay (500 ps spread), as minidaq_sim --gain-spread 0.1 --saturation 1500
--time-skew 500 makes it, with the truth written by --crystal-truth.

1. A calibration acquisition: a uniform cylinder centered in the ring, no phantom, 20 MBq for 3 s.
   The procedure (python3 -m tools.calib), how long it took, and its results against the truth:
   gains, where each crystal's photopeak lands through its curve, delays, and the energy
   resolution of the summed spectrum before and after.
2. The same with a point source at the center: what the acceptance criteria say, and how wrong
   the delays would be if the table were written anyway.
3. A short acquisition (0.5 s): the crystals the criteria refuse, and why.
4. minidaq_server with the table: the status names it; a configuration for another scanner serial
   is refused.
5. The photopeak monitor's baseline in a patient-like run: the cylinder in a 90 mm water phantom,
   5 MBq for 0.5 s, calibrated with the table of 1: the mean calibrated energy in 430 to 590 keV,
   as the monitor computes it per block.

    python3 measurements/ch26/calibration.py build/release/minidaq/apps > measurements/ch26/calibration.txt
"""
import json
import os
import re
import pathlib
import platform
import socket
import subprocess
import sys
import tempfile
import time

import numpy as np

APPS = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "build/release/minidaq/apps")
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.calib import energy, readout  # noqa: E402

DETECTOR = ["--gain-spread", "0.1", "--saturation", "1500", "--time-skew", "500", "--seed", "26"]
E_SAT = "1500"
SERIAL = "MDQ-REF-0001"


def simulate(tmp, name, source, seconds):
    words, truth = tmp / f"{name}.words", tmp / f"{name}-truth.csv"
    t0 = time.monotonic()
    subprocess.run([str(APPS / "minidaq_sim"), "--activity", "2e7", "--seconds", str(seconds),
                    "--source", source, "--phantom", "0", *DETECTOR, "--words", str(words),
                    "--crystal-truth", str(truth)], check=True, capture_output=True)
    return words, truth, time.monotonic() - t0


def calibrate(tmp, name, words, *extra):
    out, report = tmp / f"{name}.json", tmp / f"{name}-report.json"
    t0 = time.monotonic()
    r = subprocess.run([sys.executable, "-B", "-m", "tools.calib", str(words), "--out", str(out),
                        "--report", str(report), "--id", "CAL-0002", "--version", "2",
                        "--serial", SERIAL, "--e-sat", E_SAT, "--now", "2026-11-03T09:00:00Z",
                        *extra], cwd=ROOT, capture_output=True, text=True, check=False)
    seconds = time.monotonic() - t0
    return r, out, json.loads(report.read_text()), seconds


def truth_of(path):
    t = np.genfromtxt(path, delimiter=",", names=True)
    return t["gain"], t["delay_ps"]


def delay_error(report, delay):
    off = np.array([c["offset_ps"] for c in report["crystals"]], dtype=float)
    err = off - delay
    return err - err.mean()


def fwhm_percent(e_kev):
    """FWHM of the 511 keV photopeak of a summed spectrum, in % of its center (2 keV bins)."""
    h = np.histogram(e_kev, bins=512, range=(0, 1024))[0][None, :]
    center, sigma, _, ok = energy.fit_photopeaks(h, lo=150, hi=400, smooth=9)
    return (2.0 * float(center[0]) + 1.0, 2.3548 * float(sigma[0]) / float(center[0]) * 100.0,
            bool(ok[0]))


def section(title):
    print(f"\n## {title}\n")


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def server_check(tmp, table):
    port = free_port()
    ctl = [str(APPS / "minidaq_ctl"), "--port", str(port)]
    srv = subprocess.Popen([str(APPS / "minidaq_server"), "--port", str(port), "--no-auth"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):
            if subprocess.run([*ctl, "hello"], capture_output=True).returncode == 0:
                break
            time.sleep(0.05)
        results = []
        for serial in (SERIAL, "MDQ-OTHER-0002"):
            cfg = tmp / f"config-{serial}.json"
            cfg.write_text(json.dumps({"schema_version": "1.4", "source": {"rate_hz": 1e6},
                                       "stop_after_s": 2,
                                       "calibration": {"file": str(table),
                                                       "scanner_serial": serial}}))
            subprocess.run([*ctl, "reset"], capture_output=True)
            r = subprocess.run([*ctl, "configure", str(cfg)], capture_output=True, text=True)
            status = subprocess.run([*ctl, "status"], capture_output=True, text=True).stdout
            results.append((serial, r.returncode, (r.stdout + r.stderr).strip(), status))
        return results
    finally:
        srv.terminate()
        srv.wait(timeout=10)


def main():
    print("# Chapter 26: calibrating an uncalibrated detector\n")
    print(f"Machine: {platform.machine()}, {os.cpu_count()} CPUs, Python "
          f"{platform.python_version()}, numpy {np.__version__}.")
    print("Detector: minidaq_sim " + " ".join(DETECTOR) + "; acquisitions at 20 MBq, no phantom.")
    with tempfile.TemporaryDirectory() as d:
        tmp = pathlib.Path(d)

        # 1. The cylinder.
        words, truth, sim_s = simulate(tmp, "cylinder", "cylinder", 3)
        r, table, rep, cal_s = calibrate(tmp, "cylinder", words)
        gain, delay = truth_of(truth)
        s = rep["summary"]
        section("1. Uniform cylinder, 3 s")
        print(f"Simulated in {sim_s:.0f} s; calibrated in {cal_s:.1f} s; exit status {r.returncode}.")
        print(f"Singles {s['singles']:,}; isolated pairs {s['pairs']:,}, of which "
              f"{s['pairs_set_aside']:,} set aside as outliers; timing solution "
              f"{s['timing_iterations']} iterations, residual {s['timing_residual_ps']} ps rms.")
        print(f"Least photopeak counts {s['photopeak_counts_min']:.0f}; least pairs "
              f"{s['pairs_per_crystal_min']}; least partners {s['partners_min']}; worst curve "
              f"error {100 * s['curve_error_max']:.2f}%; failed crystals {s['failed_crystals']}.")
        found = np.array([c["gain"] for c in rep["crystals"]])
        g_err = found / gain - 1
        print(f"Gain error against the truth: mean {100 * g_err.mean():+.3f}%, rms "
              f"{100 * g_err.std():.3f}%, worst {100 * np.abs(g_err).max():.2f}%.")
        doc = json.loads(table.read_text())
        a, b, q = (np.array(doc["energy"][k]) for k in ("a_kev", "b_kev", "q_kev"))
        c511 = gain * energy.saturate(511.0, float(E_SAT)) / readout.ENERGY_LSB_KEV
        e511 = a + c511 * (b + c511 * q)
        print(f"Each crystal's true photopeak through its curve: mean {e511.mean():.2f} keV, rms "
              f"spread {e511.std():.2f} keV, worst {np.abs(e511 - 511).max():.2f} keV from 511.")
        err = delay_error(rep, delay)
        print(f"Delay error against the truth (common constant removed): rms {err.std():.1f} ps, "
              f"worst {np.abs(err).max():.0f} ps; the delays themselves spread {delay.std():.0f} ps "
              f"rms.")
        ring = np.arange(readout.NUM_CRYSTALS) // 384
        edges = np.isin(ring, (0, 1, 46, 47))
        print(f"  in the two rings at each end: rms {err[edges].std():.1f} ps, mean "
              f"{err[edges].mean():+.1f} ps; elsewhere rms {err[~edges].std():.1f} ps.")
        crystal, code, _ = readout.read(words)
        raw = code * readout.ENERGY_LSB_KEV
        cal = energy.apply(code, crystal, a, b, q)
        for label, e in (("as reported (0.5 keV per code)", raw), ("calibrated", cal)):
            center, fwhm, ok = fwhm_percent(e)
            print(f"Summed spectrum, {label}: photopeak at {center:.0f} keV, FWHM {fwhm:.1f}% "
                  f"(fit {'ok' if ok else 'failed'}).")
        os.unlink(words)

        # 2. The point source.
        words, truth, _ = simulate(tmp, "point", "point", 3)
        r, _, rep, _ = calibrate(tmp, "point", words)
        _, delay = truth_of(truth)
        s = rep["summary"]
        section("2. Point source at the center, 3 s")
        print(f"Exit status {r.returncode}; failed crystals {s['failed_crystals']}; least partners "
              f"{s['partners_min']}, median "
              f"{np.median([c['partners'] for c in rep['crystals']]):.0f}; residual "
              f"{s['timing_residual_ps']} ps rms; {s['timing_iterations']} iterations.")
        print("First lines of its report:")
        for line in r.stderr.splitlines()[:3]:
            print("    " + line)
        err = delay_error(rep, delay)
        print(f"Delay error if the table were written anyway: rms {err.std():.1f} ps, worst "
              f"{np.abs(err).max():.0f} ps.")
        os.unlink(words)

        # 3. Too short.
        words, _, _ = simulate(tmp, "short", "cylinder", 0.5)
        r, out, rep, _ = calibrate(tmp, "short", words)
        s = rep["summary"]
        section("3. Uniform cylinder, 0.5 s")
        reasons = {}
        for c in rep["crystals"]:
            for f in c["failures"]:
                key = re.sub(r"-?\d[\d.,]*", "N", f)
                reasons[key] = reasons.get(key, 0) + 1
        print(f"Exit status {r.returncode}; table written: {out.exists()}; failed crystals "
              f"{s['failed_crystals']} of {readout.NUM_CRYSTALS}.")
        for k, v in sorted(reasons.items(), key=lambda kv: -kv[1]):
            print(f"  {v:6d} crystals: {k}")
        print("Last lines of its report:")
        for line in r.stderr.splitlines()[-2:]:
            print("    " + line)

        # 5. The monitor's baseline with scatter (before 4, while the table is at hand).
        words5 = tmp / "phantom.words"
        subprocess.run([str(APPS / "minidaq_sim"), "--activity", "5e6", "--seconds", "0.5",
                        "--source", "cylinder", *DETECTOR, "--words", str(words5)], check=True,
                        capture_output=True)
        crystal, code, _ = readout.read(words5)
        e = energy.apply(code, crystal, a, b, q)
        m = (e >= 430.0) & (e <= 590.0)
        block = (crystal // 384 // 16) * 24 + (crystal % 384) // 16
        means = np.bincount(block[m], e[m], 72) / np.bincount(block[m], minlength=72)
        os.unlink(words5)

        # 4. The server.
        section("4. minidaq_server with the table of 1")
        for serial, rc, text, status in server_check(tmp, table):
            print(f"Configuration naming scanner {serial}: minidaq_ctl exit status {rc}.")
            if rc != 0:
                print("    " + json.loads(text)["error"]["message"][:200])
            else:
                st = json.loads(status)["status"]
                print("    status calibration: " + json.dumps(st.get("calibration")))

        section("5. The photopeak monitor's baseline, cylinder in a 90 mm water phantom")
        print(f"Calibrated singles in 430 to 590 keV: {int(m.sum()):,}; mean {e[m].mean():.1f} keV "
              f"({100 * (e[m].mean() / 511 - 1):+.2f}% from 511); per block {means.min():.1f} to "
              f"{means.max():.1f} keV.")


if __name__ == "__main__":
    main()
