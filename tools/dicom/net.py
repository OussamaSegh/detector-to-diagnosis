# SPDX-License-Identifier: MIT
"""DICOM network storage as a service class user (Chapter 35): the upper layer protocol of part 8
over TCP, and the C-ECHO and C-STORE services of part 7.

    with associate("pacs.example.org", 11112, "MINIDAQ", "ARCHIVE") as a:
        a.echo()                                   # 0x0000 if the archive answers
        status = a.store(ds)                       # the archive's status for this instance

An association starts with A-ASSOCIATE-RQ, which proposes presentation contexts (an abstract
syntax, the SOP class, with the transfer syntaxes the sender can use); the acceptor answers with
A-ASSOCIATE-AC, naming per context whether it is accepted and in which transfer syntax, and its
maximum PDU length, or with A-ASSOCIATE-RJ. DIMSE messages then travel in P-DATA-TF PDUs: a
command set, always in Implicit VR Little Endian, and the data set in the accepted syntax, each
cut into fragments that fit the peer's maximum. A-RELEASE-RQ and -RP end it; A-ABORT ends it at
once. Every PDU header is big-endian; the data inside is little-endian.

Every read has a time limit, a PDU longer than this side accepts is an abort, and a status is
reported as the archive gave it: only the archive's success status says an instance is stored.
"""
import socket
import struct

from . import dictionary, encode, uid
from .encode import Dataset, DicomError

ASSOCIATE_RQ, ASSOCIATE_AC, ASSOCIATE_RJ, P_DATA, RELEASE_RQ, RELEASE_RP, ABORT = range(1, 8)
DEFAULT_MAX_PDU = 16384
LIMIT_ASSOCIATE = 65536        # the longest association PDU this side reads
C_STORE_RQ, C_STORE_RSP, C_ECHO_RQ, C_ECHO_RSP = 0x0001, 0x8001, 0x0030, 0x8030
NO_DATASET = 0x0101
CONTEXT_RESULTS = {0: "accepted", 1: "rejected by the user", 2: "rejected, no reason",
                   3: "abstract syntax not supported", 4: "transfer syntaxes not supported"}


class AssociationError(DicomError):
    """The association could not be made, or ended without a release."""


# [snippet:status]
def status_class(status):
    """'success', 'warning' or 'failure', as part 7 groups the status codes of C-STORE. Only
    success means the archive stored the instance as sent; a warning means it stored it but
    changed or did not check something (0xB000 coercion of data elements, 0xB006 elements
    discarded, 0xB007 data set does not match the SOP class)."""
    if status == 0x0000:
        return "success"
    if status in (0x0001, 0x0107, 0x0116) or 0xB000 <= status <= 0xBFFF:
        return "warning"
    return "failure"


def transient(status):
    """True for a failure worth retrying later: 0xA7xx, the archive is out of resources."""
    return 0xA700 <= status <= 0xA7FF
# [/snippet:status]


def _ae(title):
    b = title.encode("ascii")
    if not 0 < len(b) <= 16 or b"\\" in b or not title.strip():
        raise DicomError(f"AE title {title!r} must be 1 to 16 characters, not all spaces")
    return b.ljust(16, b" ")


def _item(kind, body):
    return struct.pack(">BBH", kind, 0, len(body)) + body


def _pdu(kind, body):
    return struct.pack(">BBI", kind, 0, len(body)) + body


def associate_rq(calling, called, contexts, max_pdu=DEFAULT_MAX_PDU,
                 implementation=uid.IMPLEMENTATION_CLASS, version="MINIDAQ"):
    """The bytes of an A-ASSOCIATE-RQ. contexts: [(id, abstract syntax, [transfer syntaxes])],
    ids odd, 1 to 255."""
    body = struct.pack(">HH", 1, 0) + _ae(called) + _ae(calling) + b"\0" * 32
    body += _item(0x10, uid.APPLICATION_CONTEXT.encode())
    for cid, abstract, syntaxes in contexts:
        if not (cid % 2 and 1 <= cid <= 255):
            raise DicomError(f"presentation context id {cid} must be odd, 1 to 255")
        sub = _item(0x30, abstract.encode()) + b"".join(_item(0x40, s.encode()) for s in syntaxes)
        body += _item(0x20, struct.pack(">BBBB", cid, 0, 0, 0) + sub)
    user = _item(0x51, struct.pack(">I", max_pdu)) + _item(0x52, implementation.encode())
    user += _item(0x55, version.encode())
    body += _item(0x50, user)
    return _pdu(ASSOCIATE_RQ, body)


def items(buf, pos=0, end=None):
    """[(type, bytes)] of the variable items of an association PDU."""
    end = len(buf) if end is None else end
    out = []
    while pos < end:
        if pos + 4 > end:
            raise AssociationError("truncated item in an association PDU")
        kind, _, length = struct.unpack_from(">BBH", buf, pos)
        if pos + 4 + length > end:
            raise AssociationError("an item longer than its PDU")
        out.append((kind, bytes(buf[pos + 4:pos + 4 + length])))
        pos += 4 + length
    return out


def parse_associate(body):
    """(called, calling, contexts, max_pdu) of the body of an A-ASSOCIATE-RQ or -AC. For an RQ,
    contexts is {id: (abstract, [syntaxes])}; for an AC, {id: (result, syntax)}."""
    if len(body) < 68:
        raise AssociationError("association PDU shorter than its fixed fields")
    called = body[4:20].decode("ascii", "replace").strip()
    calling = body[20:36].decode("ascii", "replace").strip()
    contexts, max_pdu = {}, 0
    for kind, value in items(body, 68):
        if kind == 0x20 and len(value) >= 4:      # proposed (RQ)
            subs = items(value, 4)
            abstract = [v.decode().rstrip("\0") for k, v in subs if k == 0x30]
            syntaxes = [v.decode().rstrip("\0") for k, v in subs if k == 0x40]
            contexts[value[0]] = (abstract[0] if abstract else "", syntaxes)
        elif kind == 0x21 and len(value) >= 4:    # answered (AC)
            syntaxes = [v.decode().rstrip("\0") for k, v in items(value, 4) if k == 0x40]
            contexts[value[0]] = (value[2], syntaxes[0] if syntaxes else "")
        elif kind == 0x50:
            for k, v in items(value):
                if k == 0x51 and len(v) == 4:
                    max_pdu = struct.unpack(">I", v)[0]
    return called, calling, contexts, max_pdu


def read_pdu(sock, limit):
    """(type, body) of the next PDU; AssociationError on a closed connection, a timeout or a PDU
    longer than limit bytes."""
    head = _read_exactly(sock, 6)
    kind, _, length = struct.unpack(">BBI", head)
    if length > limit:
        raise AssociationError(f"a PDU of {length} bytes, more than the {limit} accepted")
    return kind, _read_exactly(sock, length)


def _read_exactly(sock, n):
    out = bytearray()
    while len(out) < n:
        try:
            chunk = sock.recv(n - len(out))
        except socket.timeout:
            raise AssociationError("no answer from the peer within the time limit") from None
        except OSError as e:
            raise AssociationError(f"connection failed: {e}") from None
        if not chunk:
            raise AssociationError("the peer closed the connection")
        out += chunk
    return bytes(out)


def command(**elements):
    """The bytes of a DIMSE command set: Implicit VR Little Endian, led by its group length."""
    ds = Dataset()
    for keyword, value in elements.items():
        ds.set(keyword, value)
    body = encode.encode_dataset(ds, explicit=False)
    return encode.encode_element(0x00000000, "UL", len(body), explicit=False) + body


# [snippet:fragments]
def pdata(context_id, payload, is_command, max_pdu):
    """The P-DATA-TF PDUs that carry one command or data set: fragments of at most max_pdu - 6
    bytes (the PDV item's own length field and its two header bytes take the rest), the last one
    flagged. A max_pdu of 0 means the peer set no limit."""
    room = (max_pdu - 6) if max_pdu else max(len(payload), 1)
    if room < 2:
        raise DicomError(f"maximum PDU length {max_pdu} leaves no room for data")
    out, pos = [], 0
    while True:
        piece = payload[pos:pos + room]
        pos += len(piece)
        last = pos >= len(payload)
        control = (1 if is_command else 0) | (2 if last else 0)
        pdv = struct.pack(">IBB", len(piece) + 2, context_id, control) + piece
        out.append(_pdu(P_DATA, pdv))
        if last:
            return out
# [/snippet:fragments]


class Association:
    """An established association, as requester. Use associate() to make one."""

    def __init__(self, sock, accepted, peer_max_pdu, max_pdu, timeout):
        self.sock, self.accepted, self.peer_max_pdu = sock, accepted, peer_max_pdu
        self.max_pdu, self.timeout, self._message_id, self.open = max_pdu, timeout, 0, True
        self.last_context = None

    def __enter__(self):
        return self

    def __exit__(self, kind, *_):
        if self.open and kind is None:
            self.release()
        else:
            self.abort()      # also closes the socket of an association the peer ended

    def _context(self, abstract):
        for cid, (syntax_abstract, syntax) in self.accepted.items():
            if syntax_abstract == abstract:
                return cid, syntax
        raise DicomError(f"no accepted presentation context for {abstract}")

    def _send(self, cid, payload, is_command):
        for pdu in pdata(cid, payload, is_command, self.peer_max_pdu):
            self.sock.sendall(pdu)

    def _receive_message(self, first=None):
        """(command data set, data set bytes or None) of the next DIMSE message; first is its
        first PDU when the caller has already read it. The context id of the message is kept in
        last_context."""
        parts = {True: bytearray(), False: bytearray()}
        done = {True: False, False: False}
        cmd = None
        while True:
            if first is not None:
                (kind, body), first = first, None
            else:
                kind, body = read_pdu(self.sock, self.max_pdu + 6 if self.max_pdu else 2**31)
            if kind == ABORT:
                self.open = False
                raise AssociationError("the peer aborted the association")
            if kind != P_DATA:
                self.abort()
                raise AssociationError(f"unexpected PDU type {kind} during a message")
            pos = 0
            while pos < len(body):
                if pos + 6 > len(body):
                    raise AssociationError("truncated PDV item")
                length, _, control = struct.unpack_from(">IBB", body, pos)
                if length < 2 or pos + 4 + length > len(body):
                    raise AssociationError("a PDV item longer than its PDU")
                is_command = bool(control & 1)
                self.last_context = body[pos + 4]
                parts[is_command] += body[pos + 6:pos + 4 + length]
                done[is_command] = done[is_command] or bool(control & 2)
                pos += 4 + length
            if done[True] and cmd is None:
                cmd = encode.decode_dataset(bytes(parts[True]), explicit=False)
                if cmd.get("CommandDataSetType") == NO_DATASET:
                    return cmd, None
            if cmd is not None and done[False]:
                return cmd, bytes(parts[False])

    def _next_id(self):
        self._message_id = self._message_id % 65535 + 1
        return self._message_id

    def echo(self):
        """The status of a C-ECHO (verification): 0x0000 when the peer answers."""
        cid, _ = self._context(uid.VERIFICATION)
        mid = self._next_id()
        self._send(cid, command(AffectedSOPClassUID=uid.VERIFICATION, CommandField=C_ECHO_RQ,
                                MessageID=mid, CommandDataSetType=NO_DATASET), True)
        rsp, _ = self._receive_message()
        self._check_response(rsp, C_ECHO_RSP, mid)
        return rsp.get("Status")

    # [snippet:store]
    def store(self, ds):
        """Sends one instance with C-STORE and returns the archive's status for it."""
        sop_class, sop_instance = ds.get("SOPClassUID"), ds.get("SOPInstanceUID")
        cid, syntax = self._context(sop_class)
        data = encode.encode_dataset(ds, explicit=(syntax == encode.EXPLICIT_LE))
        mid = self._next_id()
        self._send(cid, command(AffectedSOPClassUID=sop_class, CommandField=C_STORE_RQ,
                                MessageID=mid, Priority=0, CommandDataSetType=0x0000,
                                AffectedSOPInstanceUID=sop_instance), True)
        self._send(cid, data, False)
        rsp, _ = self._receive_message()
        self._check_response(rsp, C_STORE_RSP, mid)
        if rsp.get("AffectedSOPInstanceUID") not in (None, sop_instance):
            raise AssociationError("the response names another instance")
        return rsp.get("Status")
    # [/snippet:store]

    def _check_response(self, rsp, field, mid):
        if rsp.get("CommandField") != field or rsp.get("MessageIDBeingRespondedTo") != mid:
            self.abort()
            raise AssociationError(f"expected the response to message {mid}, got command "
                                   f"{rsp.get('CommandField')} to {rsp.get('MessageIDBeingRespondedTo')}")
        if rsp.get("Status") is None:
            raise AssociationError("a response without a status")

    def release(self):
        """Ends the association in order: A-RELEASE-RQ, then the peer's A-RELEASE-RP."""
        if not self.open:
            return
        self.open = False
        try:
            self.sock.sendall(_pdu(RELEASE_RQ, b"\0" * 4))
            kind, _ = read_pdu(self.sock, 64)
            if kind != RELEASE_RP:
                raise AssociationError(f"expected A-RELEASE-RP, got PDU type {kind}")
        finally:
            self.sock.close()

    def abort(self):
        """Ends the association at once (A-ABORT, source: service user)."""
        if self.open:
            self.open = False
            try:
                self.sock.sendall(_pdu(ABORT, struct.pack(">BBBB", 0, 0, 0, 0)))
            except OSError:
                pass
        self.sock.close()


# [snippet:associate]
def associate(host, port, calling, called, abstracts=(uid.PET_IMAGE_STORAGE, uid.VERIFICATION),
              timeout=10.0, max_pdu=DEFAULT_MAX_PDU, nodelay=True):
    """An association with the archive at host:port; AssociationError if it is rejected, aborted
    or not answered within timeout seconds, or if no proposed context is accepted. nodelay sets
    TCP_NODELAY: without it, the last small PDU of a message waits for the acknowledgment of the
    previous one, which the peer delays (measurements/ch35: about 40 ms per instance)."""
    contexts = [(2 * i + 1, a, [encode.EXPLICIT_LE, encode.IMPLICIT_LE])
                for i, a in enumerate(abstracts)]
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
    except OSError as e:
        raise AssociationError(f"cannot connect to {host}:{port}: {e}") from None
    sock.settimeout(timeout)
    if nodelay:
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    try:
        sock.sendall(associate_rq(calling, called, contexts, max_pdu))
        kind, body = read_pdu(sock, LIMIT_ASSOCIATE)
        if kind == ASSOCIATE_RJ:
            result, source, reason = body[1], body[2], body[3]
            raise AssociationError(f"association rejected ({'permanent' if result == 1 else 'transient'}"
                                   f", source {source}, reason {reason})")
        if kind == ABORT:
            raise AssociationError("association aborted by the peer")
        if kind != ASSOCIATE_AC:
            raise AssociationError(f"expected A-ASSOCIATE-AC, got PDU type {kind}")
        _, _, answered, peer_max = parse_associate(body)
        proposed = {cid: a for cid, a, _ in contexts}
        accepted = {cid: (proposed[cid], syntax) for cid, (result, syntax) in answered.items()
                    if result == 0 and cid in proposed}
        if not accepted:
            reasons = {proposed.get(c, c): CONTEXT_RESULTS.get(r, r) for c, (r, _) in answered.items()}
            raise AssociationError(f"no presentation context accepted: {reasons}")
    except BaseException:
        sock.close()
        raise
    return Association(sock, accepted, peer_max, max_pdu, timeout)
# [/snippet:associate]


def describe(status):
    """'0xA700 (failure)'."""
    return f"0x{status:04X} ({status_class(status)})"


__all__ = ["associate", "Association", "AssociationError", "status_class", "transient",
           "describe", "dictionary"]
