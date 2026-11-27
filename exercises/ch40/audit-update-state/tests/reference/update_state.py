# SPDX-License-Identifier: MIT
"""The state of an A/B update store (Chapter 25, Chapter 40): state.json says which slot holds
the known good release and which, if any, holds a release on trial. The updater reads it at
every boot and before every update; if it cannot trust it, it stops and a person looks."""
import json
from collections import namedtuple

State = namedtuple("State", "good good_version trial trial_version")
SLOTS = ("a", "b")


class Damaged(Exception):
    """state.json cannot be trusted; the message says why and asks for a person."""


def open_state(text):
    """The State in state.json's text, or Damaged."""
    try:
        d = json.loads(text)
    except json.JSONDecodeError as e:
        raise Damaged(f"state.json is damaged ({e}): a person must look at the store") from None
    if not isinstance(d, dict):
        raise Damaged("state.json is damaged (not an object): a person must look at the store")
    good = d.get("good")
    if not isinstance(good, str) or good not in SLOTS:
        raise Damaged(f"state.json is damaged (good is {good!r}): a person must look at the store")
    if "trial" not in d:
        raise Damaged("state.json is damaged (no trial): a person must look at the store")
    trial = d["trial"]  # a slot, or null for no trial; nothing else
    if trial is not None and not isinstance(trial, str):
        raise Damaged(f"state.json is damaged (trial is {trial!r}): a person must look at the store")
    if trial is not None and (trial not in SLOTS or trial == good):
        raise Damaged(f"state.json is damaged (trial is {trial!r}): a person must look at the store")
    for key in ("good_version", "trial_version"):  # strings when present
        if key in d and not isinstance(d[key], str):
            raise Damaged(f"state.json is damaged ({key} is {d[key]!r}): a person must look at the store")
    good_version = d.get("good_version", "").strip()
    trial_version = d.get("trial_version", "").strip()
    return State(good, good_version, trial, trial_version)
