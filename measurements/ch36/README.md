# Chapter 36 measurements: MiniDAQ's history under the commit policy

`history.txt` is the output of `python3 measurements/ch36/history.py measurements/ch36/history.txt`
(a few seconds) in a whole clone with its tags. It prints counts only: no address, name or message
of a commit. The commit it was measured at is on its first line.

What it shows:

1. The history: its commits, merges and the first-parent line of `main`, how many identities made
   it, and its annotated tags (every chapter and release tag is annotated).
2. Every rule of policy 1 over the whole history and from the first change request on. The old
   history breaks the rules review (no parsed trailer), layout (bodies wrapped at about 100
   characters, the width of the book's prose) and subject on most commits; that is why the
   policy starts after them, at the commit named in `tools/commit_policy.json`.
3. **Found while measuring:** a rule that put five documents as whole files under control fired
   on commits after change control began that changed no requirement: verification evidence of
   the SRS, the wording of the risk management plan. With the requirement, the hazard and the item
   as the unit, it fires on none of them, and on three commits from before the first change
   request.
4. **Found while measuring:** the line `Review:` is in 191 commits and is a trailer in none, by
   this tool and by `git log --format=%(trailers:key=Review)`: it stands above a blank line and
   the co-author lines, so git's trailer block is only the last paragraph. The policy moves it
   into the block.
5. Widths of subjects and of the longest body line.
6. Content addressing: the name of a file's content computed by hand equals `git hash-object`, and
   one changed bit changes the whole name.
7. The check takes about a second over the whole history.

Three merges made on the hosting service's web interface carry a personal address as author
(section 2, merges): the service uses the account's address for a merge it makes. They are left
in the history by the owner's decision (ADR 0031); merges are made locally since.
