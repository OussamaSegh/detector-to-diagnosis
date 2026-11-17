# SPDX-License-Identifier: MIT
"""Exercise 35.4: DICOM UIDs that are valid, and derived UIDs that cannot collide.

A UID is at most 64 characters of digits and dots, and each component is a number without a
leading zero (DICOM part 5, 9.1). Under the root 2.25 a UID is "2.25." and a UUID written as one
decimal integer (ITU-T X.667).

This starter runs and gives plausible UIDs. TODO: make the tests pass.
"""
import re
import uuid

ROOT = "2.25."
NAMESPACE = uuid.UUID("6f1a8f43-3c0e-5b54-9a51-0d4c1b9a2e35")


def valid(u):
    """True if u is a syntactically valid UID."""
    return isinstance(u, str) and len(u) <= 64 and re.match(r"[0-9.]+", u) is not None


def from_uuid(u):
    """The UID of a UUID under 2.25."""
    return ROOT + uuid.UUID(str(u)).hex


def derived(*parts):
    """A UID that depends only on parts."""
    return from_uuid(uuid.uuid5(NAMESPACE, ".".join(str(p) for p in parts)))
