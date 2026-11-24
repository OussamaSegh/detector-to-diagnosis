# Roadmap for release 2.3.0

Status: accepted. Drafted on 2026-11-24, after the release of 2.2.0 (tag `book-v2.2.0` on
c4b5ca3) and the merge of its independent review (PR #23, 14bd28b). Accepted the same day by the
coordinator under the author's standing delegation ("I am the customer, you are the planner and
builder, you approve and decide", 2026-11-23) and the direction that work go on release by
release, each planned before it starts (2026-11-16).

## 1. Where 2.2.0 leaves the project

- **The book.**
  - The Second Edition has 40 chapters in ten Parts and Appendix A.
  - The PDF has 794 pages, which leaves 34 pages under KDP's limit of 828. The solutions manual
    has 233 pages.
  - The book has about 240 figures, all drawn or generated, and no photos. An audit of every
    chapter on 2026-11-24 found no picture of anything physical. It also found few images of
    data as the team sees it, and fourteen long sections with no figure
    ([`ROADMAP-2.3.0-illustrations.md`](ROADMAP-2.3.0-illustrations.md), section 1).
- **Open problem reports.**
  - MDQ-PR-006 is unchanged until control API 4.0 (roadmap 3.0.0).
  - MDQ-PR-096 is the latency criterion ACC-04. It failed twice on the release machine, and
    2.2.0 was released with a recorded deviation. The control soak shows 2.2.0 no worse than
    2.1.0 on that machine. It does not show SRS-PERF-022 met: 19 of 1,200 intervals, 1.58%,
    against the 1% allowed (review of 2.2.0, MDQ-PR-099).
- **Due at 2.3.0.**
  - SDP version 24, a draft that gives section 8 its deviation path (MDQ-PR-099), to approve.
  - The effectiveness check of CAPA-0007: the release facts are written once.
  - The internal audit, and the SOUP review for 2.3.
- **Left by the review of 2.2.0** (HANDOFF):
  - `minidaq/src/sim/synthetic_source.cpp` has two lines still indented as before the CR-0037
    refactor.
  - The edit hook formats a whole file. So the next edit of a file written before
    `.clang-format` reformats all of it, and a small change arrives with a large diff.
- **Proposed.** CR-0038: the latency is judged against the previous release's programs,
  interleaved on the same machine.

## 2. What 2.3.0 is for

2.3.0 is the last 2.x release: 3.0.0 is the final version (the author, 2026-11-24), so what
2.3.0 leaves open goes to 3.0.0, which closes it (`docs/ROADMAP-3.0.0.md`, section 9). The final
deliverable is a book ready to sell and one companion zip of MiniDAQ and the exercises; 2.3.0's
part of it is the illustrations, the photos and the page budget.

A minor version: compatible additions only (maintenance plan, section 4), and no interface
breaks. It does three things:

1. **It makes the book's explanations visual** where a picture teaches faster than a paragraph.
   That means physical views of the scanner and its electronics, data as the team sees it,
   mechanisms built up step by step, and photos under a licensing policy.
2. **It makes the latency criterion able to tell the machine from the code**, so that a release
   is neither stopped by a busy host nor passed on a quiet one, and SRS-PERF-022 can be judged
   again.
3. **It closes what 2.2.0 left open**: the deviation path in the plan, the formatting debt, and
   CAPA-0007's check.

## 3. Themes and scope

### Theme I: illustrations and photos

The plan is [`ROADMAP-2.3.0-illustrations.md`](ROADMAP-2.3.0-illustrations.md), accepted
on 2026-11-24. Its five prototypes came with PR #22, merged as 0c4a6cd. This
roadmap adopts its sections 3 to 8 as they stand. In summary:

- **Photo policy** (its section 3). Drawn and generated figures stay the default. A photo
  must be in the public domain, CC0 or CC BY; never BY-SA, NC, ND or a product photo.
  - A photo shows no face, patient data, brand or identifiable place.
  - Its metadata is stripped.
  - It has an entry in `book/figures/photos/credits.json`, with a license page that a person
    has read.
  - `book/LICENSE` names the photos' own licenses.
- **Milestones** (its section 4):
  - M1: the photo pipeline and its checks, with a change request for the new check in
    `book.figures`.
  - M2: Part II's physical and data views.
  - M3: Parts V and VI, and the front-matter map.
  - M4: up to ten photos, through a manual GitHub Actions job, since Commons is not
    reachable from the sessions.
  - M5: the long sections without a figure.
  - M6: the B/W proof, EPUBCheck and the page budget.
- **About 30 new figures and up to 10 photos**, at most 12 to 15 pages. P3 items move to
  3.0.0 first if the budget is short.
- Book only: no change to MiniDAQ's code, requirements, risk controls or interfaces.

### Theme L: the latency judged against the previous release (CR-0038, MDQ-PR-096)

- **The A/B soak.** Part 3 of the release checks soaks the previous release's programs and
  the candidate's on the same machine in the same session.
  - The two soaks are interleaved in blocks of 20 minutes each, so a slow spell of the host
    falls on both. Each program runs 100 minutes in all.
  - The previous release is built from its tag in a scratch worktree, as the regression gate
    already does for the benchmarks (`tools/perf_ab.sh`).
  - `tools/soak.py` records the per-second measure for both.
- **Two verdicts, kept apart** (CR-0038, as the review corrected it):
  - ACC-04 stays absolute: at most 1% of the candidate's intervals above 10 ms.
  - A new criterion, ACC-10, compares the two counts with Fisher's exact test (one-sided,
    α 0.05). It says whether the candidate is worse than the previous release on the same
    machine.
  - A release that fails ACC-04 but not ACC-10 is released only with a deviation, under SDP
    version 24, section 8. A release that fails ACC-10 has a problem report against the
    commit.
- **The cost.** Part 3 gets about 100 minutes longer. The release checks already run as
  `resume` parts, and the A/B soak is a resumable step of its own. A run stopped by the
  two-hour limit restarts at the soak block it was in, not at the start of the soak.
- **MDQ-PR-096** closes when ACC-04 passes on a release soak, or when CR-0038's comparison and a
  documented machine change explain the rate. Until then it stays open with its decision.
- **Records:**
  - CR-0038 approved and implemented.
  - The acceptance specification gains ACC-10.
  - The system test plan, SDP section 6 (the soak) and the record skeleton's soak rows change.
  - A test of the comparison against the recorded soaks of `measurements/mdq-pr-064/` and
    `measurements/mdq-pr-096/`.

### Theme H: housekeeping from 2.2.0

- **SDP version 24** is approved at the release, with any change 2.3.0 adds (Theme L's soak in
  section 6).
- **Formatting debt.**
  - Format the two lines of `synthetic_source.cpp`.
  - Change the edit hook so that it formats only the lines an edit touched
    (clang-format `--lines` on the file's diff against HEAD), not the whole file, and give it a
    unit test.
  - No whole-tree format commit. ADR 0027 chose to format the code as it is edited and to
    keep each line's history; a format commit would touch 334 C++ files and shift the `lines=`
    listings of the book. With the hook formatting touched lines, the reason for such a commit
    is gone (decided 2026-11-24, MDQ-PR-102). `tools/check_format.py` keeps judging touched
    lines.
- **CAPA-0007's effectiveness check** at the internal audit. It is effective if no fact of the
  release checks was found written twice in 2.3.0-dev, and if the test that reads
  `tools/release_facts.json` still fails on a copy written back.
- **The plan of 3.0.0** gets its 2.3.0 row in section 5.

## 4. Order and milestones

| Milestone | Content | Exit criterion |
|---|---|---|
| 2.3.0-dev, first | Theme H: the hook that formats touched lines, `synthetic_source.cpp`; `tools/post_release.py . 2.3.0-dev` and the SOUP review for 2.3 | The hook's test passes; `synthetic_source.cpp` formatted; CI green |
| 2.3.0-dev, second | Theme L: CR-0038 approved, the interleaved A/B soak with resume, ACC-10, its tests against the recorded soaks | The comparison test passes on the recorded soaks; a full A/B soak runs on the machine |
| 2.3.0-dev, third | Theme I, M1 to M3 (pipeline, Parts II, V and VI, the map), in the illustrations thread | `figures.py check` covers photos; all P1 items merged |
| 2.3.0-dev, fourth | Theme I, M4 and M5 (photos, the long sections) | Each photo has a credit checked by a person; the list of section 1 closed item by item |
| 2.3.0 | Internal audit with CAPA-0007's check, SDP v24 approved, Theme I's M6 (B/W proof, EPUBCheck, page budget), full release checks with the A/B soak | CI green on the release commit; tag `book-v2.3.0` |

Themes H and L are MiniDAQ and tool work, done in this build thread. Theme I is book work,
done in the illustrations thread. The two touch different files: Theme I touches `book/` and
the chapters; Themes H and L touch `tools/`, `minidaq/` and `docs/regulatory/`. The chapter
text that describes the soak (Chapter 33) is edited only once, in Theme L, after Theme I's
edits to it are merged.

The rhythm stays as before:

- Every release gets an independent review on an Opus model.
- That review's fixes go out in the next patch or minor release.
- Each controlled document that changes is approved before the release checks, by the author
  or by the coordinator under the author's delegation.

## 5. Acceptance

- The release checks pass on one commit, with the A/B soak. ACC-01 to ACC-10 pass, or a
  failure has a deviation recorded under SDP version 24 and named row by row.
- Theme I's acceptance, from its plan, section 6:
  - `figures.py check` has 0 problems, photos included.
  - Every figure builds in the three profiles and the EPUB, with no overfull box.
  - EPUBCheck passes.
  - Every figure is referenced, has alt text, and reads in gray.
  - Drawings of hardware say "drawn, not to scale".
  - The screen PDF stays under 828 pages.
- The edit hook's test shows that an edit of one line in an unformatted file changes that line
  only.
- CAPA-0007 is evaluated and closed or extended.
- The independent review of 2.3.0 covers the figures and the A/B soak.

## 6. Out of scope for 2.3.0

- **Breaking changes**: control API 4.0, schema 3.0 and the list-mode format MDQ-P2 wait for
  3.0.0.
- **Part XI's chapters.**
- **New third-party dependencies**, unless the author approves each one. Theme L uses the
  standard library; Fisher's exact test is a few lines of Python. Theme I uses TikZ,
  matplotlib and poppler, which already build the book.
- **A faster or dedicated release machine.** CR-0038 measures the machine instead of
  replacing it. A bare-metal reference machine is a question for 3.0.0.
- **Redrawing existing figures**, animations, and any figure of real patient data.

## 7. Risks

| Risk | Effect | Response |
|---|---|---|
| The A/B soak doubles part 3's time | Release checks of about five hours, more restarts at the two-hour limit | Resumable soak blocks; part 3 is the only part that grows |
| Interleaving still leaves the two soaks under different host load | ACC-10 blames the code or the machine wrongly | Blocks of 20 minutes, alternating; the per-second steal and run-queue measure kept for both; the test is one-sided and its power stated in the record |
| ACC-04 keeps failing on this machine for every release | Every release needs a deviation | ACC-10 tells whether the code got worse; the question of a quieter machine goes to 3.0.0; the deviation path is in SDP v24, not invented each time |
| A photo's license is wrong | An infringing image in a public repository | Theme I's policy: only PD, CC0 and CC BY; a person reads every license page; removed at once on doubt |
| Page budget | The PDF passes 828 pages | Measured after each milestone; P3 items move to 3.0.0 first |
| Two threads edit the same files | Merge conflicts | Theme I keeps to `book/` and the chapters; Chapter 33 edited once, after Theme I's edits to it |
