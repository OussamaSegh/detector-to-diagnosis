# CR-0018: The build as an interface: installed packages, presets, a wheel, formatting

| Field | Value |
|---|---|
| Status | implemented |
| Requested | 2026-11-04, by the software lead |
| Source | improvement: other projects need the projector library and module without MiniDAQ's tree; developers need CI's configurations as one command; the code's formatting has never been checked (ADR 0027) |
| Decision | approved, 2026-11-04, software lead |
| Commits | 83f2e4c, c72ed58, db7314d, e6ac69a and the commit that adds the chapter |

## Description

The projector library `recon::projector` installs as a CMake package (export set, configuration
file with `find_dependency(Threads)`, version file, component `recon_dev`), with include
directories per context and the warnings target in the build interface only. Every configuration
preset has build, test and workflow presets of its name, and compilers come from toolchain files.
The projector's Python module builds as a wheel with scikit-build-core from the main CMake project.
`.clang-format` (Google's style at 100 columns) is checked on changed lines by
`tools/check_format.py`, in a pre-commit hook (which also refuses whitespace errors and e-mail
addresses that are not placeholders) and in a new CI job `format`; the gate self-test gains the
fault `format`. Exercises 32.1 to 32.3 and the helper `minidaq_cmake_exercise`. The move to
toolchain files left the compiler out of a fresh build tree's cache, which the release bundle and
the system test report read (MDQ-PR-049): both fall back to the build tree's record.

## Reason

A library used by copying its sources or its build tree's paths drifts and breaks with the
machine; a configuration run by hand differs from CI's; two build systems for one module drift;
inconsistent formatting makes diffs noisy and reviews slower (ADR 0027).

## Impact analysis

### Requirements

New: SRS-BLD-001 to SRS-BLD-005 (SRS version 21), all verified by test. No requirement changed.

### Software items and safety class

None of the product's programs or libraries change their code. The build of the shipped programs
changes in one way: the compiler is set by a toolchain file instead of a cache variable, which
selects the same compiler; the reproducibility check gives an identical product archive from two
checkouts of the commit that fixes MDQ-PR-049, and the hardening check passes.

### Risk

No hazard changes. The installed package and the wheel serve tools (TL-31, TL-38); a wrong wheel
is H-13's cause through a new path, controlled by `recon.wheel`, which runs the projector's tests
against the installed module.

### SOUP

scikit-build-core 1.1.2 was already in the lock file (CR-0017); it is now used and listed as tool
TL-38. clang-format 18.1.3 is a new tool, TL-37 (Ubuntu's package, version checked by
`tools/check_tools.py --environment`). No product dependency changes; FetchContent pins stay, and
no package manager is introduced (Conan was not approved).

### Interfaces and data formats

New: the installed CMake package `recon` (targets `recon::projector`, version compatibility
`SameMinorVersion`), and the wheel `minidaq-recon` with the module `recon_cpp`. Both are interfaces
for tool users.

### Documents

ADR 0027 (new) and the ADR index; the SRS, version 21; the trace matrix; the coding standard,
version 5 (rule 1.4); the development plan, version 11 (section 6); the tool list (TL-37, TL-38);
the architecture description, version 18; the threat model, version 6 (reviewed: no element added;
the gap "The build runs the repository's code"); the problem reports MDQ-PR-048, MDQ-PR-049 and
MDQ-PR-050 (ADR 0027's options as a list);
CAPA-0001; the CHANGELOG.

### Regulatory

The intended use of MiniDAQ does not change.

## Verification

The tests cmake.consumer, recon.wheel, docs.presets, tools.check_presets, tools.check_format and
tools.pre_commit, among them Presets.test_a_configuration_without_a_workflow_is_found,
CheckFormat.test_untouched_lines_of_an_unformatted_file_are_not_checked,
CheckFormat.test_a_badly_formatted_staged_line_is_found and
PreCommit.test_an_address_is_refused_and_a_placeholder_is_not; the CI jobs format and python; the gate self-test's fault `format`, caught for
its reason; the reproducibility check (identical archives); Exercises 32.1 to 32.3, whose starters
fail and whose solutions pass with GCC and Clang; the measurements in `measurements/ch32/`.

## Decision

Approved on 2026-11-04 by the software lead: build changes with tests, no change to the product's
code, no new product dependency.
