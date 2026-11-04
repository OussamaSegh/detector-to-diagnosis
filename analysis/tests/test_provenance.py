# SPDX-License-Identifier: MIT
"""The dataset manifest notices any change to the bytes."""
from __future__ import annotations

import hashlib
import pathlib

from minidaq_analysis import provenance as P


def test_a_manifest_verifies_until_a_byte_changes(tmp_path: pathlib.Path) -> None:
    # REQ: SRS-ANA-006
    (tmp_path / "a.mdql").write_bytes(b"x" * 1000)
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.json").write_text("{}")
    files = [tmp_path / "sub" / "b.json", tmp_path / "a.mdql"]
    m = P.make_manifest(files, tmp_path)
    assert [f["path"] for f in m["files"]] == ["a.mdql", "sub/b.json"]
    assert m["files"][0]["sha256"] == hashlib.sha256(b"x" * 1000).hexdigest()
    assert P.verify_manifest(m, tmp_path) == []
    (tmp_path / "a.mdql").write_bytes(b"x" * 999 + b"y")
    assert P.verify_manifest(m, tmp_path) == ["a.mdql: SHA-256 differs"]
    (tmp_path / "sub" / "b.json").unlink()
    assert "sub/b.json: missing" in P.verify_manifest(m, tmp_path)


def test_the_manifest_id_names_the_content_not_the_order(tmp_path: pathlib.Path) -> None:
    # REQ: SRS-ANA-006
    for name in ("a", "b"):
        (tmp_path / name).write_text(name)
    one = P.make_manifest([tmp_path / "a", tmp_path / "b"], tmp_path)
    two = P.make_manifest([tmp_path / "b", tmp_path / "a"], tmp_path)
    assert P.manifest_id(one) == P.manifest_id(two)
    (tmp_path / "b").write_text("c")
    assert P.manifest_id(P.make_manifest([tmp_path / "a", tmp_path / "b"], tmp_path)) != \
        P.manifest_id(one)


def test_the_environment_names_the_versions_that_change_numbers() -> None:
    # REQ: SRS-ANA-006
    env = P.environment(["minidaq-qc", "x"])
    assert env["libraries"]["numpy"] and env["libraries"]["scipy"]
    assert env["command"] == ["minidaq-qc", "x"] and env["created_utc"].endswith("Z")


def _pep440(version: str) -> str:
    """MiniDAQ's VERSION ("0.8.0-dev" or "0.8.0") as a Python package version."""
    return version[:-len("-dev")] + ".dev0" if version.endswith("-dev") else version


def test_the_recorded_version_is_the_repository_version() -> None:
    # REQ: SRS-ANA-006
    # The environment record names the package's version; it stayed 0.7.0.dev0 through release
    # 0.7.0 and into 0.8.0-dev. The package, its pyproject.toml and the wheel of the projector
    # must follow VERSION, which the release changes.
    import tomllib

    from minidaq_analysis import __version__

    root = pathlib.Path(__file__).resolve().parents[2]
    want = _pep440((root / "VERSION").read_text().strip())
    assert __version__ == want
    for pyproject in ("analysis/pyproject.toml", "recon/python/pyproject.toml"):
        with open(root / pyproject, "rb") as f:
            assert tomllib.load(f)["project"]["version"] == want, pyproject
