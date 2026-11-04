# 0032. AI-assisted changes: recorded in trailers, verified like any other change, with a test for each change of product code

Date: 2026-11-04
Status: Accepted

## Context

MiniDAQ and the book about it were written by an author working with an AI coding assistant
(Claude Code): the assistant wrote most of the code, tests, documents and measurements, and the
author directed, decided, reviewed and committed. Chapter 37 is about doing that for medical-device
software. The questions are what the regulated process asks of a change an assistant wrote, how
the assistant itself is treated as a tool, and what to record. IEC 62304 and ISO 13485 do not
mention AI assistants; they ask for verified changes, controlled tools and records.

## Options

1. **Recording.** Nothing (the author is responsible, whoever typed); a note in the change
   request; or a trailer in every commit the assistant helped make (`Co-Authored-By:`), read by
   a tool.
2. **The assistant as a tool.** Out of the tool list (an editor, like any other); or in it, with
   the class its output deserves: T3, since what it writes becomes part of the product.
3. **Validation.** Validate the assistant (test it on a suite of tasks); or validate the process
   around it: review, tests, static analysis, CI, independent review, and a rule that each
   assisted change of product code comes with a test.
4. **The rule.** None; an assisted change of product code must change a test; or must change a
   test or name the tests that cover it.

## Decision

- **A trailer in every commit** (option 1, the third), the record that `tools/ai_provenance.py`
  reads and that the release record summarizes.
- **In the tool list as T3** (option 2, the second, TL-48). An editor writes what the developer
  types; an assistant writes what the developer did not, and that is the property the tool
  classes are about.
- **Validate the process, not the tool** (option 3, the second). The assistant's output varies
  between runs, versions and prompts, so a validation of the tool would be a validation of one
  afternoon. Every change it makes passes the checks any change passes, and the independent
  review of each Part by a separate session is diverse redundancy.
- **A test, or the tests named** (option 4, the third). Six of the nine assisted changes of
  product code without a test were comment and warning fixes, where a new test would be
  ceremony; a `Tests:` trailer makes the author say which tests cover the change, which is what a
  reviewer needs to know.

## Consequences

### Positive

- Which items an assistant changed, and with what evidence, is in the history and in each release
  record; a reviewer can start with the assisted changes of class B items that came without a
  test.
- The rule asks the question at the moment the change is made, when the author still knows the
  answer.

### Negative

- A trailer is the author's statement; an assistant's work committed without it is not found. The
  rule depends on the honesty of the record, as the review trailer does.
- A `Tests:` trailer can name tests that do not cover the change; the reviewer checks it, as the
  reviewer checks a change request a commit names.
- The assistant sends what it reads to its provider: the repository must hold no patient data,
  credentials or confidential documents, which is a rule for people, recorded in the development
  plan and the threat model's gap, not a check.
