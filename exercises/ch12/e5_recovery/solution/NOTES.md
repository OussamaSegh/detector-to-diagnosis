# Exercise 12.5: notes on the solution

**The three mistakes.**

- *Trusting a block by its header.* The starter checked the block header's CRC and
  the length, not the payload CRC. After a power loss the file system can keep a
  file's new length and not the data written into it (the contents read as zeros, or
  as the old contents of the sector): the header of the block was written, the records
  were not. Kept, those zeros would decode as coincidences at crystal 0 with energy 0.
  Only both CRCs make a block trustworthy.
- *Closing after the torn tail.* The starter appended the closing block to the end of
  the file. The half block in front of it stays, and a reader meets garbage before the
  end of run: `minidaq_listmode verify` reports it, and a simple reader that stops at
  the first bad block (the one in Exercise 12.2) never sees the closing block. Cut at
  the end of the last intact block, then append.
- *A hole in the segment numbers.* Segments 0000, 0002 and 0003 are not a crash: the
  sink renames a segment before it creates the next one, so 0001 was deleted, moved or
  never copied. A tool that "recovers" such a run makes a file set that looks complete
  and is not. It must stop and say so, as it does for two partial files and for a
  damaged complete file.

**A real crash** (Then, by hand, 1). Seven trials on this machine (the VM of the
Chapter 12 measurements), killed after 0.1 to 1.3 s. In six, the last segment was a
`.part` that `recover` closed with an end-of-run block and renamed, keeping every record
(for example 393,216 in segment 0047 of a 48-segment run of 49,483,776 records);
`minidaq_listmode verify` then reported the file as ok. In the seventh, the kill came
between the closing block of a segment and its rename, and `recover` only renamed it.
In these seven the `.part` happened to end at a block boundary, but a kill can also
leave half a block: Linux lets a fatal signal end a large write(2) part of the way
through, and 7 of the 20 trials of `measurements/ch12/crash.txt` ended in a truncated
block. A block whose length is on the disk and whose contents are not (the case of the
third test) needs a power loss or a kernel crash, which a kill cannot produce (verify:
with a fault injector such as dm-log-writes, as `measurements/ch12/crash.py` notes).

**Which bytes truncation destroys** (Then, by hand, 2). Only bytes after the last block
whose two CRCs are right and whose sequence number is the expected one: bytes that no
reader would return as records. It is safe because the sink wrote blocks strictly in
order and only ever at the end of the last `.part` file, so nothing intact can come
after a damaged block in that file. It would not be safe if that assumption broke:
a file that is damaged in the middle (a bad sector, not a crash), or a format version
that writes out of order. Then a resynchronizing reader (`listmode::Reader`) could
still find intact blocks after the damage, and truncation would throw them away. The
tool should stop, as it does for a damaged complete file: report, change nothing, and
leave the decision, and perhaps a copy of the file, to a person. In a regulated
product, "the tool changed a raw data file" is also something the run's records must
show: print the report into the run's log, not only on a terminal.
