"""Acceptance tests for Exercise 14.4: a trace matrix generated from requirement tags."""
import pathlib
import unittest

import trace_matrix as tm

FIXTURE = pathlib.Path(__file__).resolve().parent / "fixture"


def analyse(srs_text, tags):
    reqs, evidence, dups = tm.parse_srs(srs_text)
    return tm.check(reqs, evidence, dups, tags)


SRS = (FIXTURE / "docs/regulatory/srs.md").read_text()


class Tags(unittest.TestCase):
    def test_cpp_tags_belong_to_the_test_above_them(self):
        tags = tm.find_tags("t.cpp", "TEST(A, B) {\n  // REQ: SRS-AAA-001\n}\nTEST_F(F, G) {\n  // REQ: SRS-AAA-002\n}\n")
        self.assertEqual(tags, [("SRS-AAA-001", "A.B", "t.cpp"), ("SRS-AAA-002", "F.G", "t.cpp")])

    def test_one_tag_may_list_several_requirements(self):
        tags = tm.find_tags("t.cpp", "TEST(A, B) {\n  // REQ: SRS-AAA-001, SRS-BBB-002\n}\n")
        self.assertEqual([t[0] for t in tags], ["SRS-AAA-001", "SRS-BBB-002"])

    def test_python_tests_are_found(self):
        tags = tm.find_tags("t.py", "def test_x(self):\n    # REQ: SRS-AAA-001\n")
        self.assertEqual(tags, [("SRS-AAA-001", "test_x", "t.py")])


class Checks(unittest.TestCase):
    def test_the_fixture_is_complete(self):
        errors, tested = analyse(SRS, tm.scan(FIXTURE))
        self.assertEqual(errors, [])
        self.assertEqual(tested["SRS-BBB-002"], {("minidaq/tests/unit/test_widget.cpp", "WidgetFixture.RejectsNegativeInput"),
                                                 ("tools/test_gadget.py", "test_logs_every_input")})

    def test_an_untested_requirement_is_reported(self):
        errors, _ = analyse(SRS, [("SRS-AAA-002", "T.t", "x.cpp"), ("SRS-BBB-002", "T.t", "x.cpp")])
        self.assertTrue(any(e.startswith("SRS-AAA-001:") for e in errors), errors)

    def test_an_unknown_requirement_is_reported(self):
        errors, _ = analyse(SRS, tm.scan(FIXTURE) + [("SRS-ZZZ-009", "T.t", "x.cpp")])
        self.assertTrue(any("SRS-ZZZ-009" in e for e in errors), errors)

    def test_a_withdrawn_requirement_must_not_be_tested(self):
        errors, _ = analyse(SRS, tm.scan(FIXTURE) + [("SRS-BBB-001", "T.t", "x.cpp")])
        self.assertTrue(any("SRS-BBB-001" in e and "withdrawn" in e for e in errors), errors)

    def test_other_methods_need_evidence(self):
        no_evidence = SRS.replace("| SRS-AAA-003 | M | measurements/widget.txt: 2,500 inputs/s |\n", "")
        errors, _ = analyse(no_evidence, tm.scan(FIXTURE))
        self.assertTrue(any(e.startswith("SRS-AAA-003:") for e in errors), errors)

    def test_a_duplicate_id_is_reported(self):
        twice = SRS + "| SRS-AAA-001 | The widget shall count again. | widget | T |\n"
        errors, _ = analyse(twice, tm.scan(FIXTURE))
        self.assertTrue(any("more than once" in e for e in errors), errors)


class Matrix(unittest.TestCase):
    def setUp(self):
        reqs, evidence, dups = tm.parse_srs(SRS)
        _, tested = tm.check(reqs, evidence, dups, tm.scan(FIXTURE))
        self.text = tm.render(reqs, evidence, tested)

    def test_every_live_requirement_has_a_row(self):
        for rid in ("SRS-AAA-001", "SRS-AAA-002", "SRS-AAA-003", "SRS-BBB-002"):
            self.assertIn(f"| {rid} |", self.text)
        self.assertNotIn("| SRS-BBB-001 |", self.text)

    def test_rows_name_tests_and_evidence_but_no_line_numbers(self):
        row = next(ln for ln in self.text.splitlines() if ln.startswith("| SRS-BBB-002 |"))
        self.assertIn("WidgetFixture.RejectsNegativeInput", row)
        self.assertIn("test_logs_every_input", row)
        self.assertNotRegex(row, r":\d+")
        self.assertIn("measurements/widget.txt", next(ln for ln in self.text.splitlines() if ln.startswith("| SRS-AAA-003 |")))

    def test_the_matrix_is_reproducible(self):
        reqs, evidence, dups = tm.parse_srs(SRS)
        _, tested = tm.check(reqs, evidence, dups, list(reversed(tm.scan(FIXTURE))))
        self.assertEqual(tm.render(reqs, evidence, tested), self.text)


if __name__ == "__main__":
    unittest.main()
