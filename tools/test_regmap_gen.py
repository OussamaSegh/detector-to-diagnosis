#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Tests of tools/regmap_gen.py (Chapter 22)."""
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from regmap_gen import SpecError, doc, header, load, main  # noqa: E402

GOOD = """
[map]
name = "demo"
version = "0.1"

[[register]]
name = "control"
address = 0x0
access = "rw"
reset = 0x1
fields = [{ name = "enable", lsb = 0, width = 1 }, { name = "mode", lsb = 4, width = 3 }]

[[register]]
name = "temperature"
address = 0x4
access = "ro"
fields = [{ name = "celsius_q7", lsb = 0, width = 16, signed = true, unit = "1/128 C" }]
"""


def spec_with(register: str) -> str:
    return '[map]\nname = "demo"\n\n[[register]]\n' + register


class Validation(unittest.TestCase):
    def assert_refused(self, text: str, message: str) -> None:
        with self.assertRaises(SpecError) as e:
            load(text)
        self.assertIn(message, str(e.exception))

    def test_a_good_specification_loads(self):
        # REQ: SRS-HW-008
        self.assertEqual(len(load(GOOD)["register"]), 2)

    def test_an_address_must_be_aligned_and_unique(self):
        # REQ: SRS-HW-008
        self.assert_refused(spec_with('name = "a"\naddress = 0x2\naccess = "rw"\n'), "multiple of 4")
        twice = GOOD + '\n[[register]]\nname = "again"\naddress = 0x4\naccess = "ro"\n'
        self.assert_refused(twice, "address 0x004 is also temperature")

    def test_fields_must_fit_and_not_overlap(self):
        # REQ: SRS-HW-008
        self.assert_refused(
            spec_with('name = "a"\naddress = 0\naccess = "rw"\nfields = [{ name = "x", lsb = 30, width = 4 }]\n'),
            "not inside 32 bits")
        self.assert_refused(
            spec_with('name = "a"\naddress = 0\naccess = "rw"\n'
                      'fields = [{ name = "x", lsb = 0, width = 4 }, { name = "y", lsb = 3, width = 2 }]\n'),
            "overlaps another field")

    def test_the_reset_value_sets_only_field_bits(self):
        # REQ: SRS-HW-008
        self.assert_refused(
            spec_with('name = "a"\naddress = 0\naccess = "rw"\nreset = 0x10\n'
                      'fields = [{ name = "x", lsb = 0, width = 4 }]\n'),
            "outside every field")

    def test_access_must_be_known(self):
        # REQ: SRS-HW-008
        self.assert_refused(spec_with('name = "a"\naddress = 0\naccess = "rc"\n'), "access must be one of")


class Output(unittest.TestCase):
    def test_the_header_has_a_type_per_register_and_field(self):
        # REQ: SRS-HW-008
        h = header(load(GOOD), "demo.toml")
        self.assertIn("struct Control : Register<0x000, Access::rw, 0x00000001> {", h)
        self.assertIn("struct Mode : Field<Control, 4, 3> {};", h)
        self.assertIn("struct CelsiusQ7 : Field<Temperature, 0, 16, true> {};", h)
        self.assertIn("std::array<RegisterInfo, 2> registers", h)

    def test_the_document_has_a_row_per_field(self):
        # REQ: SRS-HW-008
        d = doc(load(GOOD), "demo.toml")
        self.assertIn("| `0x004` | `temperature` | ro | `0x00000000` | `celsius_q7` | 15:0 | (1/128 C), signed |", d)

    def test_check_fails_while_an_output_is_out_of_date(self):
        # REQ: SRS-HW-008
        with tempfile.TemporaryDirectory() as tmp:
            t = pathlib.Path(tmp)
            (t / "demo.toml").write_text(GOOD)
            args = [str(t / "demo.toml"), "--header", str(t / "demo.hpp"), "--doc", str(t / "demo.md")]
            self.assertEqual(main(args + ["--check"]), 1)
            self.assertEqual(main(args), 0)
            self.assertEqual(main(args + ["--check"]), 0)
            (t / "demo.toml").write_text(GOOD.replace('version = "0.1"', 'version = "0.2"'))
            self.assertEqual(main(args + ["--check"]), 1)
            (t / "demo.toml").write_text("[map]\n")
            self.assertEqual(main(args + ["--check"]), 2)


if __name__ == "__main__":
    unittest.main()
