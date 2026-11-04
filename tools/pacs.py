#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""MiniDAQ's image export to an archive (Chapter 35, tool TL-44).

    tools/pacs.py export IMAGE.npy --order ORDER.json --acquisition ACQ.json \
        --reconstruction REC.json --outbox OUTBOX
    tools/pacs.py send OUTBOX --host HOST --port PORT [--calling MINIDAQ] [--called ARCHIVE]
    tools/pacs.py echo --host HOST --port PORT [--calling MINIDAQ] [--called ARCHIVE]
    tools/pacs.py scp DIRECTORY [--port PORT] [--ae ARCHIVE]     # a test archive, until Ctrl-C
    tools/pacs.py dump FILE.dcm

export makes a PET Image series of the image (a .npy array, [slice, row, column] or one
[row, column] slice, in MiniDAQ's gantry frame) and puts it in the outbox's pending/ directory;
send sends what is pending and prints the counts. The JSON files are described in
tools/dicom/pet.py; examples are in measurements/ch35/. Exit status: 0 when nothing is left
pending or failed, 1 otherwise, 2 for an input the export refuses.
"""
import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from tools.dicom import dictionary, encode, net, outbox, pet  # noqa: E402


def _json(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def dump(ds, indent=""):
    lines = []
    for tag, e in sorted(ds.items()):
        if e.vr == "SQ":
            lines.append(f"{indent}{dictionary.name(tag)} SQ, {len(e.value)} item(s)")
            for item in e.value:
                lines += dump(item, indent + "  ")
        elif isinstance(e.value, bytes):
            lines.append(f"{indent}{dictionary.name(tag)} {e.vr} {len(e.value)} bytes")
        else:
            lines.append(f"{indent}{dictionary.name(tag)} {e.vr} {e.value!r}")
    return lines


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="command", required=True)
    ex = sub.add_parser("export")
    ex.add_argument("image")
    for name in ("order", "acquisition", "reconstruction", "outbox"):
        ex.add_argument(f"--{name}", required=True)
    for name in ("send", "echo"):
        p = sub.add_parser(name)
        if name == "send":
            p.add_argument("outbox")
        p.add_argument("--host", required=True)
        p.add_argument("--port", type=int, required=True)
        p.add_argument("--calling", default="MINIDAQ")
        p.add_argument("--called", default="ARCHIVE")
        p.add_argument("--timeout", type=float, default=10.0)
        p.add_argument("--max-pdu", type=int, default=net.DEFAULT_MAX_PDU)
    sc = sub.add_parser("scp")
    sc.add_argument("directory")
    sc.add_argument("--port", type=int, default=11112)
    sc.add_argument("--ae", default="ARCHIVE")
    du = sub.add_parser("dump")
    du.add_argument("file")
    args = ap.parse_args(argv)

    if args.command == "export":
        import numpy as np  # noqa: PLC0415
        image = np.load(args.image)
        if image.ndim == 2:
            image = image[np.newaxis]
        try:
            paths = outbox.enqueue(args.outbox, pet.series(
                image, _json(args.order), _json(args.acquisition), _json(args.reconstruction)))
        except (encode.DicomError, KeyError) as e:
            print(f"export refused: {e}", file=sys.stderr)
            return 2
        print(f"{len(paths)} instance(s) pending in {paths[0].parent}")
        return 0
    if args.command == "send":
        report = outbox.send(args.outbox, args.host, args.port, args.calling, args.called,
                             args.timeout, args.max_pdu)
        print(json.dumps(report, indent=1))
        return 0 if report["pending"] == 0 and report["failed"] == 0 else 1
    if args.command == "echo":
        try:
            with net.associate(args.host, args.port, args.calling, args.called,
                               timeout=args.timeout, max_pdu=args.max_pdu) as a:
                status = a.echo()
        except net.AssociationError as e:
            print(f"echo failed: {e}", file=sys.stderr)
            return 1
        print(f"C-ECHO status {net.describe(status)}")
        return 0 if status == 0 else 1
    if args.command == "scp":
        from tools.dicom import scp  # noqa: PLC0415
        with scp.StorageSCP(args.directory, ae=args.ae, host="0.0.0.0", port=args.port) as s:
            print(f"storage SCP {args.ae} on port {s.port}, files in {args.directory}")
            try:
                s._stop.wait()
            except KeyboardInterrupt:
                pass
        return 0
    meta, ds = encode.read_file_bytes(pathlib.Path(args.file).read_bytes())
    print("\n".join(dump(meta) + dump(ds)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
