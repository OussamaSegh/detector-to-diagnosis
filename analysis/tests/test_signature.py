# SPDX-License-Identifier: MIT
"""Signed runs and signed reports (release 1.3.0, CR-0027): every key is made by the test."""
from __future__ import annotations

import json
import pathlib

import mdql
import numpy as np
import pytest
from conftest import synthetic

from minidaq_analysis.__main__ import main
from minidaq_analysis.provenance import sha256_file
from minidaq_analysis.signature import (
    SignatureError,
    make_test_key,
    sign_file,
    verify_report,
    verify_run,
)


def signed_run(tmp_path: pathlib.Path, rng: np.random.Generator, key: pathlib.Path) -> pathlib.Path:
    """A run as the server signs it: the record lists each file's size and SHA-256 and is signed."""
    r = synthetic(rng, 50_000, seconds=1.0)
    n = int(np.count_nonzero((r["a"] & 0x8000) == 0))
    record = mdql.write_run(tmp_path / "run", [r], {"corrections": {"prompts": n}})
    doc = json.loads(record.read_text())
    doc["file_digests"] = [{"file": f, "bytes": (record.parent / f).stat().st_size,
                            "sha256": sha256_file(record.parent / f)} for f in doc["files"]]
    doc["signature"] = {"algorithm": "Ed25519", "key_id": "test"}
    record.write_text(json.dumps(doc, indent=2) + "\n")
    sign_file(record, key)
    return record


def test_a_signed_run_verifies_until_a_file_or_its_record_changes(
        tmp_path: pathlib.Path, rng: np.random.Generator) -> None:
    # REQ: SRS-ANA-007
    key, keys = make_test_key(tmp_path / "site")
    _, other = make_test_key(tmp_path / "other")
    record = signed_run(tmp_path, rng, key)
    assert verify_run(record, keys) == "test.pem"
    with pytest.raises(SignatureError, match="does not verify"):
        verify_run(record, other)
    data = record.parent / json.loads(record.read_text())["files"][0]
    raw = bytearray(data.read_bytes())
    raw[len(raw) // 2] ^= 1
    data.write_bytes(bytes(raw))
    with pytest.raises(SignatureError, match="SHA-256"):
        verify_run(record, keys)
    raw[len(raw) // 2] ^= 1
    data.write_bytes(bytes(raw))
    text = record.read_text()
    record.write_text(text.replace('"prompts"', '"prompts" ', 1))
    with pytest.raises(SignatureError, match="does not verify"):
        verify_run(record, keys)
    record.write_text(text)
    pathlib.Path(str(record) + ".sig").unlink()
    with pytest.raises(SignatureError, match="no signature"):
        verify_run(record, keys)


def test_the_qc_refuses_a_run_it_cannot_verify_and_signs_its_report(
        tmp_path: pathlib.Path, rng: np.random.Generator) -> None:
    # REQ: SRS-ANA-007
    # REQ: SRS-ANA-008
    key, keys = make_test_key(tmp_path / "site")
    record = signed_run(tmp_path, rng, key)
    out = tmp_path / "qc"
    assert main([str(record), str(out), "--keys", str(keys), "--sign", str(key)]) in (0, 1)
    assert verify_report(out, keys) == "test.pem"
    report = out / "report.json"
    report.write_text(report.read_text() + " ")  # any edit after signing
    with pytest.raises(SignatureError):
        verify_report(out, keys)

    pathlib.Path(str(record) + ".sig").unlink()
    refused = tmp_path / "refused"
    assert main([str(record), str(refused), "--keys", str(keys)]) == 2
    assert not (refused / "report.json").exists(), "no report of a run that does not verify"


def test_a_malformed_record_signed_by_a_trusted_key_is_refused(
        tmp_path: pathlib.Path, rng: np.random.Generator) -> None:
    # REQ: SRS-ANA-007
    # A trusted key can sign a record that is malformed: every case is a SignatureError, never
    # another exception (MDQ-PR-071).
    key, keys = make_test_key(tmp_path / "site")
    record = signed_run(tmp_path, rng, key)
    good = json.loads(record.read_text())
    name = good["files"][0]

    def refused(text: str, match: str) -> None:
        record.write_text(text)
        sign_file(record, key)
        with pytest.raises(SignatureError, match=match):
            verify_run(record, keys)

    def with_digest(**fields: object) -> str:
        doc = json.loads(json.dumps(good))
        doc["file_digests"][0].update(fields)
        return json.dumps(doc)

    refused("not json", "not a run record")
    refused("[1, 2]", "do not match")
    refused(with_digest(sha256=7), "no size or no SHA-256")
    refused(with_digest(bytes="12"), "no size or no SHA-256")
    refused(with_digest(bytes=True), "no size or no SHA-256")
    refused(with_digest(file=7), "has no digest")
    doc = json.loads(json.dumps(good))
    doc["files"][0] = doc["file_digests"][0]["file"] = 7
    refused(json.dumps(doc), "has no digest")
    for bad in ("", ".", ".."):
        doc["files"][0] = doc["file_digests"][0]["file"] = bad
        refused(json.dumps(doc), "not a path")
    record.write_text(json.dumps(good))
    sign_file(record, key)
    assert (record.parent / name).is_file()
    assert verify_run(record, keys) == "test.pem"
