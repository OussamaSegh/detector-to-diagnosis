# Exercise 25.4: notes on the solution

**Two directions.** Checking every listed file only proves that the listed files are right. The tree
must also hold nothing else, so the solution walks the tree and compares it with the list: what is
listed and absent is missing, what is present and not listed is unlisted. A hidden file counts like
any other; `recursive_directory_iterator` returns it.

**Never follow a link.** `symlink_status` describes the link itself, and the iterator does not enter
linked directories by default. A link named like a listed program would otherwise be hashed through,
and if it pointed at a copy of the right file elsewhere, would pass. Directories are allowed; every
other type (link, FIFO, socket, device) is reported, listed or not.

**Paths are checked before they are used.** A listed `../outside` would make `root / path` name a
file outside the slot, and the check would then vouch for it. Every component must be a plain name;
`.` and empty components are refused too, so each file has one spelling and duplicates are found.
MiniDAQ's `verify_tree` and the `contained` check of the archive's member names in
`minidaq/src/update/slots.cpp` apply the same rule.

**The format is exact.** `sha256sum` writes two spaces between the digest and the path in text mode,
and a space and an asterisk in binary mode. Accepting only the form the release tool writes keeps
one way to say each thing. Lowercase only, for the same reason.

**What this catches that the archive's digest does not.** The archive's digest is checked before
unpacking, so it proves the bytes that were signed arrived. It does not prove that `tar` wrote what
the release tool meant: an archive built from a staging directory with a stray file or a link, a
member name that `tar` resolved differently, a file changed in the slot after unpacking by another
process or a failing disk, or an earlier partial extraction left in a reused slot. The manifest
check compares the result with the list the release tool computed from the stage.

**What neither catches.** A release whose signed contents are themselves wrong: a bug, a malicious
change that passed review, a compromised build machine, or a stolen signing key. Those are for the
release process (review, reproducible builds compared with the SBOM, a key held in an HSM), not for
the acquisition PC.
