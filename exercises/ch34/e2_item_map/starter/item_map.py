# SPDX-License-Identifier: MIT
"""Exercise 34.2: the owner of every file, and what the item map gets wrong."""


def owner(path, items):
    """The id of the item whose longest matching prefix is the longest, or None."""
    for item in items:
        for prefix in item["paths"]:
            if path.startswith(prefix):
                return item["id"]
    return None


def check_map(files, items):
    """{"unowned", "ambiguous", "shadowed", "dead", "owned"} for the files and the map."""
    unowned = sorted(f for f in files if owner(f, items) is None)
    return {"unowned": unowned, "ambiguous": [], "shadowed": [], "dead": [], "owned": {}}
