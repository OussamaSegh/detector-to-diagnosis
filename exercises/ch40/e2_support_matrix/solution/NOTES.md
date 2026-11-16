# Exercise 40.2: notes

The starter fails every test: it measures support from a line's newest release, so a patch keeps
the line alive; its 30-day months end 1.1 eleven days early; it sorts `1.10` before `1.3` and
`1.3.2` after `1.3.10`; and it asks for a plan for an item whose support ends exactly on the
horizon.

Design choices:

- Support is a promise made when the line is released, so it starts at `X.Y.0` and nothing later
  moves it. A site can plan with the date in the release notes.
- Calendar months, with the last day of a short month: the period a person reads in a plan is
  "24 months", and "730 days" is a different date.
- Versions compare as tuples of integers. Text comparison is right for every version until the
  first `1.10`, which is why it survives so long.
- `needs_plan` uses "before the horizon": an item supported until the horizon's own day covers the
  whole period.
- The function does not decide what that plan is. It says which items need one; the plan itself
  (upgrade, another supplier's backports, or a reason to stay) is a decision recorded in the SOUP
  list.
