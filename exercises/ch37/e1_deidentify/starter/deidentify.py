# SPDX-License-Identifier: MIT
"""Exercise 37.1: take the patient out of an image header (starter)."""

KEEP = ["Modality", "SOPClassUID", "Rows", "Columns", "PixelSpacing", "SliceThickness",
        "ImagePositionPatient", "ImageOrientationPatient", "PatientPosition", "Units",
        "RescaleSlope", "RescaleIntercept", "SeriesTime", "AcquisitionTime", "DecayCorrection",
        "CorrectedImage", "RadionuclideHalfLife", "ImageIndex"]
PSEUDONYMS = ["PatientName", "PatientID"]
DATES = ["StudyDate", "SeriesDate", "AcquisitionDate", "ContentDate"]
UIDS = ["StudyInstanceUID", "SeriesInstanceUID", "SOPInstanceUID", "FrameOfReferenceUID"]


def deidentify(header, key):
    out = dict(header)
    out.pop("PatientName", None)
    out.pop("PatientID", None)
    return out
