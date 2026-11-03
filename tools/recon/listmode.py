# SPDX-License-Identifier: MIT
"""The coincidences of MDQ-L1 list-mode files (docs/formats/mdq-l1.md), as numpy arrays.

The reader checks what the C++ reader checks: the magic numbers, the version, both CRC-32s of every
block (zlib's CRC is the same one, IEEE 802.3) and the sequence of blocks. A damaged file is an
error here, not a partial result: the corrections of Chapter 27 are computed once per run, and a
run with a hole in it needs a person, not a guess.
"""
import json
import pathlib
import zlib

import numpy as np

FILE_MAGIC = b"MDQL\r\n\x1a\n"
BLOCK_MAGIC = b"MDQB"
TAG_CRYSTAL = 0x7FFF
DELAYED_BIT = 0x8000
ENERGY_LSB_KEV = 1.0 / 32.0

# [snippet:record]
RECORD = np.dtype([("time_offset", "<u4"), ("crystal_a", "<u2"), ("crystal_b", "<u2"),
                   ("dt_ps", "<i4"), ("energy_a", "<u2"), ("energy_b", "<u2")])
# [/snippet:record]


class FormatError(ValueError):
    """A list-mode file that is not a valid MDQ-L1 file."""


def _u32(b, at):
    return int.from_bytes(b[at:at + 4], "little")


def read_file(path):
    """(metadata dict, coincidences dict of arrays) of one list-mode file.

    The arrays: time_ps (int64, the earlier single's time), crystal_a and crystal_b (int32, the
    earlier and the later single), delayed (bool), dt_ps (int32), energy_a_kev and energy_b_kev
    (float32). Tags are left out."""
    raw = pathlib.Path(path).read_bytes()
    if raw[:8] != FILE_MAGIC:
        raise FormatError(f"{path}: not an MDQ-L1 file")
    major = int.from_bytes(raw[8:10], "little")
    if major != 1:
        raise FormatError(f"{path}: version {major}, this reader reads 1")
    header_bytes, meta_bytes = _u32(raw, 12), _u32(raw, 16)
    if _u32(raw, header_bytes - 8) != zlib.crc32(raw[:header_bytes - 8]):
        raise FormatError(f"{path}: file header CRC")
    meta = json.loads(raw[32:32 + meta_bytes].decode("utf-8"))
    parts = []
    bases = []
    at, seq = header_bytes, 0
    while at < len(raw):
        h = raw[at:at + 32]
        if len(h) < 32 or h[:4] != BLOCK_MAGIC:
            raise FormatError(f"{path}: block {seq} at byte {at}: no block header")
        if _u32(h, 28) != zlib.crc32(h[:28]):
            raise FormatError(f"{path}: block {seq}: header CRC")
        if _u32(h, 4) != seq:
            raise FormatError(f"{path}: block {seq}: sequence {_u32(h, 4)}")
        n = _u32(h, 8)
        body = raw[at + 32:at + 32 + 16 * n]
        if len(body) != 16 * n or _u32(h, 24) != zlib.crc32(body):
            raise FormatError(f"{path}: block {seq}: records CRC")
        parts.append(np.frombuffer(body, dtype=RECORD))
        bases.append(np.full(n, int.from_bytes(h[16:24], "little", signed=True), dtype=np.int64))
        at += 32 + 16 * n
        seq += 1
    rec = np.concatenate(parts) if parts else np.zeros(0, dtype=RECORD)
    base = np.concatenate(bases) if bases else np.zeros(0, dtype=np.int64)
    a = rec["crystal_a"]
    event = (a & ~np.uint16(DELAYED_BIT)) != TAG_CRYSTAL
    rec, base = rec[event], base[event]
    a = rec["crystal_a"]
    return meta, {
        "time_ps": base + rec["time_offset"].astype(np.int64),
        "crystal_a": (a & ~np.uint16(DELAYED_BIT)).astype(np.int32),
        "crystal_b": rec["crystal_b"].astype(np.int32),
        "delayed": (a & np.uint16(DELAYED_BIT)) != 0,
        "dt_ps": rec["dt_ps"].astype(np.int32),
        "energy_a_kev": rec["energy_a"].astype(np.float32) * np.float32(ENERGY_LSB_KEV),
        "energy_b_kev": rec["energy_b"].astype(np.float32) * np.float32(ENERGY_LSB_KEV),
    }


def read_run(record_path):
    """(run record dict, coincidences) of a whole run, from its .run.json: every file it lists, in
    order, joined."""
    record_path = pathlib.Path(record_path)
    record = json.loads(record_path.read_text())
    parts = [read_file(record_path.parent / f)[1] for f in record["files"]]
    if not parts:
        raise FormatError(f"{record_path}: the run has no files")
    joined = {k: np.concatenate([p[k] for p in parts]) for k in parts[0]}
    return record, joined
