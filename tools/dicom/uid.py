# SPDX-License-Identifier: MIT
"""Unique identifiers (UIDs) for DICOM (Chapter 35).

A UID is at most 64 characters of digits and dots; each component is a number without a leading
zero (part 5). An organization normally registers a root and numbers below it. The root 2.25 lets
anyone make a UID from a UUID instead: "2.25." followed by the UUID as one decimal integer
(ITU-T X.667), at most 44 characters.

Random UIDs (uuid4) are right for anything that happens once. For the objects of an export,
MiniDAQ derives the UIDs from their content instead (uuid5 of a name): exporting the same image
again gives the same series and instance UIDs, so an archive that receives a series twice, after
a send that failed halfway, stores one series and not two. A different image, or the same image
with different metadata, gives different UIDs.
"""
import re
import uuid

ROOT = "2.25."
NAMESPACE = uuid.UUID("6f1a8f43-3c0e-5b54-9a51-0d4c1b9a2e35")  # MiniDAQ's own, fixed forever
SYNTAX = re.compile(r"^(0|[1-9][0-9]*)(\.(0|[1-9][0-9]*))*$")

# Well-known UIDs of the standard (part 6).
PET_IMAGE_STORAGE = "1.2.840.10008.5.1.4.1.1.128"
VERIFICATION = "1.2.840.10008.1.1"
APPLICATION_CONTEXT = "1.2.840.10008.3.1.1.1"


def valid(u):
    """True if u is a syntactically valid UID."""
    return isinstance(u, str) and 0 < len(u) <= 64 and bool(SYNTAX.match(u))


def random_uid():
    """A new UID from a random UUID."""
    return ROOT + str(uuid.uuid4().int)


# [snippet:derived]
def derived(*parts):
    """A UID that depends only on parts: the same parts give the same UID on any machine, and
    different parts give different UIDs (a name-based UUID, SHA-1 inside, under 2.25)."""
    name = "\x1f".join(str(p) for p in parts)  # a separator no part contains
    return ROOT + str(uuid.uuid5(NAMESPACE, name).int)
# [/snippet:derived]


IMPLEMENTATION_CLASS = derived("MiniDAQ implementation class", 1)
