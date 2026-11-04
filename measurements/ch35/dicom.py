#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Chapter 35 measurements: the image of Chapter 33's phantom, exported as DICOM and sent.

    python3 measurements/ch35/dicom.py OUT_TEXT

Needs numpy, pydicom and pynetdicom (analysis/requirements.lock). Reads the image and the run
record kept in measurements/ch33/e2e/, the order, acquisition and reconstruction of this
directory, and writes the results as text; the numbers of the chapter come from that text.
Sections:
1. the series of the phantom: what it holds, read back by this package and by pydicom;
2. the quantization: the error of every pixel, and a slope per slice against one slope for a
   volume (a 47-slice volume made from the image, one slice ten times hotter);
3. the decimal string: the slope as format_ds writes it and as a fixed six decimals would;
4. the geometry: the cylinder's center in patient coordinates;
5. sending: the series to the test archive and to pynetdicom at several maximum PDU lengths;
6. faults: an association aborted after 20 instances, the resend, and a second export;
7. the independent reader is not strict: a sequence item with its tag in the wrong byte order.
"""
import io
import json
import pathlib
import statistics
import struct
import sys
import tempfile
import time
import warnings

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
from tools.dicom import encode, net, outbox, pet, scp, uid  # noqa: E402
from tools.dicom.encode import Dataset  # noqa: E402

import pydicom  # noqa: E402
from pynetdicom import AE, AllStoragePresentationContexts, evt  # noqa: E402
from pynetdicom.sop_class import Verification  # noqa: E402


def load():
    order = json.loads((HERE / "order.json").read_text())
    acq = json.loads((HERE / "acquisition.json").read_text())
    rec = json.loads((HERE / "reconstruction.json").read_text())
    image = np.load(ROOT / "measurements/ch33/e2e/image.npy")
    return image, order, acq, rec


def volume(image, slices=47, hot=23):
    """A volume for the quantization: the image in every slice, scaled by an axial profile
    (a cosine, 0.5 at the ends), and one slice ten times hotter."""
    z = np.linspace(-1.0, 1.0, slices)
    vol = np.stack([image * (0.75 + 0.25 * np.cos(np.pi * zi)) for zi in z])
    vol[hot] *= 10.0
    return vol


def main(out_path):
    lines = []

    def say(text=""):
        lines.append(text)

    image, order, acq, rec = load()
    say("Chapter 35: the DICOM export of the phantom image of Chapter 33")
    say(f"image: measurements/ch33/e2e/image.npy, {image.shape[0]} x {image.shape[1]}, "
        f"max {image.max():.6g}, min {image.min():.3g} (proportional counts)")
    say(f"pydicom {pydicom.__version__}, pynetdicom {__import__('pynetdicom').__version__}, "
        f"numpy {np.__version__}")
    say()

    say("1. The series")
    ds = pet.series(image[np.newaxis], order, acq, rec)
    with tempfile.TemporaryDirectory() as d:
        paths = pet.write_series(ds, d)
        size = paths[0].stat().st_size
        f = pydicom.dcmread(paths[0])
        _, mine = encode.read_file_bytes(paths[0].read_bytes())
    pixels = 2 * ds[0].get("Rows") * ds[0].get("Columns")
    say(f"instances: {len(ds)}; file size {size} bytes, of which pixel data {pixels} and "
        f"everything else {size - pixels} ({len(mine)} elements, preamble and meta included)")
    say(f"check_series: {pet.check_series(ds) or 'no problem'}")
    say(f"SeriesInstanceUID {ds[0].get('SeriesInstanceUID')} ({len(ds[0].get('SeriesInstanceUID'))} "
        "characters)")
    say(f"pydicom reads: PatientName {f.PatientName}, Units {f.Units}, RescaleSlope {f.RescaleSlope}, "
        f"ImagePositionPatient {list(f.ImagePositionPatient)}")
    same = np.array_equal(f.pixel_array.astype(np.float64) * float(f.RescaleSlope),
                          pet.values(mine))
    say(f"pydicom's pixel values times its slope equal this package's: {same}")
    say()

    say("2. Quantization")
    v = pet.values(ds[0])
    err = np.abs(v - image[::-1])
    slope = float(ds[0].get("RescaleSlope"))
    say(f"one slice: slope {ds[0].get('RescaleSlope')}, largest error {err.max():.4g} = "
        f"{err.max() / slope:.4f} slope, {err.max() / image.max():.3g} of the maximum")
    vol = volume(image)
    per_slice = pet.series(vol, order, acq, rec)
    global_slope = float(encode.format_ds(vol.max() / 65535))
    rel_per, rel_glob = [], []
    for k, d in enumerate(sorted(per_slice, key=lambda d: d.get("ImageIndex"))):
        truth = vol[k][::-1]
        mask = truth > 0.1 * truth.max()
        rel_per.append(float(np.median(np.abs(pet.values(d) - truth)[mask] / truth[mask])))
        g = np.rint(truth / global_slope) * global_slope
        rel_glob.append(float(np.median(np.abs(g - truth)[mask] / truth[mask])))
    cold = [k for k in range(len(rel_per)) if k != 23]
    say(f"volume of {vol.shape[0]} slices, slice 23 ten times hotter: median relative error inside "
        "the object (above 10% of the slice's maximum)")
    say(f"  slope per slice:  cold slices {statistics.median([rel_per[k] for k in cold]):.3g}, "
        f"hot slice {rel_per[23]:.3g}")
    say(f"  one slope (16 bits for the volume): cold slices "
        f"{statistics.median([rel_glob[k] for k in cold]):.3g}, hot slice {rel_glob[23]:.3g}")
    say()

    say("3. The decimal string")
    s = float(image.max()) / 65535
    six = f"{s:.6f}"
    say(f"slope {s!r}: format_ds gives {encode.format_ds(s)!r}; six decimals give {six!r}, "
        f"which a reader takes as {float(six)}: every pixel would read as 0")
    say()

    say("4. Geometry")
    v = pet.values(ds[0])
    ipp = np.array([float(t) for t in ds[0].get("ImagePositionPatient")])
    iop = np.array([float(t) for t in ds[0].get("ImageOrientationPatient")])
    p = float(ds[0].get("PixelSpacing")[0])
    rows, cols = np.mgrid[0:v.shape[0], 0:v.shape[1]]
    w = v / v.sum()
    centroid = ipp + (w * cols).sum() * p * iop[:3] + (w * rows).sum() * p * iop[3:]
    say(f"the cylinder's centroid in patient coordinates (LPS, mm): "
        f"({centroid[0]:.3f}, {centroid[1]:.3f}, {centroid[2]:.3f}); pixel {p:g} mm")
    say()

    say("5. Sending (loopback, a 47-slice series; median of 5 sends; TCP_NODELAY on both sides")
    say("   unless the line says otherwise)")
    series = per_slice
    nbytes = sum(len(encode.encode_dataset(d)) for d in series)
    say(f"data sets: {nbytes} bytes in all")
    for target, max_pdu, nodelay in [("test archive", m, True) for m in (4096, 16384, 65536, 0)] \
            + [("test archive", 16384, False)] \
            + [("pynetdicom", m, True) for m in (4096, 16384, 65536, 0)]:
        if True:
            times = []
            for _ in range(5):
                with tempfile.TemporaryDirectory() as d:
                    if target == "test archive":
                        with scp.StorageSCP(d, max_pdu=max_pdu) as a:
                            t = time.perf_counter()
                            with net.associate("127.0.0.1", a.port, "MINIDAQ", "ARCHIVE",
                                               nodelay=nodelay) as assoc:
                                statuses = [assoc.store(x) for x in series]
                            times.append(time.perf_counter() - t)
                    else:
                        ae = AE(ae_title="PYNETDICOM")
                        ae.supported_contexts = AllStoragePresentationContexts
                        ae.add_supported_context(Verification)
                        ae.maximum_pdu_size = max_pdu
                        with socket_port() as port:
                            pass
                        server = ae.start_server(("127.0.0.1", port), block=False,
                                                 evt_handlers=[(evt.EVT_C_STORE, lambda e: 0)])
                        try:
                            t = time.perf_counter()
                            with net.associate("127.0.0.1", port, "MINIDAQ",
                                               "PYNETDICOM") as assoc:
                                statuses = [assoc.store(x) for x in series]
                            times.append(time.perf_counter() - t)
                        finally:
                            server.shutdown()
            pdus = len(net.pdata(1, encode.encode_dataset(series[0]), False, max_pdu))
            flag = "" if nodelay else ", sender WITHOUT TCP_NODELAY"
            say(f"  {target:12s} max PDU {max_pdu or 'none':>6}{flag}: "
                f"{statistics.median(times) * 1000:7.1f} ms "
                f"({min(times) * 1000:.1f} to {max(times) * 1000:.1f}), {pdus} PDU(s) per data set, "
                f"all statuses 0x0000: {all(s == 0 for s in statuses)}")
    say()

    say("6. Faults")
    with tempfile.TemporaryDirectory() as d:
        d = pathlib.Path(d)
        box = d / "outbox"
        outbox.enqueue(box, series)
        with scp.StorageSCP(d / "archive", abort_after=20) as a:
            r = outbox.send(box, "127.0.0.1", a.port, "MINIDAQ", "ARCHIVE", timeout=2)
        say(f"aborted after 20: sent {r['sent']}, pending {r['pending']}, error: {r['errors'][0]}")
        outbox.enqueue(box, pet.series(vol, order, acq, rec))
        with scp.StorageSCP(d / "archive") as a:
            r = outbox.send(box, "127.0.0.1", a.port, "MINIDAQ", "ARCHIVE", timeout=2)
            files = len(a.files())
        say(f"exported again and resent: sent {r['sent']}, pending {r['pending']}, failed "
            f"{r['failed']}; the archive holds {files} instances")
        journal = (box / "journal.jsonl").read_text().splitlines()
        say(f"journal: {len(journal)} lines")
    say()

    say("7. The independent reader is not strict")
    item = encode.encode_dataset(Dataset().set("CodeValue", "77004003"))
    wrong = (bytes.fromhex("5400 0003") + b"SQ\0\0" + struct.pack("<I", 8 + len(item))
             + struct.pack("<II", 0xFFFEE000, len(item)) + item)
    base = Dataset().set("SOPClassUID", uid.PET_IMAGE_STORAGE).set("SOPInstanceUID", "2.25.1")
    data = encode.file_bytes(base, uid.IMPLEMENTATION_CLASS) + wrong
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        f = pydicom.dcmread(io.BytesIO(data))
        code = f.RadionuclideCodeSequence[0].CodeValue
    say(f"item tag written as one 32-bit integer (bytes 00 E0 FE FF instead of FE FF 00 E0): "
        f"pydicom reads CodeValue {code} with {len(caught)} warning(s)")
    try:
        encode.read_file_bytes(data)
        say("this package's reader: accepted")
    except encode.DicomError as e:
        say(f"this package's reader: refused ({e})")

    pathlib.Path(out_path).write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


class socket_port:
    """A free port on loopback."""

    def __enter__(self):
        import socket  # noqa: PLC0415
        self.s = socket.socket()
        self.s.bind(("127.0.0.1", 0))
        return self.s.getsockname()[1]

    def __exit__(self, *_):
        self.s.close()


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else HERE / "dicom.txt")
