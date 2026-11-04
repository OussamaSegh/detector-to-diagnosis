# Capstone: MiniDAQ 1.0, end to end {#ch33}

::: box-why
Every stage of MiniDAQ passes its own tests. That is a statement about stages, and a scanner is not
a set of stages: it is a chain in which each stage receives what the previous one produced. A count
that one stage loses and the next never misses, a rounding that one stage applies and the reference
of the next does not, a summary that prints the wrong counter: none of these fails a stage's tests,
and each of them is found in the first hour of running the chain. This chapter runs the chain, from
simulated decays to an image, through the programs that ship; checks every count between every
pair of stages; compares the server's output with an independent computation of what it should be;
and then writes down, in a form a tool can check, what MiniDAQ must show before it is called 1.0.
:::

**A day in the life.** The release of a new acquisition software version is a week away. The
software lead asks the question every release review asks: "how do we know the whole thing works?"
The answers come one stage at a time. The sorter's tests pass. The list-mode writer's benchmark is
well above its limit. The reconstruction chapter's images look right. The system tests run the
server for 34 test cases. Then a physicist asks something nobody can answer from that list: "if I
put a phantom in the scanner, do the singles the detectors produced arrive in the image, and are the
coincidences in the file the ones the detectors made?" Every stage was tested with inputs its own
tests made up. The reconstruction read files the simulator wrote directly, without the server in
between. The server's system tests used its synthetic source, which skips the readout link. No test
had ever put the stages in a row.

## Learning objectives {.unnumbered}

After this chapter you can:

1. Explain what a chain test adds to the tests of its stages, and which defects only a chain test
   finds.
2. Build an offline reference for a streaming system that must agree with it record for record,
   and decide what the reference must model (here, the quantization of the readout link) for the
   agreement to be exact.
3. Write conservation equations between the stages of a pipeline from the counters the stages
   already report, and show that each equation can fail.
4. Say why a damaged input is checked by accounting and integrity, not by comparison with a
   reference.
5. Write an acceptance specification as data (criteria, requirements, targets, evidence) and
   evaluate it with verdicts that cannot turn missing or stale evidence into a pass.
6. Freeze a set of requirements against a baseline so that a change after verification goes
   through change control, and say when a baseline is retaken.

## Prerequisites and estimated time {.unnumbered}

Chapter 9 (the readout link and its fault injection), Chapter 10 (the coincidence sorter and its
counters), Chapter 12 (the list mode), Chapter 19 (the system tests and the soak), Chapter 20 (the
release checks), Chapters 26 to 28 (calibration, corrections, reconstruction) and Chapter 31 (the
QC report). Reading: about 3 hours. Exercises: 5 hours. Milestone: 6 hours. If time is short, do
Exercise 33.2.

## What the stages' tests leave between them

List what each stage's tests feed it, and the gaps show themselves. The simulator's tests check
the singles it generates against the physics it models. The readout link's tests encode singles
into MDQ-P1 words, pack them into MDQ-R1 packets, damage some, and check what the decoder makes of
them. The sorter's tests (Chapter 10) push singles made up by the test and compare the
coincidences with a reference written for the test. The server's system tests (Chapter 19) start
the real program, configure it over its control socket and acquire, but from the synthetic source,
a generator inside the server that produces singles without a link. The reconstruction (Chapter
28) reads list-mode files that `minidaq_sim` writes directly, without the server.

Each of those is the right test for its stage, and none of them sends a single from the detector
model through the link and the server into a file that the reconstruction then reads. The places
where one stage hands over to the next are exactly where the tests of each side stop:

- **Units and quantization.** The simulator computes in double precision; the link carries time in
  units of 5 ps and energy in units of 0.5 keV. A stage downstream of the link sees values the
  simulator never produced.
- **Counts.** Each stage counts what it received, passed on and set aside. Whether the count one
  stage passes on equals the count the next one receives is a property of the pair, not of either
  stage.
- **Configuration.** The server and the offline tools each have an energy window, a coincidence
  window and a policy for multiples. Agreement between them is checked nowhere unless something
  runs both.
- **Names.** A summary line, a status field, a report column: each stage names its quantities, and
  a quantity printed under the wrong name is invisible until another program's number is put next
  to it.

A chain test closes those gaps by running the stages as they run in the product, in order, with
real programs, real files and a real socket, and by checking what passes between them. It does not
replace the stages' tests, which find a defect in the stage that has it and run in milliseconds. It
finds the defects that live between stages, which no stage's test can see.

## An offline reference of the same singles

The first question of a chain test is what the output is compared with. There are three options,
and MiniDAQ has used each of them somewhere.

**Plausibility.** The rates, the spectra and the ratio of prompts to delayed coincidences lie
within chance of what the simulation predicts. Chapter 19's statistical golden test works this way.
It catches a stage that is broken; it does not catch a stage that loses one coincidence in ten
thousand, or one that shifts a time by 5 ps.

**A stored golden file.** Chapter 19's exact golden test stores the output of the synthetic source
for a fixed configuration and compares every run with it. Exact, and right for a deterministic
generator inside one program. For a chain of several programs it records whatever the chain did on
the day the file was made, defects included, and must be regenerated, and reviewed, after every
intended change to any stage.

**An offline reference.** Compute what the output should be, independently of the program under
test, from the same input. MiniDAQ has one ready: `minidaq_sim` can sort its own singles with the
same `CoincidenceSorter` the server uses and write list-mode files. `minidaq_send`, given the same
seed, generates the same singles and sends them over UDP. If the server receives every packet, its
files must hold exactly the reference's coincidences (SRS-SYS-006): not statistically, but record
for record, so that a hash of the records is equal.

The first comparison did not agree. Over 0.5 s at 2 MBq, 10 of the reference's 13,126 prompts were
not the server's. The cause was not a defect but a
missing piece of the model: the simulator's sorter saw energies in double precision, while the
server saw them after the link had rounded them to 0.5 keV. A single at 434.8 keV is outside a
window that starts at 435 keV; on the link it becomes 435.0 keV and is inside. Ten singles moved
across the window's edges, and each changed a coincidence.

There are two ways to make the comparison exact. One is to loosen it: compare with a tolerance, or
compare only coincidences far from the edges. Both throw away what makes the comparison worth
having. The other is to model the link in the reference. That is what `quantize_as_on_link` does,
and `minidaq_sim --link 1` applies it before the sorter:

```{.cpp include="minidaq/include/minidaq/sim/readout_link.hpp" snippet="as_on_link"}
```

The implementation does not compute the rounding itself. It encodes each single into its MDQ-P1
word and decodes it again with the server's own `StreamDecoder`, the same code the server runs, so
that the reference sees the link's rounding, its truncation of time to 5 ps and its handling of the
38-bit counter's wrap every 1.374 s by construction. A second implementation of the rounding would
be a second place for a mistake, and it would agree with the decoder only as long as nobody
changed either. The unit tests (SRS-SIM-024) check that the result is the decoder's across a wrap,
that the truth fields the simulator attaches to each single survive, and that a crystal outside
the scanner is refused rather than silently passed.

With the link modeled, the server's records and the reference's are identical in every run of the
chapter: the daily QC acquisition (a point source, 912,139 singles, 135,972 prompts and 338 delayed
coincidences) and the phantom acquisition (4,466,628 singles, 134,605 prompts and 6,453 delayed),
with equal SHA-256 digests of the records.

The reference has one weakness, and the decision record (ADR 0028) states it: the offline sorter
and the server's sorter are the same class. A defect in `CoincidenceSorter` is in both, and the
comparison cannot see it. That is acceptable only because the sorter has its own independent
checks: its unit tests against hand-built cases, the truth-classified report of Chapter 10 that
counts true, scattered and random coincidences from the simulator's truth, and the statistical
golden test. A reference shares code with what it checks only where something else checks that
code.

## Every count, between every pair of stages

Equality with the reference says that the output is right. It does not say where a difference came
from when there is one, and on a damaged link there is no reference to compare with. The second
part of the chain test is accounting: a set of equations between the counters that the stages
already report, each saying that what one stage passed on is what the next one received, and that
what a stage received is split exactly into what it passed on and what it set aside and counted
(SRS-SYS-007).

```{.python include="tools/e2e.py" snippet="accounting"}
```

Each line uses counters that already existed. The sender reports the singles and packets it sent
and the damage it injected; the server's status reports, for the link, the packets received,
delivered, lost and stale and the words delivered; for the sorter, the partition of its singles
from Chapter 10; for the sink, the coincidences written. The list-mode files are counted by reading
them, and the sinogram binning reports where each record went. The chain needs no new counter,
only equations that relate the old ones.

The equations are of two kinds. A **hand-over** equation says that two stages agree:
the singles into the sorter equal the words delivered by the decoder, less those it found invalid;
the coincidences written equal the prompts and delayed coincidences the sorter emitted; the records
in the files equal what the sink wrote. A **partition** equation says that a stage lost nothing
inside itself: every single entering the sorter was rejected by energy, left alone, in a multiple,
or one of the two singles of a pair window; every record read by the binning was binned or set
aside for a named reason. Together they make a closed account from the first packet sent to the
last record binned.

An equation that always holds is indistinguishable from an equation that can never fail. The test
`Accounting.test_every_counter_off_by_one_fails_a_check` takes the counters of a clean run, changes
each one by plus one and by minus one, and requires that at least one equation then fails. The check
of a check is cheap and worth its few lines: Exercise 33.1 does the same for the
sorter's own counters, and shows the one counter that no equation over them can pin down.

### What the accounting found

The first end-to-end run failed one check that was not in the list above. `minidaq_sim` printed
"445,867 recorded singles" for a run of which `minidaq_send`, from the same seed, sent 445,866.
Every coincidence agreed. The difference was in a summary line: the simulator generates singles
until the first one at or after the end of the run and keeps that single for the next call, and
the line printed the simulator's statistics, which count every single simulated, that one
included. The files, the sorter report and the count rates used only the singles before the end.
No test read the summary line, and no test of the simulator could have seen it, because the
simulator was right about what it had simulated. Only a second program's count, put next to the
first, showed that the line named one quantity and printed another. The problem report MDQ-PR-055
records the defect, its five whys and its escape: nothing compared counts across programs until
this chapter.

It is a small defect with a general lesson. A summary line is read by people: an operator who
compares it with the scanner's display, a physicist who puts it in a table. A number under the
wrong name is a defect even when no data is wrong, and the defects of that kind are found by
putting two programs' numbers side by side.

### A damaged link

With `--loss`, `--reorder` and `--duplicate`, `minidaq_send` damages the stream as Chapter 9's
fault injection did. On a damaged link the reference comparison is skipped, and not because it is
inconvenient. A lost packet removes singles, and a removed single can remove a coincidence, but it
can also add one: a window that held three singles is a multiple, which the `kill_all` policy
discards; lose one of the three and the window holds a pair, which may be a prompt. The server's
output on a damaged link is neither the reference nor a subset of it.

What a damaged run must get right is the account and the verdict. Every packet sent is delivered
or counted lost (delivered plus lost equals sent), every packet received is delivered or stale,
every single that reached the sorter is in the sorter's partition, and the run is marked
incomplete with the loss named in its integrity record, the control of hazard H-01 (silent data
loss) since Chapter 19. In the measured damaged run (0.2% of packets lost, 0.2% reordered, 0.2%
duplicated), 909,591 of the QC acquisition's 912,139 singles reached the sorter, every one
accounted for, and both runs said they were incomplete because packets were lost.

## The run, from decays to an image

`tools/e2e.py` (TL-40) runs two acquisitions. The first is the daily QC acquisition: a point
source of 1 MBq for 2 s, whose list mode goes to the QC report of Chapter 31. The second is the
end-to-end phantom: an 80 mm radius cylinder of activity at 5 MBq inside a 90 mm radius cylinder
of water, whose list mode is binned into sinograms, corrected and reconstructed. Each acquisition
has the same structure:

```{.python include="tools/e2e.py" snippet="acquire"}
```

The reference runs first, from the same seed. The server is started as the system tests start it,
configured over its control socket, and receives the singles over UDP from `minidaq_send` at
detector speed. The test waits for the datagrams it expects before it stops the run: not a sleep
but a condition (Chapter 19's rule for tests that wait). Then the files are verified with
`minidaq_listmode verify`, the records of both sides are hashed, and the binning reports its own
account. Every number in the result has a check that names the equation it was held to, so that a
reader of `e2e.md` sees "4466628 / 4466628" next to "sorter singles in = words delivered - invalid
words", not a bare "pass".

### The image at the end of the chain

The phantom's sinograms go through the corrections and the reconstruction of Part VI: randoms
estimated from the singles, attenuation computed for the water cylinder, and OSEM with 4 iterations
of 8 subsets on 2 mm pixels.

```{.python include="tools/e2e.py" snippet="image"}
```

What should an image check check? Not its pixels against a stored image: that is a golden file
again, and the image changes with every improvement of the reconstruction. Not the noise, which
depends on the counts and the iterations more than on the chain. The two checks (SRS-SYS-008, by
demonstration) ask whether the image shows what was put in the scanner:

- **Size.** The activity's radius at half its level is within 2 mm of 80 mm. Measured: 80.25 mm.
  A geometry error anywhere in the chain (a crystal map, a ring radius, a line of response binned
  at the wrong angle) moves the edge.
- **Flatness.** The mean of the disc within 24 mm of the center is within 10% of the mean of the
  ring from 24 to 48 mm. Measured: 1.042. Without the attenuation correction, the same data give
  0.86: the center of a water cylinder comes out low, because photons from the center cross more
  water. A chain that skipped the correction, or applied the wrong map, fails this check.

The first version of the second check was a coefficient of variation of the pixels, which came out
at 0.54 and failed, not because the chain was wrong but because a 2 s acquisition has few counts
per pixel, and pixel noise measures the counts. A check must measure the property it names. The
flatness ratio averages over thousands of pixels and measures the correction; the noise is kept in
the result (`block_cv`, 0.20 for 8 mm blocks) for information only.

Before choosing the limits, `measurements/ch33/flatness.py` ran the reconstruction for five seeds
with and without the attenuation correction. With it the radius ranges from 80.18 to 80.48 mm and
the ratio from 0.937 to 1.042; without it the radius is 82.64 to 82.76 mm and the ratio 0.756 to
0.861. The limits sit between the two populations with a margin on both sides. A limit chosen from
one run is a guess; a limit chosen from the spread of runs that should pass and runs that should
fail is a measurement. The run itself uses one fixed seed, so its numbers are the same on every
run of the same code, and a change in them is a change in the code.

### Two speeds

The whole run takes about a minute on the release build: 15 s for the phantom's reference, 15 s for
its acquisition, about 2 s each for the QC report and the reconstruction with the C++ projector.
The release checks run it in part 3, with the image, and keep its result as evidence
(`e2e/e2e.json`). On every change, the test `system.e2e` runs a short version: 0.5 s acquisitions
at 2 MBq, the clean link and the damaged link, without the image, in about 35 s in the debug build.
It cannot judge the image; it does catch every defect of accounting or of agreement with the
reference within a day of its commit, not at the next release.

::: box-mistakes
- **Comparing a chain's output only for plausibility.** Rates within chance of the prediction
  pass a chain that loses one coincidence in ten thousand. Compute the exact expected output where
  the system is deterministic.
- **A reference that does not model a stage.** The first comparison differed in 10 of 13,126
  prompts because the reference skipped the link's rounding. Model the stage, preferably with its
  own code, rather than loosening the comparison.
- **Comparing a damaged run with the reference.** A lost single can add a coincidence. Check the
  account and the integrity verdict instead.
- **Equations that cannot fail.** Change each counter by one and show that an equation catches it.
- **An image check that measures noise.** A pixel's coefficient of variation measures the counts.
  Check what the chain must get right: size, flatness, position.
- **Limits from one run.** Measure the spread of runs that should pass and runs that should fail,
  then put the limit between them.
- **Waiting with a sleep.** Wait for the condition (the datagrams the sender sent), with a
  timeout.
:::

## What 1.0 must show: an acceptance specification

The chain test answers "does the whole thing work?" for one run. A release asks a broader
question: does this version meet everything we said it must? Until this chapter MiniDAQ answered it
in prose. The release record of 0.7.0 says that the performance results were "read against
SRS-PERF-020 and SRS-PERF-021 by hand"; the list of verifications in the development plan (SDP
section 6) names what must be run, not what each result must show. A reviewer could check that
every verification ran. Whether each one met its target was a judgment made while reading a page of
benchmark output, and nothing kept the judgment the same between releases.

The acceptance specification, `docs/regulatory/verification/acceptance.json`, writes the judgment
down. Each criterion names the product-level property it accepts, the requirements it
demonstrates, the target in words, the evidence file in the output of the release checks, the part
of the release checks that produces it, and the rule that reads it:

| Criterion | What | Requirements | Target |
|---|---|---|---|
| ACC-01 | pipeline throughput, hardened | SRS-PERF-020 | median of 5 at least 20 M singles/s |
| ACC-02 | list-mode writer, fsync at close | SRS-PERF-021 | slowest of 3 at least 3 M coinc./s |
| ACC-03 | a long acquisition | SRS-SYS-003 | 30 min at 1 M singles/s, no loss, complete |
| ACC-04 | end-to-end latency | SRS-PERF-022 | p99 of every 10 s interval at most 10 ms |
| ACC-05 | the chain end to end | SRS-SYS-006, 007, SRS-ANA-005 | all checks pass, records equal |
| ACC-06 | the image | SRS-SYS-008 | radius and flatness within their limits |
| ACC-07 | the system test plan | SRS-SYS-001, 002, 004, 005 | every case passed, none skipped |
| ACC-08 | every release verification | (process) | all four parts passed |
| ACC-09 | trace, risk, anomalies, freeze | (process) | the four checks pass on the candidate |

ACC-04 needed a requirement that did not exist. The soak has measured the end-to-end latency since
Chapter 19, and every release record quoted it, but no requirement said what it must be. A target
without a requirement is a number someone liked; SRS-PERF-022 now states it (at most 10 ms for the
99th percentile of every 10 s interval at 1 M singles/s, about twice the 4.42 ms measured at 0.7.0),
and CR-0020 names it as an addition.

`tools/acceptance.py` (TL-41) evaluates the specification from one output directory of the release
checks. Each rule reads one kind of evidence and returns whether the target is met and what was
found:

```{.python include="tools/acceptance.py" snippet="rules"}
```

The rules are small on purpose. Each parses the evidence file that the release checks already
write, so that the specification adds no new measurement, only a reading of the existing ones that
is the same at every release. What matters more is the verdict around them:

```{.python include="tools/acceptance.py" snippet="verdict"}
```

There are four verdicts, and only one of them counts:

- **PASS**: the evidence exists, is of the candidate commit, and meets the target.
- **FAIL**: the evidence exists and is of the candidate, and does not meet the target.
- **MISSING**: the evidence does not exist or cannot be read. A benchmark that crashed, a soak
  that was skipped, a JSON file cut short: none of these is a pass, and none of them is an
  exception that stops the report either. The report names what is missing.
- **STALE**: the evidence exists but was produced on another commit, or on a working tree with
  changes. Every part of the release checks records its commit (`commit.txt`, `commit-part-N.txt`)
  and the end-to-end result records its own, with `-dirty` for a changed tree. A benchmark of last
  week's commit says nothing about this one, whatever its value.

The order matters. Freshness is checked before the target: evidence of another commit is STALE
even when its value would fail, because a FAIL sends a reader looking for a regression in the
candidate that may not be there. And the candidate is accepted only when every criterion passes:
"no criterion failed" is the wrong question, because MISSING and STALE are absences of evidence,
not evidence of success. Exercise 33.2 builds the same verdicts on a simpler evidence format and
meets the subtler ways of getting them wrong (a NaN that passes a negated comparison, a `true`
that Python counts as the number 1).

The tool was first run against the evidence of release 0.7.0, as if that release had been judged
by the specification (`measurements/ch33/acceptance-0.7.0.md`): six criteria pass, the two of the
chain are MISSING (the end-to-end run did not exist), and the repository criterion is STALE (the
repository has moved on from the release's commit). That is the right answer for 0.7.0, and the
answer the specification exists to give: a release cannot be accepted on evidence it does not
have.

The targets are book-level numbers, and the specification says so. A manufacturer's acceptance
criteria come from the scanner's system requirements and from design validation, decided by people
who know what the clinical use needs (assumption: confirm with team). What a software team owns is
the mechanism: that each criterion is written down with its requirements and its evidence, that a
tool reads the evidence the same way every time, and that nothing becomes a pass by being absent.

## The requirements freeze

The acceptance specification judges a release against its requirements. That judgment is only as
stable as the requirements. A requirement verified at one release and edited at the next, a limit
lowered by one word in a large table, a requirement deleted with the code it described: each of
these makes an earlier verification refer to text that no longer exists, and none of them fails a
test.

A freeze is the rule that, from a given point, a requirement changes only through change control.
MiniDAQ's freeze is a baseline of digests, `docs/regulatory/srs-baseline.json`, taken from SRS
version 21 at release 0.7.0, and a check that compares the SRS with it on every change:

```{.python include="tools/req_baseline.py" snippet="digest"}
```

The digest covers the text, the item and the method, with runs of white space made one space.
Rewrapping a table, or padding its columns, changes nothing; changing a word, a number, the item
that implements a requirement or the method that verifies it changes the digest. A digest rather
than the text keeps the baseline small and the comparison exact. The old text is not lost: the
baseline's name says which release it was taken at, and version control has the SRS of that
release.

```{.python include="tools/req_baseline.py" snippet="check"}
```

Every requirement added, changed or removed since the baseline must be named by a change request
that is approved or implemented. A proposed request is an intention, a rejected one a decision
against the change, and neither authorizes it. The test `docs.baseline` runs the check on every
change; this chapter's own additions (SRS-SIM-024, SRS-SYS-006 to SRS-SYS-008 and SRS-PERF-022, in
SRS version 22) pass it because CR-0020 names them, and a sixth requirement added without a request
would fail it.

The rule that a request "names" a requirement when its ID appears in its text is deliberately
simple, and it has a hole that Exercise 33.3 asks about: a request that says "SRS-SYS-001 does not
change" names SRS-SYS-001. Closing it without parsing English means a structured field in the
request (a table of requirements with "added", "changed" or "withdrawn"), or recording in the
request the digest it expects after the change. MiniDAQ keeps the simple rule and relies on the
change control review to read what a request says; a team with many requests a week might not.

The baseline is retaken at a release, after the review of every difference, by a person
(`tools/req_baseline.py --write NAME`). A tool that retook the baseline when the check failed would
turn the freeze into a record of whatever was written last. Retaking it is part of the release
review, listed in the release steps; it is never the way to make `docs.baseline` pass.

## The release record gains a report

Two smaller changes make the release checks feed the specification directly. `release_checks.sh`
now writes every result into `release-checks.txt` as it runs, one section per part (`## part 3`),
ending with "all release checks passed (part 3)" or the list of failures. Until 0.7.0 that file
was collated by hand from four terminal outputs, which is the kind of step that is done slightly
differently at every release. A part run again appends a new section, and the rule of ACC-08 reads
the last section of each part, so a failed run followed by a passing one counts as passing, and the
reverse as failing. Part 3 also runs the end-to-end run, and the last line of part 4 now says what
to do next: run `tools/acceptance.py OUT` and keep its report as item 7 of the release record (SDP
version 12, section 8).

## What this leaves out

A chain test on a simulator is not a test of a scanner. The detector model is the one Chapter 8
built, the link is a UDP socket on one machine, and the phantom is two cylinders. A real system
verification runs on the real detectors, electronics and acquisition computer, with phantoms and
procedures from the performance standards (NEMA NU 2 for PET), and measures what the simulator
cannot: dead time of real electronics, the timing resolution of real crystals, the behavior of a
real network under load. Above that, design validation asks whether the product meets the users'
needs in its intended use, which no software test answers. The acceptance specification covers the
software's share of that work and is written to be extended: a criterion is a JSON object and a
rule a small function.

The image checks are two numbers on one phantom. Contrast recovery, resolution and quantitative
accuracy (Chapter 30's measures) are not acceptance criteria here; adding them is a change of the
specification, through change control, with limits chosen from measured spreads as the flatness
limit was. And the comparison with the reference shares the sorter with the server, a limit the
decision record states and the sorter's own tests cover.

::: box-regulated
- **System testing.** IEC 62304 expects software system testing against the software
  requirements, with the results recorded, and the evaluation of anomalies found (verify: the
  standard's clauses on software system testing; assumption: confirm with team). The end-to-end
  run is MiniDAQ's software system test of the whole chain; its result file names every check,
  its equation and its values, and it is kept as release evidence.
- **Release.** The standard expects the verification to be complete and evaluated, known residual
  anomalies documented, and the released version identified before release (verify: the clauses
  on software release). The acceptance report shows, criterion by criterion, that the evidence of
  this commit meets its target, and the problem reports list the known anomalies.
- **Configuration management of requirements.** A requirement that has been verified is a
  configuration item; a change to it is a change request with an impact analysis. The baseline
  and `docs.baseline` enforce that, and the baseline is retaken only in the release review.
- **Acceptance criteria are not the team's choice.** The targets in `acceptance.json` are
  book-level; a manufacturer derives them from the system requirements and design validation
  (assumption: confirm with team). Changes to the specification go through change control like the
  SRS.
- **Records.** CR-0020 (the change), ADR 0028 (the decisions and the options not taken), MDQ-PR-055
  (the defect the chain found), TL-40 to TL-42 (the new tools), the SRS version 22, the
  development plan version 12, the threat model version 8 (reviewed: no new element of the running
  system).
:::

::: box-askteam
1. Is there a test that runs the whole chain, from the detectors' data to an image, with the
   programs that ship? How long does it take, and when does it run?
2. What is the chain's output compared with: plausibility, a stored golden file, or an independent
   reference? What does the reference share with the system it checks?
3. Do the counters of each stage add up between stages? Has anyone checked that an off-by-one in a
   counter would be noticed?
4. Where are the acceptance criteria of a release written, and who sets the targets? Is the
   evidence of each criterion checked to be of the release's commit?
5. When were the requirements last frozen, and what stops a verified requirement from being
   edited?
6. Which numbers in our summaries and displays are compared with another program's numbers?
:::

## Exercises {.unnumbered}

**Exercise 33.1 (E): Counts that add up.** *Goal:* write the sorter's conservation equations as a
function that names every equation that does not hold, from its counters and the coincidences it
wrote. *Starter:* `exercises/ch33/e1_counts_add_up/starter/accounting.cpp`, which checks the
partition of the singles and nothing else. *Acceptance:* `tests/test_accounting.cpp` passes: the
sorter's own counters over 200,000 random singles, pushed in random chunks with out-of-order singles
mixed in, satisfy every equation; ten counters, each raised and lowered by one, fail the equation
the test names; a coincidence lost before the file is seen; a multiple window of two singles is
impossible. Then explain in `NOTES.md` why `multiple_windows` can be off by one without failing any
equation, and write the equation that replaces "pair windows" under `take_all_goods`. *Time:* 60
minutes.

**Exercise 33.2 (M): An acceptance verdict that cannot be fooled.** *Goal:* give each criterion a
verdict (PASS, FAIL, MISSING, STALE) from a JSON evidence file, and accept a candidate only when
every criterion passes. *Starter:* `exercises/ch33/e2_acceptance_verdict/starter/verdict.py`, right
on the happy path and wrong everywhere else. *Acceptance:* `tests/test_verdict.py` passes: PASS and
FAIL at and around the limits in both directions; MISSING for an absent, unreadable or non-numeric
value, including `true`, NaN and infinity; STALE for another commit or a dirty tree, before the
target; a short and a long form of a commit match; no verdicts is not an acceptance. *Time:* 2
hours.

**Exercise 33.3 (M): A requirements freeze that sees every change, and only changes.** *Goal:*
compare an SRS with its frozen baseline and list every difference that no approved or implemented
change request names. *Starter:* `exercises/ch33/e3_requirements_freeze/starter/freeze.py`, which
reports a rewrapped row as a change, never sees a removed requirement, and lets a proposed request
cover a change. *Acceptance:* `tests/test_freeze.py` passes: white space and padding change no
digest, a word of the text, item or method does; added, changed and removed are listed in order;
only approved and implemented requests count. Then answer in `NOTES.md` the question of the request
that names a requirement by saying it does not change. *Time:* 2 hours.

## MiniDAQ milestone: MiniDAQ 1.0, end to end {.unnumbered}

::: box-milestone
**Goal.** The chain runs end to end on every change and at every release; the server's records
equal the offline reference's over a clean link; every count balances between the stages; the
acceptance of a release is a report that a tool computes from its evidence; and the requirements
are frozen against a baseline. **Start:** tag `ch32`. **End:** tag `ch33`.
:::

1. Write change request CR-0020 and ADR 0028; add SRS-SIM-024, SRS-SYS-006 to SRS-SYS-008 and
   SRS-PERF-022 (SRS version 22); add TL-40 to TL-42 to the tool list; update the development plan
   (version 12: the end-to-end run and the requirements freeze in section 6, the acceptance report
   in section 8) and review the threat model (version 8).
2. Add `quantize_as_on_link` to the item `sim`, the option `--link` to `minidaq_sim` and its unit
   tests; fix MDQ-PR-055 and record it.
3. Add `tools/e2e.py` and `tools/test_e2e.py` (the test `system.e2e`); run it on the release build
   with a clean and a damaged link, and keep the results in `measurements/ch33/`, with the image
   checks over five seeds.
4. Add `docs/regulatory/verification/acceptance.json`, `tools/acceptance.py` and its tests; make
   `release_checks.sh` write `release-checks.txt` and run the end-to-end run in part 3; evaluate
   the specification against the evidence of release 0.7.0.
5. Add `docs/regulatory/srs-baseline.json` from SRS version 21, `tools/req_baseline.py`, its tests
   and the test `docs.baseline`.
6. Add Exercises 33.1 to 33.3.

**Definition of done.** `ci/run_all.sh` is green on all six presets; `system.e2e`,
`tools.acceptance`, `tools.req_baseline` and `docs.baseline` pass; `tools/e2e.py` passes on the
release build with both links; the trace matrix shows the five new requirements verified; the
acceptance report of 0.7.0's evidence gives six passes, two missing and one stale; every starter of
the chapter fails. Tag `ch33`.

## Check yourself {.unnumbered}

1. Name three kinds of defect that only a chain test finds, and say why a stage's test cannot.
2. Why is equality with an offline reference a stronger check than plausibility, and what does it
   need from the system that plausibility does not?
3. Why did the first comparison differ in 10 of 13,126 prompts? Why model the link rather than
   compare with a tolerance?
4. Why does `quantize_as_on_link` call the server's decoder instead of rounding the values itself?
5. What does the reference share with the server, and what covers that shared part?
6. What is the difference between a hand-over equation and a partition equation? Give one of each.
7. Why change each counter by one in a test of the equations?
8. Why is a damaged run not compared with the reference? What is it checked against instead?
9. What did MDQ-PR-055 get wrong, and why did no test of `minidaq_sim` see it?
10. Why was a pixel coefficient of variation the wrong image check, and how were the flatness
    limits chosen?
11. What are the four verdicts of the acceptance tool, and why does only one count?
12. Why is freshness checked before the target?
13. Why did ACC-04 need a new requirement?
14. What does the requirements baseline store, and why is rewrapping a table not a change?
15. When is the baseline retaken, by whom, and why never by the check itself?

## Summary {.unnumbered}

- A chain test runs the stages in order with the programs that ship and checks what passes
  between them; it finds the defects between stages (units, counts, configuration, names) that no
  stage's test sees, and complements the stages' tests rather than replacing them.
- The server's records are compared with an offline reference from the same seed, record for
  record (SRS-SYS-006). The reference models the readout link with the server's own decoder
  (`quantize_as_on_link`, SRS-SIM-024); without it, 10 of 13,126 prompts differed by design.
- Conservation equations over the counters the stages already report close the account from the
  first packet to the last record binned (SRS-SYS-007); a test shows that every counter off by one
  fails one of them.
- A damaged link is checked by accounting and by the integrity verdict, not by the reference,
  because a lost single can also add a coincidence.
- The first run found MDQ-PR-055, a summary line that printed one count under the name of another,
  visible only next to a second program's count.
- The phantom's image is checked for size (radius 80.25 mm, limit 2 mm around 80) and flatness
  (1.042, limit 10%), with limits placed between runs with and without the attenuation correction
  over five seeds.
- `system.e2e` runs a short chain on every change (about 35 s); the release checks run the full
  one with the image in part 3.
- `acceptance.json` writes nine product-level criteria with their requirements, targets and
  evidence; `tools/acceptance.py` gives PASS, FAIL, MISSING or STALE, and accepts only when all
  pass. Against 0.7.0's evidence: six pass, two missing, one stale.
- The requirements are frozen against a baseline of digests from SRS version 21; `docs.baseline`
  fails for every difference that no approved or implemented change request names, and the
  baseline is retaken only in a release review.

## Further reading {.unnumbered}

- IEC 62304:2006+A1:2015, *Medical device software: Software life cycle processes*, the clauses on
  software system testing, software release and configuration management.
- U.S. Food and Drug Administration, *General Principles of Software Validation; Final Guidance
  for Industry and FDA Staff*, 2002, on verification, validation and the evidence a release needs.
- NEMA NU 2-2018, *Performance Measurements of Positron Emission Tomographs*, for the phantoms and
  procedures a real PET system verification uses.
- T. Winters, T. Manshreck and H. Wright, *Software Engineering at Google*, O'Reilly, 2020, the
  chapters on test sizes and on larger tests.
- G. J. Myers, C. Sandler and T. Badgett, *The Art of Software Testing*, 3rd edition, Wiley, 2011,
  on system and acceptance testing.
- ADR 0028 and CR-0020 in the repository: the decisions and the change record.
