# SPDX-License-Identifier: MIT
"""The check of an output array that a caller gives to the projector, so that the projection
is written into it in place (forward(image, out=...)). The C++ side writes doubles through a
raw pointer, so the array must be what it will be treated as; anything else is refused with a
reason, never written with the wrong layout."""
import numpy as np


def writable_out(out, shape):
    """`out` itself, if the projector can write a result of `shape` into it; else ValueError."""
    if not isinstance(out, np.ndarray):
        raise ValueError(f"out must be a NumPy array, got {type(out).__name__}")
    # Equivalence, not identity: an unpickled array has a float64 dtype object of its own.
    # == also compares the byte order, so a big-endian array is refused.
    if out.dtype != np.dtype(np.float64):
        raise ValueError(f"out must be float64 in native byte order, got {out.dtype.str}")
    if out.shape != tuple(shape):
        raise ValueError(f"out must have shape {tuple(shape)}, got {out.shape}")
    if not out.flags.c_contiguous:
        raise ValueError("out must be C-contiguous")
    if not out.flags.writeable:
        raise ValueError("out is read-only")
    return out
