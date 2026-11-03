#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Chapter 27 measurements: the corrections, each against minidaq_sim's truth.

One scanner (crystal seed 7): every crystal with its own detection efficiency (minidaq_sim
--efficiency-spread 0.05: mean 0.90, 0.05 rms), otherwise the simulator's default detector.

1. A normalization scan: a cylinder of activity in air, radius 118 mm and 120 mm long (it fills the
   transaxial and the axial field of view), 10 MBq, six runs of 5 s with different seeds. Each
   crystal's efficiency from the fan sums of its list mode, against the truth.
2. A patient-like scan: the default source (a cylinder of radius 80 mm, 100 mm long) in a water
   cylinder of radius 90 mm, 20 MBq for 5 s, same scanner. Randoms from the delayed window and
   from the singles of the run record, with and without the singles already in coincidence,
   against the truth.
3. The same scan: scatter by tail fitting, against the truth: a Gaussian fitted to the tails, and
   the shape of a model scaled to the tails. The model is a simulation of the same phantom on a
   perfect scanner (another seed, no efficiency spread), as a Monte Carlo model of the object.
4. The same scan: what the corrections give, step by step. The profile of the slices well inside
   the source, summed over the views, against the source's own projection (its chords), which is
   what an ideal scanner would see.

    python3 measurements/ch27/corrections.py build/release/minidaq/apps [WORK_DIR] \
        > measurements/ch27/corrections.txt

WORK_DIR keeps the simulated runs (about 1.5 GB); a run already there is not simulated again.
"""
import os
import pathlib
import platform
import subprocess
import sys
import tempfile
import time

import numpy as np

APPS = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "build/release/minidaq/apps")
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.recon import corrections as cor, listmode, sinogram as sg  # noqa: E402

SCANNER = ["--efficiency-spread", "0.05", "--crystal-seed", "7"]
NORM_RUNS = 6
NORM = ["--activity", "1e7", "--seconds", "5", "--phantom", "0", "--source-radius", "118",
        "--source-length", "120"]
PHANTOM = ["--activity", "2e7", "--seconds", "5"]  # the default: source 80 mm in water 90 mm
ONE_SECOND = ["--activity", "2e7", "--seconds", "1"]
DEAD_TAU_NS = 200
SOURCE_RADIUS, WATER_RADIUS = 80.0, 90.0


def simulate(work, name, args, seed, scanner=SCANNER):
    d = work / name
    if (d / "truth.hdr").exists() and list(d.glob("*.run.json")):
        return 0.0
    d.mkdir(parents=True, exist_ok=True)
    truth = ["--crystal-truth", str(work / "crystals.csv")] if scanner else []
    t0 = time.monotonic()
    with open(d / "sim.txt", "w") as out:
        subprocess.run([str(APPS / "minidaq_sim"), *args, *scanner, "--seed", str(seed),
                        "--listmode", str(d), "--truth-sino", str(d / "truth"), *truth],
                       check=True, stdout=out)
    return time.monotonic() - t0


def section(title):
    print(f"\n## {title}\n")


def pct(x):
    return 100.0 * x


def tails_cols(h):
    return (np.abs(h.s_mm) >= WATER_RADIUS + 2) & (np.abs(h.s_mm) <= WATER_RADIUS + 22)


def main():
    work_arg = sys.argv[2] if len(sys.argv) > 2 else None
    tmp = None if work_arg else tempfile.TemporaryDirectory()
    work = pathlib.Path(work_arg or tmp.name)
    work.mkdir(parents=True, exist_ok=True)
    print("# Chapter 27: the corrections against the simulator's truth\n")
    print(f"Machine: {platform.machine()}, {os.cpu_count()} CPUs, Python "
          f"{platform.python_version()}, numpy {np.__version__}.")
    print("Scanner: minidaq_sim " + " ".join(SCANNER) + ".")
    sim_s = sum(simulate(work, f"norm{k}", NORM, k) for k in range(1, NORM_RUNS + 1))
    sim_s += simulate(work, "phantom", PHANTOM, 1000)
    sim_s += simulate(work, "scatter_model", PHANTOM, 2000, scanner=[])
    print(f"Simulated in {sim_s:.0f} s (0 if the runs were reused).")
    truth = np.genfromtxt(work / "crystals.csv", delimiter=",", names=True)
    eff_true = truth["efficiency"].reshape(sg.RINGS, sg.CRYSTALS_PER_RING)

    # 1. Normalization.
    t0 = time.monotonic()
    a, b, dl = [], [], []
    for k in range(1, NORM_RUNS + 1):
        _, c = listmode.read_run(next((work / f"norm{k}").glob("*.run.json")))
        a.append(c["crystal_a"]), b.append(c["crystal_b"]), dl.append(c["delayed"])
    a, b, dl = np.concatenate(a), np.concatenate(b), np.concatenate(dl)
    eff = cor.crystal_efficiencies(a, b, dl)
    read_s = time.monotonic() - t0
    rel_true = eff_true / eff_true.mean(axis=1, keepdims=True)
    err = eff / rel_true - 1
    prompts, delayeds = int((~dl).sum()), int(dl.sum())
    fan = cor.fan_sums(a, b, np.where(dl, -1.0, 1.0))
    section("1. Normalization scan: crystal efficiencies from fan sums")
    print(f"{NORM_RUNS} runs: {prompts:,} prompts, {delayeds:,} delayeds; read and summed in "
          f"{read_s:.1f} s.")
    print(f"Fan sum (prompts minus delayeds) per crystal: mean {fan.mean():,.0f}, so a Poisson "
          f"error of about {pct(1 / np.sqrt(fan.mean())):.1f}%.")
    print(f"True efficiencies: mean {eff_true.mean():.4f}, rms spread {pct(eff_true.std()):.2f}%; "
          f"relative to their ring's mean, rms {pct(rel_true.std()):.2f}%.")
    print(f"Found against true (each relative to its ring): rms error {pct(err.std()):.2f}%, "
          f"worst {pct(np.abs(err).max()):.1f}%, mean {pct(err.mean()):+.3f}%.")
    ring_mean = eff_true.mean(axis=1)
    print(f"Ring means, left to the geometric factors: {ring_mean.min():.4f} to "
          f"{ring_mean.max():.4f}.")

    hn = sg.read_header(work / "norm1" / "truth.hdr")
    norm_p = sum(sg.read(sg.read_header(work / f"norm{k}" / "truth.hdr"), "prompts")
                 for k in range(1, NORM_RUNS + 1))
    norm_d = sum(sg.read(sg.read_header(work / f"norm{k}" / "truth.hdr"), "delayeds")
                 for k in range(1, NORM_RUNS + 1))
    prod = cor.efficiency_products(eff, hn)
    geo = cor.geometric_factors(norm_p - norm_d, prod, hn, 118.0)
    n_found = cor.normalization(prod, geo)
    prod_true = cor.efficiency_products(rel_true, hn)
    pe = prod[prod > 0] / prod_true[prod > 0] - 1
    print("Per bin, the mean efficiency product over its ring pairs: rms error "
          f"{pct(pe.std()):.2f}% "
          f"(the products of {sg.RINGS} ring pairs average the crystals' errors).")
    print(f"Geometric factors: {geo[geo > 0].min():.3f} to {geo.max():.3f} "
          f"(slices x columns, mean 1).")
    del a, b, dl

    # 2. Randoms.
    h = sg.read_header(work / "phantom" / "truth.hdr")
    record, c = listmode.read_run(next((work / "phantom").glob("*.run.json")))
    k = record["run"]["corrections"]
    seconds = (k["singles_last_ps"] - k["singles_first_ps"]) * 1e-12
    P = sg.read(h, "prompts")
    D = sg.read(h, "delayeds")
    T, S, R = (sg.read(h, x) for x in ("trues", "scatters", "randoms"))
    prompt = ~c["delayed"]
    paired = cor.fan_sums(c["crystal_a"][prompt], c["crystal_b"][prompt])
    window = k["coincidence_window_ps"]
    R_all = cor.randoms_from_singles(k["singles_per_crystal"], window, seconds, h)
    R_s = cor.randoms_from_singles(k["singles_per_crystal"], window, seconds, h,
                                   in_coincidence=paired)
    section("2. Patient-like scan: randoms")
    print(f"Run: {seconds:.3f} s; {k['singles_in_window']:,} singles in "
          f"{k['energy_window_kev'][0]:.0f} to {k['energy_window_kev'][1]:.0f} keV, of which "
          f"{pct(paired.sum() / k['singles_in_window']):.1f}% in a prompt coincidence; window "
          f"{window} ps, {k['window_mode']}.")
    print(f"Binned prompts {P.sum():,.0f}: trues {T.sum():,.0f}, scatters {S.sum():,.0f}, randoms "
          f"{R.sum():,.0f} ({pct(R.sum() / P.sum()):.1f}% of the prompts).")
    print("Randoms estimates against the truth, in the binned field of view:\n")
    print("| Estimate | Randoms | Against the truth |")
    print("|---|---:|---:|")
    for label, x in (("delayed window", D), ("2 tau S_a S_b / t, all singles", R_all),
                     ("the same, singles in a prompt coincidence subtracted", R_s)):
        print(f"| {label} | {x.sum():,.0f} | {pct(x.sum() / R.sum() - 1):+.1f}% |")
    m = R_s > 0
    print(f"\nPer bin: mean {R.mean():.4f} true randoms. The delayeds scatter about the singles "
          f"estimate by {np.sqrt(((D - R_s)[m] ** 2).mean()):.3f} rms, Poisson noise on means of "
          f"{R_s[m].mean():.4f}; the singles estimate has no noise of its own (its singles are "
          f"thousands per crystal).")
    # The profile of the randoms: is the singles estimate's shape right?
    prof_t, prof_s = R.sum(axis=(0, 1)), R_s.sum(axis=(0, 1))
    print(f"Shape over s (sum of all slices and views): singles estimate / truth from "
          f"{(prof_s / prof_t).min():.3f} to {(prof_s / prof_t).max():.3f} across the columns, "
          f"rms {pct((prof_s / prof_t).std()):.1f}% (truth Poisson about "
          f"{pct(1 / np.sqrt(prof_t.mean())):.1f}% per column).")

    # 3. Scatter.
    with np.errstate(divide="ignore", invalid="ignore"):
        n_safe = np.where(n_found > 0, n_found, 1.0)
        y = (P - R_s) / n_safe
        s_true = S / n_safe
    hm = sg.read_header(work / "scatter_model" / "truth.hdr")
    model = sg.read(hm, "scatters").sum(axis=1, keepdims=True) / hm.views  # per slice
    with np.errstate(divide="ignore", invalid="ignore"):
        g3 = geo[:, None, :]
        model = np.where(g3 > 0, model / np.where(g3 > 0, g3, 1.0), 0.0)
    inside = np.abs(h.s_mm) <= WATER_RADIUS
    section("3. Patient-like scan: scatter by tail fitting")
    tl = tails_cols(h)
    print(f"True scatter fraction of the binned prompts {pct(S.sum() / (T.sum() + S.sum())):.1f}%. "
          f"Tails: |s| from {WATER_RADIUS + 2:.0f} to {WATER_RADIUS + 22:.0f} mm, where the "
          "prompts "
          f"are {S[..., tl].sum():,.0f} scatters and {R[..., tl].sum():,.0f} randoms (the singles "
          f"estimate: {R_s[..., tl].sum():,.0f}).\n")
    print("| Shape | Under the object | s = 0 | s = 40 | s = 80 | s = 95 |")
    print("|---|---:|---:|---:|---:|---:|")
    estimates = {}
    y_true_r = (P - R) / n_safe
    for label, shape, data, axes in (
            ("Gaussian fitted to the tails, a scale per slice", None, y, (1,)),
            ("model (a simulated phantom of the same size), a scale per slice", model, y, (1,)),
            ("model, one scale for all slices", model, y, (0, 1)),
            ("model, one scale, the true randoms subtracted", model, y_true_r, (0, 1))):
        est, sigma = cor.tail_fit_scatter(data, h, WATER_RADIUS, shape=shape, sensitivity=n_found,
                                          shared_axes=axes)
        estimates[label] = est
        if sigma is not None:
            label += f" (sigma {sigma:.0f} mm)"
        counts = est * n_found  # compared in counts: per bin, S / n blows up where n is small
        prof_e, prof_t = counts.sum(axis=(0, 1)), S.sum(axis=(0, 1))
        cells = []
        for s0 in (0.0, 40.0, 80.0, 95.0):
            j = np.argmin(np.abs(h.s_mm - s0))
            cells.append(f"{prof_e[j] / prof_t[j]:.2f}")
        tot = counts[..., inside].sum() / S[..., inside].sum()
        print(f"| {label} | {tot:.3f} | " + " | ".join(cells) + " |")
    print("\nEach cell is the estimate over the truth, in counts, summed over the slices and "
          f"views; under the object is the sum over |s| <= {WATER_RADIUS:.0f} mm. The scale is the "
          "Poisson "
          "maximum likelihood of each slice's tail counts.")
    for label in ("model (a simulated phantom of the same size), a scale per slice",
                  "model, one scale for all slices"):
        e = (estimates[label] * n_found)[20:75][..., inside].sum(axis=(1, 2))
        err = e / S[20:75][..., inside].sum(axis=(1, 2)) - 1
        print(f"Slice by slice (slices 20 to 74), {label}: scatter under the object against the "
              f"truth, rms {pct(np.sqrt(np.mean(np.square(err)))):.1f}%.")
    print(f"A slice's tails hold about {P[20:75][..., tl].sum() / 55:.0f} prompts, of which "
          f"{S[20:75][..., tl].sum() / 55:.0f} scatters.")
    s_est = estimates["model, one scale for all slices"]

    # 4. Everything, step by step.
    A = cor.attenuation_factors(h, WATER_RADIUS)
    chord = cor.cylinder_chords(h, SOURCE_RADIUS)
    central = slice(20, 75)  # slices 20 to 74: z within +-34 mm, inside the 100 mm source
    with np.errstate(divide="ignore", invalid="ignore"):
        n_true = np.where(prod_true > 0, prod_true * geo[:, None, :], 0.0)
        t_true = np.where(n_true > 0, T / np.where(n_true > 0, n_true, 1.0), 0.0) / A
    steps = [
        ("prompts as measured", P),
        ("minus randoms (singles)", P - R_s),
        ("normalized", (P - R_s) / n_safe),
        ("minus scatter (model, one scale)", (P - R_s) / n_safe - s_est),
        ("attenuation corrected", ((P - R_s) / n_safe - s_est) / A),
        ("truth: trues / (n A)", T / n_safe / A),
        ("truth: trues / (n_true A)", t_true),
    ]
    section("4. Patient-like scan: the profile, step by step")
    print("Slices 20 to 74, summed over the views, the two sides of s averaged, divided by the "
          "source's chord and scaled to a mean of 1 over |s| < 65 mm. A correct correction is "
          "flat (1.000) "
          "under the source (|s| < 80 mm); the rms is over |s| < 65 mm, away from the edge, "
          "which the detector's resolution blurs.\n")
    cols = [0.0, 20.0, 40.0, 60.0, 75.0, 85.0, 100.0]
    print("| Step | " + " | ".join(f"s = {c:.0f}" for c in cols) + " | rms, abs(s) < 65 |")
    print("|---|" + "---:|" * (len(cols) + 1))
    j0 = np.argmin(np.abs(h.s_mm))
    under = (np.abs(h.s_mm) < 65.0) & (chord > 0)
    for label, x in steps:
        prof = x[central].sum(axis=(0, 1))
        prof = 0.5 * (prof + prof[::-1])  # the columns are symmetric about s = 0
        with np.errstate(divide="ignore", invalid="ignore"):
            shape = np.where(chord > 0, prof / np.where(chord > 0, chord, 1.0), 0.0)
        shape = shape / shape[under].mean()
        vals = []
        for c0 in cols:
            j = np.argmin(np.abs(h.s_mm - c0))
            vals.append(f"{shape[j]:.3f}" if chord[j] > 0 else f"({prof[j] / prof[j0]:.3f})")
        rms = np.sqrt(((shape[under] - shape[under].mean()) ** 2).mean())
        print(f"| {label} | " + " | ".join(vals) + f" | {pct(rms):.1f}% |")
    tc = T[central].sum(axis=(0, 1))
    tc = 0.5 * (tc + tc[::-1])
    print("\nOutside the source a value in parentheses is the profile itself over its value at the "
          "center. The central column is low in the truth too, by 2.4 times its Poisson noise. "
          "Poisson noise of the trues per column (both sides together): about "
          f"{pct(1 / np.sqrt(tc[under].mean())):.1f}%.")
    # 5. Dead time.
    dead_args = ["--deadtime", "non_paralyzable", "--tau", str(DEAD_TAU_NS)]
    t0 = time.monotonic()
    simulate(work, "dead_none", ONE_SECOND, 3000)
    simulate(work, "dead_np", ONE_SECOND + dead_args, 3000)
    section("5. Dead time: the live fraction from the singles per block")
    rec = {}
    for name in ("dead_none", "dead_np"):
        r, _ = listmode.read_run(next((work / name).glob("*.run.json")))
        hd = sg.read_header(work / name / "truth.hdr")
        rec[name] = (r["run"]["corrections"], sg.read(hd, "trues").sum())
    k_np, t_np = rec["dead_np"]
    k_0, t_0 = rec["dead_none"]
    secs = (k_np["singles_last_ps"] - k_np["singles_first_ps"]) * 1e-12
    live = cor.live_fractions(k_np["singles_per_block"], secs, DEAD_TAU_NS)
    pair = cor.pair_live_fraction(live)
    print(f"The phantom for 1 s at 20 MBq, the same seed, without and with a non-paralyzable dead "
          f"time of {DEAD_TAU_NS} ns per block (minidaq_sim {' '.join(dead_args)}). Recorded "
          f"singles per block: {np.mean(k_np['singles_per_block']) / secs / 1e3:,.0f} kHz on "
          f"average, {np.min(k_np['singles_per_block']) / secs / 1e3:,.0f} to "
          f"{np.max(k_np['singles_per_block']) / secs / 1e3:,.0f} kHz.\n")
    print("| Quantity | From the singles per block | From the two runs |")
    print("|---|---:|---:|")
    print(f"| Singles live fraction | {np.mean(live):.4f} | "
          f"{sum(k_np['singles_per_block']) / sum(k_0['singles_per_block']):.4f} |")
    print(f"| Coincidence live fraction (trues) | {pair:.4f} | {t_np / t_0:.4f} |")
    print(f"\nTrues binned: {t_0:,.0f} without, {t_np:,.0f} with dead time (Poisson "
          f"{pct(np.sqrt(1 / t_np + 1 / t_0)):.2f}% on their ratio, though the two runs share "
          f"their decays). Simulated in {time.monotonic() - t0:.0f} s.")
    if tmp:
        tmp.cleanup()


if __name__ == "__main__":
    main()
