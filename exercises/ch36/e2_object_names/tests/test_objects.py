# SPDX-License-Identifier: MIT
"""Acceptance tests of Exercise 36.2, with git itself as the oracle."""
import os
import pathlib
import subprocess
import tempfile
import unittest

from objects import blob_id, commit_id, snapshot, tree_id

ENV = dict(os.environ, GIT_AUTHOR_NAME="A U Thor", GIT_AUTHOR_EMAIL="author@example.org",
           GIT_COMMITTER_NAME="C O Mitter", GIT_COMMITTER_EMAIL="committer@example.org",
           GIT_AUTHOR_DATE="1700000000 +0100", GIT_COMMITTER_DATE="1700000060 +0000",
           GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
AUTHOR = "A U Thor <author@example.org> 1700000000 +0100"
COMMITTER = "C O Mitter <committer@example.org> 1700000060 +0000"


class Repo:
    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        self.git("init", "-q", "--object-format=sha1")

    def git(self, *args, data=None):
        return subprocess.run(["git", "-C", str(self.root), *args], input=data, env=ENV,
                              capture_output=True, check=True).stdout.decode().strip()

    def blob(self, data):
        path = self.root / "blob.tmp"
        path.write_bytes(data)
        try:
            return self.git("hash-object", "-w", str(path))
        finally:
            path.unlink()


class Objects(unittest.TestCase):
    def setUp(self):
        self.repo = Repo()

    def tearDown(self):
        self.repo.tmp.cleanup()

    def test_blob(self):
        for data in (b"", b"MiniDAQ 0.9\n", bytes(range(256)) * 3):
            self.assertEqual(blob_id(data), self.repo.blob(data))

    def test_tree_in_any_order_with_a_file_next_to_a_directory(self):
        a = self.repo.blob(b"a\n")
        sub = self.repo.git("mktree", data=f"100644 blob {a}\tx.cpp\n".encode())
        entries = [("100644", "a.txt", a), ("40000", "a", sub), ("100755", "run.sh", a),
                   ("100644", "a-b", a), ("100644", "B", a)]
        text = "".join(f"{m} {'tree' if m == '40000' else 'blob'} {o}\t{n}\n"
                       for m, n, o in entries)
        expected = self.repo.git("mktree", data=text.encode())
        self.assertEqual(tree_id(entries), expected)
        self.assertEqual(tree_id(list(reversed(entries))), expected)

    def test_snapshot_equals_write_tree(self):
        work = self.repo.root
        (work / "src" / "net").mkdir(parents=True)
        (work / "src" / "net" / "udp.cpp").write_text("int udp;\n")
        (work / "src.txt").write_text("a file next to src\n")
        (work / "build.sh").write_text("#!/bin/sh\n")
        os.chmod(work / "build.sh", 0o755)
        (work / "empty").mkdir()
        self.repo.git("add", "-A")
        expected = self.repo.git("write-tree")
        # snapshot sees the working tree; leave out what git keeps in .git
        tree = self.snapshot_without_git(work)
        self.assertEqual(tree, expected)

    def snapshot_without_git(self, work):
        with tempfile.TemporaryDirectory() as d:
            for p in work.rglob("*"):
                rel = p.relative_to(work)
                if rel.parts[0] == ".git":
                    continue
                target = pathlib.Path(d) / rel
                if p.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(p.read_bytes())
                    os.chmod(target, p.stat().st_mode)
            return snapshot(d)

    def test_commit_and_one_byte(self):
        a = self.repo.blob(b"one\n")
        tree = self.repo.git("mktree", data=f"100644 blob {a}\tVERSION\n".encode())
        message = "First\n\nBody.\n\nReview: ok\n"
        root = self.repo.git("commit-tree", tree, data=message.encode())
        self.assertEqual(commit_id(tree, [], AUTHOR, COMMITTER, message), root)
        second = self.repo.git("commit-tree", tree, "-p", root, data=b"Second\n")
        self.assertEqual(commit_id(tree, [root], AUTHOR, COMMITTER, "Second\n"), second)
        b = blob_id(b"onf\n")
        changed = commit_id(tree_id([("100644", "VERSION", b)]), [], AUTHOR, COMMITTER, message)
        self.assertNotEqual(changed, root)
        later = commit_id(tree, [changed], AUTHOR, COMMITTER, "Second\n")
        self.assertNotEqual(later, second)


if __name__ == "__main__":
    unittest.main()
