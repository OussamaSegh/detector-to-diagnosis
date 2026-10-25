# SPDX-License-Identifier: MIT
"""Acceptance tests for Exercise 13.3."""
import unittest

from classify import Device, classify


class Scanners(unittest.TestCase):
    def test_a_brain_pet_scanner_is_class_iia(self):
        r = classify(Device("brain PET", images_radiopharmaceuticals=True))
        self.assertEqual(r.device_class, "IIa")
        self.assertTrue(any("Rule 10" in x for x in r.rules), r.rules)

    def test_a_ct_scanner_is_class_iib(self):
        r = classify(Device("CT", emits_ionizing_radiation_for_diagnosis=True))
        self.assertEqual(r.device_class, "IIb")

    def test_pet_ct_takes_the_strictest_rule(self):
        r = classify(Device("PET/CT", images_radiopharmaceuticals=True,
                            emits_ionizing_radiation_for_diagnosis=True))
        self.assertEqual(r.device_class, "IIb")
        self.assertEqual(len(r.rules), 2, "both Rule 10 indents apply and both are reported")

    def test_an_active_device_with_no_special_rule_is_class_i(self):
        self.assertEqual(classify(Device("electric hospital bed")).device_class, "I")


class Software(unittest.TestCase):
    def test_daq_software_takes_the_class_of_the_scanner_it_drives(self):
        r = classify(Device("DAQ software", software_only=True, drives_device_class="IIa",
                            informs_decisions=True, decision_impact="serious"))
        self.assertEqual(r.device_class, "IIa")
        self.assertTrue(r.rules[0].startswith("3.3"), r.rules)

    def test_daq_software_of_a_pet_ct_is_class_iib(self):
        r = classify(Device("DAQ software", software_only=True, drives_device_class="IIb"))
        self.assertEqual(r.device_class, "IIb")

    def test_standalone_software_follows_the_impact_of_the_decision(self):
        cases = {"non_serious": "IIa", "none": "IIa", "serious": "IIb", "irreversible": "III"}
        for impact, want in cases.items():
            with self.subTest(impact=impact):
                d = Device("quantification", software_only=True, informs_decisions=True,
                           decision_impact=impact)
                self.assertEqual(classify(d).device_class, want)

    def test_monitoring_software(self):
        d = Device("monitor", software_only=True, monitors_physiology=True)
        self.assertEqual(classify(d).device_class, "IIa")
        d.patient_in_immediate_danger = True
        self.assertEqual(classify(d).device_class, "IIb")

    def test_other_software_is_class_i(self):
        d = Device("report formatter", software_only=True)
        r = classify(d)
        self.assertEqual(r.device_class, "I")
        self.assertIn("Rule 11", r.rules[0])


if __name__ == "__main__":
    unittest.main()
