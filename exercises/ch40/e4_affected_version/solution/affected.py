# SPDX-License-Identifier: MIT
"""Exercise 40.4, a solution: is the version we ship affected by an advisory?

Two kinds of version meet here. The project's (upstream) versions, which an advisory's ranges are
written in: OpenSSL's are numbers with, before 3.0, a letter suffix for each patch release
(1.1.1, 1.1.1a, ..., 1.1.1z, 1.1.1za, ...). And the distribution's package versions, which say what
is installed: `[epoch:]upstream[-revision]`, compared as dpkg compares them. A distribution
backports fixes without changing the upstream part, so 3.0.13-0ubuntu3.5 can be fixed while upstream 3.0.13
is affected: the distribution's own advisory, which names the package version that fixes it,
decides.
"""
import re

_OPENSSL = re.compile(r"(\d+)\.(\d+)\.(\d+)([a-z]*)")


def openssl_key(version):
    """A sort key for an OpenSSL version: the three numbers, then the letters, where no letter comes
    first and a longer run of letters (za) after a shorter one (z)."""
    m = _OPENSSL.fullmatch(version)
    if not m:
        raise ValueError(f"not an OpenSSL version: {version!r}")
    letters = m.group(4)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)), len(letters), letters)


def upstream_affected(version, ranges):
    """True if version is in any [introduced, fixed) range; fixed None means not fixed yet."""
    k = openssl_key(version)
    for introduced, fixed in ranges:
        if openssl_key(introduced) <= k and (fixed is None or k < openssl_key(fixed)):
            return True
    return False


def _order(c):
    """dpkg's order of one character of a non-digit run: ~ first, then the end, letters, others."""
    if c == "~":
        return -1
    if c.isalpha():
        return ord(c)
    return ord(c) + 256


def _compare_part(a, b):
    """dpkg's comparison of an upstream version or a revision: alternate runs of non-digits
    (character by character, in _order) and digits (as numbers)."""
    while a or b:
        na = re.match(r"[^0-9]*", a).group()
        nb = re.match(r"[^0-9]*", b).group()
        a, b = a[len(na):], b[len(nb):]
        for i in range(max(len(na), len(nb))):
            ca = _order(na[i]) if i < len(na) else 0
            cb = _order(nb[i]) if i < len(nb) else 0
            if ca != cb:
                return -1 if ca < cb else 1
        da = re.match(r"[0-9]*", a).group()
        db = re.match(r"[0-9]*", b).group()
        a, b = a[len(da):], b[len(db):]
        ia, ib = int(da or 0), int(db or 0)
        if ia != ib:
            return -1 if ia < ib else 1
    return 0


def _split(version):
    if not re.fullmatch(r"(\d+:)?[0-9][A-Za-z0-9.+~:-]*", version):
        raise ValueError(f"not a package version: {version!r}")
    epoch, _, rest = version.partition(":") if ":" in version else ("0", "", version)
    upstream, _, revision = rest.rpartition("-") if "-" in rest else (rest, "", "")
    return int(epoch), upstream, revision


def debian_compare(a, b):
    """-1, 0 or 1 as package version a is older than, equal to or newer than b (dpkg's rules)."""
    ea, ua, ra = _split(a)
    eb, ub, rb = _split(b)
    if ea != eb:
        return -1 if ea < eb else 1
    return _compare_part(ua, ub) or _compare_part(ra, rb)


def upstream_of(package_version):
    """The upstream part of a package version: 3.0.13 for 1:3.0.13-0ubuntu3.5."""
    return _split(package_version)[1]


def verdict(package_version, ranges, distro_fixed=None):
    """'affected' or 'not-affected' when the distribution's advisory decides (distro_fixed is the
    package version that fixes it, or 'not-affected' when it says the package never was);
    otherwise 'affected-upstream' or 'not-affected-upstream', which only the upstream ranges
    decided and a person must confirm."""
    if distro_fixed == "not-affected":
        return "not-affected"
    if distro_fixed is not None:
        return "affected" if debian_compare(package_version, distro_fixed) < 0 else "not-affected"
    if upstream_affected(upstream_of(package_version), ranges):
        return "affected-upstream"
    return "not-affected-upstream"
