# MiniDAQ: context for coding agents

Version 1 (MiniDAQ 2.2.0-dev). Status: approved for release 2.2.0, 2026-11-24, given by the author
(software lead) in writing on 2026-11-24 at 08:25 UTC. Owner: software lead.

This file is what a coding agent reads first in this repository. It is a controlled document
(CR-0036): a change to it gets a new version and a history row, `docs.agent_files` checks that
every path, command and test it names exists, and a person reviews it like code. The rules here
repeat the project's plans; where they differ, the plan wins and this file is wrong.

## What the repository is

MiniDAQ, the data acquisition and reconstruction software of a teaching PET scanner, written in
C++23 with Python tools, and the book that teaches it (`book/`). The software is developed as a
class B medical device software under IEC 62304, as the
[software development plan](docs/regulatory/sdp.md) states.

- `minidaq/`: the acquisition library, the server and their tests (`minidaq/tests/`).
- `recon/` and `analysis/`: reconstruction and the analysis package.
- `tools/`: the project's checks, each in the [tool list](docs/regulatory/verification/tools.md).
- `docs/regulatory/`: the SRS, the risk file, the problem reports, the change requests, the
  release records.
- `exercises/`: the book's exercises, each with a starter and a solution.

## Build and test

```sh
cmake --preset debug && cmake --build --preset debug
ctest --test-dir build/debug -L unit -j8
```

A change to a test, a tool or a controlled document is pushed only after the whole
`ctest -L unit` passes on the staged tree, and the CI result of the last push is read before the
next push (SDP section 5, CAPA-0006).

Before a person reviews a change, run the agent gate and give its report with the change:

```sh
python3 tools/agent_gate.py . BASE            # fast checks, seconds
python3 tools/agent_gate.py . BASE --full     # with the build, the unit tests, static analysis
```

A PASS is not a review. The gate reports a change to one of its own checks for a person.

## Rules a change follows

- Every new test of a product item names the requirement it verifies, `// REQ: SRS-XXX-nnn`
  (or `# REQ:` in Python), and `python3 tools/trace_matrix.py . --write` updates the matrix.
  Grep before choosing a new requirement ID: reuse is not checked.
- A change to a requirement, a risk control, a safety class, a SOUP item, an interface or a data
  format needs an approved change request first (`docs/regulatory/changes/`). The software lead
  approves; an agent never records an approval it was not given in writing.
- A change to a class B item's code changes a test in the same commit.
- A whole value is validated with `re.fullmatch` or `std::regex_match`, never `^...$` with
  `match` or `search` (coding standard, rule 3.6).
- C++ is formatted as `.clang-format` writes it; the edit hook does it after each edit.
- No new third-party dependency without the software lead's approval.
- A problem found while working gets a problem report in
  `docs/regulatory/problem-reports.json`, then `python3 tools/anomalies.py . --write`.
- A new file under `docs/` is indexed with `python3 tools/design_file.py . --write`.

## Commits and pushes

- The commit message follows `tools/commit_policy.json`: a subject without "wip", body lines of
  72 characters or fewer, and a trailer block that git parses with `Tests:` and
  `Review: change control checklist, items 1 to 6.`; check it with
  `python3 tools/check_commits.py . HEAD~1..HEAD`.
- An assisted commit names its assistant in a `Co-Authored-By:` trailer
  (`tools/ai_provenance.py`).
- Push only the session's own branch and `main`; never force a push, push tags or rewrite
  published history. Tags are set by a line in `.github/tags.txt`. The command hook refuses the
  rest.

## Privacy

The repository is public. Never commit a personal name other than the book's author line, an
e-mail address other than a no-reply one, a secret, a private key, or an absolute path of the
machine you run on. Use placeholders (`example.invalid`) in examples.

## Agent files

The register of the agent files, with their versions and owners, is `.claude/README.md`. A
subagent reports and does not edit; a skill's steps are commands a person could run.

## Document history

| Version | Change |
|---|---|
| 1 | First version (CR-0036, roadmap 2.2.0, Theme P2). |
