# Exercise 25.2 (M): Which version is newer

**Goal.** Decide whether an update is newer than what is installed, exactly as Semantic Versioning
2.0.0 (semver.org, section 11) defines precedence. MiniDAQ's updater refuses an older version unless
a person asks for it, so the comparison is a safety function: get it wrong and a release candidate
is refused as a downgrade, or an old version with a known bug installs as an upgrade.

**Time.** 45 minutes.

**Starter.** `starter/semver.hpp` and `.cpp`.

**Tasks.** `parse` and `compare`, as the header's comments say.

**Acceptance** (`ch25/e2_semver/<variant>/...`): the parts of a full version, sixteen versions the
specification does not allow, the example chain of its section 11, numbers that string comparison
gets wrong, and build metadata.

**Then** answer in `NOTES.md`: MiniDAQ's own `update::Version` compares pre-release labels as
strings (`minidaq/include/minidaq/update/bundle.hpp`). Find a pair of versions it orders wrongly,
say why that is acceptable for MiniDAQ today, and what rule in the release process keeps it so.
