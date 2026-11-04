# Exercise 34.2 (M): Who owns this file?

**Goal.** Check a map of software items against the files of a repository: give every file its
owner by the rule "the longest matching path prefix wins", and report what the map gets wrong.
An item map is the bridge between the safety classification (a document) and the code (the
files); a new engineer who trusts a wrong map reviews the wrong change at the wrong rigor.

**Time.** 2 hours.

**The input.** `items` is a list of `{"id": ..., "paths": [prefix, ...]}`; a prefix is a
directory ending in `/` or the start of a file name (`src/processing/coincidence_sorter` claims
`.hpp` and `.cpp`). `files` is the list of tracked files to check.

**What to compute.**
- `owner(path, items)`: the id of the item whose matching prefix is the longest, or `None`.
  Two items whose longest matching prefixes have the same length make the owner ambiguous:
  raise `ValueError` naming both.
- `check_map(files, items)` returns a dict with:
  - `unowned`: the files no prefix matches, sorted;
  - `ambiguous`: the files with an ambiguous owner, sorted;
  - `shadowed`: `(file, owner, other)` for every file that another item's shorter prefix also
    matches, sorted: legal under the rule, but a reader of the other item's directory will
    think the file is theirs;
  - `dead`: `(item, prefix)` for every prefix that matches no file, in the map's order;
  - `owned`: `{item: number of files}`, with 0 for an item that owns nothing.

**Starter.** `starter/item_map.py` gives each file the first item that matches, so the answer
depends on the order of the map; it reports unowned files and nothing else.

**Acceptance** (`tests/test_item_map.py`):
- The owner is the same whatever the order of the items and of their prefixes.
- An ambiguous owner raises `ValueError` from `owner` and is listed by `check_map`, which never
  raises.
- Shadowed files, dead prefixes and the count of every item, including items that own nothing.
- A prefix that is a file stem does not claim a file whose name merely starts with it in another
  directory (`src/a/x` claims `src/a/x.cpp` and `src/a/x_test.cpp`, not `src/ab/x.cpp`).

**Then, by hand.**
1. Run `tools/survey.py .` on MiniDAQ. Which files are shadowed, and which prefixes were dead
   before CR-0021? Would you move the shadowed files, or leave the map as it is? Why?
2. Why must `check_map` never raise, when `owner` does?
3. A file that no item claims is a failure in `tools/check_items.py`. Why is a dead prefix only a
   report?
