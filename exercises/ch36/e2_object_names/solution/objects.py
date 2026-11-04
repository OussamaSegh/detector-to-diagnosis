# SPDX-License-Identifier: MIT
"""Exercise 36.2: the names of git's objects, SHA-1 format (solution)."""
import hashlib
import os
import pathlib


def object_id(kind, body):
    """The name of an object: the SHA-1 of its type, its size, a zero byte and its content."""
    return hashlib.sha1(b"%s %d\0" % (kind, len(body)) + body).hexdigest()


def blob_id(data):
    return object_id(b"blob", bytes(data))


def tree_id(entries):
    def order(entry):
        mode, name, _ = entry
        key = name.encode()
        return key + b"/" if mode == "40000" else key

    body = b"".join(b"%s %s\0" % (mode.encode(), name.encode()) + bytes.fromhex(oid)
                    for mode, name, oid in sorted(entries, key=order))
    return object_id(b"tree", body)


def commit_id(tree, parents, author, committer, message):
    head = f"tree {tree}\n" + "".join(f"parent {p}\n" for p in parents)
    head += f"author {author}\ncommitter {committer}\n\n"
    return object_id(b"commit", (head + message).encode())


def snapshot(directory):
    """The tree id of a directory, or None for one with no file anywhere below it."""
    entries = []
    for p in pathlib.Path(directory).iterdir():
        if p.is_dir():
            sub = snapshot(p)
            if sub is not None:
                entries.append(("40000", p.name, sub))
        elif p.is_file():
            mode = "100755" if os.access(p, os.X_OK) else "100644"
            entries.append((mode, p.name, blob_id(p.read_bytes())))
    return tree_id(entries) if entries else None
