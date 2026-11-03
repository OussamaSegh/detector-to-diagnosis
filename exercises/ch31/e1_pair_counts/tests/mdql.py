# SPDX-License-Identifier: MIT
"""A small MDQ-L1 writer for the tests of Exercise 31.1, from docs/formats/mdq-l1.md (the same as
analysis/tests/mdql.py)."""
from __future__ import annotations

import json
import pathlib
import struct
import zlib
from typing import Any

import numpy as np
import numpy.typing as npt

SCANNER = {"model": "MiniDAQ reference", "crystals_per_ring": 576, "crystal_rings": 32,
           "inner_radius_mm": 150.0, "axial_pitch_mm": 3.2}


def metadata(delayed_window_ps: int = 100_000) -> dict[str, Any]:
    return {"format": "MDQ-L1", "software": "tests", "created_utc": "2026-11-03T08:00:00Z",
            "simulated": True, "file": {"segment": 0, "run_name": "test"}, "scanner": SCANNER,
            "records": {"time_unit": "ps", "energy_lsb_kev": 0.03125,
                        "delayed_window_ps": delayed_window_ps, "coincidence_window_ps": 4000}}


def records(time_ps: npt.ArrayLike, crystal_a: npt.ArrayLike, crystal_b: npt.ArrayLike,
            dt_ps: npt.ArrayLike, energy_a_kev: npt.ArrayLike, energy_b_kev: npt.ArrayLike,
            delayed: npt.ArrayLike | None = None) -> dict[str, npt.NDArray[Any]]:
    t = np.asarray(time_ps, dtype=np.int64)
    a = np.asarray(crystal_a, dtype=np.int64)
    if delayed is not None:
        a = a | np.where(np.asarray(delayed, dtype=bool), 0x8000, 0)
    return {"t": t, "a": a, "b": np.asarray(crystal_b, dtype=np.int64),
            "dt": np.asarray(dt_ps, dtype=np.int64),
            "ea": np.clip(np.rint(np.asarray(energy_a_kev) * 32), 0, 65535).astype(np.int64),
            "eb": np.clip(np.rint(np.asarray(energy_b_kev) * 32), 0, 65535).astype(np.int64)}


def tag(time_ps: int, kind: int = 2, value: int = 0) -> dict[str, npt.NDArray[Any]]:
    one = np.array([0], dtype=np.int64)
    return {"t": np.array([time_ps]), "a": one + 0x7FFF, "b": one + kind, "dt": one + value,
            "ea": one, "eb": one}


def concat(*parts: dict[str, npt.NDArray[Any]]) -> dict[str, npt.NDArray[Any]]:
    out = {k: np.concatenate([p[k] for p in parts]) for k in parts[0]}
    order = np.argsort(out["t"], kind="stable")
    return {k: v[order] for k, v in out.items()}


def _block(seq: int, recs: list[bytes], base: int, flags: int = 0) -> bytes:
    payload = b"".join(recs)
    head = struct.pack("<4sIIIqI", b"MDQB", seq, len(recs), flags, base, zlib.crc32(payload))
    return head + struct.pack("<I", zlib.crc32(head)) + payload


def file_bytes(r: dict[str, npt.NDArray[Any]], block_records: int = 4096,
               closing: int | None = 1, meta: dict[str, Any] | None = None) -> bytes:
    m = json.dumps(meta or metadata()).encode("utf-8")
    pad = (len(m) + 7) & ~7
    head = struct.pack("<8sHHIIIII", b"MDQL\r\n\x1a\n", 1, 0, 40 + pad, len(m), 0, 16, 0)
    head += m + b"\0" * (pad - len(m))
    out = [head + struct.pack("<II", zlib.crc32(head), 0)]
    seq, i, n = 0, 0, r["t"].size
    while i < n:
        base = int(r["t"][i])
        recs: list[bytes] = []
        while i < n and len(recs) < block_records and int(r["t"][i]) - base < 2**32 and (
                not recs or r["t"][i] >= r["t"][i - 1]):
            recs.append(struct.pack("<IHHiHH", int(r["t"][i]) - base, int(r["a"][i]),
                                    int(r["b"][i]), int(r["dt"][i]), int(r["ea"][i]),
                                    int(r["eb"][i])))
            i += 1
        out.append(_block(seq, recs, base))
        seq += 1
    if closing is not None:
        out.append(_block(seq, [], 0, closing))
    return b"".join(out)


def write_run(directory: pathlib.Path, parts: list[dict[str, npt.NDArray[Any]]],
              run_record_extra: dict[str, Any] | None = None, block_records: int = 4096,
              delayed_window_ps: int = 100_000) -> pathlib.Path:
    """One file per part, the last ending the run, and the run record; returns its path."""
    directory.mkdir(parents=True, exist_ok=True)
    names = []
    for k, part in enumerate(parts):
        name = f"t-test-{k:04d}.mdql"
        closing = 1 if k == len(parts) - 1 else 2
        meta = metadata(delayed_window_ps)
        (directory / name).write_bytes(file_bytes(part, block_records, closing, meta))
        names.append(name)
    record = {"format": "MDQ-L1 run record", "run_name": "test", "files": names,
              "sink_counters": {}, "run": {}}
    if run_record_extra:
        record["run"].update(run_record_extra)
    path = directory / "t-test.run.json"
    path.write_text(json.dumps(record))
    return path
