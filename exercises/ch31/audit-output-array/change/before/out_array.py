# SPDX-License-Identifier: MIT
"""The check of an output array that a caller gives to the projector, so that the projection
is written into it in place (forward(image, out=...)). The C++ side writes doubles through a
raw pointer, so the array must be what it will be treated as; anything else is refused with a
reason, never written with the wrong layout."""
import numpy as np


def writable_out(out, shape):
    """`out` itself, if the projector can write a result of `shape` into it; else ValueError."""
    raise NotImplementedError
