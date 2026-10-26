#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compares an installed system with the platform definition, and writes the platform's SBOM
(Chapter 25, ADR 0020).

Usage: tools/platform_check.py [--definition platform/platform.json] [--root /]
                               [--facts FILE | --collect FILE] [--sbom OUT.cdx.json]

Without --facts, the facts are collected from the running system: /etc/os-release, the
architecture, `uname -r`, the kernel command line, dpkg-query for each package, /proc/sys for each sysctl, getent for each
user, and the installed configuration files under --root, compared byte for byte with the
repository's. --collect writes those facts to FILE (an installation record) and checks them;
--facts checks a record made earlier, on another machine. Every difference is printed as a
DEVIATION; the exit status is 1 if there is any. The platform is SOUP that the product's SBOM
(tools/make_sbom.py) does not list, so --sbom lists it: one CycloneDX component per package,
with the version found, as the installation qualification's record of what the PC runs.
"""
import argparse
import datetime
import hashlib
import json
import os
import pathlib
import platform as pyplatform
import subprocess
import sys
import uuid

REPO = pathlib.Path(__file__).resolve().parent.parent


def run(*args):
    r = subprocess.run(args, capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def os_release(root):
    out = {}
    for path in (root / "etc/os-release", root / "usr/lib/os-release"):
        if path.is_file():
            for line in path.read_text().splitlines():
                if "=" in line:
                    k, v = line.split("=", 1)
                    out[k] = v.strip('"')
            break
    return out


def package_version(name):
    """The installed version; on a multiarch system, that of the native architecture's package."""
    native = run("dpkg", "--print-architecture")
    found = run("dpkg-query", "-W", "-f=${Version}", f"{name}:{native}") if native else None
    return found or run("dpkg-query", "-W", "-f=${Version}", name)


# [snippet:collect]
def collect(definition, root):
    """The facts the definition asks about, from the running system and the files under root."""
    rel = os_release(root)
    facts = {
        "distribution": rel.get("ID"), "release": rel.get("VERSION_ID"),
        "architecture": run("dpkg", "--print-architecture") or pyplatform.machine(),
        "kernel": pyplatform.release(),
        "cmdline": pathlib.Path("/proc/cmdline").read_text().split() if pathlib.Path("/proc/cmdline").is_file() else [],
        "packages": {p["name"]: package_version(p["name"]) for p in definition["packages"]},
        "sysctl": {},
        "users": {u: run("getent", "passwd", u) is not None for u in definition["users"]},
        "files": {},
        "platform_id": None,
    }
    for key in definition["sysctl"]:
        path = pathlib.Path("/proc/sys") / key.replace(".", "/")
        facts["sysctl"][key] = path.read_text().strip() if path.is_file() else None
    for f in definition["files"]:
        target = root / f["target"]
        facts["files"][f["target"]] = hashlib.sha256(target.read_bytes()).hexdigest() if target.is_file() else None
    id_file = root / definition["platform_id_file"]
    if id_file.is_file():
        facts["platform_id"] = id_file.read_text().strip()
    return facts
# [/snippet:collect]


# [snippet:check]
def check(definition, facts, repo=REPO):
    """Every way the facts differ from the definition, as text; empty when the system conforms."""
    out = []

    def expect(what, found, wanted):
        if found != wanted:
            out.append(f"{what}: found {found!r}, the definition says {wanted!r}")

    base = definition["base"]
    expect("distribution", facts["distribution"], base["distribution"])
    expect("release", facts["release"], base["release"])
    expect("architecture", facts["architecture"], base["architecture"])
    prefix = definition["kernel"]["release_prefix"]
    if not (facts["kernel"] or "").startswith(prefix):
        out.append(f"kernel: found {facts['kernel']!r}, the definition says {prefix}*")
    for arg in definition["kernel"].get("cmdline", []):
        if arg not in facts.get("cmdline", []):
            out.append(f"kernel command line: {arg} is missing (the CPUs of the real-time profile, Chapter 4)")
    for p in definition["packages"]:
        expect(f"package {p['name']}", facts["packages"].get(p["name"]), p["version"])
    for key, value in definition["sysctl"].items():
        expect(f"sysctl {key}", facts["sysctl"].get(key), value)
    for user in definition["users"]:
        if not facts["users"].get(user):
            out.append(f"user {user}: missing")
    for f in definition["files"]:
        wanted = hashlib.sha256((repo / f["source"]).read_bytes()).hexdigest()
        found = facts["files"].get(f["target"])
        if found != wanted:
            out.append(f"file /{f['target']}: " + ("missing" if found is None else f"differs from {f['source']}"))
    expect("platform id", facts["platform_id"], definition["id"])
    return out
# [/snippet:check]


def sbom(definition, facts):
    """A CycloneDX 1.5 SBOM of the platform's packages, at the versions found."""
    distro = f"{definition['base']['distribution']}-{definition['base']['release']}"
    arch = facts["architecture"]
    components = []
    for p in definition["packages"]:
        version = facts["packages"].get(p["name"]) or "unknown"
        components.append({
            "type": "library" if p["name"].startswith("lib") else "application",
            "bom-ref": f"{p['name']}@{version}", "name": p["name"], "version": version,
            "purl": f"pkg:deb/{definition['base']['distribution']}/{p['name']}@{version}?arch={arch}&distro={distro}",
            "description": p["why"]})
    components.append({"type": "operating-system", "bom-ref": f"linux@{facts['kernel']}", "name": "linux",
                       "version": facts["kernel"] or "unknown", "description": "kernel"})
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    when = datetime.datetime.fromtimestamp(int(epoch), datetime.timezone.utc) if epoch else \
        datetime.datetime.now(datetime.timezone.utc)
    bom = {
        "bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
        "metadata": {"timestamp": when.strftime("%Y-%m-%dT%H:%M:%SZ"),
                     "tools": {"components": [{"type": "application", "name": "platform_check.py"}]},
                     "component": {"type": "platform", "bom-ref": definition["id"], "name": definition["id"]}},
        "components": components,
        "dependencies": [{"ref": definition["id"], "dependsOn": [c["bom-ref"] for c in components]}],
    }
    digest = hashlib.sha256(json.dumps(bom, sort_keys=True).encode()).hexdigest()
    bom["serialNumber"] = "urn:uuid:" + str(uuid.uuid5(uuid.NAMESPACE_URL, "minidaq-platform-sbom:" + digest))
    return bom


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--definition", type=pathlib.Path, default=REPO / "platform" / "platform.json")
    ap.add_argument("--root", type=pathlib.Path, default=pathlib.Path("/"))
    group = ap.add_mutually_exclusive_group()
    group.add_argument("--facts", type=pathlib.Path, help="check facts recorded earlier")
    group.add_argument("--collect", type=pathlib.Path, help="record the facts in this file, then check them")
    ap.add_argument("--sbom", type=pathlib.Path)
    args = ap.parse_args(argv)
    definition = json.loads(args.definition.read_text())
    if args.facts:
        facts = json.loads(args.facts.read_text())
    else:
        facts = collect(definition, args.root)
        if args.collect:
            args.collect.write_text(json.dumps(facts, indent=2, sort_keys=True) + "\n")
    deviations = check(definition, facts)
    for d in deviations:
        print(f"DEVIATION {d}")
    if args.sbom:
        args.sbom.write_text(json.dumps(sbom(definition, facts), indent=2) + "\n")
    print(f"platform_check: {definition['id']}: " +
          (f"{len(deviations)} deviations" if deviations else "the system conforms"))
    return 1 if deviations else 0


if __name__ == "__main__":
    sys.exit(main())
