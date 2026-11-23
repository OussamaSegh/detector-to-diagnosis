# CR-0036: The agent gate and the agent files under the quality system

| Field | Value |
|---|---|
| Status | proposed |
| Requested | 2026-11-23, by the software lead |
| Source | improvement; roadmap 2.2.0, themes P1 and P2 |
| Decision | pending |
| Commits | none yet |

## Description

Two things are added, both tools: neither the programs nor their interfaces change.

1. **The agent gate** (`tools/agent_gate.py`, TL-51), already added as a tool in 6fe8a40: one
   verdict for a change before a person reviews it, with the reason for each failure, shown to
   reject each change of its known-bad library. This change request gives it requirements.
2. **The agent files**, kept under the quality system:
   - the repository's context file `CLAUDE.md` and the agent's settings `.claude/settings.json`
     (permissions and hooks), each a controlled document with a version, an owner and a
     history;
   - a review subagent for IEC 62304 traceability (`.claude/agents/trace-review.md`), with
     read-only tools, and its eval (`tools/agent_evals/trace-review/`);
   - a release-check skill (`.claude/skills/release-checks/SKILL.md`), whose every step is a
     command a person could run;
   - two hooks (`tools/hooks/agent_command.py` before each command, `tools/hooks/agent_edit.py`
     after each edit), each with a unit test;
   - `tools/check_agent_files.py` (TL-52), run in CI on every agent file;
   - an optional `Gate:` trailer that names the gate's report, which the provenance report and
     the commit policy read (commit policy 3).

## Reason

An agent writes code quickly and says it is done; the project's checks are what turn that into
evidence, and today an agent's instructions, permissions and helpers live outside the quality
system, where a stale path or a wide permission is not reviewed. The roadmap of 2.2.0 makes both
the gate and the agent files the groundwork of the Third Edition's Part XI. Without this change,
the files would be added without requirements, tests or a document history, and the gate's
verdict would not be traced.

## Impact analysis

### Requirements

Six requirements are added to the SRS's AI group, item `tools`, all verified by test. They take
the group's next numbers, 005 to 010, in this order, when the SRS draft is written:

- **AI 005**: The agent gate shall run each of its checks, in the version of the gate that
  judges, on the change between a base commit and a checked-out commit or the working tree, and
  give the verdict FAIL with each failing check's reasons when a check fails, PASS otherwise, and
  report a check whose tool is not installed as skipped.
- **AI 006**: The agent gate shall report as a failure, for a person to review, every change
  that edits the gate or a check the gate runs.
- **AI 007**: The agent file checker shall report every agent file that lacks a field its
  kind requires, that names a repository path, a command or a test that does not exist, that
  allows a tool outside its kind's least-privilege list, or that holds a secret, an e-mail
  address or an absolute path outside the repository.
- **AI 008**: The command hook shall refuse, naming the rule, a command that writes to an
  absolute path outside the repository and the temporary directories, or that pushes to a branch
  other than the session's own and `main`, and shall allow every other command.
- **AI 009**: The edit hook shall format an edited C++ file of the repository with the
  repository's formatter, and leave every other file unchanged.
- **AI 010**: The provenance report and the commit policy shall read an optional `Gate:`
  trailer that names the gate's report, report each assisted commit with it, and not require it.

No existing requirement changes.

### Software items and safety class

None. Only tools change; no product item's code, class or segregation.

### Risk

None for the product's hazards: the gate and the agent files are verification and development
tools (class T2 for TL-51 and TL-52). A threat model review of an agent with shell access is
added (its permissions, the secrets it can read, its network and what it installs).

### SOUP

None: the gate, the checker and the hooks use the Python standard library and tools already in
the SOUP list.

### Interfaces and data formats

None. The `Gate:` trailer is optional (commit policy 3, compatible).

### Documents

The SRS (version 39, the AI group's requirements 005 to 010); the tool list (TL-51, TL-52); the commit policy
(version 3); the threat model (a new version with the agent review); `CLAUDE.md` and
`.claude/settings.json` (version 1 each); ADR 0040; the design file; the CHANGELOG.

### Regulatory

The intended use does not change, and no safety-relevant function changes. A person's review of
every change stays required, however it was written.

## Verification

`tools.agent_gate` (each known-bad change fails its own check, the good one passes);
`tools.check_agent_files` and `docs.agent_files`; the hooks' unit tests; `tools.ai_provenance`;
`docs.trace`, `docs.srs`, `docs.changes`; the subagent's eval, run by hand with an agent and its
results kept as evidence.

## Decision

Pending: the software lead.
