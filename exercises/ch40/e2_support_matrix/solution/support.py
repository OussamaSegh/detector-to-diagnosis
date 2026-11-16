# SPDX-License-Identifier: MIT
"""Exercise 40.2: which releases are supported, and which SOUP needs a plan (solution)."""
import datetime


def _date(text):
    return datetime.date.fromisoformat(text)


def months_later(date, months):
    """The date `months` calendar months after `date` (a datetime.date), on the same day of the
    month, or the month's last day when it has no such day."""
    m = date.month - 1 + months
    y, m = date.year + m // 12, m % 12 + 1
    first_of_next = datetime.date(y + (m == 12), m % 12 + 1, 1)
    last = (first_of_next - datetime.timedelta(days=1)).day
    return datetime.date(y, m, min(date.day, last))


def _key(version):
    return tuple(int(x) for x in version.split("."))


def lines(releases):
    """{"X.Y": date of X.Y.0} from [(version, "YYYY-MM-DD")]; a line without its .0 is an error."""
    out = {}
    for version, date in releases:
        x, y, z = version.split(".")
        if z == "0":
            out[f"{x}.{y}"] = _date(date)
    missing = {".".join(v.split(".")[:2]) for v, _ in releases} - set(out)
    if missing:
        raise ValueError(f"no .0 release for the lines {sorted(missing)}")
    return out


def supported(releases, on, months=24):
    """The minor lines supported on the date `on`: from the date of X.Y.0 for `months` calendar
    months. A patch release does not extend its line's support."""
    day = _date(on)
    return sorted((line for line, start in lines(releases).items()
                   if start <= day < months_later(start, months)), key=_key)


def latest(releases, line):
    """The newest release of a minor line, by version number, not by date or list order."""
    found = [v for v, _ in releases if v.startswith(line + ".")]
    if not found:
        raise ValueError(f"no release of {line}")
    return max(found, key=_key)


def needs_plan(items, review, months=24):
    """The SOUP items whose support ends before `months` after the review date: {name: end date
    "YYYY-MM-DD" or None for no announced end}. Sorted by name."""
    horizon = months_later(_date(review), months)
    return sorted(name for name, end in items.items() if end is not None and _date(end) < horizon)
