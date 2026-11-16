#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Tests of tools/migrate_config.py and tools/check_interfaces.py (CR-0030), run by CTest as
tools.migrate_config.

tools/testdata/migrate_config/ holds every 1.x acquisition configuration that the repository and
the book showed before 2.0: the shipped configurations, the fuzz corpus, the book's listings and
the configurations that the system tests and tools wrote, and one annotated file with every
renamed key. Each must convert into a document that validates against schema 2.0 and gives the
run the same settings: every value of the old file at its new place, nothing else added but the
version and the source type that 1.x assumed. The repository's own files must be the converted
ones, and no 1.x configuration may remain among them.

    python3 tools/test_migrate_config.py
"""
import contextlib
import io
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import check_interfaces  # noqa: E402
import migrate_config as mc  # noqa: E402

FIXTURES = HERE / "testdata/migrate_config"
# Fixture -> the repository file that is its conversion.
CONVERTED = {
    "configs-default.json": "minidaq/configs/default.json",
    "configs-short-run.json": "minidaq/configs/short-run.json",
    "configs-udp-loopback.json": "minidaq/configs/udp-loopback.json",
    "fuzz-default.json": "fuzz/corpus/config/default.json",
    "fuzz-edge.json": "fuzz/corpus/config/edge.json",
    "fuzz-short-run.json": "fuzz/corpus/config/short-run.json",
}
MOVED = {old: new for old, new in mc.MOVES}


def load(path):
    return json.loads(mc.strip_comments(path.read_text())[0])


def leaves(doc, at=()):
    """{path: value} of every value that is not an object."""
    if isinstance(doc, dict) and doc:
        out = {}
        for k, v in doc.items():
            out.update(leaves(v, at + (k,)))
        return out
    return {at: doc}


class Conversion(unittest.TestCase):
    def fixtures(self):
        found = sorted(FIXTURES.glob("*.json"))
        self.assertGreaterEqual(len(found), 12)
        return found

    def test_every_1x_configuration_converts_into_a_valid_2_0_document(self):
        # REQ: SRS-CFG-015
        for path in self.fixtures():
            with self.subTest(path.name):
                old = load(path)
                self.assertTrue(old["schema_version"].startswith("1."))
                new, changes = mc.migrate(old)
                self.assertEqual(mc.validate(new), [])
                self.assertEqual(new["schema_version"], "2.0")
                self.assertIn("type", new["source"])
                self.assertTrue(changes)

    def test_the_converted_document_keeps_every_setting(self):
        # REQ: SRS-CFG-015
        for path in self.fixtures():
            with self.subTest(path.name):
                old = load(path)
                new, _ = mc.migrate(old)
                expected = {MOVED.get(p, p): v for p, v in leaves(old).items() if p != ("schema_version",)}
                got = leaves(new)
                self.assertEqual(got.pop(("schema_version",)), "2.0")
                self.assertEqual(got.pop(("source", "type")), old.get("source", {}).get("type", "synthetic"),
                                 "the 1.x default, made explicit")
                expected.pop(("source", "type"), None)
                if ("pipeline",) not in expected:
                    expected = {p: v for p, v in expected.items() if p != ("pipeline",)}
                self.assertEqual(got, expected)

    def test_the_repository_holds_the_converted_files(self):
        for fixture, target in CONVERTED.items():
            with self.subTest(target):
                new, _ = mc.migrate(load(FIXTURES / fixture))
                self.assertEqual(load(ROOT / target), new)

    def test_no_1x_configuration_is_left_in_the_repository(self):
        tracked = subprocess.run(["git", "-C", str(ROOT), "ls-files", "*.json"], capture_output=True,
                                 text=True, check=False).stdout.split()
        if not tracked:
            self.skipTest("not a git checkout")
        for name in tracked:
            if name.startswith("tools/testdata/migrate_config/"):
                continue
            try:
                doc = load(ROOT / name)
            except (json.JSONDecodeError, UnicodeDecodeError, FileNotFoundError):
                continue
            if mc.is_acquisition_config(doc) and isinstance(doc["schema_version"], str) \
                    and doc["schema_version"].startswith("1."):
                self.fail(f"{name} is a 1.x acquisition configuration")

    def test_what_is_not_a_1x_acquisition_configuration_is_refused(self):
        for doc, why in (
                ({"schema_version": "2.0", "source": {"type": "udp"}}, "not 1.x"),
                ({"schema_version": "1.1", "backend": "simulated", "boards": [{}]}, "hardware description"),
                ({"schema_version": "1.0", "crystals": 288, "coefficients": []}, "calibration table"),
                ({"source": {}}, "no schema_version"),
                ({"schema_version": "1", "source": {}}, "MAJOR.MINOR"),
                ({"schema_version": "1.4", "source": 3}, "not an object"),
                ({"schema_version": "1.4", "stop_after_s": 1, "source": {"stop_after_s": 2}}, "mixes")):
            with self.subTest(why), self.assertRaises(mc.MigrationError) as e:
                mc.migrate(doc)
            if why == "mixes":
                self.assertIn("mixes 1.x and 2.0", str(e.exception))

    def test_the_validator_sees_what_the_reader_refuses(self):
        good, _ = mc.migrate({"schema_version": "1.0"})
        self.assertEqual(mc.validate(good), [])
        for change, path in (
                (lambda d: d.pop("source"), "/source: is required"),
                (lambda d: d["source"].pop("type"), "/source/type: is required"),
                (lambda d: d.update(stop_after_s=1), "/stop_after_s: unknown key"),
                (lambda d: d["source"].update(rate_hz=0), "/source/rate_hz: below"),
                (lambda d: d["source"].update(type="tcp"), "/source/type: must be one of"),
                (lambda d: d.update(sorter={"window_ps": 1.5}), "/sorter/window_ps: must be an integer"),
                (lambda d: d.update(sorter={"window_ps": True}), "/sorter/window_ps: must be an integer"),
                (lambda d: d.update(schema_version="2"), "/schema_version: does not match")):
            doc = json.loads(json.dumps(good))
            change(doc)
            with self.subTest(path):
                self.assertTrue(any(e.startswith(path) for e in mc.validate(doc)), mc.validate(doc))

    def test_comments_are_removed_but_not_inside_strings(self):
        text, found = mc.strip_comments('// a\n{"a": "x//y", /* b */ "c": "/*z*/"}\n')
        self.assertTrue(found)
        self.assertEqual(json.loads(text), {"a": "x//y", "c": "/*z*/"})
        self.assertEqual(mc.strip_comments('{"a": "q\\"//"}')[0], '{"a": "q\\"//"}')


class CommandLine(unittest.TestCase):
    def run_tool(self, *args):
        err = io.StringIO()
        out = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
            code = mc.main([str(a) for a in args])
        return code, out.getvalue(), err.getvalue()

    def test_convert_write_and_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = pathlib.Path(tmp) / "old.json"
            old.write_text((FIXTURES / "commented.json").read_text())
            self.assertEqual(self.run_tool(old, "--check")[0], 1, "a 1.x file does not validate as 2.0")
            code, out, err = self.run_tool(old)
            self.assertEqual(code, 0, err)
            self.assertEqual(json.loads(out)["sorter"]["window_ps"], 3000)
            self.assertIn("comments removed", err)
            self.assertIn("/stop_after_s -> /source/stop_after_s", err)
            new = pathlib.Path(tmp) / "new.json"
            self.assertEqual(self.run_tool(old, "-o", new)[0], 0)
            self.assertEqual(self.run_tool(new, "--check")[0], 0)
            self.assertEqual(self.run_tool(new)[0], 1, "a 2.0 file is not converted again")
            self.assertEqual(self.run_tool(old, "--in-place")[0], 0)
            self.assertEqual(json.loads(old.read_text()), json.loads(new.read_text()))

    def test_not_json_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = pathlib.Path(tmp) / "bad.json"
            bad.write_text("{")
            self.assertEqual(self.run_tool(bad)[0], 2)


class Interfaces(unittest.TestCase):
    def problems(self, name, text):
        return check_interfaces.problems_in(pathlib.PurePath(name), text)

    def test_the_book_and_the_exercises_show_only_the_current_interfaces(self):
        err = io.StringIO()
        with contextlib.redirect_stdout(err):
            code = check_interfaces.main(["check_interfaces.py", str(ROOT)])
        self.assertEqual(code, 0, err.getvalue())

    def test_old_requests_and_configurations_are_found(self):
        page = "\n".join([
            "Text with {\"api\": \"2.0\"} outside a block is prose.", "```text",
            '-> {"api": "2.5", "id": 1, "cmd": "status"}',
            '-> {"id": 2, "cmd": "status"}',
            '-> {"api": "3.0", "id": 3, "cmd": "configure", "config": {"schema_version": "1.4",',
            '   "source": {"type": "udp"}}}',
            '-> {"api": "3.0", "id": 4, "cmd": "configure", "config": {"schema_version": "2.0",',
            '   "source": {"type": "udp"}}}', "```", "```json",
            '{"schema_version": "1.1", "backend": "simulated", "boards": [{}]}', "```",
            "```{.text .old-interface}", '-> {"api": "2.0", "cmd": "status"}', "```"])
        self.assertEqual([line for line, _ in self.problems("p.md", page)], [3, 4, 5])
        found = dict(self.problems("p.md", page))
        self.assertIn("API 2.x", found[3])
        self.assertIn('without "api"', found[4])
        self.assertIn("schema 1.x", found[5])
        self.assertEqual(self.problems("t.py", 'cfg = {"schema_version": "1.3", "source": {}}')[0][0], 1)
        self.assertEqual(self.problems("t.py", 'cfg = {"schema_version": "2.0", "source": {}}'), [])


if __name__ == "__main__":
    unittest.main()
