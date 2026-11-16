#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Turns an acquisition configuration of schema 1.x into schema 2.0 (CR-0030).

MiniDAQ 2.0 refuses a 1.x file instead of guessing what it meant (hazard H-04): a renamed key
read with its default would change the run without a word. This tool makes the conversion
explicit, prints what it changed, and checks its result against the schema document.

    tools/migrate_config.py OLD.json                 # the 2.0 document on standard output
    tools/migrate_config.py OLD.json -o NEW.json     # written to a file
    tools/migrate_config.py OLD.json --in-place      # replaces the file (comments are lost)
    tools/migrate_config.py NEW.json --check         # exit 1 unless it validates against 2.0

The changes, the same as in docs/migration-2.0.md:

    schema_version                  "1.x" -> "2.0"
    source.type                     required; "synthetic", the 1.x default, made explicit
    stop_after_s                    -> source.stop_after_s
    pipeline.coincidence_window_ps  -> sorter.window_ps
    output.max_file_mb              -> output.max_file_mib (the same number: it always was MiB)
    rt_profile                      -> rt_profile_file

Every other key keeps its place and its value, and no default changes, so the converted file
gives the run the same effective configuration. Comments, which the server allows, are removed
(JSON has none); the tool says so when it drops any.
"""
import argparse
import copy
import json
import pathlib
import re
import sys

SCHEMA = pathlib.Path(__file__).resolve().parent.parent / "docs/architecture/acquisition-config.schema.json"
VERSION = "2.0"

# (old path, new path); a path is a tuple of keys.
MOVES = (
    (("stop_after_s",), ("source", "stop_after_s")),
    (("pipeline", "coincidence_window_ps"), ("sorter", "window_ps")),
    (("output", "max_file_mb"), ("output", "max_file_mib")),
    (("rt_profile",), ("rt_profile_file",)),
)
HARDWARE_KEYS = {"backend", "boards"}
CALIBRATION_KEYS = {"crystals", "coefficients", "procedure"}


class MigrationError(Exception):
    pass


def strip_comments(text):
    """The text without // and /* */ comments outside strings, and whether there were any."""
    out, i, n, found = [], 0, len(text), False
    while i < n:
        c = text[i]
        if c == '"':
            j = i + 1
            while j < n and text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            out.append(text[i:j + 1])
            i = j + 1
        elif text.startswith("//", i):
            found = True
            while i < n and text[i] != "\n":
                i += 1
        elif text.startswith("/*", i):
            found = True
            end = text.find("*/", i + 2)
            i = n if end < 0 else end + 2
        else:
            out.append(c)
            i += 1
    return "".join(out), found


def is_acquisition_config(doc):
    """True for an acquisition configuration, false for a hardware description or a calibration
    table, which have schema versions of their own and are not changed by 2.0."""
    return isinstance(doc, dict) and "schema_version" in doc and not (
        HARDWARE_KEYS & doc.keys() or CALIBRATION_KEYS & doc.keys())


def _pop(doc, path):
    node = doc
    for key in path[:-1]:
        if not isinstance(node, dict) or key not in node:
            return False, None
        node = node[key]
    if not isinstance(node, dict) or path[-1] not in node:
        return False, None
    value = node.pop(path[-1])
    return True, value


def _put(doc, path, value):
    node = doc
    for key in path[:-1]:
        node = node.setdefault(key, {})
        if not isinstance(node, dict):
            raise MigrationError(f"/{'/'.join(path[:-1])} is not an object")
    if path[-1] in node:
        raise MigrationError(f"/{'/'.join(path)} is there already: the file mixes 1.x and 2.0 names")
    node[path[-1]] = value


def migrate(doc):
    """(the 2.0 document, [what changed]) for a 1.x document; MigrationError if it is not one."""
    if not is_acquisition_config(doc):
        raise MigrationError("not an acquisition configuration (no schema_version, or a hardware "
                             "description or calibration table, which 2.0 does not change)")
    version = doc["schema_version"]
    if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+", version):
        raise MigrationError(f"schema_version {version!r} is not of the form MAJOR.MINOR")
    if version.split(".")[0] != "1":
        raise MigrationError(f"schema_version {version} is not 1.x: nothing to convert")
    new = copy.deepcopy(doc)
    changes = [f"/schema_version: {version} -> {VERSION}"]
    new["schema_version"] = VERSION
    source = new.get("source", {})
    if not isinstance(source, dict):
        raise MigrationError("/source is not an object")
    if "type" not in source:
        changes.append('/source/type: "synthetic" (the 1.x default) made explicit')
    for old, to in MOVES:
        found, value = _pop(new, old)
        if found:
            if old == ("stop_after_s",) and "source" not in new:
                new["source"] = {}
            _put(new, to, value)
            changes.append(f"/{'/'.join(old)} -> /{'/'.join(to)}")
    if isinstance(new.get("pipeline"), dict) and not new["pipeline"]:
        del new["pipeline"]
        changes.append("/pipeline: empty after the move, removed")
    # source.type first, as the documentation writes it.
    src = new.get("source", {})
    new["source"] = {"type": src.get("type", "synthetic"), **{k: v for k, v in src.items() if k != "type"}}
    ordered = {k: new[k] for k in ("schema_version", "description") if k in new}
    ordered.update({k: v for k, v in new.items() if k not in ordered})
    return ordered, changes


def validate(doc, schema=None, at=""):
    """[error] of doc against the schema document: the keywords it uses (type, properties,
    required, additionalProperties false, enum, minimum, maximum, pattern), nothing else."""
    if schema is None:
        schema = json.loads(SCHEMA.read_text())
    errors = []
    types = {"object": dict, "string": str, "boolean": bool, "array": list}
    kind = schema.get("type")
    if kind == "integer":
        if isinstance(doc, bool) or not isinstance(doc, int):
            return [f"{at or '/'}: must be an integer"]
    elif kind == "number":
        if isinstance(doc, bool) or not isinstance(doc, (int, float)):
            return [f"{at or '/'}: must be a number"]
    elif kind in types and not isinstance(doc, types[kind]):
        return [f"{at or '/'}: must be of type {kind}"]
    if "enum" in schema and doc not in schema["enum"]:
        errors.append(f"{at or '/'}: must be one of {schema['enum']}")
    if "minimum" in schema and isinstance(doc, (int, float)) and doc < schema["minimum"]:
        errors.append(f"{at}: below the minimum {schema['minimum']}")
    if "maximum" in schema and isinstance(doc, (int, float)) and doc > schema["maximum"]:
        errors.append(f"{at}: above the maximum {schema['maximum']}")
    if "pattern" in schema and isinstance(doc, str) and not re.search(schema["pattern"], doc):
        errors.append(f"{at}: does not match {schema['pattern']}")
    if isinstance(doc, dict):
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in doc:
                errors.append(f"{at}/{key}: is required")
        for key, value in doc.items():
            if key in props:
                errors += validate(value, props[key], f"{at}/{key}")
            elif schema.get("additionalProperties") is False:
                errors.append(f"{at}/{key}: unknown key")
    return errors


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("file", type=pathlib.Path)
    out = ap.add_mutually_exclusive_group()
    out.add_argument("-o", "--output", type=pathlib.Path)
    out.add_argument("--in-place", action="store_true")
    out.add_argument("--check", action="store_true", help="validate against schema 2.0 only")
    args = ap.parse_args(argv)
    text, had_comments = strip_comments(args.file.read_text())
    try:
        doc = json.loads(text)
    except json.JSONDecodeError as e:
        print(f"{args.file}: not valid JSON: {e}", file=sys.stderr)
        return 2
    if args.check:
        errors = validate(doc)
        for e in errors:
            print(f"{args.file}: {e}", file=sys.stderr)
        return 1 if errors else 0
    try:
        new, changes = migrate(doc)
    except MigrationError as e:
        print(f"{args.file}: {e}", file=sys.stderr)
        return 1
    errors = validate(new)
    if errors:
        for e in errors:
            print(f"{args.file}: the converted document does not validate: {e}", file=sys.stderr)
        return 1
    for c in changes:
        print(f"{args.file}: {c}", file=sys.stderr)
    if had_comments:
        print(f"{args.file}: comments removed; add them again where they matter", file=sys.stderr)
    result = json.dumps(new, indent=2) + "\n"
    target = args.file if args.in_place else args.output
    if target:
        target.write_text(result)
    else:
        sys.stdout.write(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
