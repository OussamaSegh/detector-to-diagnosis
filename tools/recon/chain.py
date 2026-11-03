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
