# SPDX-License-Identifier: MIT
"""Exercise 37.1: take the patient out of an image header (solution)."""
import datetime
import hashlib
import hmac

KEEP = ["Modality", "SOPClassUID", "Rows", "Columns", "PixelSpacing", "SliceThickness",
        "ImagePositionPatient", "ImageOrientationPatient", "PatientPosition", "Units",
        "RescaleSlope", "RescaleIntercept", "SeriesTime", "AcquisitionTime", "DecayCorrection",
        "CorrectedImage", "RadionuclideHalfLife", "ImageIndex"]
PSEUDONYMS = ["PatientName", "PatientID"]
DATES = ["StudyDate", "SeriesDate", "AcquisitionDate", "ContentDate"]
UIDS = ["StudyInstanceUID", "SeriesInstanceUID", "SOPInstanceUID", "FrameOfReferenceUID"]


def _mac(key, text):
    k = key.encode() if isinstance(key, str) else key
    return hmac.new(k, text.encode(), hashlib.sha256).digest()


def deidentify(header, key):
    """A new header with only the listed keywords: kept, pseudonymized, shifted or remapped."""
    out = {k: header[k] for k in KEEP if k in header}
    patient = header.get("PatientID", "")
    mac = _mac(key, "patient:" + patient)
    if "PatientName" in header:
        out["PatientName"] = "ANON^" + mac.hex()[:10]
    if "PatientID" in header:
        out["PatientID"] = "ANON-" + mac.hex()[:10]
    shift = datetime.timedelta(days=1 + int.from_bytes(mac[-4:], "big") % 365)
    for k in DATES:
        if k in header:
            day = datetime.datetime.strptime(header[k], "%Y%m%d").date()
            out[k] = (day - shift).strftime("%Y%m%d")
    for k in UIDS:
        if k in header:
            out[k] = "2.25." + str(int.from_bytes(_mac(key, "uid:" + header[k])[:16], "big"))
    return out
