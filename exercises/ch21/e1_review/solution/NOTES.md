# Exercise 21.1: notes on the solution

**What the checklist found.** Section 3 (concurrency) asks, for each shared variable, which
threads write and read it and what orders the accesses. The header says which thread calls what,
so the answer is right there: counts_ has one writer and one reader and nothing orders them. That
is the most serious finding, and the one that tests will not find: the unit test runs one thread.

Sections 2.2 (boundary values) and 2.5 (lifetime) find the two other blockers by looking at each
loop bound and each returned view. Section 2.1 (error paths) finds set_window(). The unbounded
loop of add() is found by asking what the first call does, which is a boundary value too: the
initial state of latest_s_.

**Why the first finding names a fix but does not insist on one.** The author decides how to fix
it (checklist, section 7). A mutex is simplest and costs a lock per batch on the receive thread,
which is fine at a few thousand batches per second; atomics per slot avoid the lock but need the
window logic to tolerate a slot that changes during the sum.

**The question at the end.** A review also checks that the change is what its description says.
Here the description promises a status field the diff does not add. Asking costs nothing and
saves a second change request.

**What a reviewer should not do.** Rewrite the code in the review, or list ten minor style points
that bury the three blockers. The grading allows two blocker or major findings that point at no
seeded defect, because a real diff often has more to say, but each one costs the author time.
