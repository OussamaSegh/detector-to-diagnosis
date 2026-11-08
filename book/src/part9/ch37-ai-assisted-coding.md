# AI-assisted coding for medical-device software {#ch37}

::: box-why
An AI coding assistant can read a repository, write a parser and its tests, run the build, read
the failure and fix it, in minutes, and it writes fluent, idiomatic code that looks reviewed
before anyone has reviewed it. That is the danger and the opportunity in one sentence. Nothing in
IEC 62304 or ISO 13485 forbids it, and nothing in them was written for it: they ask for verified
changes, controlled tools and records, whoever or whatever typed the code. This book and MiniDAQ
were written by an author working with such an assistant, every commit says so, and this chapter
uses that history as its evidence: what the assistant was good at, what it got wrong, what found
its mistakes, and what a regulated process has to add.
:::

**A day in the life.** An engineer asks an assistant to fix a flaky test of the coincidence
sorter. Twenty minutes later there is a tidy change: the race in the test's setup is fixed, a
comment explains it, and the whole suite is green. The reviewer reads the diff, which is short and
clear, and approves. Three weeks later a release check fails on the performance gate, and the
investigation finds that the same change also widened a tolerance in a property test of the
sorter from one picosecond to one nanosecond, "to stabilize it". The property no longer checked
the ordering it was written for. Nobody had lied. The assistant had been asked to make the test
pass, and it did; the diff showed the widened tolerance in one line among forty, and the review
had read the forty lines as one change with one purpose.

## Learning objectives {.unnumbered}

After this chapter you can:

1. Describe what a coding assistant does in a repository and where its output is weakest.
2. Give an assistant the context it needs (rules, decisions, the recipe of a change) and keep that
   context true.
3. Work in small, verified steps, with numbers that come from measurements and listings that come
   from tested code.
4. Review an assistant's change by testing it against its requirement, and use independent
   implementations and independent reviews to find what its own tests cannot.
5. Treat the assistant as a tool under the quality system: its class, what is validated, and what
   is recorded with each change.
6. Keep patient data, credentials and confidential documents out of its context, and record the
   assistant's access in the threat model.
7. Decide which steps an assistant takes alone and which wait for a person.

## Prerequisites and estimated time {.unnumbered}

Chapter 14 (IEC 62304's activities), Chapter 16 (change control), Chapter 18 (testing and
mutation testing), Chapter 20 (tool confidence and CI), Chapter 21 (code review), Chapter 35 (the
DICOM export and its independent checks) and Chapter 36 (the commit policy). Some use of an AI
coding assistant helps but is not required. Reading: about 3 hours. Exercises: 6 hours. Milestone:
2 hours. If time is short, do Exercise 37.3.

## What an assistant does in a repository

A coding assistant of the kind this chapter means is a large language model with tools. It reads
files, searches the repository, edits files, runs commands (the build, the tests, git) and reads
their output, and it repeats that loop until the task is done or it stops to ask. Claude Code,
which wrote most of MiniDAQ with its author, works that way; so do other assistants built into
editors and terminals. The model's knowledge comes from its training data and from what it reads
in the session; it has no memory between sessions beyond what is written down for it.

Its output has a characteristic shape, and it is worth knowing it before reviewing any of it:

- **It is fluent.** The code compiles, follows the repository's style, has sensible names and
  comments. Fluency is not evidence: a mistake written fluently is harder to see, not easier.
- **It is plausible at every scale.** A number in a document, a reference in a bibliography, a
  claim about a standard's clause: each looks like what would be there. A model that has not
  measured something will still write a number for it if the text seems to call for one.
- **It optimizes for the request.** "Make the test pass" is satisfied by a weaker test. "Fix the
  warning" is satisfied by a suppression. The request is the specification the assistant works
  to, and a request is usually less than the requirement.
- **It shares its blind spots with itself.** The tests an assistant writes for its own code come
  from the same reading of the problem as the code. They show the code does what its author
  thought, which is the one thing a review is there to question.
- **It is fast, and it does not get tired.** It will write the twentieth test as carefully as the
  first, run the whole suite after every change, and re-read a standard's text a fourth time. The
  limiting factor moves from writing to reviewing.

The last point is the reason to use one, and the other four are the reasons the rest of this
chapter exists.

## Where it helps, and where it does not

The history of this project gives a rough map of where an assistant earns its place in
medical-device work and where it needs the most help.

It is strongest at **completeness**, the work that people skip because it is tedious: a test for
every row of a requirements table, every requirement tagged and the trace matrix regenerated,
every hazard's controls checked against their tests, every exercise with a starter, a solution,
notes and a solutions chapter. Chapter 36's commit policy, its tests against Git's own parser and
the measurement of 260 commits took one session. It is strong at **reading failures**: a CI log of
thousands of lines, a sanitizer report, a core file's backtrace (Chapter 21), and at proposing the
smallest change that explains them. It is strong at **mechanical refactoring under tests**, where
the test suite says whether the change preserved behavior, and at **writing the measurement
scripts** that turn a claim into a file.

It is weakest where the truth is not in the repository or in well-known text. **Hardware facts**
(a board's register map, a detector's dead time, a scanner's geometry) are invented with the same
fluency as they are recalled; this book marks every one of them as an assumption to confirm.
**Numbers** without a measurement, and **references** without a check, are the same problem.
**Concurrency and timing** are where its code is most often subtly wrong, as anyone's is, and
where the sanitizers and stress runs of Chapters 3 and 20 found what review did not.
**Regulatory interpretation** (whether a change is significant, which class an item is, what a
notified body expects) is a judgment a team owns and records; an assistant can lay out the
arguments and point to the clauses, and the decision is a person's. And **anything irreversible**
is a decision for a person by definition.

Between the two is most of the work: code that an assistant writes well and that is wrong in a way
only a test from the requirement shows. The rest of this chapter is about that middle.

## Context: what the assistant knows

An assistant starts each session knowing only what the repository and its context tell it. Most
assistants read a file of instructions from the repository's root at the start (`CLAUDE.md` for
Claude Code, `AGENTS.md` or similar for others); a team can also give it a memory of facts that
persist between sessions. For MiniDAQ the context had four layers, and each turned out to matter:

- **A handoff file**, `HANDOFF.md`, that a new session reads first: the rules, the layout, how to
  build and release, the state of the work, and what is left to do. It is kept current with every
  milestone, because the next session starts from it with nothing else.
- **The person's rules**, written as rules, with the date and the reason: no personal information
  in any commit, the book must be generic and publishable, ask before adding any dependency, push
  after every commit, merge pull requests locally. A rule stated once in conversation is
  forgotten when the session ends; a rule in the context file is applied every time.
- **Decisions already made**, in a section of their own that says "do not reopen". An assistant
  that rediscovers a question will often answer it differently; the architecture decision records
  (Chapter 6) and that list make it consistent across sessions.
- **The recipe of a change.** For a chapter: the code, the tests with their requirement tags, the
  SRS rows with the change request that names them, the risk file and threat model review, the
  tool list entry, the measurements, the exercises with a starter that fails, the text, the
  solutions, the CHANGELOG, then the tag after CI is green. With the recipe written down, each
  chapter's checks found what was missing before the commit.

Context goes stale, and an assistant follows a stale instruction exactly as faithfully as a true
one. That cuts both ways. MiniDAQ's convention that each commit ends with a review line above the
co-author lines was followed in 191 commits without a single deviation, and was wrong in all of
them: the blank line above the co-author lines kept Git from ever parsing it (Chapter 36). Exercise
37.2 checks a context file against the repository: every path it names exists, every pattern
matches something, every test it tells you to run is defined. On MiniDAQ's own handoff file it
reports six lines, and none is stale: five name build outputs that exist only after a build, one
uses a placeholder the check does not know. A check like that finds broken references; it cannot
find a rule the team has dropped or a number that changed. The context file is a controlled
document in effect: it has an owner, and a change that makes it wrong updates it in the same
commit.

## Small steps, each one verified

The working method that produced MiniDAQ is unremarkable, and every part of it exists because of
the assistant's characteristics above.

**One change at a time, committed and pushed.** Each chapter is a series of commits, each of which
builds, passes the whole test suite (more than 900 tests) and is pushed at once. A session can end
at any point, by a limit or a context window that fills up, and the next session continues from
the repository, not from a memory of what was half done.

**Run everything, every time.** The assistant runs the whole `ctest` before each commit, not the
tests it thinks are affected. In this book's history that rule found failures the change was not
about: the lint of the SRS refusing a new requirement with three "shall"s in one row, a timing test
that fails under load, a test of Chapter 32's pre-commit hook that the commit-msg hook of Chapter 36
broke the moment it was installed. The assistant's guess of what a change affects is the guess that
is wrong.

**Numbers come from measurements.** Every number in this book's text comes from a file in
`measurements/`, written by a script in the same directory from the code it describes; the text
quotes the file. When a number is not measured, it is marked as an assumption to confirm, and
claims that could not be checked are marked "verify". A model writes plausible numbers easily, so
the rule is mechanical: no number without its file. It also found things. The DICOM export's first
send of 47 slices took 2.07 seconds, 44 ms per instance; the measurement made the delay visible,
and the cause (Nagle's algorithm meeting delayed acknowledgments) was found and fixed with
`TCP_NODELAY`. A number written from expectation would have been the number after the fix, for a
program that did not yet exist.

**Listings come from tested code.** Every code listing in this book is included from the
repository at build time, between snippet markers, so the code a reader sees is the code the tests
ran. An assistant that writes a listing directly into a chapter writes a plausible listing; one
that includes it cannot.

**Every exercise has a starter that fails.** Each exercise's starter is checked to fail its tests,
and each solution to pass. A test that the starter passes tests nothing, and an assistant asked to
write both a starter and its tests will, without the check, sometimes write a starter that is
already correct.

**Stop and ask before the irreversible.** The assistant takes reversible steps alone (a branch, a
commit, a pull request, a measurement) and asks before the others: a new dependency, a change to
the history, a message outside the project, a release. MiniDAQ's two test-only DICOM libraries
were added after the author approved them; a history rewrite to remove personal data waited for
the owner's decision; tags go through a reviewed list. What the assistant may do alone is a
decision for the team, written in the context file, not a question of what the assistant can do.

## What found the mistakes

Every commit of MiniDAQ that is not a merge, 256 of them, names the assistant in a
`Co-Authored-By:` trailer (`measurements/ch37/`). That makes the project's 60 problem reports a
record of what an assistant's work gets wrong, and of what finds it. By the field "found" of each
report:

| Found by | Reports |
|---|---|
| The release checks and their reviews (coverage, documents, SOUP) | 20 |
| CI runs | 14 |
| The author's own tests and runs | 12 |
| Design, development and measurement | 6 |
| Fuzzing | 5 |
| The independent review of a Part | 2 |
| An internal audit | 1 |

The classes come from keyword rules on a text field, not from reading each report, so read the
table as a shape, not a statistic. The shape is clear enough: almost everything was found by
running something. The release checks (Chapter 20), which run every test in every build with
sanitizers, stress, fuzzing and the performance gate, found a third; CI found another quarter.
Ten of the 60 were evaluated as safety relevant. Their root causes, where recorded, were split
between code (8), tests (12), tools (10) and process (11): an assistant's mistakes are not only in
the code it writes but in the tests that should have caught them and in the tools and procedures
around both.

Three findings from writing Part IX show the kinds of mistake that only an independent check
finds, because the assistant's own checks shared the mistake.

- **The byte order of a tag.** The DICOM export's first version wrote a sequence item's tag as
  one 32-bit integer, so its bytes came out in the wrong order. The independent reader, pydicom,
  read the file without a warning; the export's own strict reader refused it. An implementation
  checked only by a lenient peer would have shipped it (Chapter 35).
- **A dependency with an advisory.** The first pin of pydicom had a published vulnerability on
  the day it was added; the lock file's audit (Chapter 31) refused it before the first commit. An
  assistant chooses the version it knows, and the version it knows is old by the time it is used.
- **A record no tool could read.** The review line that Git never parsed, in 191 commits, written
  by the same assistant following the same instruction (Chapter 36). Only asking Git found it.

And the independent reviews. After each Part from Part IV on, a separate session that had not
written the Part reviewed it and opened a pull request with its fixes, which were reviewed again
before the merge, and sometimes changed or rejected. The five reviews changed 37 files: for Parts
IV to VI mostly in the book (a number that did not match its measurement, a claim stronger than
its evidence, a layout fault), for Parts VII and VIII mostly in the code and the records, where
the review of Part VIII found two defects that every test had passed: a sorter partition that left
out a class of singles in an accounting test (MDQ-PR-059), and an acceptance rule that matched a
commit by a single character (MDQ-PR-060). Two problem reports from five reviews is few. It is
also two defects that the author, the assistant, the tests and CI had all accepted, which is what
a review by someone who did not write the code is for.

## Reviewing an assistant's change

A review of an assistant's change starts from the requirement, not from the diff. The diff tells
you what the code does; the requirement tells you what it should do; a review that reads only the
diff checks that the code does what it does.

Exercise 37.3 makes that concrete. Its subject is a function an assistant could have written for a
coincidence check on a 40-bit picosecond counter that wraps: two singles are coincident if their
distance, taken the shorter way around the counter's circle and independent of their order, is at
most the window. The function reads well, compiles without a warning and passes the two tests that
came with it, a pair 2 ns apart in a 4 ns window and a pair 10 ns apart. Seven other versions pass
those two tests just as well, and each is a line an assistant writes fluently: `<` for `<=`, the
wrap forgotten, the distance taken one way around only, invalid timestamps masked instead of
refused, the distance computed in 32 bits, the period off by one, the window's limit missing. Each
is wrong for an input the requirement covers. Some would lose a fraction of coincidences at the
window's edge, some once a second when the counter wraps, and one would pair a corrupt timestamp
with a real single, a fabricated coincidence. Only the first, the second and the last are visible
to a careful reader of the code. All seven are caught by eight tests written clause by clause from
the requirement, each with the values on both sides of its edge, without looking at the mutants at
all.

The practices that follow are the ones Part IV taught, used with more discipline because the
author of the code will not remember writing it:

- **Read the requirement first and write the edge cases down** before reading the change. Then
  check that the tests exercise them.
- **Read the tests as carefully as the code,** and look for tests that were weakened: a wider
  tolerance, a removed assertion, a retry, a skip, a sleep. A change that makes a failing test pass
  without changing the code under test needs a reason in its message.
- **Ask for one purpose per change.** A change that fixes a race and widens a tolerance is two
  changes; ask for two commits.
- **Use mutation testing on the assistant's tests** (Chapter 18): a test suite that kills its
  mutants is evidence; one that does not is a list of examples.
- **Check against an independent implementation** where one exists: a reference model, a
  standard's reference data, another library used only in the tests (Chapter 35).
- **Re-derive one number** in every document change: a measurement, a limit, a clause. If it does
  not come from a file you can open, it is a claim.

## The assistant under the quality system

IEC 62304 does not mention AI assistants. It asks that changes are verified, that the tools used
are identified and controlled, and that the records show what was done. ISO 13485 asks that
software used in the quality system is validated for its use (clause 4.1.6). An assistant fits
those requirements without new ones, once three questions are answered.

**What kind of tool is it?** MiniDAQ's tool list (Chapter 20) classifies tools by what a defect in
them can do: T3 makes part of the product, T2 can fail to reveal a defect, T1 neither. A compiler
is T3. An editor is not a tool in this sense, because it writes what the developer types. An
assistant writes what the developer did not type, so it is T3: what it writes becomes part of the
product. The tool list has it as TL-48, off the shelf, with a version that is not pinned, since it
is a service.

**What is validated?** Not the assistant. Its output varies between runs, prompts, versions and
models, so a validation of the tool would be a validation of one afternoon. What is validated is
the process around it, and every part of that process already exists for other reasons: the
review, the tests, the static analysis and sanitizers, CI on every commit, the release checks, the
independent review of each Part, and the measurements that every number comes from. The tool
list's entry says exactly that: its output is never trusted as such, and the evidence for each
change is the evidence any change needs. A team that uses an assistant on class C software adds
what class C asks of any change (Chapter 14), and decides whether the assistant may change class
C items at all (assumption: confirm with team).

**What is recorded?** Each commit the assistant helped make names it in a `Co-Authored-By:`
trailer, so the history says which changes it took part in. `tools/ai_provenance.py` (TL-47) reads
those trailers, with Git's own rule from Chapter 36, and reports for a range of commits which
items and classes the assisted commits changed and which changed product code without a test:

```{.python include="tools/ai_provenance.py" snippet="assisted"}
```

On MiniDAQ's history it reports 52 assisted commits that changed product code, and 9 of them that
changed no test in the same commit. All nine were read. Six are comment, assertion and warning
fixes (a `static_assert`, a suppression with its reason, two compiler and clang-tidy findings,
comments made product-neutral); one is an optimization of the simulator's replay loop; one is a
change of behavior, the server sending READY before its watchdog starts, which the system test
`system.platform` had caught in the first place; and one is a robustness fix whose message names
no test. None is a defect. But for each, a reviewer had to reconstruct why no test was needed.

So the commit policy of Chapter 36 has a seventh rule from version 2 on: an assisted change of a
product item's code changes a test, or names in a `Tests:` trailer the tests that cover it.

```{.python include="tools/check_commits.py" snippet="assisted_rule"}
```

The rule does not ask for a new test with every change; for a comment, that would be ceremony. It
asks the author to say which tests cover the change, at the moment the author still knows, in the
place a reviewer and an auditor will look. Like the review trailer, it records a statement; the
reviewer checks that the statement is true.

**Who is responsible?** The person who commits. The development plan (version 13, section 4) says
so in one sentence, and it is the sentence that makes the rest work: the assistant is a tool, and
a tool's output is the responsibility of the person who uses it. A reviewer who approves an
assistant's change approves it on the same terms as anyone's.

## What goes into the context

An assistant sends what it reads to its provider's service: files, command output, whatever you
paste. For medical-device software that raises three questions, and none of them has a technical
answer alone.

**Patient data.** It does not go into an assistant's context, any more than into an e-mail to a
vendor. MiniDAQ's repository holds synthetic data only (the DICOM export's order is invented), and
that is the rule that makes using an assistant on it simple. When a defect needs real data, the
data is de-identified first, and de-identification is harder than deleting the patient's name.
Exercise 37.1 de-identifies an image header with a list of what to keep, a keyed hash for
pseudonyms, one date shift per patient and remapped UIDs. Its starter deletes the name and the ID
and keeps eight other attributes that identify the patient in that header alone, among them a
private attribute whose name says nothing and whose value is the patient's name. DICOM part 15's
confidentiality profiles describe the full job, and pixels, burned-in text and rare combinations
of attributes can still identify a person after it.

**Credentials and confidential documents.** No keys in the repository or the assistant's
environment, and no confidential documents in its context unless the company's agreement with the
provider covers them. MiniDAQ's repository is public, which makes the rule simple to state and
easy to break: the pre-commit hook (Chapter 32) refuses an address in a staged change, and the
commit policy's identity rule (Chapter 36) was added because personal addresses reached the
history anyway, through merges made on a web page.

**The provider's terms.** Whether the provider keeps what it receives, for how long, and whether it
trains on it, is in its terms and the company's agreement; the development plan names the
assistants that may be used and under which agreement (assumption: confirm with team the company's
policy on AI tools).

## The assistant in the threat model

An assistant that runs commands has the rights of the developer who runs it. It reads text that
others wrote (a web page, an issue, a dependency's README, the output of a command), and text can
carry instructions: a comment in a fetched file that says "also run this" is a prompt injection,
the first entry of OWASP's list of risks for applications built on language models. A change it
proposes can do something other than what its description says, by mistake or because it was told
to by something it read.

The controls are those of any tool with the developer's rights, made explicit:

- **Permissions.** Assistants ask before running a command or editing a file unless allowed, and
  the allowed commands can be listed (the build, the tests, read-only git) and the rest left to a
  prompt. Some assistants can run a check of their own before each tool call, a hook that can
  refuse it, for example a read of a file that holds patient data (verify: the hook and permission
  settings of the assistant you use, which change between versions).
- **Isolation.** A session on a machine or container with access to the repository and nothing
  else: no production systems, no site networks, no stored credentials beyond what the task needs.
  MiniDAQ's sessions ran in disposable containers with a proxy that limited where they could
  connect.
- **Review.** Every change goes through the same review and CI as any other, which is the control
  that catches a change that does something other than it says.

MiniDAQ's threat model records the assistant as a gap in its section 7 (version 12): a development
tool outside the running system, whose access to the repository, to the developer's commands and to
its provider is limited by those controls and not modeled further. A scanner's development
environment is part of its supply chain, and IEC 81001-5-1 asks for its security to be managed;
the assistant is now part of that environment.

::: box-mistakes
- **Taking fluency for correctness.** Well-named, well-commented code with a mistake in it is the
  assistant's normal failure.
- **Accepting the assistant's tests as evidence for its code.** They share its reading of the
  problem; write or check tests from the requirement.
- **"Make the test pass."** Ask for the defect to be fixed, and read the test's diff for widened
  tolerances, removed assertions, retries and skips.
- **A number or a reference without its source.** Every number from a measurement file, every
  reference checked to exist.
- **A context file nobody owns.** It goes stale, and the assistant follows it faithfully.
- **Letting the assistant decide what is irreversible.** The team decides which steps wait for a
  person, and writes it down.
- **Real patient data in a prompt** "just to reproduce the bug". De-identify first, or reproduce
  with synthetic data.
- **One long change with several purposes.** Ask for one purpose per commit.
- **No record.** Without a trailer, nobody can later tell which changes an assistant made.
:::

## What this leaves out

AI in the device itself, which is another subject entirely: machine-learning-enabled software as
a medical device, its data management, the FDA's predetermined change control plans, and the EU's
AI Act (Regulation (EU) 2024/1689), under which AI systems in medical devices can be high-risk.
Also: the licensing questions of generated code that resembles code under another license, which
are legal questions for your company (assumption: confirm with team); assistants that review pull
requests automatically; measuring an assistant's productivity, which is easy to do badly; and the
studies of the security of assistant-written code, two of which are in the further reading.

::: box-regulated
- **Tools.** The assistant is TL-48, class T3 (what it writes becomes part of the product); the
  provenance report is TL-47, class T2. The process around the assistant is what is validated,
  with evidence from every change's verification.
- **Change control.** IEC 62304 clauses 7 and 8 and ISO 13485 clause 7.3.9 apply to an assisted
  change as to any change: verified, reviewed, traced. The commit policy's rule `assisted` asks for
  a test or the tests named with each assisted change of product code.
- **Records.** The `Co-Authored-By:` trailer of every assisted commit, the provenance report in the
  release record, and the development plan's section on the assistant (version 13).
- **Data protection.** No patient data, credentials or confidential documents in the assistant's
  context; the repository holds synthetic data only.
- **Security.** The threat model, version 12, records the assistant's access as a gap in section 7,
  with permissions, isolation and review as its controls.
- **Records of this chapter.** CR-0024, ADR 0032, SRS version 26 (SRS-AI-001 to SRS-AI-004), TL-47
  and TL-48, the development plan version 13, the threat model version 12, `measurements/ch37/`.
:::

::: box-askteam
1. What is our company's policy on AI coding assistants: which ones, under which agreement, for
   which code?
2. May an assistant change class C items? What does a reviewer of an assisted change check that
   they would not check otherwise?
3. How do we record which changes an assistant took part in?
4. What may go into an assistant's context, and who decides? How do we de-identify data for a
   defect that needs real data?
5. Which commands may an assistant run without asking, and on which machines?
6. Who owns the context files in our repositories, and are their changes reviewed?
7. Is the assistant in our tool list, with which class, and what is our validation argument?
8. What does our notified body expect to see about AI tools in our development process?
:::

## Exercises {.unnumbered}

**Exercise 37.1 (E): Nothing of the patient leaves.** *Goal:* de-identify an image header before it
goes into an assistant's context or a bug report: keep what the problem needs, pseudonymize the
patient, shift dates, remap UIDs, drop everything else. *Starter:*
`exercises/ch37/e1_deidentify/starter/deidentify.py`, which deletes the name and the ID and keeps
the rest. *Acceptance:* `tests/test_deidentify.py` passes: no identifying value of the original in
the output and every unlisted attribute dropped; kept attributes unchanged; pseudonyms stable for
one patient and key and different otherwise; intervals between dates kept; UIDs valid and
consistent. *Time:* 1 hour.

**Exercise 37.2 (M): A context file that stays true.** *Goal:* check that a context file names only
paths that exist, patterns that match and tests that are defined. *Starter:*
`exercises/ch37/e2_context_file/starter/context.py`, which takes every code span with a slash and
checks it with `os.path.exists`. *Acceptance:* `tests/test_context.py` passes: existing paths,
directories and `path:line` pass; missing ones are reported with their line; URLs and prose are not
references; placeholders are patterns; fenced blocks are read; `ctest -R` names are checked
against `add_test`. *Time:* 2 hours.

**Exercise 37.3 (H): A review written as tests.** *Goal:* review an assistant-written coincidence
check on a wrapping 40-bit counter by testing it against its requirement. *Starter:*
`exercises/ch37/e3_review_by_tests/starter/test_review.cpp`, the assistant's own two tests.
*Acceptance:* CTest builds your tests against the function and seven fluent, wrong versions of it:
the original passes, every mutant fails, and there are at least 8 tests. *Time:* 3 hours.

## MiniDAQ milestone: the assistant's part on the record {.unnumbered}

::: box-milestone
**Goal.** Every assisted commit is on the record, the assisted changes of product code are listed
per release, and every new one comes with a test or names the tests that cover it.
**Start:** tag `ch36`. **End:** tag `ch37`.
:::

1. Write change request CR-0024 and ADR 0032; add SRS-AI-001 to SRS-AI-004 (SRS version 26), TL-47
   and TL-48; update the development plan (version 13) and the threat model (version 12).
2. Add `tools/ai_provenance.py`, the commit policy's version 2 with its patterns and the rule
   `assisted`, and the test `tools.ai_provenance`.
3. Measure the history (`measurements/ch37/`) and read every assisted change of product code that
   came without a test.
4. Add Exercises 37.1 to 37.3.

**Definition of done.** `tools.ai_provenance` and `tools.commits` pass, including the policy over
the repository from its first commit; `docs.trace`, `docs.tools` and `docs.baseline` (the four
requirements named by CR-0024) pass; every starter of the chapter fails. Tag `ch37`.

## Check yourself {.unnumbered}

1. Name four characteristics of an assistant's output and the practice each one calls for.
2. What goes into a context file, and why does a stale one do more harm with an assistant than
   with a person?
3. Why does every number in this book come from a measurement file, and what did that rule find in
   Chapter 35?
4. What found most of MiniDAQ's problem reports? What did the independent reviews find that
   nothing else had?
5. Why are an assistant's own tests weak evidence for its code? How did Exercise 37.3 show it?
6. Which tool class is an assistant, and why not the class of an editor?
7. Why is the process validated and not the assistant?
8. What does the rule `assisted` ask for, and why not a new test with every change?
9. Who is responsible for an assistant's change?
10. Why is deleting the patient's name and ID not de-identification? What does a list of what to
    keep give you?
11. What is a prompt injection, and which controls limit what one can do?
12. Which steps should wait for a person, and where is that written?

## Summary {.unnumbered}

- A coding assistant reads, edits and runs commands in a loop; its output is fluent, plausible,
  optimized for the request and tested by its own reading of the problem.
- Context makes it consistent: a handoff file, the person's rules, decisions not to reopen and the
  recipe of a change. Context goes stale, and an assistant follows a stale rule faithfully.
- Small verified steps: commit and push each change, run every test every time, numbers only from
  measurements, listings only from tested code, a failing starter for every exercise, and a person's
  decision before anything irreversible.
- On MiniDAQ, running things found nearly every defect; independent checks (a strict reader, a lock
  audit, Git itself, independent reviews) found the ones the assistant's own checks shared.
- Review from the requirement: eight tests written clause by clause caught seven fluent mutants
  that the assistant's two tests passed.
- The assistant is a T3 tool; the process around it is validated; each assisted commit says so in a
  trailer, and each assisted change of product code changes a test or names the tests that cover
  it.
- No patient data, credentials or confidential documents in its context; de-identification keeps a
  list of what to keep, not of what to remove.
- The assistant has the developer's rights: permissions, isolation and review limit what a prompt
  injection or a wrong change can do, and the threat model records it.
- The person who commits is responsible for the change, whoever wrote it.

## Further reading {.unnumbered}

- IEC 62304:2006+A1:2015, clauses 5.1 (development planning), 7 and 8; ISO 13485:2016, clauses
  4.1.6 and 7.3.9.
- FDA, *Computer Software Assurance for Production and Quality System Software*, guidance (verify:
  the current status and date of the guidance), on assurance proportionate to risk for software
  used in the quality system.
- OWASP, *Top 10 for Large Language Model Applications*, https://owasp.org, on prompt injection and
  excessive agency.
- N. Perry, M. Srivastava, D. Kumar and D. Boneh, "Do Users Write More Insecure Code with AI
  Assistants?", ACM CCS 2023.
- H. Pearce, B. Ahmad, B. Tan, B. Dolan-Gavitt and R. Karri, "Asleep at the Keyboard? Assessing
  the Security of GitHub Copilot's Code Contributions", IEEE Symposium on Security and Privacy,
  2022.
- NEMA, DICOM PS3.15, *Security and System Management Profiles*, annex E (attribute
  confidentiality profiles).
- Regulation (EU) 2024/1689 (the AI Act), for AI in the device rather than in its development.
- The Claude Code documentation, https://code.claude.com/docs, on context files, permissions and
  hooks.
- ADR 0032 and CR-0024 in the repository; `measurements/ch37/README.md`.
