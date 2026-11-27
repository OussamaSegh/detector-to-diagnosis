# The session, condensed

This session is reconstructed for the book. The change was written to hold defects that
MiniDAQ really had, and the dialogue is shortened to the steps that matter. It works from this
record alone: you do not need an agent to do the exercise.

**Person:** Implement `change/SPEC.md` in `qc_metadata.py`.

**Agent:** I'll read the two fields with `int(...)`, which normalizes whatever JSON gives us
into an integer, and turn a missing key into `FormatError`. A missing `records` falls back to
an empty dict, so the default window applies.

*(edits `qc_metadata.py`: the diff is `change/agent.patch`)*

**Agent:** Tests:

```text
test_reads_complete_metadata ............... ok
test_default_window ........................ ok
test_missing_scanner_is_format_error ....... ok
test_missing_crystals_is_format_error ...... ok
test_zero_crystals_is_format_error ......... ok
Ran 5 tests in 0.001s  OK
```

Every path that can fail raises `FormatError`, so the tool always ends with a clean message.

**Person:** I'll review it.
