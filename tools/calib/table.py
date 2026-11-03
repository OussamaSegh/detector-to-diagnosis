# SPDX-License-Identifier: MIT
"""The calibration table file (docs/formats/calibration.md), as minidaq_server reads it.

The server keeps each coefficient as a 32-bit float and checks a CRC-32 over the coefficients as it
read them (minidaq/processing/calibration.hpp, canonical_bytes): per crystal a, b and q as IEEE
floats and the time offset as a signed 32-bit integer, all little-endian. So this module rounds
every coefficient to a float32 first and writes the double that is exactly that float32: the
server's double-then-float conversion gives back the same bits, and the CRCs agree.
"""
import json
import struct
import zlib

import numpy as np

from . import readout

SCHEMA_VERSION = "1.0"

# [snippet:limits]
# The server's own limits (CalibrationLimits in minidaq/processing/calibration.hpp). The procedure
# checks them too, so that it never writes a table that minidaq_server would refuse.
SERVER_LIMITS = {"min_gain": 0.5, "max_gain": 2.0, "max_abs_a_kev": 100.0,
                 "max_curvature_down": 0.4, "max_curvature_up": 1.5,
                 "max_abs_time_offset_ps": 5000}


def server_refusals(a, b, q, offset_ps, limits=SERVER_LIMITS):
    """Per crystal, the reason the server would refuse its entry, or "" (the float32 values)."""
    a, b, q = (np.asarray(v, dtype=np.float32).astype(float) for v in (a, b, q))
    t = np.asarray(offset_ps)
    top = float(readout.MAX_CODE)
    gain = b / readout.ENERGY_LSB_KEV
    with np.errstate(divide="ignore", invalid="ignore"):
        bend = q * top / b
    why = np.full(a.size, "", dtype=object)
    checks = [
        (~(np.isfinite(a) & np.isfinite(b) & np.isfinite(q)), "a coefficient is not finite"),
        ((gain < limits["min_gain"]) | (gain > limits["max_gain"]), "gain outside 0.5 to 2"),
        (np.abs(a) > limits["max_abs_a_kev"], "energy at code 0 beyond 100 keV"),
        (b + 2.0 * q * top <= 0.0, "energy falls with the code"),
        ((bend < -limits["max_curvature_down"]) | (bend > limits["max_curvature_up"]),
         "curvature at code 2047 outside -0.4 to 1.5"),
        (np.abs(t) > limits["max_abs_time_offset_ps"], "time offset beyond 5 ns"),
    ]
    for mask, text in reversed(checks):  # the first failing check wins, as in the server
        why[mask] = text
    return why
# [/snippet:limits]


def to_float32(x):
    """The values as float32, then as Python floats that are exactly those float32 values."""
    return [float(v) for v in np.asarray(x, dtype=np.float32)]


# [snippet:crc]
def crc32(a, b, q, offset_ps):
    """The CRC-32 the server computes over the coefficients: <fffi per crystal, little-endian."""
    a32, b32, q32 = (np.asarray(v, dtype="<f4") for v in (a, b, q))
    t32 = np.asarray(offset_ps, dtype="<i4")
    rows = np.empty(a32.size, dtype=[("a", "<f4"), ("b", "<f4"), ("q", "<f4"), ("t", "<i4")])
    rows["a"], rows["b"], rows["q"], rows["t"] = a32, b32, q32, t32
    return zlib.crc32(rows.tobytes()) & 0xFFFFFFFF
# [/snippet:crc]


def crc32_slow(a, b, q, offset_ps):
    """The same CRC, one struct.pack per crystal: the definition, for the tests."""
    data = b"".join(struct.pack("<fffi", float(x), float(y), float(z), int(t))
                    for x, y, z, t in zip(a, b, q, offset_ps))
    return zlib.crc32(data) & 0xFFFFFFFF


def build(info, a, b, q, offset_ps):
    """The table document: `info` holds id, version, scanner_serial, created_utc, valid_until_utc,
    reference_temperature_c and procedure."""
    n = readout.NUM_CRYSTALS
    for name, v in (("a", a), ("b", b), ("q", q), ("offset_ps", offset_ps)):
        if np.asarray(v).shape != (n,):
            raise ValueError(f"{name} must have one value per crystal ({n})")
    offsets = np.asarray(offset_ps)
    if not np.issubdtype(offsets.dtype, np.integer):
        raise ValueError("offset_ps must be integers")
    doc = {"schema_version": SCHEMA_VERSION}
    for key in ("id", "version", "scanner_serial", "created_utc", "valid_until_utc",
                "reference_temperature_c", "procedure"):
        doc[key] = info[key]
    doc["crystals"] = n
    doc["energy"] = {"a_kev": to_float32(a), "b_kev": to_float32(b), "q_kev": to_float32(q)}
    doc["time"] = {"offset_ps": [int(t) for t in offsets]}
    doc["crc32"] = f"{crc32(a, b, q, offsets):08x}"
    return doc


def write(path, doc):
    """Compact JSON on one line: about 1 MB for the 18,432 crystals."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps(doc, separators=(",", ":")))
        f.write("\n")


def read(path):
    """A table file back as (document, a, b, q, offset_ps), with its CRC checked."""
    with open(path, encoding="utf-8") as f:
        doc = json.load(f)
    a, b, q = (np.asarray(doc["energy"][k], dtype=np.float32) for k in ("a_kev", "b_kev", "q_kev"))
    t = np.asarray(doc["time"]["offset_ps"], dtype=np.int32)
    if f"{crc32(a, b, q, t):08x}" != doc["crc32"]:
        raise ValueError(f"{path}: the CRC does not match the coefficients")
    return doc, a, b, q, t
