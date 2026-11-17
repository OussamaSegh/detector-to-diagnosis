# SPDX-License-Identifier: MIT
"""Configure, build and install the exercise's project in scratch directories (Chapter 32).

The project is EX_PROJECT (the starter or the solution); CMake, the generator and the compiler
are this build's (EX_CMAKE, EX_GENERATOR, EX_CXX), and the scratch directories are under EX_WORK.
Outside CTest, the defaults build the solution with the cmake and c++ on the path."""
import os
import pathlib
import shutil
import subprocess
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
PROJECT = pathlib.Path(os.environ.get("EX_PROJECT", HERE.parent / "solution"))
CMAKE = os.environ.get("EX_CMAKE", "cmake")
GENERATOR = os.environ.get("EX_GENERATOR", "Ninja" if shutil.which("ninja") else "Unix Makefiles")
CXX = os.environ.get("EX_CXX", "c++")


def scratch(name):
    """An empty directory of its own for one test."""
    base = pathlib.Path(os.environ.get("EX_WORK", tempfile.gettempdir()))
    base.mkdir(parents=True, exist_ok=True)
    return pathlib.Path(tempfile.mkdtemp(prefix=name + "-", dir=base))


def cmake(*args, cwd=None):
    """Runs cmake; returns the CompletedProcess (stdout and stderr together in .output)."""
    r = subprocess.run([CMAKE, *map(str, args)], cwd=cwd, capture_output=True, text=True)
    r.output = r.stdout + r.stderr
    return r


def configure(source, build, *defines):
    return cmake("-S", source, "-B", build, "-G", GENERATOR, f"-DCMAKE_CXX_COMPILER={CXX}",
                 "-DCMAKE_BUILD_TYPE=Release", *defines)


def build(build_dir, *args):
    return cmake("--build", build_dir, *args)
