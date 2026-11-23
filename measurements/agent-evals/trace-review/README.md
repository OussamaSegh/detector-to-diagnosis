# Eval of the trace-review subagent, 2026-11-23

The subagent eval of CR-0036 (roadmap 2.2.0, Theme P2), run by hand as ADR 0040 requires: no
agent runs in CI.

## Setup

- **Agent:** the draft `.claude/agents/trace-review.md`, version 1 (read-only tools: Read, Grep,
  Glob), run as six separate subagents with its instructions and nothing else.
- **Base:** a worktree of 8b1eeab, the eval's base commit in `tools/agent_evals/trace-review/cases.json`.
  Each subagent was given one case's patch as the change; the patch was not applied.
- **Scoring:** `python3 tools/agent_evals/score.py tools/agent_evals/trace-review/cases.json <case> <case>.md`.
  Each report is kept verbatim in `<case>.md`.

## Results

| Case | Expected | Score | A person's judgment |
|---|---|---|---|
| test-without-requirement | 2: EmptySourceTypeIsRefused | PASS | Right. |
| behavior-without-requirement | 4: coincidence_sorter.cpp | PASS | Right. Its extra finding 3 (RC-17's verification) is also right. |
| requirement-loses-its-test | 1: SRS-CFG-001 | PASS | Right. The extra lines "- 2:" to "- 4:" are notes that nothing was found, not findings. |
| new-requirement-without-test | 1: SRS-SRT-999 | PASS | Right. |
| weakened-risk-control | 3: SRS-SRT-009 | PASS | Right: it found the loosened assertion that the gate passes (ADR 0040, negative consequences). |
| good-tagged-test | none | FAIL | The verdict is right ("No findings under criteria 1 to 4"), but the report numbered its reasons 1 to 4, which the scorer reads as findings. It also noted, rightly, that the SRS-CFG-001 tag fits the test poorly. |

Five of six cases pass by the scorer, six of six by a person's reading. The one failure is the
report's form, not its judgment, and it is corrected where it arose: version 2 of the subagent
says "Number only findings", and a criterion with nothing to report gets no line. The scorer is
not loosened to accept numbered reasons, since a numbered line is how a finding is recognized.

## To do at the next run

Run the six cases again with version 2 of the subagent when it is committed, and keep the
reports here beside these.
