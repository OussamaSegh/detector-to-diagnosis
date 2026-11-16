# SPDX-License-Identifier: MIT
"""The corrections of Chapter 27 as steps on whole runs: what a reconstruction (Chapter 28) needs
from a normalization scan and from the run it reconstructs. Each step reads a run directory as
minidaq_sim or minidaq_server writes it: the list mode, the run record and, from the simulator,
truth.hdr with its sinograms."""
import pathlib

import numpy as np

from . import corrections as cor, listmode, sinogram as sg


def run_record(run_dir):
    """(record, coincidences) of the one run in run_dir."""
    return listmode.read_run(next(pathlib.Path(run_dir).glob("*.run.json")))


# [snippet:tof-guard]
class TimeBaseError(ValueError):
    """A run whose time base cannot be trusted for time of flight."""


def check_time_base_for_tof(record):
    """Raises TimeBaseError unless the run record says its time base held: a time of flight puts
    each event c tau / 2 along its line, so a block clock 400 ps off moves its events by 60 mm,
    where a reconstruction without TOF only loses a few coincidences (Chapters 38 and 39).

    A run of the server must carry the time base monitor's verdict (control API 3.1) with no
    interval at alarm and no lock loss of a board's clock. A simulation (its record has
    "simulation") has the clocks it was given and passes; a run without the verdict does not."""
    run = record.get("run", {})
    if "simulation" in run:
        return
    timing = run.get("timing")
    if timing is None:
        raise TimeBaseError("the run record has no time base verdict (a server before 2.0, or the "
                            "monitor was off): reconstruct it without time of flight")
    if timing.get("alarm_intervals", 0) > 0:
        blocks = [i for i, b in enumerate(timing.get("blocks", [])) if b.get("alarm_intervals", 0)]
        raise TimeBaseError(f"the time base was at alarm in {timing['alarm_intervals']} intervals "
                            f"(blocks {blocks}): reconstruct it without time of flight")
    lost = [i for i, b in enumerate(run.get("hardware", {}).get("boards", []))
            if b.get("clock_lock_losses", 0)]
    if lost:
        raise TimeBaseError(f"the clock of boards {lost} lost its lock during the run: "
                            "reconstruct it without time of flight")


def tof_sinograms(run_dir, header, tof_bins, tof_bin_ps):
    """(prompts, delayeds) of the run in run_dir with time of flight, the only way the tool bins a
    run with it: the run record is checked first, and TimeBaseError raised before any event is
    placed along its line."""
    record, c = run_record(run_dir)
    check_time_base_for_tof(record)
    return sg.bin_2d(c, header, tof_bins, tof_bin_ps)
# [/snippet:tof-guard]


def normalization(norm_dirs, source_radius_mm):
    """n for every bin, and the crystal efficiencies, from the normalization scans in norm_dirs (a
    cylinder of activity in air of source_radius_mm, centered)."""
    a, b, dl = [], [], []
    for d in norm_dirs:
        _, c = run_record(d)
        a.append(c["crystal_a"]), b.append(c["crystal_b"]), dl.append(c["delayed"])
    a, b, dl = np.concatenate(a), np.concatenate(b), np.concatenate(dl)
    eff = cor.crystal_efficiencies(a, b, dl)
    h = sg.read_header(pathlib.Path(norm_dirs[0]) / "truth.hdr")
    scan = sum(sg.read(sg.read_header(pathlib.Path(d) / "truth.hdr"), "prompts")
               - sg.read(sg.read_header(pathlib.Path(d) / "truth.hdr"), "delayeds")
               for d in norm_dirs)
    prod = cor.efficiency_products(eff, h)
    geo = cor.geometric_factors(scan, prod, h, source_radius_mm)
    return cor.normalization(prod, geo), geo, eff


def randoms(run_dir, header):
    """The randoms of every bin of the run, from its singles, the paired singles left out."""
    record, c = run_record(run_dir)
    k = record["run"]["corrections"]
    seconds = (k["singles_last_ps"] - k["singles_first_ps"]) * 1e-12
    prompt = ~c["delayed"]
    paired = cor.fan_sums(c["crystal_a"][prompt], c["crystal_b"][prompt])
    return cor.randoms_from_singles(k["singles_per_crystal"], k["coincidence_window_ps"], seconds,
                                    header, in_coincidence=paired)


def scatter_shape(model_dir, geo):
    """A scatter model's shape per slice, in normalized units: the scatters of a simulation of the
    object on a perfect scanner, averaged over the views, divided by the geometric factors."""
    hm = sg.read_header(pathlib.Path(model_dir) / "truth.hdr")
    model = sg.read(hm, "scatters").sum(axis=1, keepdims=True) / hm.views
    g3 = geo[:, None, :]
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(g3 > 0, model / np.where(g3 > 0, g3, 1.0), 0.0)
