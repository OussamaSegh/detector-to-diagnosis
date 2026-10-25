"""Exercise 15.4: minimal cut sets of a fault tree.

A tree is {"top": name, "gates": {name: {"type": "and" | "or", "inputs": [names]}}}. A name
that is not a gate is a basic event. A cut set is a set of basic events whose joint
occurrence causes the top event; it is minimal if no proper subset is a cut set. Order-1
minimal cut sets are single points of failure.
"""


# [snippet:cutsets]
def minimal_cut_sets(tree):
    gates = tree["gates"]

    def expand(name, path):
        if name not in gates:
            return [frozenset([name])]
        if name in path:
            raise ValueError(f"cycle through {name}")
        gate = gates[name]
        children = [expand(i, path | {name}) for i in gate["inputs"]]
        if gate["type"] == "or":
            return [s for c in children for s in c]
        if gate["type"] == "and":
            sets = [frozenset()]
            for c in children:
                sets = [a | b for a in sets for b in c]
            return sets
        raise ValueError(f"gate {name}: unknown type {gate['type']}")

    sets = set(expand(tree["top"], frozenset()))
    minimal = [s for s in sets if not any(t < s for t in sets)]
    return sorted((tuple(sorted(s)) for s in minimal), key=lambda s: (len(s), s))
# [/snippet:cutsets]


def single_points(tree):
    return [s[0] for s in minimal_cut_sets(tree) if len(s) == 1]
