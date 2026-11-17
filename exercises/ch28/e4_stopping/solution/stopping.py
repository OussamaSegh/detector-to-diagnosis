# SPDX-License-Identifier: MIT
"""Exercise 28.4, a solution: when to stop OSEM, from a noise target.

`ordered.osem` (Exercise 28.3) runs OSEM; one call with iterations=1 and x0 continues a
reconstruction by one iteration, so the noise can be measured after each one.
"""
import numpy as np

import ordered

MIN_VIEWS = 6  # fewer views in a subset and OSEM stops following MLEM (Chapter 28, section 6)


def background_noise(x, background):
    """The coefficient of variation of the image over the background mask: the noise of a uniform
    region, which the image's own structure does not inflate."""
    values = x[background]
    return float(values.std() / values.mean())


def stop(y, projector, mult, add, count, target, background, max_iterations=100):
    """Runs OSEM with count subsets and returns (iterations, image, noise) for the last iteration
    whose background noise is still at most target, before it first passes target."""
    views = np.asarray(y).shape[0]
    if count < 1 or views // count < MIN_VIEWS:
        raise ValueError(f"{count} subsets of {views} views leave fewer than {MIN_VIEWS} views "
                         "in a subset")
    x = None
    kept = None
    for it in range(1, max_iterations + 1):
        x = ordered.osem(y, projector, mult, add, 1, count, x0=x)
        noise = background_noise(x, background)
        if noise > target:
            if kept is None:
                raise ValueError(f"the first iteration of {count} subsets is already at "
                                 f"{noise:.1%}, above {target:.1%}: fewer subsets stop finer")
            return kept
        kept = (it, x, noise)
    return kept
