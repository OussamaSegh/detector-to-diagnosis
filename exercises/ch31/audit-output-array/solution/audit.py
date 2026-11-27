# SPDX-License-Identifier: MIT
"""Exercise 31.5 (A): tests of the agent's writable_out, with arrays from where a scientist
gets them: made here, loaded, sent from another process, viewed, and the ones to refuse."""
import io
import pickle
import unittest

import numpy as np


class Audit(unittest.TestCase):
    subject = None  # set by tests/test_audit.py

    def taken(self, out, shape=(4, 3)):
        self.assertIs(self.subject.writable_out(out, shape), out)

    def refused(self, out, shape=(4, 3)):
        with self.assertRaises(ValueError):
            self.subject.writable_out(out, shape)

    def test_a_new_float64_array_of_the_right_shape_is_taken(self):
        self.taken(np.zeros((4, 3)))
        self.taken(np.empty((4, 3), dtype="f8"))
        self.taken(np.zeros((4, 3), dtype=np.dtype("<f8") if np.little_endian else np.dtype(">f8")))

    def test_an_array_sent_from_another_process_is_taken(self):
        # multiprocessing and joblib pickle their arguments.
        self.taken(pickle.loads(pickle.dumps(np.zeros((4, 3)))))

    def test_an_array_loaded_from_a_file_is_taken(self):
        buf = io.BytesIO()
        np.save(buf, np.zeros((4, 3)), allow_pickle=False)
        buf.seek(0)
        self.taken(np.load(buf))

    def test_an_array_whose_byte_order_was_swapped_twice_is_taken(self):
        a = np.zeros((4, 3))
        self.taken(a.view(a.dtype.newbyteorder().newbyteorder()))

    def test_a_big_endian_array_is_refused(self):
        self.refused(np.zeros((4, 3), dtype=">f8" if np.little_endian else "<f8"))

    def test_other_types_shapes_and_layouts_are_refused(self):
        self.refused(np.zeros((4, 3), dtype=np.float32))
        self.refused(np.zeros((4, 3), dtype=np.int64))
        self.refused(np.zeros((3, 4)))
        self.refused(np.zeros(12))
        self.refused(np.zeros((3, 4)).T)  # the right shape, Fortran order
        self.refused(np.zeros((4, 6))[:, ::2])  # the right shape, a strided view
        self.refused([[0.0] * 3] * 4)

    def test_a_read_only_array_is_refused(self):
        a = np.zeros((4, 3))
        a.flags.writeable = False
        self.refused(a)
