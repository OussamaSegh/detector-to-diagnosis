# 0040. Judge an agent's changes by the project's own checks, and keep its files under control

Date: 2026-11-23
Status: Accepted

## Context

MiniDAQ's commits have named an AI assistant since Chapter 37 (ADR 0032), and the third edition
(roadmap 3.0.0, Part XI) teaches an engineer's work when agents write much of the code. Two
questions had no recorded answer:

- **When is an agent's change ready for a person?** An agent writes code quickly and says it is
  done. The project has a dozen checks (the trace matrix, the requirements' form, document
  control, the waits in tests, the layers, the format, the build, the tests, static analysis),
  each run in its own place; nothing ran them together on one change and said what was wrong.
- **Who controls what the agent reads and may do?** A context file, a subagent, a skill or the
  agent's settings tell the agent what the project is and what it may run. None was in the
  repository, so none was versioned, reviewed or checked, and a stale path or a wide permission
  would be followed as faithfully as a true one.

The formats of the agent's files were read from the agent's documentation on 2026-11-23: a
subagent is Markdown with YAML frontmatter whose `name` and `description` are required and whose
`tools` is a list of tool names; a skill is `SKILL.md` in a directory of its own, with optional
frontmatter including `allowed-tools`; the settings hold `permissions` (`allow`, `ask`, `deny`
rules of the form `Tool(specifier)`) and `hooks` (an event, a matcher on the tool's name, and
commands that read the event as JSON on stdin; exit status 2 refuses the tool call and shows the
reason to the agent).

## Options

1. **Trust the agent's report and the person's review.** Nothing to build; the review starts from
   the agent's claim, and each check the reviewer forgets is not run.
2. **Run CI on every change.** CI already runs every check, after a push, in tens of minutes,
   and on main; a change that fails is already public, and the answer is a list of jobs, not of
   reasons.
3. **A gate on the change, shown to fail, and the agent's files under document control.** The
   project's checks, run on the change between a base and the working tree before a person
   reviews it, with one verdict and a reason per failure; a library of known-bad changes that it
   must reject; the agent's files versioned, registered and checked statically, with hooks that
   refuse only what the rules already forbid.

## Decision

Option 3 (CR-0036).

- **The gate** (`tools/agent_gate.py`, TL-51) runs the checks of its own version on the change,
  so that a change cannot weaken the checks that judge it, and reports a change to any of them
  for a person (SRS-AI-005, SRS-AI-006). It is fast without a build (seconds) and complete with
  `--full`. Its verdict can travel with the commit as an optional `Gate:` trailer (commit policy
  3, SRS-AI-010).
- **The known-bad library** (`tools/agent_gate/known-bad/`) is the gate's verification: each
  change is a patch against a fixed commit, taken from the project's problem reports and rules,
  and `tools.agent_gate` requires each to fail for its own reason and a good change to pass. An
  escape found later becomes a new case.
- **The agent's files** (`CLAUDE.md`, `.claude/`) are registered with a version and an owner in
  `.claude/README.md` and checked by `tools/check_agent_files.py` (TL-52, SRS-AI-007): their
  fields, the paths, commands and tests they name, the tools they allow against a least-privilege
  policy, and that they hold no secret, address or absolute path.
- **The hooks** refuse a write outside the repository and a push to a branch other than the
  session's own and `main` (SRS-AI-008), and format an edited C++ file (SRS-AI-009). They are
  guards against mistakes, not a sandbox.
- **No agent runs in CI.** The gate judges a change, however it was written. A subagent's eval
  (`tools/agent_evals/`) is run by hand with an agent and its results are kept as evidence.

The principles are stated for any agent: least privilege per kind of file; every step of a skill
a command a person could run; a hook refuses only what a rule forbids, and names the rule; the
files checked like code; and the check reads only the fields it needs, so that a change of the
agent's format is a change request, not a silent edit.

## Consequences

### Positive

- A reviewer starts from what is known to be wrong, with the reason, before a push.
- The gate is shown to fail: its library holds twelve changes it must reject, one of them a
  subagent given the tools to edit what it should only report on.
- What an agent is told and allowed is versioned, reviewed and checked in CI like any other
  controlled document.

### Negative

- A PASS is not a review. The gate cannot see a change that is wrong but consistent: the
  subagent eval's case that loosens a risk control's test passes every check of the gate. The
  person's review stays required (SRS-AI).
- The hooks see the command as written: a path built at run time is not refused.
- The agent's files follow one agent's formats; another agent needs its own entries in the
  policy and the register.
