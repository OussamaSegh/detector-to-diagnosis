# Agent files

Version 2 (MiniDAQ 2.3.0-dev). Status: approved for release 2.3.0, 2026-11-26, given by the
coordinator under the software lead's standing delegation, in writing on 2026-11-26 at 07:33 UTC.
Version 1 was approved for release 2.2.0, 2026-11-24, given by the author (software lead) in
writing on 2026-11-24 at 08:25 UTC. Owner: software lead.

The register of the files that a coding agent reads or obeys in this repository (CR-0036,
roadmap 2.2.0, Theme P2). Each is versioned and owned like a controlled document, and
`tools/check_agent_files.py` (test `docs.agent_files`, TL-52) checks each against this table and
the least-privilege policy `tools/agent_files_policy.json`. The settings have no place for a
version of their own, so their version is the one in this table; a change to any agent file
raises its version here.

| File | Kind | Version | Owner |
|---|---|---|---|
| `CLAUDE.md` | context | 1 | software lead |
| `.claude/settings.json` | settings | 1 | software lead |
| `.claude/agents/trace-review.md` | agent | 2 | software lead |
| `.claude/skills/release-checks/SKILL.md` | skill | 2 | software lead |

## Principles

These apply to any coding agent, not only to the one whose file formats are used here.

- **Least privilege.** A subagent that reviews has read-only tools. A skill may run only the
  commands its steps name. The settings allow the build, the tests and the project's tools, ask
  before a push, and deny secrets, forced pushes, network downloads and installs.
- **Commands a person could run.** Every step of a skill is a command in the repository; nothing
  is hidden in the agent's own judgment that a person could not repeat.
- **Hooks refuse only what the rules forbid,** and name the rule
  (`tools/hooks/agent_command.py`, `tools/hooks/agent_edit.py`).
- **Checked like code.** A path, a command or a test that a file names must exist; a file that
  changes gets a new version; a person reviews it.
- **Formats change.** The check reads only the fields it needs. A change of the agent's file
  format is a change request, not a silent edit.

A machine's own writable directories, outside the repository and the temporary directories, go
in its uncommitted `.claude/settings.local.json`, as the variable `MINIDAQ_AGENT_WRITABLE`.

## Document history

| Version | Change |
|---|---|
| 1 | First version (CR-0036). |
| 2 | The release-checks skill is at version 2, and may run `tools/evidence_paths.py` (CAPA-0008). |
