# The skills map and a self-assessment {#app-skills}

Agents now write much of the code of a system like MiniDAQ: whole functions, tests, scripts and
documents. What stays with the engineer is what an agent cannot give itself. This book trains
eight skills for that work. This appendix maps each one to the chapters that teach it, the
exercises that practice it and the records in the companion repository that show it done. It
ends with a self-assessment: what a reviewer of your work should be able to see.

The skills are not a second syllabus. Every chapter still teaches its subject, and the skills
grow out of the subjects: nobody can review a lock-free queue, a coincidence window or a
real-time thread without understanding them. The map shows where the book trains each skill
on purpose, so that you can find the practice you need.

## The eight skills {.unnumbered}

1. **Specify.** Write requirements and acceptance tests precise enough that a wrong change
   fails them.
2. **Review and verify.** Judge code you did not write, with tests as the review, mutation,
   differential tests and measurement.
3. **Judge architecture and interfaces.** Make the decisions that are expensive to undo, and
   write them down before anyone builds on them.
4. **Reason about risk and safety.** Know what a failure does to a patient's scan, and whether
   a control reduces the risk it cites.
5. **Bring tools under the quality system.** Traceability, tool validation, controlled
   context files and records, as IEC 62304 and ISO 13485 ask.
6. **Debug and measure.** Find what went wrong first, including in parts nobody on the team
   wrote by hand, and give numbers with their uncertainty.
7. **Run agent workflows.** Specifications, context, permissions, guardrails and gates, and
   the team's own agent tooling, composed, tested and kept under control.
8. **Know the domain physics.** Know it well enough to see a plausible result that is wrong.

## Where each skill is trained {.unnumbered}

Exercises marked A are audits: you receive a recorded agent change to the chapter's code, with
its specification and its session, and write the tests that reject it and accept the corrected
change. Each audit holds defects that MiniDAQ really had, taken from its problem reports.

| Skill | Chapters that teach it | Exercises that practice it | Records that show it |
|---|---|---|---|
| 1. Specify | 14 (testable requirements), 18 (properties), 33 (acceptance) | 14.2, 18.2, 33.2, 7.6 (A), 21.6 (A) | `docs/regulatory/srs.md`, `docs/regulatory/verification/acceptance.json`, the `REQ:` tags of the tests |
| 2. Review and verify | 18 (unit tests and mutation), 21 (review), 37 (an assistant's change) | 1.4, 18.1, 18.5, 21.1, 37.3, and every exercise marked A | `docs/code-review-checklist.md`, `tools/agent_gate/known-bad/`, `tools/mutation_test.py` |
| 3. Architecture and interfaces | 6 (architecture), 12 (a file format), Appendix A | 6.3, 36.5 (A) | `docs/adr/`, `docs/architecture/architecture.md`, `docs/architecture/layers.json` |
| 4. Risk and safety | 15 (ISO 14971), 17 (cybersecurity), 25 (the platform), 40 (maintenance) | 15.1, 15.2, 15.3, 15.6 (A), 40.5 (A) | `docs/regulatory/risk/hazards.json`, the threat model, `docs/regulatory/problem-reports.json` |
| 5. Tools under the quality system | 14 (IEC 62304), 16 (ISO 13485), 20 (CI in a regulated setting) | 14.4, 14.5, 16.3, 16.4, 20.3, 21.6 (A) | `docs/regulatory/verification/tools.md`, `docs/regulatory/capa/`, `docs/regulatory/releases/` |
| 6. Debug and measure | 2, 3, 5 (performance), 21 (debugging), 23 (networking), 33 (the end-to-end run) | 20.5, 21.2, 21.4, 21.5, 23.5 (A), 33.5 (A) | `measurements/`, the postmortems of Chapter 21, the release records' soak |
| 7. Agent workflows | 37 (AI-assisted coding) | 37.2, 36.5 (A) | `CLAUDE.md`, `.claude/`, `tools/agent_gate.py`, `tools/hooks/` |
| 8. Domain physics | 8 (PET physics), 10 and 11 (sorting and count rates), 26 to 30 (calibration to image quality), 39 (time of flight) | 8.3, 8.6 (A), 30.5 (A), 31.5 (A) | `measurements/ch08/`, the QC reports, `recon/` and its tests |

The chapters written for the Third Edition around these skills, and their own audit
exercises, extend this map where they train a skill on purpose.

## The audit exercises {.unnumbered}

The ten audits of Parts I to X, with the skill each one trains most and the problem reports
its defects come from (the solutions manual names them; the exercise does not, so as not to
give the answer away):

| Exercise | Part | The change under audit | Skill |
|---|---|---|---|
| 7.6 | I | A reader of untrusted input that "never throws" | 2, 1 |
| 8.6 | II | A coincidence finder, judged against 2τ S~1~ S~2~ | 8, 2 |
| 15.6 | III | A risk control that a test suite "verifies" | 4 |
| 21.6 | IV | The rules that keep the version of a crash report honest | 5, 1 |
| 23.5 | V | The loss counters an operator judges a scan by | 6, 2 |
| 30.5 | VI | The metadata reader of the daily QC report | 2, 8 |
| 31.5 | VII | The check of a NumPy output array | 8, 2 |
| 33.5 | VIII | The count checks of the end-to-end run | 6, 1 |
| 36.5 | IX | The guard against a push that rewrites history | 7, 3 |
| 40.5 | X | The reader of an update store's state | 4, 2 |

Each audit works from its recorded session alone, so you need no agent to do it. If you use
one, give it the same specification and judge its change with your tests: the same acceptance
applies to every change, whoever wrote it.

## A self-assessment {.unnumbered}

A skill is visible in what you leave behind. For each skill, here is what a reviewer of your
work, a colleague, a lead or an auditor, should be able to see in your changes and records
without asking you. Score each statement 0 (not yet), 1 (sometimes) or 2 (every time), on your
own last ten changes, and come back to the chapters of the lowest scores.

**1. Specify.**

- Every change starts from a requirement or an acceptance test that was written before the
  code, and that a plausible wrong change fails.
- Your requirements name a number, a limit or an observable behavior, never "fast" or
  "robust".
- You can point to a test that failed before your change and passes after it.

**2. Review and verify.**

- Your review comments are tests, or name the test that would show the problem.
- You checked at least one claim of the change's author, human or agent, against the code or a
  measurement, and said what you found.
- Your tests of a reader try every type in every field, and the edges of every numeric type.

**3. Architecture and interfaces.**

- An interface change of yours has a decision record, a version, a migration note and a test
  that the old form is refused clearly.
- You can say, for each of your recent changes, which layer it is in and why it is not in
  another.

**4. Risk and safety.**

- For a change to a class B item, you can name the hazard it touches, and the control's test
  is one test per cause the control names.
- Your problem reports have an evaluation of the effect on a scan, not only on the code.

**5. Tools under the quality system.**

- Every tool that judges your work is in the tool list, with what shows it can fail.
- Your commits carry their trailers, and the trace matrix and the documents' versions were
  updated in the same commit as the change.

**6. Debug and measure.**

- Your postmortems find what went wrong first, not what was noticed first.
- Every number you quote has its file under `measurements/`, its spread and the machine it was
  measured on.

**7. Agent workflows.**

- The agents you use run with the fewest permissions that do the job, and their context files
  are true: every path, command and test they name exists.
- An agent's change of yours passed the gate and a person's review, and the record says which
  agent made it.

**8. Domain physics.**

- You can predict a count, a rate or a resolution before you run the code, and you say so when
  the code disagrees.
- At least one of your tests uses physics as its oracle: a formula, a conservation or a known
  phantom.

A total is less useful than its lowest line. A team that reviews agent changes needs each
engineer to score 2 on the second and the fourth skills before the others.
