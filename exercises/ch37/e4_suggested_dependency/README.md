# Exercise 37.4 (M): A dependency an assistant suggests

**Goal.** An assistant that writes code also writes `pip install` lines and requirement pins, for
the version it remembers and sometimes for a package that does not exist or that only looks like
the one meant. Check one suggested requirement against the lock file and the SOUP list before it
reaches either: is it pinned, is it approved, does it look like an approved package without being
it, and does the lock file already pin it, at the same version or another.

**Time.** 1 hour.

**Starter.** `starter/suggested.py`, with `check(line, lock_text, approved)`, which returns a list
of findings: `unpinned`, `not-approved`, `near:<approved>`, `already-locked`,
`conflict:<locked version>`. It compares names exactly as written, never looks for look-alikes,
takes `>=` as a pin and reads any line.

**Acceptance** (`tests/test_suggested.py`, run by `ctest --test-dir build/debug -R ch37/e4`), with
a lock file shaped like `analysis/requirements.lock`:
- `numpy==2.5.3` is already locked; so are `pygments==2.21.0`, `Mypy-Extensions==1.2.0` and
  `python_dateutil==2.9.0.post0`, whose names the lock file writes differently.
- `pydicom==3.0.1` conflicts with the locked 2.4.4; `pybind11==3.1.0` is approved and not locked.
- `scipy>=1.18`, a bare name and `==3.*` are not pins.
- `nunpy`, `nmupy`, `num-py`, `py-dicom`, `pydicom2`, `dicom`, `scapy`, `mathplotlib` and
  `dateutil` are not approved and each is near the approved package it resembles.
- `requests` and `pandas` are not approved and near nothing.
- An empty line, a missing name or version, a space for `==`, a marker with a shell command and a
  URL are refused with `ValueError`.

**Then, by hand.**
1. Run your check on every pin of `analysis/requirements.lock`, with the other pins as the approved
   list. Which legitimate packages look like each other, and what should a reviewer do with such a
   finding?
2. `scapy` is a real, well-known package, not a typosquat. Is flagging it near `scipy` a false
   positive?
3. Your check cannot tell whether a package exists, or what its latest version and advisories are.
   Which tool of the repository asks the index, and why must its failure to run not count as a pass?

**Hints.** PEP 503: `re.sub(r"[-_.]+", "-", name).lower()`. An edit distance that counts a swap of
two neighbors as one edit (Damerau). Also compare names with separators and a leading `py` or
`python` removed.
