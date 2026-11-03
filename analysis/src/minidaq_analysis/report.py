# SPDX-License-Identifier: MIT
"""The acquisition quality control report of one run.

One pass over the run fills the histograms (histograms.py); the fits (fitting.py) and the rate
check (rates.py) turn them into numbers with uncertainties; each number is compared with the limit
the QC protocol gives it; the report is written as JSON (for machines and for the next report's
trend), Markdown (for people) and figures, next to the provenance of every input.

The protocol is a TOML file, so that the limits are a reviewed document and not constants in the
code. ``DEFAULT_PROTOCOL`` is the book's: its limits are book-level numbers (assumption: confirm
with team the acceptance values of your scanner's daily QC procedure).
"""
from __future__ import annotations

import json
import math
import pathlib
import tomllib
from dataclasses import dataclass
from typing import Any

import numpy as np

from . import fitting, plots, provenance
from .histograms import RunHistograms
from .listmode import ListModeFile, Run
from .rates import check_rate

# [snippet:protocol]
DEFAULT_PROTOCOL = """
name = "MiniDAQ acquisition QC, point source at the center"
version = 1

[energy]
fit_low_kev = 440.0     # inside the sorter's energy window (435 to 585 keV), away from its edges
fit_high_kev = 580.0
peak_kev = [505.9, 516.1]   # 511 keV within 1%
resolution_max = 0.14       # FWHM / E

[timing]
fit_half_width_ps = 1500.0
ctr_max_ps = 400.0          # FWHM
offset_max_ps = 25.0        # |mean| for a source at the center

[rate]
bin_ms = 10.0
p_min = 0.001               # both the constancy test and the dip test

[fit]
reduced_statistic_max = 2.0 # deviance / degrees of freedom
"""
# [/snippet:protocol]


@dataclass(frozen=True)
class Check:
    name: str
    value: float
    error: float | None
    unit: str
    limit: str
    passed: bool


def load_protocol(path: pathlib.Path | None) -> dict[str, Any]:
    text = DEFAULT_PROTOCOL if path is None else path.read_text()
    return tomllib.loads(text)


def fill(run: Run, rate_bin_ms: float, max_records: int = 1 << 20) -> RunHistograms:
    with ListModeFile(run.files[0], verify=False) as first:
        meta = first.metadata
    scanner = meta["scanner"]
    crystals = int(scanner["crystals_per_ring"]) * int(scanner["crystal_rings"])
    delayed = int(meta["records"].get("delayed_window_ps") or 0)
    h = RunHistograms(crystals, delayed, rate_bin_ps=round(rate_bin_ms * 1e9))
    for chunk, tags in run.chunks(max_records):
        h.add(chunk, tags)
    return h


def _reduced(r: fitting.FitResult) -> float:
    return r.statistic / r.ndf


# [snippet:qc]
def quality_control(run: Run, protocol: dict[str, Any]) -> tuple[dict[str, Any], RunHistograms,
                                                                  dict[str, fitting.FitResult]]:
    """(report dict, histograms, fits) of one run under `protocol`."""
    pe, pt, pr = protocol["energy"], protocol["timing"], protocol["rate"]
    max_reduced = float(protocol["fit"]["reduced_statistic_max"])
    h = fill(run, float(pr["bin_ms"]))
    checks: list[Check] = []

    e = fitting.fit_photopeak(h.energy_histogram(), pe["fit_low_kev"], pe["fit_high_kev"])
    mean, mean_err = e["mean"]
    res, res_err = fitting.fwhm_fraction(e)
    lo, hi = pe["peak_kev"]
    checks.append(Check("photopeak position", mean, mean_err, "keV", f"{lo} to {hi}",
                        lo <= mean <= hi))
    checks.append(Check("energy resolution (FWHM/E)", res, res_err, "",
                        f"<= {pe['resolution_max']}", res <= pe["resolution_max"]))
    checks.append(Check("photopeak fit, deviance per degree of freedom", _reduced(e), None, "",
                        f"<= {max_reduced}", _reduced(e) <= max_reduced))

    w = float(pt["fit_half_width_ps"])
    t = fitting.fit_timing(h.dt_histogram().window(-w, w))
    ctr, ctr_err = fitting.fwhm(t)
    offset, offset_err = t["mean"]
    checks.append(Check("coincidence time resolution (FWHM)", ctr, ctr_err, "ps",
                        f"<= {pt['ctr_max_ps']}", ctr <= pt["ctr_max_ps"]))
    checks.append(Check("timing offset", offset, offset_err, "ps", f"|x| <= {pt['offset_max_ps']}",
                        abs(offset) <= pt["offset_max_ps"]))
    checks.append(Check("timing fit, deviance per degree of freedom", _reduced(t), None, "",
                        f"<= {max_reduced}", _reduced(t) <= max_reduced))

    full = h.rate_prompt[:-1]  # the last bin is partial
    rate = check_rate(full)
    checks.append(Check("prompt rate constant (p)", rate.p_constant, None, "",
                        f">= {pr['p_min']}", rate.p_constant >= pr["p_min"]))
    checks.append(Check("no dip in the prompt rate (p)", rate.p_dip, None, "",
                        f">= {pr['p_min']}", rate.p_dip >= pr["p_min"]))

    recorded = run.record.get("run", {}).get("corrections", {})
    if "prompts" in recorded:
        checks.append(Check("prompts in the files minus prompts recorded",
                            h.prompts - int(recorded["prompts"]), None, "", "= 0",
                            h.prompts == int(recorded["prompts"])))
    checks.append(Check("coincidences out of time order", h.out_of_order, None, "", "= 0",
                        h.out_of_order == 0))

    duration_s = ((h.last_ps or 0) - (h.t0_ps or 0)) * 1e-12
    report = {
        "format": "minidaq-analysis QC report 1",
        "protocol": {"name": protocol["name"], "version": protocol["version"]},
        "run": {"name": run.record.get("run_name"), "record": run.record_path.name,
                "files": [f.name for f in run.files], "duration_s": duration_s,
                "prompts": h.prompts, "delayeds": h.delayeds, "tags": h.tags,
                "crystals_hit": int(np.count_nonzero(h.per_crystal)),
                "pairs_hit": int(h.pairs[0].size)},
        "fits": {name: {"method": r.method,
                        "parameters": dict(zip(r.names, r.values.tolist(), strict=True)),
                        "errors": dict(zip(r.names, r.errors.tolist(), strict=True)),
                        "statistic": r.statistic, "ndf": r.ndf, "p_value": r.p_value}
                 for name, r in (("photopeak", e), ("timing", t))},
        "rate": {"bin_ms": float(pr["bin_ms"]), "bins": rate.bins,
                 "mean_per_s": rate.mean_per_bin / (float(pr["bin_ms"]) * 1e-3),
                 "dispersion": rate.dispersion, "lowest": rate.lowest},
        "checks": [{k: _plain(v) for k, v in c.__dict__.items()} for c in checks],
        "passed": bool(all(c.passed for c in checks)),
    }
    return report, h, {"photopeak": e, "timing": t}
# [/snippet:qc]


def _plain(v: Any) -> Any:
    """A numpy scalar as the Python value json can write."""
    return v.item() if isinstance(v, np.generic) else v


def _fmt(c: dict[str, Any]) -> str:
    v, err = c["value"], c["error"]
    if err is None:
        return f"{v:.4g}"
    digits = max(0, 1 - math.floor(math.log10(err))) if err > 0 else 3
    return f"{v:.{digits}f} ± {err:.{digits}f}"


def markdown(report: dict[str, Any]) -> str:
    r = report["run"]
    lines = [f"# Acquisition QC: {r['name']}", "",
             f"Protocol: {report['protocol']['name']}, version {report['protocol']['version']}. "
             f"Result: **{'PASS' if report['passed'] else 'FAIL'}**.", "",
             f"{r['prompts']:,} prompts and {r['delayeds']:,} delayed coincidences in "
             f"{r['duration_s']:.3f} s, {r['crystals_hit']:,} crystals and {r['pairs_hit']:,} "
             "crystal pairs hit.", "",
             "| Check | Value | Unit | Limit | Result |", "|---|---|---|---|---|"]
    for c in report["checks"]:
        lines.append(f"| {c['name']} | {_fmt(c)} | {c['unit']} | {c['limit']} | "
                     f"{'pass' if c['passed'] else 'FAIL'} |")
    lines += ["", "Uncertainties are one standard error, from the fit's covariance. Figures: "
              "`energy.png`, `timing.png`, `rate.png`. Inputs and environment: `provenance.json`.",
              ""]
    return "\n".join(lines)


def write_report(record_path: pathlib.Path, out: pathlib.Path,
                 protocol_path: pathlib.Path | None = None,
                 argv: list[str] | None = None) -> dict[str, Any]:
    """Runs the QC of one run and writes report.json, report.md, provenance.json and the figures
    into `out`. Returns the report."""
    protocol = load_protocol(protocol_path)
    run = Run(record_path)
    report, h, fits = quality_control(run, protocol)
    out.mkdir(parents=True, exist_ok=True)
    inputs = [run.record_path, *run.files] + ([protocol_path] if protocol_path else [])
    manifest = provenance.make_manifest(inputs, run.record_path.parent if protocol_path is None
                                        else _common_root(inputs))
    prov = {"inputs": manifest, "inputs_id": provenance.manifest_id(manifest),
            "environment": provenance.environment(argv)}
    report["inputs_id"] = prov["inputs_id"]
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    (out / "provenance.json").write_text(json.dumps(prov, indent=2) + "\n")
    (out / "report.md").write_text(markdown(report))
    plots.energy(h, fits["photopeak"], out / "energy.png")
    plots.timing(h, fits["timing"], out / "timing.png")
    plots.rate(h, out / "rate.png")
    return report


def _common_root(paths: list[pathlib.Path]) -> pathlib.Path:
    resolved = [p.resolve() for p in paths]
    root = resolved[0].parent
    while not all(root in p.parents for p in resolved):
        root = root.parent
    return root
