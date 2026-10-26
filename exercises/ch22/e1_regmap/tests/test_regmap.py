# SPDX-License-Identifier: MIT
"""Acceptance tests for Exercise 22.1. Run with the starter or solution directory on PYTHONPATH
(CTest does this)."""
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

from regmap import SpecError, header, load

GOOD = """
[map]
name = "demo"

[[register]]
name = "control"
address = 0x008
access = "rw"
reset = 0x00000001
fields = [{ name = "enable", lsb = 0, width = 1 }, { name = "mode", lsb = 4, width = 3 }]

[[register]]
name = "status"
address = 0x00C
access = "ro"
fields = [{ name = "ready", lsb = 0, width = 1 }, { name = "count", lsb = 16, width = 16 }]
"""

CHECK = r"""
#include <array>
#include <cstdint>
#include "demo.hpp"

int main() {
  std::array<std::uint32_t, 16> regs{};  // a fake block of registers, indexed by address / 4
  regs[demo::CONTROL_ADDR / 4] = demo::CONTROL_RESET;
  auto& control = regs[demo::CONTROL_ADDR / 4];
  control = (control & ~demo::CONTROL_MODE_MASK) | ((5U << demo::CONTROL_MODE_SHIFT) & demo::CONTROL_MODE_MASK);
  const auto mode = (control & demo::CONTROL_MODE_MASK) >> demo::CONTROL_MODE_SHIFT;
  const auto enable = (control & demo::CONTROL_ENABLE_MASK) >> demo::CONTROL_ENABLE_SHIFT;
  regs[demo::STATUS_ADDR / 4] = 0xBEEF0001U;
  const auto count = (regs[demo::STATUS_ADDR / 4] & demo::STATUS_COUNT_MASK) >> demo::STATUS_COUNT_SHIFT;
  return (mode == 5 && enable == 1 && control == 0x51 && count == 0xBEEF) ? 0 : 1;
}
"""


def register(body: str) -> str:
    return '[map]\nname = "demo"\n\n[[register]]\nname = "bad"\n' + body


class Load(unittest.TestCase):
    def refused(self, text, *words):
        with self.assertRaises(SpecError) as e:
            load(text)
        for w in words:
            self.assertIn(w, str(e.exception))

    def test_a_good_specification_is_accepted(self):
        spec = load(GOOD)
        self.assertEqual([r["name"] for r in spec["register"]], ["control", "status"])

    def test_an_address_must_be_a_multiple_of_4(self):
        self.refused(register('address = 0x006\naccess = "rw"\n'), "bad")

    def test_two_registers_cannot_share_an_address_or_a_name(self):
        self.refused(GOOD + '\n[[register]]\nname = "other"\naddress = 0x00C\naccess = "ro"\n', "other")
        self.refused(GOOD + '\n[[register]]\nname = "status"\naddress = 0x010\naccess = "ro"\n', "status")

    def test_the_access_must_be_known(self):
        self.refused(register('address = 0\naccess = "rc"\n'), "bad")

    def test_a_field_lies_inside_32_bits(self):
        self.refused(register('address = 0\naccess = "rw"\nfields = [{ name = "x", lsb = 30, width = 3 }]\n'), "bad")
        self.refused(register('address = 0\naccess = "rw"\nfields = [{ name = "x", lsb = 0, width = 0 }]\n'), "bad")

    def test_fields_do_not_overlap(self):
        self.refused(register('address = 0\naccess = "rw"\n'
                              'fields = [{ name = "x", lsb = 0, width = 4 }, { name = "y", lsb = 3, width = 2 }]\n'),
                     "bad")

    def test_the_reset_value_sets_only_field_bits(self):
        self.refused(register('address = 0\naccess = "rw"\nreset = 0x2\nfields = [{ name = "x", lsb = 0, width = 1 }]\n'),
                     "bad")


class Header(unittest.TestCase):
    def test_constants_for_every_register_and_field(self):
        h = header(load(GOOD))
        for line in ("#pragma once", "namespace demo {",
                     "inline constexpr std::uint32_t CONTROL_ADDR = 0x008;",
                     "inline constexpr std::uint32_t CONTROL_RESET = 0x00000001;",
                     "inline constexpr std::uint32_t CONTROL_MODE_SHIFT = 4;",
                     "inline constexpr std::uint32_t CONTROL_MODE_MASK = 0x00000070;",
                     "inline constexpr std::uint32_t STATUS_RESET = 0x00000000;",
                     "inline constexpr std::uint32_t STATUS_COUNT_MASK = 0xFFFF0000;"):
            self.assertIn(line, h.splitlines())

    def test_the_header_compiles_and_its_fields_work(self):
        cxx = os.environ.get("CXX") or shutil.which("c++")
        if not cxx:
            self.skipTest("no C++ compiler (CXX or c++)")
        with tempfile.TemporaryDirectory() as tmp:
            t = pathlib.Path(tmp)
            (t / "demo.hpp").write_text(header(load(GOOD)))
            (t / "check.cpp").write_text(CHECK)
            subprocess.run([cxx, "-std=c++20", "-Wall", "-Werror", "-o", str(t / "check"), str(t / "check.cpp")],
                           check=True, cwd=tmp)
            self.assertEqual(subprocess.run([str(t / "check")]).returncode, 0)


if __name__ == "__main__":
    unittest.main()
