# Exercise 37.4: notes on the solution

## 1. The real lock file

Of the 30 pins of `analysis/requirements.lock`, one pair looks alike: `numpy` and `numba`, two
substitutions apart, both legitimate and both on the SOUP list. Every other pin is near nothing
else. A look-alike finding is a question for a person, not a verdict: here the answer is in the SOUP
list, which names both with their purposes, and the reviewer confirms the suggestion is the one the
code imports. What the finding guards against is the other case, a name one keystroke from an
approved package that nobody on the team has heard of.

## 2. scapy

Not a false positive in the sense that matters. `scapy` is a packet manipulation library and has
nothing to do with `scipy`; a suggestion of `scapy` in an analysis package is either a typo or a
confusion, and either way it is not approved. The check flags a name for a person to look at; it
cannot know intent. A check that never flags a legitimate package would also miss the
typosquatted ones, which are registered precisely to look legitimate.

## 3. What the check cannot know

Whether the package exists on the index (an assistant can invent a plausible name, and someone can
register that name later, which is called slopsquatting), its latest version, and its advisories.
`tools/lock_audit.py` asks the index for every pin and reports the advisories it lists; Chapter 37
tells how it refused the first pin of pydicom. Its exit status 2 means the index could not be read, and that must fail
the check: an audit that did not run says nothing about the pins, and treating it as clean is how a
vulnerable version gets in on the day the network is down.
