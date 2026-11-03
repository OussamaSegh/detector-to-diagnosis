# SPDX-License-Identifier: MIT
"""The packed singles of a words file (minidaq_sim --words, the readout format of Chapter 9).

Each word is 64 bits, little-endian: crystal (15 bits) | energy code (11 bits) | time (38 bits of
5 ps). The time counter wraps every 1.374 s; read() unwraps it, assuming, as the decoder does, that
consecutive words are less than half a wrap apart.
"""
import numpy as np

TIME_BITS = 38
ENERGY_BITS = 11
CRYSTAL_BITS = 15
TIME_LSB_PS = 5
ENERGY_LSB_KEV = 0.5
MAX_CODE = (1 << ENERGY_BITS) - 1
NUM_CRYSTALS = 384 * 48


def unpack(words):
    """(crystal, energy code, time in ps) of an array of uint64 words, time unwrapped."""
    w = np.asarray(words, dtype=np.uint64)
    crystal_mask = np.uint64((1 << CRYSTAL_BITS) - 1)
    crystal = ((w >> np.uint64(TIME_BITS + ENERGY_BITS)) & crystal_mask).astype(np.int64)
    code = ((w >> np.uint64(TIME_BITS)) & np.uint64(MAX_CODE)).astype(np.int64)
    t = (w & np.uint64((1 << TIME_BITS) - 1)).astype(np.int64)
    # A step back by more than half the counter's range is a wrap.
    half = 1 << (TIME_BITS - 1)
    step = np.diff(t, prepend=t[:1])
    wraps = np.cumsum(step < -half) - np.cumsum(step > half)
    t = (t + wraps * (1 << TIME_BITS)) * TIME_LSB_PS
    return crystal, code, t


def read(path):
    """The singles of a words file: crystal, energy code and time in ps, as numpy arrays."""
    words = np.fromfile(path, dtype="<u8")
    crystal, code, t = unpack(words)
    keep = crystal < NUM_CRYSTALS  # the decoder drops these too
    return crystal[keep], code[keep], t[keep]
