# SPDX-License-Identifier: MIT
"""Exercise 35.2: the attributes that place a slice in the patient."""
import numpy as np


def export_rows(image):
    """The array as written to the file."""
    return image


def plane(shape, row_mm, col_mm, z_mm, position):
    rows, cols = shape
    gx, gy = -(cols - 1) / 2.0 * col_mm, -(rows - 1) / 2.0 * row_mm
    return {"ImagePositionPatient": [gx, -gy, z_mm],
            "ImageOrientationPatient": [1.0, 0.0, 0.0, 0.0, 1.0, 0.0],
            "PixelSpacing": [col_mm, row_mm]}


def to_patient(ipp, iop, spacing, r, c):
    ipp, iop = np.asarray(ipp, float), np.asarray(iop, float)
    return ipp + c * spacing[0] * iop[:3] + r * spacing[1] * iop[3:]
