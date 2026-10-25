"""Acceptance tests for Exercise 15.4: minimal cut sets, and the data-loss tree."""
import copy
import json
import pathlib
import unittest

import cutsets

TREE = json.loads((pathlib.Path(__file__).resolve().parent / "data-loss.json").read_text())


def tree(**gates):
    return {"top": "T", "gates": {k: {"type": v[0], "inputs": list(v[1:])} for k, v in gates.items()}}


class CutSets(unittest.TestCase):
    def test_or_gives_one_set_per_input(self):
        self.assertEqual(cutsets.minimal_cut_sets(tree(T=("or", "A", "B"))), [("A",), ("B",)])

    def test_and_gives_one_set_of_all_inputs(self):
        self.assertEqual(cutsets.minimal_cut_sets(tree(T=("and", "A", "B"))), [("A", "B")])

    def test_nested_gates_multiply_out(self):
        t = tree(T=("and", "G", "C"), G=("or", "A", "B"))
        self.assertEqual(cutsets.minimal_cut_sets(t), [("A", "C"), ("B", "C")])

    def test_a_repeated_event_counts_once(self):
        t = tree(T=("and", "G", "H"), G=("or", "A", "B"), H=("or", "A", "C"))
        self.assertEqual(cutsets.minimal_cut_sets(t), [("A",), ("B", "C")])

    def test_supersets_are_absorbed(self):
        t = tree(T=("or", "A", "G"), G=("and", "A", "B"))
        self.assertEqual(cutsets.minimal_cut_sets(t), [("A",)])

    def test_duplicates_are_removed(self):
        t = tree(T=("or", "G", "H"), G=("and", "A", "B"), H=("and", "B", "A"))
        self.assertEqual(cutsets.minimal_cut_sets(t), [("A", "B")])

    def test_sorted_by_order_then_name(self):
        t = tree(T=("or", "G", "Z", "B"), G=("and", "A", "C"))
        self.assertEqual(cutsets.minimal_cut_sets(t), [("B",), ("Z",), ("A", "C")])

    def test_a_cycle_is_an_error(self):
        with self.assertRaises(ValueError):
            cutsets.minimal_cut_sets(tree(T=("or", "G"), G=("and", "T", "A")))

    def test_an_unknown_gate_type_is_an_error(self):
        with self.assertRaises(ValueError):
            cutsets.minimal_cut_sets(tree(T=("xor", "A", "B")))


class DataLoss(unittest.TestCase):
    def test_every_minimal_cut_set_pairs_a_loss_with_a_failure_to_notice(self):
        sets = cutsets.minimal_cut_sets(TREE)
        self.assertEqual(len(sets), 15)
        for s in sets:
            self.assertEqual(len(s), 2)
            self.assertIn(s[0], {"E1", "E2", "E3", "E4", "E5"})
            self.assertIn(s[1], {"E6", "E7", "E8"})
        self.assertEqual(cutsets.single_points(TREE), [])

    def test_a_loss_without_a_counter_is_a_single_point_of_failure(self):
        # Open windows that are never closed (E5) lose data on a path with no
        # counter: E5 also causes E6. Drawn honestly, the tree shows it.
        t = copy.deepcopy(TREE)
        t["gates"]["G2"]["inputs"].append("E5")
        self.assertEqual(cutsets.single_points(t), ["E5"])
        self.assertEqual(len(cutsets.minimal_cut_sets(t)), 13)


if __name__ == "__main__":
    unittest.main()
