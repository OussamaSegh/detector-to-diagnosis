# SPDX-License-Identifier: MIT
"""MiniDAQ's scanner geometry and its SSRB sinograms (Chapter 12), as numpy arrays.

A sinogram bin (slice, view, r) counts the lines of response between transaxial crystals i < j of
rings ring_a and ring_b with ring_a + ring_b = slice. Each (view, r) holds exactly one transaxial
pair (i, j): N (N - 1) / 2 pairs and N / 2 views of N - 1 radial bins. crystal_pairs() finds it the
way minidaq::sino::lor_bin() does, so that a correction computed per crystal (an efficiency, a
singles rate) lands in the bin the histogrammer used.
"""
import pathlib
from dataclasses import dataclass

import numpy as np

CRYSTALS_PER_RING = 384
RINGS = 48
RADIUS_MM = 150.0           # the crystals' front faces
AXIAL_PITCH_MM = 2.45
CRYSTALS_PER_BLOCK_T = 16   # transaxial
CRYSTALS_PER_BLOCK_A = 16   # axial
BLOCKS_PER_RING = CRYSTALS_PER_RING // CRYSTALS_PER_BLOCK_T


def ring_of(crystal):
    return np.asarray(crystal) // CRYSTALS_PER_RING


def transaxial_of(crystal):
    return np.asarray(crystal) % CRYSTALS_PER_RING


def block_of(crystal):
    """minidaq::ScannerGeometry::block_of: block ring times blocks per ring plus the block."""
    c = np.asarray(crystal)
    return ((ring_of(c) // CRYSTALS_PER_BLOCK_A) * BLOCKS_PER_RING
            + transaxial_of(c) // CRYSTALS_PER_BLOCK_T)


@dataclass(frozen=True)
class Header:
    """What the Interfile header of minidaq_listmode sino says about its data."""
    path: pathlib.Path
    radial_bins: int
    views: int
    slices: int
    tof_bins: int
    first_r: int
    max_ring_difference: int
    fov_radius_mm: float
    files: dict

    @property
    def shape(self):
        plain = (self.slices, self.views, self.radial_bins)
        return (self.tof_bins, *plain) if self.tof_bins > 1 else plain

    @property
    def r(self):
        """The radial bin index r of each column."""
        return np.arange(self.first_r, self.first_r + self.radial_bins)

    @property
    def s_mm(self):
        """Each column's distance from the axis: s = -R sin(pi r / N), not arc-corrected."""
        return -RADIUS_MM * np.sin(np.pi * self.r / CRYSTALS_PER_RING)

    @property
    def phi(self):
        """Each view's angle: the mean of the two interleaved normals, (2v + 1/2) pi / N."""
        return (2.0 * np.arange(self.views) + 0.5) * np.pi / CRYSTALS_PER_RING


def read_header(path):
    path = pathlib.Path(path)
    kv = {}
    for line in path.read_text().splitlines():
        if ":=" in line and not line.startswith(";"):
            k, _, v = line.partition(":=")
            kv[k.strip().lower()] = v.strip()
    suffix = " data file"
    files = {k[:-len(suffix)]: path.parent / v for k, v in kv.items() if k.endswith(suffix)}
    return Header(path=path, radial_bins=int(kv["matrix size [radial]"]),
                  views=int(kv["matrix size [view]"]), slices=int(kv["matrix size [slice]"]),
                  tof_bins=int(kv["matrix size [tof]"]), first_r=int(kv["first radial bin r"]),
                  max_ring_difference=int(kv["maximum ring difference"]),
                  fov_radius_mm=float(kv["fov radius (mm)"]), files=files)


def read(header, which="prompts"):
    """The sinogram `which` (prompts, delayeds, or another raw file next to the header with the same
    layout, such as minidaq_sim's trues) as float64 of header.shape."""
    if isinstance(header, (str, pathlib.Path)):
        header = read_header(header)
    path = header.files.get(which)
    if path is None:  # minidaq_sim --truth-sino: PREFIX.trues.u32 next to PREFIX.hdr
        path = header.path.with_suffix(f".{which}.u32")
    data = np.fromfile(path, dtype="<u4")
    if data.size != int(np.prod(header.shape)):
        raise ValueError(f"{path}: {data.size} values, the header says {header.shape}")
    return data.reshape(header.shape).astype(np.float64)


# [snippet:pairs]
def crystal_pairs(header):
    """(i, j): the transaxial crystals that each (view, column) joins, arrays of shape
    (views, radial_bins); -1 where no pair falls in the bin. As lor_bin(): k = i + j + 1 is twice
    the normal's angle in units of pi / N and d = j - i; a k of N or more is the same line seen
    from the other side, at k - N with d -> N - d."""
    n = CRYSTALS_PER_RING
    i, j = np.triu_indices(n, k=1)
    k = i + j + 1
    d = j - i
    wrapped = k >= n
    k = np.where(wrapped, k - n, k)
    d = np.where(wrapped, n - d, d)
    view, r = k // 2, d - n // 2
    ti = np.full((header.views, header.radial_bins), -1, dtype=np.int64)
    tj = np.full_like(ti, -1)
    col = r - header.first_r
    inside = (col >= 0) & (col < header.radial_bins)
    ti[view[inside], col[inside]] = i[inside]
    tj[view[inside], col[inside]] = j[inside]
    return ti, tj
# [/snippet:pairs]


def axial_sum(a, b, max_ring_difference=RINGS - 1):
    """For two arrays of per-ring values with rings on axis 0, the SSRB sum over ring pairs:
    out[slice] = sum over ring_a + ring_b = slice, |ring_a - ring_b| <= max_ring_difference, of
    a[ring_a] * b[ring_b], for every column of the other axes. Without a cut it is a convolution
    along the rings, done by FFT."""
    rings = a.shape[0]
    n = 2 * rings - 1
    if max_ring_difference >= rings - 1:
        size = 1 << (n - 1).bit_length()
        fa = np.fft.rfft(a, size, axis=0)
        fb = np.fft.rfft(b, size, axis=0)
        return np.fft.irfft(fa * fb, size, axis=0)[:n]
    out = np.zeros((n,) + np.broadcast_shapes(a.shape[1:], b.shape[1:]))
    for ra in range(rings):
        lo, hi = max(0, ra - max_ring_difference), min(rings, ra + max_ring_difference + 1)
        out[ra + lo:ra + hi] += a[ra] * b[lo:hi]
    return out


def ring_pairs_per_slice(max_ring_difference=RINGS - 1):
    """How many (ring_a, ring_b) pairs each SSRB slice holds."""
    ones = np.ones(RINGS)
    return np.rint(axial_sum(ones, ones, max_ring_difference)).astype(np.int64)
