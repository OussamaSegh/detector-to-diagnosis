# Task given to the agent

Finish `open_state(text)` in `update_state.py`: read the fields of state.json.

- `good` (required): the slot of the known good release, `"a"` or `"b"`.
- `trial` (required): the slot of the release on trial, `"a"` or `"b"` but not `good`; or
  `null` when no release is on trial.
- `good_version`, `trial_version` (optional): strings, the versions in those slots; an absent
  one is `""`.

A state.json that breaks any of these, in any way, is `Damaged`, whose message asks a person
to look at the store. state.json is written by the updater, but a person may edit it by hand
and a disk may damage it: the updater must never trust a store it cannot read, and must never
stop with any other error than `Damaged`.

Add tests.
