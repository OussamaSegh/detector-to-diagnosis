# Exercise 36.1 (E): The trailers git sees

**Goal.** Find the trailers of a commit message the way git finds them, so that a check of the
line `Review:` agrees with `git log --format=%(trailers)` and with every other tool that asks git.
A line that looks like a trailer is one only if git says so.

**Time.** 1 hour.

**What to write** (`trailers.py`):
- `trailers(message)`: a list of `(key, value)` pairs. The trailer block is the last paragraph of
  the message (paragraphs are separated by blank lines; blank lines at the end do not count), and
  never the first paragraph, which is the subject. It counts only if every line in it is a
  trailer, `Key: value` with a key of letters, digits and hyphens that starts with a letter or a
  digit, or a continuation, a line that starts with white space and adds to the value before it
  (joined with one space). Otherwise there are no trailers. This is git's rule for a block without
  a `Signed-off-by:` line; leave that case out.
- `value(message, key)`: the values of every trailer with that key, compared without regard to
  case, as `git log --format='%(trailers:key=...)'` does.

**Starter.** `starter/trailers.py` takes every line of the message that looks like `Key: value`,
wherever it is.

**Acceptance** (`tests/test_trailers.py`):
- For each message of the tests, the result equals `git interpret-trailers --parse` on it: a
  block of trailers; a `Review:` line above a blank line and another paragraph; a subject that
  looks like a trailer; a block with one line of prose; a continuation; blank lines at the end;
  a URL; `Note:` in the body.
- `value` finds `review:` and `Review:` alike and returns them in order.

**Then, by hand.**
1. MiniDAQ's commits until Chapter 36 put `Review:` in a paragraph of its own above the
   co-author lines. What did git make of it, and which tools would have noticed?
2. Why does git not take any line of the form `Key: value` as a trailer?
3. Write a message whose body has the line `Fixes: the sorter's overflow` in the middle. Is it a
   trailer? Should a tool that closes problem reports read it?
