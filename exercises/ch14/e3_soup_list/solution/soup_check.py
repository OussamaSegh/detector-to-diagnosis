"""Exercise 14.3: check a SOUP list against the pins of the build.

pins() reads every FetchContent_Declare of a CMake file: the dependency's name, its version
and its pin (the git commit, or the archive's SHA-256). check() returns every way in which a
SOUP list fails to identify what the build uses, or lacks what a reviewer needs.
"""
import re

DECLARE = re.compile(r"FetchContent_Declare\(\s*(\w+)(.*?)\)", re.S)
FIELDS = ("Identification", "Purpose", "Requirements", "Known anomalies", "Risk", "Last review")


# [snippet:pins]
def pins(cmake_text):
    """[(name, version, pin)] for every FetchContent_Declare."""
    out = []
    for name, body in DECLARE.findall(cmake_text):
        tag = re.search(r"GIT_TAG\s+([0-9a-f]{40})(?:\s*#\s*v?(\S+))?", body)
        url = re.search(r"URL\s+(\S+)", body)
        digest = re.search(r"URL_HASH\s+SHA256=([0-9a-f]{64})", body)
        if tag:
            out.append((name, tag.group(2), tag.group(1)))
        elif url and digest:
            v = re.search(r"/v(\d+\.\d+\.\d+)/", url.group(1))
            out.append((name, v.group(1) if v else None, digest.group(1)))
        else:
            out.append((name, None, None))  # a branch or tag name is not a pin
    return out
# [/snippet:pins]


def tables(soup_text):
    """{item name: {field: value}} for every '| Field | <name> |' table."""
    out = {}
    for m in re.finditer(r"^\| Field \| (.+?) \|\n\|[-| ]+\|\n((?:\|.*\|\n?)+)", soup_text, re.M):
        rows = {}
        for line in m.group(2).splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 2:
                rows[cells[0]] = "|".join(cells[1:])
        out[m.group(1).strip()] = rows
    return out


# [snippet:check]
def check(cmake_text, soup_text, minidaq_version, shipped):
    """Problems of a SOUP list; `shipped` names the dependencies that ship with MiniDAQ."""
    errors = []
    minor = ".".join(minidaq_version.split(".")[:2])
    items = tables(soup_text)
    for name, version, pin in pins(cmake_text):
        if pin is None or version is None:
            errors.append(f"{name}: not pinned to a commit or a hash with a version")
            continue
        if pin not in soup_text or version not in soup_text:
            errors.append(f"{name}: the SOUP list does not name version {version} and pin {pin}")
        if name not in shipped:
            continue
        table = next((t for t in items.values() if pin in t.get("Identification", "")), None)
        if table is None:
            errors.append(f"{name}: shipped, but has no table whose Identification names its pin")
            continue
        for field in FIELDS:
            if not table.get(field, "").strip():
                errors.append(f"{name}: no '{field}'")
        review = re.match(r"(\d{4}-\d{2}-\d{2}), for MiniDAQ (\d+\.\d+)\b", table.get("Last review", ""))
        if not review:
            errors.append(f"{name}: 'Last review' must start 'YYYY-MM-DD, for MiniDAQ X.Y'")
        elif review.group(2) != minor:
            errors.append(f"{name}: reviewed for MiniDAQ {review.group(2)}, this is {minor}")
    return errors
# [/snippet:check]
