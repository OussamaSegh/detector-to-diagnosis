# SPDX-License-Identifier: MIT
import os
import unittest

import attack_tree as a

HERE = os.path.dirname(os.path.abspath(__file__))
VARIANT = os.path.dirname(os.path.abspath(a.__file__))


def leaf(i, *blocked_by):
    return {"id": i, "label": i, "blocked_by": list(blocked_by)}


def node(i, op, *children):
    return {"id": i, "label": i, "op": op, "children": list(children)}


def ids(sets):
    return sorted(sorted(s) for s in sets)


class Leaves(unittest.TestCase):
    def test_blockers(self):
        self.assertTrue(a.leaf_open(leaf("x"), frozenset(), True))
        self.assertFalse(a.leaf_open(leaf("x", "SRS-A-001"), frozenset({"SRS-A-001"}), True))
        self.assertTrue(a.leaf_open(leaf("x", "SRS-A-001"), frozenset(), True), "an unverified requirement blocks nothing")
        self.assertFalse(a.leaf_open(leaf("x", "ENV:site"), frozenset(), True))
        self.assertTrue(a.leaf_open(leaf("x", "ENV:site"), frozenset(), False))
        self.assertFalse(a.leaf_open(leaf("x", "ENV:site", "SRS-A-001"), frozenset({"SRS-A-001"}), False))


class Attacks(unittest.TestCase):
    def test_or_and(self):
        t = node("r", "OR", node("1", "AND", leaf("a"), leaf("b")), leaf("c"))
        self.assertEqual(ids(a.attacks(t)), [["a", "b"], ["c"]])

    def test_and_of_ors(self):
        t = node("r", "AND", node("1", "OR", leaf("a"), leaf("b")), node("2", "OR", leaf("c"), leaf("d")))
        self.assertEqual(ids(a.attacks(t)), [["a", "c"], ["a", "d"], ["b", "c"], ["b", "d"]])

    def test_blocked_child_blocks_and(self):
        t = node("r", "AND", leaf("a"), leaf("b", "SRS-A-001"))
        self.assertEqual(a.attacks(t, frozenset({"SRS-A-001"})), [])
        self.assertEqual(ids(a.attacks(t)), [["a", "b"]])

    def test_minimal(self):
        # "a" alone reaches the root, so {"a", "b"} is not a minimal attack.
        t = node("r", "OR", leaf("a"), node("1", "AND", leaf("a"), leaf("b")))
        self.assertEqual(ids(a.attacks(t)), [["a"]])
        self.assertEqual(ids(a.minimize([frozenset("ab"), frozenset("a"), frozenset("a"), frozenset("cd")])),
                         [["a"], ["c", "d"]])

    def test_bad_op(self):
        with self.assertRaises(ValueError):
            a.attacks(node("r", "XOR", leaf("a")))


class StopTheScan(unittest.TestCase):
    """The tree of threat-model.md, section 4."""

    def setUp(self):
        self.tree = a.load(os.path.join(HERE, "stop_scan.json"))
        self.verified = frozenset(a.requirements(self.tree))

    def test_without_controls_anyone_local_can_stop_a_scan(self):
        self.assertIn(["1.1.1", "1.2.2"], ids(a.attacks(self.tree, frozenset())))

    def test_residual_attacks(self):
        self.assertEqual(ids(a.attacks(self.tree, self.verified, True)), [["3.2"]],
                         "with every requirement verified and the site doing its part, only filling the disk")
        self.assertEqual(ids(a.attacks(self.tree, self.verified, False)),
                         [["1.1.1", "1.2.8"], ["2"], ["3.1"], ["3.2"], ["4.2"]])

    def test_critical_requirements(self):
        self.assertEqual(a.critical(self.tree, self.verified, True),
                         ["SRS-SEC-002", "SRS-SEC-003", "SRS-SEC-004", "SRS-SEC-006", "SRS-SEC-007",
                          "SRS-SEC-008", "SRS-SEC-009"])
        self.assertIn("SRS-SEC-005", a.critical(self.tree, self.verified, False),
                      "the bind check matters once the operator's account is not trusted")


class YourTree(unittest.TestCase):
    """tamper_data.json, your attack tree for changing a scan's data unnoticed."""

    def setUp(self):
        self.tree = a.load(os.path.join(VARIANT, "tamper_data.json"))

    def leaves(self, n):
        return [n] if "children" not in n else [x for c in n["children"] for x in self.leaves(c)]

    def test_shape(self):
        leaves = self.leaves(self.tree)
        self.assertGreaterEqual(len(leaves), 5)
        self.assertEqual(len({x["id"] for x in leaves}), len(leaves), "leaf ids are unique")
        ops = set()

        def walk(n):
            if "children" in n:
                ops.add(n["op"])
                for c in n["children"]:
                    walk(c)
        walk(self.tree)
        self.assertEqual(ops, {"AND", "OR"})
        blockers = [b for x in leaves for b in x["blocked_by"]]
        self.assertTrue(any(b.startswith("ENV:") for b in blockers), "the site's part")
        self.assertIn("SRS-LMF-006", blockers, "the CRC of each block")

    def test_it_shows_the_gap(self):
        verified = frozenset(a.requirements(self.tree))
        self.assertEqual(a.attacks(self.tree, verified, True), [],
                         "with every control in place, each attack needs the site to fail")
        self.assertTrue(a.attacks(self.tree, verified, False),
                        "but the operator's own account can still change the data: the gap of section 7")


if __name__ == "__main__":
    unittest.main()
