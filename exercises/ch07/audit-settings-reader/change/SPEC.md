# Task given to the agent

In `settings.hpp`, the reader of the acquisition settings file:

1. Add `coincidence_window_ns`, a decimal number of nanoseconds in (0, 100], default 4. It
   may be written as `4`, `4.5` or `4e0`.
2. Accept files of schema 2.1 as well as 2.2. A 2.1 file has no `coincidence_window_ns` and
   gets the default.
3. Keep the reader's contract: whatever the file holds, `read_settings` returns settings or
   an error that names its reason. It never throws and never crashes, because the file comes
   from outside the program. A file without a `schema_version`, or with one that is not 2.1
   or 2.2, is refused (SRS-CFG-002: a file is never read as a format it does not say it is).

Add tests.
