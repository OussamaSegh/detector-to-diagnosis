# SPDX-License-Identifier: MIT
"""Exercise 17.3: the triage rules of tools/vuln_triage.py, as a module.

Every finding of the scan needs a decision in the analysis states of CycloneDX VEX; see the
repository's tools/vuln_triage.py for the rules.
"""
import datetime

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


def apply(scan, decisions, today):
    """The problems of the triage: findings without a decision and decisions that break a rule."""
    by_key = {(d["vulnerability"], d["component"]): d for d in decisions}
    errors = []
    for f in findings(scan):
        d = by_key.get((f["id"], f["component"]))
        where = f"{f['id']} in {f['component']}"
        if d is None:
            errors.append(f"{where}: no decision")
        else:
            errors += [f"{where}: {p}" for p in check_decision(d, f["severity"], today)]
    return errors
