# SPDX-License-Identifier: MIT
"""A PET Image series from a reconstructed image (Chapter 35).

    datasets = series(image, order, acquisition, reconstruction)
    problems = check_series(datasets)      # [] when the series may be sent
    paths = write_series(datasets, directory)

The image is a numpy array [slice, row, column] in MiniDAQ's gantry frame, as tools/recon makes
it: x along a row to the right seen from the front of the gantry, y up (the row index grows with
y), z along the axis into the gantry, pixel centers symmetric about the axis. The order holds the
patient and study attributes, which come from the hospital (a worklist or the console), never
from MiniDAQ; the acquisition, the radiopharmaceutical and the scanner; the reconstruction, how
the image was made and what it is in.

One PET Image object (SOP class 1.2.840.10008.5.1.4.1.1.128) per slice, with the modules the PET
Image IOD makes mandatory (part 3, A.21.3): Patient, General Study, General Series, PET Series,
PET Isotope, NM/PET Patient Orientation, Frame of Reference, General Equipment, General
Acquisition, General Image, Image Plane, Image Pixel, PET Image and SOP Common.

The checks refuse what would make a reader file the series under the wrong patient, place it
wrong or read wrong values: a missing patient ID or study UID, a patient position the mapping does
not know, a value that is not finite. check_series checks what a series must be before it leaves:
every type 1 attribute present and not empty, every type 2 present, one patient, study, series
and frame of reference for all instances, distinct instances, one image index per slice.
"""
import datetime
import hashlib
import json
import math
import pathlib

import numpy as np

from . import encode, uid
from .encode import Dataset, DicomError, format_ds

SOP_CLASS = uid.PET_IMAGE_STORAGE

# Gantry (x, y, z) to the patient coordinate system of DICOM (LPS: x to the patient's left, y to
# the posterior, z to the head), for a patient lying on their back. Head first: the patient's
# left is on the right seen from the front, the head goes in first, and up is anterior.
# assumption: confirm with team the gantry frame of the scanner and the positions it supports.
POSITIONS = {"HFS": (1, -1, 1), "FFS": (-1, -1, -1)}
GANTRY_RELATION = {"HFS": ("102540008", "SCT", "headfirst"),
                   "FFS": ("102541007", "SCT", "feet-first")}
RECUMBENT = ("102538003", "SCT", "recumbent")
SUPINE = ("40199007", "SCT", "supine")

# Physical data of the radionuclides the export knows (verify: against the scanner's own table,
# which the dose calibrator and the decay correction share).
RADIONUCLIDES = {"F18": {"half_life_s": 6586.2, "positron_fraction": 0.9686,
                         "code": ("77004003", "SCT", "^18^Fluorine")}}
RADIOPHARMACEUTICALS = {"FDG": ("35321007", "SCT", "Fluorodeoxyglucose F^18^")}
UNITS = {"BQML", "CNTS", "PROPCNTS"}
CORRECTIONS = {"NORM", "DTIM", "ATTN", "SCAT", "DECY", "RAN", "DCAL"}
DECAY = {"NONE", "START"}

# [snippet:required]
TYPE1 = ["SOPClassUID", "SOPInstanceUID", "StudyInstanceUID", "SeriesInstanceUID", "Modality",
         "FrameOfReferenceUID", "SeriesDate", "SeriesTime", "Units", "CountsSource", "SeriesType",
         "DecayCorrection", "NumberOfSlices", "ImageType", "SamplesPerPixel",
         "PhotometricInterpretation", "Rows", "Columns", "BitsAllocated", "BitsStored", "HighBit",
         "PixelRepresentation", "PixelSpacing", "ImageOrientationPatient", "ImagePositionPatient",
         "RescaleIntercept", "RescaleSlope", "FrameReferenceTime", "ImageIndex", "PixelData"]
TYPE2 = ["PatientName", "PatientID", "PatientBirthDate", "PatientSex", "StudyDate", "StudyTime",
         "ReferringPhysicianName", "StudyID", "AccessionNumber", "SeriesNumber", "Manufacturer",
         "PositionReferenceIndicator", "InstanceNumber", "SliceThickness", "CorrectedImage",
         "CollimatorType", "RadiopharmaceuticalInformationSequence",
         "PatientOrientationCodeSequence", "PatientGantryRelationshipCodeSequence",
         "AcquisitionDate", "AcquisitionTime", "ActualFrameDuration"]
SHARED = ["PatientName", "PatientID", "PatientBirthDate", "PatientSex", "StudyInstanceUID",
          "AccessionNumber", "SeriesInstanceUID", "FrameOfReferenceUID", "SeriesDate",
          "SeriesTime", "Units", "DecayCorrection", "NumberOfSlices", "Rows", "Columns"]
# [/snippet:required]


def _code(value, scheme, meaning):
    return Dataset().set("CodeValue", value).set("CodingSchemeDesignator", scheme) \
                    .set("CodeMeaning", meaning)


def _when(text, what):
    """An aware datetime from ISO 8601 text with an offset; a time without one is refused,
    because a DICOM time without a time zone means local time of a place the file does not
    name."""
    try:
        t = datetime.datetime.fromisoformat(text)
    except (TypeError, ValueError):
        raise DicomError(f"{what}: {text!r} is not an ISO 8601 time") from None
    if t.utcoffset() is None:
        raise DicomError(f"{what}: {text!r} has no UTC offset")
    return t


def _da(t):
    return t.strftime("%Y%m%d")


def _tm(t):
    return t.strftime("%H%M%S.%f")


def _offset(t):
    minutes = int(t.utcoffset().total_seconds() // 60)
    sign = "+" if minutes >= 0 else "-"
    return f"{sign}{abs(minutes) // 60:02d}{abs(minutes) % 60:02d}"


def check_order(order):
    """Refuse an order without the identifiers that file a series under its patient and study."""
    pid = order.get("PatientID", "")
    if not isinstance(pid, str) or not pid.strip():
        raise DicomError("the order has no PatientID: a series without one cannot be filed")
    if not isinstance(order.get("PatientName", ""), str) or not order.get("PatientName", ""):
        raise DicomError("the order has no PatientName")
    if not uid.valid(order.get("StudyInstanceUID")):
        raise DicomError(f"the order's StudyInstanceUID {order.get('StudyInstanceUID')!r} is not "
                         "a valid UID")
    if order.get("PatientSex", "") not in ("", "M", "F", "O"):
        raise DicomError(f"PatientSex {order['PatientSex']!r} is not M, F, O or empty")
    for key in ("PatientBirthDate", "StudyDate"):
        v = order.get(key, "")
        if v:
            try:
                datetime.datetime.strptime(v, "%Y%m%d")
            except ValueError:
                raise DicomError(f"{key} {v!r} is not a date YYYYMMDD") from None


# [snippet:quantize]
def quantize(plane):
    """(stored values, slope text, signed) of one slice. The slope is per slice and the intercept
    0, as PET requires; unsigned 16-bit when no value is negative, signed otherwise. The stored
    values are computed with the slope as written (float of its DS text), not as computed, so
    that a reader that multiplies them by the slope it reads gets each value back within half a
    slope."""
    if not np.all(np.isfinite(plane)):
        raise DicomError("the image has values that are not finite")
    lo, hi = float(plane.min()), float(plane.max())
    signed = lo < 0
    top = 32767 if signed else 65535
    peak = max(abs(lo), abs(hi))
    slope_text = format_ds(peak / top if peak > 0 else 1.0)
    slope = float(slope_text)
    stored = np.clip(np.rint(plane / slope), -top - 1 if signed else 0, top)
    return stored.astype("<i2" if signed else "<u2"), slope_text, signed
# [/snippet:quantize]


def decay_factor(half_life_s, duration_s):
    """The factor that corrects the counts of a frame of duration_s that starts at the reference
    time for the decay during the frame: lambda T / (1 - exp(-lambda T))."""
    lam_t = math.log(2.0) / half_life_s * duration_s
    return lam_t / -math.expm1(-lam_t) if lam_t > 0 else 1.0


def mean_activity_time_s(half_life_s, duration_s):
    """The time after the frame's start at which the activity equals its mean over the frame:
    ln(lambda T / (1 - exp(-lambda T))) / lambda (earlier than the middle of the frame)."""
    lam = math.log(2.0) / half_life_s
    return math.log(decay_factor(half_life_s, duration_s)) / lam if duration_s > 0 else 0.0


def _content_digest(image, order, acquisition, reconstruction):
    h = hashlib.sha256()
    h.update(str(image.shape).encode())
    h.update(np.ascontiguousarray(image, dtype="<f8").tobytes())
    h.update(json.dumps([order, acquisition, reconstruction], sort_keys=True).encode())
    return h.hexdigest()


# [snippet:geometry]
def geometry(shape, pixel_mm, slice_mm, z0_mm, position):
    """(positions, orientation, along) of each exported slice: the patient coordinates (LPS) of
    the center of its first pixel, the direction cosines of a row and of a column, and the
    position along the slices' normal. Rows are exported top down (gantry y decreasing), so that
    for a patient on their back the column direction points to the posterior, as viewers
    expect."""
    if position not in POSITIONS:
        raise DicomError(f"patient position {position!r} is not supported "
                         f"(only {', '.join(sorted(POSITIONS))})")
    sx, sy, sz = POSITIONS[position]
    slices, rows, cols = shape
    row_dir = np.array([sx, 0.0, 0.0])            # increasing column: gantry +x
    col_dir = np.array([0.0, -sy, 0.0])           # increasing exported row: gantry -y
    normal = np.cross(row_dir, col_dir)
    positions = []
    for k in range(slices):
        gx = -(cols - 1) / 2.0 * pixel_mm
        gy = (rows - 1) / 2.0 * pixel_mm
        gz = z0_mm + k * slice_mm
        positions.append(np.array([sx * gx, sy * gy, sz * gz]) + 0.0)
    along = [float(p @ normal) for p in positions]
    return positions, (row_dir, col_dir), along
# [/snippet:geometry]


def series(image, order, acquisition, reconstruction):
    """The data sets of a PET Image series, one per slice; raises DicomError for an input that
    would give a series a reader could misfile, misplace or misread."""
    image = np.asarray(image, dtype=np.float64)
    if image.ndim != 3 or min(image.shape) < 1:
        raise DicomError(f"the image must be [slice, row, column], not of shape {image.shape}")
    if image.shape[1] > 65535 or image.shape[2] > 65535:
        raise DicomError("rows and columns are limited to 65535")
    check_order(order)
    acq, rec = acquisition, reconstruction
    start = _when(acq["start"], "acquisition start")
    nuclide = RADIONUCLIDES.get(acq.get("radionuclide"))
    if nuclide is None:
        raise DicomError(f"radionuclide {acq.get('radionuclide')!r} is not known "
                         f"(only {', '.join(sorted(RADIONUCLIDES))})")
    if rec["units"] not in UNITS:
        raise DicomError(f"units {rec['units']!r} are not one of {sorted(UNITS)}")
    corrections = list(rec.get("corrections", []))
    if set(corrections) - CORRECTIONS:
        raise DicomError(f"unknown corrections {sorted(set(corrections) - CORRECTIONS)}")
    decay = rec.get("decay_correction", "NONE")
    if decay not in DECAY or (decay == "START") != ("DECY" in corrections):
        raise DicomError("decay correction START must come with DECY among the corrections, "
                         "and NONE without it")
    pixel_mm, slice_mm = float(rec["pixel_mm"]), float(rec["slice_mm"])
    if not (pixel_mm > 0 and slice_mm > 0):
        raise DicomError("pixel and slice sizes must be positive")
    duration_s = float(acq["duration_s"])
    if not duration_s > 0:
        raise DicomError("the acquisition must have a positive duration")
    position = acq.get("patient_position", "HFS")
    positions, (row_dir, col_dir), along = geometry(image.shape, pixel_mm, slice_mm,
                                                    float(rec.get("z0_mm", 0.0)), position)

    study_uid = order["StudyInstanceUID"]
    digest = _content_digest(image, order, acq, rec)
    series_uid = uid.derived("series", study_uid, digest)
    frame_uid = uid.derived("frame of reference", study_uid, acq["start"], acq.get("run", ""))
    order_index = sorted(range(image.shape[0]), key=lambda k: along[k])
    frame_ref_ms = mean_activity_time_s(nuclide["half_life_s"], duration_s) * 1000.0
    charset = order.get("SpecificCharacterSet", "ISO_IR 192")

    radiopharm = Dataset()
    radiopharm.set("RadionuclideCodeSequence", [_code(*nuclide["code"])])
    radiopharm.set("RadionuclideHalfLife", nuclide["half_life_s"])
    radiopharm.set("RadionuclidePositronFraction", nuclide["positron_fraction"])
    if "radiopharmaceutical" in acq:
        code = RADIOPHARMACEUTICALS[acq["radiopharmaceutical"]]
        radiopharm.set("Radiopharmaceutical", code[2].replace("^", ""))
        radiopharm.set("RadiopharmaceuticalCodeSequence", [_code(*code)])
    if "injected_bq" in acq:
        radiopharm.set("RadionuclideTotalDose", float(acq["injected_bq"]))
    if "injection" in acq:
        inj = _when(acq["injection"], "injection time")
        radiopharm.set("RadiopharmaceuticalStartDateTime",
                       inj.strftime("%Y%m%d%H%M%S.%f") + _offset(inj))
    orientation = _code(*RECUMBENT).set("PatientOrientationModifierCodeSequence",
                                        [_code(*SUPINE)])

    out = []
    for index, k in enumerate(order_index, start=1):
        plane = image[k][::-1, :]  # exported top down: the first row is the highest gantry y
        stored, slope_text, signed = quantize(plane)
        ds = Dataset()
        ds.set("SpecificCharacterSet", charset)
        # SOP Common, Patient, General Study (from the order alone)
        ds.set("SOPClassUID", SOP_CLASS)
        ds.set("SOPInstanceUID", uid.derived("instance", series_uid, index))
        for key in ("PatientName", "PatientID"):
            ds.set(key, order[key])
        for key in ("PatientBirthDate", "PatientSex", "AccessionNumber", "StudyID",
                    "ReferringPhysicianName"):
            ds.set(key, order.get(key, ""))
        ds.set("StudyInstanceUID", study_uid)
        ds.set("StudyDate", order.get("StudyDate", _da(start)))
        ds.set("StudyTime", order.get("StudyTime", _tm(start)))
        ds.set("TimezoneOffsetFromUTC", _offset(start))
        # General Series, PET Series, PET Isotope, NM/PET Patient Orientation
        ds.set("Modality", "PT")
        ds.set("SeriesInstanceUID", series_uid)
        ds.set("SeriesNumber", int(rec.get("series_number", 1)))
        ds.set("SeriesDescription", rec.get("description", "MiniDAQ reconstruction"))
        ds.set("PatientPosition", position)
        ds.set("SeriesDate", _da(start))
        ds.set("SeriesTime", _tm(start))
        ds.set("Units", rec["units"])
        ds.set("CountsSource", "EMISSION")
        ds.set("SeriesType", ["STATIC", "IMAGE"])
        ds.set("NumberOfSlices", image.shape[0])
        ds.set("CorrectedImage", corrections)
        ds.set("DecayCorrection", decay)
        ds.set("ReconstructionMethod", rec.get("method", ""))
        ds.set("CollimatorType", "NONE")
        ds.set("RadiopharmaceuticalInformationSequence", [radiopharm])
        ds.set("PatientOrientationCodeSequence", [orientation])
        ds.set("PatientGantryRelationshipCodeSequence", [_code(*GANTRY_RELATION[position])])
        # Frame of Reference, General Equipment
        ds.set("FrameOfReferenceUID", frame_uid)
        ds.set("PositionReferenceIndicator", "")
        scanner = acq.get("scanner", {})
        ds.set("Manufacturer", scanner.get("manufacturer", ""))
        if scanner.get("model"):
            ds.set("ManufacturerModelName", scanner["model"])
        if scanner.get("serial"):
            ds.set("DeviceSerialNumber", scanner["serial"])
        if scanner.get("software"):
            ds.set("SoftwareVersions", scanner["software"])
        # General Image, Image Plane, Image Pixel, PET Image
        ds.set("InstanceNumber", index)
        ds.set("ImageType", ["ORIGINAL", "PRIMARY"])
        ds.set("AcquisitionDate", _da(start))
        ds.set("AcquisitionTime", _tm(start))
        ds.set("ActualFrameDuration", int(round(duration_s * 1000.0)))
        ds.set("ImagePositionPatient", [float(v) for v in positions[k]])
        ds.set("ImageOrientationPatient", [float(v) for v in (*row_dir, *col_dir)])
        ds.set("SliceLocation", along[k])
        ds.set("PixelSpacing", [pixel_mm, pixel_mm])
        ds.set("SliceThickness", slice_mm)
        ds.set("SamplesPerPixel", 1)
        ds.set("PhotometricInterpretation", "MONOCHROME2")
        ds.set("Rows", stored.shape[0])
        ds.set("Columns", stored.shape[1])
        ds.set("BitsAllocated", 16)
        ds.set("BitsStored", 16)
        ds.set("HighBit", 15)
        ds.set("PixelRepresentation", 1 if signed else 0)
        ds.set("RescaleIntercept", "0")
        ds.set("RescaleSlope", slope_text)
        ds.set("FrameReferenceTime", frame_ref_ms)
        ds.set("ImageIndex", index)
        if decay == "START":
            ds.set("DecayFactor", decay_factor(nuclide["half_life_s"], duration_s))
        ds.set("PixelData", stored.tobytes())
        out.append(ds)
    return out


def _empty(v):
    return v is None or v == "" or v == [] or v == b""


def check_series(datasets):
    """The problems of a series that must not leave: [] if there are none."""
    problems = []
    if not datasets:
        return ["the series has no instances"]
    for i, ds in enumerate(datasets, start=1):
        for key in TYPE1:
            if not ds.has(key) or _empty(ds.get(key)):
                problems.append(f"instance {i}: type 1 {key} is missing or empty")
        for key in TYPE2:
            if not ds.has(key):
                problems.append(f"instance {i}: type 2 {key} is missing")
        for key in ("SOPInstanceUID", "StudyInstanceUID", "SeriesInstanceUID",
                    "FrameOfReferenceUID", "SOPClassUID"):
            if ds.has(key) and not uid.valid(ds.get(key)):
                problems.append(f"instance {i}: {key} {ds.get(key)!r} is not a valid UID")
        if ds.get("Modality") != "PT" or ds.get("SOPClassUID") != SOP_CLASS:
            problems.append(f"instance {i}: not a PET Image object")
        if ds.has("RescaleIntercept") and float(ds.get("RescaleIntercept")) != 0.0:
            problems.append(f"instance {i}: the rescale intercept of PET must be 0")
        if (ds.get("BitsAllocated"), ds.get("BitsStored"), ds.get("HighBit")) != (16, 16, 15):
            problems.append(f"instance {i}: PET pixels are 16 bits allocated and stored")
        if ds.has("PixelData") and ds.has("Rows") and ds.has("Columns") and \
                len(ds.get("PixelData")) != 2 * ds.get("Rows") * ds.get("Columns"):
            problems.append(f"instance {i}: the pixel data is not Rows x Columns x 2 bytes")
    first = datasets[0]
    for key in SHARED:
        if any(ds.get(key) != first.get(key) for ds in datasets):
            problems.append(f"{key} differs between the instances of the series")
    sops = [ds.get("SOPInstanceUID") for ds in datasets]
    if len(set(sops)) != len(sops):
        problems.append("two instances have the same SOPInstanceUID")
    indices = sorted(ds.get("ImageIndex") or 0 for ds in datasets)
    if indices != list(range(1, len(datasets) + 1)):
        problems.append("the image indices are not 1 to the number of instances")
    if first.get("NumberOfSlices") != len(datasets):
        problems.append("NumberOfSlices is not the number of instances")
    return problems


def write_series(datasets, directory):
    """Writes each data set as a DICOM file named after its SOP Instance UID, atomically (a file
    is complete or absent), after check_series; returns the paths."""
    problems = check_series(datasets)
    if problems:
        raise DicomError("the series is not fit to leave: " + "; ".join(problems))
    directory = pathlib.Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    paths = []
    for ds in datasets:
        path = directory / (ds.get("SOPInstanceUID") + ".dcm")
        tmp = path.with_suffix(".tmp")
        tmp.write_bytes(encode.file_bytes(ds, uid.IMPLEMENTATION_CLASS))
        tmp.replace(path)
        paths.append(path)
    return paths


def values(ds):
    """The image values of one data set: stored values times the rescale slope, as a reader
    computes them, as float64 [row, column]."""
    dtype = "<i2" if ds.get("PixelRepresentation") == 1 else "<u2"
    stored = np.frombuffer(ds.get("PixelData"), dtype=dtype).reshape(ds.get("Rows"),
                                                                     ds.get("Columns"))
    return stored.astype(np.float64) * float(ds.get("RescaleSlope")) \
        + float(ds.get("RescaleIntercept"))
