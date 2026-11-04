#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""The wheel of recon_cpp (Chapter 32, SRS-BLD-003).

Builds the wheel from recon/python/pyproject.toml with scikit-build-core, installs it into an
empty directory, and runs the C++ projector's tests (tools/test_recon_cpp.py) against the
installed module, with nothing of the build tree on the path. Exit status 77 (CTest's skip) when
scikit-build-core or build is not installed: the CI job "python" installs them from
analysis/requirements.lock.

    test_wheel.py SOURCE_DIR WORK_DIR [FETCHCONTENT_BASE_DIR]
"""
import importlib.util
import os
import pathlib
import shutil
import subprocess
import sys
import unittest

SOURCE = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 2 else None
WORK = pathlib.Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else None
DEPS = sys.argv[3] if len(sys.argv) > 3 else ""


class Wheel(unittest.TestCase):
    def test_the_wheel_installs_and_passes_the_projector_tests(self):
        # REQ: SRS-BLD-003
        shutil.rmtree(WORK, ignore_errors=True)
        out, site = WORK / "dist", WORK / "site"
        env = dict(os.environ)
        env.pop("MINIDAQ_RECON_CPP", None)
        if DEPS:  # reuse the sources the main build fetched, at the same pins
            env["SKBUILD_CMAKE_DEFINE"] = (f"FETCHCONTENT_BASE_DIR={DEPS};"
                                           "FETCHCONTENT_UPDATES_DISCONNECTED=ON")
        subprocess.run([sys.executable, "-m", "build", "--wheel", "--no-isolation", "-o", str(out),
                        str(SOURCE / "recon/python")], check=True, env=env,
                       stdout=subprocess.DEVNULL)
        (wheel,) = out.glob("minidaq_recon-*.whl")
        subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "--no-deps",
                        "--target", str(site), str(wheel)], check=True)
        installed = sorted(p.name for p in site.iterdir() if not p.name.endswith(".dist-info"))
        self.assertEqual(len(installed), 1, installed)
        self.assertTrue(installed[0].startswith("recon_cpp."), installed)
        env["PYTHONPATH"] = str(site)
        # Run from the empty work directory: Python puts the current directory on the path, and
        # CTest's is the build directory, where the build's own module is (the first version of
        # this test imported that one).
        r = subprocess.run([sys.executable, "-B", str(SOURCE / "tools/test_recon_cpp.py")],
                           env=env, capture_output=True, text=True, cwd=WORK)
        self.assertEqual(r.returncode, 0, r.stderr[-2000:])
        loaded = subprocess.run([sys.executable, "-c", "import recon_cpp; print(recon_cpp.__file__)"],
                                env=env, capture_output=True, text=True, check=True,
                                cwd=WORK).stdout
        self.assertTrue(loaded.startswith(str(site)), loaded)


if __name__ == "__main__":
    if SOURCE is None:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    missing = [m for m in ("scikit_build_core", "build", "numpy")
               if importlib.util.find_spec(m) is None]
    if missing:
        print(f"{', '.join(missing)} not installed (analysis/requirements.lock): skipped")
        sys.exit(1 if os.environ.get("MINIDAQ_ANALYSIS_REQUIRED") == "1" else 77)
    unittest.main(argv=sys.argv[:1])
