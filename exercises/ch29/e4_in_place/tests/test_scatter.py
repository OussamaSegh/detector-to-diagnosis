# SPDX-License-Identifier: MIT
"""Acceptance tests of Exercise 29.4."""
import pickle
import threading
import time
import unittest

try:
    import numpy as np
except ImportError:
    raise unittest.SkipTest("numpy is not installed")

import scatter


class InPlace(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(4)
        self.values = rng.random(1000)
        self.index = rng.integers(0, 50, 1000)
        self.want = np.zeros(50)
        np.add.at(self.want, self.index, self.values)

    def test_adds_into_the_callers_array(self):
        out = np.zeros(50)
        self.assertIsNone(scatter.scatter_add(self.values, self.index, out))
        self.assertTrue(np.allclose(out, self.want, rtol=1e-12))
        scatter.scatter_add(self.values, self.index, out)  # adds, does not overwrite
        self.assertTrue(np.allclose(out, 2 * self.want, rtol=1e-12))

    def test_a_view_of_a_larger_array_is_written_in_place(self):
        image = np.zeros((10, 5))
        scatter.scatter_add(self.values, self.index, image)
        self.assertTrue(np.allclose(image.ravel(), self.want, rtol=1e-12))
        rows = np.zeros((20, 5))
        scatter.scatter_add(self.values, self.index, rows[:10])  # C-contiguous rows of it
        self.assertTrue(np.allclose(rows[:10].ravel(), self.want, rtol=1e-12))
        self.assertFalse(rows[10:].any())

    def test_inputs_of_other_types_are_converted(self):
        out = np.zeros(50)
        scatter.scatter_add(self.values.astype(np.float32), self.index.astype(np.int32), out)
        self.assertTrue(np.allclose(out, self.want, rtol=1e-6))

    def test_a_float64_output_with_a_dtype_object_of_its_own_is_written(self):
        # An unpickled array is float64 with a dtype object that is not numpy's own float64
        # (MDQ-PR-088): it is what the C++ writes, so it is accepted.
        out = pickle.loads(pickle.dumps(np.zeros(50)))
        scatter.scatter_add(self.values, self.index, out)
        self.assertTrue(np.allclose(out, self.want))

    def test_an_output_it_cannot_write_is_refused(self):
        # Each of these would be converted to a new array: the sums would go there, and the
        # caller's array would stay as it was, without an error.
        for out, reason in ((np.zeros(50, dtype=np.float32), "float64"),
                            (np.zeros((5, 10), order="F"), "C-contiguous"),
                            (np.zeros(100)[::2], "C-contiguous"),
                            (np.zeros(50, dtype=">f8"), "float64")):
            keep = out.copy()
            with self.assertRaisesRegex(ValueError, reason):
                scatter.scatter_add(self.values, self.index, out)
            self.assertTrue(np.array_equal(out, keep))
        ro = np.zeros(50)
        ro.flags.writeable = False
        with self.assertRaisesRegex(ValueError, "read-only"):
            scatter.scatter_add(self.values, self.index, ro)
        with self.assertRaises(TypeError):
            scatter.scatter_add(self.values, self.index, [0.0] * 50)

    def test_an_index_outside_is_refused_before_any_write(self):
        out = np.zeros(50)
        bad = self.index.copy()
        bad[-1] = 50
        with self.assertRaisesRegex(IndexError, "index\\[999\\] = 50, out has 50"):
            scatter.scatter_add(self.values, bad, out)
        self.assertFalse(out.any())
        bad[-1] = -1
        with self.assertRaises(IndexError):
            scatter.scatter_add(self.values, bad, out)
        with self.assertRaisesRegex(ValueError, "same length"):
            scatter.scatter_add(self.values, self.index[:10], out)

    def test_python_threads_run_during_the_call(self):
        # A long call: 3e7 additions, about 0.1 s. While the C++ holds the GIL, no Python thread
        # can run at all, however long the call takes. The other thread notes the time as it
        # counts; when the call returns, Python may switch to it before this thread reads the
        # clock, so only the first half of the call counts. On a loaded machine the other
        # thread may not get a CPU during one call (CI, MDQ-PR-086), and five calls were not
        # always enough either (MDQ-PR-095), so the call is tried for up to 20 s: with the GIL
        # released one attempt is enough, with it held none can pass however long it tries.
        n = 30_000_000
        values = np.ones(n)
        index = np.zeros(n, dtype=np.int64)
        seen = []
        # A margin of 20 s over a stall of about 50 ms.
        deadline = time.monotonic() + 20.0  # clock: deadline
        while not seen or time.monotonic() < deadline:  # clock: deadline
            out = np.zeros(1)
            seen.append(self._stamps_during(values, index, out))
            self.assertEqual(out[0], n)
            if seen[-1] > 10:
                return
        self.fail(f"the other thread did not run during the call in {len(seen)} attempts "
                  f"over 20 s: {seen[:10]} stamps in the first ten")

    @staticmethod
    def _stamps_during(values, index, out):
        stamps = []
        running = threading.Event()
        done = threading.Event()

        def count():
            running.set()
            ticks = 0
            while not done.is_set():
                ticks += 1
                if ticks % 100 == 0:
                    stamps.append(time.perf_counter())  # clock: measure (when the thread ran)

        worker = threading.Thread(target=count)  # threads: joined
        worker.start()
        running.wait()
        time.sleep(0.01)  # sleep: minimum (the counter is running)
        t0 = time.perf_counter()  # clock: measure
        scatter.scatter_add(values, index, out)
        t1 = time.perf_counter()  # clock: measure
        done.set()
        worker.join()
        return len([s for s in stamps if t0 < s < t0 + (t1 - t0) / 2])


if __name__ == "__main__":
    unittest.main()
