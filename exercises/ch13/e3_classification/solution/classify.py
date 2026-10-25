# SPDX-License-Identifier: MIT
"""A small model of the EU MDR classification rules that matter for a PET scanner
(Annex VIII: implementing rules 3.3 and 3.5, Rules 10, 11 and 13).

This is a teaching model, not a classification tool. The real rules have more cases,
and a real classification is a documented decision of the manufacturer, checked by the
notified body (verify against the MDR text and MDCG 2021-24).
"""
from dataclasses import dataclass, field

ORDER = ["I", "IIa", "IIb", "III"]


@dataclass
class Device:
    name: str
    active: bool = True
    software_only: bool = False
    # Implementing rule 3.3: software that drives or influences the use of a device
    # takes that device's class. Give the class of the device it drives.
    drives_device_class: str | None = None
    # Rule 10 (active devices for diagnosis and monitoring).
    images_radiopharmaceuticals: bool = False
    emits_ionizing_radiation_for_diagnosis: bool = False
    supplies_energy_absorbed_by_body: bool = False
    diagnoses_vital_processes: bool = False
    patient_in_immediate_danger: bool = False
    # Rule 11 (software).
    informs_decisions: bool = False
    decision_impact: str = "none"  # none, non_serious, serious, irreversible
    monitors_physiology: bool = False


@dataclass
class Result:
    device_class: str
    rules: list[str] = field(default_factory=list)  # every rule that applied, with its class


def strictest(classes):
    return max(classes, key=ORDER.index)


# [snippet:rules]
def classify(d: Device) -> Result:
    found = []  # (class, rule)
    if d.software_only and d.drives_device_class:
        found.append((d.drives_device_class, "3.3: drives or influences a device"))
    elif d.software_only:
        if d.informs_decisions:
            impact = {"irreversible": "III", "serious": "IIb"}.get(d.decision_impact, "IIa")
            found.append((impact, "Rule 11: information for decisions"))
        if d.monitors_physiology:
            found.append(("IIb" if d.patient_in_immediate_danger else "IIa",
                          "Rule 11: monitors physiological processes"))
        if not found:
            found.append(("I", "Rule 11: all other software"))
    elif d.active:
        if d.emits_ionizing_radiation_for_diagnosis:
            found.append(("IIb", "Rule 10: emits ionizing radiation for diagnosis"))
        if d.images_radiopharmaceuticals:
            found.append(("IIa", "Rule 10: images radiopharmaceuticals"))
        if d.supplies_energy_absorbed_by_body:
            found.append(("IIa", "Rule 10: supplies energy absorbed by the body"))
        if d.diagnoses_vital_processes:
            found.append(("IIb" if d.patient_in_immediate_danger else "IIa",
                          "Rule 10: diagnoses vital physiological processes"))
        if not found:
            found.append(("I", "Rule 13: all other active devices"))
    else:
        raise ValueError(f"{d.name}: non-active devices are outside this model")
    # Implementing rule 3.5: if several rules apply, the strictest one decides.
    return Result(strictest(c for c, _ in found), [f"{r} -> {c}" for c, r in found])
# [/snippet:rules]
