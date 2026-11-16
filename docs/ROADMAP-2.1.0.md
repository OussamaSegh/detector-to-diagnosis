# Roadmap for release 2.1.0

Status: accepted. Drafted on 2026-11-16, after the release of 2.0.0 and the merge of its
independent review. Accepted the same day by the coordinator under the author's standing
delegation of 2026-11-15, after the author asked that the work continue.

## 1. Where 2.0.0 leaves the project

- **The book.**
  - The Second Edition has 40 chapters in ten Parts and Appendix A.
  - The PDF is 819 pages at 8.5 x 11 in. Amazon KDP's paperback limit is 828 pages, so nine
    pages of room are left. Any new text needs room made first (roadmap 2.0.0, section 8,
    answer 5: a denser layout first, then Appendix A online).
  - The solutions manual has 218 pages.
- **Thin chapters.** Measured by words, exercises and measurement files, the chapters of Parts
  VI to X are thinner than those of Parts I to V:
  - Chapters 26 to 40 have three exercises each. Chapters 1 to 25 have four to six.
  - Chapter 29 (C++ and Python) is the shortest chapter in the book, at about 4,600 words. It
    covers the bridge between the acquisition code and the reconstruction and analysis code.
  - Chapter 28 (image reconstruction) is about 6,600 words.
  - Chapters 1, 6 and 22 have no measurements folder.
- **Open problem reports.**
  - MDQ-PR-006 has been decided again and has no further decision due.
  - MDQ-PR-064, the latency peaks of the soak, is open. Its finer measure exists since the
    review of 2.0.0, but no run has caught a peak with it yet. ACC-04 has shipped with a
    deviation since 1.0.0.
- **Due at 2.1.0.**
  - The effectiveness check of CAPA-0005.
  - The trend analysis of the problem reports (maintenance plan, section 6).
  - The SOUP review for 2.1.
  - The approval of SDP version 20, unless 2.0.1 approves it first.
- **Process.** The new rule on running a failed release check again (SDP section 8,
  MDQ-PR-077) was not enforced by `tools/release_checks.sh` (done for 2.0.1).

## 2. What 2.1.0 is for

A minor version: compatible additions only (maintenance plan, section 4). No interface breaks.

1. **Depth where the Second Edition is thin.** Parts VI to X get the exercises and worked
   measurements that Parts I to V have. The C++ and Python chapter becomes as deep as its
   neighbors.
2. **ACC-04 without a deviation.** Find the cause of MDQ-PR-064 and remove it, or show that it
   lies in the machine and decide the requirement again on that evidence.
3. **Room for the text**, within one volume.
4. **A release process that enforces its own rules.**

## 3. Themes and scope

### Theme G: room in one volume

- Measure what a denser layout gains: the body font and leading, the space around listings, and
  the figure sizes. Keep the reading quality checks of the interior design (release 1.1.0).
- If a denser layout gains less than about 40 pages, move Appendix A to the web edition, and
  keep a two-page summary in print (answer 5 of roadmap 2.0.0).
- Exit: the PDF has at least 40 pages of room under 828 before Theme H adds text.

### Theme H: depth in Parts VI to X

- **Chapter 29, C++ and Python.**
  - Zero-copy exchange of arrays with the buffer protocol.
  - Releasing the GIL around the projector.
  - Building and testing the extension as a wheel.
  - Measuring the cost of the crossing.
  - All of this uses pybind11, which is already approved.
- **Chapter 28, image reconstruction.** One more worked measurement: convergence against noise
  for the subset count.
- **One new exercise in each chapter from 26 to 40.** Each has a starter that fails, a solution
  and a test, so that Parts VI to X have four exercises per chapter.
- **Measurement folders for Chapters 1, 6 and 22**, where the text quotes a measured number.
- Exit: the chapter recipe is complete for each changed chapter (code, tests, exercises,
  measurements, review).

### Theme I: ACC-04 without a deviation (MDQ-PR-064)

- Catch peaks with the per-second measure:
  - longer soaks, with the release preset;
  - one run with the pipeline's threads pinned to CPUs, and one run without.
- If the cause is the scheduling of MiniDAQ's own threads, add a compatible setting:
  - a new optional field in the configuration (schema 2.2) for the pipeline threads' CPU
    affinity;
  - the default stays what 2.0 does;
  - a change request, an ADR, and a requirement for it.
- If the cause is the machine, record the evidence and decide SRS-PERF-022's limit and ACC-04
  again, without a deviation.
- Exit: MDQ-PR-064 is closed, or re-decided with the cause named.

### Theme J: release process

- `tools/release_checks.sh resume` runs a failed part again only after its investigation is
  written, and refuses a second rerun for a release (SDP section 8, MDQ-PR-077). Done for 2.0.1,
  since it completes the fix of MDQ-PR-077.
- Patch releases: the maintenance plan says when a patch may be made from main, namely when main
  holds only changes that a patch may contain, and when `release/X.Y` is cut.
- At 2.1.0:
  - the CAPA-0005 effectiveness check;
  - `tools/pr_trends.py` in the internal audit;
  - the SOUP review for 2.1.

## 4. Order and milestones

| Milestone | Content | Exit criterion |
|---|---|---|
| 2.0.1 | Patch: the fixes of the review of 2.0.0 (MDQ-PR-077 to MDQ-PR-080) with the rerun rule in the tool, SDP v20 and maintenance plan v3 approved, a measured soak for MDQ-PR-064 | Release checks pass; tag `book-v2.0.1` |
| 2.1.0-dev, first | Theme G (room) | At least 40 pages of room |
| 2.1.0-dev, second | Theme I (MDQ-PR-064) | Report closed or re-decided with its cause |
| 2.1.0-dev, third | Theme H, Chapters 29 and 28, then the new exercises of Chapters 26 to 40 and the measurement folders | Chapter recipe complete for each |
| 2.1.0 | Internal audit with trends, CAPA-0005 check, SOUP review, full release checks | CI green on the release commit; tag `book-v2.1.0` |

The same rhythm as before applies:

- Each release gets an independent review on an Opus model before the next milestone is
  released.
- The fixes of that review go out in the next patch or minor release.

## 5. Out of scope for 2.1.0

- **Breaking changes** to the control API, the configuration or the file formats. Those wait for
  3.0.0.
- **New chapters.** The page budget is for depth first.
- **GPU reconstruction.** It needs a new dependency and hardware this project does not have.
- **Scaling the acquisition across machines.** It is a candidate for a later minor release, with
  its own chapter.
- **New third-party dependencies**, unless the author approves each one.

## 6. Risks

| Risk | Effect | Response |
|---|---|---|
| The denser layout hurts reading on paper or in the Boox PDF | A worse book | Compare page images before and after; keep the 1.1.0 checks |
| MDQ-PR-064's peaks do not appear in the soaks | The cause stays unknown | Run longer soaks; if none appears in five hours of soak, decide again on the evidence that the peaks are rare and harmless (no loss) |
| A new setting for CPU affinity changes the measured performance | The gate fails | Default unchanged; the gate runs with the default |
| Fifteen new exercises are a lot of work | The milestone slips | Do them chapter by chapter, and release when the Part is complete |
