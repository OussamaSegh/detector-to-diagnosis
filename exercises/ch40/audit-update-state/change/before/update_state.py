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
    raise NotImplementedError("the fields")
