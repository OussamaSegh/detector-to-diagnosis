#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""The agent's hook before each shell command (roadmap 2.2.0, Theme P2; CR-0036).

`.claude/settings.json` runs it before every Bash command an agent asks for. It reads the hook's
JSON on stdin (`tool_name`, `tool_input.command`, `cwd`) and refuses, with exit status 2 and the
rule on stderr, a command that

1. writes to an absolute path outside the repository, the temporary directories (`/tmp`,
   `$TMPDIR`, `/dev/null` and the other `/dev/` streams) and the directories that the variable
   MINIDAQ_AGENT_WRITABLE lists (separated by `:`; a machine sets it in its own, uncommitted
   `.claude/settings.local.json`): a redirection (`>`, `>>`), `tee`, the target of `cp`, `mv`,
   `install`, `ln`, or the operands of `rm`, `mkdir`, `touch`, `rmdir`;
2. pushes to a branch other than the session's own (the variable MINIDAQ_SESSION_BRANCH, else the
   branch checked out) and `main`, pushes every branch or tag at once (`--all`, `--mirror`,
   `--tags`), deletes a remote branch, or forces a push (SDP section 5: a published history is
   not rewritten without a change request).

Every other command is allowed (exit status 0, nothing printed). The hook refuses only what the
project's rules already forbid, and names the rule, so that a session does not learn to work
around it. It is a guard against mistakes, not a sandbox: a command built at run time (`eval`, a
script, a variable that holds a path) is not seen. The permissions of `.claude/settings.json` and
a person's review stay the controls.

    agent_command.py [--root DIR]      (the hook: JSON on stdin)
"""
import json
import os
import pathlib
import re
import shlex
import subprocess
import sys

SEPARATORS = re.compile(r"\s*(?:&&|\|\||;|\||\n)\s*")
REDIRECT = re.compile(r"(?:^|[\s0-9&])>>?\s*([^\s;&|]+)")
TARGET_LAST = {"cp", "mv", "install", "ln"}
ALL_OPERANDS = {"rm", "mkdir", "touch", "rmdir", "tee"}
PUSH_REFUSED = {"--all": "pushes every branch", "--mirror": "pushes every ref",
                "--tags": "pushes every tag (tags go through .github/tags.txt)",
                "--delete": "deletes a remote branch", "-d": "deletes a remote branch",
                "--force": "forces a push", "-f": "forces a push",
                "--force-with-lease": "forces a push"}


def temporary_dirs():
    dirs = ["/tmp", "/var/tmp", "/dev"]
    if os.environ.get("TMPDIR"):
        dirs.append(os.environ["TMPDIR"])
    dirs += [d for d in os.environ.get("MINIDAQ_AGENT_WRITABLE", "").split(":") if d]
    return [pathlib.Path(d).resolve() for d in dirs]


def inside(path, dirs):
    return any(path == d or d in path.parents for d in dirs)


def outside_write(path, root):
    """True when path is absolute (or ~) and outside the repository and the temporary dirs."""
    if not path.startswith(("/", "~")):
        return False
    p = pathlib.Path(os.path.expanduser(path)).resolve()
    return not inside(p, [root.resolve()] + temporary_dirs())


def words(segment):
    try:
        return shlex.split(segment, comments=True)
    except ValueError:
        return segment.split()


def check_writes(segment, root):
    found = [m.group(1) for m in REDIRECT.finditer(segment)]
    w = words(segment)
    while w and re.fullmatch(r"\w+=.*", w[0]):  # VAR=value before the command
        w = w[1:]
    if w and w[0] == "sudo":
        w = w[1:]
    if w:
        operands = [a for a in w[1:] if not a.startswith("-")]
        name = pathlib.PurePath(w[0]).name
        if name in TARGET_LAST and operands:
            found.append(operands[-1])
        elif name in ALL_OPERANDS:
            found.extend(operands)
    return [f"writes to {p}, outside the repository (rule: an agent changes only its checkout "
            "and the temporary directories)" for p in found if outside_write(p, root)]


def session_branch(root):
    if os.environ.get("MINIDAQ_SESSION_BRANCH"):
        return os.environ["MINIDAQ_SESSION_BRANCH"]
    p = subprocess.run(["git", "-C", str(root), "symbolic-ref", "--short", "HEAD"],
                       capture_output=True, text=True)
    return p.stdout.strip() if p.returncode == 0 else ""


def check_push(segment, root):
    w = words(segment)
    if len(w) < 2 or pathlib.PurePath(w[0]).name != "git":
        return []
    i = 1
    while i < len(w) and w[i].startswith("-"):  # git -C DIR push ...
        i += 2 if w[i] in ("-C", "-c") else 1
    if i >= len(w) or w[i] != "push":
        return []
    args = w[i + 1:]
    errors = [f"git push {a}: {why} (rule: SDP section 5 and the session's branch)"
              for a, why in PUSH_REFUSED.items() if a in args]
    plain = [a for a in args if not a.startswith("-")]
    own = session_branch(root)
    allowed = {"main", own} - {""}
    for ref in plain[1:]:  # plain[0] is the remote
        if ref.startswith("+"):
            errors.append(f"git push {ref}: forces a push (rule: SDP section 5)")
            ref = ref[1:]
        dst = ref.split(":", 1)[1] if ":" in ref else ref
        dst = own if dst == "HEAD" else dst.removeprefix("refs/heads/")
        if dst not in allowed:
            errors.append(f"git push to '{dst}': only the session's branch ('{own}') and 'main' "
                          "(rule: the session pushes only its own branch and main)")
    return errors


def refusals(command, root):
    errors = []
    for segment in SEPARATORS.split(command):
        if segment.strip():
            errors += check_writes(segment, root) + check_push(segment, root)
    return errors


def main(argv):
    root = pathlib.Path(argv[argv.index("--root") + 1] if "--root" in argv
                        else os.environ.get("CLAUDE_PROJECT_DIR", ".")).resolve()
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0  # not a hook event: nothing to judge
    if event.get("tool_name") != "Bash":
        return 0
    errors = refusals(event.get("tool_input", {}).get("command", ""), root)
    for e in errors:
        print(f"refused by tools/hooks/agent_command.py: {e}", file=sys.stderr)
    return 2 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
