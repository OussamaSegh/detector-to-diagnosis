# Exercise 25.4 (M): Check an unpacked tree against its manifest

**Goal.** Before a new version may run, check that its slot holds exactly what was signed: every
listed file with its digest, and nothing else. The signature covers the manifest; this check carries
that trust to every file, and refuses the ways an archive can smuggle something in: an extra file, a
symbolic link to a system file, a path that climbs out of the slot.

**Time.** 60 minutes.

**Starter.** `starter/verify_tree.hpp` and `.cpp`; `sha256.cpp` is given.

**Tasks.** `verify`, as the header's comment says.

**Acceptance** (`ch25/e4_verify_tree/<variant>/...`): an intact tree, files changed, missing and
added (hidden ones too), links and a FIFO, listed paths that leave the tree or repeat, lines that
are not digest lines, and a missing manifest.

**Then** answer in `NOTES.md`: `tar` was told not to restore owners and permissions, and the archive
was checked against a signed digest before it was unpacked. Which attacks does this check still
catch that those two do not, and which ones does neither catch?
