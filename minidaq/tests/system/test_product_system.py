#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""System tests of the product build (CR-0029): the shipped server has no simulator.

A product build (preset product, CMake option MINIDAQ_WITH_SIMULATOR off) leaves the synthetic
source and the simulated boards out of minidaq_server, and refuses a configuration that asks for
them. The same tests run in a development build, where they check the opposite, so that a check
that could never fail is noticed. CTest sets MINIDAQ_PRODUCT to 1 in a product build.
"""
import os
import re
import shutil
import subprocess
import unittest

from systest import Ctl, Server, SystemTest, app, run_config, write_json

PRODUCT = os.environ.get("MINIDAQ_PRODUCT", "0") == "1"
REFUSAL = "this is a product build: the simulator is not part of it"
# Code of the simulator: its namespace and the simulated board.
SIMULATOR_SYMBOL = re.compile(r"minidaq::sim::|minidaq::hw::FakeBoard")


class Product(SystemTest):
    def test_the_product_refuses_the_synthetic_source_when_it_is_configured(self):
        # REQ: SRS-PLT-012
        with Server(self.tmp) as server:
            ctl = Ctl(server)
            hello = ctl.ok("hello")
            self.assertEqual(hello["simulator"], not PRODUCT)
            code, response, _ = ctl("configure", str(write_json(self.tmp / "run.json", run_config(self.tmp))))
            if PRODUCT:
                self.assertEqual(code, 1)
                self.assertEqual(response["error"]["code"], "config_error")
                self.assertIn(REFUSAL, response["error"]["message"])
                self.assertEqual(ctl.status()["state"], "idle")
            else:
                self.assertEqual(code, 0, response)

    def test_the_product_refuses_simulated_boards_at_start_up(self):
        # REQ: SRS-PLT-012
        description = write_json(self.tmp / "hardware.json", {
            "schema_version": "1.0", "backend": "simulated", "boards": [{"slot": 0}]})
        if PRODUCT:
            p = subprocess.run([app("minidaq_server"), "--port", "0", "--hardware", str(description)],
                               capture_output=True, text=True, timeout=30,
                               env=dict(os.environ, MINIDAQ_RUNTIME_DIR=str(self.tmp)))
            self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
            self.assertIn(f'hardware: hardware backend "simulated": {REFUSAL}', p.stderr)
        else:
            with Server(self.tmp, "--hardware", str(description)) as server:
                self.assertIn("simulated", Ctl(server).status()["hardware"]["description"])

    @unittest.skipUnless(shutil.which("nm"), "needs nm (GNU binutils)")
    def test_the_product_server_contains_no_code_of_the_simulator(self):
        # REQ: SRS-PLT-012
        symbols = subprocess.run(["nm", "-C", app("minidaq_server")], capture_output=True, text=True,
                                 check=True).stdout
        found = sorted({line.split(" ", 2)[-1] for line in symbols.splitlines() if SIMULATOR_SYMBOL.search(line)})
        if PRODUCT:
            self.assertEqual(found, [], "simulator code in the product server")
        else:
            self.assertNotEqual(found, [], "the check finds nothing even where the simulator is linked")


if __name__ == "__main__":
    unittest.main()
