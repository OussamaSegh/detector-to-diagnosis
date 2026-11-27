# Audit report: the agent's change to the settings reader (Exercise 7.6)

Not mergeable: the reader can still throw, and it reads a file whose version is empty as if
it were a supported one. Both defects are MiniDAQ's own, from the real configuration reader.

## Defect 1: a number outside the range of double ends the program (MDQ-PR-001)

`std::stod` throws `std::invalid_argument` for text that is not a number and
`std::out_of_range` for a number that does not fit in a `double`, such as `6e688`, `1e400` or
`1e-400`. The agent catches only the first. The second escapes `read_settings`, which the
specification says never throws.

- *Test:* `Audit.ANumberOutsideTheRangeOfDoubleIsAnErrorNotACrash`.
- *Effect:* the exception ends the configure step of the server: a lost scan at the scanner,
  from one character in a file. No wrong value is accepted, so the hazard is availability.
- *Correction:* catch `std::logic_error` (both exceptions derive from it), or parse with
  `std::from_chars`, which reports `errc::result_out_of_range` instead of throwing.
- *How it was found in MiniDAQ:* `fuzz_config`, in this chapter. The agent's own tests tried
  zero and text, never the edges of the type.

## Defect 2: an empty schema_version is read as a supported one (MDQ-PR-042)

The version check skips an empty version, on the agent's claim that the line parser already
reports it. It does not: `schema_version =` is a valid line whose value is empty. A missing
key is refused; an empty value passes, and the file is read as the current format.

- *Test:* `Audit.EveryVersionButTheTwoSupportedOnesIsRefused` (the empty string).
- *Effect:* a file that does not say what it is gets read as 2.2, which SRS-CFG-002 forbids:
  a file of another format could be taken with its fields misread.
- *Correction:* check every version that is present, the empty one included.

## Verdict

Request changes. The claims in the transcript ("the only call that can throw is inside a
`try`", "already reported by the line parser") are both checkable in a minute, and both are
false: check an agent's statement about its own code the way you check the code.
