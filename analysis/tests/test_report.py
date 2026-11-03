# SPDX-License-Identifier: MIT
"""The QC report end to end, on synthetic runs with known faults, and on the simulator."""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import mdql
import numpy as np
import pytest
from conftest import synthetic

from minidaq_analysis.__main__ import main
from minidaq_analysis.report import write_report

N = 200_000


def run_of(tmp_path: pathlib.Path, r: dict[str, np.ndarray], prompts: int | None = None,
           ) -> pathlib.Path:
    delayed = (r["a"] & 0x8000) != 0
    n = int(np.count_nonzero(~delayed)) if prompts is None else prompts
    return mdql.write_run(tmp_path / "run", [r], {"corrections": {"prompts": n}})


def checks(report: dict) -> dict[str, bool]:  # type: ignore[type-arg]
    return {c["name"]: c["passed"] for c in report["checks"]}


def test_a_good_run_passes_and_says_where_it_came_from(tmp_path: pathlib.Path,
                                                       rng: np.random.Generator) -> None:
    # REQ: SRS-ANA-005
    record = run_of(tmp_path, synthetic(rng, N, seconds=2.0))
    out = tmp_path / "qc"
    assert main([str(record), str(out)]) == 0
    report = json.loads((out / "report.json").read_text())
    assert report["passed"] and all(checks(report).values())
    assert report["run"]["prompts"] + report["run"]["delayeds"] == N
    prov = json.loads((out / "provenance.json").read_text())
    names = [f["path"] for f in prov["inputs"]["files"]]
    assert names == ["t-test-0000.mdql", "t-test.run.json"]
    assert prov["inputs_id"] == report["inputs_id"]
    for f in ("report.md", "energy.png", "timing.png", "rate.png"):
        assert (out / f).stat().st_size > 1000
    assert "PASS" in (out / "report.md").read_text()


def test_a_worse_detector_fails_its_limits(tmp_path: pathlib.Path,
                                           rng: np.random.Generator) -> None:
    # REQ: SRS-ANA-005
    record = run_of(tmp_path, synthetic(rng, N, ctr_ps=450.0, resolution=0.16))
    out = tmp_path / "qc"
    assert main([str(record), str(out)]) == 1
    c = checks(json.loads((out / "report.json").read_text()))
    assert not c["coincidence time resolution (FWHM)"]
    assert not c["energy resolution (FWHM/E)"]
    assert c["photopeak position"]


def test_a_lost_block_and_a_wrong_count_are_found(tmp_path: pathlib.Path,
                                                  rng: np.random.Generator) -> None:
    # REQ: SRS-ANA-005
    r = synthetic(rng, N, seconds=2.0)
    # Remove 4,000 consecutive coincidences (a lost stretch of 40 ms); keep the recorded count.
    keep = np.ones(N, dtype=bool)
    keep[100_000:104_000] = False
    full = int(np.count_nonzero((r["a"] & 0x8000) == 0))
    record = run_of(tmp_path, {k: v[keep] for k, v in r.items()}, prompts=full)
    report = write_report(record, tmp_path / "qc")
    c = checks(report)
    assert not c["no dip in the prompt rate (p)"]
    assert not c["prompts in the files minus prompts recorded"]


def test_a_protocol_file_sets_the_limits(tmp_path: pathlib.Path,
                                         rng: np.random.Generator) -> None:
    # REQ: SRS-ANA-005
    from minidaq_analysis.report import DEFAULT_PROTOCOL
    strict = tmp_path / "strict.toml"
    strict.write_text(DEFAULT_PROTOCOL.replace("ctr_max_ps = 400.0", "ctr_max_ps = 250.0"))
    record = run_of(tmp_path, synthetic(rng, N))
    report = write_report(record, tmp_path / "qc", strict)
    assert not checks(report)["coincidence time resolution (FWHM)"]
    prov = json.loads((tmp_path / "qc" / "provenance.json").read_text())
    assert any(f["path"].endswith("strict.toml") for f in prov["inputs"]["files"])


def test_a_damaged_run_is_an_error_not_a_report(tmp_path: pathlib.Path,
                                                rng: np.random.Generator) -> None:
    # REQ: SRS-ANA-005
    record = run_of(tmp_path, synthetic(rng, 10_000))
    f = record.parent / "t-test-0000.mdql"
    data = bytearray(f.read_bytes())
    data[-100] ^= 1
    f.write_bytes(bytes(data))
    assert main([str(record), str(tmp_path / "qc")]) == 2
    assert not (tmp_path / "qc" / "report.json").exists()


@pytest.mark.slow
@pytest.mark.skipif(not os.environ.get("MINIDAQ_APPS"), reason="MINIDAQ_APPS not set")
def test_a_simulated_point_source_passes_with_the_simulators_resolutions(
        tmp_path: pathlib.Path) -> None:
    """minidaq_sim's detector: 12% energy resolution, 300 ps CTR (the singles' blur; the depth
    of interaction adds about 1%, Chapter 31)."""
    # REQ: SRS-ANA-005
    sim = pathlib.Path(os.environ["MINIDAQ_APPS"]) / "minidaq_sim"
    subprocess.run([str(sim), "--source", "point", "--phantom", "0", "--activity", "1e6",
                    "--seconds", "1", "--seed", "31", "--listmode", str(tmp_path)],
                   check=True, stdout=subprocess.DEVNULL)
    record = next(tmp_path.glob("*.run.json"))
    out = tmp_path / "qc"
    done = subprocess.run([sys.executable, "-m", "minidaq_analysis", str(record), str(out)],
                          capture_output=True, text=True)
    assert done.returncode == 0, done.stdout + done.stderr
    report = json.loads((out / "report.json").read_text())
    fits = report["fits"]
    sigma = fits["photopeak"]["parameters"]["sigma"]
    mean = fits["photopeak"]["parameters"]["mean"]
    assert 2.3548 * sigma / mean == pytest.approx(0.12, rel=0.03)
    assert 2.3548 * fits["timing"]["parameters"]["sigma"] == pytest.approx(305.0, rel=0.03)
