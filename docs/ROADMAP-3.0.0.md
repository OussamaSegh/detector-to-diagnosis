# Roadmap for release 3.0.0

Status: proposed. The author asked for it on 2026-11-16. Section 7 holds the questions that only
the author can answer, each with a recommendation. Work on 3.0.0 starts after release 2.1.0
(`docs/ROADMAP-2.1.0.md`). Nothing here changes 2.0.1 or 2.1.0.

## 1. Where 2.x will leave the project

- **The book.**
  - The Second Edition has 40 chapters in ten Parts and Appendix A, in 819 pages.
  - KDP's paperback limit is 828 pages.
  - Release 2.1.0 makes room with a denser layout, or by moving Appendix A online, and spends
    that room on depth in Parts VI to X. A new Part of three chapters (75 to 100 pages) will not
    fit in one volume afterwards.
- **What 2.0.0 left out on purpose** (roadmap 2.0.0, section 3, Theme C, candidates 4 and 5):
  - scaling the acquisition from one acquisition PC to several;
  - GPU reconstruction.
- **What the 2.x interfaces cannot change in a minor release** (maintenance plan, section 4):
  - The control API is a request and reply protocol, so a client learns of a fault only by
    asking.
  - The service learns of a port's fault by polling every 20 ms. This is MDQ-PR-006, a known
    anomaly decided again for 1.3.0. Making it event-driven touches every port and the control
    API.
  - The configuration and the list-mode format describe one acquisition PC.
- **The platform.**
  - C++23 is limited to what GCC 13 supports, the compiler of Ubuntu 24.04 (roadmap 2.0.0,
    answer 4).
  - `std::print`, explicit object parameters and `std::ranges::to` wait for a newer compiler.
  - Ubuntu 26.04 LTS is the next long-term release (verify: its GCC and Clang versions, and the
    date its GitHub runner image is generally available).
- **Standards.** The book cites IEC 62304:2006 with Amendment 1:2015, which is still the edition
  harmonized under the MDR (verify: the state of the second edition of IEC 62304 and of the
  harmonized standards list before writing).

## 2. What 3.0.0 is for

A major version: a Third Edition of the book and a breaking release of MiniDAQ.

1. **A scanner with more than one acquisition PC.** MiniDAQ acquires from several readout nodes,
   sorts coincidences across them, and survives the loss of one node, all within a single
   process tree that the book can run on one machine.
2. **Run control that tells instead of being asked.** The control API pushes the run's events
   and faults to its clients, and the service hears each port's fault when it happens. That
   closes MDQ-PR-006.
3. **The full C++23 on the next LTS platform**, with the text of Part I updated once.
4. **Room for the whole book**, in the format the author chooses (section 7, question 1).

## 3. Themes and scope

### Theme K: the Third Edition's format

- Two volumes are the last resort of roadmap 2.0.0 (answer 5). With a new Part they become
  necessary:
  - Volume 1, "The System and the Process", holds Parts I to V.
  - Volume 2, "From Data to Diagnosis", holds Parts VI to XI and Appendix A.
  - Each volume has its own index, and the cross-references between volumes name the volume.
- The solutions manual stays one book.
- The web edition stays one site; the volumes are only a print matter.
- KDP's rules on a new edition and on a set of volumes are to be checked before the files are
  made (verify:).

### Theme L: Part XI, the acquisition at scale (three chapters)

Each chapter follows the chapter recipe: code, tests, exercises, measurements and review. Each
runs on one machine, with nodes as processes on the loopback interface or in network
namespaces, so no new hardware is needed.

1. **Chapter 41, more than one acquisition PC.**
   - How a scanner's blocks are divided among readout nodes.
   - Partitioning the coincidence search at the node boundaries.
   - The merge of time-ordered streams from several nodes.
   - The node's identifier in the list-mode format.
   - Measured throughput with one to four nodes.
2. **Chapter 42, a node that fails.**
   - Detecting the loss of a node in time.
   - What a run may keep and what it must mark incomplete (RC-01 extended).
   - Restarting a node within a run, or not.
   - The risk analysis of a partial scan (ISO 14971, new hazards).
   - The integrity verdict across nodes.
3. **Chapter 43, run control for a distributed system.**
   - Events pushed to clients (API 4.0).
   - An event-driven fault path in the service, which closes MDQ-PR-006.
   - Time across nodes, which builds on Chapter 38's time base.
   - Upgrading a fleet of nodes with the update slots of Chapter 25.

### Theme M: breaking changes, grouped once

Each item gets a change request, an ADR, a migration note (`docs/migration-3.0.md`) and a test
that the old form is refused clearly.

- **Control API 4.0**: a subscription to the run's events and faults, beside the replies. The
  clients and the book's transcripts move to it, and `minidaq_ctl wait` stops polling.
- **Configuration schema 3.0**:
  - The topology: nodes, which blocks each node reads, and the merge.
  - The single-PC configuration of 2.x remains valid as a one-node topology, and
    `tools/migrate_config.py` converts it.
- **List-mode format MDQ-P2**:
  - Each event carries its node.
  - The header names the topology.
  - Readers of 3.0 still read MDQ-P1, read-only.
- **Removed**: the 1.x configuration path of `tools/migrate_config.py`, which 2.0 kept for one
  major version.

### Theme N: the platform

- The baseline compiler moves to the one of Ubuntu 26.04, if its runner image is generally
  available by 3.0.0-dev.
- C++23 is used in full where it makes the code clearer: `std::print`, explicit object
  parameters, `std::ranges::to`, and `std::expected` as before.
- Modules stay out until both compilers and CMake support them without workarounds.
- A SOUP review for 3.0: every dependency at the version of the new platform.
- The Mac setup (OrbStack Ubuntu VM) moves to the same release.

### Theme O: the regulatory chapters, checked again

- Chapters 13 to 17 are checked against the standards and guidance in force at 3.0.0-rc:
  - IEC 62304 and its second edition (verify:);
  - IEC 81001-5-1;
  - the MDR's harmonized standards;
  - FDA's cybersecurity guidance.
- Every "verify:" that this raises is settled before the release.

## 4. Order and milestones

| Milestone | Content | Exit criterion |
|---|---|---|
| 2.1.0 | Its own roadmap | Released |
| 2.2.0 | Groundwork that breaks nothing: several simulated nodes in the simulator, a node identifier in the status, a merge of time-ordered streams inside one process, and measurements | Release checks pass; the merge is measured |
| 3.0.0-dev, first | Theme N (platform, C++23 in full, SOUP review for 3.0) | Every preset green on the new compiler; Part I updated |
| 3.0.0-dev, second | Theme M (API 4.0, schema 3.0, MDQ-P2), with the earlier chapters, exercises and solutions updated to the new interfaces | `docs.interfaces` passes; migration note complete |
| 3.0.0-dev, third | Chapters 41 to 43 (Theme L), written against the new interfaces | Chapter recipe complete for each |
| 3.0.0-rc | Theme O, Theme K (two volumes), the whole-book review | Each volume within 828 pages; KDP files built |
| 3.0.0 | Third Edition: internal audit, full release checks, KDP files | CI green on the release commit; tag `book-v3.0.0` |

The rhythm stays as before:

- Every release gets an independent review on an Opus model.
- The fixes of that review go out in the next release.
- Breaking changes are grouped in one milestone, so that the text about interfaces is rewritten
  once (the lesson of 2.0.0).

## 5. Out of scope for 3.0.0

- **GPU reconstruction**, unless the author approves a dependency for it (section 7,
  question 3).
- **A real scanner's data or any manufacturer's product.** The book stays generic.
- **New third-party dependencies** without the author's approval of each one. Theme L needs
  none: the nodes use the sockets and the formats that MiniDAQ already has.
- **A translation, a video course or a hardcover edition.**

## 6. Risks

| Risk | Effect | Response |
|---|---|---|
| Partitioning the coincidence search loses coincidences at node boundaries | Wrong counts; a hazard | The boundary overlap is specified first, tested with property tests against the single-node sorter, and measured |
| A distributed system on one machine hides network effects | The book teaches what a real cluster would contradict | Network namespaces with delay and loss (tc netem of iproute2; verify: that CI's runners allow it) for the failure chapter; state the limits in the text |
| The new platform is late on GitHub's runners | Theme N waits | Theme N moves after Theme M; nothing else depends on it |
| API 4.0 comes soon after API 3.0 | Readers' clients break twice | The migration note, a refusal that names it, and a converter where one is possible |
| Two volumes change the book's references | Broken cross-references | `book.xrefs` learns volumes; the web edition stays one site |
| Scope grows | The edition never ships | The Part XI list is fixed at the start; anything else goes to a later edition |

## 7. Questions for the author

1. **Format of the Third Edition.** Two volumes in print (recommended, since a new Part does not
   fit in 828 pages), or one volume with Appendix A and the solutions online only?
2. **New material.** Part XI on the acquisition at scale (recommended), or something else, for
   example fleet operations and service of installed scanners?
3. **GPU reconstruction.** Keep it out (recommended), or approve a dependency (SYCL or CUDA) and
   accept that CI cannot run it?
4. **Breaking changes.** API 4.0 with pushed events, schema 3.0 and the list-mode format MDQ-P2,
   grouped in one milestone (recommended)?
5. **Platform.** Move to Ubuntu 26.04 and C++23 in full for 3.0.0 (recommended, if its runner
   image is available in time)?

Until the author answers, the work goes on with the recommendations, and nothing that cannot
be undone is done. Theme K is decided only before the KDP files are made, at 3.0.0-rc.
