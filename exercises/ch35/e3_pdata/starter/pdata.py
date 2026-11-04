# SPDX-License-Identifier: MIT
"""Exercise 35.3: DIMSE messages out of P-DATA-TF fragments."""
import struct


def command_has_dataset(command):
    """False if the command (Implicit VR Little Endian) has (0000,0800) = 0x0101."""
    pos = 0
    while pos + 8 <= len(command):
        group, element, length = struct.unpack_from("<HHI", command, pos)
        if (group, element) == (0x0000, 0x0800):
            return struct.unpack_from("<H", command, pos + 8)[0] != 0x0101
        pos += 8 + length
    return True


def messages(pdus):
    command = None
    for kind, body in pdus:
        length, cid, control = struct.unpack_from(">IBB", body, 0)
        fragment = body[6:4 + length]
        if control & 1:
            command = fragment
            if not command_has_dataset(command):
                yield cid, command, None
        else:
            yield cid, command, fragment
