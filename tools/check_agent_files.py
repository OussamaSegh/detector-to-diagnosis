#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Checks MiniDAQ's agent files (roadmap 2.2.0, Theme P2; CR-0036; TL-52).

The agent files are what an AI coding agent reads or obeys in this repository: the context file
`CLAUDE.md`, the settings `.claude/settings.json` (permissions and hooks), the subagents
`.claude/agents/*.md`, the skills `.claude/skills/*/SKILL.md`, and their register
`.claude/README.md`. An agent follows a stale instruction as faithfully as a true one, and a
permission it was given is used, so the files are checked like code:

1. **Fields.** A subagent or skill starts with frontmatter that has the fields its kind requires
   (tools/agent_files_policy.json), a `name` equal to its file's (or directory's) name, a
   `version` that its body's `## Document history` table ends with, and an `owner`.
2. **References.** Every repository path named in a code span or a fenced block exists (with the
   placeholders `NN`, `X.Y.Z`, `<name>` and `*`), and every `ctest -R NAME` names a test that a
   CMakeLists.txt defines (Exercise 37.2, extended).
3. **Least privilege.** A subagent's `tools` and a skill's `allowed-tools` are within its kind's
   list; the settings allow no rule the policy forbids, deny every rule it requires, set a
   default mode it allows, and run the policy's hooks, whose scripts exist.
4. **Nothing private.** No private key, token or password, no e-mail address other than a
   placeholder or a no-reply address, and no absolute path to a home or mount directory.
5. **Register.** `.claude/README.md` lists every agent file with its kind, version and owner, and
   the versions agree with the files. With --since REF, every agent file that changed since REF
   has a version other than the one it had there.

The check reads only the fields it needs, so a field the agent's format adds later does not
break it; a field it relies on that changes is a change request (roadmap 2.2.0, section 6).

    check_agent_files.py ROOT [--since REF]

Exit status 0 if every file passes, 1 if one fails.
"""
import json
import pathlib
import re
import subprocess
import sys

POLICY = pathlib.Path(__file__).resolve().parent / "agent_files_policy.json"
REGISTER = ".claude/README.md"
SPAN = re.compile(r"`([^`\n]+)`")
FENCE = re.compile(r"^\s*(```|~~~)")
TEST = re.compile(r"\bctest\b[^\n`]*?\s-R\s+'?\"?([\w./-]+)")
ADD_TEST = re.compile(r"add_test\(\s*NAME\s+([\w./-]+)")
PLACEHOLDER = re.compile(r"NN|X\.Y\.Z|<[^>/]+>|\*")
TOOL = re.compile(r"[A-Za-z_][\w-]*(?:\([^)]*\))?")
HISTORY = re.compile(r"^## Document history\b", re.M)
ROW = re.compile(r"^\|\s*(\d+)\s*\|", re.M)
VERSION_LINE = re.compile(r"^Version (\d+)\b", re.M)
SECRETS = [
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "a private key"),
    (re.compile(r"\b(?:ghp|gho|ghs|ghu)_[A-Za-z0-9]{20,}|\bgithub_pat_[A-Za-z0-9_]{20,}"), "a GitHub token"),
    (re.compile(r"\bsk-[A-Za-z0-9-]{20,}"), "an API key"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "an AWS access key"),
    (re.compile(r"(?i)\b(?:password|passwd|secret|api[_-]?key|token)\s*[:=]\s*['\"]?[^\s'\"`]{8,}"),
     "a credential"),
]
ADDRESS = re.compile(r"(?<![\w.%+-])[A-Za-z0-9][A-Za-z0-9._%+-]*"
                     r"@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,})")
ALLOWED_DOMAINS = ("example.com", "example.org", "example.invalid", "users.noreply.github.com")
ABSOLUTE = re.compile(r"(?<![\w.~$}])(/(?:home|Users|root|mnt)/[^\s`'\")]*|\b[A-Za-z]:\\[^\s`]*)")


def agent_files(root):
    """{relative path: kind} of the agent files present under root."""
    found = {}
    for rel, kind in [("CLAUDE.md", "context"), (REGISTER, "register"),
                      (".claude/settings.json", "settings")]:
        if (root / rel).is_file():
            found[rel] = kind
    for p in sorted((root / ".claude/agents").glob("*.md")):
        found[p.relative_to(root).as_posix()] = "agent"
    for p in sorted((root / ".claude/skills").glob("*/SKILL.md")):
        found[p.relative_to(root).as_posix()] = "skill"
    return found


# [snippet:frontmatter]
def frontmatter(text):
    """The fields of a file's YAML frontmatter as {key: str or [str]}, or None without one.

    Only the forms the agent files use: `key: value`, `key: >` with indented lines, and a list
    of `- item` lines under `key:`."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    fields, key = {}, None
    for line in lines[1:]:
        if line.strip() == "---":
            return fields
        m = re.fullmatch(r"([\w-]+):\s*(.*)", line)
        if m:
            key, value = m.group(1), m.group(2).strip()
            fields[key] = "" if value in (">", "|", ">-", "|-") else value.strip("'\"")
        elif key and re.fullmatch(r"\s+-\s+.*", line):
            item = line.strip()[1:].strip().strip("'\"")
            fields[key] = (fields[key] if isinstance(fields[key], list) else []) + [item]
        elif key and line.startswith((" ", "\t")) and isinstance(fields[key], str):
            fields[key] = (fields[key] + " " + line.strip()).strip()
    return None  # no closing ---
# [/snippet:frontmatter]


def tools_of(value):
    """The tools a `tools` or `allowed-tools` field names: a comma- or space-separated string, or
    a list."""
    items = value if isinstance(value, list) else [value]
    return [t for item in items for t in TOOL.findall(item)]


def history_version(text):
    """The last version of the `## Document history` table, or None."""
    h = HISTORY.search(text)
    if not h:
        return None
    rows = [int(n) for n in ROW.findall(text[h.end():].split("\n## ", 1)[0])]
    return rows[-1] if rows and rows == list(range(1, len(rows) + 1)) else -1


def check_fields(rel, kind, text, policy):
    fm = frontmatter(text)
    if fm is None:
        return [f"{rel}: no frontmatter (--- at the first line, fields, ---)"], None
    errors = [f"{rel}: frontmatter lacks '{f}'" for f in policy[kind]["required"] if not fm.get(f)]
    expected = pathlib.PurePath(rel).stem if kind == "agent" else pathlib.PurePath(rel).parent.name
    if fm.get("name") and fm["name"] != expected:
        errors.append(f"{rel}: name '{fm['name']}' is not the file's name '{expected}'")
    version = fm.get("version", "")
    if version and not version.isdigit():
        errors.append(f"{rel}: version '{version}' is not a whole number")
    elif version:
        last = history_version(text)
        if last is None:
            errors.append(f"{rel}: no '## Document history' table")
        elif last != int(version):
            errors.append(f"{rel}: version {version}, but the history table ends with {last} "
                          "(or is not numbered 1, 2, 3 ...)")
    key = "tools" if kind == "agent" else "allowed-tools"
    for t in tools_of(fm.get(key, [])):
        if t not in policy[kind]["tools"]:
            errors.append(f"{rel}: allows {t}, which a {kind} may not (tools/agent_files_policy.json)")
    if kind == "agent" and fm.get("permissionMode"):
        errors.append(f"{rel}: sets permissionMode; a subagent keeps the session's permissions")
    return errors, fm


def tracked(root):
    p = subprocess.run(["git", "-C", str(root), "ls-files", "--cached", "--others",
                        "--exclude-standard"], capture_output=True, text=True)
    return p.stdout.splitlines() if p.returncode == 0 else []


def pattern(path):
    out = ""
    for part in re.split(r"(NN|X\.Y\.Z|<[^>/]+>|\*)", path):
        if part == "NN":
            out += r"\d\d"
        elif part == "X.Y.Z":
            out += r"\d+\.\d+\.\d+"
        elif part == "*" or part.startswith("<"):
            out += r"[^/]+"
        else:
            out += re.escape(part)
    return re.compile(out + r"(?:/.*)?")


def references(text, tops):
    found, fenced = [], False
    for n, line in enumerate(text.splitlines(), 1):
        if FENCE.match(line):
            fenced = not fenced
            continue
        words = line.split() if fenced else [w for s in SPAN.findall(line) for w in s.split()]
        for word in words:
            if "://" in word or word.startswith("$"):
                continue
            path = re.sub(r":\d+(-\d+)?$", "", word.strip().strip(".,;:()[]'\"")).rstrip("/")
            if path and path.split("/")[0] in tops:
                found.append((n, path))
    return found


def check_references(rel, text, root, files, tests):
    tops = {f.split("/")[0] for f in files}
    dirs = {"/".join(f.split("/")[:k]) for f in files for k in range(1, f.count("/") + 1)}
    every = set(files) | dirs
    errors = []
    for n, path in references(text, tops):
        if PLACEHOLDER.search(path):
            if not any(pattern(path).fullmatch(f) for f in every):
                errors.append(f"{rel}:{n}: nothing matches {path}")
        elif path not in every:
            errors.append(f"{rel}:{n}: {path} does not exist")
    for n, line in enumerate(text.splitlines(), 1):
        for name in TEST.findall(line):
            if name not in tests:
                errors.append(f"{rel}:{n}: no test named {name}")
    return errors


def check_private(rel, text):
    errors = []
    for n, line in enumerate(text.splitlines(), 1):
        for rx, what in SECRETS:
            if rx.search(line):
                errors.append(f"{rel}:{n}: holds {what}")
        for m in ADDRESS.finditer(line):
            if not m.group(1).lower().endswith(ALLOWED_DOMAINS) and "noreply" not in m.group(0):
                errors.append(f"{rel}:{n}: holds an e-mail address")
        for m in ABSOLUTE.finditer(line):
            errors.append(f"{rel}:{n}: names {m.group(1)}, an absolute path outside the repository")
    return errors


def check_settings(rel, text, root, policy):
    try:
        data = json.loads(text)
    except ValueError as e:
        return [f"{rel}: not JSON: {e}"]
    p, errors = policy["settings"], []
    perms = data.get("permissions", {})
    for rule in perms.get("allow", []):
        if any(re.fullmatch(f, rule) for f in p["forbidden"]):
            errors.append(f"{rel}: allows {rule}, which the policy forbids")
    for rule in p["deny"]:
        if rule not in perms.get("deny", []):
            errors.append(f"{rel}: does not deny {rule}")
    mode = perms.get("defaultMode", "default")
    if mode not in p["modes"]:
        errors.append(f"{rel}: default mode {mode} is not one of {', '.join(p['modes'])}")
    for event, script in p["hooks"].items():
        commands = [h.get("command", "") for group in data.get("hooks", {}).get(event, [])
                    for h in group.get("hooks", [])]
        if not any(script in c for c in commands):
            errors.append(f"{rel}: no {event} hook runs {script}")
    for group in [g for gs in data.get("hooks", {}).values() for g in gs]:
        for h in group.get("hooks", []):
            for script in re.findall(r"(tools/[\w./-]+)", h.get("command", "")):
                if not (root / script).is_file():
                    errors.append(f"{rel}: hook runs {script}, which does not exist")
    return errors


def register(root):
    """{path: (kind, version, owner)} from the register's table."""
    rows = {}
    f = root / REGISTER
    if f.is_file():
        for m in re.finditer(r"^\|\s*`([^`]+)`\s*\|\s*(\w+)\s*\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|",
                             f.read_text(), re.M):
            rows[m.group(1)] = (m.group(2), int(m.group(3)), m.group(4))
    return rows


def version_in_file(kind, text):
    if kind in ("agent", "skill"):
        v = (frontmatter(text) or {}).get("version", "")
        return int(v) if str(v).isdigit() else None
    if kind in ("context", "register"):
        m = VERSION_LINE.search("\n".join(text.splitlines()[:6]))
        return int(m.group(1)) if m else None
    return None  # settings: JSON has no place for it; the register holds its version


def check_register(root, found):
    if not found:
        return []
    if REGISTER not in found:
        return [f"{REGISTER}: the register of the agent files is missing"]
    rows, errors = register(root), []
    for rel, kind in found.items():
        if rel == REGISTER:
            continue
        if rel not in rows:
            errors.append(f"{REGISTER}: does not list {rel}")
            continue
        if rows[rel][0] != kind:
            errors.append(f"{REGISTER}: lists {rel} as {rows[rel][0]}, it is a {kind}")
        v = version_in_file(kind, (root / rel).read_text())
        if v is not None and v != rows[rel][1]:
            errors.append(f"{REGISTER}: lists {rel} at version {rows[rel][1]}, the file is at {v}")
    errors += [f"{REGISTER}: lists {rel}, which does not exist" for rel in rows if rel not in found]
    return errors


def git_show(root, ref, rel):
    p = subprocess.run(["git", "-C", str(root), "show", f"{ref}:{rel}"], capture_output=True,
                       text=True)
    return p.stdout if p.returncode == 0 else None


def check_since(root, found, ref):
    """Every agent file that changed since ref has a new version (in the file or the register)."""
    errors = []
    old_rows = {}
    old_reg = git_show(root, ref, REGISTER)
    if old_reg is not None:
        for m in re.finditer(r"^\|\s*`([^`]+)`\s*\|\s*\w+\s*\|\s*(\d+)\s*\|", old_reg, re.M):
            old_rows[m.group(1)] = int(m.group(2))
    rows = register(root)
    for rel in found:
        old = git_show(root, ref, rel)
        if old is None or old == (root / rel).read_text():
            continue
        if rel in rows and rel in old_rows and rows[rel][1] == old_rows[rel]:
            errors.append(f"{rel}: changed since {ref} and still at version {rows[rel][1]}")
    return errors


def check(root, since=None):
    root = pathlib.Path(root).resolve()
    policy = json.loads(POLICY.read_text())
    found = agent_files(root)
    files = tracked(root)
    tests = {n for f in files if f.endswith("CMakeLists.txt") and (root / f).is_file()
             for n in ADD_TEST.findall((root / f).read_text(errors="replace"))}
    errors = []
    for rel, kind in found.items():
        text = (root / rel).read_text(errors="replace")
        if kind in ("agent", "skill"):
            errors += check_fields(rel, kind, text, policy)[0]
        if kind == "settings":
            errors += check_settings(rel, text, root, policy)
        else:
            errors += check_references(rel, text, root, files, tests)
        errors += check_private(rel, text)
    errors += check_register(root, found)
    if since:
        errors += check_since(root, found, since)
    return found, errors


def main(argv):
    if len(argv) < 2:
        print(__doc__.split("\n\n")[-2], file=sys.stderr)
        return 2
    since = argv[argv.index("--since") + 1] if "--since" in argv else None
    found, errors = check(argv[1], since)
    for e in errors:
        print(e, file=sys.stderr)
    print(f"agent files: {len(found)} file(s), {len(errors)} problem(s)", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
