# Audit report: the agent's open_state (Exercise 40.5)

Not mergeable. A version of another type stops the updater with a Python error, and a trial of
another type is silently forgotten. Both are MiniDAQ's own defects, in `minidaq_update`'s slot
store, found by the internal audit before release 2.0.0 (MDQ-PR-074).

## Defect 1: a version of another type ends the updater with another error (MDQ-PR-074)

`.get("good_version", "")` returns the default only when the key is absent. When it is there
with a number, a list or null, `.strip()` raises AttributeError.

- *Test:* `test_a_version_of_another_type_is_damaged_not_a_crash`.
- *At the scanner:* the updater stops with "'int' object has no attribute 'strip'" instead of
  "state.json is damaged: a person must look at the store". The field engineer gets a
  programmer's message with no action in it. In MiniDAQ's C++ it was nlohmann's
  "type must be string, but is number".
- *Correction:* check that each version present is a string, and raise `Damaged` otherwise.

## Defect 2: a trial of another type is taken as no trial (MDQ-PR-074)

"Anything else means no trial" turns `"trial": 7` into `None`. A store with a release on
trial, whose state a person or a disk changed, is then trusted as a store with none: the
updater may boot the trial slot's release as if it were not on trial, or overwrite it, with
no one asked.

- *Test:* `test_a_trial_of_another_type_is_damaged_not_forgotten`.
- *Correction:* the trial is a slot or null; anything else is `Damaged`. Leniency with a file
  the updater cannot understand is the opposite of what the specification asks: the safe
  answer is to stop and ask a person.

## Verdict

Request changes. "Every malformed file I tried" was six files, none with a field of the wrong
type: a reader of a state file needs every JSON type in every field, as Chapter 7's fuzzing and
CAPA-0005's rule ask.
