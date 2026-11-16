# Exercise 40.1 (E): The kind of release a change needs

**Goal.** Decide whether a change may ship in a patch release, needs a minor release or needs a
major one, by the rules of MiniDAQ's maintenance plan (section 4), and give the next version.

**Time.** 1 hour.

**What to write** (`release.py`):
- `kind(change)`: `change` is a dict of booleans, a missing key meaning False: `breaks_clients`,
  `new_requirement`, `changes_format`, `changes_api`, `new_soup`, `new_feature`,
  `fixes_report`, `soup_update`, `documentation`. Return `"patch"`, `"minor"` or `"major"`: a
  change that breaks an existing client, configuration or file is major; one that adds a
  requirement, a field, a command, a SOUP item or a feature is minor; a fix, a SOUP update in the
  same version line or a documentation correction is a patch, if nothing else in it needs more.
  A change that does none of these raises ValueError.
- `combined(changes)`: the kind of one release that carries all of them.
- `next_version(current, kind)`: the version after a released `X.Y.Z`. A version that is not
  released (`2.0.0-dev`) or an unknown kind raises ValueError.

**Starter.** `starter/release.py` calls every fix a patch, whatever else it changes, looks only at
the first change of a release, and does not reset the lower numbers of a version.

**Acceptance** (`tests/test_release.py`): the rules above, a release of three changes, the
versions after 1.3.0 and 1.3.2, and the refusals.

**Then, by hand.**
1. MiniDAQ 2.0.0 renamed fields of the control API (CR-0030). A site on 1.3 reports a problem
   relevant to safety. Which release carries its fix to that site, and why not 2.0.1?
2. A fix needs one new field in the run record, which every reader ignores if it does not know
   it. Patch or minor, and what does the answer cost a site that wants only the fix?
3. Why does the maintenance plan forbid a new SOUP item in a patch release, even a small one?
