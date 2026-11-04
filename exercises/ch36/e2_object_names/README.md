# Exercise 36.2 (M): The name of an object

**Goal.** Compute the names git gives a file, a directory and a commit, and see why a commit's
name stands for the whole history behind it. A release record that names a commit names every
byte of every file of that release, and every commit before it.

**Time.** 2 hours.

**What to write** (`objects.py`), for a repository with SHA-1 object names:
- `blob_id(data)`: the name of a file's content, the SHA-1 of `blob <size>\0` followed by the
  bytes, in hexadecimal.
- `tree_id(entries)`: the name of a directory from `(mode, name, object_id)` entries, mode
  `"100644"` for a file, `"100755"` for an executable and `"40000"` for a directory. The tree's
  content is, for each entry, `<mode> <name>\0` and the 20 bytes of the id (not its hexadecimal
  text), the entries in git's order: by name as bytes, a directory's name compared as if it ended
  with `/`; the header is `tree <size>\0`.
- `commit_id(tree, parents, author, committer, message)`: the name of a commit whose content is
  `tree <id>\n`, a `parent <id>\n` line per parent, `author <author>\n`, `committer <committer>\n`,
  a blank line and the message; `author` and `committer` are `Name <address> <seconds> <zone>`.
  The header is `commit <size>\0`.
- `snapshot(directory)`: the tree id of a directory on disk, recursively (files and executables;
  an empty directory is not stored).

**Starter.** `starter/objects.py` hashes the content without its header, writes a directory's mode
as `040000` and the ids as text, and sorts the entries by name alone.

**Acceptance** (`tests/test_objects.py`), with git as the oracle:
- `blob_id` equals `git hash-object` for an empty file, text and binary data.
- `tree_id` equals `git mktree` for entries given in any order, with a file `a.txt` next to a
  directory `a`, and `snapshot` equals `git write-tree` for a directory with an executable and a
  subdirectory.
- `commit_id` equals `git commit-tree` with fixed dates, for a root commit and a commit with a
  parent; changing one byte of one file changes the commit's name.

**Then, by hand.**
1. A release record names commit `X`. Someone changes a file of that release in the history and
   pushes. What happens to `X`, and to the names of every later commit?
2. What does a commit's name not prove? Who wrote it, when, and whether the tests ran.
3. Git can store a repository with SHA-256 names (`git init --object-format=sha256`). What would
   change in your three functions?
