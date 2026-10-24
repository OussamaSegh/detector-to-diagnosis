#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Writes a CycloneDX 1.5 SBOM for MiniDAQ (Chapter 7) from the pinned
dependencies in cmake/Dependencies.cmake, and optionally validates it against
the vendored schema (tools/sbom/schemas/).

Usage: tools/make_sbom.py [--validate] [-o minidaq-X.Y.Z.cdx.json] [repo-root]

The SBOM is reproducible: the same sources give the same bytes, as long as
SOURCE_DATE_EPOCH is set (otherwise the timestamp is the current time). The
platform (compiler runtime, C library, kernel) is not listed: it comes from the
target system and is qualified separately (Chapter 25).
"""
import argparse
import datetime
import hashlib
import json
import os
import pathlib
import re
import sys
import uuid

# Facts the CMake file does not state. Shipped components are "required" in the
# product; test-only ones are "excluded" (in the repository, not in the product).
# [snippet:known]
KNOWN = {
    "nlohmann_json": {"name": "nlohmann-json", "group": "nlohmann", "license": "MIT", "scope": "required",
                      "purl": "pkg:github/nlohmann/json@v{version}",
                      "description": "JSON for configuration, control protocol and audit trail"},
    "googletest": {"name": "googletest", "group": "google", "license": "BSD-3-Clause", "scope": "excluded",
                   "purl": "pkg:github/google/googletest@v{version}",
                   "description": "Unit test framework (tests only, not shipped)"},
    "googlebenchmark": {"name": "benchmark", "group": "google", "license": "Apache-2.0", "scope": "excluded",
                        "purl": "pkg:github/google/benchmark@v{version}",
                        "description": "Micro-benchmark framework (benchmarks only, not shipped)"},
}
# [/snippet:known]

DECLARE = re.compile(r"FetchContent_Declare\(\s*(\w+)(.*?)\)", re.S)


def dependencies(cmake_text):
    """Yields (cmake name, fields) for every FetchContent_Declare."""
    for name, body in DECLARE.findall(cmake_text):
        fields = {}
        for line in body.splitlines():
            m = re.match(r"\s*(GIT_REPOSITORY|GIT_TAG|URL|URL_HASH)\s+(\S+)(?:\s*#\s*v?(\S+))?", line)
            if m:
                fields[m.group(1)] = m.group(2)
                if m.group(3):
                    fields["version"] = m.group(3)
        if "URL" in fields and "version" not in fields:
            v = re.search(r"/v(\d+\.\d+\.\d+)/", fields["URL"])
            fields["version"] = v.group(1) if v else None
        yield name, fields


def component(cmake_name, f):
    if cmake_name not in KNOWN:
        raise SystemExit(f"make_sbom: {cmake_name} is not in KNOWN; add its license and scope")
    k = KNOWN[cmake_name]
    if not f.get("version"):
        raise SystemExit(f"make_sbom: no version for {cmake_name}; add '# vX.Y.Z' after GIT_TAG")
    c = {
        "type": "library",
        "bom-ref": f"{k['group']}/{k['name']}@{f['version']}",
        "group": k["group"],
        "name": k["name"],
        "version": f["version"],
        "description": k["description"],
        "scope": k["scope"],
        "licenses": [{"license": {"id": k["license"]}}],
        "purl": k["purl"].format(version=f["version"]),
        "externalReferences": [],
    }
    if "URL_HASH" in f:
        algo, digest = f["URL_HASH"].split("=", 1)
        c["hashes"] = [{"alg": {"SHA256": "SHA-256", "SHA512": "SHA-512"}[algo], "content": digest}]
        c["externalReferences"].append({"type": "distribution", "url": f["URL"]})
    if "GIT_REPOSITORY" in f:
        c["externalReferences"].append({"type": "vcs", "url": f["GIT_REPOSITORY"]})
        c["properties"] = [{"name": "minidaq:git-commit", "value": f["GIT_TAG"]}]
    return c


def make_bom(root):
    version = (root / "VERSION").read_text().strip()
    cmake = (root / "cmake/Dependencies.cmake").read_text()
    components = [component(n, f) for n, f in dependencies(cmake)]
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    when = datetime.datetime.fromtimestamp(int(epoch), datetime.timezone.utc) if epoch else \
        datetime.datetime.now(datetime.timezone.utc)
    bom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {
            "timestamp": when.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "tools": {"components": [{"type": "application", "name": "make_sbom.py", "version": version}]},
            "component": {"type": "application", "bom-ref": f"minidaq@{version}", "name": "minidaq",
                          "version": version, "licenses": [{"license": {"id": "MIT"}}]},
        },
        "components": components,
        "dependencies": [{"ref": f"minidaq@{version}", "dependsOn": [c["bom-ref"] for c in components]}],
    }
    # A serial number derived from the content: unique per BOM, yet reproducible.
    digest = hashlib.sha256(json.dumps(bom, sort_keys=True).encode()).hexdigest()
    bom["serialNumber"] = "urn:uuid:" + str(uuid.uuid5(uuid.NAMESPACE_URL, "minidaq-sbom:" + digest))
    return bom


def validate(bom, schema_dir):
    try:
        import jsonschema
        import referencing
    except ImportError:
        print("make_sbom: jsonschema is not installed; cannot validate", file=sys.stderr)
        return 77  # CTest: skipped
    resources = []
    for path in schema_dir.glob("*.schema.json"):
        doc = json.loads(path.read_text())
        res = referencing.Resource.from_contents(doc, default_specification=referencing.jsonschema.DRAFT7)
        resources += [(doc["$id"], res), (path.name, res)]
    registry = referencing.Registry().with_resources(resources)
    schema = json.loads((schema_dir / "bom-1.5.schema.json").read_text())
    validator = jsonschema.Draft7Validator(schema, registry=registry, format_checker=jsonschema.FormatChecker())
    errors = sorted(validator.iter_errors(bom), key=lambda e: list(e.absolute_path))
    for e in errors:
        print(f"make_sbom: /{'/'.join(map(str, e.absolute_path))}: {e.message}", file=sys.stderr)
    return 1 if errors else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("root", nargs="?", default=pathlib.Path(__file__).resolve().parent.parent, type=pathlib.Path)
    ap.add_argument("-o", "--output", type=pathlib.Path)
    ap.add_argument("--validate", action="store_true")
    args = ap.parse_args()
    bom = make_bom(args.root)
    text = json.dumps(bom, indent=2) + "\n"
    if args.output:
        args.output.write_text(text)
    elif not args.validate:
        sys.stdout.write(text)
    if args.validate:
        status = validate(bom, args.root / "tools/sbom/schemas")
        if status == 0:
            print(f"make_sbom: valid CycloneDX 1.5, {len(bom['components'])} components")
        return status
    return 0


if __name__ == "__main__":
    sys.exit(main())
