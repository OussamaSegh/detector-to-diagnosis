#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Applies MiniDAQ's vulnerability triage to a scan of its SBOM (Chapter 17).

A scanner such as Grype matches the SBOM's components against vulnerability databases and
reports every vulnerability recorded for a component's version. It cannot know whether MiniDAQ
uses the affected function, so every finding needs a decision by a person, recorded in
docs/regulatory/security/vulnerability-triage.json in the analysis states of CycloneDX's
vulnerability exploitability exchange (VEX):

- not_affected: with a justification from CycloneDX's list and a detail that says why;
- exploitable: with a response (update, workaround_available, ...) and, for a high or critical
  severity, a "fix_by" date that has not passed;
- in_triage: allowed only below high severity;
- resolved, false_positive: with a detail.

This tool fails for a finding without a decision, for a decision that breaks these rules, and,
with --strict, for a decision that matches no finding (the component was updated, so the
decision is stale). With --vex FILE it writes the decisions for the scan's findings as a
CycloneDX 1.5 VEX document.

Usage: vuln_triage.py SCAN.json TRIAGE.json [--today YYYY-MM-DD] [--strict] [--vex OUT.json]
SCAN.json is Grype's JSON output (grype sbom:minidaq.cdx.json -o json). Exit status 0 if every
finding is triaged and every decision is valid.
"""
import argparse
import datetime
import json
import pathlib
import sys

STATES = {"resolved", "resolved_with_pedigree", "exploitable", "in_triage", "false_positive", "not_affected"}
JUSTIFICATIONS = {"code_not_present", "code_not_reachable", "requires_configuration", "requires_dependency",
                  "requires_environment", "protected_by_compiler", "protected_at_runtime", "protected_at_perimeter",
                  "protected_by_mitigating_control"}
RESPONSES = {"can_not_fix", "will_not_fix", "update", "rollback", "workaround_available"}
SEVERE = {"high", "critical"}


def findings(scan):
    """(vulnerability id, component name, severity, fixed-in versions) for every match."""
    out = []
    for m in scan.get("matches", []):
        v, a = m["vulnerability"], m["artifact"]
        fix = v.get("fix", {}).get("versions", [])
        out.append({"id": v["id"], "component": a["name"], "version": a.get("version", ""),
                    "severity": v.get("severity", "Unknown").lower(), "fixed_in": fix})
    return out


# [snippet:rules]
def check_decision(d, severity, today):
    """The problems of one decision, for a finding of the given severity."""
    problems = []
    state = d.get("state")
    if state not in STATES:
        return [f"state '{state}' is not a CycloneDX analysis state"]
    if not d.get("detail", "").strip():
        problems.append("no detail: say why")
    if state == "not_affected" and d.get("justification") not in JUSTIFICATIONS:
        problems.append("not_affected needs a CycloneDX justification")
    if state == "exploitable":
        if d.get("response") not in RESPONSES:
            problems.append("exploitable needs a response")
        if severity in SEVERE:
            fix_by = d.get("fix_by")
            if not fix_by:
                problems.append(f"exploitable and {severity}: needs a fix_by date")
            elif datetime.date.fromisoformat(fix_by) < today:
                problems.append(f"exploitable and {severity}: fix_by {fix_by} has passed")
    if state == "in_triage" and severity in SEVERE:
        problems.append(f"{severity}: may not stay in triage; decide")
    return problems
# [/snippet:rules]


def vex(matched):
    """A CycloneDX 1.5 document that carries only the vulnerabilities and their analysis."""
    vulns = []
    for f, d in matched:
        analysis = {"state": d["state"], "detail": d["detail"]}
        if "justification" in d:
            analysis["justification"] = d["justification"]
        if "response" in d:
            analysis["response"] = [d["response"]]
        vulns.append({"id": f["id"], "analysis": analysis,
                      "affects": [{"ref": f"{f['component']}@{f['version']}"}]})
    return {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1, "vulnerabilities": vulns}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("scan", type=pathlib.Path)
    ap.add_argument("triage", type=pathlib.Path)
    ap.add_argument("--today", type=datetime.date.fromisoformat, default=datetime.date.today())
    ap.add_argument("--strict", action="store_true", help="fail for decisions that match no finding")
    ap.add_argument("--vex", type=pathlib.Path)
    args = ap.parse_args(argv)
    found = findings(json.loads(args.scan.read_text()))
    decisions = json.loads(args.triage.read_text())["decisions"]
    by_key = {(d["vulnerability"], d["component"]): d for d in decisions}

    errors, matched, used = [], [], set()
    for f in sorted(found, key=lambda f: (f["component"], f["id"])):
        key = (f["id"], f["component"])
        d = by_key.get(key)
        where = f"{f['id']} in {f['component']} {f['version']} ({f['severity']})"
        if d is None:
            fix = f", fixed in {', '.join(f['fixed_in'])}" if f["fixed_in"] else ""
            errors.append(f"{where}: no decision{fix}")
            continue
        used.add(key)
        matched.append((f, d))
        errors += [f"{where}: {p}" for p in check_decision(d, f["severity"], args.today)]
    stale = [k for k in by_key if k not in used]
    for vid, comp in stale:
        print(f"{vid} in {comp}: decision matches no finding (stale)")
    if args.strict:
        errors += [f"{vid} in {comp}: stale decision" for vid, comp in stale]
    for e in errors:
        print(e)
    if args.vex:
        args.vex.write_text(json.dumps(vex(matched), indent=2) + "\n")
    states = {}
    for _, d in matched:
        states[d["state"]] = states.get(d["state"], 0) + 1
    summary = ", ".join(f"{n} {s}" for s, n in sorted(states.items())) or "none"
    print(f"vulnerability triage: {len(found)} finding(s) ({summary}), "
          + ("ok" if not errors else f"{len(errors)} problem(s)"))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
