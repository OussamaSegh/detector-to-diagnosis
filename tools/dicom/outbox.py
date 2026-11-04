# SPDX-License-Identifier: MIT
"""A store-and-forward queue for the export (Chapter 35): no image leaves the queue before the
archive has said it stored it.

    OUTBOX/pending/<series UID>/<instance UID>.dcm   written by enqueue, waiting to be sent
    OUTBOX/sent/<series UID>/...                     the archive answered success (or a warning)
    OUTBOX/failed/<series UID>/...                   the archive refused it for good: a person
                                                     must look (the journal says why)
    OUTBOX/journal.jsonl                             one line per attempt, append only

send() moves an instance to sent/ only after a success or warning status for it, keeps it in
pending/ after a transient failure (out of resources, a network error, a timeout), and moves it to
failed/ after any other failure status. A series that is sent again, whole or in part, carries
the same UIDs (tools/dicom/uid.py derives them from the content), so the archive replaces what it
already has instead of storing a second copy.
"""
import json
import pathlib
import shutil
import time

from . import encode, net, pet


def _dirs(outbox):
    root = pathlib.Path(outbox)
    return {k: root / k for k in ("pending", "sent", "failed")}, root / "journal.jsonl"


def enqueue(outbox, datasets):
    """Checks a series (pet.check_series) and writes it to pending/; returns the paths."""
    dirs, _ = _dirs(outbox)
    series_uid = datasets[0].get("SeriesInstanceUID") if datasets else "empty"
    return pet.write_series(datasets, dirs["pending"] / series_uid)


def _journal(path, **entry):
    entry["time"] = round(time.time(), 3)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")


def _move(path, dirs, where):
    target = dirs[where] / path.parent.name / path.name
    target.parent.mkdir(parents=True, exist_ok=True)
    path.replace(target)
    if not any(path.parent.iterdir()):
        path.parent.rmdir()


def counts(outbox):
    """{"pending": n, "sent": n, "failed": n} of instances."""
    dirs, _ = _dirs(outbox)
    return {k: len(list(d.glob("*/*.dcm"))) if d.exists() else 0 for k, d in dirs.items()}


# [snippet:send]
def send(outbox, host, port, calling, called, timeout=10.0, max_pdu=net.DEFAULT_MAX_PDU):
    """Sends every pending instance, one association per series. Returns a report: the counts
    after the attempt and the errors that stopped a series."""
    dirs, journal = _dirs(outbox)
    errors = []
    for series_dir in sorted(dirs["pending"].glob("*")) if dirs["pending"].exists() else []:
        files = sorted(series_dir.glob("*.dcm"))
        try:
            with net.associate(host, port, calling, called, timeout=timeout,
                               max_pdu=max_pdu) as assoc:
                for path in files:
                    try:
                        _, ds = encode.read_file_bytes(path.read_bytes())
                    except encode.DicomError as e:
                        _journal(journal, sop=path.stem, series=series_dir.name, action="failed",
                                 error=f"unreadable: {e}")
                        _move(path, dirs, "failed")
                        continue
                    status = assoc.store(ds)
                    kind = net.status_class(status)
                    if kind != "failure":
                        action = "sent"
                    elif net.transient(status):
                        action = "pending"
                    else:
                        action = "failed"
                    _journal(journal, sop=path.stem, series=series_dir.name,
                             status=f"0x{status:04X}", status_class=kind, action=action)
                    if action != "pending":
                        _move(path, dirs, action)
        except net.AssociationError as e:
            errors.append(f"series {series_dir.name}: {e}")
            _journal(journal, series=series_dir.name, action="pending", error=str(e))
    return {**counts(outbox), "errors": errors}
# [/snippet:send]


def retry_failed(outbox, series_uid):
    """Puts the failed instances of one series back in pending/, after a person has fixed the
    cause; journaled."""
    dirs, journal = _dirs(outbox)
    src = dirs["failed"] / series_uid
    if not src.exists():
        return 0
    dst = dirs["pending"] / series_uid
    dst.mkdir(parents=True, exist_ok=True)
    n = 0
    for path in sorted(src.glob("*.dcm")):
        path.replace(dst / path.name)
        n += 1
    shutil.rmtree(src, ignore_errors=True)
    _journal(journal, series=series_uid, action="retry", instances=n)
    return n
