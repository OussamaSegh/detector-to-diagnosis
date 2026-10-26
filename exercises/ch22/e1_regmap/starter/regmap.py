# SPDX-License-Identifier: MIT
"""Exercise 22.1: a register map generator."""
import tomllib  # noqa: F401  (you will need it)

ACCESS = ("ro", "rw", "wo", "rw1c")


class SpecError(Exception):
    pass


def load(text: str) -> dict:
    """The parsed specification; SpecError naming the register for every mistake of the README."""
    raise NotImplementedError("TODO: parse with tomllib and check every register and field")


def header(spec: dict) -> str:
    """The C++ header of constants for a specification that load() accepted."""
    raise NotImplementedError("TODO: one ADDR and RESET per register, one SHIFT and MASK per field")
