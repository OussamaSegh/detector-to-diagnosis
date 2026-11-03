# SPDX-License-Identifier: MIT
"""The calibration procedure (Chapter 26): from the singles of a calibration acquisition to a
calibration table, or to a list of the crystals that keep it from being written.

    python3 -m tools.calib SINGLES.words --out TABLE.json --id CAL-0002 --version 2 \\
        --serial MDQ-REF-0001 --e-sat 1500 [--report REPORT.json]

Steps:
1. Each crystal's code spectrum, its photopeak (energy.fit_photopeaks) and its gain.
2. Each crystal's quadratic from code to keV (energy.fit_curve).
3. The calibrated energies; the isolated pairs in the 511 keV window (timing.pairs); each
   channel's delay (timing.solve_delays).
4. The acceptance criteria (SRS-CAL-007). The table is written only when every crystal passes;
   otherwise each failing crystal is reported, with why, and the exit status is 1.

The source must be a uniform cylinder centred in the field of view (minidaq_sim --source cylinder),
so that each pair of crystals' mean difference in time of flight is zero (timing.py). A point
source at the centre has that property too, but it pairs each crystal only with the few opposite
it, and the delays of those small groups are hard to compare with each other.

Exit status: 0 table written, 1 a criterion failed, 2 the command line or the input file is wrong.
"""
import argparse
import datetime
import json
import sys

import numpy as np

from . import energy, readout, table, timing

# [snippet:criteria]
# The acceptance criteria. Each bounds what one fit can get wrong; the values are this book's
# (assumption: confirm with team, against the scanner's own specification).
CRITERIA = {
    # Photopeak counts per crystal: the centre's statistical error is about sigma / sqrt(counts),
    # 0.25% of 511 keV at 500 counts and a 6% resolution.
    "min_counts": 500,
    # A photopeak's sigma as a fraction of its centre: LYSO with SiPMs is about 4 to 6% (10 to
    # 14% FWHM); outside 2 to 10% the fit has found something else.
    "min_sigma_fraction": 0.02,
    "max_sigma_fraction": 0.10,
    # The gain the photopeak gives, against nominal: the server's own limit is 0.5 to 2.
    "min_gain": 0.6,
    "max_gain": 1.6,
    # How far the quadratic may be from the exact inverse of the response, 200 to 700 keV.
    "max_curve_error": 0.01,
    # Coincident pairs per crystal for its delay: the delay's error is about the residual over
    # sqrt(pairs), 33 ps at 100 pairs and the 326 ps residual below.
    "min_pairs": 100,
    # Distinct crystals each crystal is paired with. A centred cylinder pairs each crystal with a
    # fan across the ring; a point source only with the few opposite it, which leaves the delays
    # of those small groups badly determined (timing.py). This is the criterion that notices the
    # wrong source.
    "min_partners": 40,
    # The residual of the timing solution, ps rms: the coincidence time resolution (300 ps FWHM,
    # 127 ps rms) and the cylinder's own spread of flight times (about 270 ps rms for 80 mm
    # radius), plus what the delays did not explain. Measured: 326 ps; a quarter above that.
    "max_residual_ps": 400.0,
    # A channel delay the server accepts (CalibrationLimits::max_abs_time_offset_ps).
    "max_abs_offset_ps": 5000,
}
# [/snippet:criteria]


def utc(t):
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_args(argv):
    p = argparse.ArgumentParser(prog="python3 -m tools.calib", description=__doc__.split("\n")[0])
    p.add_argument("words", help="the singles, as minidaq_sim --words writes them")
    p.add_argument("--out", required=True, help="the table file to write")
    p.add_argument("--report", help="a JSON report of every crystal's results")
    p.add_argument("--id", required=True, help="the table's id, e.g. CAL-0002")
    p.add_argument("--version", type=int, required=True, help="one more than the previous table's")
    p.add_argument("--serial", required=True, help="the scanner's serial number")
    p.add_argument("--e-sat", type=float, required=True,
                   help="the SiPM's saturation energy in keV, from the bench (0: linear)")
    p.add_argument("--temperature", type=float, default=25.0,
                   help="the detector temperature during the acquisition, degrees C")
    p.add_argument("--valid-days", type=int, default=90, help="days until the table expires")
    p.add_argument("--procedure", default="CP-026 version 1")
    p.add_argument("--now", help="the creation time, YYYY-MM-DDTHH:MM:SSZ (default: now)")
    for key, value in CRITERIA.items():
        p.add_argument("--" + key.replace("_", "-"), type=type(value), default=value)
    a = p.parse_args(argv)
    if a.version < 1 or not 0 <= a.e_sat <= 1e6 or not 1 <= a.valid_days <= 3650:
        p.error("--version must be 1 or more, --e-sat 0 to 1e6 keV, --valid-days 1 to 3650")
    return a


# [snippet:accept]
def accept(c, counts, ok, centre, sigma, gain, curve_error, pairs_per_crystal, partners, offsets,
           rms):
    """Each crystal's failures, as a list of reasons per crystal (empty: it passed), and the
    failures of the whole solution."""
    why = [[] for _ in range(readout.NUM_CRYSTALS)]

    def flag(mask, text):
        for i in np.flatnonzero(mask):
            why[i].append(text(i))

    flag(counts < c["min_counts"], lambda i: f"{counts[i]:.0f} photopeak counts, "
         f"{c['min_counts']} needed")
    flag(~ok, lambda i: "the photopeak fit did not converge")
    frac = np.where(centre > 0, sigma / np.maximum(centre, 1e-9), np.inf)
    flag(ok & ((frac < c["min_sigma_fraction"]) | (frac > c["max_sigma_fraction"])),
         lambda i: f"photopeak sigma {100 * frac[i]:.1f}% of its centre, "
         f"{100 * c['min_sigma_fraction']:.0f} to {100 * c['max_sigma_fraction']:.0f}% expected")
    flag(ok & ((gain < c["min_gain"]) | (gain > c["max_gain"])),
         lambda i: f"gain {gain[i]:.3f}, {c['min_gain']} to {c['max_gain']} expected")
    flag(ok & (curve_error > c["max_curve_error"]),
         lambda i: f"the quadratic is {100 * curve_error[i]:.2f}% from the response, "
         f"{100 * c['max_curve_error']:.1f}% allowed")
    flag(pairs_per_crystal < c["min_pairs"],
         lambda i: f"{pairs_per_crystal[i]} coincident pairs, {c['min_pairs']} needed")
    flag(partners < c["min_partners"],
         lambda i: f"paired with {partners[i]} other crystals, {c['min_partners']} needed")
    flag(np.abs(offsets) > c["max_abs_offset_ps"],
         lambda i: f"delay {offsets[i]} ps, at most {c['max_abs_offset_ps']} ps allowed")
    overall = []
    if rms > c["max_residual_ps"]:
        overall.append(f"the timing residual is {rms:.1f} ps rms, at most "
                       f"{c['max_residual_ps']:.0f} ps allowed")
    return why, overall
# [/snippet:accept]


def run(a):
    crystal, code, t = readout.read(a.words)
    if crystal.size == 0:
        raise ValueError(f"{a.words}: no singles")
    order = np.argsort(t, kind="stable")
    crystal, code, t = crystal[order], code[order], t[order]

    # 1 and 2: energy.
    centre, sigma, counts, ok = energy.photopeaks(energy.spectra(crystal, code))
    gain = energy.gains_from_peaks(centre, a.e_sat)
    ca, cb, cq, curve_error = energy.fit_curve(np.where(ok, gain, 1.0), a.e_sat)
    e_kev = energy.apply(code, crystal, ca, cb, cq)

    # 3: timing, on the singles the energy calibration puts in the 511 keV window.
    i, j = timing.pairs(t, crystal, e_kev)
    ci, cj = crystal[i], crystal[j]
    delays, rms, kept, iterations = timing.solve(ci, cj, (t[i] - t[j]).astype(float))
    offsets = np.round(delays).astype(np.int64)
    per_crystal = np.bincount(ci[kept], minlength=readout.NUM_CRYSTALS) + np.bincount(
        cj[kept], minlength=readout.NUM_CRYSTALS)
    n = readout.NUM_CRYSTALS
    links = np.unique(np.concatenate((ci[kept] * n + cj[kept], cj[kept] * n + ci[kept])))
    partners = np.bincount(links // n, minlength=n)

    # 4: acceptance, then the server's own limits on what would be written.
    c = {k: getattr(a, k) for k in CRITERIA}
    why, overall = accept(c, counts, ok, centre, sigma, gain, curve_error, per_crystal, partners,
                          offsets, rms)
    for k, reason in enumerate(table.server_refusals(ca, cb, cq, offsets)):
        if reason:
            why[k].append("minidaq_server would refuse it: " + reason)
    failed = [k for k in range(readout.NUM_CRYSTALS) if why[k]]
    summary = {
        "singles": int(crystal.size),
        "pairs": int(ci.size),
        "pairs_set_aside": int(ci.size - kept.sum()),
        "timing_iterations": int(iterations),
        "timing_residual_ps": round(rms, 1),
        "photopeak_counts_min": float(counts.min()),
        "gain_min": float(gain[ok].min()) if ok.any() else None,
        "gain_max": float(gain[ok].max()) if ok.any() else None,
        "curve_error_max": float(curve_error.max()),
        "pairs_per_crystal_min": int(per_crystal.min()),
        "partners_min": int(partners.min()),
        "failed_crystals": len(failed),
        "failures": overall,
        "criteria": c,
    }
    if a.report:
        crystals = [{"crystal": k, "counts": float(counts[k]), "centre_code": float(centre[k]),
                     "sigma_code": float(sigma[k]), "gain": float(gain[k]),
                     "curve_error": float(curve_error[k]), "pairs": int(per_crystal[k]),
                     "partners": int(partners[k]),
                     "offset_ps": int(offsets[k]), "failures": why[k]}
                    for k in range(readout.NUM_CRYSTALS)]
        with open(a.report, "w", encoding="utf-8") as f:
            json.dump({"summary": summary, "crystals": crystals}, f, separators=(",", ":"))
    print(json.dumps({k: v for k, v in summary.items() if k != "criteria"}))
    if failed or overall:
        for line in overall:
            print("calibration failed: " + line, file=sys.stderr)
        for k in failed[:20]:
            print(f"crystal {k}: " + "; ".join(why[k]), file=sys.stderr)
        if len(failed) > 20:
            print(f"and {len(failed) - 20} more crystals", file=sys.stderr)
        print(f"no table written: {len(failed)} crystals failed", file=sys.stderr)
        return 1

    now = (datetime.datetime.strptime(a.now, "%Y-%m-%dT%H:%M:%SZ") if a.now
           else datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None, microsecond=0))
    info = {"id": a.id, "version": a.version, "scanner_serial": a.serial,
            "created_utc": utc(now),
            "valid_until_utc": utc(now + datetime.timedelta(days=a.valid_days)),
            "reference_temperature_c": a.temperature, "procedure": a.procedure}
    table.write(a.out, table.build(info, ca, cb, cq, offsets))
    print(f"wrote {a.out}", file=sys.stderr)
    return 0


def main(argv=None):
    a = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        return run(a)
    except (OSError, ValueError) as e:
        print(f"calib: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
