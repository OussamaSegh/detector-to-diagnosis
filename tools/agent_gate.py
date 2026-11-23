#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""The gate a change must pass before a person reviews it, however it was written (roadmap
2.2.0, Theme P1; TL-51).

An agent writes code quickly and says it is done. The gate turns "done" into evidence: it runs
the project's own checks on the change and gives one verdict, with a reason for each failure, so
the reviewer starts from what is known to be wrong. It never replaces the review (SRS-AI): a
change that passes the gate can still be the wrong change.

    agent_gate.py ROOT BASE [HEAD] [--full] [--build DIR] [--json | --trailer]

ROOT is the checkout with the change; BASE the commit the change starts from; HEAD the commit
with the change, checked out in ROOT (default: ROOT's working tree, staged or not). The checks are those of this
file's own version, run on ROOT: a change cannot weaken the gate that judges it, and a change to
one of the gate's checks is reported for a person to review (check `gate`).

The fast checks (seconds) need no build:

  gate         the change edits a check the gate runs, or the gate itself
  tags         each new test of a product item names the requirement it verifies (// REQ:)
  tests        a change to a class B item's source changes a test too
  validation   a new regular expression check of a whole value uses fullmatch or regex_match,
               not ^...$ with match or search (coding standard rule 3.6, MDQ-PR-084)
  trace        the trace matrix (tools/trace_matrix.py --check)
  requirements the SRS in testable form (tools/req_lint.py)
  documents    no controlled document changed without a new version (tools/design_file.py)
  waits        no test waits or reads a clock without its reason (tools/check_test_waits.py)
  layers       the architecture's layers (tools/check_layers.py)
  agents       the agent files (tools/check_agent_files.py --since BASE)
  format       the touched C++ lines as clang-format writes them (tools/check_format.py)

With --full, in BUILD (a debug build of ROOT, default ROOT/build/debug):

  build        the build, warnings as errors
  unit         ctest -L unit
  static       tools/static_analysis.sh on ROOT/build/clang-release, if that build exists

With --trailer it prints only the line a commit message may carry (commit policy 3), such as
`Gate: PASS, fast, 11 passed, 1 skipped, since 8b1eeab`, with the names of the checks that fail.

Exit status 0 if every check passes or is skipped, 1 if one fails, 2 if the gate cannot run.
The gate is shown to fail: tools/test_agent_gate.py applies each change of the known-bad
library (tools/agent_gate/known-bad/) and requires the failure it holds.
"""
import argparse
import json
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
PRODUCT_TESTS = ("minidaq/tests/", "recon/tests/", "analysis/tests/")
GATE_FILES = ("tools/agent_gate.py", "tools/trace_matrix.py", "tools/req_lint.py",
              "tools/design_file.py", "tools/check_test_waits.py", "tools/check_layers.py",
              "tools/check_format.py", "tools/static_analysis.sh", "tools/agent_gate/",
              "tools/check_agent_files.py", "tools/agent_files_policy.json",
              "tools/hooks/agent_", ".claude/settings.json",
              ".clang-tidy", ".clang-format", "docs/architecture/layers.json",
              "docs/architecture/software-items.json")
TAG = re.compile(r"(?://|#)\s*REQ:\s*SRS-[A-Z]+-\d{3}")
CPP_TEST = re.compile(r"^\s*TEST(?:_F|_P)?\(\s*(\w+)\s*,\s*(\w+)\s*\)")
PY_TEST = re.compile(r"^\s*def\s+(test_\w+)\s*\(")
# A pattern anchored at both ends, given to a function that does not require the whole value.
ANCHORED = re.compile(r"""(?:\bre\.(?:match|search)|std::regex_search)\s*\(\s*r?["'](?:\^)[^"']*\$["']""")
ANCHORED_COMPILED = re.compile(r"""\bre\.compile\(\s*r?["']\^[^"']*\$["']""")
COMPILED_NAME = re.compile(r"""^\s*(\w+)\s*=\s*re\.compile\(\s*r?["']\^.*\$["']""")
NAMED_CALL = re.compile(r"\b(\w+)\.(?:match|search)\(")


def git(root, *args):
    p = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {p.stderr.strip()}")
    return p.stdout


def changed_files(root, base, head):
    rng = [base, head] if head else [base]
    names = git(root, "diff", "--name-only", *rng).split()
    if not head:  # new files that are not staged yet are part of the change too
        names += git(root, "ls-files", "--others", "--exclude-standard").split()
    return sorted(set(names))


def added_lines(root, base, head, path):
    """The lines the change adds to path, as (line number in the new file, text)."""
    if not head and path in git(root, "ls-files", "--others", "--exclude-standard").split():
        return list(enumerate((root / path).read_text(errors="replace").splitlines(), 1))
    rng = [base, head] if head else [base]
    out, number = [], 0
    for line in git(root, "diff", "-U0", *rng, "--", path).splitlines():
        m = re.match(r"@@ -\S+ \+(\d+)", line)
        if m:
            number = int(m.group(1))
        elif line.startswith("+") and not line.startswith("+++"):
            out.append((number, line[1:]))
            number += 1
    return out


def new_text(root, head, path):
    if head:
        p = subprocess.run(["git", "-C", str(root), "show", f"{head}:{path}"], capture_output=True, text=True)
        return p.stdout if p.returncode == 0 else ""
    f = root / path
    return f.read_text(errors="replace") if f.is_file() else ""


def class_b_paths(root):
    items = json.loads((root / "docs/architecture/software-items.json").read_text())["items"]
    return [p for it in items if it.get("class") == "B" and it.get("shipped") for p in it["paths"]]


# [snippet:fast]
def check_gate(files, **_):
    touched = [f for f in files if f.startswith(GATE_FILES)]
    return [f"{f}: the change edits a check the gate runs; a person reviews it first" for f in touched]


def check_tags(root, base, head, files, **_):
    """Each test the change adds to a product item's tests names a requirement in its body."""
    errors = []
    for f in files:
        if not f.startswith(PRODUCT_TESTS) or not f.endswith((".cpp", ".py")):
            continue
        added = {n for n, _ in added_lines(root, base, head, f)}
        lines = new_text(root, head, f).splitlines()
        starts = [(i, m) for i, line in enumerate(lines, 1)
                  if (m := CPP_TEST.match(line) or PY_TEST.match(line))]
        for k, (i, m) in enumerate(starts):
            if i not in added:
                continue
            end = starts[k + 1][0] - 1 if k + 1 < len(starts) else len(lines)
            if not any(TAG.search(line) for line in lines[i - 1:end]):
                errors.append(f"{f}:{i}: {'.'.join(g for g in m.groups() if g)} names no requirement (REQ:)")
    return errors


def check_tests(root, files, **_):
    """A change to a class B item's source changes a test too."""
    b = class_b_paths(root)
    sources = [f for f in files if f.startswith(tuple(b)) and f.endswith((".cpp", ".hpp"))]
    tests = [f for f in files if "/tests/" in f or pathlib.PurePath(f).name.startswith("test_")]
    if sources and not tests:
        return [f"{', '.join(sources)}: class B source changed and no test changed"]
    return []


def check_validation(root, base, head, files, **_):
    errors = []
    for f in files:
        if not f.endswith((".py", ".cpp", ".hpp")) or "/tests/" in f or pathlib.PurePath(f).name.startswith("test_"):
            continue  # a test's patterns are its data
        anchored = {m.group(1) for line in new_text(root, head, f).splitlines()
                    if (m := COMPILED_NAME.match(line))}
        for n, line in added_lines(root, base, head, f):
            named = {m.group(1) for m in NAMED_CALL.finditer(line)} & anchored
            if ANCHORED.search(line) or ANCHORED_COMPILED.search(line) or named:
                errors.append(f"{f}:{n}: a whole value checked with ^...$; use fullmatch or "
                              "std::regex_match (coding standard rule 3.6)")
    return errors
# [/snippet:fast]


def tool(root, args, cwd=None):
    p = subprocess.run([sys.executable, str(HERE / args[0]), *args[1:]], cwd=cwd or root,
                       capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr).strip()


def from_tool(args, expect_ok=0):
    def run(root, base, **_):
        code, out = tool(root, [a.replace("{root}", str(root)).replace("{base}", base) for a in args])
        return [] if code == expect_ok else [line for line in out.splitlines() if line.strip()][-8:]
    return run


def check_documents(root, base, **_):
    code, out = tool(root, ["design_file.py", str(root), "--check", "--since", base])
    return [] if code == 0 else [line for line in out.splitlines() if "design file:" not in line][-8:]


def check_format(root, base, head, **_):
    code, out = tool(root, ["check_format.py", base] + ([head] if head else []))
    if code == 2:
        return None  # clang-format is not installed: skipped, and the verdict says so
    return [] if code == 0 else ["touched lines need formatting (tools/check_format.py)"]


FAST = [
    ("gate", check_gate),
    ("tags", check_tags),
    ("tests", check_tests),
    ("validation", check_validation),
    ("trace", from_tool(["trace_matrix.py", "{root}", "--check"])),
    ("requirements", from_tool(["req_lint.py", "{root}/docs/regulatory/srs.md"])),
    ("documents", check_documents),
    ("waits", from_tool(["check_test_waits.py", "{root}"])),
    ("layers", from_tool(["check_layers.py", "{root}"])),
    ("agents", from_tool(["check_agent_files.py", "{root}", "--since", "{base}"])),
    ("format", check_format),
]


def full_checks(build):
    def run_build(root, **_):
        p = subprocess.run(["cmake", "--build", str(build), "-j4"], capture_output=True, text=True)
        return [] if p.returncode == 0 else (p.stdout + p.stderr).strip().splitlines()[-8:]

    def run_unit(root, **_):
        p = subprocess.run(["ctest", "--test-dir", str(build), "-L", "unit", "-j4"],
                           capture_output=True, text=True)
        failed = [line.strip() for line in p.stdout.splitlines() if "(Failed)" in line or "(Timeout)" in line]
        return [] if p.returncode == 0 else failed or p.stdout.strip().splitlines()[-4:]

    def run_static(root, **_):
        tidy = root / "build/clang-release"
        if not tidy.is_dir():
            return None
        p = subprocess.run([str(HERE / "static_analysis.sh"), str(tidy)], cwd=root,
                           capture_output=True, text=True)
        return [] if p.returncode == 0 else (p.stdout + p.stderr).strip().splitlines()[-8:]

    return [("build", run_build), ("unit", run_unit), ("static", run_static)]


def judge(root, base, head=None, full=False, build=None):
    """[(check, 'pass' | 'FAIL' | 'skipped', [reasons])] and the verdict."""
    root = pathlib.Path(root).resolve()
    if head and git(root, "rev-parse", "HEAD").strip() != git(root, "rev-parse", head).strip():
        raise RuntimeError(f"{root} must have {head} checked out: the checks read its files")
    files = changed_files(root, base, head)
    checks = FAST + (full_checks(build or root / "build/debug") if full else [])
    results = []
    for name, check in checks:
        found = check(root=root, base=base, head=head, files=files)
        results.append((name, "skipped" if found is None else ("FAIL" if found else "pass"), found or []))
    verdict = "FAIL" if any(r[1] == "FAIL" for r in results) else "PASS"
    return files, results, verdict


def trailer(results, verdict, base, full):
    """The `Gate:` trailer of a verdict: the verdict first, then what it rests on."""
    count = {r: sum(1 for _, x, _ in results if x == r) for r in ("pass", "FAIL", "skipped")}
    parts = [verdict, "full" if full else "fast", f"{count['pass']} passed"]
    if count["FAIL"]:
        parts.append(f"failed: {' '.join(n for n, x, _ in results if x == 'FAIL')}")
    if count["skipped"]:
        parts.append(f"{count['skipped']} skipped")
    return f"Gate: {', '.join(parts)}, since {base[:7]}"


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("root", type=pathlib.Path)
    ap.add_argument("base")
    ap.add_argument("head", nargs="?")
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--build", type=pathlib.Path)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--trailer", action="store_true")
    a = ap.parse_args(argv[1:])
    try:
        files, results, verdict = judge(a.root, a.base, a.head, a.full, a.build)
    except (RuntimeError, OSError, KeyError, ValueError) as e:
        print(f"agent gate: cannot run: {e}", file=sys.stderr)
        return 2
    if a.trailer:
        print(trailer(results, verdict, git(a.root, "rev-parse", "--short=7", a.base).strip(), a.full))
    elif a.json:
        print(json.dumps({"base": a.base, "head": a.head or "working tree", "files": files,
                          "checks": [{"check": n, "result": r, "reasons": why} for n, r, why in results],
                          "verdict": verdict}, indent=1))
    else:
        print(f"agent gate: {len(files)} file(s) changed since {a.base}")
        for name, result, why in results:
            print(f"{result:8} {name}")
            for line in why:
                print(f"         {line}")
        print(f"verdict: {verdict}")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
