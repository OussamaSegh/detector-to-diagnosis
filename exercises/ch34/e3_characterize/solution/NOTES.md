# Exercise 34.3: notes

The starter's two tests pass on the original and catch one change of seven: the seventh, because
1,000 counts divided by a million microseconds is 0 before the scaling. The other six, including
both "fixes", pass them.

The solution has nine tests, one per behavior, and every change fails at least one:

| Change | What it does | Caught by |
|---|---|---|
| 1 | no interval shows 0 instead of error -1 | NoIntervalIsErrorMinusOneEvenAtZero |
| 2 | a dead block becomes error -1 ("fix") | ABlockDeadTheWholeIntervalShowsZeroNotAnError |
| 3 | the live time is not cut to the interval | ALiveTimeLongerThanTheIntervalIsCutToTheInterval |
| 4 | the rate is rounded ("fix") | TheRateIsTruncatedNotRounded |
| 5 | the display limit becomes 5 M | TheDisplayLimitIsFiftyMillionAndItIsReached |
| 6 | a negative count shows 0 | ANegativeCountIsErrorMinusTwo |
| 7 | the division comes before the scaling | CountsAreScaledBeforeTheDivision |

By hand:

1. Changes 2 and 4 are fixes in the eyes of whoever makes them (an error is more honest than 0,
   rounding is more accurate than truncating); 1, 3, 5, 6 and 7 are mistakes. To the tests they
   are the same: each changes what the display, the service tools and the scripts receive, and
   nobody decided it. A fix is made by changing the test on purpose, in the same reviewed change,
   with the reason.
2. In the test (a comment, as here), and in a problem report that names the behavior and its
   consequence (a dead block cannot be told from a quiet one). Whether it changes is a decision of
   whoever owns the display's requirements, after an impact analysis of everything that reads the
   value: the change control of the item.
3. A characterization test is read later by someone who wants to change the behavior. Its name is
   the only statement of what the old code did; "TheRateIsTruncatedNotRounded" tells them what
   they are about to change, "Case7" does not.
