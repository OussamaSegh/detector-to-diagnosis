"""Exercise 15.4: minimal cut sets of a fault tree.

A tree is {"top": name, "gates": {name: {"type": "and" | "or", "inputs": [names]}}}. A name
that is not a gate is a basic event. A cut set is a set of basic events whose joint
occurrence causes the top event; it is minimal if no proper subset is a cut set. Order-1
minimal cut sets are single points of failure.
"""


def minimal_cut_sets(tree):
    gates = tree["gates"]

    def expand(name):
        if name not in gates:
            return [[name]]
        gate = gates[name]
        children = [expand(i) for i in gate["inputs"]]
        if gate["type"] == "or":
            return [s for c in children for s in c]
        sets = [[]]
        for c in children:
            sets = [a + b for a in sets for b in c]
        return sets

    # TODO: duplicates, repeated events, non-minimal sets, cycles, unknown gate types.
    return sorted((tuple(sorted(s)) for s in expand(tree["top"])), key=lambda s: (len(s), s))


def single_points(tree):
    return [s[0] for s in minimal_cut_sets(tree) if len(s) == 1]
