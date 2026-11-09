# SPDX-License-Identifier: MIT
"""Figure for Chapter 5: the flame graph after the sort fix, from measurements/ch05/flame/after.folded.

    python3 book/tools/figures.py build book/figures/plots/ch05/flame_after.py screen 1 pdf
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import flamelib  # noqa: E402

if __name__ == "__main__":
    flamelib.draw("after.folded", sys.argv[1], "after the fix")
