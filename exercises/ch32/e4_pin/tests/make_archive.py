# SPDX-License-Identifier: MIT
"""Writes tinylib-1.0.tar from tinylib/, byte for byte the same on every machine: sorted names,
no time stamps, no owners. `python3 make_archive.py [OUT] [--tamper]`; --tamper writes the same
archive with one line of the header changed, as a moved tag or a replaced download would."""
import io
import pathlib
import sys
import tarfile

HERE = pathlib.Path(__file__).resolve().parent


def write(out, tamper=False):
    root = HERE / "tinylib"
    with tarfile.open(out, "w", format=tarfile.USTAR_FORMAT) as tar:
        for path in sorted(p for p in root.rglob("*") if p.is_file()):
            data = path.read_bytes()
            if tamper and path.name == "scale.hpp":
                data = data.replace(b"value * gain", b"value * gain + 1")
            info = tarfile.TarInfo("tinylib-1.0/" + path.relative_to(root).as_posix())
            info.size, info.mode, info.mtime = len(data), 0o644, 0
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            tar.addfile(info, io.BytesIO(data))


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--tamper"]
    write(args[0] if args else HERE / "tinylib-1.0.tar", "--tamper" in sys.argv)
