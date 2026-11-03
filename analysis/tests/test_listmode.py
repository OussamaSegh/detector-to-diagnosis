# SPDX-License-Identifier: MIT
"""The memory-mapped list-mode reader against an independent writer (tests/mdql.py)."""
from __future__ import annotations

import pathlib

import mdql
import numpy as np
import pytest
from conftest import synthetic

from minidaq_analysis.listmode import Coincidences, FormatError, ListModeFile, Run


def write(tmp_path: pathlib.Path, data: bytes, name: str = "f.mdql") -> pathlib.Path:
    p = tmp_path / name
    p.write_bytes(data)
    return p


def test_reads_back_what_was_written(tmp_path: pathlib.Path, rng: np.random.Generator) -> None:
    # REQ: SRS-ANA-001
    r = synthetic(rng, 10_000)
    with ListModeFile(write(tmp_path, mdql.file_bytes(r, block_records=1000))) as f:
        c = f.coincidences()
        assert f.metadata["scanner"]["crystals_per_ring"] == 576
        assert f.records_total == 10_000 and f.ends_run
    assert len(c) == 10_000
    np.testing.assert_array_equal(c.time_ps, r["t"])
    np.testing.assert_array_equal(c.crystal_a, r["a"] & 0x7FFF)
    np.testing.assert_array_equal(c.delayed, (r["a"] & 0x8000) != 0)
    np.testing.assert_array_equal(c.dt_ps, r["dt"])
    np.testing.assert_array_equal(c.energy_b_kev, r["eb"] / 32.0)


@pytest.mark.parametrize("chunk", [1, 999, 1000, 1001, 4096, 1 << 20])
def test_every_chunk_size_gives_the_same_coincidences(tmp_path: pathlib.Path,
                                                      rng: np.random.Generator,
                                                      chunk: int) -> None:
    # REQ: SRS-ANA-001
    r = synthetic(rng, 5_000)
    path = write(tmp_path, mdql.file_bytes(r, block_records=1000))
    with ListModeFile(path) as f:
        whole = f.coincidences()
        parts = [c for c, _ in f.chunks(chunk)]
    joined = Coincidences.concatenate(parts)
    for field in ("time_ps", "crystal_a", "crystal_b", "delayed", "dt_ps", "energy_a_kev"):
        np.testing.assert_array_equal(getattr(joined, field), getattr(whole, field))
    # A chunk holds whole blocks and no more records than asked, unless one block is larger.
    assert all(len(p) <= max(chunk, 1000) for p in parts)


def test_skips_and_counts_tags(tmp_path: pathlib.Path, rng: np.random.Generator) -> None:
    # REQ: SRS-ANA-001
    r = mdql.concat(synthetic(rng, 100), mdql.tag(5), mdql.tag(10**9, kind=1, value=3))
    with ListModeFile(write(tmp_path, mdql.file_bytes(r))) as f:
        (c, tags), = list(f.chunks())
    assert len(c) == 100 and tags == 2


def test_a_file_with_no_coincidences_is_read(tmp_path: pathlib.Path) -> None:
    # REQ: SRS-ANA-001
    empty = mdql.records([], [], [], [], [], [])
    with ListModeFile(write(tmp_path, mdql.file_bytes(empty))) as f:
        assert len(f.coincidences()) == 0


def damaged(data: bytes, at: int, value: int | None = None) -> bytes:
    b = bytearray(data)
    b[at] = (b[at] ^ 0x01) if value is None else value
    return bytes(b)


@pytest.mark.parametrize("what, edit, message", [
    ("magic", lambda d: damaged(d, 0), "not an MDQ-L1 file"),
    ("version", lambda d: damaged(d, 8, 2), "format version 2"),
    ("metadata", lambda d: damaged(d, 40), "file header CRC"),
    ("block header", lambda d: damaged(d, len(mdql.file_bytes(mdql.records(
        [], [], [], [], [], []), closing=None)) + 5), "no intact block header"),
    ("records", lambda d: damaged(d, len(d) - 100), "records CRC"),
    ("cut", lambda d: d[:-50], "do not fit in the file"),
    ("no closing block", lambda d: d[:-32], "no closing block"),
])
def test_refuses_a_file_that_is_not_complete_and_intact(tmp_path: pathlib.Path,
                                                        rng: np.random.Generator, what: str,
                                                        edit: object, message: str) -> None:
    # REQ: SRS-ANA-001
    del what
    good = mdql.file_bytes(synthetic(rng, 3000), block_records=1000)
    assert callable(edit)
    path = write(tmp_path, edit(good))
    with pytest.raises(FormatError, match=message):
        ListModeFile(path)


def test_without_verification_a_damaged_payload_is_not_noticed_at_open(
        tmp_path: pathlib.Path, rng: np.random.Generator) -> None:
    # REQ: SRS-ANA-001
    good = mdql.file_bytes(synthetic(rng, 3000), block_records=1000)
    path = write(tmp_path, damaged(good, len(good) - 100))
    with ListModeFile(path, verify=False) as f:  # the cost of not verifying: a quiet error
        assert f.records_total == 3000


def test_refuses_data_after_the_closing_block_and_a_wrong_sequence(
        tmp_path: pathlib.Path, rng: np.random.Generator) -> None:
    # REQ: SRS-ANA-001
    r = synthetic(rng, 10)
    good = mdql.file_bytes(r)
    with pytest.raises(FormatError, match="data after the closing block"):
        ListModeFile(write(tmp_path, good + good[-32:], "a.mdql"))
    # Two blocks with sequence 0: the second block of a file written in two halves.
    first = mdql.file_bytes(r, closing=None)
    head = len(mdql.file_bytes(mdql.records([], [], [], [], [], []), closing=None))
    twice = first + first[head:] + mdql.file_bytes(mdql.records([], [], [], [], [], []))[head:]
    with pytest.raises(FormatError, match="sequence number 0"):
        ListModeFile(write(tmp_path, twice, "b.mdql"))


def test_a_run_joins_its_files_in_order(tmp_path: pathlib.Path, rng: np.random.Generator) -> None:
    # REQ: SRS-ANA-001
    r = synthetic(rng, 3000, seconds=3.0)
    cut = [0, 1000, 2000, 3000]
    parts = [{k: v[cut[i]:cut[i + 1]] for k, v in r.items()} for i in range(3)]
    run = Run(mdql.write_run(tmp_path, parts))
    c = run.coincidences()
    np.testing.assert_array_equal(c.time_ps, r["t"])


def test_a_run_whose_files_end_wrongly_is_refused(tmp_path: pathlib.Path,
                                                  rng: np.random.Generator) -> None:
    # REQ: SRS-ANA-001
    r = synthetic(rng, 100)
    record = mdql.write_run(tmp_path, [r, r])
    # The first file ends the run: the second would be data after the end of the run.
    first = tmp_path / "t-test-0000.mdql"
    first.write_bytes(mdql.file_bytes(r, closing=1))
    with pytest.raises(FormatError, match="closing flag"):
        Run(record).coincidences()


def test_the_record_must_be_a_run_record(tmp_path: pathlib.Path) -> None:
    # REQ: SRS-ANA-001
    p = tmp_path / "x.run.json"
    p.write_text('{"format": "something else", "files": ["a"]}')
    with pytest.raises(FormatError, match="not an MDQ-L1 run record"):
        Run(p)
