---
name: release-checks
description: Runs MiniDAQ's release checks on one clean commit, applies the rerun rule of SDP section 8, and drafts the release record. Use it when a release candidate is ready and its CI is green.
allowed-tools: Read Bash(tools/release_checks.sh *) Bash(python3 tools/release_record.py *) Bash(python3 tools/acceptance.py *) Bash(tail *)
version: 1
owner: software lead
---

Every step is a command a person could run. Do not skip one, and do not record a result you
did not read.

1. **Prepare.** The candidate is one clean commit whose CI is green. Check it out in a git
   worktree outside the main tree, so that the main tree can keep changing, and choose an output
   directory OUT that is not in the repository.
2. **Run.** In the worktree:

   ```sh
   tools/release_checks.sh OUT 600 resume
   ```

   The checks take more than two hours. A command that runs in the background may be stopped at
   two hours by the agent's tool; then run the same command again with the same OUT: `resume`
   skips each part that `OUT/release-checks.txt` records as passed. A FAIL line written when the
   command was stopped is not a failed check: read which part was running.
3. **Read.** Read `OUT/release-checks.txt` to the end. Every part must be recorded as passed.
4. **A failed check.** Apply SDP section 8 (`docs/regulatory/sdp.md`): a failed check is not run
   again until its failure is investigated and the cause recorded in `OUT/rerun-part-N.md`. It
   may run again only when the investigation shows the failure is not in the commit (the same
   code as the previous release, or a fault of the machine or the tool with its own problem
   report), and at most once. A second failure is a problem report against the commit: stop and
   report it to the software lead.
5. **Accept.** Judge the acceptance criteria:

   ```sh
   python3 tools/acceptance.py OUT
   ```

   Every criterion must be PASS; MISSING and STALE are not a pass.
6. **Draft the record.** Copy OUT's evidence to `measurements/release-X.Y.Z/` (the README of
   an earlier release's folder, such as `measurements/release-2.1.0/`, shows what is kept), then

   ```sh
   python3 tools/release_record.py skeleton . X.Y.Z
   ```

   writes the record's rows from that folder. Save it as `docs/regulatory/releases/X.Y.Z.md`, then fill
   each `TODO(record):` line from the evidence, and check it:

   ```sh
   python3 tools/release_record.py check . docs/regulatory/releases/X.Y.Z.md
   ```

7. **Hand over.** Report the result of each part, any rerun with its investigation, and the
   record's draft to the software lead, who approves the release. Do not tag, push or package:
   those steps follow the software lead's approval.

## Document history

| Version | Change |
|---|---|
| 1 | First version (CR-0036, roadmap 2.2.0, Theme P2). |
