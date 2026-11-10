# Git and the workflow of a regulated team {#ch36}

::: box-why
A regulated team does not keep its history for its own convenience. The change request names the
commits that implemented it, the release record names the commit the release was built from, the
review record says who looked at a change and against which checklist, and an auditor may ask for
any of them years later. In most teams all of that lives in Git, or points into it. Git is very
good at keeping content and very indifferent to what the content means: it will store a commit
whose message says "fix", made under any name anyone typed, merged in a way that drops the
commits a change request lists. This chapter treats the history as a record, measures MiniDAQ's
own against a policy, and finds that a line written in 191 commits as the record of review was
never read by Git at all.
:::

**A day in the life.** An auditor picks a requirement at random: the coincidence window of
release 2.3. The change request that changed it names two commits. The first is not in the
repository; the branch it was on was rebased before it was merged, and the commit that reached
`main` has another name. The second is a squash merge made on the hosting service's web page, with
the message "Sorter fixes (#212)" and, as its author, the personal address of an engineer who left
two years ago. The review discussion was on the pull request, on a service the company has since
left. The team can show that the code is right, by testing it. It cannot show, from its own
records, that the change was reviewed before it was released. Each step was normal Git usage; the
team had simply never written down what the history must prove, and never checked it.

## Learning objectives {.unnumbered}

After this chapter you can:

1. Explain what a commit is (a snapshot named by its content, with its parents) and what its name
   proves and does not prove.
2. Choose a branching model for a team that maintains released versions, and say what each way of
   integrating a branch (merge, rebase, squash) does to the record.
3. Merge three versions of a file, recognize a conflict and say why a clean merge still needs the
   tests.
4. Write commit messages that both people and tools can read, with trailers that Git parses.
5. Write a commit policy, check a range of commits against it in a hook and in CI, and decide
   where the policy should begin.
6. Trace a commit to the change request or problem report it implements at the level of a
   requirement, not of a file.
7. Say what identity, signatures and protected branches add, and what remains a matter of the
   team's process.

## Prerequisites and estimated time {.unnumbered}

Chapter 16 (change control and the design and development file), Chapter 20 (CI as evidence),
Chapter 21 (code review and bisecting) and Chapter 34 (reading a codebase through its history).
Daily use of Git: commit, branch, merge, push. Reading: about 3 hours. Exercises: 6 hours.
Milestone: 2 hours. If time is short, do Exercise 36.3.

## What a commit is

Git stores four kinds of objects, each named by the hash of its content. A **blob** is the content
of a file, without its name. A **tree** is a directory: for each entry, a mode, a name and the name
of a blob or of another tree. A **commit** is a tree (the whole snapshot of the project), the names
of its parent commits, an author, a committer, each with a time and a time zone, and a message. A
**tag** object names another object, usually a commit, with its own message and tagger. That is
nearly all of Git's data model; branches are only files that hold the name of a commit, and they
move.

The name of an object is the SHA-1 of a short header (its type, a space, its size in bytes and a
zero byte) followed by its content. You can compute it yourself:

```python
import hashlib
data = open("VERSION", "rb").read()
print(hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest())  # = git hash-object VERSION
```

The measurement of this chapter does exactly that for MiniDAQ's `VERSION` file and gets the name
`git hash-object` prints; changing one bit of the file changes all 20 bytes of the name
(`measurements/ch36/`). A tree's content holds the names of its entries, and a commit's content
holds the name of its tree and of its parents. So the name of a commit stands for every byte of
every file in that snapshot and, through its parents, for every commit before it. Change one byte
of one file anywhere in the past and every later commit gets another name. Exercise 36.2 builds
blob, tree and commit names by hand and checks them against `git hash-object`, `git mktree` and
`git commit-tree`; the details that make an implementation wrong are small (the order of entries
in a tree, a directory's mode written as `40000`, the binary form of the names), which is a reason
to test it against Git.

This is why a release record that names a commit is a strong record: anyone with the repository
can check out that commit and get exactly the files the release was built from, and anyone can
tell when a history has been rewritten, because the name no longer resolves or resolves to
something else. MiniDAQ's release records name a full commit name; its change requests name
abbreviated ones, at least seven characters, which `docs.changes` resolves in the repository.

A name proves less than it seems to. It proves *which content*. It does not prove who wrote the
commit (the author and committer fields hold whatever the maker's configuration said), when (the
times are the maker's clock and can be set at will), or that anything was reviewed or tested. And
SHA-1 is no longer collision resistant: in 2017 a team from CWI Amsterdam and Google published two
different PDF files with the same SHA-1. Git has used a hardened SHA-1 that detects such constructed
collisions since version 2.13, and it can create repositories named with SHA-256 (`git init
--object-format=sha256`); support for those on hosting services has lagged, so check the service
your team uses. Integrity against accidents is what the names give you; integrity against an
adversary needs signatures, which come later in this chapter.

Figure [](#fig-ch36-objects) draws the objects behind one commit.

```{.figure #fig-ch36-objects src="book/figures/tikz/ch36/objects.tex" caption="What a commit is. A commit names a tree and its parent; trees name trees and blobs; every name is a hash of the content, so one changed bit renames everything above it." alt="A commit box, 34cf130 with author and message, points to its parent commit and that one to its parent. The commit also points to the root tree, which holds a docs tree and the blobs VERSION, c70836ca5cf3, and README.md; the docs tree holds sdp.md. A note gives the hash of the VERSION blob and says one changed bit changes all 20 bytes of its name, and the names of the tree and commit above it." width="90%"}
```

## The history as a record

ISO 13485 asks for records that stay legible, identifiable and retrievable, and for their changes
to be identifiable; IEC 62304 asks for configuration management (clause 8): identify each
configuration item and its version, control changes to them, and keep a history from which you
can tell what went into each release. A Git repository does most of the mechanical work if you
let it. What it cannot do is decide what the history should prove. For MiniDAQ the answer is in
four places:

- **Change requests** (Chapter 16) list, in their field `Commits`, the commits that implemented
  them. `tools/check_changes.py` checks that those commits exist.
- **Release records** (Chapter 20) name the commit the release was built from, and the annotated tag
  `book-v0.8.0` names the same one. Every chapter and release tag in MiniDAQ's repository is an
  annotated tag (43 of 43 when measured), which carries its own message and tagger; a lightweight
  tag is only a name.
- **The review record.** MiniDAQ's procedure asks that every change be reviewed against the change
  control checklist, and every commit message has carried the line
  `Review: change control checklist, items 1 to 6.` as the record that it was.
- **Problem reports** (`docs/regulatory/problem-reports.json`) name the commits that fixed them.

The record has one rule that matters more than all the others: **a published history is not
rewritten.** Every name above points into it. A rebase, an amended commit or a filter of the whole
history makes new commits with new names, and every change request, release record and tag that
named the old ones now names nothing. MiniDAQ's own history was rewritten once, early, to remove
personal data from it, and 188 commit names cited in its documents had to be remapped in the same
operation, with a script, a review and a check from a fresh clone that every cited name resolved.
That is what a rewrite costs a project with a few hundred commits and no customers. It is sometimes
necessary (a secret or personal data committed by mistake), and then it is a change with a change
request, an impact analysis that lists every record that names a commit, and a decision by someone
who can make it.

Short of that, a mistake in a published commit is corrected by another commit. `git revert`
makes a commit that undoes an earlier one and names it in its message; the earlier commit stays,
with its review record, and so does the record that it was undone.

## Branches and the shape of the work

A branching model is the team's answer to two questions: where does finished work go, and where
do fixes for released versions go?

**Trunk-based development** answers the first with one main branch. Each change is a short-lived
branch, reviewed and merged within a day or two; the main branch is always releasable, and CI
runs on every merge. Long-lived feature branches are avoided because they diverge: the longer a
branch lives, the larger its merge and the less its review covered what the merged code does.

**Release branches** answer the second. When version 2.3 is released and installed at sites,
someone will need 2.3.1 with one fix and nothing else from the main branch. The usual practice:
make the fix on the main branch first, through the normal review; then create a branch
`release/2.3` from the release's tag, if it does not exist, and bring the fix over with
`git cherry-pick -x`. The `-x` adds a line `(cherry picked from commit ...)` to the message, which
is the trace from the copy to the original. The release branch gets its own CI, its own release
checks and its own release record. A fix that cannot be made on the main branch first (the code
has changed too much) is a separate change with its own review, and the change request says why.

**Git flow**, with its develop, feature, release and hotfix branches, is a fuller version of the
same idea, designed for products released on a schedule. Its extra branch between features and
the main branch adds a merge and a place for work to wait; many teams that ship from one main
branch do without it. Which model your team uses matters less than that it is written down in the
development plan and that the history can be checked against it.

MiniDAQ is the simplest case: one main branch and no maintained release, since every release so
far was the next development step. Each Part's independent review (Chapter 37) was a branch with a
pull request, merged into `main` with `git merge --no-ff`, so that the merge commit marks where
the review's work entered. The measurement counts 260 commits, 6 merges, and 249 commits on the
first-parent line of `main`: the line you get by following only the first parent of each merge,
which is the sequence of states `main` was actually in. `git log --first-parent` and
`git bisect --first-parent` (Chapter 21) walk that line, and on a history where every first-parent
commit passed CI, a bisection on it never lands in the middle of someone's unfinished branch.

## Merging, rebasing and squashing

There are three ways to bring a reviewed branch into the main branch, and each leaves a different
record.

- **A merge commit** keeps every commit of the branch with its name and adds a commit with two
  parents. Every name a change request cites stays valid; the history is less tidy.
- **A rebase** replays the branch's commits on top of the main branch, as new commits with new
  names, and the main branch then moves forward to them. The history is a line. Any commit name
  that was cited before the rebase (in a change request written during the review, in a CI log, in
  a reviewer's comment) is gone.
- **A squash** makes one new commit with the combined change and discards the branch's commits.
  The history is short, and everything the branch's commits said about themselves (which commit
  fixed which review finding) is reduced to one message.

None is wrong in itself. What is wrong is choosing one after records already name the commits it
will discard. A team that rebases or squashes writes the change request's commits after the merge,
from the main branch; a team that cites commits during review merges. MiniDAQ merges, and writes
the field `Commits` when a change request is implemented.

Figure [](#fig-ch36-integrate) puts the three side by side.

```{.figure #fig-ch36-integrate src="book/figures/tikz/ch36/integrate.tex" caption="Three ways to bring a branch to main. A merge keeps the branch's commits and their names; a rebase rewrites them; a squash folds them into one." alt="Three panels, each with main and a branch of two commits a and b. Merge: a merge commit M with two parents, and a and b keep their names. Rebase: new commits a prime and b prime on top of main, so every cited name of a and b is gone. Squash: a single commit ab on main whose one message merges what a and b said." width="100%"}
```

Whichever way you integrate, Git has to combine changes, and it does that file by file with a
**three-way merge**. It finds the merge base (the last commit both sides share), and for each file
compares the base with each side. Where only one side changed a region, it takes that side; where
both made the same change, it takes it once; where both changed the same region differently, it
stops and writes a **conflict**, both versions between markers, for a person to resolve.

Exercise 36.3 writes that merge for lines. Its starter compares the three files line by line at
the same index and lets the side that changed win, which works for a change of one line in place
and is wrong the moment one side inserts or deletes a line: every later line is compared with the
wrong line, and the merged file is silently nonsense. The solution uses a diff of the base against
each side to find the lines both sides kept; between two such stable lines, the four cases above
decide. Two cases surprise people. Changes of two **adjacent** lines conflict, even though neither
side touched the other's line, because no unchanged line separates them; and a **clean** merge is
not a correct program. If one side renames a function and the other adds a call to it under the
old name, in another part of the file, Git merges both without a word, and the result does not
compile. If one side changes a time from microseconds to nanoseconds and the other adds a
comparison with a constant in microseconds, the result compiles and is wrong.

So the merged result is a new version of the software that nobody has reviewed as a whole. Two
practices follow. CI runs on the merge, not only on the branch: on a pull request, GitHub's checkout
is a merge of the branch into the current main branch, made for the run. And a branch that has
lived long, or whose merge needed conflicts resolved, gets its merged result reviewed, not only its
own diff; resolving a conflict is writing code.

## Messages that people and tools can read

A commit message has two readers. A person reads it in `git log`, in a review, in a bisection
three years later, and wants to know what changed and why. A tool reads it to find the change
request, the reviewer, the co-authors. Both are served by the same form (an invented example; the
number and the test are placeholders):

```
Sorter: drop a pair whose second single is late (MDQ-PR-nnn)

The coincidence sorter kept a pair when its second single arrived after
the window had closed, because the comparison used the first single's
time. A late single now ends the pair; SorterProperties.LateSingle shows
the old behavior failing.

Review: change control checklist, items 1 to 6.
Reviewed-by: J. Reviewer <reviewer@example.org>
```

The **subject** says what the commit does in one line, short enough to read in a list: the common
limit is 72 characters, and 50 is a common target, a convention from the patch-by-e-mail days that
still fits `git log --oneline` and every hosting service's list. The **body**, after a blank line,
says why, wrapped at 72 so that `git log` indents it and still fits a terminal of 80 columns. It
says what a reader cannot get from the diff: the defect, the reason for the approach, the test that
shows it, the request it implements.

The last paragraph holds **trailers**: lines `Key: value`, as in an e-mail header. Git has a precise
rule for them, implemented once and used by `git interpret-trailers`, by `git log
--format=%(trailers)` and by every tool that asks Git. The trailer block is the last paragraph of
the message, never the subject's. It counts if every line in it is a trailer or a continuation (a
line that starts with white space), or if it contains a line Git generates itself
(`Signed-off-by:` or `(cherry picked from commit ...)`) and at least a quarter of its lines are
trailers. Anything else is prose, however much it looks like a header. MiniDAQ's check implements
the rule and tests it against Git's own parser on messages at its edges:

```{.python include="tools/check_commits.py" snippet="trailers"}
```

Here is the finding that started this chapter's tool. MiniDAQ's procedure asked for the line
`Review: change control checklist, items 1 to 6.` in every commit, and the commits wrote it like
this:

```
Review: change control checklist, items 1 to 6.

Co-Authored-By: ...
```

The blank line makes the review line a paragraph of its own, and the trailer block is only the
last paragraph. The measurement found the review line in 191 of the 260 commits, and Git parses
it as a trailer in none: `git log --format='%(trailers:key=Review)'` prints nothing for every one
of them. Nobody had noticed, because nobody had asked Git; people read the line and saw a record.
A record that a tool cannot find is a record that no check enforces, and a hook or a CI job that
counted reviewed commits would have found zero. The fix is one line less: the review line goes into
the trailer block, with the co-author lines, and from Chapter 36 on MiniDAQ's commits end with one
paragraph:

```
Review: change control checklist, items 1 to 6.
Co-Authored-By: ...
```

Exercise 36.1 writes the simpler half of Git's rule and tests it against `git interpret-trailers`.
Its starter takes any line of the form `Key: value`, and so finds a "trailer" in a subject such as
`Fix: the sorter`, in a URL (the key `https`) and in a sentence that starts with `Note:`.
The URL is also a lesson about oracles: git 2.43 takes `https` for a key, and git 2.56, on CI's
runners, does not. MiniDAQ's parser and the exercise follow the newer rule, and their tests leave
that one case out of the comparison when the installed git is older. CI failed on exactly this line
before the tests knew it; the oracle has a version, like any tool.

Figure [](#fig-ch36-message) labels the three parts on one of the project's own messages.

```{.figure #fig-ch36-message src="book/figures/tikz/ch36/message.tex" caption="The parts of a commit message: a subject that says what, a body that says why, and a block of trailers that tools read." alt="A sample commit message divided into three braced parts: the subject line, labelled what, at most 72 characters; the body, labelled why and what changed, wrapped at 72; and the trailers at the end, labelled read by tools, holding the review line and the co-author." width="85%"}
```

## A policy the history is checked against

A rule that nobody checks drifts, and MiniDAQ's commit conventions were all unchecked: the review
line, the no-reply identity (Chapter 32's pre-commit hook checks for addresses in the staged
changes, not in the commit's own author field), the trace to a change request. Chapter 36 writes
them down as a **commit policy**, `tools/commit_policy.json`, with six rules, and a tool that checks
a range of commits against it, `tools/check_commits.py` (TL-46):

```{.python include="tools/check_commits.py" snippet="rules"}
```

- **identity:** the author's and the committer's addresses are no-reply or placeholder addresses.
  The repository is public, and an address in a commit is published with the history, in every
  clone, forever. The report does not repeat the address it found.
- **subject** and **layout:** the form above; and no `fixup!`, `squash!` or work-in-progress commit
  on the main branch, since those are notes to oneself that were meant to be folded into another
  commit before the merge.
- **review:** a `Review:` trailer that Git parses, and a message that says so when the line is there
  but outside the block.
- **reference:** the trace to a change request or problem report, discussed in the next section.
- **merge:** a merge has two parents and a subject that says what it merges.

The first decision is **where the policy begins.** Run over the whole history with every rule, the
check reports, per rule, the number of commits that break it: identity 3, subject 91, layout 151,
review 254, reference 3 (`measurements/ch36/`). Almost all of it is the old convention: bodies
wrapped at about 100 characters, the width of this book's prose, and the review line above a blank
line. None of it can be fixed without rewriting the history, and a gate that fails on every run
for things nobody can fix is a gate people learn to ignore. So the policy has a field `since`, the
last commit before the policy, and by default the check covers `since..HEAD`: everything after it.
The old history is measured, its numbers kept, and left as it is (ADR 0031). Exceptions after
that point are possible but explicit: the policy's list `accepted` names a commit, the one rule it
may break and the reason, and a commit that breaks another rule still fails.

The second decision is **where the check runs.** In two places:

- **A commit-msg hook**, `tools/hooks/commit-msg`, installed with Chapter 32's pre-commit hook by
  `git config core.hooksPath tools/hooks`. It checks the message being committed and the author and
  committer Git will record (`git var GIT_AUTHOR_IDENT`) against the four rules that need no
  history, after removing the comment lines Git removes. It answers at the moment a mistake is
  cheapest to fix.
- **CI**, in the job that already checks document control, with the whole history fetched
  (`fetch-depth: 0`). A hook is the developer's: `git commit --no-verify` skips it, and a commit
  made on a hosting service's web page never runs it. CI is the gate.

One detail of the CI step is worth knowing. For a pull request, GitHub checks out a merge of the
branch into the main branch, made by GitHub for the run; that commit will never be part of the
history. The step therefore checks up to the branch's own head
(`github.event.pull_request.head.sha`), and the test of the repository's own history skips itself
on that checkout. A shallow clone, the default of many CI systems, does not contain the policy's
first commit; the check exits with status 2 and says to fetch the whole history, instead of
checking an empty range and passing.

The check takes about a second over all 260 commits. It costs nothing to run on every push, which
is the only frequency at which it is worth having.

Figure [](#fig-ch36-policy) shows what the check found when it was first run on this repository.

```{.figure #fig-ch36-policy src="book/figures/plots/ch36/policy.py" caption="The project's own history checked against the commit policy, before any accepted exception. The review rule fails almost everywhere because the review line was not in the trailer block; the identity, reference and merge rules almost never fail." alt="A grouped bar chart of the percentage of commits breaking each rule, for the whole history of 260 commits and since CR-0001 with 194. Identity 3 and 3, subject 91 and 75, layout 151 and 130, review 254 and 188, reference 3 and 0, merge 0 and 0." width="90%" inputs="measurements/ch36/history.txt"}
```

## What is under control

The rule **reference** is the trace from the history to change control: a commit that changes
something the procedure puts under change control names the change request or problem report it
implements (`CR-0022`, `MDQ-PR-059`), and that request or report exists in the repository.

The first version of the rule put files under control: any commit that changed the SRS, the risk
file, the software items, the SOUP list or the threat model had to name a request. Over the 194
commits since the first change request, that rule fired on eleven commits. Not one of them changed
a requirement, a hazard or a class. They updated the verification evidence of a requirement (the
measured exposure of a service unit went from 1.8 to 1.7), the wording of the risk management plan
when the book became generic, the version line of the SRS at a release, the SOUP list at a periodic
review. Chapter 16's procedure routes none of these through a change request: a new document
version, yes; a request, no. A rule that fires on them is a rule people satisfy by adding a request
number that means nothing, which is worse than no rule.

So the unit of control is what the procedure controls: a requirement's text, item or methods; the
hazards and risk controls; the software items and their classes. For the SRS the check parses the
file before and after the commit with the trace matrix's own parser and compares the requirements,
not the lines:

```{.python include="tools/check_commits.py" snippet="controlled"}
```

With that unit, the rule fires on no commit since the first change request, and on three before
it, when there was no change control to trace to. The SOUP list and the threat model are left out:
they change at every periodic review, which the procedure records in the document's own history
table. The policy names the controlled files, and a team whose procedure differs changes the
policy, not the tool.

The trace works in **either direction.** Most of MiniDAQ's chapter commits do not name their
change request in the message; the request names them, in its field `Commits`, written when it is
implemented. The check accepts both: a commit that names an existing request or report, or a commit
that a request lists. It does not check that the trace is true. A commit can name `CR-0022` and do
something else entirely; that is what the review is for, and the reviewer reads the request the
commit names. A tool that checks that the trace exists and a person who checks that it is right
are a better pair than either alone.

## Identity, signatures and who may push

The rule **identity** found three commits, all merges, whose author is a personal address. They
were made on the hosting service's web page, which merged the pull request with the address from
the account's settings, not the no-reply address every other commit uses. The pre-commit hook could
not see them, since the service does not run your hooks; no check looked at authors. The
repository's owner chose to leave them in the history rather than rewrite it, and MiniDAQ's pull
requests have been merged locally since, with the no-reply identity, then pushed. The policy now
fails a merge like that in CI, which is the earliest place it can be seen.

The finding shows what the author field is: text. `git -c user.name=... -c user.email=... commit`
writes whatever it is given, and so does a script, a bot, or an assistant. The author of a commit is
a claim. To make it more than a claim you sign the commit. Git can sign commits and tags with GPG,
with X.509 certificates, or, since version 2.34, with SSH keys (`gpg.format = ssh`, a key in
`user.signingkey`, `commit.gpgSign = true`), and `git log --show-signature` or `git verify-commit`
checks a signature against keys the verifier trusts (`gpg.ssh.allowedSignersFile` for SSH). A
signature proves that someone holding that key made the commit. It does not prove they reviewed it,
and it is worth only as much as the team's management of its keys: who has them, how they are
revoked when someone leaves, where the list of allowed signers lives.

The hosting service adds the controls that a repository alone cannot have: **protected branches**
on which nobody pushes directly, **required reviews** before a merge (one or two approvals, and
approvals dismissed when new commits arrive), **required status checks** (CI green on the merged
result), **code owners** who must approve changes to the paths they own (the requirements, the risk
file, the sorter), and a rule that commits on the branch be signed. These are settings of a service,
not files in the repository, and so they are not under the repository's change control; a team
records them in its development plan and checks them at each release (assumption: confirm with
team which of them your repository uses, and who can change them).

MiniDAQ, a teaching project with one maintainer, uses none of them, and its threat model says so.
Its section 7 already had the gap "The build runs the repository's code"; Chapter 36 reviews it
(version 11): the commit policy in CI now checks what each commit says (identity, review, trace),
but not who pushed it, and protected branches and verified signatures would make an unreviewed
change harder to land. A scanner's repository is part of its supply chain, and IEC 81001-5-1 asks
for the development environment's security to be managed; the settings above are where that starts.

Figure [](#fig-ch36-identity) puts the three layers in order.

```{.figure #fig-ch36-identity src="book/figures/tikz/ch36/identity.tex" caption="Who made a commit, in three layers. The name in it is a claim; a signature binds it to a key; the server's rules decide what reaches main." alt="Four boxes in a row joined by arrows: author and committer, whatever user.name and user.email say, noted as a claim, not a proof; a signature by SSH or GPG that binds the commit to a key, verified against the person's registered key; the server's push rules, protected main and required review and CI, the control that actually holds; and main, the record, where no-reply addresses keep emails private." width="100%"}
```

## Review in the workflow

Chapter 21 described how to review a change. In a Git workflow the review usually happens on a
**pull request**: a branch, a description, a discussion, approvals, and the CI results on the
merged result. That is a good place to review and a poor place to keep the record. The discussion
lives in the hosting service's database, not in the repository; it moves when the team changes
services, and it is gone when the service deletes the project. The squash merge in this chapter's
day in the life kept nothing of it.

So the outcome of the review goes where the history goes. The review trailer in each commit says the
checklist was applied. The change request records the decision and lists the commits. A finding that
the review makes and the change does not fix becomes a problem report with a number. A merge commit
says what it merged (`Merge the Part VIII review (PR #6, branch ...)`), so the pull request can
still be found by number. And a pull request template (`.github/pull_request_template.md` on GitHub)
can ask for the change request, the items and classes touched, and the checklist, so that the
description is written while the author still knows.

MiniDAQ's own reviews show the workflow and its value. After each Part's release, an independent
reviewer read the whole Part, opened a branch with its fixes and a pull request; the fixes were
reviewed again before the merge, sometimes rejected or changed, and merged locally. The reviews of
Parts IV to VIII found defects the author's own checks had passed, among them a sorter partition
that dropped a class of singles from an accounting test (MDQ-PR-059) and an acceptance rule that
matched a commit by a single character (MDQ-PR-060). Each became a problem report and a commit that
names it. The record of that is in the repository, not on a web page.

## Releases from the history

A release is a commit with a name people agree on. MiniDAQ's release procedure (Chapter 20) runs
the release checks on a clean checkout of one commit, writes the release record with that commit's
full name, and then creates an annotated tag on it, `book-v0.8.0`, whose message summarizes the
release. Three details make the tag trustworthy:

- **The tag is made after CI is green on the commit.** A tag on a commit that failed CI is a release
  of untested software, and tags are not moved: a moved tag means two releases with one name, and
  `git fetch` does not update a tag a clone already has unless forced.
- **A tag is itself a reviewed change.** MiniDAQ's tags are created by a workflow
  (`.github/workflows/tags.yml`) from a list in the repository (`.github/tags.txt`): adding a line
  to the list is a commit like any other, and the workflow, not a person's machine, makes the tag.
  A team can go further and allow only that workflow to create tags matching the release pattern.
- **The tag can be checked against the record.** `git rev-parse book-v0.8.0^{commit}` must print the
  name the release record gives, and Chapter 33's acceptance tool already refuses evidence from
  release checks that ran on another commit than the candidate.

`git describe` names any commit relative to the nearest tag
(`git describe --match 'book-v*' 34cf130` prints `book-v0.8.0-7-g34cf130`: 7 commits after the
release tag, at commit `34cf130`). MiniDAQ's version string comes from the file `VERSION` instead,
so that a build from a source archive without a `.git` directory still knows its version; a product
that also embeds the commit's name in its binaries can say exactly what a running program was built
from. And a release can be rebuilt from its tag: Chapter 20 showed the shipped build reproducible
from two checkouts, so the tag, the record and the archive all name the same thing.

Figure [](#fig-ch36-releases) draws the releases from the CHANGELOG itself.

```{.figure #fig-ch36-releases src="book/figures/plots/ch36/releases.py" caption="The project's releases, read from its CHANGELOG: when each was made and how long its entry is. Releases came fast and their entries shrank as the work moved from building to fixing." alt="A stem plot with release dates on the horizontal axis from 24 October and the number of non-blank lines in each CHANGELOG entry on the vertical axis. 0.1.0 has 105 lines, 0.2.0 113, 0.3.0 127, 0.4.0 152, then 0.5.0 79, 0.6.0 82, 0.7.0 62, 0.8.0 65, 0.9.0 58 and 1.0.0 34, with the major release in the Part color." width="90%" inputs="CHANGELOG.md"}
```

::: box-mistakes
- **Rewriting a published history** with rebase, amend or a filter: every commit name a record
  cites stops resolving. Revert instead; rewrite only with a change request.
- **Squashing or rebasing after records cite the branch's commits.** Decide how branches are
  integrated before anyone writes a commit name down.
- **Trusting a clean merge.** Run CI on the merged result and review the result of a long branch.
- **A record line that is not a trailer.** Ask Git (`git interpret-trailers --parse`) what it sees.
- **Merging on the hosting service's web page** in a public repository without checking which
  address it will use.
- **A gate on the whole old history.** It fails forever and gets ignored; start the policy at a
  named commit and keep the measurement of what came before.
- **A file as the unit of control.** It fires on evidence updates and wording; control what the
  procedure controls.
- **A shallow clone in CI** for a check of history: it passes on an empty range. Fail instead.
- **Taking the author field as proof of authorship.** It is text; signatures and the service's
  rules are what make it more.
- **Moving a tag.** A release has one name and the name has one commit.
:::

## What this leaves out

Large binary files and Git LFS (MiniDAQ keeps its measurement data small enough not to need it);
submodules and the alternatives for vendored code (Chapter 32 pins third-party sources by hash);
monorepositories with many products and their tools; partial and sparse clones; server-side hooks
and review systems such as Gerrit, which make the review a precondition of the push; the signing of
release artifacts with Sigstore or similar; and the electronic records rules of some markets, such
as the FDA's 21 CFR Part 11, which can apply to records kept in such systems (assumption: confirm
with team which records your quality system treats as electronic records). S. Chacon and B. Straub's
*Pro Git* covers the Git side of all of these.

::: box-regulated
- **Configuration management.** IEC 62304 clause 8: the repository identifies every configuration
  item and its version, the history records every change, and each release names a commit. The
  development plan says which branches exist, how they are integrated and who may create release
  tags.
- **Change control.** Clause 8.2 and ISO 13485 clause 7.3.9: a change to what the procedure
  controls traces to its request or problem report. The check verifies that the trace exists; the
  review verifies that it is right.
- **Records.** ISO 13485 clause 4.2.5: the history is a record, so it is not rewritten without a
  change request, and the review outcome lives in the repository, not only on the hosting service.
- **Tools.** The commit policy check is TL-46, class T2 (a defect lets a commit through without its
  record), with its validation in `tools/test_check_commits.py`.
- **Security.** The repository is part of the supply chain (IEC 81001-5-1); identity, signatures,
  protected branches and required checks are recorded in the threat model, version 11.
- **Records of this chapter.** CR-0023, ADR 0031, SRS version 25 (SRS-GIT-001 to SRS-GIT-007),
  TL-46, the threat model version 11, `tools/commit_policy.json`, `measurements/ch36/`.
:::

::: box-askteam
1. What is our branching model, and where is it written? Which released versions do we maintain,
   and how does a fix reach them?
2. Do we merge, rebase or squash pull requests, and do our change requests cite commits from
   before or after that step?
3. Where does the record of a review live: in the repository, in the hosting service, in the
   quality system? What happens to it if we change services?
4. Which branches are protected, which checks and approvals are required, and who can change those
   settings? Are they checked at each release?
5. Do we sign commits or tags? Who manages the keys, and how are they revoked?
6. Has our history ever been rewritten? How did we update the records that cited it?
7. Who may create a release tag, and what checks the tag against the release record?
8. Which of our records count as electronic records for our markets?
:::

## Exercises {.unnumbered}

**Exercise 36.1 (E): The trailers git sees.** *Goal:* find the trailers of a commit message as Git
does, and the values of one key without regard to case. *Starter:*
`exercises/ch36/e1_trailers/starter/trailers.py`, which takes every line that looks like
`Key: value`. *Acceptance:* `tests/test_trailers.py` passes: for every message of the tests the
result equals `git interpret-trailers --parse` (a block of trailers, a review line above a blank
line, a subject that looks like a trailer, a block with a line of prose, a continuation, trailing
blank lines, a URL, `Note:` in the body); `value` finds `review:` and `Review:` alike. *Time:* 1
hour.

**Exercise 36.2 (M): The name of an object.** *Goal:* compute the names of a blob, a tree and a
commit, and of a directory on disk. *Starter:* `exercises/ch36/e2_object_names/starter/objects.py`,
which hashes a file without its header, writes a directory's mode as `040000` and the names as text,
and sorts the entries by name alone. *Acceptance:* `tests/test_objects.py` passes: blob names equal
`git hash-object`; tree names equal `git mktree` in any order, with a file `a.txt` next to a
directory `a`; a directory's name equals `git write-tree`; commit names equal `git commit-tree`
with fixed dates; one changed byte changes the commit's name. *Time:* 2 hours.

**Exercise 36.3 (H): A merge that knows when to stop.** *Goal:* merge two versions of a file with
their common base, with conflicts written as Git writes them. *Starter:*
`exercises/ch36/e3_merge3/starter/merge3.py`, which compares the files line by line at the same
index. *Acceptance:* `tests/test_merge3.py` passes: clean merges equal `git merge-file -p` (changes
far apart, an insertion and a deletion that shift the lines, the same change on both sides, one side
unchanged); conflicts are as many as Git counts, each between markers (one line changed twice, a
deletion against a change, two insertions at one place, two adjacent lines, a conflict with a clean
change elsewhere, two conflicts). *Time:* 3 hours.

## MiniDAQ milestone: a history that can be checked {.unnumbered}

::: box-milestone
**Goal.** Every commit from now on carries a review trailer Git parses, a no-reply identity and a
trace to a change request when it changes a requirement, a hazard or an item, and CI fails a commit
that does not. **Start:** tag `ch35`. **End:** tag `ch36`.
:::

1. Write change request CR-0023 and ADR 0031; add SRS-GIT-001 to SRS-GIT-007 (SRS version 25) and
   TL-46; review the threat model (version 11).
2. Add `tools/commit_policy.json` with `since` at the last commit before it,
   `tools/check_commits.py`, the commit-msg hook and the test `tools.commits`; add the step to CI's
   job document-control.
3. Measure the history (`measurements/ch36/`), and move the review line into the trailer block in
   your own commits.
4. Add Exercises 36.1 to 36.3.

**Definition of done.** `tools.commits` passes, including the check of the repository from the
policy's first commit; CI's step passes on `main`; `docs.trace`, `docs.tools` and `docs.baseline`
(the seven requirements named by CR-0023) pass; every starter of the chapter fails. Tag `ch36`.

## Check yourself {.unnumbered}

1. What are Git's four kinds of object, and what does each hold?
2. How is an object's name computed? Why does a commit's name stand for the whole history before
   it?
3. What does a commit's name prove, and what does it not prove?
4. Why is a published history not rewritten, and what is done instead? When is a rewrite
   justified, and what does it then need?
5. How does a fix reach a released version in a trunk-based team? What does `cherry-pick -x` add?
6. What does each of merge, rebase and squash do to the commits a change request cites?
7. Why do changes of two adjacent lines conflict? Give a clean merge that is wrong.
8. What is Git's rule for the trailer block? Why was MiniDAQ's review line never a trailer?
9. Why does the commit policy start at a named commit, and how are exceptions after it recorded?
10. Why does the check run both in a hook and in CI? What does the CI step check for a pull request,
    and why not the checked-out commit?
11. Why is a requirement, and not the SRS file, the unit of control for the trace? What did the
    file-level rule fire on?
12. What do signatures, protected branches and required checks each add? What does none of them
    prove?
13. Where should the outcome of a review be recorded, and why not only on the pull request?
14. What three things make a release tag trustworthy?

## Summary {.unnumbered}

- A commit is a snapshot named by the hash of its content, with its parents; its name stands for
  every file and every earlier commit, and proves which content, not who, when or whether it was
  reviewed.
- The history is a record that change requests, release records and tags point into, so a
  published history is not rewritten; mistakes are reverted, and a necessary rewrite is a change
  with its own request.
- Trunk-based development with release branches and `cherry-pick -x` keeps the main branch
  releasable and released versions maintainable; the model is written in the development plan.
- Merge, rebase and squash leave different records; choose before anyone cites a commit. A clean
  merge is unreviewed code, so CI runs on the merged result.
- Trailers are the last paragraph by Git's rule; MiniDAQ's review line, written in 191 commits, was
  a trailer in none, and now is.
- The commit policy has six rules, starts after a named commit, runs in a commit-msg hook and in CI
  over the whole history in about a second, and fails rather than check a shallow clone.
- The trace to change control works at the level of a requirement, a hazard and an item: the
  file-level rule fired on eleven commits that changed none of them, the requirement-level one on
  none since change control began.
- An author is a claim; signatures, protected branches, required reviews and checks make it more,
  and are recorded as settings the team controls.
- The review is done on a pull request and recorded in the repository: trailers, change requests,
  problem reports, merge commits that say what they merged.

## Further reading {.unnumbered}

- S. Chacon and B. Straub, *Pro Git*, 2nd edition, Apress, 2014, https://git-scm.com/book:
  chapter 10 on Git's internals (objects, trees, commits), chapter 5 on workflows.
- The Git documentation, https://git-scm.com/docs: `git-interpret-trailers`, `git-merge-file`,
  `git-cherry-pick`, `git-verify-commit`, `gitformat-signature`, and the hash function transition
  plan.
- M. Stevens, E. Bursztein, P. Karpman, A. Albertini and Y. Markov, "The first collision for full
  SHA-1", CRYPTO 2017.
- T. Pope, "A Note About Git Commit Messages", 2008, on the short subject and the wrapped body.
- P. Hammant, *Trunk Based Development*, https://trunkbaseddevelopment.com.
- IEC 62304:2006+A1:2015, clause 8 (software configuration management); ISO 13485:2016,
  clauses 4.2.5 and 7.3.9.
- IEC 81001-5-1:2021, on the security of the development environment.
- ADR 0031 and CR-0023 in the repository; `measurements/ch36/README.md`.
