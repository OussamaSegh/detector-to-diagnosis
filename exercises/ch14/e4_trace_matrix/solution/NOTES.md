# Exercise 14.4: notes

- **Names, not lines.** A line number changes whenever anything above the test changes, so a
  matrix with line numbers would differ after almost every commit and the out-of-date check
  would fail for changes that do not touch the trace. A test's file and name change only when
  the test does, which is exactly when the reviewer should look at the trace.
- **Committed and checked.** A matrix generated only at release time shows its gaps when
  there is least time to close them, and its history says nothing. Committed, every pull
  request that changes it shows the change to the trace in its diff, the reviewer sees a
  requirement losing its last test, and the check (`docs.trace`) stops a gap on the day it
  appears.
- **What the matrix does not prove.** A tag says that a test claims to verify a requirement,
  not that it does. Reviewing that each tagged test really checks its requirement's
  acceptance criteria stays a human task, and the matrix tells the reviewer where to look.
