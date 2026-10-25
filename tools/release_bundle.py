#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Packages a MiniDAQ release and its evidence, and verifies the packages (Chapter 20).

    release_bundle.py make BUILD OUT [--evidence DIR]
    release_bundle.py verify PRODUCT.tar [--evidence EVIDENCE.tar]
    release_bundle.py programs PRODUCT.tar

`make` takes the shipped build (preset `hardened`: Release, hardening and reproducible paths)
of a clean commit and writes two archives to OUT:

- minidaq-VERSION-COMMIT.tar, the product: the shipped programs without debug information,
  their debug information in separate files (found by build ID or debug link), the SBOM,
  BUILDINFO.json (what the build was made from and with) and MANIFEST.sha256. It contains only
  what the commit and the toolchain determine, no time and no host name, so that a second build
  of the same commit with the same toolchain gives the same archive, byte for byte
  (tools/repro_check.sh). Its SHA-256 is the identity of the release.
- minidaq-VERSION-COMMIT-evidence.tar, if --evidence is given: the output directory of
  tools/release_checks.sh for that commit, with its own manifest and the SHA-256 of the product
  archive it is evidence for.

`verify` checks an archive against itself (manifest, build IDs, debug links, the programs'
hashes in BUILDINFO.json) and, with --evidence, that the evidence belongs to this product: the
same commit, a clean tree, passing release checks and a passing system test report.
Exit status 0 if everything holds, 1 if not. `programs` lists the programs of a product
archive with their build IDs and SHA-256, as BUILDINFO.json records them.
"""
import argparse
import hashlib
import io
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
PROGRAMS = ["minidaq_server", "minidaq_ctl"]  # the shipped items (software-items.json)
# The cache entries that change the shipped programs. Options that only add tests, benchmarks or
# exercises are left out, so that a build of the programs alone gives the same product.
OPTIONS = ["CMAKE_CXX_STANDARD", "MINIDAQ_HARDENING", "MINIDAQ_REPRODUCIBLE", "MINIDAQ_SANITIZERS",
           "MINIDAQ_USE_SYSTEM_DEPS", "MINIDAQ_WARNINGS_AS_ERRORS"]
REQUIRED_EVIDENCE = ["commit.txt", "release-checks.txt", "system-test-report.md", "run_all.txt"]


def run(*cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=True).stdout


def first_line(*cmd):
    try:
        return run(*cmd).splitlines()[0].strip()
    except (OSError, subprocess.CalledProcessError, IndexError):
        return "not found"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def cache(build):
    text = (build / "CMakeCache.txt").read_text()
    return dict(re.findall(r"^([A-Za-z_0-9]+):[A-Z]+=(.*)$", text, re.M))


def build_id(path):
    m = re.search(r"Build ID: ([0-9a-f]+)", run("readelf", "-n", str(path)))
    return m.group(1) if m else None


def debuglink(path):
    """The file name and CRC-32 of a program's .gnu_debuglink section, or None."""
    with tempfile.TemporaryDirectory() as tmp:
        out = pathlib.Path(tmp) / "link"
        try:
            run("objcopy", "--dump-section", f".gnu_debuglink={out}", str(path), str(pathlib.Path(tmp) / "x"))
        except subprocess.CalledProcessError:
            return None
        data = out.read_bytes()
    name = data.split(b"\0", 1)[0].decode()
    return name, int.from_bytes(data[-4:], "little")


def toolchain(c):
    """The versions of the tools whose output is in the product (the tool list, Chapter 20)."""
    return {
        "compiler": first_line(c["CMAKE_CXX_COMPILER"], "--version"),
        "cmake": first_line("cmake", "--version"),
        "ninja": first_line("ninja", "--version"),
        "binutils": first_line("objcopy", "--version"),
        "c_library": first_line("ldd", "--version"),
        "openssl": first_line("openssl", "version"),
        "python": first_line(sys.executable, "--version"),
    }


# [snippet:deterministic_tar]
def write_tar(out, top, files):
    """A tar archive that depends only on the files' names, contents and modes: sorted entries,
    one fixed time, no owner. Uncompressed, so that a different zlib cannot change the bytes."""
    epoch = int(os.environ["SOURCE_DATE_EPOCH"])
    with tarfile.open(out, "w", format=tarfile.PAX_FORMAT) as tar:
        for rel in sorted(files):
            src = top / rel
            info = tarfile.TarInfo(f"{top.name}/{rel}")
            info.size = src.stat().st_size
            info.mtime = epoch
            info.mode = 0o755 if os.access(src, os.X_OK) else 0o644
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            with open(src, "rb") as f:
                tar.addfile(info, f)
# [/snippet:deterministic_tar]


def write_manifest(top):
    files = sorted(str(p.relative_to(top)) for p in top.rglob("*") if p.is_file())
    files = [f for f in files if f != "MANIFEST.sha256"]
    (top / "MANIFEST.sha256").write_text("".join(f"{sha256(top / f)}  {f}\n" for f in files))
    return files + ["MANIFEST.sha256"]


def split(built, top):
    """Copies one program into the product without its debug information, and the debug
    information into its own file. Returns the program's entry for BUILDINFO.json."""
    # [snippet:split]
    prog = built.name
    debug = top / "debug" / f"{prog}.debug"
    shipped = top / "bin" / prog
    run("objcopy", "--only-keep-debug", str(built), str(debug))
    # The debug link names the debug file and holds its CRC-32; objcopy reads the file from the
    # current directory, so the link has no directory in it.
    run("objcopy", "--strip-debug", f"--add-gnu-debuglink={debug.name}", str(built), str(shipped), cwd=debug.parent)
    # [/snippet:split]
    return {"name": prog, "build_id": build_id(shipped), "sha256": sha256(shipped), "debug_sha256": sha256(debug)}


def package_product(programs, info, out, sbom=None):
    """Writes the product archive for `programs` (paths of built programs) and returns its path.
    `info` is BUILDINFO.json without the programs; it must name version, commit and
    source_date_epoch. `sbom(path)` writes the SBOM, if given."""
    name = f"minidaq-{info['version']}-{info['commit'][:12]}"
    os.environ["SOURCE_DATE_EPOCH"] = str(info["source_date_epoch"])
    with tempfile.TemporaryDirectory() as tmp:
        top = pathlib.Path(tmp) / name
        for d in ("bin", "debug", "sbom"):
            (top / d).mkdir(parents=True)
        info = dict(info, programs=[split(p, top) for p in programs])
        if sbom:
            sbom(top / "sbom/minidaq.cdx.json")
        (top / "BUILDINFO.json").write_text(json.dumps(info, indent=2, sort_keys=True) + "\n")
        product = out / f"{name}.tar"
        write_tar(product, top, write_manifest(top))
    return product


def package_evidence(product, evidence_dir, out):
    """Writes the evidence archive that binds `evidence_dir` to `product` by its SHA-256."""
    name = product.name.removesuffix(".tar") + "-evidence"
    with tempfile.TemporaryDirectory() as tmp:
        top = pathlib.Path(tmp) / name
        shutil.copytree(evidence_dir, top / "evidence")
        (top / "PRODUCT.sha256").write_text(f"{sha256(product)}  {product.name}\n")
        evidence = out / f"{name}.tar"
        write_tar(evidence, top, write_manifest(top))
    return evidence


def make(args):
    build = args.build.resolve()
    c = cache(build)
    wanted = {"CMAKE_BUILD_TYPE": "Release", "MINIDAQ_HARDENING": "ON", "MINIDAQ_REPRODUCIBLE": "ON"}
    wrong = {k: c.get(k) for k, v in wanted.items() if c.get(k) != v}
    if wrong:
        sys.exit(f"{build} is not the shipped build (preset hardened): {wrong}")
    commit = run("git", "-C", str(ROOT), "rev-parse", "HEAD").strip()
    if run("git", "-C", str(ROOT), "status", "--porcelain", "--untracked-files=no").strip():
        sys.exit("the working tree has uncommitted changes: a release is made from a commit")
    info = {
        "product": "MiniDAQ",
        "version": (ROOT / "VERSION").read_text().strip(),
        "commit": commit,
        "source_date_epoch": int(run("git", "-C", str(ROOT), "log", "-1", "--format=%ct").strip()),
        "preset": "hardened",
        "build_type": c["CMAKE_BUILD_TYPE"],
        "cxx_flags": c.get("CMAKE_CXX_FLAGS_RELEASE", ""),
        "options": {k: c.get(k, "") for k in OPTIONS},
        "rebuild": ["git checkout " + commit, "cmake --preset hardened", "cmake --build --preset hardened",
                    "tools/release_bundle.py make build/hardened OUT"],
        "toolchain": toolchain(c),
    }

    def sbom(path):
        subprocess.run([sys.executable, str(ROOT / "tools/make_sbom.py"), "-o", str(path), str(ROOT)],
                       check=True, capture_output=True)

    args.out.mkdir(parents=True, exist_ok=True)
    product = package_product([build / "minidaq/apps" / p for p in PROGRAMS], info, args.out, sbom)
    print(f"{product}  sha256 {sha256(product)}")
    if args.evidence:
        evidence = package_evidence(product, args.evidence, args.out)
        print(f"{evidence}  sha256 {sha256(evidence)}")
    return 0


class Checks:
    def __init__(self):
        self.failures = []

    def __call__(self, ok, what):
        print(f"{'ok  ' if ok else 'FAIL'}  {what}")
        if not ok:
            self.failures.append(what)


def unpack(archive, into):
    with tarfile.open(archive) as tar:
        tar.extractall(into, filter="data")
    tops = list(pathlib.Path(into).iterdir())
    if len(tops) != 1:
        raise ValueError(f"{archive}: expected one top directory, found {len(tops)}")
    return tops[0]


# [snippet:verify_manifest]
def check_manifest(top, check):
    listed = {}
    for line in (top / "MANIFEST.sha256").read_text().splitlines():
        digest, rel = line.split("  ", 1)
        listed[rel] = digest
    present = {str(p.relative_to(top)) for p in top.rglob("*") if p.is_file()} - {"MANIFEST.sha256"}
    check(not (present - listed.keys()), f"no file outside the manifest {sorted(present - listed.keys())}")
    check(not (listed.keys() - present), f"no file of the manifest missing {sorted(listed.keys() - present)}")
    changed = sorted(r for r in listed.keys() & present if sha256(top / r) != listed[r])
    check(not changed, f"every file matches its SHA-256 {changed}")
# [/snippet:verify_manifest]


def verify(args):
    check = Checks()
    with tempfile.TemporaryDirectory() as tmp:
        top = unpack(args.product, pathlib.Path(tmp) / "p")
        check_manifest(top, check)
        info = json.loads((top / "BUILDINFO.json").read_text())
        check(top.name == f"minidaq-{info['version']}-{info['commit'][:12]}", f"archive named after its build {top.name}")
        for p in info["programs"]:
            shipped, debug = top / "bin" / p["name"], top / "debug" / f"{p['name']}.debug"
            check(sha256(shipped) == p["sha256"], f"{p['name']}: SHA-256 as in BUILDINFO.json")
            check(build_id(shipped) == p["build_id"] == build_id(debug),
                  f"{p['name']}: build ID {p['build_id']} in the program and in its debug file")
            link = debuglink(shipped)
            check(link == (debug.name, zlib.crc32(debug.read_bytes())), f"{p['name']}: debug link names its debug file and its CRC")
            check(".debug_info" not in run("readelf", "-S", "-W", str(shipped)), f"{p['name']}: shipped without debug information")
        check((top / "sbom/minidaq.cdx.json").is_file(), "SBOM present")
        product_sha = sha256(args.product)
        print(f"product {args.product.name}  sha256 {product_sha}")

        if args.evidence:
            etop = unpack(args.evidence, pathlib.Path(tmp) / "e")
            check_manifest(etop, check)
            digest, _ = (etop / "PRODUCT.sha256").read_text().split("  ", 1)
            check(digest == product_sha, "the evidence names this product's SHA-256")
            ev = etop / "evidence"
            for f in REQUIRED_EVIDENCE:
                check((ev / f).is_file(), f"evidence has {f}")
            if (ev / "commit.txt").is_file():
                lines = (ev / "commit.txt").read_text().splitlines()
                check(lines[:1] == [f"commit {info['commit']}"] and len(lines) == 1,
                      "the release checks ran on this commit, on a clean tree")
            if (ev / "release-checks.txt").is_file():
                text = (ev / "release-checks.txt").read_text()
                check("all release checks passed" in text and "FAIL " not in text, "every release check passed")
            if (ev / "system-test-report.md").is_file():
                text = (ev / "system-test-report.md").read_text()
                check("The system tests passed." in text and "uncommitted" not in text,
                      "the system test report passed, on a clean commit")
    print(f"{len(check.failures)} check(s) failed" if check.failures else "verified")
    return 1 if check.failures else 0


def programs(args):
    with tarfile.open(args.product) as tar:
        info = next(m for m in tar.getmembers() if m.name.endswith("/BUILDINFO.json"))
        for p in json.load(tar.extractfile(info))["programs"]:
            print(f"  {p['name']:16} build ID {p['build_id']}  sha256 {p['sha256']}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make")
    m.add_argument("build", type=pathlib.Path)
    m.add_argument("out", type=pathlib.Path)
    m.add_argument("--evidence", type=pathlib.Path)
    v = sub.add_parser("verify")
    v.add_argument("product", type=pathlib.Path)
    v.add_argument("--evidence", type=pathlib.Path)
    sub.add_parser("programs").add_argument("product", type=pathlib.Path)
    args = ap.parse_args(argv)
    return {"make": make, "verify": verify, "programs": programs}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
