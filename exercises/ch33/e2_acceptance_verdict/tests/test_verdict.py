# SPDX-License-Identifier: MIT
"""Acceptance tests of Exercise 33.2."""
import json
import pathlib
import tempfile
import unittest

from verdict import accepted, verdict

COMMIT = "392e4ae9d5a290ae371394b2858172f8a07cfd1e"
AT_LEAST = {"id": "ACC-01", "evidence": "pipeline.json", "limit": 20.0, "at_least": True}
AT_MOST = {"id": "ACC-04", "evidence": "latency.json", "limit": 10.0, "at_least": False}


class Verdict(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.out = pathlib.Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def put(self, name, value, commit="392e4ae", dirty=False, raw=None):
        text = raw if raw is not None else json.dumps(
            {"commit": commit, "dirty": dirty, "value": value})
        (self.out / name).write_text(text)

    def v(self, criterion, candidate=COMMIT):
        return verdict(criterion, self.out, candidate)[0]

    def test_pass_and_fail_at_the_limits(self):
        for value, expected in ((20.0, "PASS"), (20.001, "PASS"), (19.999, "FAIL"), (0, "FAIL")):
            self.put("pipeline.json", value)
            self.assertEqual(self.v(AT_LEAST), expected, value)
        for value, expected in ((10.0, "PASS"), (9.99, "PASS"), (10.01, "FAIL"), (11, "FAIL")):
            self.put("latency.json", value)
            self.assertEqual(self.v(AT_MOST), expected, value)

    def test_a_file_that_is_not_there_is_missing(self):
        self.assertEqual(self.v(AT_LEAST), "MISSING")

    def test_evidence_that_cannot_be_read_is_missing(self):
        for raw in ("{not json", "[1, 2]", "", json.dumps({"commit": "392e4ae", "dirty": False})):
            self.put("pipeline.json", None, raw=raw)
            self.assertEqual(self.v(AT_LEAST), "MISSING", raw)

    def test_a_value_that_is_not_a_number_is_missing(self):
        for value in ("37.4", None, True, [37.4]):
            self.put("pipeline.json", value)
            self.assertEqual(self.v(AT_LEAST), "MISSING", repr(value))

    def test_a_value_that_is_not_finite_is_missing(self):
        for raw in ('{"commit": "392e4ae", "dirty": false, "value": NaN}',
                    '{"commit": "392e4ae", "dirty": false, "value": Infinity}'):
            self.put("pipeline.json", None, raw=raw)
            self.put("latency.json", None, raw=raw.replace("Infinity", "-Infinity"))
            self.assertEqual(self.v(AT_LEAST), "MISSING", raw)
            self.assertEqual(self.v(AT_MOST), "MISSING", raw)

    def test_evidence_of_another_commit_or_a_dirty_tree_is_stale(self):
        self.put("pipeline.json", 37.4, commit="1572784")
        self.assertEqual(self.v(AT_LEAST), "STALE")
        self.put("pipeline.json", 37.4, dirty=True)
        self.assertEqual(self.v(AT_LEAST), "STALE")
        self.put("pipeline.json", 5.0, commit="1572784")
        self.assertEqual(self.v(AT_LEAST), "STALE", "stale is checked before the target")

    def test_short_and_long_forms_of_a_commit_match_and_a_too_short_one_does_not(self):
        self.put("pipeline.json", 37.4, commit=COMMIT)
        self.assertEqual(self.v(AT_LEAST, candidate="392e4ae"), "PASS")
        self.put("pipeline.json", 37.4, commit="392e4ae")
        self.assertEqual(self.v(AT_LEAST, candidate=COMMIT), "PASS")
        self.put("pipeline.json", 37.4, commit="392e")
        self.assertEqual(self.v(AT_LEAST, candidate=COMMIT), "STALE")
        self.put("pipeline.json", 37.4, commit=COMMIT)
        self.assertEqual(self.v(AT_LEAST, candidate="3"), "STALE")

    def test_a_verdict_comes_with_what_was_found(self):
        self.put("pipeline.json", 37.4)
        found = verdict(AT_LEAST, self.out, COMMIT)[1]
        self.assertIsInstance(found, str)
        self.assertIn("37.4", found)


class Accepted(unittest.TestCase):
    def test_accepted_only_when_every_verdict_passes(self):
        self.assertTrue(accepted(["PASS", "PASS"]))
        for other in ("FAIL", "MISSING", "STALE"):
            self.assertFalse(accepted(["PASS", other]), other)

    def test_no_verdicts_is_not_an_acceptance(self):
        self.assertFalse(accepted([]))

    def test_a_generator_of_verdicts_is_accepted_like_a_list(self):
        self.assertTrue(accepted(v for v in ["PASS"]))


if __name__ == "__main__":
    unittest.main()
