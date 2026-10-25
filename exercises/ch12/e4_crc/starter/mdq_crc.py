# SPDX-License-Identifier: MIT
"""Exercise 12.4: the CRC-32 of MDQ-L1, written out, and what it can promise.

MDQ-L1 uses the CRC-32 of zlib, Ethernet and PNG. This version follows a
textbook's description of a CRC and does not give zlib's numbers; find out why.
undetected_two_bit_errors is yours to write.
"""

POLY = 0x04C11DB7  # the CRC-32 polynomial


def crc32_bitwise(data, crc=0):
    """One bit at a time. `crc` is the CRC of the bytes before `data`, as in zlib.crc32."""
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ (POLY if crc & 1 else 0)
    return crc


def make_table():
    """table[b]: what eight steps of crc32_bitwise do to a register holding b and zeros."""
    table = []
    for b in range(256):
        c = b
        for _ in range(8):
            c = (c >> 1) ^ (POLY if c & 1 else 0)
        table.append(c)
    return table


TABLE = make_table()


def crc32_table(data, crc=0):
    """One byte at a time, with the table: the same result, eight times fewer steps."""
    for byte in data:
        crc = (crc >> 8) ^ TABLE[(crc ^ byte) & 0xFF]
    return crc


def undetected_two_bit_errors(n_bytes, crc=crc32_table):
    """How many of the n_bits * (n_bits - 1) / 2 two-bit errors in an n_bytes message
    leave its CRC unchanged. It must take seconds, not hours, for n_bytes = 1024."""
    raise NotImplementedError
