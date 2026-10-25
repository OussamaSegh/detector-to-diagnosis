# Exercise 20.1: notes on the solution

**Design.** One pass collects the regular files and, separately, everything else that is not a
directory; links go straight to `added`, so a package cannot smuggle a pointer to a file outside
itself past the check. Paths are POSIX and sorted, so the manifest of the same files has the same
bytes whatever the order in which they were written, and `sha256sum -c` reads it. The manifest
is parsed strictly: a line that is not `<64 hex digits><two spaces><path>`, an absolute path, a
`..` part or a duplicate is an error, not a skipped line, because a verifier that skips what it
cannot read reports success on a manifest it did not check.

**What the manifest protects against.** Damage in transit or storage, a partial copy, a file
added or replaced by mistake: every one shows as a named difference, and all of them at once.

**What it does not protect against.** Someone who changes a file can change its line in the
manifest too; the archive then verifies against itself. To notice that, the digest of the whole
package (or of the manifest) must be kept somewhere the package does not control: MiniDAQ writes
the product archive's SHA-256 into its evidence archive and into the release record, which is
committed and tagged, so a changed product no longer matches the number in the record. A
signature over the manifest with a key the release process holds (assumption: confirm with team
how your company signs releases) does the same without a second document.
