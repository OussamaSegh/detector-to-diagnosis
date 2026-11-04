# SPDX-License-Identifier: MIT
"""Exercise 35.2: the attributes that place a slice in the patient."""
import numpy as np

# gantry (x, y, z) -> LPS, for a patient on their back
SIGNS = {"HFS": (1, -1, 1), "FFS": (-1, -1, -1)}


def export_rows(image):
    """The array as written to the file: the first row is the highest gantry y."""
    return image[::-1, :]


def plane(shape, row_mm, col_mm, z_mm, position):
    if position not in SIGNS:
        raise ValueError(f"patient position {position!r} is not supported")
    sx, sy, sz = SIGNS[position]
    rows, cols = shape
    gx = -(cols - 1) / 2.0 * col_mm       # first column: the smallest gantry x
    gy = (rows - 1) / 2.0 * row_mm        # first exported row: the largest gantry y
    return {"ImagePositionPatient": [sx * gx + 0.0, sy * gy + 0.0, sz * z_mm + 0.0],
            "ImageOrientationPatient": [float(sx), 0.0, 0.0, 0.0, float(-sy), 0.0],
            "PixelSpacing": [row_mm, col_mm]}


def to_patient(ipp, iop, spacing, r, c):
    """Pixel Spacing is [between rows, between columns]: a step along a row (next column) is
    spacing[1], a step down a column (next row) is spacing[0]."""
    ipp, iop = np.asarray(ipp, float), np.asarray(iop, float)
    return ipp + c * spacing[1] * iop[:3] + r * spacing[0] * iop[3:]
