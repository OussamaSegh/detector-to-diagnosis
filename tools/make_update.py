#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Builds and signs an update bundle for minidaq_update (Chapter 25, ADR 0020).

Usage: tools/make_update.py --stage DIR --version X.Y.Z --commit SHA --platform ID
                            --key PRIVATE.pem --out BUNDLE_DIR

DIR is the tree to install into a slot (bin/minidaq_server, bin/minidaq_ctl, share/...).
The bundle gets three files: the archive minidaq-X.Y.Z.tar.gz, which holds the tree and its
MANIFEST.sha256; update.json, which names the archive with its size and SHA-256; and
update.json.sig, an Ed25519 signature of update.json made with `openssl pkeyutl -rawin`.

The archive is reproducible: members sorted, owner 0, modes 0755 or 0644, times and the gzip
header from SOURCE_DATE_EPOCH (0 if unset), so the same tree gives the same bytes and a release
can be checked against its SBOM later. The private key belongs to the release process: in an
HSM or on an offline machine, never in the repository or on an acquisition PC (assumption:
confirm with team how the key is held and who may sign). Symbolic links and special files in
the stage are refused, as minidaq_update would refuse them.
"""
import argparse
import gzip
import hashlib
import io
import json
import os
import pathlib
import re
import subprocess
import sys
import tarfile

MANIFEST_FORMAT = "minidaq-update 1"
VERSION = re.compile(r"^\d{1,5}\.\d{1,5}\.\d{1,5}(-[0-9A-Za-z.]+)?$")


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def tree(stage):
    """The stage's regular files, relative and sorted; refuses anything else."""
    files = []
    for path in sorted(stage.rglob("*")):
        rel = path.relative_to(stage).as_posix()
        if path.is_symlink() or not (path.is_file() or path.is_dir()):
            raise SystemExit(f"make_update: {rel} is not a regular file or a directory")
        if path.is_file():
            if rel == "MANIFEST.sha256":
                raise SystemExit("make_update: the stage must not have its own MANIFEST.sha256")
            files.append(rel)
    if not files:
        raise SystemExit(f"make_update: {stage} has no files")
    return files


# [snippet:archive]
def archive(stage, files, epoch):
    """The tar.gz bytes of the stage's files plus MANIFEST.sha256, reproducibly."""
    contents = {rel: (stage / rel).read_bytes() for rel in files}
    manifest = "".join(f"{sha256(contents[rel])}  {rel}\n" for rel in files).encode()
    contents["MANIFEST.sha256"] = manifest
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.PAX_FORMAT) as tar:
        dirs = sorted({str(d) for rel in contents for d in pathlib.PurePosixPath(rel).parents} - {"."})
        for d in dirs:
            info = tarfile.TarInfo(d)
            info.type, info.mode, info.mtime = tarfile.DIRTYPE, 0o755, epoch
            tar.addfile(info)
        for rel in sorted(contents):
            info = tarfile.TarInfo(rel)
            info.size, info.mtime = len(contents[rel]), epoch
            executable = rel != "MANIFEST.sha256" and os.access(stage / rel, os.X_OK)
            info.mode = 0o755 if executable else 0o644
            tar.addfile(info, io.BytesIO(contents[rel]))
    out = io.BytesIO()
    with gzip.GzipFile(fileobj=out, mode="wb", mtime=epoch, filename="") as gz:
        gz.write(raw.getvalue())
    return out.getvalue()
# [/snippet:archive]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--stage", required=True, type=pathlib.Path)
    ap.add_argument("--version", required=True)
    ap.add_argument("--commit", required=True)
    ap.add_argument("--platform", required=True)
    ap.add_argument("--key", required=True, type=pathlib.Path, help="Ed25519 private key (PEM)")
    ap.add_argument("--out", required=True, type=pathlib.Path)
    args = ap.parse_args(argv)
    if not VERSION.match(args.version):
        raise SystemExit(f"make_update: version {args.version!r} is not MAJOR.MINOR.PATCH[-PRE]")
    epoch = int(os.environ.get("SOURCE_DATE_EPOCH", "0"))

    data = archive(args.stage, tree(args.stage), epoch)
    args.out.mkdir(parents=True, exist_ok=True)
    name = f"minidaq-{args.version}.tar.gz"
    (args.out / name).write_bytes(data)
    manifest = {"format": MANIFEST_FORMAT, "product": "minidaq", "version": args.version,
                "commit": args.commit, "platform": args.platform, "archive": name,
                "size": len(data), "sha256": sha256(data)}
    (args.out / "update.json").write_text(json.dumps(manifest, indent=2) + "\n")
    # [snippet:sign]
    subprocess.run(["openssl", "pkeyutl", "-sign", "-rawin", "-inkey", str(args.key),
                    "-in", str(args.out / "update.json"), "-out", str(args.out / "update.json.sig")],
                   check=True)
    # [/snippet:sign]
    print(f"make_update: {args.out}: {name}, {len(data)} bytes, sha256 {manifest['sha256'][:16]}...")
    return 0


if __name__ == "__main__":
    sys.exit(main())
