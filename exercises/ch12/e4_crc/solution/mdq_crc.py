# SPDX-License-Identifier: MIT
"""Exercise 12.4: the CRC-32 of MDQ-L1, written out, and what it can promise.

MDQ-L1 uses the CRC-32 of zlib, Ethernet and PNG: the polynomial 0x04C11DB7,
processed least significant bit first (so the constant in the code is its bit
reversal, 0xEDB88320), a start value of 0xFFFFFFFF and a final XOR with
0xFFFFFFFF. Its check value, the CRC of the nine bytes b"123456789", is
0xCBF43926.
"""

POLY_REFLECTED = 0xEDB88320  # 0x04C11DB7 with its 32 bits reversed


def crc32_bitwise(data, crc=0):
    """One bit at a time. `crc` is the CRC of the bytes before `data`, as in zlib.crc32."""
    crc ^= 0xFFFFFFFF  # undo the previous final XOR: this is the register's real state
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ (POLY_REFLECTED if crc & 1 else 0)
    return crc ^ 0xFFFFFFFF


def make_table():
    """table[b]: what eight steps of crc32_bitwise do to a register holding b and zeros."""
    table = []
    for b in range(256):
        c = b
        for _ in range(8):
            c = (c >> 1) ^ (POLY_REFLECTED if c & 1 else 0)
        table.append(c)
    return table


TABLE = make_table()


def crc32_table(data, crc=0):
    """One byte at a time, with the table: the same result, eight times fewer steps."""
    crc ^= 0xFFFFFFFF
    for byte in data:
        crc = (crc >> 8) ^ TABLE[(crc ^ byte) & 0xFF]
    return crc ^ 0xFFFFFFFF


def undetected_two_bit_errors(n_bytes, crc=crc32_table):
    """How many of the n_bits * (n_bits - 1) / 2 two-bit errors in an n_bytes message
    leave its CRC unchanged.

    The CRC is affine over XOR: for messages of one length, crc(a ^ b ^ c) =
    crc(a) ^ crc(b) ^ crc(c). So the change an error e makes, crc(m ^ e) ^ crc(m),
    does not depend on m, and the change of two flips is the XOR of the changes of
    each. Two flips cancel exactly when their single-flip changes are equal: count
    the equal pairs among n_bits values instead of computing every pair's CRC.
    """
    zero = bytes(n_bytes)
    base = crc(zero)
    counts = {}
    for bit in range(8 * n_bytes):
        e = bytearray(n_bytes)
        e[bit // 8] = 1 << (bit % 8)
        s = crc(bytes(e)) ^ base
        counts[s] = counts.get(s, 0) + 1
    return sum(k * (k - 1) // 2 for k in counts.values())
