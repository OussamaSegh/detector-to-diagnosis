#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Checks MiniDAQ's risk management file (Chapter 15).

docs/regulatory/risk/hazards.json holds the acceptability criteria and the hazard analysis:
for each hazard the sequence of events, the hazardous situation, the harm, its severity, the
probability of harm before and after the risk controls, the controls and the residual risk.
This tool checks what can be checked mechanically:

1. Every hazard has every field, its severity and probabilities are on the scales of the
   criteria, and its controls have IDs that no other control has.
2. Every control is inherent, protective or information; it is implemented by requirements
   of the SRS that are verified (a test names them, or the SRS gives evidence), and the
   evidence of its effectiveness exists: a test that the tests define, or a file.
3. A hazard whose risk after control is not acceptable is "open" and says what is planned;
   a closed hazard has an acceptable residual risk.
4. Every hazard refines one preliminary hazard of the software item classification
   (docs/architecture/software-items.json), every preliminary hazard is refined, and its
   severity there is the worst severity of the hazards that refine it.
5. The sorter's FMEA (docs/regulatory/risk/fmea-sorter.json) covers every sorter function and
   rates each failure mode on the severity scale and names existing requirements or controls.

Usage: check_risk.py ROOT. Exit status 0 if the file is consistent.
"""
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from trace_matrix import SRS, parse_srs, scan  # noqa: E402

RISK = pathlib.Path("docs/regulatory/risk/hazards.json")
FMEA = pathlib.Path("docs/regulatory/risk/fmea-sorter.json")
ITEMS = pathlib.Path("docs/architecture/software-items.json")
FIELDS = ("preliminary", "hazard", "sequence", "hazardous_situation", "harm", "severity", "probability_before",
          "controls", "probability_after", "residual", "status")
TYPES = {"inherent", "protective", "information"}


# [snippet:acceptable]
def index(level):
    return int(level[1:])


def acceptable(severity, probability):
    """MiniDAQ's criterion: severity index + probability index <= 5 (hazards.json)."""
    return index(severity) + index(probability) <= 5
# [/snippet:acceptable]


def check_hazards(doc, reqs, evidence, tests, root):
    errors = []
    crit = doc["criteria"]
    seen = set()
    for h in doc["hazards"]:
        hid = h.get("id", "?")
        for f in FIELDS:
            if f not in h or (isinstance(h[f], str) and not h[f].strip()):
                errors.append(f"{hid}: no {f}")
        if any(f not in h for f in FIELDS):
            continue
        if h["severity"] not in crit["severity"]:
            errors.append(f"{hid}: severity {h['severity']} is not on the scale")
            continue
        for p in ("probability_before", "probability_after"):
            if h[p] not in crit["probability"]:
                errors.append(f"{hid}: {p} {h[p]} is not on the scale")
        if any(h[p] not in crit["probability"] for p in ("probability_before", "probability_after")):
            continue
        if index(h["probability_after"]) > index(h["probability_before"]):
            errors.append(f"{hid}: the controls make harm more probable")
        ok_after = acceptable(h["severity"], h["probability_after"])
        if h["status"] == "closed" and not ok_after:
            errors.append(f"{hid}: closed, but {h['severity']}/{h['probability_after']} is not acceptable")
        if h["status"] == "open" and "planned" not in h["residual"].lower():
            errors.append(f"{hid}: open, so its residual risk says what is planned")
        if h["status"] not in ("open", "closed"):
            errors.append(f"{hid}: status must be 'open' or 'closed'")
        # [snippet:controls]
        for c in h["controls"]:
            cid = c.get("id", "?")
            if cid in seen:
                errors.append(f"{hid}: control {cid} is defined twice")
            seen.add(cid)
            if c.get("type") not in TYPES:
                errors.append(f"{cid}: type must be inherent, protective or information")
            for rid in c.get("requirements", []):
                if rid not in reqs:
                    errors.append(f"{cid}: requirement {rid} is not in the SRS")
                elif rid not in tests["by_requirement"] and rid not in evidence:
                    errors.append(f"{cid}: requirement {rid} is not verified")
            if c.get("type") != "information" and not c.get("requirements"):
                errors.append(f"{cid}: a design control is implemented by requirements")
            eff = c.get("effectiveness", {})
            method, ev = eff.get("method"), eff.get("evidence", "")
            if method == "test" and ev not in tests["names"]:
                errors.append(f"{cid}: effectiveness test {ev} does not exist or names no requirement")
            elif method == "inspection" and not (root / ev.split(",")[0]).is_file():
                errors.append(f"{cid}: inspected document {ev.split(',')[0]} does not exist")
            elif method not in ("test", "inspection", "analysis") or not ev.strip():
                errors.append(f"{cid}: effectiveness needs a method (test, inspection, analysis) and evidence")
        # [/snippet:controls]
    return errors


def check_items(doc, items):
    """The classification rests on the preliminary hazards; the analysis refines them."""
    errors = []
    order = list(doc["criteria"]["severity"])
    worst = {}
    for h in doc["hazards"]:
        z = h.get("preliminary")
        if z is None:
            errors.append(f"{h['id']}: no preliminary hazard of the classification")
        elif h.get("severity") in order:
            worst[z] = max(worst.get(z, h["severity"]), h["severity"], key=order.index)
    for z in items["hazards"]:
        if z["id"] not in worst:
            errors.append(f"software-items.json: {z['id']} is analyzed by no hazard of the risk file")
            continue
        cls = doc["criteria"]["severity_class"][worst[z["id"]]]
        if z["severity"] != cls:
            errors.append(f"software-items.json: {z['id']} is '{z['severity']}', its worst hazard is '{cls}':"
                          " revisit the classification")
    known = {z["id"] for z in items["hazards"]}
    for z in sorted(set(worst) - known):
        errors.append(f"risk file: preliminary hazard {z} is not in software-items.json")
    return errors


def check_fmea(fmea, reqs, controls, scale):
    errors = []
    covered = {row["function"] for row in fmea["rows"]}
    for f in fmea["functions"]:
        if f not in covered:
            errors.append(f"FMEA: function '{f}' has no failure mode")
    for row in fmea["rows"]:
        where = f"FMEA {row.get('function', '?')}: {row.get('failure_mode', '?')}"
        for k in ("function", "failure_mode", "effect", "cause", "severity", "detection", "controls"):
            if not row.get(k):
                errors.append(f"{where}: no {k}")
        if row.get("severity") and row["severity"] not in scale:
            errors.append(f"{where}: severity {row['severity']} is not on the scale")
        for ref in row.get("controls", []):
            if not (ref in reqs or ref in controls):
                errors.append(f"{where}: {ref} is neither a requirement nor a risk control")
        for ref in re.findall(r"H-\d\d", row.get("effect", "")):
            if ref not in {c.split(":")[0] for c in controls.values()}:
                errors.append(f"{where}: effect names {ref}, which the risk file does not define")
    return errors


def load(root):
    doc = json.loads((root / RISK).read_text())
    reqs, evidence, _ = parse_srs((root / SRS).read_text())
    tags = scan(root)
    tests = {"names": {t for _, t, _ in tags}, "by_requirement": {r for r, _, _ in tags}}
    return doc, reqs, evidence, tests


def main(root):
    doc, reqs, evidence, tests = load(root)
    errors = check_hazards(doc, reqs, evidence, tests, root)
    errors += check_items(doc, json.loads((root / ITEMS).read_text()))
    controls = {c["id"]: f"{h['id']}:{c['id']}" for h in doc["hazards"] for c in h["controls"]}
    if (root / FMEA).exists():
        errors += check_fmea(json.loads((root / FMEA).read_text()), reqs, controls, doc["criteria"]["severity"])
    else:
        errors.append(f"{FMEA} is missing")
    for e in errors:
        print(e)
    open_ = [h["id"] for h in doc["hazards"] if h.get("status") == "open"]
    print(f"risk file: {len(doc['hazards'])} hazards ({len(open_)} open: {', '.join(open_) or 'none'}), "
          + ("ok" if not errors else f"{len(errors)} problem(s)"))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(pathlib.Path(sys.argv[1]).resolve()))
