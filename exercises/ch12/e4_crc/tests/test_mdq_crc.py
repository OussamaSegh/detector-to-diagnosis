# SPDX-License-Identifier: MIT
import random
import time
import unittest
import zlib

import mdq_crc as c


def rand_bytes(rng, n):
    return bytes(rng.getrandbits(8) for _ in range(n))


class SameAsZlib(unittest.TestCase):
    def test_check_value(self):
        self.assertEqual(c.crc32_bitwise(b"123456789"), 0xCBF43926)
        self.assertEqual(c.crc32_table(b"123456789"), 0xCBF43926)
        self.assertEqual(c.crc32_table(b""), 0)

    def test_random_messages(self):
        rng = random.Random(12)
        for n in list(range(0, 40)) + [255, 1000]:
            m = rand_bytes(rng, n)
            self.assertEqual(c.crc32_bitwise(m), zlib.crc32(m), n)
            self.assertEqual(c.crc32_table(m), zlib.crc32(m), n)

    def test_in_pieces(self):
        # A block's CRC is computed as the records are written, piece by piece.
        rng = random.Random(4)
        m = rand_bytes(rng, 300)
        for cut in (0, 1, 7, 150, 299, 300):
            self.assertEqual(c.crc32_table(m[cut:], c.crc32_table(m[:cut])), zlib.crc32(m), cut)


class WhatItDetects(unittest.TestCase):
    def test_affine(self):
        # The property every argument below rests on.
        rng = random.Random(7)
        for n in (1, 16, 64):
            a, b, d = (rand_bytes(rng, n) for _ in range(3))
            x = bytes(p ^ q ^ r for p, q, r in zip(a, b, d))
            self.assertEqual(c.crc32_table(x), c.crc32_table(a) ^ c.crc32_table(b) ^ c.crc32_table(d))

    def test_every_burst_up_to_32_bits(self):
        # A burst of length L: L consecutive bits, the first and the last flipped.
        rng = random.Random(3)
        m = bytearray(rand_bytes(rng, 64))
        ref = c.crc32_table(bytes(m))
        for length in range(1, 33):
            for start in range(0, 8 * 64 - length + 1, 5):
                inner = rng.getrandbits(max(length - 2, 0)) if length > 2 else 0
                pattern = 1 | (inner << 1) | (1 << (length - 1))
                e = bytearray(m)
                for k in range(length):
                    if pattern >> k & 1:
                        bit = start + k
                        e[bit // 8] ^= 1 << (bit % 8)
                self.assertNotEqual(c.crc32_table(bytes(e)), ref, (length, start))

    def test_two_bit_errors_in_a_block(self):
        # 64 KiB of records is 524,288 bits; a block of 1 KiB already has 33 million pairs.
        self.assertEqual(c.undetected_two_bit_errors(8), 0)
        t0 = time.monotonic()
        self.assertEqual(c.undetected_two_bit_errors(1024), 0)
        self.assertLess(time.monotonic() - t0, 60.0, "count the pairs without computing each one's CRC")

    def test_some_errors_are_missed(self):
        # A CRC is a 32-bit summary: 1 error pattern in 2^32 slips through. Here is one,
        # built from the generator polynomial itself: x^32 + ... + 1 is 33 bits long.
        rng = random.Random(9)
        m = bytearray(rand_bytes(rng, 16))
        ref = c.crc32_table(bytes(m))
        g = (1 << 32) | 0x04C11DB7  # bit k is the coefficient of x^k
        # Bits go out least significant first, and the first bit sent is the highest
        # power of x: bit `within` of byte `byte` is x^(nbits - 1 - (8 * byte + within)).
        # Adding a multiple of the generator leaves the remainder, and so the CRC, unchanged.
        nbits = 8 * len(m)
        for k in range(33):
            if g >> k & 1:
                byte, within = divmod(nbits - 1 - k, 8)
                m[byte] ^= 1 << within
        self.assertEqual(c.crc32_table(bytes(m)), ref)


if __name__ == "__main__":
    unittest.main()
