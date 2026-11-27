# SPDX-License-Identifier: MIT
"""The guard an agent's shell commands pass before they run: it refuses a git push that would
change published history or reach a branch the session does not own (SDP section 5)."""
import re
import shlex

SEPARATORS = re.compile(r"\s*(?:&&|\|\||;|\||\n)\s*")
REFUSED = {"--all": "pushes every branch", "--mirror": "pushes every ref",
           "--tags": "pushes every tag", "--delete": "deletes a remote branch",
           "-d": "deletes a remote branch", "--force": "forces a push", "-f": "forces a push",
           "--force-with-lease": "forces a push"}


def words(segment):
    try:
        return shlex.split(segment)
    except ValueError:
        return segment.split()


def check_push(segment, own_branch):
    w = words(segment)
    if len(w) < 2 or w[0] != "git":
        return []
    i = 1
    while i < len(w) and w[i].startswith("-"):  # git -C DIR push ...
        i += 2 if w[i] == "-C" else 1
    if i >= len(w) or w[i] != "push":
        return []
    args = w[i + 1:]
    errors = [f"git push {a}: {REFUSED[a.split('=')[0]]}" for a in args if a.split("=")[0] in REFUSED]
    for a in args:  # short options together, -fu or -uf: each letter is an option
        if re.fullmatch(r"-[A-Za-z]{2,}", a):
            errors += [f"git push {a}: {REFUSED['-' + c]}" for c in "fd" if c in a[1:]]
    plain = [a for a in args if not a.startswith("-")]
    for ref in plain[1:]:  # plain[0] is the remote
        if ref.startswith("+"):
            errors.append(f"git push {ref}: forces a push")
            ref = ref[1:]
        if ref.startswith(":"):  # an empty source deletes the destination
            errors.append(f"git push {ref}: deletes a remote branch")
        dst = ref.split(":", 1)[1] if ":" in ref else ref
        if dst not in (own_branch, "main"):
            errors.append(f"git push to '{dst}': only '{own_branch}' and 'main'")
    return errors


def refusals(command, own_branch):
    """The reasons to refuse `command` (a shell command line), an empty list to allow it."""
    return [e for s in SEPARATORS.split(command) if s.strip() for e in check_push(s, own_branch)]
