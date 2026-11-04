# SPDX-License-Identifier: MIT
"""Acceptance tests of Exercise 35.3."""
import struct
import unittest

from pdata import messages


def element(group, el, value):
    return struct.pack("<HHI", group, el, len(value)) + value


def command(has_dataset=True):
    return (element(0, 0x0100, struct.pack("<H", 1))
            + element(0, 0x0800, struct.pack("<H", 0x0000 if has_dataset else 0x0101)))


def pdv(cid, is_command, last, data):
    return struct.pack(">IBB", len(data) + 2, cid, (1 if is_command else 0) | (2 if last else 0)) + data


def pdu(*items):
    return 4, b"".join(items)


DATA = bytes(range(256)) * 8


class Messages(unittest.TestCase):
    def test_a_message_in_one_pdu(self):
        got = list(messages([pdu(pdv(1, True, True, command()), pdv(1, False, True, DATA))]))
        self.assertEqual(got, [(1, command(), DATA)])

    def test_a_data_set_in_many_fragments_across_pdus(self):
        pieces = [DATA[i:i + 300] for i in range(0, len(DATA), 300)]
        stream = [pdu(pdv(3, True, True, command()))]
        stream += [pdu(pdv(3, False, i == len(pieces) - 1, p)) for i, p in enumerate(pieces)]
        self.assertEqual(list(messages(stream)), [(3, command(), DATA)])

    def test_a_command_in_two_fragments(self):
        c = command()
        stream = [pdu(pdv(1, True, False, c[:5])), pdu(pdv(1, True, True, c[5:]),
                                                       pdv(1, False, True, DATA))]
        self.assertEqual(list(messages(stream)), [(1, c, DATA)])

    def test_several_pdvs_in_one_pdu_end_one_message_and_start_the_next(self):
        stream = [pdu(pdv(1, True, True, command()), pdv(1, False, False, DATA[:100])),
                  pdu(pdv(1, False, True, DATA[100:]), pdv(1, True, True, command()),
                      pdv(1, False, True, b"ab"))]
        self.assertEqual(list(messages(stream)), [(1, command(), DATA), (1, command(), b"ab")])

    def test_an_echo_then_a_store(self):
        stream = [pdu(pdv(1, True, True, command(has_dataset=False))),
                  pdu(pdv(3, True, True, command()), pdv(3, False, True, DATA))]
        self.assertEqual(list(messages(stream)),
                         [(1, command(has_dataset=False), None), (3, command(), DATA)])

    def test_a_pdu_of_another_type_is_refused(self):
        with self.assertRaises(ValueError):
            list(messages([pdu(pdv(1, True, True, command())), (5, b"\0\0\0\0")]))

    def test_a_pdv_that_does_not_fit_its_pdu_is_refused(self):
        bad = struct.pack(">IBB", 100, 1, 3) + b"short"
        with self.assertRaises(ValueError):
            list(messages([(4, bad)]))
        with self.assertRaises(ValueError):
            list(messages([(4, struct.pack(">IBB", 1, 1, 3))]))

    def test_a_fragment_on_another_context_is_refused(self):
        with self.assertRaises(ValueError):
            list(messages([pdu(pdv(1, True, True, command()), pdv(3, False, True, DATA))]))

    def test_fragments_out_of_order_are_refused(self):
        with self.assertRaises(ValueError):
            list(messages([pdu(pdv(1, False, True, DATA))]))
        with self.assertRaises(ValueError):
            list(messages([pdu(pdv(1, True, True, command()), pdv(1, True, True, command()))]))

    def test_input_that_ends_in_the_middle_of_a_message_is_refused(self):
        with self.assertRaises(ValueError):
            list(messages([pdu(pdv(1, True, True, command()), pdv(1, False, False, DATA))]))


if __name__ == "__main__":
    unittest.main()
