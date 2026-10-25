"""Acceptance tests for Exercise 16.5: document control between two releases."""
import pathlib
import unittest

import doc_control

HERE = pathlib.Path(__file__).resolve().parent


def release(name):
    root = HERE / name
    return {p.relative_to(root).as_posix(): p.read_text() for p in sorted(root.rglob("*.md"))}


OLD, NEW = release("old"), release("new")
IU = "docs/regulatory/intended-use.md"
SDP = "docs/regulatory/sdp.md"


def changed(path, edit):
    new = dict(NEW)
    new[path] = edit(new[path])
    return doc_control.problems(OLD, new)


def about(errors, path):
    return [e for e in errors if e.startswith(path)]


class Release(unittest.TestCase):
    def test_the_fixture_release_is_consistent(self):
        self.assertEqual(doc_control.problems(OLD, NEW), [])

    def test_versions_and_history(self):
        self.assertEqual(doc_control.version(NEW[SDP]), 3)
        self.assertEqual(sorted(doc_control.history(NEW[SDP])), [1, 2, 3])
        self.assertEqual(doc_control.history("# No table\n\nVersion 1\n"), {})


class Rules(unittest.TestCase):
    def test_a_change_needs_a_new_version(self):
        errors = doc_control.problems(OLD, {**NEW, IU: OLD[IU] + "\nA new sentence.\n"})
        self.assertTrue(any("still version 1" in e for e in about(errors, IU)), errors)

    def test_an_unchanged_document_keeps_its_version(self):
        self.assertEqual(about(doc_control.problems(OLD, NEW), "docs/coding-standard.md"), [])

    def test_the_version_must_be_the_last_history_row(self):
        errors = changed(IU, lambda t: t.replace("Version 2 (", "Version 3 ("))
        self.assertTrue(about(errors, IU), errors)

    def test_history_rows_are_numbered_without_gaps(self):
        errors = changed(SDP, lambda t: t.replace("| 2 | Risk management review before each release. |\n", ""))
        self.assertTrue(any("1, 2, 3" in e for e in about(errors, SDP)), errors)

    def test_two_versions_in_one_release_are_allowed(self):
        self.assertEqual(about(doc_control.problems(OLD, NEW), SDP), [])

    def test_a_version_never_goes_down(self):
        old = {**OLD, IU: NEW[IU]}
        errors = doc_control.problems(old, {**NEW, IU: OLD[IU]})
        self.assertTrue(any("down" in e for e in about(errors, IU)), errors)

    def test_history_is_never_rewritten(self):
        errors = changed(IU, lambda t: t.replace("| 1 | First version. |", "| 1 | First approved version. |"))
        self.assertTrue(any("row 1" in e for e in about(errors, IU)), errors)

    def test_a_new_document_starts_at_version_one(self):
        rmp = "docs/regulatory/risk/risk-management-plan.md"
        errors = changed(rmp, lambda t: t.replace("Version 1 (", "Version 2 (").replace(
            "| 1 | First version. |", "| 1 | First version. |\n| 2 | Reviewed. |"))
        self.assertTrue(any("version 1" in e for e in about(errors, rmp)), errors)

    def test_a_withdrawn_document_is_reported(self):
        new = dict(NEW)
        del new["docs/coding-standard.md"]
        self.assertTrue(about(doc_control.problems(OLD, new), "docs/coding-standard.md"))

    def test_a_document_without_a_version_is_reported(self):
        errors = changed(IU, lambda t: t.replace("Version 2 (MiniDAQ 0.3.0). ", ""))
        self.assertTrue(about(errors, IU), errors)


if __name__ == "__main__":
    unittest.main()
