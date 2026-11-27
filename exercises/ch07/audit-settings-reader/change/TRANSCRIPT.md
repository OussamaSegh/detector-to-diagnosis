# The session, condensed

This session is reconstructed for the book. The change was written to hold defects that
MiniDAQ really had, and the dialogue is shortened to the steps that matter. It works from this
record alone: you do not need an agent to do the exercise.

**Person:** Implement `change/SPEC.md` in `settings.hpp`.

**Agent:** The reader parses `run_seconds` with `std::from_chars`. `from_chars` for `double`
is not available on every standard library this project might meet, so I'll use `std::stod`,
which also accepts the exponent form the specification asks for. I'll check that the whole
value was used, so that `4ns` is refused, and catch the exception `stod` throws for text that
is not a number, so that the reader still never throws.

For the version, I'll accept 2.1 and 2.2. A `schema_version =` line with nothing after it is
already reported by the line parser, so the version check only needs to look at a version
that is there.

*(edits `settings.hpp`: the diff is `change/agent.patch`)*

**Agent:** Tests added and passing:

```text
[ RUN      ] Settings.ReadsTheWindow                         [       OK ]
[ RUN      ] Settings.RefusesAWindowOfZero                   [       OK ]
[ RUN      ] Settings.RefusesTextAsAWindow                   [       OK ]
[ RUN      ] Settings.ReadsA21FileWithTheDefaultWindow       [       OK ]
[ RUN      ] Settings.RefusesVersion30                       [       OK ]
[  PASSED  ] 5 tests.
```

The reader still never throws: the only call that can throw, `std::stod`, is inside a
`try` block.

**Person:** I'll review it.
