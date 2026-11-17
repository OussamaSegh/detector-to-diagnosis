# Maintenance and post-market {#ch40}

::: box-why
The day a release ships, the software stops being one thing. There is the main branch, where
work goes on, and there are installed copies of every release that a site still runs, each with
its own defects, each depending on SOUP whose supplier keeps its own calendar. A defect found
on main is now a question about all of them: which releases have it, which sites must be told,
which release will carry the fix, and what a fix may change for a site that wants nothing else.
The standards call this maintenance (IEC 62304 clause 6) and post-market surveillance (ISO
13485, ISO 14971 clause 10, and the regulations behind them). This chapter writes MiniDAQ's
maintenance plan, makes its records answer "which releases are affected?" and "when does this
SOUP stop being supported?", analyzes thirteen releases' problem reports for trends, and walks
through MiniDAQ's own history from 1.0 to 2.0 as the example.
:::

**A day in the life.** A service engineer calls from a hospital whose scanner runs MiniDAQ 1.3.0.
After the site's IT department hardened the acquisition PC, the server no longer starts; the
service log shows it waiting at a terminal that nobody sees. The engineer has three questions.
Is this a known problem? Does 1.3 get a fix, or must the site move to 2.0, with its new control
API and a configuration to migrate? And are the other three sites on 1.3 at risk? The developer
who takes the call finds the problem report at once: MDQ-PR-073, fixed on main two weeks ago.
The report says how the problem was found, why it is not relevant to safety and how it was fixed.
It does not say which releases have it, the release notes of 1.3.0 do not mention it, and nobody
has decided whether a release line that is already superseded still gets fixes. Answering the
engineer takes an afternoon of reading git history and a meeting.

## Learning objectives {.unnumbered}

After this chapter you can:

1. Name what IEC 62304 clause 6 asks of a software maintenance plan, and how it connects to the
   quality system's feedback, complaint handling, CAPA and vigilance.
2. Evaluate a problem from the field: its relevance to safety, the releases it affects, its
   effect on the risk file, and the decision.
3. Find the releases that contain a defect from a repository's history, including changes merged
   from branches and fixes that were cherry-picked.
4. Decide what kind of release a change needs, and run a maintenance branch with fixes
   cherry-picked from main.
5. Record when a SOUP item's support ends and decide what to do before it does.
6. Analyze problem reports for trends with a u-chart, and tell a change in the product from a
   change in the checks that find problems.

## Prerequisites and estimated time {.unnumbered}

Chapter 13 (the regulatory landscape and post-market surveillance), Chapter 14 (IEC 62304, the
problem reports and the SOUP list), Chapter 16 (ISO 13485, CAPA and internal audits), Chapter 21
(root cause analysis) and Chapter 36 (git and the team workflow). Reading: about 3 hours.
Exercises: 7 hours. Milestone: 3 hours. If time is short, do Exercise 40.3.

## A release is a promise

Before a release, a defect is a defect of the code. After it, the defect also belongs to every
installed copy of every release that contains it. The installed copies are not under your
control: a site runs the version it validated, on the platform it was given, and changes it when
its own procedures allow, which may be once a year. Three things follow.

- **Every question has a version.** "Is it fixed?" means "is it fixed in the release this site
  runs, or in one it can move to?" The answer needs a record of which releases have the defect
  and which have the fix.
- **A fix has a cost for the site.** Installing a release means validating it again, migrating
  configurations when an interface changed, and retraining when the behavior changed. A fix that
  arrives inside a release full of new features is a fix that sites will not install.
- **Time keeps moving underneath.** The compiler, the operating system and every SOUP item are
  maintained by someone else, on their own schedule. A release that was secure on the day it
  shipped is not secure two years later unless its SOUP still receives fixes.

The standards organize this into two loops that meet in the software team:

- **Maintenance** is the software life cycle after release. IEC 62304 clause 6 asks for a
  *software maintenance plan* (6.1): how feedback is received, documented and evaluated, the
  criteria for deciding whether feedback is a problem, how problem resolution (clause 9) is used,
  how modifications are analyzed and made, and how SOUP is managed. Clause 6.2 analyzes a
  problem or a modification request for its effect on safety, and clause 6.3 implements it with
  the same development process as before release.
- **Post-market surveillance** is the manufacturer's watch over the device in use. ISO 13485 asks
  for feedback (8.2.1) and complaint handling (8.2.2), reporting to regulators (8.2.3), analysis
  of data (8.4) and corrective and preventive action (8.5); ISO 14971 clause 10 asks the risk
  file to be kept current with production and post-production information. In the EU the Medical
  Device Regulation adds a post-market surveillance plan and periodic reports (Articles 83 to 86)
  and vigilance (Articles 87 to 92); in the US, 21 CFR 803 governs reports of adverse events and
  21 CFR 806 reports of corrections and removals, and since February 2026 the Quality Management
  System Regulation incorporates ISO 13485 (assumption: confirm with team which regulations apply
  to your product and who in the company owns each).

The software team does not decide whether a problem is reportable to a regulator or whether
installed scanners need a field action; the quality system does. What the software team must do
is give that decision what it needs, quickly and correctly: what the problem does, whether it can
lead to harm, which releases have it, and what a fix would involve. Every one of those answers is
a record that either exists before the call or is reconstructed under pressure.

MiniDAQ is a teaching project with no installed base, no complaints and no regulator. Its
software development plan said four lines about maintenance. Thirteen releases later, that is
the gap this chapter closes with change request CR-0033 and ADR 0039: a maintenance plan, and the
records it relies on, checked.

## The maintenance plan

`docs/regulatory/maintenance-plan.md` is a controlled document, version 1. It is short, because
most of what a maintenance plan needs is the development process that already exists: a change
after release is a change request, with requirements, tests and release checks like any other
(SDP sections 3 to 8). The maintenance plan adds only what exists after a release.

- **Feedback** (section 1). The sources, and how each becomes a problem report: complaints and
  service calls through the quality system's complaint handling, the server's own diagnostics
  (the flight recorder, the crash report and `tools/postmortem.sh` of Chapter 21), run records
  marked incomplete without a reason, SOUP advisories and the vulnerability scan, reviews, audits
  and readers.
- **Evaluation** (section 2). Relevance to safety, the affected releases, the effect on the risk
  file, and the decision, in that order, before anything is changed. A problem relevant to safety
  goes to the quality system the same day.
- **Supported releases** (section 3). A minor release line is supported for 24 months from its
  `.0` release (assumption: confirm with team; a manufacturer sets this from its service
  commitments and the device's declared lifetime). Supported means that a problem relevant to
  safety is fixed in a patch release of that line, and its SOUP stays under review.
- **Kinds of release** (section 4). What a patch, a minor and a major release may contain, and
  how a fix reaches a maintenance branch.
- **SOUP over the years** (section 5). Each item's end of support, and a plan for one that ends
  within the support period.
- **Trends** (section 6). The problem reports analyzed together at every minor release, with
  rules for when a pattern becomes a CAPA.
- **Retirement** (section 7). What is kept when a release's support ends: its archive, and the
  readers of every data format it wrote.

The SDP's section 10 now points to it, the design file lists it as evidence for feedback
(ISO 13485 clause 8.2.1), and the rest of this chapter is what each section requires of the
records and the tools.

## From a field report to a decision

A report from the field arrives as a symptom in the reporter's words: "the server does not start
after the IT update". The first job is to turn it into a problem report that a developer can
reproduce and an evaluator can judge. MiniDAQ's problem reports already record, since Chapter 14,
how the problem was found, the item it concerns, its description and its evaluation for safety;
since Chapter 21, a closed one also records its root cause, its category and why it escaped.
Evaluation then answers four questions, in order.

**Is it relevant to safety, and why?** Against the hazards of the risk file, not against
intuition. MDQ-PR-073's evaluation reads: "It happens at start-up, before the control API
listens: the server does not start, or names a wrong reason. No run is affected and nothing is
signed with a wrong key." The reasoning names the property that makes it harmless (it fails
before anything starts) so that a reviewer can check it, and so that a later change that breaks
the property also breaks the argument.

**Which releases have it?** That needs the history (next section).

**Does the risk file change?** A new sequence of events, or a probability that turns out to be
higher than assumed, is a change to the risk file, made with the fix's change request. A problem
that reveals a hazard nobody had listed is the most valuable feedback a product can get, and the
one most easily lost when the fix is quick.

**What is decided?** Fix it, in which kind of release; or release with it as a known anomaly, with
the decision and its reason recorded in the report. MDQ-PR-006, a port fault noticed up to 20 ms
late, has been open since Chapter 6 on purpose: its decision was made for release 0.3.0 and made
again for 1.3.0, with the cost of the fix weighed. An open report with a recorded decision is not a
failure of the process; an open report without one is.

The first three answers are the software team's; the quality system takes them from there.
Whether a problem is a complaint, whether it must be reported to a regulator and in what time,
and whether installed devices must be corrected are its decisions, under procedures with deadlines
measured in days (assumption: confirm with team how your company's complaint handling reaches the
software team, and how fast).

### Which releases have it

"Which releases have the defect?" sounds like a question about the defect. It is a question about
two commits and the repository's history: the commit that introduced the defect, and the commit
that fixed it. A release has the defect when its tag contains the first and not the second.

Git answers "which tags contain this commit?" directly:

```text
git tag --contains 0891ec8          # every tag whose history holds the commit
git merge-base --is-ancestor 0891ec8 book-v1.3.0 && echo "1.3.0 has it"
```

Three details make it harder than it looks, and Exercise 40.3 works through each.

- **Finding the introducing commit.** The fix is known; what it fixes often is not. `git blame` on
  the lines the fix changed names the commits that last touched them, which is a candidate, not
  an answer: the defect may lie in what a commit did not do (MDQ-PR-073's key loader passed no
  callback, and the line that should have had one was written in 1.3.0). `git bisect` with a test
  that reproduces the defect is the reliable way, when the test can run on old commits.
- **Merges.** A defect that came in on a feature branch reaches main through the merge's second
  parent. A walk along first parents only, which is what `git log --first-parent` shows, never
  sees it.
- **Cherry-picks.** A fix copied to a maintenance branch is a new commit with a new id; "does the
  tag contain the fix?" must also look for its copies. `git cherry-pick -x` writes "(cherry
  picked from commit ...)" into the copy's message, and that line is the only link between the
  two. This is why the maintenance plan requires `-x`.

MiniDAQ's problem reports now record the answer, in a field `affects`: the released versions that
contain the defect, or an empty list when the defect never reached a release. It is required from
MDQ-PR-065, the first report after release 1.0.0, and for every open report; `tools/anomalies.py`
checks it against the releases that `CHANGELOG.md` records, so that a version that was never
released cannot appear (SRS-MNT-001):

```{.python include="tools/anomalies.py" snippet="affects"}
```

The values for the eleven reports that needed one were found this way, with `git merge-base
--is-ancestor` between the commits and the tags. Some are what you would expect: MDQ-PR-070, the
decoder's slowdown caught by the release checks of 1.3.0, has `[]`, because the checks stopped
the release until it was fixed. Some are not. MDQ-PR-072, a crash at start-up when a board's bus
cannot be opened, was found while building the product preset for 2.0.0-dev, and its `affects`
runs from 0.5.0 to 1.3.0: nine releases had it, and none of their tests opened a device that did
not exist. The known anomalies of each release now show, for each open report, the releases that
share it ("0.1.0 to 1.3.0 (13 releases)" for MDQ-PR-006), which is what a site reads to decide
whether a known anomaly is news.

Back to the service engineer. With the field filled in, the report itself answers: MDQ-PR-073
affects 1.3.0 only. The other questions, whether 1.3 gets a fix and in what, are the subject of
the next section.

## Patch, minor and major

The version number is a promise about what an upgrade costs a site. MiniDAQ follows the usual
meaning of the three numbers (Semantic Versioning states it precisely), and the maintenance plan
turns it into rules about content:

| Kind | May contain | May not contain |
|---|---|---|
| Patch (X.Y.Z+1) | Fixes of problem reports; a SOUP update within its version line for a security or anomaly fix; documentation corrections | A new or changed requirement other than one the fix needs; a change of a data format, the control API or the configuration schema; a new SOUP item; a new feature |
| Minor (X.Y+1.0) | Compatible additions: requirements, fields, commands | Anything that makes an existing client, configuration or file fail |
| Major (X+1.0.0) | Breaking changes, each with a migration path, named in the release notes | A breaking change without a migration path |

What decides the kind is what a change does, not why it was made. A fix that needs a new field in
the run record is a minor release, even though its reason is a problem report; a fix that renames
a field is a major one. Exercise 40.1 writes the rule, and its tests are mostly about fixes that
look like patches and are not.

MiniDAQ 2.0.0 is a major release because of two changes, and its release notes will name both:
CR-0029, which removes the simulator from the product build, and CR-0030, which renames fields of
the control API (version 3.0) and the configuration schema (version 2.0). Each has a migration
path: `docs/migration-2.0.md` lists every renamed field, and `tools/migrate_config.py` (tool TL-49)
converts a 1.x configuration and says what it changed. A site that moves from 1.3 to 2.0 must
migrate its configurations, update any client of the control API, and validate the new release.
That is a reasonable price for new features. It is an unreasonable price for one fix, which is
why supported release lines exist.

### Maintenance branches

A patch release of a line that is no longer the newest cannot be made from main: main holds the next
release, with everything that the patch may not contain. The maintenance plan's answer is the usual
one, shown in Figure [](#fig-ch40-branches):

- A maintenance branch, `release/X.Y`, starts at the tag of `X.Y.0` when the first patch is needed.
- A fix is made on main first, through the normal process, so that no fix is lost in the next
  release. It is then cherry-picked to each supported maintenance branch with
  `git cherry-pick -x`, and the branch's full release checks run on the result.
- A fix that does not cherry-pick cleanly is written again for the branch and reviewed as a new
  change, because the code around it differs. The change request lists every branch the fix
  reached.
- Each patch release has its own release record, known anomalies and tag, like any other.

```{.figure #fig-ch40-branches src="book/figures/tikz/ch40/branches.tex" caption="A maintenance branch. The defect x came in before 1.3.0; the fix f is made on main and copied to release/1.3 with git cherry-pick -x, which names f in the copy's message. 1.3.0 is affected; 1.3.1 and 2.0.0 are not." alt="Diagram of two branch lines. The main line runs left to right with commits; the second is highlighted as x, the defect; a tag 1.3.0 follows; later a highlighted commit f, the fix; then a tag 2.0.0. A branch named release/1.3 leaves main at the 1.3.0 tag, runs parallel below, and has a highlighted commit fed by a dashed arrow from f, labeled cherry-pick -x: a new commit naming f in its message; a tag 1.3.1 follows on the branch. A note below says affected: 1.3.0 (has x, not f); not affected: 1.3.1 (has a copy of f), 2.0.0 (has f)." width="95%"}
```

Every supported line multiplies the cost of every fix that must reach it: a cherry-pick, a review
when it does not apply cleanly, and a full release cycle with its checks and its records. That cost
is what the support period buys. Three lines at once is common in practice; ten is not sustainable.
The period is a business decision with a safety argument in it, and the maintenance plan records it
as an assumption until someone owns it.

MiniDAQ has never made a patch release. Under the maintenance plan, would MDQ-PR-073 get one? Line
1.3 is supported until 2028-11-15. The problem is not relevant to safety, and the maintenance plan
promises patches for problems relevant to safety; for others, the fix ships with the next release
that the line's sites take. So the answer to the service engineer is: no 1.3.1 for this one, a
documented workaround (store the key unencrypted, protected by the permissions of its file, which is
what the server now says), and the fix in 2.0.0. A different evaluation would give a different
answer, and that is the point of recording the evaluation first.

## SOUP over the years

Chapter 14 made the SOUP list review each item's known anomalies before every minor release. That
answers "is the version we ship known to be defective?" It does not answer "will its supplier
still fix it next year?", and for a product used for ten years that question matters more.

MiniDAQ's own list had the answer to find. Every shipped server links OpenSSL from the platform,
OpenSSL 3.0.13 from Ubuntu 24.04. The OpenSSL project supported 3.0, a long-term support release,
until 2026-09-07. The SOUP list's reviews of 1.2, 1.3 and 2.0 went on reading the project's
advisories as the source of fixes, two months after the project stopped making them for 3.0. No
check failed, because nothing asked.

The answer is not that MiniDAQ was shipping unsupported software. Ubuntu 24.04 is a long-term
support distribution: Canonical backports security fixes to its `openssl` package for the
distribution's standard support, until 2029, and with Expanded Security Maintenance for longer.
The supplier of MiniDAQ's OpenSSL is the distribution, not the project, and the distribution's
date is the one that matters. But that is a decision, and it was nowhere.

The SOUP list now records, for each item of the shipped software, a row `Support ends`: a date,
or "no announced end" with the date it was checked. An item whose support ends within the
maintenance plan's support period, measured from its last review, must also have a row
`End-of-support plan`. `tools/check_soup.py` checks both (SRS-MNT-002):

```{.python include="tools/check_soup.py" snippet="support"}
```

OpenSSL's plan, decided with CR-0033, says three things. Fixes now come through the distribution's
backports, so the known-anomaly review reads Ubuntu's security notices for `openssl` first and the
project's advisories as information. The move to OpenSSL 3.5, the project's current long-term
support release (supported until 2030-04-08), is made with the next platform definition on the next
Ubuntu LTS, as a SOUP change with its own change request. And that change request checks every
OpenSSL call MiniDAQ makes against 3.5. nlohmann/json has no announced end: its project maintains
the latest release only, and a fix arrives as a new release that MiniDAQ adopts by a change
request, as CR-0002 did for 3.12.0 (assumption: confirm with team which support contract the
product's platform includes; that decides the OpenSSL date).

Three patterns cover most SOUP over a long life, and each has a cost:

- **Upgrade within the supported versions.** Cheapest per step, but the steps never stop, and each
  one is a change with its verification.
- **Rely on a long-term maintainer.** A distribution, a commercial support contract, or a vendor's
  long-term branch. It moves the question to the maintainer's dates and to a contract someone
  must keep paying.
- **Freeze and own it.** Keep the version and fix what matters yourself. Sometimes the only
  option for a component deep in a validated system; it makes you the supplier of that SOUP, with
  everything that implies.

None of them is free, and the worst choice is not choosing. The check makes the question come up
at every review, while there is still time to plan.

## Reading the problem reports together

A problem report is evaluated on its own. A quality system also asks what the reports say
together: whether the same kind of defect keeps escaping, whether a part of the product keeps
failing, whether the checks find problems before or after release. ISO 13485 calls this analysis
of data (clause 8.4), and it is where a CAPA should come from, rather than from the last memorable
incident.

MiniDAQ has 73 problem reports, 54 with a root cause analysis. `tools/pr_trends.py` (tool TL-50)
reads them together (SRS-MNT-003). The first question is the hardest: which release does a report
belong to? A report's date is not enough. Several of MiniDAQ's releases were made on the same day
(1.2.0 and 1.3.0 on 2026-11-15), and a problem found by the release checks of 1.3.0 was found on
the day 1.2.0 was released. The tool uses the record's own history instead: a report counts in the
first release whose tag contains the commit that added it to `problem-reports.json`.

The second question is how big each window was. Ten problems in a release that took 60 commits
are not the same as ten in one that took 10. The tool counts the commits from one release's tag to
the next as the window's exposure, gives the reports per 100 commits, and draws a u-chart, the
control chart for counts of events per unit of varying size:

```{.python include="tools/pr_trends.py" snippet="u-chart"}
```

The limit is wider for a small window, where a few reports are a large rate by chance. Figure
[](#fig-ch40-uchart) shows MiniDAQ's windows.

```{.figure #fig-ch40-uchart src="book/figures/plots/ch40/uchart.py" caption="MiniDAQ's problem reports per 100 commits in each release window, with the mean and the u-chart's upper control limit for the window's size. Two windows are above their limits: 0.3.0, when the reports file was created and the problems found before it were recorded at once, and 0.4.0, when Part IV's new checks started finding problems." alt="Bar chart of reports per 100 commits for the release windows 0.1.0 to 1.3.0 and 2.0-dev, with the number of reports on each bar. 0.1.0 and 0.2.0 have none. 0.3.0 has 14 reports, about 67 per 100 commits, and 0.4.0 has 20, about 36; both bars are in the alarm color and above a dashed step line, the upper limit, which varies between about 34 and 60. The other windows are between 3 and 29 per 100 commits, under their limits; a dotted line marks the mean, 17.6." width="100%" inputs="measurements/ch40/trends.txt"}
```

Two windows are above their limits, and neither says that the product got worse.

**0.3.0** is an artifact of recording. The problem reports file was created in Chapter 14, during
0.3.0's development, and the nine problems found before it, in Chapters 6 to 12, were recorded then,
beside the five that Part III's own work found. The windows of 0.1.0 and 0.2.0 have no reports
because there was no file, not because there were no problems. A trend tool counts records, and a
change in how records are kept looks exactly like a change in what they record.

**0.4.0** is a change in the checks. Part IV added property-based tests, the coverage review of
each software item, system tests through the real server and the release checks run as one script
(Chapters 18 to 21). Twenty problems were recorded, seven of them by the release checks and seven
by CI. New checks find old defects; a rate that rises when the checks improve is the checks
working. A signal on a control chart is a reason to look for the cause, and here the cause is
known and good.

The other tables of `measurements/ch40/trends.txt` say more about the process than about the code.
Of the 73 reports, 24 were found by the release checks, 18 by CI, 10 by reviews and audits, 9 by
tests, 9 during development (in a chapter's design or its code, by none of these) and 3 by
measurements. The release checks, run a dozen times, found a
third of everything: the long, slow checks that run before a release, the soak, the regression
gate, the stress run under ThreadSanitizer, the coverage review, find what the checks of every
commit do not. By root cause, process (16) and test (13) outnumber code (12) and tool (12): most
problems were in how the work was checked, not in what it did. Nine of the eleven reports
with an `affects` field reached at least one release. The seven of them that are closed name, in
their escape fields, the check that would have caught each; the other two, MDQ-PR-006 and
MDQ-PR-064, are open known anomalies with recorded decisions.

The maintenance plan's rules (section 6) turn this into decisions at each minor release: a window
above its limit, a root cause category with three or more reports in one window, or a problem
that reached a release by the same escape as an earlier one, is evaluated for a CAPA, and the
evaluation is recorded in the internal audit. The u-chart does not decide; it makes sure the
question is asked.

Two limits of the measure must be said. Commits are a rough exposure: one commit can hold a chapter
and another a typo, and MiniDAQ's history was rewritten once, which compressed its first windows.
And the "found by" classification is made by rules on the report's text, which is why the tool
lists them, in order, where they can be read and argued with:

```{.python include="tools/pr_trends.py" snippet="found-by"}
```

## MiniDAQ from 1.0 to 2.0

MiniDAQ's own history since 1.0.0 is short, and it holds most of what this chapter is about.

**Release 1.0.0** (2026-11-08) shipped with a recorded deviation: the soak's latency criterion,
ACC-04, failed in 2 of 180 intervals, and MDQ-PR-064 stayed open with a decision to find the cause
with a finer measure before judging the limit again. A known anomaly with a decision is a
legitimate state of a release; the record is what makes it legitimate.

**The independent review of 1.0.0** found that CAPA-0002's effectiveness check, due at 0.4.0, had
never been made, and that the release records of 0.9.0 and 1.0.0 said "No CAPA is open"
(MDQ-PR-065). It also found fifteen controlled documents released with the status "draft for
review" (MDQ-PR-066). Both
were process problems in releases already made. Their fixes were checks: `tools/check_capa.py`
fails on an overdue effectiveness check, and the design file check fails on a draft document in a
release. Their `affects` fields say which releases carry the wrong records, which is all a fix of
a record can do for a release already made.

**Release 1.3.0** (2026-11-15) added time markers and signed run records. Its release checks found
the decoder 16% slower than in 1.2.0 and stopped the release until it was fixed (MDQ-PR-070,
`affects: []`). Its coverage review found that `verify-run` threw on a signed record with a field
of the wrong type (MDQ-PR-071), and the review after the release found that the server waited for
a passphrase on a terminal when its key was encrypted (MDQ-PR-073). Both affect 1.3.0.

**2.0.0-dev** made the breaking changes once, with migration paths, and found MDQ-PR-072 on the way,
a crash nine releases old. Then Chapters 38 and 39, and this chapter.

One part of the roadmap for 2.0 did not happen. The roadmap set an errata window of four to six
weeks after 1.0.0, for readers' reports to be folded into 1.0.x patch releases. It was dropped,
because no reader had a way to report anything: there was no errata page and no issue template yet.
Every problem report since 1.0.0 came from reviews, audits and the project's own checks. That is the
post-market lesson in its smallest form: surveillance needs a channel, and a quiet field is not a
safe field until someone has made it possible to speak.

## Telemetry and service logs

A scanner in a hospital cannot be debugged from a developer's desk. What the software leaves
behind when something goes wrong is the evidence the maintenance process starts from, and the
time to design it is before release. MiniDAQ leaves four kinds of evidence, each from an earlier
chapter:

- **The run record** of every run, with its integrity verdict, its time base verdict and its
  signature: what was acquired, how, and whether it is complete (Chapters 15, 25 and 38).
- **The audit trail** of commands and state changes, with who and when (Chapter 7).
- **The flight recorder and the crash report**: the last events before a failure, the version and
  build ID of the program, and a stack, written when the program fails (Chapter 21, ADR 0016).
  `tools/postmortem.sh` gathers them into one file that a service engineer can send.
- **The status** that the control API reports, including the counters of every port and each
  board's clock (Chapters 9, 22 and 38).

What MiniDAQ does not do is send any of it anywhere by itself. A product that reports usage or
failures from installed devices ("telemetry") needs a channel through the hospital's network, a
legal basis for every field it sends, a guarantee that no patient data leaves, security for the
channel itself (Chapter 17), and a team that reads what arrives. Each is a project of its own, and
many manufacturers do it; each is a decision of the product, not of the acquisition software
(assumption: confirm with team whether the product collects data from installed devices, and how
it reaches the software team). Whatever the channel, the rule from Chapter 21 holds: a log that
nobody designed for a question will not answer it.

::: box-mistakes
- **Fixing main and calling it done.** The sites run releases, not main. A fix is done when every
  supported line that needs it has it, or the decision not to is recorded.
- **"Which releases have it?" answered by dates.** Releases made on the same day, branches and
  cherry-picks make dates wrong. Use the history: the tags that contain the introducing commit
  and not the fix or a copy of it.
- **A cherry-pick without `-x`.** The copy is then a stranger to its original, and the question
  "does this branch have the fix?" has no answer in the history.
- **A patch release with a feature in it.** A site that wanted only the fix must now validate the
  feature, and may not install either.
- **Following first parents only.** A defect that came in on a merged branch is invisible on the
  first-parent line.
- **Reviewing a SOUP item's anomalies and not its end of support.** The review says the version is
  fine today; nobody asked whether anyone will fix it tomorrow.
- **Reading a trend without its exposure.** Twice the reports in a window twice as long is no
  change at all.
- **Taking a control chart's signal as a verdict.** A new check or a new way of recording raises
  the count; the signal says look, not blame.
- **Letting the software team decide vigilance.** Whether a problem must be reported to a
  regulator is the quality system's decision; give it the facts the same day.
- **Assuming a quiet field is a safe one.** No reports from sites can mean no way to report.
:::

## What this leaves out

The quality system's side of post-market surveillance: complaint handling procedures, the
post-market surveillance plan and periodic safety update reports of the EU MDR, the deadlines and
forms of vigilance reports, field safety corrective actions and their notices, and recalls; the
FDA's guidance on cybersecurity after release, with coordinated vulnerability disclosure and the
SBOM as a postmarket tool; installed-base management and remote software distribution; long-term
support contracts and their costs; the clinical side of post-market evidence (post-market
clinical follow-up); statistical methods beyond the u-chart, such as cumulative sum charts and
reliability growth models; and the retirement of a product line with its data. ISO/TR 24971
(clause 10), the MDR's articles, the FDA's regulations and guidance, and Montgomery's book in the
further reading cover each.

::: box-regulated
- **Maintenance.** IEC 62304 clause 6.1: the maintenance plan; 6.2.1: feedback documented and
  evaluated, with its relevance to safety; 6.2.2 to 6.2.5: the problem reports, the analysis of a
  modification and its approval through CR-0033's process; 6.3: modifications made with the
  development process (SDP sections 3 to 8). Clause 9: problem resolution, where `affects` belongs.
- **SOUP.** IEC 62304 clauses 6.1 and 7.1.3: SOUP evaluated after release; the SOUP list's `Support
  ends` and `End-of-support plan`, checked by `docs.soup`.
- **Feedback and data analysis.** ISO 13485 clauses 8.2.1 (feedback), 8.4 (analysis of data),
  8.5.2 and 8.5.3 (CAPA): `tools/pr_trends.py` at each minor release, read by the internal audit
  (SDP section 8, item 9).
- **Risk.** ISO 14971 clause 10: post-production information reviewed against the risk file; the
  evaluation of each problem report against the hazards.
- **Requirements and tools.** SRS-MNT-001 to SRS-MNT-003 (SRS version 36), verified by
  `tools.maintenance`; TL-50 in the tool list.
- **Records of this chapter.** CR-0033, ADR 0039, the maintenance plan (version 1), SDP version 18,
  SOUP list version 29, the problem reports' `affects`, `measurements/ch40/trends.txt`.
:::

::: box-askteam
1. Is there a software maintenance plan, and who owns it? How long is each release line
   supported, and who decided?
2. How does a complaint about the scanner reach the software team, and how fast? Who decides
   whether it is reportable?
3. How do we find which installed releases have a defect? Is `affects` (or its equivalent) a field
   of our problem reports?
4. What may a patch release contain? Do we keep maintenance branches, and how does a fix reach
   them?
5. Which of our SOUP items reach the end of their supplier's support within the support period,
   and what is the response for each?
6. Which platform support contract does the product rely on (distribution, ESM, vendor), and who
   pays for it?
7. How are problem reports analyzed for trends, by whom, and what has the analysis led to?
8. What evidence do our devices leave for service, and does any of it leave the hospital?
:::

## Exercises {.unnumbered}

**Exercise 40.1 (E): The kind of release a change needs.** *Goal:* decide whether a change may
ship in a patch, needs a minor or needs a major release, by the maintenance plan's rules, and
give the next version. *Starter:* `exercises/ch40/e1_kind_of_release/starter/release.py`, which
calls every fix a patch, looks at a release's first change only, and does not reset the lower
numbers of a version. *Acceptance:* `tests/test_release.py` passes: fixes that change a format or
break a client are minor and major, a release takes the largest kind of its changes, the versions
after 1.3.0 and 1.3.2, and a development version or an unknown kind refused. *Time:* 1 hour.

**Exercise 40.2 (M): The support matrix.** *Goal:* the release lines supported on a given day, the
newest release of a line, and the SOUP items that need an end-of-support plan. *Starter:*
`exercises/ch40/e2_support_matrix/starter/support.py`, which measures support from a line's newest
patch, counts a month as 30 days and sorts versions as text. *Acceptance:* `tests/test_support.py`
passes: a patch three years later does not keep its line alive, months end on calendar days, `1.10`
sorts after `1.3`, and five SOUP items over two support periods. *Time:* 2 hours.

**Exercise 40.3 (H): Which releases contain a defect.** *Goal:* from a commit history, the release
tags, the introducing commit and the fix, the released versions that contain the defect.
*Starter:* `exercises/ch40/e3_affected_releases/starter/affected.py`, which follows first parents
only and looks for the fix by its id. *Acceptance:* `tests/test_affected.py` passes: a defect
merged from a branch, a fix cherry-picked to a maintenance branch and picked again from there, a
release branch made before the defect, a defect fixed before any release, and a history of 20,000
commits. *Time:* 3 hours.

**Exercise 40.4 (M): Is the version we ship affected?** *Goal:* decide whether an installed package
is affected by an advisory: OpenSSL's versions with their letters, package versions compared as
dpkg compares them, and the distribution's advisory deciding when it has spoken. *Starter:*
`exercises/ch40/e4_affected_version/starter/affected.py`, which drops the letters, compares package
versions as strings and ignores the distribution's fix. *Acceptance:* `tests/test_affected.py`
passes: twelve OpenSSL versions in order, the upstream ranges, seven pairs in dpkg's order
(`-0ubuntu3.5` before `-0ubuntu3.16`), and verdicts from a distribution's fix or, without one, an
upstream lead. Then check the version on an Ubuntu machine and answer in `NOTES.md` why an upstream
match is a lead and what the review must record. *Time:* 1 hour.

## MiniDAQ milestone: a maintained product {.unnumbered}

::: box-milestone
**Goal.** MiniDAQ has a software maintenance plan; every problem report since 1.0.0 says which
releases it affects; every shipped SOUP item says when its support ends; and the problem reports
are analyzed for trends at each minor release.
**Start:** tag `ch39`. **End:** tag `ch40`.
:::

1. Write change request CR-0033 and ADR 0039; add SRS-MNT-001 to SRS-MNT-003 (SRS version 36).
2. Write `docs/regulatory/maintenance-plan.md`; point SDP section 10 to it (version 18); add it to
   the design file's controlled documents and to clause 8.2.1's evidence.
3. Add `affects` to `tools/anomalies.py` and fill it in for every report that needs it, from the
   history; regenerate the known anomalies.
4. Add `Support ends` and `End-of-support plan` to `tools/check_soup.py` and to the SOUP list
   (version 29).
5. Add `tools/pr_trends.py`, its tests (`tools.maintenance`) and TL-50; write
   `measurements/ch40/trends.txt`.
6. Add Exercises 40.1 to 40.4.

**Definition of done.** `tools.maintenance` passes; `docs.anomalies`, `docs.soup`, `docs.srs`,
`docs.trace`, `docs.baseline`, `docs.design_file`, `docs.changes` and `docs.tools` pass; every
starter of the chapter fails. Tag `ch40`.

## Check yourself {.unnumbered}

1. What does IEC 62304 ask a software maintenance plan to cover, and what does it reuse from the
   development process?
2. Which decisions about a field problem belong to the software team, and which to the quality
   system?
3. A defect was introduced on a feature branch and merged. Why does `git log --first-parent`
   not find it, and what does?
4. Why does the maintenance plan require `git cherry-pick -x`?
5. A fix needs a new field in the run record. What kind of release is it, and why does the reason
   for the change not decide?
6. What does a maintenance branch cost per fix, and what limits how many lines you can support?
7. OpenSSL 3.0's project support ended in September 2026. Why was MiniDAQ's platform OpenSSL still
   supported, and what had to be decided?
8. Why does `tools/pr_trends.py` place a report by the commit that recorded it rather than by its
   date?
9. Why is a u-chart's limit wider for a small window?
10. The 0.4.0 window is above its limit. Why is that good news, and how would you tell it from bad
    news?
11. What does the errata window that never happened teach about post-market surveillance?
12. What evidence does a MiniDAQ server leave for a service engineer, and why does it send none of
    it by itself?

## Summary {.unnumbered}

- After a release, every defect is a question about each installed release: which have it, which
  will carry the fix, and what the fix costs a site.
- IEC 62304 clause 6 asks for a maintenance plan; most of it is the development process, and the
  rest is feedback, evaluation, supported releases, kinds of release, SOUP and trends.
- The software team evaluates a problem for safety, affected releases and the risk file; the
  quality system decides complaints, vigilance and field actions.
- A release has a defect when its tag contains the introducing commit and neither the fix nor a
  cherry-pick of it; MiniDAQ's reports record this as `affects`, checked by `docs.anomalies`.
- Patch releases carry fixes only, minor releases compatible additions, major releases breaking
  changes with a migration path; maintenance branches receive fixes cherry-picked from main.
- Each shipped SOUP item records when its support ends; OpenSSL 3.0 left its project's support on
  2026-09-07, and MiniDAQ now relies on the distribution's backports until the move to 3.5.
- `tools/pr_trends.py` places each report in its release window by its record's history, and a
  u-chart of reports per 100 commits shows two signals, both from changes in the checks and the
  records.
- Release checks found a third of MiniDAQ's 73 problems; process and test causes outnumber code.
- Surveillance needs a channel: the errata window was dropped because nobody could report.

## Further reading {.unnumbered}

- IEC 62304:2006+A1:2015, clause 6 (software maintenance process) and clause 9 (software problem
  resolution process).
- ISO 13485:2016, clauses 8.2.1 (feedback), 8.2.2 (complaint handling), 8.2.3 (reporting to
  regulatory authorities), 8.4 (analysis of data) and 8.5 (improvement).
- ISO 14971:2019, clause 10 (production and post-production activities), and ISO/TR 24971:2020,
  its guidance.
- Regulation (EU) 2017/745 (the Medical Device Regulation), Articles 83 to 92 and Annex III:
  post-market surveillance and vigilance.
- US FDA, 21 CFR Part 803 (medical device reporting) and Part 806 (reports of corrections and
  removals); *Postmarket Management of Cybersecurity in Medical Devices*, guidance, 2016.
- D. C. Montgomery, *Introduction to Statistical Quality Control*, 8th edition, Wiley, 2019:
  control charts for attributes, the u-chart among them.
- T. Preston-Werner, *Semantic Versioning 2.0.0*, semver.org.
- The OpenSSL project's release strategy, on its website, and Ubuntu's release cycle page: the
  two calendars that decide MiniDAQ's OpenSSL.
- `git help cherry-pick`, `git help bisect` and `git help tag` (`--contains`).
- The maintenance plan, ADR 0039, CR-0033 and `measurements/ch40/trends.txt` in the repository.
