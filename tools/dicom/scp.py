# SPDX-License-Identifier: MIT
"""A small storage service class provider (SCP) for tests (Chapter 35): it accepts associations,
answers C-ECHO, and stores every C-STORE as a DICOM file named after its SOP Instance UID, so a
second send of the same instance replaces the first.

    with StorageSCP(directory, ae="ARCHIVE") as scp:      # listens on 127.0.0.1, a free port
        ... associate("127.0.0.1", scp.port, "MINIDAQ", "ARCHIVE") ...

Faults, to show what the sender does when the archive misbehaves:
  reject=(result, source, reason)  answer every A-ASSOCIATE-RQ with an A-ASSOCIATE-RJ;
  statuses={n: status}             answer the n-th C-STORE (counted from 1) with that status
                                   and do not store it unless the status is a success or warning;
  abort_after=n                    after n C-STOREs, abort the association at the next one;
  stall_after=n                    after n C-STOREs, never answer the next one;
  max_pdu=n                        the maximum PDU length it accepts (0: no limit).

It is a test double, not an archive: it checks the called AE title and the protocol, and keeps
what it receives; it does not check the IODs.
"""
import pathlib
import socket
import struct
import threading

from . import encode, net, uid

ABSTRACTS = {uid.PET_IMAGE_STORAGE, uid.VERIFICATION}


class StorageSCP:
    def __init__(self, directory, ae="ARCHIVE", reject=None, statuses=None, abort_after=None,
                 stall_after=None, max_pdu=net.DEFAULT_MAX_PDU,
                 syntaxes=(encode.EXPLICIT_LE, encode.IMPLICIT_LE), host="127.0.0.1", port=0):
        self.directory = pathlib.Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.ae, self.reject, self.statuses = ae, reject, dict(statuses or {})
        self.abort_after, self.stall_after, self.max_pdu = abort_after, stall_after, max_pdu
        self.syntaxes = list(syntaxes)
        self.received, self.associations, self.errors = [], 0, []
        self.stores = 0
        self._lock = threading.Lock()
        self._listener = socket.create_server((host, port))
        self.port = self._listener.getsockname()[1]
        self._stop = threading.Event()
        self._threads = []

    def __enter__(self):
        t = threading.Thread(target=self._serve, daemon=True)
        t.start()
        self._threads.append(t)
        return self

    def __exit__(self, *_):
        self._stop.set()
        self._listener.close()
        for t in self._threads:
            t.join(timeout=5)

    def files(self):
        return sorted(self.directory.glob("*.dcm"))

    def _serve(self):
        self._listener.settimeout(0.2)
        while not self._stop.is_set():
            try:
                conn, _ = self._listener.accept()
            except (socket.timeout, OSError):
                continue
            t = threading.Thread(target=self._association, args=(conn,), daemon=True)
            t.start()
            self._threads.append(t)

    def _association(self, conn):
        conn.settimeout(10)
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        try:
            with conn:
                self._handle(conn)
        except (net.AssociationError, encode.DicomError, OSError) as e:
            with self._lock:
                self.errors.append(str(e))

    def _handle(self, conn):
        kind, body = net.read_pdu(conn, net.LIMIT_ASSOCIATE)
        if kind != net.ASSOCIATE_RQ:
            return
        with self._lock:
            self.associations += 1
        called, calling, proposed, peer_max = net.parse_associate(body)
        if self.reject:
            conn.sendall(net._pdu(net.ASSOCIATE_RJ, struct.pack(">BBBB", 0, *self.reject)))
            return
        if called != self.ae:   # reason 7: called AE title not recognized
            conn.sendall(net._pdu(net.ASSOCIATE_RJ, struct.pack(">BBBB", 0, 1, 1, 7)))
            return
        accepted, answer = {}, b""
        for cid, (abstract, syntaxes) in sorted(proposed.items()):
            chosen = next((s for s in self.syntaxes if s in syntaxes), None)
            result = 3 if abstract not in ABSTRACTS else (4 if chosen is None else 0)
            if result == 0:
                accepted[cid] = (abstract, chosen)
            sub = net._item(0x40, (chosen or encode.EXPLICIT_LE).encode())
            answer += net._item(0x21, struct.pack(">BBBB", cid, 0, result, 0) + sub)
        fixed = body[:68]
        user = net._item(0x51, struct.pack(">I", self.max_pdu))
        user += net._item(0x52, uid.IMPLEMENTATION_CLASS.encode())
        conn.sendall(net._pdu(net.ASSOCIATE_AC, fixed + net._item(0x10, uid.APPLICATION_CONTEXT
                                                                  .encode()) + answer
                              + net._item(0x50, user)))
        peer = net.Association(conn, accepted, peer_max, self.max_pdu, 10)
        while True:
            kind, body = self._next(conn)
            if kind == net.RELEASE_RQ:
                conn.sendall(net._pdu(net.RELEASE_RP, b"\0" * 4))
                return
            if kind == net.ABORT:
                return
            cmd, data = self._message(peer, kind, body)
            cid = peer.last_context
            field, mid = cmd.get("CommandField"), cmd.get("MessageID")
            if field == net.C_ECHO_RQ:
                peer._send(cid, net.command(AffectedSOPClassUID=uid.VERIFICATION,
                                            CommandField=net.C_ECHO_RSP,
                                            MessageIDBeingRespondedTo=mid,
                                            CommandDataSetType=net.NO_DATASET, Status=0), True)
                continue
            if field != net.C_STORE_RQ:
                peer.abort()
                return
            with self._lock:
                self.stores += 1
                n = self.stores
            if self.abort_after is not None and n > self.abort_after:
                peer.abort()
                return
            if self.stall_after is not None and n > self.stall_after:
                self._stop.wait(30)
                return
            status = self.statuses.get(n, 0x0000)
            sop = cmd.get("AffectedSOPInstanceUID")
            if net.status_class(status) != "failure":
                abstract, syntax = accepted[cid]
                ds = encode.decode_dataset(data, explicit=(syntax == encode.EXPLICIT_LE))
                path = self.directory / f"{sop}.dcm"
                tmp = path.with_suffix(".tmp")
                tmp.write_bytes(encode.file_bytes(ds, uid.IMPLEMENTATION_CLASS, "MINIDAQ_SCP"))
                tmp.replace(path)
            with self._lock:
                self.received.append((sop, status))
            peer._send(cid, net.command(AffectedSOPClassUID=cmd.get("AffectedSOPClassUID"),
                                        CommandField=net.C_STORE_RSP,
                                        MessageIDBeingRespondedTo=mid,
                                        CommandDataSetType=net.NO_DATASET, Status=status,
                                        AffectedSOPInstanceUID=sop), True)

    def _next(self, conn):
        return net.read_pdu(conn, self.max_pdu + 6 if self.max_pdu else 2**31)

    def _message(self, peer, kind, body):
        """(command, data set bytes or None) of the message whose first PDU is (kind, body)."""
        if kind != net.P_DATA:
            raise net.AssociationError(f"unexpected PDU type {kind}")
        return peer._receive_message(first=(kind, body))
