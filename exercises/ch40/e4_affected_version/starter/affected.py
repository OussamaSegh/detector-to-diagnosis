# SPDX-License-Identifier: MIT
"""Exercise 40.4: is the version we ship affected by an advisory?

Two kinds of version meet here. The project's (upstream) versions, which an advisory's ranges are
written in: OpenSSL's are numbers with, before 3.0, a letter suffix for each patch release
(1.1.1, 1.1.1a, ..., 1.1.1z, 1.1.1za, ...). And the distribution's package versions, which say what
is installed: `[epoch:]upstream[-revision]`, compared as dpkg compares them.

This starter runs and gives plausible answers. TODO: make the tests pass.
"""


def openssl_key(version):
    """A sort key for an OpenSSL version."""
    return tuple(int("".join(ch for ch in part if ch.isdigit())) for part in version.split("."))


def upstream_affected(version, ranges):
    """True if version is in any [introduced, fixed) range; fixed None means not fixed yet."""
    k = openssl_key(version)
    return any(openssl_key(i) <= k and (f is None or k < openssl_key(f)) for i, f in ranges)


def debian_compare(a, b):
    """-1, 0 or 1 as package version a is older than, equal to or newer than b."""
    return (a > b) - (a < b)


def upstream_of(package_version):
    """The upstream part of a package version."""
    return package_version.split("-")[0]


def verdict(package_version, ranges, distro_fixed=None):
    """'affected', 'not-affected', 'affected-upstream' or 'not-affected-upstream'."""
    if upstream_affected(upstream_of(package_version), ranges):
        return "affected"
    return "not-affected"
