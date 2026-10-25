# Exercise 20.1 (E): A manifest that notices

**Goal.** Write the manifest of a release package and its check: one SHA-256 per file, in a
format `sha256sum -c` reads, and a verification that reports every file that changed, went
missing or was added, not only the first. A package whose check stops at the first difference
hides the others from the reviewer.

**Time.** 45 minutes.

**Starter.** `starter/manifest.py` with three functions to complete.

**Tasks.**
1. `write_manifest(top)`: writes `top/MANIFEST.sha256` with a line `<sha256>  <path>` for every
   regular file below `top` except the manifest itself, paths relative to `top` with `/`, sorted,
   so that the same files give the same manifest. Returns the list of paths.
2. `read_manifest(path)`: the mapping path to digest. Refuse a malformed line, a path that
   leaves the package (`../`, an absolute path) and a path listed twice.
3. `verify(top)`: a `Report` with the sorted lists `changed`, `missing` and `added`, and `ok`
   true only if all three are empty. A symbolic link in the package is reported as added: a
   release package holds files, and a link can point anywhere.

**Acceptance** (`ch20/e1_manifest/<variant>/unittest`): `sha256sum -c` accepts the manifest;
the same files in another order of creation give the same bytes; each kind of damage is found,
several at once are all found; malformed and escaping manifests are refused.

Then answer in `NOTES.md`: what does a manifest inside the package protect against, and what
does it not protect against? What would you add so that a damaged manifest is noticed too?
