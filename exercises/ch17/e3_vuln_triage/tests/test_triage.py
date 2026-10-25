# SPDX-License-Identifier: MIT
import datetime
import json
import os
import unittest

import triage

HERE = os.path.dirname(os.path.abspath(__file__))
VARIANT = os.path.dirname(os.path.abspath(triage.__file__))
TODAY = datetime.date(2026, 10, 25)


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class Rules(unittest.TestCase):
    def problems(self, severity, **d):
        d.setdefault("detail", "because")
        return triage.check_decision(d, severity, TODAY)

    def test_valid(self):
        self.assertEqual(self.problems("high", state="exploitable", response="update", fix_by="2026-11-01"), [])
        self.assertEqual(self.problems("low", state="not_affected", justification="code_not_present"), [])
        self.assertEqual(self.problems("medium", state="in_triage"), [])
        self.assertEqual(self.problems("medium", state="exploitable", response="workaround_available"), [])

    def test_invalid(self):
        self.assertTrue(self.problems("low", state="wontfix"))
        self.assertTrue(self.problems("low", state="not_affected"), "no justification")
        self.assertTrue(self.problems("low", state="not_affected", justification="we think so"))
        self.assertTrue(self.problems("medium", state="exploitable"), "no response")
        self.assertTrue(self.problems("critical", state="exploitable", response="update"), "no fix_by")
        self.assertTrue(self.problems("high", state="exploitable", response="update", fix_by="2026-10-24"), "passed")
        self.assertTrue(self.problems("high", state="in_triage"))
        self.assertTrue(self.problems("low", state="resolved", detail=" "), "no detail")


class YourDecisions(unittest.TestCase):
    def setUp(self):
        self.scan = load(os.path.join(HERE, "scan.json"))
        self.decisions = {d["vulnerability"]: d for d in load(os.path.join(VARIANT, "decisions.json"))["decisions"]}

    def test_complete_and_valid(self):
        self.assertEqual(triage.apply(self.scan, list(self.decisions.values()), TODAY), [])

    def test_the_decisions(self):
        d = self.decisions
        self.assertEqual(d["EX-2026-0101"]["state"], "exploitable", "the server is a TLS 1.3 server")
        self.assertEqual(d["EX-2026-0101"]["response"], "update")
        self.assertEqual(d["EX-2026-0102"]["state"], "not_affected", "no DTLS")
        self.assertEqual(d["EX-2026-0102"]["justification"], "code_not_reachable",
                         "the code is in the shared library, so it is present, but nothing reaches it")
        self.assertEqual(d["EX-2026-0103"]["state"], "exploitable", "minidaq_ctl checks host names")
        self.assertEqual(d["EX-2026-0104"]["state"], "not_affected")
        self.assertEqual(d["EX-2026-0106"]["justification"], "code_not_present", "not shipped")
        self.assertIn("SAX", d["EX-2026-0105"]["detail"], "say why the SAX defect does not reach MiniDAQ")


if __name__ == "__main__":
    unittest.main()
