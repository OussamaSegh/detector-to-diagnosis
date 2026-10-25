# SPDX-License-Identifier: MIT
import copy
import os
import unittest

import threats_check as tc

HERE = os.path.dirname(os.path.abspath(__file__))
VARIANT = os.path.dirname(os.path.abspath(tc.__file__))


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


DOT = read(os.path.join(HERE, "dashboard.dot"))
REQS = tc.requirement_ids(read(os.path.join(HERE, "requirements.txt")))
MINI = {
    "applies": {"external": "SR", "process": "STRIDE", "store": "TRID", "flow": "TID"},
    "elements": [{"id": "browser", "kind": "external"}],
    "threats": [
        {"id": "X-1", "element": "browser", "stride": "S", "status": "mitigated", "requirements": ["DASH-003"]},
        {"id": "X-2", "element": "browser", "stride": "R", "status": "accepted", "note": "nothing to deny"},
    ],
}


class Checker(unittest.TestCase):
    def errors(self, change):
        doc = copy.deepcopy(MINI)
        change(doc)
        return tc.check_coverage(doc) + tc.check_threats(doc, REQS)

    def test_minimal_model_passes(self):
        self.assertEqual(self.errors(lambda d: None), [])

    def test_coverage(self):
        self.assertTrue(self.errors(lambda d: d["threats"].pop()), "no R threat for an external entity")
        self.assertTrue(self.errors(lambda d: d["elements"].append({"id": "p", "kind": "process"})),
                        "a process needs all six")

    def test_status_rules(self):
        def set_(i, **kw):
            return lambda d: d["threats"][i].update(kw)
        self.assertTrue(self.errors(set_(0, requirements=[])), "mitigated without requirements")
        self.assertTrue(self.errors(set_(0, requirements=["DASH-099"])), "not a proposed requirement")
        self.assertTrue(self.errors(set_(1, note="")), "accepted without a reason")
        self.assertTrue(self.errors(set_(1, status="environment")), "environment without an assumption")
        self.assertEqual(self.errors(set_(1, status="environment", assumption="the network is closed")), [])
        self.assertTrue(self.errors(set_(1, status="maybe")))
        self.assertTrue(self.errors(set_(1, stride="T")), "T does not apply to an external entity")


class YourModel(unittest.TestCase):
    def setUp(self):
        self.doc = tc.load(os.path.join(VARIANT, "threats.json"))

    def find(self, element, stride):
        return [t for t in self.doc["threats"] if t["element"] == element and t["stride"] == stride]

    def test_passes_the_checker(self):
        self.assertEqual(tc.check(self.doc, DOT, REQS), [])

    def test_is_substantial(self):
        self.assertGreaterEqual(len(self.doc["threats"]), 10)

    def test_the_threats_that_matter(self):
        for element, stride, req in (("webui", "E", "DASH-002"), ("http", "I", "DASH-001"),
                                     ("browser", "S", "DASH-003"), ("webui", "D", "DASH-005")):
            mitigated = [t for t in self.find(element, stride) if t["status"] == "mitigated"]
            self.assertTrue(any(req in t["requirements"] for t in mitigated),
                            f"{element}/{stride}: a mitigated threat that {req} counters")


if __name__ == "__main__":
    unittest.main()
