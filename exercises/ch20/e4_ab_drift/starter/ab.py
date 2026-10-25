# SPDX-License-Identifier: MIT
"""Exercise 20.4 starter: A/B benchmarking on a machine that drifts. simulate() and the alarm
rates are given; write the order of the runs and the decisions."""
from __future__ import annotations

import math
import random
import statistics

import perf_gate


def schedule(rounds: int, interleave: bool = True) -> list[str]:
    """The order of 2 * rounds runs: interleaved A B B A A B ..., or all A then all B."""
    raise NotImplementedError  # TODO


def simulate(order: list[str], ratio: float = 1.0, drift: float = 0.0, noise: float = 0.01,
             seed: int = 0) -> dict[str, list[float]]:
    """Speeds of the runs in `order`: B is `ratio` times as fast as A; the machine's speed changes
    by `drift` (a fraction) per run; each run has a relative noise of `noise` (one sigma)."""
    rng = random.Random(seed)
    out: dict[str, list[float]] = {"A": [], "B": []}
    for i, side in enumerate(order):
        machine = 1.0 + drift * i
        out[side].append(machine * (ratio if side == "B" else 1.0) * (1.0 + rng.gauss(0.0, noise)))
    return out


def decide(a: list[float], b: list[float], threshold: float = 0.05, alpha: float = 0.01) -> bool:
    """True if B is a regression of A: the gate of Chapter 5 on speeds."""
    raise NotImplementedError  # TODO


def alarm_rate(rounds: int, interleave: bool, ratio: float, drift: float, noise: float = 0.01,
               trials: int = 200, seed: int = 1) -> float:
    """The fraction of simulated comparisons that the gate calls a regression."""
    order = schedule(rounds, interleave)
    hits = 0
    for t in range(trials):
        runs = simulate(order, ratio, drift, noise, seed * 100_003 + t)
        hits += decide(runs["A"], runs["B"])
    return hits / trials


def round_ratios(order: list[str], runs: dict[str, list[float]]) -> list[float]:
    """B / A within each round of an interleaved order: the machine's drift cancels in a ratio
    of two neighbors, whatever it did between rounds."""
    raise NotImplementedError  # TODO


def sign_test_p_less(ratios: list[float]) -> float:
    """One-sided p-value that B tends to be slower: the chance of at least as many rounds with a
    ratio below 1 if each round were a coin toss."""
    raise NotImplementedError  # TODO


def decide_paired(order: list[str], runs: dict[str, list[float]], threshold: float = 0.05,
                  alpha: float = 0.01) -> bool:
    """True if B is a regression of A, judged on the rounds' ratios: their median is below
    1 - threshold and the sign test rejects at alpha."""
    raise NotImplementedError  # TODO


def paired_alarm_rate(rounds: int, ratio: float, drift: float, noise: float = 0.01, trials: int = 200,
                      seed: int = 1) -> float:
    order = schedule(rounds, True)
    return sum(decide_paired(order, simulate(order, ratio, drift, noise, seed * 100_003 + t))
               for t in range(trials)) / trials
