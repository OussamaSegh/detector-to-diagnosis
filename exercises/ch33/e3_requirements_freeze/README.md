# Exercise 33.3 (M): A requirements freeze that sees every change, and only changes

**Goal.** Compare a requirements specification with the baseline taken when it was frozen, and
list every requirement added, changed or removed since that no accepted change request names. The
rules are those of `tools/req_baseline.py`, on strings instead of files.

**Time.** 2 hours.

**The inputs.** The SRS is Markdown with one table row per requirement:

    | SRS-SYS-006 | Over a clean link, the server shall write ... | tools | T |

(ID, text, software item, verification method). The baseline is `{id: digest}`. A change request
is `{"name": "CR-0020", "status": "approved", "text": "..."}`; it names a requirement when the ID
appears anywhere in its text, and it counts only when its status is `approved` or `implemented`.

**Starter.** `starter/freeze.py` finds an added requirement and a changed word. It also reports a
table that was only rewrapped, never notices a requirement that was deleted, and lets a proposed
or rejected change request cover a change.

**Acceptance** (`tests/test_freeze.py`):
- `digests`: the same digest for a row whose spaces were changed or whose cells were padded
  differently; a different digest when a word of the text, the item or the method changes; rows
  that are not requirements (the header, the separator, prose that mentions an ID) are ignored.
- `differences`: added, changed and removed, sorted by ID, nothing for an unchanged SRS.
- `unexplained`: every difference that no approved or implemented request names; a proposed or a
  rejected request names nothing; one request may name several requirements.

**Then, by hand.**
1. Why a digest and not the text itself in the baseline? What would a reviewer lose, and gain?
2. A change request that says "SRS-SYS-001 does not change" names SRS-SYS-001 under these rules.
   Is that a hole? How would you close it without parsing English?
3. When is a new baseline taken, and why must the tool not take one on its own when the check
   fails?

**Hints.** Normalize white space with `" ".join(s.split())`. Match the ID with a pattern that is
anchored to the start of a row, so a mention in prose is not a requirement.
