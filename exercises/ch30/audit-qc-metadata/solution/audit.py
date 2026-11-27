# SPDX-License-Identifier: MIT
"""Exercise 30.5 (A): tests of the agent's read_metadata, from every JSON type in every place
the report reads."""
import unittest

JSON_VALUES = {"a list": [1], "an object": {"n": 1}, "a string": "100000", "null": None,
               "true": True, "false": False, "a fraction": 2.5, "zero": 0, "negative": -5}


class Audit(unittest.TestCase):
    subject = None  # set by tests/test_audit.py

    def read(self, meta):
        return self.subject.read_metadata(meta)

    def refused(self, meta):
        """FormatError, and nothing else: anything else ends the report with a traceback."""
        try:
            self.read(meta)
        except self.subject.FormatError:
            return
        except Exception as e:  # noqa: BLE001 - any other exception is the defect
            self.fail(f"{meta!r}: {type(e).__name__} instead of FormatError: {e}")
        self.fail(f"{meta!r} was accepted")

    def test_reads_a_complete_run(self):
        m = self.read({"scanner": {"crystals": 1024}, "records": {"delayed_window_ps": 80_000}})
        self.assertEqual((m.crystals, m.delayed_window_ps), (1024, 80_000))

    def test_a_missing_window_takes_the_default(self):
        for meta in ({"scanner": {"crystals": 8}}, {"scanner": {"crystals": 8}, "records": {}}):
            self.assertEqual(self.read(meta).delayed_window_ps,
                             self.subject.DEFAULT_DELAYED_WINDOW_PS)

    def test_missing_scanner_or_crystals_is_an_error(self):
        self.refused({})
        self.refused({"scanner": {}})

    def test_crystals_of_any_other_type_or_value_is_an_error(self):
        for what, value in JSON_VALUES.items():
            with self.subTest(what):
                self.refused({"scanner": {"crystals": value}})

    def test_a_window_of_any_other_type_or_value_is_an_error(self):
        for what, value in JSON_VALUES.items():
            with self.subTest(what):
                self.refused({"scanner": {"crystals": 8}, "records": {"delayed_window_ps": value}})

    def test_scanner_or_records_that_is_not_an_object_is_an_error(self):
        for value in ([], "x", 3, None, True):
            with self.subTest(value=value):
                self.refused({"scanner": value})
                self.refused({"scanner": {"crystals": 8}, "records": value})

    def test_metadata_that_is_not_an_object_is_an_error(self):
        for value in ([], "x", 3, None):
            with self.subTest(value=value):
                self.refused(value)
