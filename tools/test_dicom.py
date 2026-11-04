#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Tests of tools/dicom and tools/pacs.py, the export of images to an archive (Chapter 35, tool
TL-44), run by CTest as tools.dicom.

The encoding is tested byte for byte on small data sets, the PET series on synthetic images with
known answers, the network side against the package's own test archive (tools/dicom/scp.py) with
faults injected, and the outbox on whole series. The tests marked "independent" check the same
output with pydicom (a reader of DICOM files) and pynetdicom (a DICOM network peer), which this
package does not use: a writer checked only by its own reader can share its mistakes. Without
them those tests are skipped, or fail when MINIDAQ_DICOM_ORACLE_REQUIRED=1 (CI's job python).
"""
import json
import os
import pathlib
import socket
import struct
import sys
import tempfile
import time
import unittest

try:
    import numpy as np
except ImportError:  # ctest counts exit status 77 as skipped
    print("numpy is not installed: skipped")
    sys.exit(77)

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tools import pacs  # noqa: E402
from tools.dicom import dictionary, encode, net, outbox, pet, scp, uid  # noqa: E402
from tools.dicom.encode import Dataset, DicomError  # noqa: E402

try:
    import pydicom
    import pynetdicom
    ORACLE = True
except ImportError:
    ORACLE = False
    if os.environ.get("MINIDAQ_DICOM_ORACLE_REQUIRED") == "1":
        print("pydicom and pynetdicom are required (MINIDAQ_DICOM_ORACLE_REQUIRED=1)")
        sys.exit(1)
independent = unittest.skipUnless(ORACLE, "pydicom and pynetdicom are not installed")

ORDER = {"PatientName": "MINIDAQ^PHANTOM", "PatientID": "PHANTOM-0001",
         "PatientBirthDate": "", "PatientSex": "O", "AccessionNumber": "ACC0001",
         "StudyID": "1", "StudyInstanceUID": "2.25.255804335339911196347126254352384611651"}
ACQ = {"start": "2026-11-04T09:30:00+01:00", "duration_s": 600, "radionuclide": "F18",
       "radiopharmaceutical": "FDG", "injected_bq": 3.7e8,
       "injection": "2026-11-04T08:30:00+01:00", "patient_position": "HFS",
       "scanner": {"manufacturer": "MiniDAQ project", "model": "MiniDAQ", "software": "0.9.0"}}
REC = {"units": "PROPCNTS", "pixel_mm": 2.0, "slice_mm": 3.0, "z0_mm": -6.0,
       "corrections": ["NORM", "ATTN", "SCAT", "RAN"], "method": "OSEM 4 iterations 8 subsets"}


def image(slices=5, n=32, seed=1, negative=False):
    rng = np.random.default_rng(seed)
    img = rng.random((slices, n, n)) * 2.0e4
    if negative:
        img -= 1.0e3
    return img


def make(img=None, order=None, acq=None, rec=None):
    return pet.series(image() if img is None else img, dict(ORDER, **(order or {})),
                      dict(ACQ, **(acq or {})), dict(REC, **(rec or {})))


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Encoding(unittest.TestCase):
    def test_the_two_explicit_header_forms_and_the_implicit_one(self):
        # REQ: SRS-DCM-001
        self.assertEqual(encode.encode_element(0x00280010, "US", 128),
                         bytes.fromhex("2800 1000") + b"US" + b"\x02\x00" + b"\x80\x00")
        self.assertEqual(encode.encode_element(0x7FE00010, "OW", b"\1\2"),
                         bytes.fromhex("e07f 1000") + b"OW\0\0" + b"\x02\0\0\0" + b"\1\2")
        self.assertEqual(encode.encode_element(0x00280010, "US", 128, explicit=False),
                         bytes.fromhex("2800 1000") + b"\x02\0\0\0" + b"\x80\x00")
        seq = encode.encode_element(0x00540300, "SQ", [Dataset().set("CodeValue", "1")])
        self.assertEqual(seq[:12], bytes.fromhex("5400 0003") + b"SQ\0\0" + struct.pack("<I", 18))
        self.assertEqual(seq[12:16], bytes.fromhex("feff 00e0"))

    def test_every_value_has_an_even_length_with_the_padding_of_its_vr(self):
        # REQ: SRS-DCM-001
        self.assertTrue(encode.encode_element(0x0020000D, "UI", "1.23").endswith(b"1.23"))
        self.assertTrue(encode.encode_element(0x0020000D, "UI", "1.2").endswith(b"1.2\0"))
        self.assertTrue(encode.encode_element(0x00080060, "CS", "PET").endswith(b"PET "))
        self.assertTrue(encode.encode_element(0x00020001, "OB", b"\1").endswith(b"\1\0"))
        for t, e in Dataset().set("PatientID", "ABC").set("Modality", "PT").items():
            self.assertEqual(len(encode.encode_element(t, e.vr, e.value)) % 2, 0)

    def test_elements_are_written_in_ascending_tag_order(self):
        # REQ: SRS-DCM-001
        ds = Dataset().set("Rows", 2).set("PatientID", "X").set("Modality", "PT")
        decoded = encode.decode_dataset(encode.encode_dataset(ds))
        self.assertEqual(list(decoded), sorted(ds))
        bad = encode.encode_element(0x00280010, "US", 1) + encode.encode_element(0x00080060, "CS", "PT")
        with self.assertRaisesRegex(DicomError, "ascend"):
            encode.decode_dataset(bad)

    def test_a_value_that_breaks_its_vr_is_refused_not_truncated(self):
        # REQ: SRS-DCM-001
        cases = [("SH", "ACCESSION-NUMBER1"), ("UI", "1." + "2" * 63), ("UI", "1.2a"),
                 ("CS", "pt"), ("LO", "a\\b"), ("DS", float("nan")), ("IS", 2**31),
                 ("PN", "A" * 65)]
        tags = {"SH": 0x00080050, "UI": 0x0020000D, "CS": 0x00080060, "LO": 0x00100020,
                "DS": 0x00281053, "IS": 0x00200013, "PN": 0x00100010}
        for vr, value in cases:
            with self.subTest(vr=vr, value=value), self.assertRaises(DicomError):
                encode.encode_element(tags[vr], vr, value)
        with self.assertRaisesRegex(DicomError, "Character Set"):
            encode.encode_element(0x00100010, "PN", "Müller^Jörg")  # ASCII by default

    def test_a_decimal_string_keeps_its_precision_within_16_characters(self):
        # REQ: SRS-DCM-001
        rng = np.random.default_rng(7)
        values = list(rng.normal(size=200) * 10.0 ** rng.integers(-12, 12, size=200))
        values += [3.2e-7, -0.0, 1.0 / 3.0, 65535.0, -1.0e-300, 1.0e300, 123456789012.345]
        for x in values:
            s = encode.format_ds(x)
            self.assertLessEqual(len(s), 16, s)
            self.assertLessEqual(abs(float(s) - x), abs(x) * 5e-10, s)  # 10 digits at worst: -d.ddddddddde-dd
        self.assertNotEqual(float(encode.format_ds(3.2e-7)), 0.0)

    def test_a_file_has_its_preamble_magic_and_meta_group_length(self):
        # REQ: SRS-DCM-001
        ds = make()[0]
        b = encode.file_bytes(ds, uid.IMPLEMENTATION_CLASS)
        self.assertEqual(b[:128], b"\0" * 128)
        self.assertEqual(b[128:132], b"DICM")
        meta, back = encode.read_file_bytes(b)
        group = encode.encode_dataset(meta)
        self.assertEqual(struct.unpack_from("<I", b, 140)[0], len(group))
        self.assertEqual(meta.get("TransferSyntaxUID"), encode.EXPLICIT_LE)
        self.assertEqual(meta.get("MediaStorageSOPInstanceUID"), ds.get("SOPInstanceUID"))
        self.assertEqual(back.get("PixelData"), ds.get("PixelData"))

    def test_the_reader_refuses_damaged_or_hostile_input(self):
        # REQ: SRS-DCM-001
        good = encode.file_bytes(make()[0], uid.IMPLEMENTATION_CLASS)
        with self.assertRaisesRegex(DicomError, "DICM"):
            encode.read_file_bytes(good[:128] + b"DICN" + good[132:])
        with self.assertRaises(DicomError):
            encode.read_file_bytes(good[:-3])                     # truncated pixel data
        odd = bytes.fromhex("1000 2000") + b"LO\x03\x00ABC"
        with self.assertRaisesRegex(DicomError, "odd length"):
            encode.decode_dataset(odd)
        deep = Dataset().set("CodeValue", "1")
        for _ in range(encode.MAX_DEPTH + 2):
            deep = Dataset().set("RadionuclideCodeSequence", [deep])
        with self.assertRaisesRegex(DicomError, "deeper"):
            encode.decode_dataset(encode.encode_dataset(deep))
        implicit = encode.file_bytes(make()[0], uid.IMPLEMENTATION_CLASS).replace(
            encode.EXPLICIT_LE.encode() + b"\0", encode.IMPLICIT_LE.encode() + b"\0\0\0", 1)
        with self.assertRaises(DicomError):
            encode.read_file_bytes(implicit)

    def test_sequences_of_undefined_length_are_read(self):
        # REQ: SRS-DCM-001
        item = encode.encode_element(0x00080100, "SH", "77004003")
        raw = (bytes.fromhex("5400 0003") + b"SQ\0\0" + b"\xff\xff\xff\xff"
               + bytes.fromhex("feff 00e0") + b"\xff\xff\xff\xff" + item
               + bytes.fromhex("feff 0de0") + b"\0\0\0\0"
               + bytes.fromhex("feff dde0") + b"\0\0\0\0"
               + encode.encode_element(0x00541001, "CS", "BQML"))
        ds = encode.decode_dataset(raw)
        self.assertEqual(ds.get("RadionuclideCodeSequence")[0].get("CodeValue"), "77004003")
        self.assertEqual(ds.get("Units"), "BQML")

    @independent
    def test_independent_the_dictionary_agrees_with_pydicom(self):
        # REQ: SRS-DCM-001
        for t, (vr, keyword) in dictionary.ELEMENTS.items():
            with self.subTest(tag=dictionary.name(t)):
                self.assertEqual(pydicom.datadict.keyword_for_tag(t), keyword)
                self.assertIn(vr, pydicom.datadict.dictionary_VR(t).split(" or "))

    @independent
    def test_independent_pydicom_reads_every_attribute_as_written(self):
        # REQ: SRS-DCM-001
        with tempfile.TemporaryDirectory() as d:
            ds = make()
            paths = pet.write_series(ds, d)
            f = pydicom.dcmread(paths[0])
            self.assertEqual(f.file_meta.TransferSyntaxUID, encode.EXPLICIT_LE)
            for t, e in ds[0].items():
                if e.vr in ("SQ", "OW"):
                    continue
                got = f[t].value
                want = encode.split(encode.encode_element(t, e.vr, e.value)[8:].rstrip(b" \0")
                                    .decode("utf-8")) if e.vr in encode.TEXT_VRS else e.value
                got = [str(v) for v in got] if isinstance(got, pydicom.multival.MultiValue) else got
                if e.vr in encode.TEXT_VRS and not isinstance(got, list):
                    got = encode.split(str(got)) if str(got) else []
                with self.subTest(tag=dictionary.name(t)):
                    self.assertEqual(got, want)
            seq = f.RadiopharmaceuticalInformationSequence[0]
            self.assertEqual(seq.RadionuclideCodeSequence[0].CodeValue, "77004003")

    @independent
    def test_independent_we_read_what_pydicom_writes(self):
        # REQ: SRS-DCM-001
        from pydicom.dataset import Dataset as PyDataset, FileMetaDataset
        meta = FileMetaDataset()
        meta.MediaStorageSOPClassUID = pet.SOP_CLASS
        meta.MediaStorageSOPInstanceUID = "2.25.1"
        meta.TransferSyntaxUID = encode.EXPLICIT_LE
        p = PyDataset()
        p.file_meta = meta
        p.SOPClassUID, p.SOPInstanceUID, p.PatientID = pet.SOP_CLASS, "2.25.1", "X1"
        code = PyDataset()
        code.CodeValue, code.CodingSchemeDesignator, code.CodeMeaning = "77004003", "SCT", "F"
        p.RadionuclideCodeSequence = [code]
        p.PixelSpacing = [2.0, 2.0]
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d) / "p.dcm"
            p.save_as(path, enforce_file_format=True)
            _, ds = encode.read_file_bytes(path.read_bytes())
        self.assertEqual(ds.get("PatientID"), "X1")
        self.assertEqual(ds.get("PixelSpacing"), ["2.0", "2.0"])
        self.assertEqual(ds.get("RadionuclideCodeSequence")[0].get("CodeValue"), "77004003")


class Series(unittest.TestCase):
    def test_a_series_has_every_attribute_its_modules_require(self):
        # REQ: SRS-DCM-002
        ds = make()
        self.assertEqual(pet.check_series(ds), [])
        for d in ds:
            for key in pet.TYPE1:
                self.assertTrue(d.has(key) and d.get(key) not in ("", [], None), key)
            for key in pet.TYPE2:
                self.assertTrue(d.has(key), key)
        self.assertEqual([d.get("ImageIndex") for d in ds], [1, 2, 3, 4, 5])
        self.assertEqual(ds[0].get("SeriesType"), ["STATIC", "IMAGE"])
        self.assertEqual(ds[0].get("CorrectedImage"), REC["corrections"])

    def test_the_check_finds_each_problem_a_series_can_have(self):
        # REQ: SRS-DCM-002
        cases = {"type 1": lambda s: s[1].pop(dictionary.tag("FrameOfReferenceUID")),
                 "type 2": lambda s: s[2].pop(dictionary.tag("PatientBirthDate")),
                 "PatientID differs": lambda s: s[3].set("PatientID", "OTHER"),
                 "same SOPInstanceUID": lambda s: s[4].set("SOPInstanceUID",
                                                           s[0].get("SOPInstanceUID")),
                 "intercept": lambda s: s[0].set("RescaleIntercept", "1"),
                 "image indices": lambda s: s[0].set("ImageIndex", 7),
                 "not a valid UID": lambda s: s[0].set("FrameOfReferenceUID", "1.02")}
        for what, damage in cases.items():
            with self.subTest(what=what):
                s = make()
                damage(s)
                self.assertTrue(any(what in p for p in pet.check_series(s)), pet.check_series(s))
                with tempfile.TemporaryDirectory() as d, self.assertRaises(DicomError):
                    pet.write_series(s, d)

    def test_each_value_comes_back_within_half_a_slope(self):
        # REQ: SRS-DCM-003
        for negative in (False, True):
            img = image(negative=negative)
            ds = make(img)
            for d, k in zip(ds, range(img.shape[0])):
                slope = float(d.get("RescaleSlope"))
                self.assertEqual(d.get("PixelRepresentation"), 1 if negative else 0)
                self.assertEqual(float(d.get("RescaleIntercept")), 0.0)
                err = np.abs(pet.values(d) - img[k][::-1])
                self.assertLessEqual(err.max(), slope / 2 * (1 + 1e-9))
                peak = np.abs(img[k]).max()
                self.assertAlmostEqual(slope, peak / (32767 if negative else 65535), delta=peak * 1e-15)

    def test_the_stored_values_use_the_slope_as_written(self):
        # REQ: SRS-DCM-003
        plane = np.array([[0.0, 1.0e-6 / 3.0], [2.0e-7, 1.0e-6]])
        stored, text, _ = pet.quantize(plane)
        self.assertLessEqual(len(text), 16)
        self.assertTrue(np.all(np.abs(stored * float(text) - plane) <= float(text) / 2))
        self.assertEqual(int(stored.max()), 65535)

    def test_an_image_with_values_that_are_not_finite_is_refused(self):
        # REQ: SRS-DCM-003
        for bad in (np.nan, np.inf):
            img = image()
            img[2, 3, 4] = bad
            with self.subTest(bad=bad), self.assertRaisesRegex(DicomError, "finite"):
                make(img)

    def test_an_empty_slice_is_written_with_a_slope_of_one(self):
        # REQ: SRS-DCM-003
        img = image()
        img[1] = 0.0
        d = make(img)[1]
        self.assertEqual(d.get("RescaleSlope"), "1")
        self.assertFalse(np.any(pet.values(d)))

    def _hot(self, position):
        img = np.zeros((3, 32, 32))
        x_mm, y_mm, k = 19.0, 29.0, 2           # gantry: right of the axis, up, third slice
        col, row = int(x_mm / 2.0 + 15.5), int(y_mm / 2.0 + 15.5)  # pixel centers at odd mm
        img[k, row, col] = 1000.0
        return img, (x_mm, y_mm, REC["z0_mm"] + k * REC["slice_mm"]), position

    def test_a_pixel_lands_at_its_position_in_the_patient(self):
        # REQ: SRS-DCM-004
        expect = {"HFS": lambda x, y, z: (x, -y, z), "FFS": lambda x, y, z: (-x, -y, -z)}
        for position, to_lps in expect.items():
            img, (x, y, z), _ = self._hot(position)
            ds = make(img, acq={"patient_position": position})
            for d in ds:
                v = pet.values(d)
                if v.max() == 0:
                    continue
                r, c = np.unravel_index(np.argmax(v), v.shape)
                ipp = np.array([float(t) for t in d.get("ImagePositionPatient")])
                iop = np.array([float(t) for t in d.get("ImageOrientationPatient")])
                spacing = [float(t) for t in d.get("PixelSpacing")]  # row spacing, column spacing
                p = ipp + c * spacing[1] * iop[:3] + r * spacing[0] * iop[3:]
                with self.subTest(position=position):
                    self.assertTrue(np.allclose(p, to_lps(x, y, z)), (p, to_lps(x, y, z)))
                    self.assertEqual(d.get("PatientPosition"), position)

    def test_the_image_index_follows_the_slices_normal(self):
        # REQ: SRS-DCM-004
        for position in ("HFS", "FFS"):
            ds = make(acq={"patient_position": position})
            normal = np.cross(*np.array([float(t) for t in ds[0].get("ImageOrientationPatient")])
                              .reshape(2, 3))
            along = [np.array([float(t) for t in d.get("ImagePositionPatient")]) @ normal
                     for d in ds]
            order = sorted(range(len(ds)), key=lambda i: along[i])
            self.assertEqual([ds[i].get("ImageIndex") for i in order], [1, 2, 3, 4, 5])
            self.assertTrue(np.allclose(np.diff(sorted(along)), REC["slice_mm"]))
        with self.assertRaisesRegex(DicomError, "not supported"):
            make(acq={"patient_position": "HFP"})

    def test_patient_and_study_come_from_the_order_verbatim(self):
        # REQ: SRS-DCM-005
        order = {"PatientName": "Müller^Jörg", "PatientID": "000123-A",
                 "AccessionNumber": "A-77", "PatientBirthDate": "19700101", "PatientSex": "F"}
        for d in make(order=order):
            for key, value in order.items():
                self.assertEqual(d.get(key), value)
            self.assertEqual(d.get("StudyInstanceUID"), ORDER["StudyInstanceUID"])
            self.assertEqual(d.get("SpecificCharacterSet"), "ISO_IR 192")

    def test_an_order_that_cannot_file_the_series_is_refused(self):
        # REQ: SRS-DCM-005
        for bad in ({"PatientID": ""}, {"PatientID": "   "}, {"PatientName": ""},
                    {"StudyInstanceUID": "1.2.03"}, {"StudyInstanceUID": ""},
                    {"PatientSex": "X"}, {"PatientBirthDate": "1970-01-01"}):
            with self.subTest(bad=bad), self.assertRaises(DicomError):
                make(order=bad)
        with self.assertRaisesRegex(DicomError, "UTC offset"):
            make(acq={"start": "2026-11-04T09:30:00"})

    def test_uids_are_valid_and_derived_from_the_content(self):
        # REQ: SRS-DCM-005
        a, b = make(), make()
        keys = ("SeriesInstanceUID", "SOPInstanceUID", "FrameOfReferenceUID")
        for x, y in zip(a, b):
            for key in keys:
                self.assertTrue(uid.valid(x.get(key)) and x.get(key).startswith("2.25."))
                self.assertEqual(x.get(key), y.get(key))
        img = image()
        img[0, 0, 0] += 1.0
        self.assertNotEqual(make(img)[0].get("SeriesInstanceUID"), a[0].get("SeriesInstanceUID"))
        self.assertNotEqual(make(rec={"method": "FBP"})[0].get("SeriesInstanceUID"),
                            a[0].get("SeriesInstanceUID"))
        self.assertEqual(len({d.get("SOPInstanceUID") for d in a}), len(a))
        self.assertFalse(uid.valid("1.02.3") or uid.valid("1..2") or uid.valid("1." + "1" * 63))

    def test_decay_factor_and_mean_activity_time(self):
        self.assertAlmostEqual(pet.decay_factor(6586.2, 6586.2), 2 * np.log(2), places=12)
        self.assertAlmostEqual(pet.decay_factor(6586.2, 1e-9), 1.0, places=9)
        t = pet.mean_activity_time_s(6586.2, 600.0)
        self.assertTrue(290.0 < t < 300.0)
        d = make(rec={"corrections": ["NORM", "DECY"], "decay_correction": "START"})[0]
        self.assertAlmostEqual(float(d.get("DecayFactor")), pet.decay_factor(6586.2, 600.0),
                               places=12)
        with self.assertRaisesRegex(DicomError, "DECY"):
            make(rec={"decay_correction": "START"})


class Network(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_echo_and_store_with_the_test_archive(self):
        # REQ: SRS-DCM-006
        ds = make()
        with scp.StorageSCP(self.dir / "a") as s:
            with net.associate("127.0.0.1", s.port, "MINIDAQ", "ARCHIVE") as a:
                # without TCP_NODELAY each instance waits ~40 ms for a delayed ACK (measurements/ch35)
                self.assertTrue(a.sock.getsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY))
                self.assertEqual(a.echo(), 0)
                self.assertEqual([a.store(d) for d in ds], [0] * len(ds))
            self.assertEqual(len(s.files()), len(ds))
            _, back = encode.read_file_bytes(s.files()[0].read_bytes())
            sent = {d.get("SOPInstanceUID"): d for d in ds}[back.get("SOPInstanceUID")]
            self.assertEqual(back.get("PixelData"), sent.get("PixelData"))

    def test_messages_are_cut_to_the_peers_maximum_pdu(self):
        # REQ: SRS-DCM-006
        payload = bytes(range(256)) * 40
        for max_pdu in (1024, 4096, 16384):
            pdus = net.pdata(1, payload, False, max_pdu)
            self.assertTrue(all(len(p) - 6 <= max_pdu for p in pdus))
            controls = [p[11] for p in pdus]
            self.assertEqual(controls, [0] * (len(pdus) - 1) + [2])
            self.assertEqual(b"".join(p[12:] for p in pdus), payload)
        with scp.StorageSCP(self.dir / "b", max_pdu=1024) as s:
            with net.associate("127.0.0.1", s.port, "MINIDAQ", "ARCHIVE") as a:
                self.assertEqual(a.peer_max_pdu, 1024)
                self.assertEqual(a.store(make()[0]), 0)
            self.assertEqual(s.errors, [])

    def test_a_rejected_association_says_why(self):
        # REQ: SRS-DCM-006
        with scp.StorageSCP(self.dir / "c", reject=(2, 3, 2)) as s, \
                self.assertRaisesRegex(net.AssociationError, "transient, source 3, reason 2"):
            net.associate("127.0.0.1", s.port, "MINIDAQ", "ARCHIVE")
        with scp.StorageSCP(self.dir / "d", ae="ARCHIVE") as s, \
                self.assertRaisesRegex(net.AssociationError, "reason 7"):
            net.associate("127.0.0.1", s.port, "MINIDAQ", "OTHER")
        with scp.StorageSCP(self.dir / "e", syntaxes=["1.2.840.10008.1.2.2"]) as s, \
                self.assertRaisesRegex(net.AssociationError, "transfer syntaxes not supported"):
            net.associate("127.0.0.1", s.port, "MINIDAQ", "ARCHIVE")

    def test_an_abort_and_a_silent_archive_end_the_association_with_an_error(self):
        # REQ: SRS-DCM-006
        ds = make()
        with scp.StorageSCP(self.dir / "f", abort_after=1) as s:
            with self.assertRaisesRegex(net.AssociationError, "aborted"):
                with net.associate("127.0.0.1", s.port, "MINIDAQ", "ARCHIVE") as a:
                    a.store(ds[0])
                    a.store(ds[1])
        with scp.StorageSCP(self.dir / "g", stall_after=0) as s:
            t = time.monotonic()
            with self.assertRaisesRegex(net.AssociationError, "time limit"):
                with net.associate("127.0.0.1", s.port, "MINIDAQ", "ARCHIVE", timeout=1.0) as a:
                    a.store(ds[0])
            self.assertLess(time.monotonic() - t, 5.0)
        with self.assertRaisesRegex(net.AssociationError, "cannot connect"):
            net.associate("127.0.0.1", free_port(), "MINIDAQ", "ARCHIVE", timeout=1.0)

    def test_a_pdu_longer_than_accepted_is_refused(self):
        # REQ: SRS-DCM-006
        a, b = socket.socketpair()
        with a, b:
            b.sendall(struct.pack(">BBI", net.P_DATA, 0, 100000))
            a.settimeout(1)
            with self.assertRaisesRegex(net.AssociationError, "more than"):
                net.read_pdu(a, 16390)

    def test_status_classes(self):
        # REQ: SRS-DCM-006
        self.assertEqual(net.status_class(0x0000), "success")
        for s in (0xB000, 0xB006, 0xB007):
            self.assertEqual(net.status_class(s), "warning")
        for s in (0xA700, 0xA900, 0xC000, 0x0110, 0x0122):
            self.assertEqual(net.status_class(s), "failure")
        self.assertTrue(net.transient(0xA700) and not net.transient(0xA900))

    @independent
    def test_independent_store_to_pynetdicom_and_from_it(self):
        # REQ: SRS-DCM-006
        from pynetdicom import AE, evt, AllStoragePresentationContexts
        from pynetdicom.sop_class import Verification
        received = []

        def on_store(event):
            received.append(event.dataset)
            return 0x0000

        ae = AE(ae_title="PYNETDICOM")
        ae.supported_contexts = AllStoragePresentationContexts
        ae.add_supported_context(Verification)
        port = free_port()
        server = ae.start_server(("127.0.0.1", port), block=False,
                                 evt_handlers=[(evt.EVT_C_STORE, on_store)])
        ds = make()
        try:
            with net.associate("127.0.0.1", port, "MINIDAQ", "PYNETDICOM", max_pdu=4096) as a:
                self.assertEqual(a.echo(), 0)
                self.assertEqual([a.store(d) for d in ds], [0] * len(ds))
        finally:
            server.shutdown()
        self.assertEqual(len(received), len(ds))
        by_uid = {d.get("SOPInstanceUID"): d for d in ds}
        for r in received:
            mine = by_uid[r.SOPInstanceUID]
            self.assertEqual(str(r.PatientID), mine.get("PatientID"))
            self.assertEqual(r.PixelData, mine.get("PixelData"))
            self.assertEqual(float(r.RescaleSlope), float(mine.get("RescaleSlope")))
        # and the other way: pynetdicom's user against this package's test archive
        with scp.StorageSCP(self.dir / "h") as s:
            user = AE(ae_title="PYSCU")
            user.add_requested_context(Verification)
            user.add_requested_context(pet.SOP_CLASS)
            assoc = user.associate("127.0.0.1", s.port, ae_title="ARCHIVE")
            self.assertTrue(assoc.is_established)
            self.assertEqual(assoc.send_c_echo().Status, 0)
            paths = pet.write_series(ds, self.dir / "series")
            self.assertEqual(assoc.send_c_store(pydicom.dcmread(paths[0])).Status, 0)
            assoc.release()
            time.sleep(0.2)
            self.assertEqual(len(s.files()), 1)
            self.assertEqual(s.errors, [])


class Outbox(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self.tmp.name)
        self.box = self.dir / "outbox"

    def tearDown(self):
        self.tmp.cleanup()

    def send(self, s):
        return outbox.send(self.box, "127.0.0.1", s.port, "MINIDAQ", "ARCHIVE", timeout=2.0)

    def test_a_series_leaves_the_outbox_only_when_stored(self):
        # REQ: SRS-DCM-007
        outbox.enqueue(self.box, make())
        with scp.StorageSCP(self.dir / "a") as s:
            report = self.send(s)
        self.assertEqual((report["pending"], report["sent"], report["failed"]), (0, 5, 0))
        lines = [json.loads(x) for x in (self.box / "journal.jsonl").read_text().splitlines()]
        self.assertEqual([x["action"] for x in lines], ["sent"] * 5)

    def test_an_interrupted_send_resumes_without_a_second_copy(self):
        # REQ: SRS-DCM-007
        ds = make()
        outbox.enqueue(self.box, ds)
        with scp.StorageSCP(self.dir / "archive", abort_after=2) as s:
            report = self.send(s)
        self.assertEqual((report["pending"], report["sent"]), (3, 2))
        self.assertTrue(report["errors"])
        outbox.enqueue(self.box, make())                    # the console exports it again
        with scp.StorageSCP(self.dir / "archive") as s:
            report = self.send(s)
            self.assertEqual((report["pending"], report["failed"]), (0, 0))
            self.assertEqual(len(s.files()), 5)              # one copy of each instance
            self.assertEqual({p.stem for p in s.files()}, {d.get("SOPInstanceUID") for d in ds})

    def test_each_status_class_has_its_own_outcome(self):
        # REQ: SRS-DCM-007
        outbox.enqueue(self.box, make())
        with scp.StorageSCP(self.dir / "a", statuses={2: 0xA900, 3: 0xA700, 4: 0xB000}) as s:
            report = self.send(s)
        self.assertEqual((report["sent"], report["pending"], report["failed"]), (3, 1, 1))
        lines = [json.loads(x) for x in (self.box / "journal.jsonl").read_text().splitlines()]
        self.assertEqual([x["status"] for x in lines], ["0x0000", "0xA900", "0xA700", "0xB000",
                                                        "0x0000"])
        series_uid = lines[0]["series"]
        self.assertEqual(outbox.retry_failed(self.box, series_uid), 1)
        with scp.StorageSCP(self.dir / "b") as s:
            report = self.send(s)
        self.assertEqual((report["sent"], report["pending"], report["failed"]), (5, 0, 0))

    def test_an_unreachable_archive_leaves_everything_pending(self):
        # REQ: SRS-DCM-007
        outbox.enqueue(self.box, make())
        report = outbox.send(self.box, "127.0.0.1", free_port(), "MINIDAQ", "ARCHIVE", timeout=1)
        self.assertEqual((report["pending"], report["sent"]), (5, 0))
        self.assertIn("cannot connect", report["errors"][0])

    def test_a_damaged_file_in_the_outbox_is_not_sent(self):
        # REQ: SRS-DCM-007
        paths = outbox.enqueue(self.box, make())
        paths[0].write_bytes(paths[0].read_bytes()[:500])
        with scp.StorageSCP(self.dir / "a") as s:
            report = self.send(s)
            self.assertEqual(len(s.files()), 4)
        self.assertEqual((report["sent"], report["failed"]), (4, 1))


class Command(unittest.TestCase):
    def test_export_send_and_dump(self):
        with tempfile.TemporaryDirectory() as d:
            d = pathlib.Path(d)
            np.save(d / "image.npy", image(slices=1)[0])
            for name, value in (("order", ORDER), ("acq", ACQ), ("rec", REC)):
                (d / f"{name}.json").write_text(json.dumps(value))
            args = ["export", str(d / "image.npy"), "--order", str(d / "order.json"),
                    "--acquisition", str(d / "acq.json"), "--reconstruction", str(d / "rec.json"),
                    "--outbox", str(d / "box")]
            self.assertEqual(pacs.main(args), 0)
            (d / "bad.json").write_text(json.dumps(dict(ORDER, PatientID="")))
            self.assertEqual(pacs.main(args[:3] + [str(d / "bad.json")] + args[4:]), 2)
            with scp.StorageSCP(d / "archive") as s:
                self.assertEqual(pacs.main(["echo", "--host", "127.0.0.1", "--port", str(s.port)]), 0)
                self.assertEqual(pacs.main(["send", str(d / "box"), "--host", "127.0.0.1",
                                            "--port", str(s.port)]), 0)
                text = "\n".join(pacs.dump(encode.read_file_bytes(s.files()[0].read_bytes())[1]))
            self.assertIn("(0010,0020) PatientID LO 'PHANTOM-0001'", text)


if __name__ == "__main__":
    unittest.main()
