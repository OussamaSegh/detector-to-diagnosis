# SPDX-License-Identifier: MIT
"""Exercise 34.2: the owner of every file, and what the item map gets wrong."""


def claims(path, items):
    """{item id: length of its longest prefix that matches the path}."""
    out = {}
    for item in items:
        for prefix in item["paths"]:
            if path.startswith(prefix):
                out[item["id"]] = max(out.get(item["id"], 0), len(prefix))
    return out


def owner(path, items):
    """The id of the item whose longest matching prefix is the longest, or None. Raises
    ValueError when two items match with prefixes of the same, longest length."""
    c = claims(path, items)
    if not c:
        return None
    longest = max(c.values())
    best = sorted(i for i, n in c.items() if n == longest)
    if len(best) > 1:
        raise ValueError(f"{path}: claimed by {' and '.join(best)} with prefixes of {longest}")
    return best[0]


def check_map(files, items):
    """{"unowned", "ambiguous", "shadowed", "dead", "owned"} for the files and the map."""
    result = {"unowned": [], "ambiguous": [], "shadowed": [], "dead": [],
              "owned": {item["id"]: 0 for item in items}}
    for f in sorted(files):
        try:
            who = owner(f, items)
        except ValueError:
            result["ambiguous"].append(f)
            continue
        if who is None:
            result["unowned"].append(f)
            continue
        result["owned"][who] += 1
        for other in sorted(claims(f, items)):
            if other != who:
                result["shadowed"].append((f, who, other))
    result["dead"] = [(item["id"], p) for item in items for p in item["paths"]
                      if not any(f.startswith(p) for f in files)]
    return result
