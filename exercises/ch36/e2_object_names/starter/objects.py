# SPDX-License-Identifier: MIT
"""Exercise 36.2: the names of git's objects (starter)."""
import hashlib
import os
import pathlib


def blob_id(data):
    return hashlib.sha1(data).hexdigest()


def tree_id(entries):
    body = b""
    for mode, name, oid in sorted(entries, key=lambda e: e[1]):
        mode = "040000" if mode == "40000" else mode
        body += f"{mode} {name}\0{oid}".encode()
    return hashlib.sha1(b"tree %d\0" % len(body) + body).hexdigest()


def commit_id(tree, parents, author, committer, message):
    lines = [f"tree {tree}"] + [f"parent {p}" for p in parents]
    lines += [f"author {author}", f"committer {committer}", "", message]
    body = "\n".join(lines).encode()
    return hashlib.sha1(b"commit %d\0" % len(body) + body).hexdigest()


def snapshot(directory):
    entries = []
    for p in sorted(pathlib.Path(directory).iterdir()):
        if p.is_dir():
            entries.append(("40000", p.name, snapshot(p)))
        else:
            mode = "100755" if os.access(p, os.X_OK) else "100644"
            entries.append((mode, p.name, blob_id(p.read_bytes())))
    return tree_id(entries)
