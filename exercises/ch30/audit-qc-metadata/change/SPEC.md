# Task given to the agent

Implement `read_metadata(meta)` in `qc_metadata.py`, for the daily QC report. `meta` is the
parsed JSON of a run's metadata.

- `scanner` is an object, and `scanner.crystals` a positive integer; both are required.
- `records` is an object, and may be missing; `records.delayed_window_ps` is a positive
  integer, and when it is missing the report uses `DEFAULT_DELAYED_WINDOW_PS`.
- "Integer" means a JSON integer. A string of digits, a boolean or a fraction is not one.
- Anything else, of any type, is `FormatError` with a message that names the field. The tool
  catches `FormatError` and prints `error: ...` with status 2; any other exception reaches the
  technologist as a traceback.

Add tests.
