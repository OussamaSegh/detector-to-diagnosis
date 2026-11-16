# Roadmap for release 3.0.0, and after

Status: proposed, revised on 2026-11-16 at the author's direction. The author's answers are in
section 8; section 7 holds the questions still open, each with a recommendation. Work on 3.0.0
starts after release 2.1.0 (`docs/ROADMAP-2.1.0.md`). Nothing here changes 2.0.1 or 2.1.0.

## 1. Why this edition changes its aim

The first two editions teach an engineer to write a regulated medical-imaging system in C++, from
memory layouts to the release record. Agentic AI changes the work they prepare for. Agents now
write much of the code: whole functions, tests, scripts and documents. They read a repository,
run commands and propose complete changes.

What stays scarce is what an agent cannot give itself:

- a precise statement of what must be true;
- the judgment of whether a fluent change is right;
- the architecture that keeps changes small;
- the risk reasoning behind a medical device;
- the evidence that a notified body accepts.

The engineer who leads a data acquisition system now does more of the following:

1. **Specify** requirements and acceptance tests precisely enough that a wrong change fails them.
2. **Review and verify** code they did not write, with tests as review, mutation, differential
   tests and measurement.
3. **Judge architecture and interfaces**: the decisions that are expensive to undo.
4. **Reason about risk and safety**: what a failure does to a patient's scan.
5. **Bring AI tools under the quality system**: traceability, tool validation, controlled
   context files and records (IEC 62304, ISO 13485).
6. **Debug and measure systems**, including parts that nobody on the team wrote by hand.
7. **Run agent workflows**: specifications, context, permissions, guardrails and CI gates.
8. **Know the domain physics** well enough to see a plausible result that is wrong.

They do less of this:

- writing routine code from a blank file;
- remembering library details;
- typing tests one by one.

The fundamentals stay. Nobody can review lock-free code, a coincidence window or a real-time
thread without understanding them, so Parts I to X keep teaching them. What changes is how the
book trains them: it asks more often for a judgment of code than for code.

Chapter 37 (Part IX) began this. It covers the assistant as tool TL-48, provenance in every
commit, a checked context file and a review written as tests. The Third Edition makes this the
spine of the book instead of one chapter.

## 2. Where 2.x will leave the project

- **The book.**
  - 40 chapters in ten Parts and Appendix A, 819 pages.
  - KDP's paperback limit is 828 pages.
  - Release 2.1.0 makes room and spends it on depth in Parts VI to X.
- **Exercises.**
  - There are 171.
  - Almost all ask the reader to write code from a starter that fails.
  - Only a handful ask for a judgment of someone else's code, for example 1.4 (undefined
    behavior), 18.5 (surviving mutants), 21.1 (a review) and 37.3 (a review written as tests).
- **Left out of 2.0.0 on purpose:**
  - scaling the acquisition beyond one PC;
  - GPU reconstruction.
- **The 2.x interfaces.** These cannot change in a minor release:
  - The control API only answers requests.
  - The service polls its ports every 20 ms (MDQ-PR-006).
  - The configuration and the list-mode format describe one acquisition PC.
- **The platform.** C++23 is limited to what GCC 13 (Ubuntu 24.04) supports. Ubuntu 26.04 LTS
  is next (verify: its compilers and when its GitHub runner image is generally available).
- **AI tools under the quality system.**
  - In place: the assistant is in the tool list (TL-48, class T3) and in the threat model, and
    the commit policy's rule `assisted` asks for tests.
  - Missing: a gate that an agent's change must pass before a person reviews it.
  - Missing: context and prompt files under document control.
  - Missing: a validation argument for an agent workflow, as opposed to a single assistant.

## 3. What 3.0.0 is for

A major version: a Third Edition of the book and a breaking release of MiniDAQ.

1. **An engineer for the agentic era.** The book trains the eight skills of section 1 on
   MiniDAQ. Agents are in the loop, and the reader is the one who specifies, verifies and signs.
2. **A scanner with more than one acquisition PC.** This is the system work the author chose
   (section 8, answer 1). It is the worked project through which Part XI teaches those skills.
3. **Run control that tells instead of being asked.** API 4.0 pushes events to clients, which
   closes MDQ-PR-006.
4. **The full C++23 on the next LTS platform.**
5. **Room for the whole book**, in two volumes.

## 4. Themes and scope

### Theme P: the agent workbench in MiniDAQ (new)

These are the tools that make agent work verifiable, built and validated like any other tool.

- No agent runs in CI.
- No exercise needs a particular vendor's agent. Claude Code is the book's example, as in
  Chapter 37.

**`tools/agent_gate.py`**, the gate an agent's change must pass before a person reviews it.

- Its checks:
  - build and tests on the presets the change touches;
  - coverage of the changed lines;
  - mutation score on the changed lines;
  - a requirement tag on each new test, and the trace checks;
  - static analysis;
  - the performance gate where the change touches a benchmarked path.
- It gives one verdict, with a reason for each failure.
- The gate is itself shown to fail: it must reject every change in a library of known-bad
  changes.

**Recorded agent sessions** as exercise material.

- Each session is a specification, the agent's transcript and its patch.
- Each is produced once, frozen in the repository and reviewed. Every reader audits the same
  change, and CI can check the audit.
- A reader with their own agent can also run it on the same specification. The same gate judges
  the result.

**Context and prompt files as controlled documents.**

- The repository's context files, the agent's permissions and its guardrails are versioned,
  reviewed and checked (Exercise 37.2's checker, extended).
- A change to them follows change control.

**Provenance, extended.** An agent's commit names the specification or change request that it
implements and the gate report it passed (`tools/ai_provenance.py`).

**Validation of the agent workflow.**

- A risk-based argument, in the manner of computer software assurance, for the workflow as a
  whole.
- Its evidence: the gate's known-bad library and every change the gate judged.
- It is recorded in the tool list as a process, not as a product.
- verify: the current FDA guidance on computer software assurance and ISO/TR 80002-2 before the
  text cites them.

**Records.**

- A change request and an ADR.
- New SRS-AI requirements, from SRS-AI-005 on.
- New tools from TL-51 on.
- A threat model review of an agent with shell access: its permissions, secrets and network,
  and the supply chain of what it installs.

### Theme L: Part XI, building the acquisition at scale with agents (four chapters)

Each chapter adds part of the multi-PC scanner to MiniDAQ and teaches one or two skills of
section 1 by doing them. In each chapter the reader:

1. writes the specification and the acceptance tests;
2. has an agent implement the change, or studies the recorded session;
3. audits the result with the chapter's methods;
4. puts it on the record.

Everything runs on one machine, with nodes as processes on the loopback interface or in network
namespaces.

**Chapter 41, specifications an agent cannot misread.**

- *Worked example:* several acquisition PCs.
  - Blocks are divided among readout nodes.
  - The coincidence search is partitioned at node boundaries.
  - Time-ordered streams are merged.
- *Skill:* requirements and acceptance tests precise enough that a wrong merge fails them.
  - Property tests use the single-node sorter as the oracle.
  - The boundary overlap is stated as a requirement.
  - The recorded session shows an ambiguity in a first draft that an agent filled the wrong
    way.

**Chapter 42, verifying code you did not write.**

- *Worked example:* a node that fails.
  - Detecting the loss of a node.
  - What a run keeps and what it marks incomplete.
  - The integrity verdict across nodes.
- *Skill:* review as evidence. The reader audits a recorded agent change that passes its own
  tests and holds three seeded defects. The methods are:
  - mutation of the changed lines;
  - differential testing;
  - fault injection with tc netem;
  - a measurement that shows a wrong timeout.
- The engineer writes the risk analysis of a partial scan (ISO 14971: new hazards and controls)
  and does not delegate it.

**Chapter 43, interfaces and architecture an agent builds on.**

- *Worked example:* control API 4.0 with pushed events, and the service's event-driven fault
  path, which closes MDQ-PR-006.
- *Skill:* judgment of interfaces and architecture.
  - Why the event schema, the ordering guarantees and the lock order are decided by a person and
    written as an ADR before any agent writes code against them.
  - How a migration note and a refusal test protect existing clients.

**Chapter 44, the agent workflow under the quality system.**

- *Worked example:* the whole workflow of Part XI, recorded as evidence.
  - Theme P's gate.
  - Context files under document control.
  - Permissions and guardrails.
  - Provenance and the validation argument.
  - An incident: an agent's change that passed the gate and failed in a soak. It is analyzed
    with Chapter 21's postmortem, and a CAPA improves the gate.
- *Skills:* running agent workflows, and debugging and measuring a system that agents helped
  build.

### Theme Q: the skills threaded through the existing book

Parts I to X keep their subjects, and their exercises shift toward judgment.

**One audit exercise per chapter, marked (A).**

- The reader receives a recorded agent change to the chapter's code and finds what is wrong
  with it, using that chapter's tools. Examples:
  - Chapter 3: a data race that TSan finds only under one schedule.
  - Chapter 10: a coincidence window that is off by one at the wrap.
  - Chapter 15: a risk control that does not reduce the risk it cites.
  - Chapter 28: a projector that converges to the wrong image.
- The acceptance tests the audit itself: the reader's tests or report must reject the change and
  accept the corrected one.
- 3.0.0 adds one audit exercise per Part, ten in all. 3.1.0 adds the other thirty.

**Specification first in the milestones.** Each chapter's MiniDAQ milestone starts from a
requirement and an acceptance test that the reader writes before any code, whoever writes the
code.

**A skills map (new Appendix B).**

- It maps the eight skills to the chapters, exercises and records that train them.
- It ends with a self-assessment: what a reviewer of your work should be able to see.
- The front matter's reading path gets a second route through the book, ordered by skill.

**Chapter 37, revised.** It becomes the bridge from an assistant that suggests to an agent that
acts, and it points ahead to Part XI.

**Less rote.**

- Exercises that only ask for code an agent writes reliably, such as a boilerplate parser, are
  shortened or turned into audits.
- The fundamentals they taught stay in the text.

### Theme M: breaking changes, grouped once

Each change has a change request, an ADR, a section in the migration note
(`docs/migration-3.0.md`) and a test that the old form is refused clearly.

- **Control API 4.0.**
  - Clients can subscribe to the run's events and faults, as well as send requests.
  - `minidaq_ctl wait` stops polling.
- **Configuration schema 3.0.**
  - It describes a topology of nodes.
  - A 2.x configuration for a single PC is a one-node topology, and `tools/migrate_config.py`
    converts it.
- **List-mode format MDQ-P2.**
  - Each event carries its node.
  - The readers of 3.0 still read MDQ-P1.
- **Removed:** the path of `tools/migrate_config.py` that converts 1.x configurations.

### Theme N: the platform

- The compiler of Ubuntu 26.04, if its runner image is available by 3.0.0-dev.
- C++23 in full where it makes the code clearer: `std::print`, explicit object parameters and
  `std::ranges::to`.
- Modules stay out.
- A SOUP review for 3.0.
- The Mac setup follows the new platform.

### Theme O: the regulatory chapters, checked again

Chapters 13 to 17 are checked against what is in force at 3.0.0-rc:

- IEC 62304 and the state of its second edition;
- IEC 81001-5-1;
- the MDR's harmonized standards;
- FDA's cybersecurity guidance;
- FDA's guidance on computer software assurance, for the validation of AI tools in the quality
  system.

AI inside the device stays out of this edition, as Chapter 37 says. That covers
machine-learning-enabled software, predetermined change control plans and the EU AI Act. It is a
candidate for 4.0.0 (section 9).

### Theme K: the Third Edition's format

- Two volumes:
  - Volume 1, "The System and the Process", holds Parts I to V.
  - Volume 2, "From Data to Diagnosis", holds Parts VI to XI and Appendices A and B.
- Each volume has its own index.
- A cross-reference to the other volume names that volume.
- The solutions manual and the web edition stay single.
- verify: KDP's rules on a new edition and on a set of volumes, before the files are made.

## 5. Order and milestones

| Milestone | Content | Exit criterion |
|---|---|---|
| 2.1.0 | Its own roadmap | Released |
| 2.2.0 | Groundwork that breaks nothing: Theme P's gate with its known-bad library, context files under document control, extended provenance, the simulator with several nodes, and the merge inside one process | The gate rejects every known-bad change; release checks pass |
| 3.0.0-dev, first | Theme N | Every preset green on the new compiler; Part I updated |
| 3.0.0-dev, second | Theme M, with the earlier chapters updated | `docs.interfaces` passes; migration note complete |
| 3.0.0-dev, third | Chapters 41 to 44 (Theme L), each with its recorded agent sessions | Chapter recipe complete; the gate's report in each chapter's record |
| 3.0.0-dev, fourth | Theme Q: ten audit exercises, milestones written specification first, Appendix B, Chapter 37 revised | Each audit exercise's acceptance rejects the bad change and accepts the fixed one |
| 3.0.0-rc | Theme O, Theme K, the review of the whole book | Each volume within 828 pages; KDP files built |
| 3.0.0 | Third Edition: internal audit and the full release checks | CI green on the release commit; tag `book-v3.0.0` |

The rhythm stays as before:

- Every release gets an independent review on an Opus model.
- That review's fixes go out in the next release.
- Breaking changes are grouped in one milestone.

## 6. Risks

| Risk | Effect | Response |
|---|---|---|
| Recorded sessions date as agents improve | The examples look old | What the book teaches is the audit, not the agent. The changes are kept for the defects they hold, and the text names the agent and version that made each one |
| A reader has no agent, or a different one | Exercises cannot be done | Every audit exercise works from the recorded session alone. Running one's own agent is optional, and the same gate judges it |
| Seeded defects are artificial | Readers learn to find planted bugs | Defects are taken from MiniDAQ's own history (80 problem reports). One session per chapter keeps defects that the agent made itself |
| The gate gives false confidence | Wrong changes pass | The gate is verified against the known-bad library. Chapter 44's incident shows what it misses. A person's review stays required (SRS-AI) |
| The book reads as one vendor's manual | No longer generic | The text and the records are vendor-neutral. Claude Code is named only as an example |
| Partitioning loses coincidences at the boundaries | Wrong counts, which is a hazard | Specified first (Chapter 41), tested against the single-node oracle, and measured |
| One machine hides network effects | The text is contradicted by real clusters | Network namespaces with delay and loss (verify: that CI's runners allow them). The text states the limits |
| Scope grows | The edition never ships | The Part XI list and the ten audit exercises are fixed at the start. Anything else goes to 3.1.0 |

## 7. Questions for the author

1. **Format.** Two volumes in print (recommended)?
2. **Part XI.** Four chapters where the multi-PC acquisition is the worked project and the
   agentic-era skills are the subject (recommended)? The alternatives:
   - Part XI on scaling alone, with the skills only in Theme Q.
   - A separate Part on agents.
3. **Audit exercises.** One per Part in 3.0.0 and the rest in 3.1.0 (recommended), or all 40 in
   3.0.0, which delays the release?
4. **GPU reconstruction.** Keep it out (recommended)?
5. **Breaking changes.** API 4.0, schema 3.0 and MDQ-P2, grouped in one milestone (recommended)?
6. **Platform.** Ubuntu 26.04 and the full C++23 (recommended, if the runner image is available
   in time)?

Until the author answers, the work follows the recommendations, and nothing that cannot be
undone is done.

## 8. Answers (author)

1. **New material, 2026-11-16, on a decision card:** Part XI on the acquisition at scale
   (several acquisition PCs, a node that fails, run control for a distributed system).
2. **Direction, 2026-11-16:** "See long term, plan 3.0.0" and "Think about engineer in agentic
   AI era, skills wont be the same!" This revision follows that direction:
   - The acquisition at scale stays Part XI's system work.
   - The Part's subject becomes the engineer's skills when agents write much of the code
     (sections 1 and 4).

## 9. After 3.0.0: the long-term plan

A breaking change still waits for a major version.

| Release | Aim |
|---|---|
| 3.1.0 | Audit exercises for the remaining 30 chapters, each from MiniDAQ's own problem history; the gate's known-bad library grows from them |
| 3.2.0 | Fleet operations and service of installed scanners: remote updates of many nodes, service logs, and field problems traced back to a release (builds on Chapters 25 and 40) |
| 3.x | The 2.x line kept under the maintenance plan: patch releases for problems relevant to safety until its support ends |
| 4.0.0 (candidate) | AI inside the device, the other half of the agentic era for this engineer: machine-learning-enabled reconstruction or quality control, data management, predetermined change control plans and the EU AI Act. It needs the author's decision on scope and probably a new dependency |

The direction stays the same throughout. The reader should leave able to say what must be true,
to show that it is, and to put it on the record, whoever or whatever wrote the code.
