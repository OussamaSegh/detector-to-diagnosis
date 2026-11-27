# SPDX-License-Identifier: MIT
"""Acceptance of an audit exercise (marked (A)). Your tests are the class Audit in audit.py, in
starter/ or solution/; they reach the code under audit as self.subject. They must:

- pass on the corrected change (reference/);
- fail on the agent's change (agent/);
- fail on each defect of the change on its own (defects/, one file per defect, if the change
  has more than one).

A test that fails on the corrected change is a test of something the specification does not
ask for. A defect that your tests let through is one a reviewer would have let through.
"""
import importlib.util
import pathlib
import unittest

import audit  # your tests, from starter/ or solution/ (on PYTHONPATH)

HERE = pathlib.Path(__file__).resolve().parent


def load(path):
    spec = importlib.util.spec_from_file_location(f"audited_{path.parent.name}_{path.stem}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_on(folder, name=None):
    """Runs the reader's tests against the subject in tests/<folder>/ (or one file of it)."""
    files = [HERE / folder / name] if name else sorted((HERE / folder).glob("*.py"))
    subject = load(files[0])
    bound = type("Audit", (audit.Audit,), {"subject": subject})
    result = unittest.TestResult()
    unittest.defaultTestLoader.loadTestsFromTestCase(bound).run(result)
    return result


def problems(result):
    return "; ".join(f"{t.id().rsplit('.', 1)[-1]}: {msg.strip().splitlines()[-1]}"
                     for t, msg in result.failures + result.errors)


class Acceptance(unittest.TestCase):
    def test_your_tests_pass_on_the_corrected_change(self):
        r = run_on("reference")
        self.assertGreater(r.testsRun, 0, "audit.py has no test")
        self.assertTrue(r.wasSuccessful(), f"your tests fail on the corrected change: {problems(r)}")

    def test_your_tests_reject_the_agents_change(self):
        r = run_on("agent")
        self.assertFalse(r.wasSuccessful(), "every test passes on the agent's change")

    def test_your_tests_reject_each_defect_on_its_own(self):
        for d in sorted((HERE / "defects").glob("*.py")):
            with self.subTest(defect=d.stem):
                self.assertFalse(run_on("defects", d.name).wasSuccessful(),
                                 f"every test passes on {d.stem}: a defect your tests let through")


if __name__ == "__main__":
    unittest.main()
