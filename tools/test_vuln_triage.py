#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Checks tools/vuln_triage.py against a made-up scan report (Chapter 17), run by CTest.

    python3 tools/test_vuln_triage.py
"""
import contextlib
import io
import json
import pathlib
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import vuln_triage  # noqa: E402

REPORT = HERE / "testdata/grype-report.json"
GOOD = [
    {"vulnerability": "TEST-2026-0001", "component": "libssl3t64", "state": "exploitable", "response": "update",
     "fix_by": "2026-11-01", "detail": "The TLS server is affected; update the platform package."},
    {"vulnerability": "TEST-2026-0002", "component": "libssl3t64", "state": "not_affected",
     "justification": "code_not_reachable", "detail": "Only in DTLS, which MiniDAQ does not use."},
    {"vulnerability": "TEST-2026-0003", "component": "nlohmann-json", "state": "not_affected",
     "justification": "code_not_present", "detail": "In the SAX interface, which MiniDAQ does not use."},
]


def run(decisions, *extra):
    with tempfile.TemporaryDirectory() as d:
        triage = pathlib.Path(d) / "triage.json"
        triage.write_text(json.dumps({"decisions": decisions}))
        vex = pathlib.Path(d) / "vex.json"
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            status = vuln_triage.main([str(REPORT), str(triage), "--today", "2026-10-25", "--vex", str(vex), *extra])
        return status, out.getvalue(), json.loads(vex.read_text())


def change(i, **fields):
    decisions = [dict(d) for d in GOOD]
    decisions[i].update(fields)
    return [{k: v for k, v in d.items() if v is not None} for d in decisions]


def expect(status, text, needle):
    assert status == 1 and needle in text, f"expected a failure with '{needle}', got {status}:\n{text}"


def main():
    status, text, vex = run(GOOD)
    assert status == 0, text
    assert "3 finding(s) (1 exploitable, 2 not_affected), ok" in text, text
    assert [v["id"] for v in vex["vulnerabilities"]] == ["TEST-2026-0001", "TEST-2026-0002", "TEST-2026-0003"]
    assert vex["vulnerabilities"][1]["analysis"]["justification"] == "code_not_reachable"

    expect(*run(GOOD[1:])[:2], "TEST-2026-0001 in libssl3t64 3.0.13-0ubuntu3.16 (high): no decision, fixed in")
    expect(*run(change(0, fix_by=None))[:2], "needs a fix_by date")
    expect(*run(change(0, fix_by="2026-10-01"))[:2], "fix_by 2026-10-01 has passed")
    expect(*run(change(0, response=None))[:2], "exploitable needs a response")
    expect(*run(change(1, justification="looks fine"))[:2], "not_affected needs a CycloneDX justification")
    expect(*run(change(2, state="in_triage"))[:2], "critical: may not stay in triage")
    expect(*run(change(1, detail=" "))[:2], "no detail")
    expect(*run(change(1, state="wontfix"))[:2], "not a CycloneDX analysis state")
    assert run(change(1, state="in_triage"))[0] == 0, "a medium finding may wait in triage"

    stale = GOOD + [{"vulnerability": "TEST-2025-9999", "component": "libssl3t64", "state": "resolved",
                     "detail": "Fixed by the platform update of 2025."}]
    status, text, _ = run(stale)
    assert status == 0 and "TEST-2025-9999 in libssl3t64: decision matches no finding (stale)" in text, text
    expect(*run(stale, "--strict")[:2], "stale decision")
    print("vuln_triage: all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
