# SPDX-License-Identifier: MIT
"""Filtered backprojection of a 2D sinogram (Chapter 30), numpy only: the reconstruction by which
NEMA NU 2 measures a scanner's spatial resolution, because, unlike OSEM, its result does not
depend on a number of iterations or on the counts.

MiniDAQ's bins are not equally spaced in s (s = -R sin(pi r / N), sinogram.py), and each view
interleaves two angles. FBP needs equal spacing: each view is interpolated onto a grid of the
central bins' spacing (the arc correction), and the view is taken at its mean angle (header.phi),
which is at most pi / (2N) from each of its bins' (0.23 degrees for MiniDAQ, 0.4 mm along the
line at 100 mm from the axis). The filter is the ramp, unwindowed (Ram-Lak), applied in space so
that its zero-frequency term is exact.
"""
import numpy as np

from . import project, sinogram as sg


# [snippet:ramp]
def ramp_kernel(half_length, ds_mm):
    """The ramp filter sampled at spacing ds_mm, from -half_length to half_length samples: 1/(4
    ds^2) at 0, -1/(pi k ds)^2 at odd k, 0 at even k (Kak and Slaney, chapter 3)."""
    k = np.arange(-half_length, half_length + 1)
    h = np.zeros(k.size)
    h[k == 0] = 1.0 / (4.0 * ds_mm ** 2)
    odd = k % 2 == 1
    h[odd] = -1.0 / (np.pi * k[odd] * ds_mm) ** 2
    return h
# [/snippet:ramp]


def arc_correct(sino, header, radius_mm):
    """(s_uniform, views x len(s_uniform)): each view interpolated onto s equally spaced at the
    central bins' spacing pi R / N, over the same range."""
    s = -radius_mm * np.sin(np.pi * header.r / sg.CRYSTALS_PER_RING)
    order = np.argsort(s)
    ds = np.pi * radius_mm / sg.CRYSTALS_PER_RING
    half = int(np.floor(s.max() / ds))
    s_u = np.arange(-half, half + 1) * ds
    out = np.array([np.interp(s_u, s[order], view[order]) for view in np.asarray(sino)])
    return s_u, out


def fbp(sino, header, radius_mm, n=128, pixel_mm=2.0, projector=project.Projector):
    """The FBP image of a sinogram of line integrals (mm times image units) with header's views
    and radial bins, n x n pixels of pixel_mm, in the image's units. projector is the class whose back()
    does the backprojection: Projector or CppProjector."""
    s_u, p = arc_correct(sino, header, radius_mm)
    ds = s_u[1] - s_u[0]
    half = s_u.size - 1
    h = ramp_kernel(half, ds)
    q = np.array([np.convolve(view, h)[half:half + s_u.size] for view in p]) * ds
    phi = np.broadcast_to(header.phi[:, None], q.shape).copy()
    a = projector(np.broadcast_to(s_u, q.shape).copy(), phi, n=n, pixel_mm=pixel_mm)
    # Joseph's backprojection spreads each line over pixel_mm^2 / ds of image per mm along it:
    # scale to the integral over the angles, pi / views per view.
    return a.back(q) * (np.pi / header.views) * ds / pixel_mm ** 2
