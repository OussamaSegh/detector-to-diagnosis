# SPDX-License-Identifier: MIT
"""A small model of the EU MDR classification rules that matter for a PET scanner
(Annex VIII: implementing rules 3.3 and 3.5, Rules 10, 11 and 13).

This is a teaching model, not a classification tool (see the README).
"""
from dataclasses import dataclass, field

ORDER = ["I", "IIa", "IIb", "III"]


@dataclass
class Device:
    name: str
    active: bool = True
    software_only: bool = False
    drives_device_class: str | None = None
    images_radiopharmaceuticals: bool = False
    emits_ionizing_radiation_for_diagnosis: bool = False
    supplies_energy_absorbed_by_body: bool = False
    diagnoses_vital_processes: bool = False
    patient_in_immediate_danger: bool = False
    informs_decisions: bool = False
    decision_impact: str = "none"  # none, non_serious, serious, irreversible
    monitors_physiology: bool = False


@dataclass
class Result:
    device_class: str
    rules: list[str] = field(default_factory=list)


def classify(d: Device) -> Result:
    # TODO: this version was written in a hurry. It stops at the first rule that
    # matches, treats all software the same, and forgets software that drives a device.
    if d.software_only:
        return Result("IIa", ["Rule 11: software -> IIa"])
    if d.images_radiopharmaceuticals:
        return Result("IIa", ["Rule 10: images radiopharmaceuticals -> IIa"])
    if d.emits_ionizing_radiation_for_diagnosis:
        return Result("IIb", ["Rule 10: emits ionizing radiation for diagnosis -> IIb"])
    return Result("I", ["Rule 13: all other active devices -> I"])
