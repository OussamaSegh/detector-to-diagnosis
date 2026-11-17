# SPDX-License-Identifier: MIT
"""Exercise 35.4, a solution: DICOM UIDs that are valid, and derived UIDs that cannot collide.

A UID is at most 64 characters of digits and dots, and each component is a number without a
leading zero (DICOM part 5, 9.1). Under the root 2.25 a UID is "2.25." and a UUID written as one
decimal integer (ITU-T X.667).
"""
import re
import uuid

ROOT = "2.25."
NAMESPACE = uuid.UUID("6f1a8f43-3c0e-5b54-9a51-0d4c1b9a2e35")
_SYNTAX = re.compile(r"(0|[1-9][0-9]*)(\.(0|[1-9][0-9]*))*")


def valid(u):
    """True if u is a syntactically valid UID: 1 to 64 characters, components of digits separated by
    single dots, none empty and none with a leading zero."""
    return isinstance(u, str) and 0 < len(u) <= 64 and _SYNTAX.fullmatch(u) is not None


def from_uuid(u):
    """The UID of a UUID under 2.25: its 128 bits as one decimal integer."""
    return ROOT + str(uuid.UUID(str(u)).int)


def _encode(part):
    """One part, written so that no two different lists of parts give the same text: its type,
    its length and its characters. Only str and int, whose text is exact."""
    if isinstance(part, bool) or not isinstance(part, (str, int)):
        raise TypeError(f"a part of a derived UID must be str or int, not {type(part).__name__}")
    kind = "s" if isinstance(part, str) else "i"
    text = str(part)
    return f"{kind}{len(text)}:{text}"


def derived(*parts):
    """A UID that depends only on parts, and on all of them: the same parts give the same UID on any
    machine, different lists of parts give different UIDs (up to the 122 bits of a UUID)."""
    if not parts:
        raise ValueError("a derived UID needs at least one part")
    name = "".join(_encode(p) for p in parts)
    return from_uuid(uuid.uuid5(NAMESPACE, name))
