#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Runs one check of the analysis package for CTest: tests, types or lint.

    run_checks.py pytest|mypy|ruff

Exit status 77 (CTest's skip) when the Python environment lacks what the check needs: the
package's dependencies come from analysis/requirements.lock, which the CI job "python" installs;
a build machine with only the system's numpy skips these checks rather than failing them.
With MINIDAQ_ANALYSIS_REQUIRED=1 (the CI job) a missing package is a failure, not a skip.
"""
import importlib.util
import os
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
NEEDS = {"pytest": ["numpy", "scipy", "matplotlib", "pytest"],
         "mypy": ["numpy", "scipy", "mypy"],
         "ruff": ["ruff"]}
COMMANDS = {"pytest": ["-m", "pytest", "-q", "-p", "no:cacheprovider", str(HERE / "tests")],
            "mypy": ["-m", "mypy", "--config-file", str(HERE / "pyproject.toml"),
                     "--cache-dir", os.devnull, str(HERE / "src")],
            "ruff": ["-m", "ruff", "check", "--no-cache", str(HERE / "src"), str(HERE / "tests")]}


def main(check: str) -> int:
    missing = [m for m in NEEDS[check] if importlib.util.find_spec(m) is None]
    if missing:
        print(f"{', '.join(missing)} not installed (analysis/requirements.lock)")
        return 1 if os.environ.get("MINIDAQ_ANALYSIS_REQUIRED") == "1" else 77
    env = dict(os.environ, PYTHONPATH=str(HERE / "src"), PYTHONDONTWRITEBYTECODE="1",
               MPLBACKEND="Agg")
    return subprocess.run([sys.executable, *COMMANDS[check]], cwd=HERE, env=env).returncode


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in COMMANDS:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
