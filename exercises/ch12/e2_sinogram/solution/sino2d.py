# SPDX-License-Identifier: MIT
"""Exercise 12.2: a 2D sinogram from an MDQ-L1 list-mode file, in pure Python.

The reader (read_coincidences) is given; lor_bin, sinogram, radial_position_mm
and fit_point are the exercise. The geometry is MiniDAQ's: 384 crystals per
ring of radius 150 mm, crystal i at angle (i + 0.5) * 2 pi / 384, crystal id =
ring * 384 + transaxial index.
"""
import math
import struct
import zlib

N = 384             # crystals per ring
RADIUS_MM = 150.0
VIEWS = N // 2      # 192


def read_coincidences(path):
    """(time_ps, crystal_first, crystal_second, delayed) for every coincidence in intact blocks."""
    data = open(path, "rb").read()
    if data[:8] != b"MDQL\r\n\x1a\n" or struct.unpack_from("<H", data, 8)[0] != 1:
        raise ValueError(f"{path}: not an MDQ-L1 version 1 file")
    header_bytes = struct.unpack_from("<I", data, 12)[0]
    if zlib.crc32(data[: header_bytes - 8]) != struct.unpack_from("<I", data, header_bytes - 8)[0]:
        raise ValueError(f"{path}: damaged file header")
    out, pos = [], header_bytes
    while pos + 32 <= len(data):
        magic, _seq, n, _flags, base, pcrc, hcrc = struct.unpack_from("<4sIIIqII", data, pos)
        if magic != b"MDQB" or zlib.crc32(data[pos : pos + 28]) != hcrc or pos + 32 + 16 * n > len(data):
            break  # damaged or truncated: this simple reader stops (minidaq_listmode resynchronizes)
        payload = data[pos + 32 : pos + 32 + 16 * n]
        if zlib.crc32(payload) == pcrc:
            for offset, a, b, _dt, _ea, _eb in struct.iter_unpack("<IHHiHH", payload):
                if a != 0x7FFF:  # not a tag
                    out.append((base + offset, a & 0x7FFF, b, a >> 15 == 1))
        pos += 32 + 16 * n
    return out


# [snippet:lorbin]
def lor_bin(t1, t2):
    """(view, r) of the LOR between transaxial crystals t1 and t2, or None if t1 == t2.

    The normal of the LOR (i, j), i < j, is at angle (i + j + 1) pi / N and the LOR
    lies at R cos(pi (j - i) / N) along it. Past 180 degrees the same line is seen
    from the other side: subtract 180 degrees and change the sign of the distance.
    """
    if t1 == t2:
        return None
    i, j = min(t1, t2), max(t1, t2)
    k, d = i + j + 1, j - i
    if k >= N:
        k, d = k - N, N - d
    return k // 2, d - N // 2
# [/snippet:lorbin]


def radial_position_mm(r):
    """The signed distance of radial bin r from the axis (not arc-corrected)."""
    return -RADIUS_MM * math.sin(math.pi * r / N)


def max_radial(fov_radius_mm):
    return int(math.floor(math.asin(fov_radius_mm / RADIUS_MM) * N / math.pi))


# [snippet:sinogram]
def sinogram(coincidences, fov_radius_mm=120.0):
    """Prompts per (view, radial bin): a list of VIEWS rows of 2 * max_radial + 1 counts."""
    m = max_radial(fov_radius_mm)
    sino = [[0] * (2 * m + 1) for _ in range(VIEWS)]
    for _t, a, b, delayed in coincidences:
        if delayed:
            continue  # delayeds estimate the randoms; they go in a sinogram of their own
        lb = lor_bin(a % N, b % N)
        if lb is None or abs(lb[1]) > m:
            continue
        sino[lb[0]][lb[1] + m] += 1
    return sino
# [/snippet:sinogram]


# [snippet:fit]
def fit_point(sino):
    """(x0, y0) of a point source from its sinusoid s(theta) = x0 cos(theta) + y0 sin(theta).

    One centroid per view, then linear least squares over the views. View v holds
    the angles 2v and 2v + 1 in units of pi / N, so its angle is (2v + 0.5) pi / N.
    """
    m = (len(sino[0]) - 1) // 2
    sxx = sxy = syy = bx = by = 0.0
    for v, row in enumerate(sino):
        n = sum(row)
        if n == 0:
            continue
        s = sum(c * radial_position_mm(r - m) for r, c in enumerate(row)) / n
        th = (2 * v + 0.5) * math.pi / N
        c, si = math.cos(th), math.sin(th)
        sxx += c * c
        sxy += c * si
        syy += si * si
        bx += c * s
        by += si * s
    det = sxx * syy - sxy * sxy
    return (syy * bx - sxy * by) / det, (sxx * by - sxy * bx) / det
# [/snippet:fit]


def save_png(sino, path):
    """Optional: draw the sinogram (needs matplotlib, which the tests do not)."""
    import matplotlib.pyplot as plt  # pylint: disable=import-outside-toplevel

    m = (len(sino[0]) - 1) // 2
    plt.figure(figsize=(5, 4))
    plt.imshow(sino, aspect="auto", origin="lower", cmap="gray_r", extent=(-m - 0.5, m + 0.5, 0, 180))
    plt.xlabel("radial bin r")
    plt.ylabel("view angle (degrees)")
    plt.colorbar(label="prompts")
    plt.tight_layout()
    plt.savefig(path, dpi=150)


if __name__ == "__main__":
    import sys

    s = sinogram(read_coincidences(sys.argv[1]))
    print("point source at x = %.2f mm, y = %.2f mm" % fit_point(s))
    if len(sys.argv) > 2:
        save_png(s, sys.argv[2])
