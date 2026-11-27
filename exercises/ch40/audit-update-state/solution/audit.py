# SPDX-License-Identifier: MIT
"""Exercise 40.5 (A): tests of the agent's open_state, with every JSON type in every field."""
import json
import unittest

GOOD = {"good": "a", "good_version": "2.3.0", "trial": "b", "trial_version": "3.0.0"}
OTHER_TYPES = [7, 2.5, True, [], ["3.0.0"], {}, {"v": 1}]


class Audit(unittest.TestCase):
    subject = None  # set by tests/test_audit.py

    def open(self, d):
        return self.subject.open_state(json.dumps(d))

    def damaged(self, d):
        """Damaged and nothing else: any other exception stops the updater with a library's
        message, and an accepted store is a store trusted that should not be."""
        try:
            s = self.open(d)
        except self.subject.Damaged:
            return
        except Exception as e:  # noqa: BLE001 - any other exception is the defect
            self.fail(f"{d!r}: {type(e).__name__} instead of Damaged: {e}")
        self.fail(f"{d!r} was trusted as {s}")

    def test_a_store_with_a_trial_is_read(self):
        s = self.open(GOOD)
        self.assertEqual(tuple(s), ("a", "2.3.0", "b", "3.0.0"))

    def test_a_store_without_a_trial_is_read(self):
        s = self.open({"good": "b", "good_version": "2.3.0", "trial": None})
        self.assertEqual((s.good, s.trial, s.trial_version), ("b", None, ""))

    def test_a_missing_or_wrong_good_or_trial_is_damaged(self):
        self.damaged({"trial": None})
        self.damaged({"good": "a"})
        self.damaged(dict(GOOD, good="c"))
        self.damaged(dict(GOOD, trial="a"))  # the trial in the good slot

    def test_a_trial_of_another_type_is_damaged_not_forgotten(self):
        for value in OTHER_TYPES:
            with self.subTest(trial=value):
                self.damaged(dict(GOOD, trial=value))

    def test_a_version_of_another_type_is_damaged_not_a_crash(self):
        for key in ("good_version", "trial_version"):
            for value in OTHER_TYPES + [None]:
                with self.subTest(key=key, value=value):
                    self.damaged(dict(GOOD, **{key: value}))

    def test_text_that_is_not_an_object_is_damaged(self):
        for text in ("", "{", "[]", "null", '"a"'):
            with self.subTest(text=text):
                with self.assertRaises(self.subject.Damaged):
                    self.subject.open_state(text)
