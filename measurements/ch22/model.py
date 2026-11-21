#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Chapter 22: the numbers the chapter computes from the SiPM's datasheet model, recomputed.

Chapter 22 quotes no measurement of a machine: its numbers come from the datasheet of the
Hamamatsu S14160-3050HS (breakdown 38 V at 25 C, 34 mV/C, overvoltage 2.7 V), from the
temperature sensor's register format (two's complement, 1/128 C per bit) and from MiniDAQ's
configuration (a 5 mV dead band). This script recomputes each so that the text can be checked
(roadmap 2.1.0, Theme H).

    python3 measurements/ch22/model.py > measurements/ch22/model.txt
"""
VBD25, K, VOV, DEAD = 38.0, 0.034, 2.7, 0.005


def overvoltage(t, bias=VBD25 + VOV):
    return bias - (VBD25 + K * (t - 25))


def temperature(word):
    """The sensor's 16-bit register in 1/128 C, two's complement."""
    return (word - 0x10000 if word & 0x8000 else word) / 128


def main():
    print("# Chapter 22: the datasheet model, recomputed\n")
    print("| Quantity | Value |")
    print("|---|---:|")
    rows = [
        ("gain lost per degree at a fixed bias", f"{100 * K / VOV:.2f}%"),
        ("breakdown shift from 25 to 29 C", f"{1000 * K * 4:.0f} mV"),
        ("overvoltage at 29 C with the bias fixed", f"{overvoltage(29):.3f} V"),
        ("gain lost at 29 C", f"{100 * (1 - overvoltage(29) / VOV):.2f}%"),
        ("register 0xF380", f"{temperature(0xF380):.2f} C"),
        ("register 0x8000 (the reset value)", f"{temperature(0x8000):.2f} C"),
        ("one bit", f"{1000 / 128:.4f} mC"),
        ("bias error if -256 C is believed", f"{K * (25 - temperature(0x8000)):.3f} V"),
        ("the dead band in degrees", f"{DEAD / K:.3f} C"),
        ("bias at 25 C", f"{VBD25 + VOV:.2f} V"),
        ("bias at 30 C", f"{VBD25 + K * 5 + VOV:.2f} V"),
        ("gain at 20 C, bias fixed at 40.7 V", f"{100 * overvoltage(20) / VOV:.1f}%"),
        ("gain at 41 C, bias fixed at 40.7 V", f"{100 * overvoltage(41) / VOV:.1f}%"),
    ]
    for name, value in rows:
        print(f"| {name} | {value} |")


if __name__ == "__main__":
    main()
