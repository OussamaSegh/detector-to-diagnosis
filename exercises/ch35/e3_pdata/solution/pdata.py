# SPDX-License-Identifier: MIT
"""Exercise 35.3: DIMSE messages out of P-DATA-TF fragments."""
import struct

P_DATA = 4


def command_has_dataset(command):
    """False if the command (Implicit VR Little Endian) has (0000,0800) = 0x0101."""
    pos = 0
    while pos + 8 <= len(command):
        group, element, length = struct.unpack_from("<HHI", command, pos)
        if (group, element) == (0x0000, 0x0800):
            return struct.unpack_from("<H", command, pos + 8)[0] != 0x0101
        pos += 8 + length
    return True


def pdvs(body):
    """(context id, is command, is last, fragment) of every PDV item of a PDU body."""
    pos = 0
    while pos < len(body):
        if pos + 6 > len(body):
            raise ValueError(f"a PDV header cut at byte {pos}")
        length, cid, control = struct.unpack_from(">IBB", body, pos)
        if length < 2 or pos + 4 + length > len(body):
            raise ValueError(f"a PDV of length {length} at byte {pos} does not fit its PDU")
        yield cid, bool(control & 1), bool(control & 2), body[pos + 6:pos + 4 + length]
        pos += 4 + length


def messages(pdus):
    """(context id, command, data set or None) of every complete message."""
    cid = None
    command, dataset = bytearray(), bytearray()
    command_done = False
    for kind, body in pdus:
        if kind != P_DATA:
            raise ValueError(f"PDU type {kind} in the middle of the data transfer")
        for pcid, is_command, last, fragment in pdvs(body):
            if cid is None:
                cid = pcid
            elif pcid != cid:
                raise ValueError(f"a fragment on context {pcid} inside a message on {cid}")
            if is_command:
                if command_done:
                    raise ValueError("a command fragment after the command was complete")
                command += fragment
                command_done = last
                if last and not command_has_dataset(bytes(command)):
                    yield cid, bytes(command), None
                    cid, command, command_done = None, bytearray(), False
            else:
                if not command_done:
                    raise ValueError("a data set fragment before the command was complete")
                dataset += fragment
                if last:
                    yield cid, bytes(command), bytes(dataset)
                    cid, command, dataset, command_done = None, bytearray(), bytearray(), False
    if cid is not None:
        raise ValueError("the input ended in the middle of a message")
