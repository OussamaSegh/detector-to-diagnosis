# Exercise 12.5 (M): After the crash, in Python

**Goal.** Write the tool an operator runs after a DAQ PC lost power or the acquisition
was killed: it puts a directory of list-mode files back into a state every reader
accepts, keeps every record that reached the disk intact, and refuses to touch a
directory that a crash alone cannot explain. This is the other half of the sink's
crash-safety argument: the `.part` name says a file is incomplete, and somebody has to
act on it. Pure Python, no numpy.

**Time.** 2.5 hours.

**Starter.** `starter/recover.py` groups the files by run, checks the segment
numbers and partial files, and repairs the last segment by renaming it. It works on
the easy cases and is wrong in three places: which blocks it trusts, what it does to
the bytes after the last of them, and one way in which a run can be incomplete that it
does not notice.

**Acceptance** (`tests/test_recover.py`, which writes its own MDQ-L1 files in a
temporary directory):
- A clean run is left exactly as it was, and reported as clean.
- A `.part` file that ends in half a block is cut after its last intact block, closed
  with an end-of-run block and renamed; reading it gives exactly the records of its
  intact blocks, and a second `recover` changes nothing.
- A last block whose length is right and whose contents are not (zeros where the
  records were, as a power loss can leave it) is not trusted.
- A `.part` that was closed but not yet renamed is renamed, not closed twice; a `.part`
  whose header never made it to the disk holds no records and is removed.
- A run with a missing segment, with two partial files, or with a complete file that
  is damaged is reported, and nothing in it is changed.
- `dry_run=True` reports what it would do and changes nothing.

On the starter, five tests pass and four fail.

**Then, by hand.**
1. Run `writer_throughput --dir DIR --forever 1 --max-file-mb 16 --fsync interval
   --every 16` (Chapter 12's benchmark), kill it with `kill -9` after a second, run
   `python3 solution/recover.py DIR`, and check the result with `minidaq_listmode
   verify`. What did the last file look like before, and after?
2. `recover` truncates a file, which destroys bytes. Which bytes, and why is that safe?
   Name a situation in which it would not be, and say what the tool should do then.
   Answer in `NOTES.md`.

**Hints.** A block is trusted only when both its CRCs are right and its sequence
number is the next one. Truncate first, then append. Segments are numbered from
0000, and a hole in the numbers is a lost file, not a crash.
