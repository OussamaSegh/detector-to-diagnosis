# SPDX-License-Identifier: MIT
"""Exercise 28.4: when to stop OSEM, from a noise target.

`ordered.osem` (Exercise 28.3) runs OSEM; one call with iterations=1 and x0 continues a
reconstruction by one iteration, so the noise can be measured after each one.

This starter runs and gives plausible numbers. TODO: make the tests pass.
"""
import numpy as np

import ordered


def background_noise(x, background):
    """The noise of the image."""
    return float(np.std(x) / np.mean(x))


def stop(y, projector, mult, add, count, target, background, max_iterations=100):
    """Runs OSEM with count subsets and returns (iterations, image, noise) where the noise
    reaches target."""
    x = None
    for it in range(1, max_iterations + 1):
        x = ordered.osem(y, projector, mult, add, 1, count, x0=x)
        noise = background_noise(x, background)
        if noise >= target:
            break
    return it, x, noise
