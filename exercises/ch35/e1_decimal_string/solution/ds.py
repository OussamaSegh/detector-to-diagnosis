# SPDX-License-Identifier: MIT
"""Exercise 35.1: a Decimal String, and a slice stored with the slope as written."""
import math

import numpy as np


def format_ds(x):
    """The text of a DS for x: at most 16 characters, as many digits as fit."""
    x = float(x)
    if not math.isfinite(x):
        raise ValueError(f"a DS cannot hold {x}")
    for digits in range(16, 0, -1):
        s = f"{x:.{digits}g}"
        if len(s) <= 16:
            return s
    raise ValueError(f"{x} does not fit in a DS")


def quantize(plane):
    """(stored uint16 values, slope text) of a plane of values that are not negative."""
    peak = float(plane.max())
    text = format_ds(peak / 65535 if peak > 0 else 1.0)
    slope = float(text)                     # what every reader of the file will use
    stored = np.clip(np.rint(plane / slope), 0, 65535).astype(np.uint16)
    return stored, text
