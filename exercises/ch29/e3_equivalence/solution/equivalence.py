# SPDX-License-Identifier: MIT
"""Exercise 29.3: is a second implementation of a projector the same as the reference?

assert_same(reference, candidate, rtol) raises AssertionError, saying what differs, unless the
candidate's forward and back projections agree with the reference's to rtol relative to their
largest value, and the candidate's back is the adjoint of its forward. Both projectors have
n, shape, forward(image) and back(sino).
"""
import numpy as np


# [snippet:assert_same]
def assert_same(reference, candidate, rtol=1e-6, seed=0):
    if (candidate.n, tuple(candidate.shape)) != (reference.n, tuple(reference.shape)):
        raise AssertionError(f"geometry: n {candidate.n} and shape {candidate.shape}, "
                             f"want {reference.n} and {reference.shape}")
    rng = np.random.default_rng(seed)
    # Random data: no symmetry that a mistake could hide behind. A centered disc projects the
    # same in every view and both ways along s, so it cannot see an angle or a sign.
    x = rng.random((reference.n, reference.n))
    y = rng.random(reference.shape)
    for name, want, got in (("forward", reference.forward(x), candidate.forward(x)),
                            ("back", reference.back(y), candidate.back(y))):
        if np.shape(got) != np.shape(want):
            raise AssertionError(f"{name}: shape {np.shape(got)}, want {np.shape(want)}")
        err = np.abs(np.asarray(got, dtype=np.float64) - want).max() / np.abs(want).max()
        if not err <= rtol:
            raise AssertionError(f"{name}: differs by {err:.1e} relative, more than {rtol:.0e}")
    # The candidate's own pair must be adjoint: forward and back can each be close to the
    # reference and still not be each other's transpose.
    lhs = float((np.asarray(candidate.forward(x), dtype=np.float64) * y).sum())
    rhs = float((x * np.asarray(candidate.back(y), dtype=np.float64)).sum())
    if not abs(lhs / rhs - 1.0) <= rtol:
        raise AssertionError(f"adjoint: <Ax, y> / <x, A^T y> = {lhs / rhs:.9f}")
# [/snippet:assert_same]
