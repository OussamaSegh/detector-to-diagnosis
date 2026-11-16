# SPDX-License-Identifier: MIT
"""Exercise 40.2: which releases are supported, and which SOUP needs a plan (starter).

TODO: the starter measures a line's support from its latest patch, counts a month as 30 days,
and sorts versions as text. See README.md."""
import datetime


def _date(text):
    return datetime.date.fromisoformat(text)


def supported(releases, on, months=24):
    """The minor lines supported on the date `on`."""
    day = _date(on)
    newest = {}
    for version, date in releases:
        line = version.rsplit(".", 1)[0]
        newest[line] = max(newest.get(line, _date(date)), _date(date))
    return sorted(line for line, start in newest.items()
                  if start <= day < start + datetime.timedelta(days=30 * months))


def latest(releases, line):
    """The newest release of a minor line."""
    return max(v for v, _ in releases if v.startswith(line))


def needs_plan(items, review, months=24):
    """The SOUP items whose support ends before `months` after the review date."""
    horizon = _date(review) + datetime.timedelta(days=30 * months)
    return sorted(name for name, end in items.items() if end and _date(end) <= horizon)
