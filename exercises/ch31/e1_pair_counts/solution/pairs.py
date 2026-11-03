# SPDX-License-Identifier: MIT
"""Exercise 31.1: coincidences per crystal pair, from an MDQ-L1 file through a memory map."""
import numpy as np

RECORD = np.dtype([("time_offset", "<u4"), ("crystal_a", "<u2"), ("crystal_b", "<u2"),
                   ("dt_ps", "<i4"), ("energy_a", "<u2"), ("energy_b", "<u2")])
DELAYED_BIT = 0x8000
TAG_CRYSTAL = 0x7FFF


def pair_counts(path, crystals=18432):
    """(keys, counts): one key per crystal pair with at least one prompt coincidence, sorted, and
    the number of prompts of each pair. A pair's key is lower id * crystals + higher id."""
    m = np.memmap(path, dtype=np.uint8, mode="r")  # nothing is read until it is touched
    header_bytes = int(m[12:16].view("<u4")[0])
    keys_parts = []
    at = header_bytes
    while at < m.size:
        n = int(m[at + 8:at + 12].view("<u4")[0])
        # A view of the mapped bytes as records: no copy until the arithmetic below.
        r = m[at + 32:at + 32 + 16 * n].view(RECORD)
        a = r["crystal_a"]
        prompt = (a & DELAYED_BIT) == 0
        prompt &= a != TAG_CRYSTAL  # a tag: crystal_a 0x7FFF with bit 15 clear
        a = a[prompt].astype(np.int64)
        b = r["crystal_b"][prompt].astype(np.int64)
        keys_parts.append(np.minimum(a, b) * crystals + np.maximum(a, b))
        at += 32 + 16 * n
    keys = np.concatenate(keys_parts) if keys_parts else np.zeros(0, dtype=np.int64)
    k, c = np.unique(keys, return_counts=True)
    return k, c.astype(np.int64)
