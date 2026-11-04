#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""The test cmake.consumer (Chapter 32, SRS-BLD-001).

Runs consumer_test.cmake, which installs the projector library from this build into an empty
prefix, checks that no installed CMake file names a path of the build or the source tree, then
configures, builds and runs recon/tests/consumer, a project that finds the library with
find_package(recon) and checks the projector's adjoint property.

    test_consumer.py CMAKE BUILD_DIR SOURCE_DIR WORK_DIR GENERATOR CXX [CXX_FLAGS [LINKER_FLAGS]]
"""
import pathlib
import subprocess
import sys
import unittest

ARGS = sys.argv[1:]


class Consumer(unittest.TestCase):
    def test_an_installed_projector_is_found_built_against_and_run(self):
        # REQ: SRS-BLD-001
        cmake, build, source, work, generator, cxx = ARGS[:6]
        flags = (ARGS[6:] + ["", ""])[:2]
        script = pathlib.Path(__file__).resolve().parent / "consumer_test.cmake"
        r = subprocess.run([cmake, f"-DBUILD_DIR={build}", f"-DSOURCE_DIR={source}",
                            f"-DWORK_DIR={work}", f"-DGENERATOR={generator}", f"-DCXX={cxx}",
                            f"-DCXX_FLAGS={flags[0]}", f"-DLINKER_FLAGS={flags[1]}",
                            "-P", str(script)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, (r.stdout + r.stderr)[-3000:])
        self.assertIn("ok: <Ax, y>", r.stdout + r.stderr)


if __name__ == "__main__":
    if len(ARGS) < 6:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    unittest.main(argv=sys.argv[:1])
