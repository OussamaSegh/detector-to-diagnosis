# Exercise 36.2: notes

The starter fails three of the four tests; its `commit_id` is right, and only shows it with a
tree that git made. Each mistake gives a name that looks like any other: a hexadecimal string of
40 characters. Only another implementation tells them apart, which is why the tests ask git.

Design choices:

- One function, `object_id`, for the header: every object's name is the hash of its type, its
  size and its content, so a blob and a tree with the same bytes have different names.
- Sorting with `name + "/"` for a directory: `a.txt` comes before the directory `a` (`.` is 0x2e,
  `/` is 0x2f), and `a-b` before both. A plain sort by name puts `a` first and gives a different
  tree for the same files.
- The id in a tree is 20 bytes, not 40 characters of text; the mode of a directory is `40000`,
  without the leading zero that `git ls-tree` prints.
- An empty directory gives `None`: git stores files, and a directory exists only as the path of a
  file. A build that needs an empty directory makes it, or the repository keeps a placeholder file.
- To the questions: a changed file in the history changes its blob, its tree, every tree above
  it, its commit and every commit after it. `X` is still the name of the old commit; the new
  history has new names, and the release record no longer names anything in it, which is how a
  rewrite is detected. A name proves which content, not who wrote it, when, or that anything was
  checked: that is the work of signatures, the review record and CI. With SHA-256 the hash and
  the id's length change (32 bytes in a tree, 64 hexadecimal characters); the layout does not.
