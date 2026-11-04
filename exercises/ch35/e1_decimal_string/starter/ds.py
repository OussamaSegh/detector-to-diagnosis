# SPDX-License-Identifier: MIT
"""Exercise 35.1: a Decimal String, and a slice stored with the slope as written."""
import numpy as np


def format_ds(x):
    """The text of a DS for x: at most 16 characters, as many digits as fit."""
    return f"{x:.6f}"


def quantize(plane):
    """(stored uint16 values, slope text) of a plane of values that are not negative."""
    peak = float(plane.max())
    slope = peak / 65535 if peak > 0 else 1.0
    stored = np.rint(plane / slope).astype(np.uint16)
    return stored, format_ds(slope)
