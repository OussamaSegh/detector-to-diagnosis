# SPDX-License-Identifier: MIT
"""Ed25519 signatures of runs and reports (release 1.3.0, ADR 0034; threat T-27).

The server signs a run's record, which lists the size and SHA-256 of every list-mode file of the
run (``<record>.sig``). Before a report trusts a run, :func:`verify_run` checks the signature
with the site's public keys and every file against the record. A report is signed the same way,
file by file, so that an edited report no longer verifies.

The cryptography is the ``openssl`` command line (OpenSSL 3, a SOUP item of MiniDAQ already),
as ``tools/make_update.py`` signs update bundles: the package needs no new dependency.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import tempfile

from .provenance import sha256_file

REPORT_FILES = ("report.json", "provenance.json", "report.md")


class SignatureError(ValueError):
    """A missing signature, one that does not verify, or a file that differs from the signed one."""


def sign_file(path: pathlib.Path, key: pathlib.Path) -> pathlib.Path:
    """Writes ``<path>.sig``, the Ed25519 signature of the file's exact bytes; returns its path."""
    sig = pathlib.Path(str(path) + ".sig")
    subprocess.run(["openssl", "pkeyutl", "-sign", "-rawin", "-inkey", str(key),
                    "-in", str(path), "-out", str(sig)], check=True, capture_output=True)
    return sig


def verify_file(path: pathlib.Path, keys: pathlib.Path) -> str:
    """The name of the public key in ``keys`` (``*.pem``) that verifies ``<path>.sig``, or
    SignatureError."""
    sig = pathlib.Path(str(path) + ".sig")
    if not sig.is_file():
        raise SignatureError(f"{path.name}: no signature {sig.name}")
    pems = sorted(keys.glob("*.pem"))
    if not pems:
        raise SignatureError(f"no public keys (*.pem) in {keys}")
    for pem in pems:
        r = subprocess.run(["openssl", "pkeyutl", "-verify", "-rawin", "-pubin", "-inkey", str(pem),
                            "-in", str(path), "-sigfile", str(sig)], capture_output=True)
        if r.returncode == 0:
            return pem.name
    raise SignatureError(f"{path.name}: the signature does not verify with any key in {keys}")


def verify_run(record: pathlib.Path, keys: pathlib.Path) -> str:
    """Checks a signed run: the record's signature first, then every file it lists against the
    size and SHA-256 the record states. Returns the key's name; SignatureError otherwise."""
    key = verify_file(record, keys)
    doc = json.loads(record.read_text(encoding="utf-8"))
    files, digests = doc.get("files"), doc.get("file_digests")
    if not isinstance(files, list) or not isinstance(digests, list) or len(files) != len(digests):
        raise SignatureError(f"{record.name}: signed, but its files and their digests do not match")
    for name, d in zip(files, digests, strict=True):
        if not isinstance(d, dict) or d.get("file") != name or "/" in str(name):
            raise SignatureError(f"{record.name}: {name} has no digest")
        p = record.parent / name
        if not p.is_file():
            raise SignatureError(f"{name}: missing")
        if p.stat().st_size != d.get("bytes") or sha256_file(p) != d.get("sha256"):
            raise SignatureError(f"{name}: its size or SHA-256 differs from the signed record")
    return key


def sign_report(out: pathlib.Path, key: pathlib.Path) -> list[pathlib.Path]:
    """Signs report.json, provenance.json and report.md in ``out``."""
    return [sign_file(out / name, key) for name in REPORT_FILES]


def verify_report(out: pathlib.Path, keys: pathlib.Path) -> str:
    """Checks the signatures of a signed report's files; returns the key's name."""
    names = {verify_file(out / name, keys) for name in REPORT_FILES}
    if len(names) != 1:
        raise SignatureError(f"{out}: the report's files were signed with different keys")
    return names.pop()


def make_test_key(directory: pathlib.Path, name: str = "test") -> tuple[pathlib.Path, pathlib.Path]:
    """A new Ed25519 key pair for tests: (private key, directory holding only its public key).
    Never for a real site: the private key lies unprotected in ``directory``."""
    directory.mkdir(parents=True, exist_ok=True)
    private = directory / f"{name}.key"
    keys = pathlib.Path(tempfile.mkdtemp(prefix=f"{name}-keys-", dir=directory))
    subprocess.run(["openssl", "genpkey", "-algorithm", "ED25519", "-out", str(private)],
                   check=True, capture_output=True)
    subprocess.run(["openssl", "pkey", "-in", str(private), "-pubout",
                    "-out", str(keys / f"{name}.pem")], check=True, capture_output=True)
    return private, keys
