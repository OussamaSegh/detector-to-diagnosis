# SPDX-License-Identifier: MIT
"""Acceptance tests for Exercise 13.1. Run: python3 -m unittest discover -s tests
with the starter or solution directory on PYTHONPATH (CTest does this)."""
import re
import shutil
import subprocess
import unittest

import map_files

EDGE = re.compile(r'^\s*"?(\w+)"?\s*->\s*"?(\w+)"?\s*(\[(.*)\])?\s*;?\s*$')
NODE = re.compile(r'^\s*"?(\w+)"?\s*\[(.*)\]\s*;?\s*$')
ATTR = re.compile(r'(\w+)\s*=\s*("((?:[^"\\]|\\.)*)"|[\w.#-]+)')
KEYWORDS = {"node", "edge", "graph", "digraph", "subgraph"}
LABELS = {"requires", "references", "presumption", "guidance"}

# Node id -> the edition its label must name.
EDITIONS = {
    "MDR": "2017/745",
    "ISO13485": "2016",
    "ISO14971": "2019",
    "TR24971": "2020",
    "IEC62304": "2006+A1:2015",
    "IEC62366": "62366-1",
    "IEC60601": "60601-1",
    "IEC81001": "2021",
}

# (from, to) -> the labels accepted for that edge.
REQUIRED = {
    ("MDR", "ISO13485"): {"presumption"},
    ("MDR", "ISO14971"): {"presumption"},
    ("ISO13485", "ISO14971"): {"references"},
    ("TR24971", "ISO14971"): {"guidance"},
    ("IEC62304", "ISO14971"): {"requires"},
    ("IEC62304", "ISO13485"): {"references"},
    ("IEC62366", "ISO14971"): {"requires"},
    ("IEC60601", "ISO14971"): {"requires"},
    ("IEC60601", "IEC62304"): {"requires"},
    ("IEC81001", "IEC62304"): {"references", "requires"},
}

# Edges that point the wrong way or claim a dependency that does not exist.
FORBIDDEN = {
    ("ISO13485", "IEC62304"): "ISO 13485 is a QMS standard; it names no software life cycle",
    ("ISO14971", "IEC62304"): "ISO 14971 covers all devices and depends on no software standard",
    ("MDR", "IEC62304"): "the MDR names no standard; it gives presumption of conformity through "
                         "harmonised standards, and only as presumption",
}


def attrs(text):
    out = {}
    for key, raw, quoted in ATTR.findall(text or ""):
        out[key] = quoted if raw.startswith('"') else raw
    return out


def parse(path):
    """A small reader for the subset of DOT this exercise uses: one statement per line."""
    nodes, edges = {}, []
    text = re.sub(r"//[^\n]*|/\*.*?\*/", "", path.read_text(), flags=re.S)
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(("digraph", "subgraph", "}", "{")):
            continue
        m = EDGE.match(line)
        if m:
            edges.append((m.group(1), m.group(2), attrs(m.group(4))))
            for n in (m.group(1), m.group(2)):
                nodes.setdefault(n, {})
            continue
        m = NODE.match(line)
        if m and m.group(1) not in KEYWORDS:
            nodes.setdefault(m.group(1), {}).update(attrs(m.group(2)))
    return nodes, edges


class StandardsMap(unittest.TestCase):
    def setUp(self):
        self.nodes, self.edges = parse(map_files.MAP)
        self.by_pair = {}
        for a, b, e in self.edges:
            self.by_pair.setdefault((a, b), []).append(e.get("label", ""))

    def test_every_document_is_drawn_with_its_edition(self):
        for node, edition in EDITIONS.items():
            self.assertIn(node, self.nodes, f"{node} is not drawn")
            label = self.nodes[node].get("label", "")
            self.assertIn(edition, label, f"{node}'s label should name {edition!r}: {label!r}")

    def test_every_edge_has_one_known_label(self):
        for (a, b), labels in self.by_pair.items():
            self.assertEqual(len(labels), 1, f"{a} -> {b} is drawn {len(labels)} times")
            self.assertIn(labels[0], LABELS, f"{a} -> {b} has label {labels[0]!r}")
            self.assertNotEqual(a, b)

    def test_required_edges(self):
        for (a, b), ok in REQUIRED.items():
            self.assertIn((a, b), self.by_pair, f"missing edge {a} -> {b}")
            self.assertIn(self.by_pair[(a, b)][0], ok,
                          f"{a} -> {b} is {self.by_pair[(a, b)][0]!r}, expected one of {sorted(ok)}")

    def test_no_wrong_edges(self):
        for (a, b), why in FORBIDDEN.items():
            self.assertNotIn((a, b), self.by_pair, f"{a} -> {b}: {why}")

    def test_presumption_only_comes_from_a_regulation(self):
        for (a, b), labels in self.by_pair.items():
            if labels[0] == "presumption":
                self.assertEqual(a, "MDR", f"{a} -> {b}: only a regulation gives presumption")

    @unittest.skipUnless(shutil.which("dot"), "Graphviz is not installed")
    def test_graphviz_renders_it(self):
        out = subprocess.run(["dot", "-Tsvg", str(map_files.MAP)], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("<svg", out.stdout)


if __name__ == "__main__":
    unittest.main()
