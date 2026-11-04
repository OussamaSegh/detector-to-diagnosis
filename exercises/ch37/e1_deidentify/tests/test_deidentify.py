# SPDX-License-Identifier: MIT
"""Acceptance tests of Exercise 37.1. The patient is invented."""
import datetime
import re
import unittest

from deidentify import deidentify

HEADER = {
    "PatientName": "Doe^Jane", "PatientID": "MRN-0042", "PatientBirthDate": "19580214",
    "PatientSex": "F", "OtherPatientIDs": "INS-77-12", "PatientComments": "claustrophobic",
    "InstitutionName": "Example Clinic", "ReferringPhysicianName": "House^Greg",
    "AccessionNumber": "ACC20261104-7", "StudyDescription": "Brain PET for Jane",
    "StudyDate": "20261104", "SeriesDate": "20261104", "AcquisitionDate": "20261105",
    "StudyInstanceUID": "1.2.826.0.1.3680043.2.1125.1", "SeriesInstanceUID": "1.2.3.4.5.6",
    "SOPInstanceUID": "1.2.3.4.5.6.7", "FrameOfReferenceUID": "1.2.3.9",
    "Modality": "PT", "Rows": "128", "Columns": "128", "PixelSpacing": ["2", "2"],
    "PatientPosition": "HFS", "Units": "PROPCNTS", "RescaleSlope": "1.4e-07",
    "SeriesTime": "101500", "PrivateVendorNote": "scan of Doe^Jane",
}
SECRET = ["Doe", "Jane", "MRN-0042", "19580214", "INS-77", "claustrophobic", "Example Clinic",
          "House", "ACC2026", "20261104", "20261105", "1.2.826.0.1.3680043.2.1125.1",
          "1.2.3.4.5.6", "1.2.3.9"]


def values(header):
    for v in header.values():
        yield from (v if isinstance(v, list) else [v])


class Deidentify(unittest.TestCase):
    def setUp(self):
        self.out = deidentify(HEADER, b"site key")

    def test_nothing_that_identifies_is_left(self):
        text = " ".join(values(self.out))
        for s in SECRET:
            self.assertNotIn(s, text)
        for k in ("PatientBirthDate", "OtherPatientIDs", "PatientComments", "InstitutionName",
                  "ReferringPhysicianName", "AccessionNumber", "StudyDescription",
                  "PrivateVendorNote", "PatientSex"):
            self.assertNotIn(k, self.out)

    def test_what_the_problem_needs_is_kept(self):
        for k in ("Modality", "Rows", "PixelSpacing", "PatientPosition", "Units", "RescaleSlope",
                  "SeriesTime"):
            self.assertEqual(self.out[k], HEADER[k])

    def test_pseudonyms_are_stable_per_patient_and_key(self):
        again = deidentify(dict(HEADER, StudyDate="20250101"), b"site key")
        self.assertEqual(again["PatientID"], self.out["PatientID"])
        self.assertTrue(self.out["PatientID"].startswith("ANON-"))
        self.assertTrue(self.out["PatientName"].startswith("ANON^"))
        other = deidentify(dict(HEADER, PatientID="MRN-0043"), b"site key")
        self.assertNotEqual(other["PatientID"], self.out["PatientID"])
        self.assertNotEqual(deidentify(HEADER, b"other key")["PatientID"], self.out["PatientID"])

    def test_dates_keep_their_intervals(self):
        def day(s):
            return datetime.datetime.strptime(s, "%Y%m%d").date()
        self.assertEqual(day(self.out["AcquisitionDate"]) - day(self.out["StudyDate"]),
                         datetime.timedelta(days=1))
        shift = day(HEADER["StudyDate"]) - day(self.out["StudyDate"])
        self.assertTrue(1 <= shift.days <= 365)

    def test_uids_are_valid_and_consistent(self):
        for k in ("StudyInstanceUID", "SeriesInstanceUID", "SOPInstanceUID",
                  "FrameOfReferenceUID"):
            u = self.out[k]
            self.assertRegex(u, r"^2\.25\.(0|[1-9][0-9]*)$")
            self.assertLessEqual(len(u), 64)
        second = deidentify(dict(HEADER, SOPInstanceUID="1.2.3.4.5.6.8"), b"site key")
        self.assertEqual(second["SeriesInstanceUID"], self.out["SeriesInstanceUID"])
        self.assertNotEqual(second["SOPInstanceUID"], self.out["SOPInstanceUID"])
        self.assertEqual(len(set(re.findall(r"2\.25\.\d+", " ".join(values(self.out))))), 4)


if __name__ == "__main__":
    unittest.main()
