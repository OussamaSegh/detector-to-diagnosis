# Roadmap for release 2.2.0

Status: accepted. Drafted on 2026-11-23, after the release of 2.1.0 and the merge of its
independent review (PR #21, 4558b1a). Accepted the same day under the author's standing
direction that the work go on release by release, each step planned before it starts
(2026-11-16).

## 1. Where 2.1.0 leaves the project

- **The book.**
  - The Second Edition has 40 chapters in ten Parts and Appendix A, with four exercises or
    more in every chapter.
  - The PDF is 794 pages, so 34 pages of room are left under KDP's 828. The solutions manual
    has 233 pages.
  - The Third Edition (roadmap 3.0.0) will be printed in two volumes, so 2.2.0 spends little of
    this room: it adds code, tools and records, and short sections only where a chapter
    already teaches the thing changed (Chapter 37 for the agent files).
- **Open problem reports.** MDQ-PR-006 is the one known anomaly. Its decision stands until
  control API 4.0 (roadmap 3.0.0, Chapter 43).
- **Found by the review of 2.1.0.**
  - MDQ-PR-088: fixed (the projector's `out` and an unpickled array).
  - MDQ-PR-089: fixed (the record's table and the evidence).
  - MDQ-PR-081, MDQ-PR-087 and MDQ-PR-089 share a cause: a change to what the release checks
    do, made in one place and not in the tool or record that describes it. The review
    recommends that the internal audit of 2.2.0 evaluate a CAPA for them.
  - The table check of MDQ-PR-089 compares a record with today's labels. The record of 2.0.1,
    whose soak lasted 30 minutes, now fails `release_record.py check`. No test runs that check
    on old records, so CI is green, but the check is wrong for them (to be reported as
    MDQ-PR-090 and fixed first).
- **Due at 2.2.0.**
  - The effectiveness check of CAPA-0006 (CI results read after every push).
  - The trend analysis, the internal audit and the SOUP review for 2.2.
- **Not yet done.** `release/2.0` is not cut: pushing that branch waits for the author's
  approval (roadmap 2.1.0, section 4).

## 2. What 2.2.0 is for

A minor version: compatible additions only (maintenance plan, section 4). No interface breaks.
It is the groundwork of the Third Edition (roadmap 3.0.0, section 5): the parts of the agent
workbench and of the acquisition at scale that can be built, tested and released without
breaking anything, so that 3.0.0 can write Part XI on code that already works.

1. **A gate for changes an agent makes**, shown to reject known-bad changes.
2. **Agent files under the quality system**: context files, a review subagent, a release-check
   skill and hooks, each versioned, checked statically in CI and least-privileged.
3. **Several acquisition nodes in the simulator**, and a merge of their streams in one process,
   tested against the single-node sorter.
4. **A release process whose records cannot drift** from what the checks do.

## 3. Themes and scope

### Theme R: records that follow the checks

- MDQ-PR-090: `release_record.py check` judges a record's table against the labels of the
  release it records. The evidence names the soak's length (`soak.txt`), so the label is read
  from it, not from today's table.
- The CAPA evaluation of MDQ-PR-081, 087 and 089 at the internal audit, with `pr_trends.py`.
  If a CAPA is opened, its action is a single source for each fact that the checks and the
  record share: the soak's length, the presets, the fuzz targets and their seconds.
- The coverage review compares two releases line by line. The release checks keep the list of
  untaken branches (`coverage/uncovered.txt`), which 2.1.0 lacked (its coverage review).
- Exit: `release_record.py check` compares every record from 2.0.0 on (the first with today's
  rows) with its own evidence; the audit records the CAPA evaluation.

### Theme P1: the agent gate and its known-bad library

- **`tools/agent_gate.py`** (TL-51): one verdict for a change, with a reason for each failure.
  - Build and tests on the presets the change touches.
  - Coverage of the changed lines (`tools/coverage.py`).
  - A requirement tag on each new test, and the trace checks.
  - Static analysis.
  - The performance gate where the change touches a benchmarked path.
  - Mutation score on the changed lines, with `tools/mutation_test.py`, where the
    change is in a class B item.
- **The known-bad library** (`tools/agent_gate/known-bad/`): at least ten changes, each a patch
  against a fixed commit with the defect it holds. They are taken from MiniDAQ's own problem
  reports (for example MDQ-PR-084, MDQ-PR-074 and MDQ-PR-014), plus one change whose test has no
  requirement tag and one that lowers coverage. The test `tools.agent_gate` applies each patch
  in a scratch worktree and requires a FAIL with the expected reason, and requires a PASS on a
  known-good change.
- No agent runs in CI. The gate judges a change, however it was written.
- Exit: the gate rejects every known-bad change for its expected reason and passes the good one.

### Theme P2: agent files under the quality system

- **Context files.** The repository's context file (`CLAUDE.md`) and the agent's settings
  (`.claude/settings.json`: permissions and hooks) are added as controlled documents, each
  with a version, an owner and a history. Exercise 37.2's checker is extended into
  `tools/check_agent_files.py` (TL-52), run in CI:
  - frontmatter and the required fields;
  - every path, command and test that a file names exists;
  - the tools an agent file allows, against a least-privilege list per kind of file;
  - no secret, no personal data, no absolute path outside the repository.
- **The review subagent for IEC 62304 traceability** (`.claude/agents/trace-review.md`):
  given a change, it reports each new requirement without a test, each test without a
  requirement tag, and each risk control without its verification. Read-only tools only; it
  reports and does not edit. Its eval: recorded changes with their expected findings
  (`tools/agent_evals/trace-review/`), run by hand with an agent, the results kept as evidence.
- **The release-check skill** (`.claude/skills/release-checks/SKILL.md`): runs
  `tools/release_checks.sh OUT 600 resume`, reads `release-checks.txt`, applies the rerun rule
  of SDP section 8, and drafts the record with `tools/release_record.py skeleton`. Each step is
  a command a person could run, and it states the two-hour limit of a background command that
  2.1.0 met.
- **Hooks**: before each command, refuse writes outside the repository and pushes to a branch
  other than the session's own and `main`; after each edit, run the formatter on the edited
  file. Each hook is a script in `tools/hooks/` with its own unit test.
- **Provenance, extended**: `tools/ai_provenance.py` accepts a `Gate:` trailer that names the
  gate's report, and the commit policy records it when present (commit policy 3, compatible:
  the trailer stays optional in 2.2).
- Records: CR-0036 (the agent files and the gate), ADR 0040, SRS-AI-005 on, TL-51 and TL-52,
  and a threat model review of an agent with shell access (its permissions, the secrets it can
  read, its network, and what it installs).
- verify: the current formats of subagents, skills, hooks and settings before the files are
  written; the principles are stated so that they apply to other agents.
- Exit: every agent file passes `tools/check_agent_files.py` in CI; the subagent's eval
  finds each expected finding in its recorded cases.

### Theme S: several nodes in the simulator

- **The simulator with several nodes**: the scanner's blocks are divided among N readout
  nodes, each a stream of its own with its own clock offset, as several acquisition PCs would
  send them. Additive: one node is the default, and every existing configuration behaves as in
  2.1 (configuration schema 2.2, an optional field).
- **The merge inside one process**: a k-way merge of the nodes' time-ordered streams into one,
  before the coincidence sorter, with a stated overlap at node boundaries so that no
  coincidence across two nodes is lost.
- **The oracle**: property tests with the single-node sorter as the reference. For any division
  of the blocks and any clock offsets within the specified bound, the merged run's
  coincidences equal the single-node run's.
- **Measured**: the merge's cost per single, and the pipeline's throughput with 1, 2 and 4
  nodes (SRS-PERF-020 must still hold with one node; the gate runs with the default).
- Records: a change request (CR-0037), SRS requirements for the merge and the boundary
  overlap, a hazard review (a coincidence lost at a boundary is a cause of H-01, coincidence
  data lost without notice).
- Not in 2.2.0: nodes as separate processes or machines, the loss of a node, the network.
  Those are Chapters 41 and 42 of 3.0.0.
- Exit: the property tests pass with the oracle; the release checks pass with the default of
  one node.

## 4. Order and milestones

| Milestone | Content | Exit criterion |
|---|---|---|
| 2.2.0-dev, first | Theme R (MDQ-PR-090, uncovered list kept) | Every record from 2.0.0 matches its own evidence |
| 2.2.0-dev, second | Theme P1: the gate and its known-bad library | Every known-bad change rejected for its reason |
| 2.2.0-dev, third | Theme P2: context files, subagent, skill, hooks, provenance, their static check | Every agent file passes its check in CI; the eval's findings recorded |
| 2.2.0-dev, fourth | Theme S: nodes in the simulator, the merge, the oracle, the measurement | Property tests pass; throughput measured |
| 2.2.0 | Internal audit with trends and the CAPA evaluation (Theme R), CAPA-0006 check, SOUP review for 2.2, full release checks | CI green on the release commit; tag `book-v2.2.0` |

The work starts with `tools/post_release.py . 2.2.0-dev` and the SOUP list's dated
known-anomaly review for 2.2 (a draft, approved by the author at the release).

The rhythm stays as before:

- Every release gets an independent review on an Opus model.
- That review's fixes go out in the next patch or minor release.
- Each controlled document that changes is approved by the author in writing before the
  release checks.

## 5. Out of scope for 2.2.0

- **Breaking changes**: control API 4.0, schema 3.0 and the list-mode format MDQ-P2 wait for
  3.0.0, grouped in one milestone.
- **Part XI's chapters** and the recorded agent sessions. They are written in 3.0.0, on the
  code of this release.
- **The tool server over the run records (MCP).** It is the last piece of Chapter 44 and needs
  the run records of several nodes; it comes in 3.0.0-dev.
- **Nodes as processes or machines, and network faults.**
- **New third-party dependencies**, unless the author approves each one. The gate and the agent
  file checker use the standard library and the tools already in the SOUP list.

## 6. Risks

| Risk | Effect | Response |
|---|---|---|
| The gate passes a bad change that a person would catch | False confidence in agent changes | The known-bad library is the gate's own verification; a person's review stays required (SRS-AI); each escape found later becomes a new known-bad change |
| Mutation testing is slow on class B items | The gate takes too long to use | Mutate only the changed lines; a time limit per change, reported in the verdict |
| Agent file formats change during the release | The static check or the files break | The check reads only the fields it needs; a format change is a change request, not a silent edit |
| A hook blocks normal work | Sessions work around the hook | Hooks refuse only what the SDP already forbids; each refusal names the rule |
| The merge loses or duplicates coincidences at node boundaries | Wrong counts, a hazard | Specified before it is coded, tested against the single-node oracle, and one node stays the default |
| The multi-node simulator slows the pipeline with one node | The performance gate fails | The one-node path bypasses the merge; the gate runs with the default |
| The roadmap's scope grows into 3.0.0 | 2.2.0 slips | Anything that breaks an interface or needs Part XI's text waits for 3.0.0 |
