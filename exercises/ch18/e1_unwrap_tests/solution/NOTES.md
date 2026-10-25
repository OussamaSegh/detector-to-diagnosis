# Exercise 18.1: notes on the solution

Sixteen tests in five groups: before the first wrap, across a wrap, late words, a starting
epoch, the epoch reported. Each test is named for one behavior of the specification and
compares whole sequences where it can, so a failure shows every time that came back wrong.

The two starter tests kill none of the seven mutants: every mutant behaves like the real code
until the first wrap or the first late word. What each mutant needed:

| Mutant | Mistake | Killed by |
|---|---|---|
| 1 | does not remember the new code after a wrap | `TheWordsAfterAWrapStayInTheNewPeriod`: the second word after a wrap looks like another wrap |
| 2 | a late word from before a wrap gets the new period | `ALateWordFromBeforeTheWrap` |
| 3 | never remembers that it has seen a word | any wrap: every word is taken as the first |
| 4 | uses a whole period as the threshold | any wrap: no difference exceeds a period |
| 5 | ignores the starting epoch | `AStartingEpochIsAddedToEveryTime`, `TheEpochIsReported` |
| 6 | computes the new epoch without storing it | `TheWordsAfterAWrapStayInTheNewPeriod`, `TheEpochCountsTheWraps` |
| 7 | `time_code - last_` in unsigned arithmetic without checking which is larger | `ALateWordInTheSamePeriod`: the difference wraps around to a huge number |

Mutants 1 and 6 are the lesson: a test with one word after the event looks complete and is not.
Mutant 7 is a real class of defect: unsigned subtraction never goes negative, so a comparison of
a difference with a threshold needs to know the order first.

The first version of `ManyWrapsInARow` broke the precondition itself: it stepped by two thirds
of a period, more than half, and failed on the real code. A test of code with a precondition
must respect it, and a test that fails on correct code is worth reading twice before the code is
changed.

Behavior exactly at half a period (a difference of 2^37 codes) is not specified (SRS-FMT-012
says "less than half"), so no test checks it: a test of unspecified behavior pins down an
accident of the implementation.
