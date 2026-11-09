# The first 90 days: taking over a data acquisition codebase {#ch34}

::: box-why
Most engineers never write a data acquisition system from the first line, as this book did. They
inherit one: a codebase of some years, written by people who have partly left, running on hardware
that is already in hospitals, under a quality system with its own records and habits. The first
months decide whether the newcomer becomes the person who understands the system or the person who
breaks it with a small change. Every chapter of this book ended with questions to ask your team.
This chapter turns them into a method: what to do in which order, what to read first, how to find
where the risk and the change are, how to change code you do not yet understand without changing
what it does, and when you can say you own it.
:::

**A day in the life.** An engineer joins the team that maintains a scanner's acquisition software.
In the second week they get a "small" ticket: the count rate on the service display shows 0 for a
detector block that is dead, which looks like a quiet block. They find the function, see that it
returns 0 when the live time is zero, change it to return the error code the display already shows
as "---", add a test, and the review approves a two-line change. A month later the field team
reports that the nightly QC script flags every scanner with a disconnected test block as failed:
the script read 0 as "no counts" and had a special case for it, and now it reads -1 as a corrupt
value. The change was correct by any reading of the code. Nobody had written down that three other
programs depended on the old behavior, and the engineer had no way to know it in the second week.
What they lacked was not skill but a map.

## Learning objectives {.unnumbered}

After this chapter you can:

1. Plan the first 90 days with a data acquisition codebase in three phases, and say what "done"
   means for each.
2. Build the system, run it end to end, and reproduce the last release's evidence before changing
   anything.
3. Read a regulated project's documents in an order that answers the questions you will be asked
   first.
4. Survey a codebase from its records and its history: the items and their safety classes, the
   hotspots, the files that change together, the gaps in the map of the code.
5. Write characterization tests that pin what legacy code does, and treat a behavior that looks
   wrong as a decision to be made, not a bug to fix in passing.
6. Make a first change through the full change control, and use it to learn the process.
7. Decide when you own an item, and write the handover you would have wanted.

## Prerequisites and estimated time {.unnumbered}

The whole book, and in particular Chapter 14 (software items and safety classes), Chapter 16 (the
quality system's records), Chapter 18 (testing, mutation testing), Chapter 21 (review and
debugging) and Chapter 33 (the chain end to end). Reading: about 3 hours. Exercises: 5 hours.
Milestone: 3 hours. If time is short, do Exercise 34.3.

## What you are taking over

A data acquisition codebase is more than its source. Before the first day, it helps to list what
you are inheriting, because each part needs a different kind of attention:

- **The product.** The programs that run on the acquisition computer, the firmware interface, the
  configuration files, the formats of the data they write. In MiniDAQ: the server, the control
  client, the update tool, about 130 source files in 22 software items.
- **The evidence.** The requirements, the architecture and its safety classification, the risk
  file, the tests and their reports, the measurements, the problem reports, the release records.
  In a regulated product the evidence is part of what is maintained: a change to the code that
  leaves the evidence behind is an incomplete change.
- **The environment.** The build, its pinned dependencies (the SOUP list), the CI, the test
  benches with real detector hardware, the machines where the release checks run.
- **The people and the process.** Who decides what (the requirements, the acceptance, the
  release), who reviews, who knows the history, how a problem from the field reaches the team.
  None of that is in the repository, and all of it decides how a change goes.

A data acquisition system adds its own particulars. The data cannot be acquired again: a run with
a patient is not repeated because the software lost a packet, so silent loss is the hazard the
whole design guards against (H-01 in MiniDAQ). Timing matters: a change that adds a millisecond to
a hot path can break a real-time budget that no functional test checks. And the meaning of the
numbers belongs to physicists: a count rate, an energy window or a coincidence policy is a physics
decision before it is a line of code.

The 90 days below fall into three phases. The days are a guide, not a contract: a small codebase
moves faster, a large one with unfamiliar hardware slower.

| Phase | Days | Goal | Done when |
|---|---|---|---|
| Reproduce | 1 to 10 | build, run and reproduce the last release | your numbers match the release record |
| Map | 10 to 30 | know where the risk and the change are | you can say, for any file, which item and class it is, and why it changes |
| Own | 30 to 90 | change, release, answer for an item | you have taken a change and a problem report through the whole process |

## Days 1 to 10: build it, run it, reproduce one release

The first goal is modest and decisive: get the system to do on your machine what it did for the
last release. Until you can, you cannot tell whether a difference you see later comes from your
change or from your setup.

**Build from a clean checkout.** Follow the written instructions exactly, and write down every
step that was missing or wrong. In a project that has been built on the same three machines for
years, the instructions are usually incomplete in ways nobody notices: an environment variable set
in someone's shell profile, a package installed once and forgotten, a tag that must be fetched.
MiniDAQ's own handover notes record two such traps: a fresh clone is shallow, and a check of the
change records fails until the full history is fetched; and the analysis tests skip, rather than
fail, without the lock file's packages. Each missing step you find is the first useful thing you
contribute, and fixing the instructions is a safe first commit.

**Run the tests, all of them.** Not the fast subset: every configuration CI runs, the system tests,
the exercises if the project has them. Note how long each takes and which ones are skipped, and
why. A test that is skipped on your machine is a test you are not running.

**Run the chain end to end.** The best introduction to a data acquisition system is to watch data
go through it. Chapter 33's `tools/e2e.py` does that for MiniDAQ in a minute: decays simulated,
sent over a socket, sorted, written, binned, reconstructed, with every count checked between the
stages. If the system you inherit has nothing like it, the first weeks are the right time to
assemble one by hand: generate or replay data, acquire it, look at every file it writes, and
compare the counts. You will learn more about the system's structure from where the counts go
than from its architecture diagram.

**Reproduce the last release's evidence.** Take the last release record and run what it says was
run: the release checks, the benchmarks, the soak. Compare your numbers with the record's. For
MiniDAQ that is `tools/release_checks.sh` in four parts and, since Chapter 33,
`tools/acceptance.py`, which tells you directly whether your evidence would accept the release. A
difference is not necessarily a problem (your machine is not the reference machine), but you must
be able to explain it. If you cannot reproduce the release, nobody can, and that is a finding for
the team, not a failure of yours.

To explain a difference, separate the machine from the code. Build the last release and the
current commit side by side, run their benchmarks one after the other on the same machine, twice,
in alternating order, and compare them with each other as well as with the recorded baseline. If
both are equally far from the record, the machine moved; if they differ from each other, the code
did. MiniDAQ's own release 0.8.0 needed exactly this: its performance gate and its latency limit
failed against the recorded figures, and the same measurements of release 0.7.0, made on the same
machine on the same day, failed the same way (the release record's deviation). Release 0.9.0
needed the same deviation, and a criterion that fails for the machine at every release stops
telling anyone anything: change request CR-0025 made the side-by-side comparison the gate of the
release checks itself, and kept the recorded baseline as a trend to explain. The method costs an
afternoon and turns "it is slower on my machine" into a statement someone can act on.

## Reading the documents in an order that pays

A regulated project has more documents than anyone reads in a week. Read them in the order of the
questions you will be asked first, and read each with a question in mind:

| Order | Document | The question it answers |
|---|---|---|
| 1 | Intended use | What is the product for, and what must it never do? |
| 2 | Architecture and software items | What are the parts, which safety class is each, and why? |
| 3 | Risk file (hazards and controls) | What can go wrong, and which code and tests control it? |
| 4 | Requirements of the items you will touch | What must the code do, and how is each verified? |
| 5 | Open problem reports | What is known to be wrong, and what was decided about it? |
| 6 | SOUP list | Which third-party code is in the product, at which version, with which anomalies? |
| 7 | The last release record and the CHANGELOG | What was verified, and what changed recently? |
| 8 | The decision records (ADRs) | Why is the system built this way, and what was rejected? |

Two things make this order pay. First, the safety class of an item decides how much rigor a change
to it needs, so knowing the classes early tells you where to be careful before you know why.
Second, the open problem reports are the team's memory of what is fragile: in MiniDAQ three are
open, each deliberately (MDQ-PR-006, a port fault noticed up to 20 ms late; MDQ-PR-007, the sorter
holding its last 104 ns of singles until more data arrives; MDQ-PR-009, simulation code linked
into the shipped server), and each records why it was left open. Someone who "fixes" one of them
in passing reopens a decision.

The decision records come last for a reason. They are the most interesting documents and the
easiest to read for pleasure; they are most useful once you know enough to ask why something is as
it is, which is usually in the second week.

Figure [](#fig-ch34-reading) is the same order as a reading path.

```{.figure #fig-ch34-reading src="book/figures/tikz/ch34/reading.tex" caption="The order to read a regulated project's documents, each with the question it answers." alt="Eight boxes in two rows of four, numbered: intended use, architecture with items and classes, risk file, requirements; then open problem reports, SOUP list, release record and CHANGELOG, ADRs. Under each a question, such as what can go wrong for the risk file and why is it built this way for the ADRs." width="80%"}
```

## A survey of the codebase

Reading tells you what the documents say. The history tells you what actually happens: which files
change, how often, together with which others. A question such as "which class B item changes most
and has open problem reports?" needs both, and a tool can put them side by side when the project
keeps its records in a form a program can read. MiniDAQ does, so Chapter 34's code is a survey:
`tools/survey.py` (TL-43, SRS-SVY-001 to SRS-SVY-003).

The first thing it needs is the owner of each file: the software item, and through it the safety
class and the hazards.

```{.python include="tools/survey.py" snippet="owners"}
```

The rule is not the survey's: it is the rule `tools/check_items.py` has applied since Chapter 14,
"the longest prefix wins". A tool that invented its own mapping would disagree with the one the
classification relies on. The second thing is the history per file:

```{.python include="tools/survey.py" snippet="churn"}
```

`git log --numstat` gives, for every commit, the lines added and deleted in each file. The two
details a first version gets wrong are renames (git writes `src/{old => new}/a.cpp`, and the file
should count under its new name) and binary files (`-` instead of numbers). The survey then puts
the two sources together:

```{.python include="tools/survey.py" snippet="survey"}
```

For every item it reports the class, the hazards, the files and code lines, the commits and lines
changed in the window, the requirements with those verified by test and those a test actually
names, and the problem reports with those still open. Then the **hotspots**: the files with the
highest product of commits and code lines. The idea comes from A. Tornhill's work on code as a
record of behavior. A large file that never changes is read once and trusted; a small file that
changes often is cheap to understand again each time; a large file that changes often is where
misunderstandings, and defects, gather, and where a newcomer should read first.

On MiniDAQ at the end of the book (`measurements/ch34/survey.md`), the class B items with open
problem reports come first: the acquisition service, the simulator and the sorter. The top hotspot
is `acquisition_service.cpp`, 500 code lines that 13 commits changed, the file where every chapter
that added a feature to a run had to touch the state machine. Second is `minidaq_sim.cpp`, a tool,
not a product item: the simulator's application grew a feature in almost every Part. Neither is a
surprise to someone who wrote the book. Both would be useful to someone who did not.

### What the survey found in the map

The survey also checks the map of the code itself, and on its first run it found three things that
no other check had reported:

- **Two prefixes that claimed no file.** The item `metrics` claimed `minidaq/src/metrics/`, and
  `processing` claimed `minidaq/src/processing/count_rates`. Both components are header-only; the
  prefixes had been written for source files that were never created. Harmless, since nothing was
  misclassified, but a map that names paths that do not exist is a map that has drifted from the
  code. CR-0021 removed them.
- **Two files owned through a longer prefix.** `hardware_config.hpp` and `.cpp` sit in the
  `config` item's directories and belong to `hw`, whose prefix names them explicitly. Correct by
  the rule, and invisible to anyone who reads the directory listing: a reviewer of a change to
  `src/config/` would assume the configuration item's rigor and reviewers. The survey lists such
  files so that the team can decide whether to move them or to say so in the architecture.
- **No requirement verified by test that no test names.** The trace matrix already enforces
  that, and the survey agrees with it; a disagreement would have meant a bug in one of the two.

The survey decides nothing. It is a list of where to read first and which questions to ask. Its
numbers have limits it states: code lines are a rough measure of complexity (a long table of
constants scores like a long function), and a commit that reformats a file counts like a commit
that fixes it. MiniDAQ's history is also short, so its commit counts reflect the order in which
the chapters were written as much as anything else. On a codebase with years of history the same
view becomes sharper, not weaker.

Figure [](#fig-ch34-treemap) draws the item table as one picture.

```{.figure #fig-ch34-treemap src="book/figures/plots/ch34/treemap.py" caption="The codebase survey as a treemap: each software item's area is its code lines, its color the commits that changed it since 2026-10-01. Where to read first, not where the bugs are." alt="A treemap of 22 software items. The largest areas are hw with 1,303 lines and 34 commits, tools with 1,108 lines, sim with 947 lines, format, service with 873 lines and 38 commits, update and pipeline. Service, hw and sim are the darkest. Small items such as audit, metrics, merger, platform and server are pale rectangles in a corner." width="100%" inputs="measurements/ch34/survey.json"}
```

## Files that change together

The survey looks at files one at a time. The history holds a second kind of information: which
files change in the same commits. Two files that always change together have a dependency, whether
or not the code shows one, and a change to one of them that leaves the other alone deserves a
second look. Exercise 34.1 computes this **change coupling** from `git log --name-only`: for every
pair of files, the commits that changed both, and the share of the less often changed file's
commits that also changed the other.

On MiniDAQ's history (`measurements/ch34/coupling.txt`) the strongest pairs are the expected ones:
the two CMake files (20 commits together, because every new source comes with its test), a header
and its source, a source and its test. The interesting pairs cross items. Every one of the five
commits that changed `acquisition_config.hpp`, the configuration's interface, also changed
`acquisition_service.cpp` (the exercise counts four of them, because the fifth touched 30 files
and is above its size limit): a dependency that the architecture description does not state and
that a reviewer of the next configuration change should look for.

Two cautions keep coupling honest. A commit that touches many files (a rename, a reformatting, a
version bump across the tree) makes every pair of its files look coupled; the exercise leaves out
commits above a size. And coupling can come from people rather than code: one developer who
habitually changes two files in the same commit, or a process rule that makes them change together
(a CHANGELOG, a generated file that is committed). Read the commits before you draw an arrow in the
architecture.

Figure [](#fig-ch34-coupling) shows the twenty pairs as a matrix.

```{.figure #fig-ch34-coupling src="book/figures/plots/ch34/coupling.py" caption="Files that change together: the twenty most coupled pairs of MiniDAQ's history, with the number of shared commits in each cell and the coupling as its color." alt="A symmetric grid of 17 files with labelled rows and columns. The darkest cell joins the two CMakeLists files with 20 shared commits. Other marked cells join headers with their sources, sources with their tests, and the configuration's header and source with acquisition_service.cpp, four shared commits each." width="60%" inputs="measurements/ch34/coupling.txt"}
```

## Before the first change: characterization tests

At some point in the first weeks you will need to change code you do not fully understand. The day
in the life at the start of this chapter shows what goes wrong: the code's behavior was a contract
with programs nobody had listed, and the change broke it. The defense is M. Feathers' technique for
legacy code: before changing what the code does, find out what it does by running it, and write
that down as tests. A **characterization test** does not say what the code should do. It says what
it does today, so that any change of behavior, a mistake or an improvement, fails a test and
becomes a decision instead of an accident.

Exercise 34.3 practices it on a function like the one in the day in the life: the live-time
corrected count rate of an older acquisition program, with an error code for a missing interval,
another for a corrupt counter, 0 for a dead block, a clamp of the live time to the interval, a
truncating division and a display limit. Seven changes are seeded into it. Five are mistakes (an
error code changed, a clamp dropped, a limit mistyped, a division done before the scaling). Two are
well-meant fixes: a dead block reported as an error, and the rate rounded instead of truncated.
The exercise accepts the tests only when every one of the seven fails them, because to the
programs that read the value, a fix nobody decided is as much a change as a mistake.

The technique has three habits worth keeping:

- **Find the boundaries in the code, not in a specification.** Every comparison is a place where
  one more or one less changes the answer; test both sides. Every integer division is a place
  where truncation and rounding differ; find an input that shows it.
- **Name each test after the behavior it pins.** `ABlockDeadTheWholeIntervalShowsZeroNotAnError`
  tells the next person exactly what they are about to change; `Case7` does not.
- **Pin a behavior that looks wrong, and report it.** The test records it; a problem report says
  why it looks wrong and what depends on it; the owner of the requirement decides whether it
  changes, after an impact analysis. Fixing it in passing, inside an unrelated change, skips all
  three.

For a whole program rather than a function, the same idea is a golden test of its output (Chapter
19), and for a whole chain, a comparison with a reference (Chapter 33). Mutation testing (Chapter
18) is how you check that your characterization tests would notice a change: Exercise 34.3 is a
mutation exercise in which you wrote the tests and the mutants were written for you.

Figure [](#fig-ch34-characterize) puts the technique in order.

```{.figure #fig-ch34-characterize src="book/figures/tikz/ch34/characterize.tex" caption="Characterization tests around a change. Pinning today's behavior first turns any change of behavior, a mistake or an undecided fix, into a failing test and a decision." alt="A flow: run the code at its boundaries, tests that pin today's behavior, make the change. Then either all pass, no behavior changed, or one fails, a mistake or a fix nobody decided, which leads to a problem report saying why it looks wrong and what depends on it. A note says a behavior that looks wrong is pinned too." width="95%"}
```

::: box-mistakes
- **Changing before reproducing.** Without the last release reproduced on your machine you cannot
  tell your change's effect from your setup's.
- **Reading every document front to back.** Read in the order of the questions you will be asked;
  the safety classes and the open problem reports first.
- **Trusting the directory layout as the item map.** A file can belong to another item through a
  longer prefix. Ask the map, not the folder.
- **Fixing a quirk in passing.** A behavior that looks wrong may be a contract with programs
  nobody listed. Pin it with a test, report it, and let its owner decide.
- **Reading hotspots as a verdict.** A hotspot is where to read, not where the bugs are. A mass
  reformat or a young history inflates the numbers.
- **Drawing an architecture arrow from coupling alone.** Read the commits; coupling can come from
  habits and process rules.
- **A first change that is too large.** The first change teaches the process; make it small enough
  that the process is the hard part.
:::

## The first change

The first change should be real, small, and taken through the whole process. Real, because a
practice change teaches nothing about the reviews and records that a real one triggers. Small,
because the point is to learn the process, and a large change hides the process behind the code.
Typical first changes are a defect from the problem reports with a known cause, a missing test for
a requirement, or a correction to the build instructions found in the first week.

Take it through every step the project requires, even the ones that seem excessive for its size.
In MiniDAQ that is the change control checklist (items 1 to 6, named in every commit message): the
change request with its impact analysis on the requirements, the items and their classes, the
risk, the SOUP and the interfaces; the code and its tests with their requirement tags; the
documents that change with it; the review; the trace matrix and the other document checks; the
CHANGELOG. At each step, write down what you did not know how to do and whom you asked. That list
is the onboarding document the team does not have.

Measure before and after when the change touches anything timed. A data acquisition system has
performance requirements (in MiniDAQ, SRS-PERF-020 to SRS-PERF-022 and their acceptance criteria),
and a change that is functionally right can still move a benchmark. Running the relevant benchmark
before and after, on the same machine, costs minutes and is the only way to answer the reviewer
who asks.

## Days 30 to 90: from reader to owner

Owning an item means being the person who can answer for it: what it does and why, how it is
verified, what is known to be wrong with it, and what a change to it would affect. The second and
third months turn the map into that knowledge, through three pieces of work.

**Own one item.** Pick, with the team, one software item of moderate size and class: not the
largest hotspot, not a trivial one. Read all its requirements and their tests, run its
measurements, read its problem reports, closed and open, and its history. Then write down what you
would tell a newcomer about it in ten minutes. If the architecture description says less, propose
the missing paragraphs; if a requirement has no test that really checks it, write one.

**Take a problem report end to end.** A report from the field, or from a test, through
reproduction, root cause, fix, verification and, if the cause is systemic, a corrective action
(Chapter 16's CAPA process). The five whys of MiniDAQ's problem reports and their "escape"
field (why no existing test caught the defect) are the most instructive part: the escape is where
the process, not the code, gets better.

**Run a release, or a part of one.** Release checks, the acceptance report, the release record,
the SOUP review. A release exercises every record the project keeps, and the person who has run
one knows which of them are kept carefully and which are kept by habit.

Figure [](#fig-ch34-timeline) puts the three months on one line.

```{.figure #fig-ch34-timeline src="book/figures/tikz/ch34/timeline.tex" caption="The first 90 days as this chapter lays them out: reproduce before changing, read in the order of the questions, map the code and pin its behavior, then own one item, one problem report and one release." alt="A time line from day 1 to day 90. Above it: build, run and reproduce a release by day 10; read the documents in order and survey the code by day 30; own one item; take a problem report end to end; run a release. Below it: characterization tests and the first change. A note says the goal is to become someone who can answer for an item." width="95%"}
```

Throughout, keep asking. Every chapter of this book ended with questions to ask your team; at
this point they become a checklist, grouped by area:

| Area | Ask |
|---|---|
| Product and use | What is the intended use? Which failure would harm a patient or an operator? Which data can never be acquired again? |
| Architecture | Which items are in which class, and why? Which items share a process without segregation? Where is the map of the code unclear? |
| Data path | Where can data be lost or altered? Which counters show it? Is there a chain test? |
| Timing | What are the real-time budgets, and which test or measurement checks each? |
| Hardware | Which firmware versions are supported? Which test benches exist, and who books them? |
| Verification | What does each test level cover? Which tests are skipped where, and why? |
| Release | Who accepts a release, against what? Can the last release be reproduced? |
| Problems | Which problem reports are open, and why were they left open? How does a field problem reach the team? |
| Changes | What does change control require for each class? Who reviews what? |
| SOUP and security | Which third-party code is in the product? Who watches its vulnerabilities? What is in the threat model? |
| People | Who decides the physics (energy windows, policies, limits)? Who knows the history of each item? |

Not all of these have answers. Recording which ones do not is as useful as the answers.

**Write the handover you would have wanted.** At the end of 90 days, write the document that
would have made your first month a week: how to build and run, the traps, the order to read in, the
map of items with what each is for, the open questions. MiniDAQ's `HANDOFF.md`, kept up to date
with every chapter of this book so that any new contributor (human or not) could continue the
work, is one example of the genre. Its most useful sections are the least glamorous: the rules
that bit, and the exact commands.

## Working with the hardware and the physicists

A data acquisition codebase sits between two groups that a software newcomer meets less often than
the software team: the people who build the detectors and the electronics, and the people who use
the data. Both decide things the code implements.

With the hardware team, learn the interface before the implementation: the readout format and its
versions, the link's error behavior, the firmware versions in the field and the ones on the test
bench. A defect at the boundary (a word misread, a counter that wraps) is found only when both
sides look at the same data; Chapter 9's timestamp unwrapping, Chapter 22's register maps and
Chapter 24's interface control document are where MiniDAQ met those boundaries. Ask for time on
a test bench early: a simulator teaches the software, a bench teaches the system.

With the physicists, learn the meaning of the numbers. An energy window, a coincidence window, a
multiples policy, a dead-time model: each was chosen for a reason that lives in a physicist's
notebook or a design review, and each appears in the code as a constant or a configuration value.
When a value looks arbitrary, ask before changing it, and record the answer next to the value.
Acceptance criteria (Chapter 33) come from them and from the system requirements, not from the
software team.

## What this leaves out

This chapter is about the codebase, not about the job. How a team is organized, how work is
planned, how to build the relationships that make the questions above welcome: these matter at
least as much, depend on the organization, and are the subject of other books (M. Watkins' on the
first 90 days in any new role is the classic). A real scanner's codebase is also larger than
MiniDAQ, with more history, more people and more hardware; the method scales, the numbers do not.
And the survey's view of the history is only as good as the history: a repository whose history
was rewritten or squashed, or whose commits mix unrelated changes, tells less.

::: box-regulated
- **Competence and training.** ISO 13485 expects the competence of personnel who affect product
  quality to be determined, and training to be provided and recorded (verify: the standard's
  clause on human resources; assumption: confirm with team). The first 90 days are part of that:
  record what was learned and how competence was confirmed, for instance by the first change and
  problem report taken through the process.
- **Maintenance.** IEC 62304's maintenance process expects modifications to be analyzed for their
  effect on the existing software, the risk controls and the documents before they are made
  (verify: the standard's clauses on software maintenance and problem resolution). The survey, the
  coupling and the characterization tests are ways to do that analysis honestly when you do not
  yet know the code.
- **Behavior is a contract.** A change of observable behavior, even a fix, goes through change
  control with an impact analysis on everything that reads the output; a characterization test
  makes the change visible.
- **The item map is part of the classification.** A file without an item, or with an unclear one,
  has no defined rigor; `check_items.py` and the survey keep the map honest.
- **Records.** CR-0021 (the survey and the two prefixes removed from the map), ADR 0029, TL-43, SRS
  version 23 (SRS-SVY-001 to SRS-SVY-003), the threat model version 9 (reviewed: no new element of
  the running system).
:::

::: box-askteam
1. Is there a written way to build and run the system from a clean checkout? When did someone new
   last follow it, and what was missing?
2. Can the last release's evidence be reproduced on a developer's machine? Who last tried?
3. Which items change most, and which have open problem reports? Does anyone track that?
4. Which files change together across items, and does the architecture say why?
5. Which behaviors of the code look wrong but are relied on by other programs? Where is that
   written?
6. What would be a good first change: small, real, and taken through the whole process?
7. Which item could I own by the end of the third month, and who owns it now?
8. Who decides the physics values in the code, and where are their reasons recorded?
:::

## Exercises {.unnumbered}

**Exercise 34.1 (E): Files that change together.** *Goal:* from `git log --name-only`, list the
pairs of files changed in the same commits, with the number of shared commits and the share of the
less often changed file's commits. *Starter:*
`exercises/ch34/e1_change_coupling/starter/coupling.py`, which counts every pair twice, keeps
commits of any size and ignores `min_shared`. *Acceptance:*
`tests/test_coupling.py` passes: a pair listed once with its shared commits and degree; a commit
above `max_files` adds nothing and does not dilute the degree; pairs below `min_shared` left out
in a fixed order; an empty log gives nothing. Then run it on MiniDAQ's history and explain its most
coupled pair across items. *Time:* 60 minutes.

**Exercise 34.2 (M): Who owns this file?** *Goal:* give every file its software item by the longest
matching prefix, and report what the item map gets wrong. *Starter:*
`exercises/ch34/e2_item_map/starter/item_map.py`, which takes the first match and reports only
unowned files. *Acceptance:* `tests/test_item_map.py` passes: the owner does not depend on the
order of the map; an ambiguous owner raises from `owner` and is listed by `check_map`; shadowed
files, dead prefixes and every item's count, including zero; a file stem claims only files in its
own directory. Then compare with what `tools/survey.py` reports on MiniDAQ. *Time:* 2 hours.

**Exercise 34.3 (M): Pin down what legacy code does.** *Goal:* write characterization tests of a
legacy count-rate function strong enough that each of seven changes, mistakes and well-meant fixes
alike, fails them. *Starter:* `exercises/ch34/e3_characterize/starter/test_characterize.cpp`, two
tests of ordinary values that catch one change of seven. *Acceptance:* the `original` test passes,
`mutant_1` to `mutant_7` each fail, and there are at least eight test cases. Then say which changes
are fixes and why that does not matter to the tests, and where you would record a behavior that
looks wrong. *Time:* 2 hours.

## MiniDAQ milestone: a map for the next maintainer {.unnumbered}

::: box-milestone
**Goal.** A new maintainer of MiniDAQ can see in a second which items matter most, which change,
which have open problems and where the map of the code is unclear; the map has no prefix that
claims nothing. **Start:** tag `ch33`. **End:** tag `ch34`.
:::

1. Write change request CR-0021 and ADR 0029; add SRS-SVY-001 to SRS-SVY-003 (SRS version 23) and
   TL-43 to the tool list; review the threat model (version 9).
2. Add `tools/survey.py`, its tests and the test `tools.survey`.
3. Run the survey on the repository; remove the two prefixes that claim no file from the item map;
   keep the survey and the change coupling in `measurements/ch34/`.
4. Add Exercises 34.1 to 34.3.
5. Bring `HANDOFF.md` up to date as the handover the next maintainer needs.

**Definition of done.** `ci/run_all.sh` is green on all six presets; `tools.survey`,
`docs.trace`, `docs.baseline` (the three new requirements named by CR-0021) and `check_items.py`
pass; the survey reports no unowned file, no ambiguous owner and no dead prefix; every starter of
the chapter fails. Tag `ch34`.

## Check yourself {.unnumbered}

1. What are the four parts of what you take over with a data acquisition codebase, and which of
   them is not in the repository?
2. Why reproduce the last release before the first change? What do you do when you cannot?
3. In which order do you read the documents, and why do the safety classes and the open problem
   reports come early?
4. Why does the survey use the item map's own rule for owners, rather than the directory layout?
5. What is a hotspot, and why commits times size rather than either alone?
6. What did the first survey of MiniDAQ find in the item map, and why did no other check report
   it?
7. What is change coupling, and why does the exercise leave out large commits?
8. Name two reasons two files can be coupled in the history without a dependency in the code.
9. What does a characterization test assert, and what does it not?
10. Why must a well-meant fix fail a characterization test?
11. What do you do with a behavior that looks wrong but that other programs may rely on?
12. What makes a good first change, and why take it through every step of the process?
13. What does it mean to own an item, and what three pieces of work get you there?
14. Which values in a data acquisition codebase belong to the physicists, and how do you treat
    them?

## Summary {.unnumbered}

- Taking over a data acquisition codebase means taking over the product, its evidence, its
  environment and its people and process; data that cannot be acquired again, timing budgets and
  physics decisions make it particular.
- The first phase is to build, run and reproduce the last release; missing steps in the
  instructions are the first useful findings, and the chain end to end is the best introduction.
- Read the documents in the order of the questions: intended use, items and classes, risk,
  requirements, open problem reports, SOUP, release record, decision records.
- `tools/survey.py` (TL-43) puts each item's records beside its history and lists the hotspots;
  on MiniDAQ it ranks the service, the simulator and the sorter first, and its top hotspot is
  `acquisition_service.cpp`.
- The survey checks the item map; its first run found two prefixes that claimed no file (removed
  by CR-0021) and two files owned through a longer prefix inside another item's directory.
- Change coupling shows dependencies the code does not state; on MiniDAQ the configuration's
  interface and the acquisition service always change together.
- Characterization tests pin what legacy code does, so that a change of behavior, a mistake or a
  fix, becomes a decision; a behavior that looks wrong is pinned, reported and decided by its
  owner.
- The first change is real, small and taken through the whole change control; the steps you did
  not know are the onboarding document the team lacks.
- Ownership comes from owning one item, taking a problem report end to end and running a release;
  the questions of every chapter become a checklist, and the handover you write at the end is the
  one you would have wanted.

## Further reading {.unnumbered}

- M. Feathers, *Working Effectively with Legacy Code*, Prentice Hall, 2004: characterization tests,
  seams, and changing code you do not understand.
- A. Tornhill, *Your Code as a Crime Scene*, Pragmatic Bookshelf (2nd edition 2024), and *Software
  Design X-Rays*, Pragmatic Bookshelf, 2018: hotspots and change coupling from version control.
- D. Spinellis, *Code Reading: The Open Source Perspective*, Addison-Wesley, 2003, on reading large
  codebases systematically.
- M. Watkins, *The First 90 Days*, updated edition, Harvard Business Review Press, 2013, on the
  transition into a new role.
- IEC 62304:2006+A1:2015, the clauses on software maintenance and problem resolution; ISO
  13485:2016, the clause on human resources.
- ADR 0029 and CR-0021 in the repository; `HANDOFF.md` as an example of a handover document.
