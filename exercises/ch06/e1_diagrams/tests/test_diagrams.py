# SPDX-License-Identifier: MIT
"""Acceptance tests for Exercise 6.1. Run: python3 -m unittest discover -s tests
with the starter or solution directory on PYTHONPATH (CTest does this)."""
import json
import pathlib
import re
import shutil
import subprocess
import unittest

import diagram_files

ROOT = pathlib.Path(__file__).resolve().parents[4]
ARCH = ROOT / "docs" / "architecture"

EDGE = re.compile(r'^\s*"?([\w.]+)"?\s*->\s*"?([\w.]+)"?\s*(\[(.*)\])?\s*;?\s*$')
NODE = re.compile(r'^\s*"?([\w.]+)"?\s*\[(.*)\]\s*;?\s*$')
ATTR = re.compile(r'(\w+)\s*=\s*("((?:[^"\\]|\\.)*)"|[\w.#-]+)')
KEYWORDS = {"node", "edge", "graph", "digraph", "subgraph"}


def attrs(text):
    out = {}
    for key, raw, quoted in ATTR.findall(text or ""):
        out[key] = quoted if raw.startswith('"') else raw
    return out


def parse(path):
    """A small reader for the subset of DOT these exercises use: one statement per line."""
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


class States(unittest.TestCase):
    def setUp(self):
        self.spec = json.loads((ARCH / "acquisition-states.json").read_text())
        self.nodes, self.edges = parse(diagram_files.STATES)

    def test_edges_equal_the_transition_table(self):
        want = sorted((t["from"], t["event"], t["to"]) for t in self.spec["transitions"])
        got = sorted((a, e.get("label", ""), b) for a, b, e in self.edges if a != "start")
        missing = sorted(set(want) - set(got))
        extra = sorted(set(got) - set(want))
        self.assertFalse(missing, f"transitions missing from the diagram: {missing}")
        self.assertFalse(extra, f"edges that are not transitions: {extra}")
        self.assertEqual(len(got), len(want), "each transition exactly once")

    def test_every_state_is_drawn_and_start_points_at_the_initial_state(self):
        for s in self.spec["states"]:
            self.assertIn(s, self.nodes, f"state {s} is not drawn")
        starts = [(a, b) for a, b, _ in self.edges if a == "start"]
        if starts:
            self.assertEqual(starts, [("start", self.spec["initial"])])


class Components(unittest.TestCase):
    CLASS_TO_LAYER = {"core": "core", "application": "application", "adapters": "adapters", "app": "apps"}
    MUST_MENTION = ["AcquisitionPipeline", "StateMachine", "AcquisitionService", "Config",
                    "DetectorPort", "protocol", "ControlServer", "minidaq_server", "minidaq_ctl"]

    def setUp(self):
        self.layers = json.loads((ARCH / "layers.json").read_text())
        self.nodes, self.edges = parse(diagram_files.COMPONENTS)

    def test_enough_components_with_valid_classes(self):
        self.assertGreaterEqual(len(self.nodes), 12, "draw at least 12 components")
        for name, a in self.nodes.items():
            self.assertIn(a.get("class"), self.CLASS_TO_LAYER, f"{name}: class must be one of {list(self.CLASS_TO_LAYER)}")
        classes = {a.get("class") for a in self.nodes.values()}
        self.assertEqual(classes, set(self.CLASS_TO_LAYER), "every layer appears")

    def test_the_important_components_are_there(self):
        text = " ".join(f"{n} {a.get('label', '')}" for n, a in self.nodes.items()).lower()
        for word in self.MUST_MENTION:
            self.assertIn(word.lower(), text, f"no component mentions {word}")

    def test_dependencies_only_point_to_allowed_layers(self):
        allowed = self.layers["may_include"]
        for a, b, e in self.edges:
            if e.get("style") == "dashed":
                continue  # a network connection, not a code dependency
            la = self.CLASS_TO_LAYER.get(self.nodes[a].get("class"))
            lb = self.CLASS_TO_LAYER.get(self.nodes[b].get("class"))
            self.assertIn(lb, allowed.get(la, []), f"{a} ({la}) may not use {b} ({lb})")

    def test_no_isolated_component(self):
        connected = {a for a, _, _ in self.edges} | {b for _, b, _ in self.edges}
        lonely = sorted(set(self.nodes) - connected)
        self.assertFalse(lonely, f"components with no edge: {lonely}")


@unittest.skipUnless(shutil.which("dot"), "Graphviz not installed")
class Render(unittest.TestCase):
    def test_both_files_render(self):
        for f in (diagram_files.STATES, diagram_files.COMPONENTS):
            r = subprocess.run(["dot", "-Tsvg", str(f)], capture_output=True, text=True, timeout=60)
            self.assertEqual(r.returncode, 0, f"{f.name}: {r.stderr}")


if __name__ == "__main__":
    unittest.main()
