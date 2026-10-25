"""Exercise 15.5: the risk matrix and the overall residual risk.

matrix() places each hazard of a risk file (docs/regulatory/risk/hazards.json) in the cell of
its severity and its probability, before or after risk control. render() draws the matrix as
a Markdown table with the cells that the criterion does not accept marked. overall() is the
mechanical part of the evaluation of overall residual risk: what must be resolved or justified
before a release.
"""
SEVERITIES = ("S1", "S2", "S3", "S4")
PROBABILITIES = ("P1", "P2", "P3", "P4", "P5")


def acceptable(severity, probability):
    return int(severity[1:]) + int(probability[1:]) <= 5


def matrix(doc, when="after"):
    key = "probability_before"  # TODO: before or after, as asked
    cells = {}
    for h in doc["hazards"]:
        cells.setdefault((h["severity"], h[key]), []).append(h["id"])
    return {k: sorted(v) for k, v in cells.items()}


def render(doc, when="after"):
    cells = matrix(doc, when)
    lines = [f"Risk {when} control (* not acceptable)", "",
             "| Severity | " + " | ".join(PROBABILITIES) + " |",
             "|---|" + "---|" * len(PROBABILITIES)]
    for s in reversed(SEVERITIES):
        row = []
        for p in PROBABILITIES:
            ids = ", ".join(cells.get((s, p), []))
            row.append(ids + ("" if acceptable(s, p) else " *"))
        lines.append(f"| {s} | " + " | ".join(c.strip() for c in row) + " |")
    return "\n".join(lines) + "\n"


def overall(doc):
    # TODO: open hazards, and the reasons a release must resolve or justify.
    unacceptable = sorted(h["id"] for h in doc["hazards"]
                          if not acceptable(h["severity"], h["probability_after"]))
    return {"acceptable": not unacceptable, "open": [], "unacceptable": unacceptable, "reasons": []}
