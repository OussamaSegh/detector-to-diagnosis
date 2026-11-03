# SPDX-License-Identifier: MIT
"""Exercise 31.1: coincidences per crystal pair, from an MDQ-L1 file through a memory map."""
import numpy as np

RECORD = np.dtype([("time_offset", "<u4"), ("crystal_a", "<u2"), ("crystal_b", "<u2"),
                   ("dt_ps", "<i4"), ("energy_a", "<u2"), ("energy_b", "<u2")])


def pair_counts(path, crystals=18432):
    """(keys, counts): one key per crystal pair with at least one prompt coincidence, sorted, and
    the number of prompts of each pair. A pair's key is lower id * crystals + higher id."""
    raw = np.fromfile(path, dtype=np.uint8)
    header_bytes = int(raw[12:16].view("<u4")[0])
    records = []
    at = header_bytes
    while at < raw.size:
        n = int(raw[at + 8:at + 12].view("<u4")[0])
        records.append(raw[at + 32:at + 32 + 16 * n].view(RECORD))
        at += 32 + 16 * n
    r = np.concatenate(records)
    keys = r["crystal_a"].astype(np.int64) * crystals + r["crystal_b"]
    return np.unique(keys, return_counts=True)
