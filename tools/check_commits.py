#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Checks a range of commits against MiniDAQ's commit policy (Chapter 36, ADR 0031).

    check_commits.py ROOT [RANGE] [--policy FILE] [--all-rules]

ROOT is the repository. RANGE is a git revision range; without it, the range starts at the
policy's `since` commit and ends at HEAD. The policy is tools/commit_policy.json. With
--all-rules, every commit of the range is checked by every rule and the problems are counted per
rule, without the accepted exceptions: that is the measurement of a history, not a gate.

The rules (the policy names them):

- identity: the author's and the committer's addresses are no-reply or placeholder addresses
  (the repository is public; an address in a commit is published with the history);
- subject: a first line of at most `subject_max` characters, no trailing period, not a fixup,
  squash or work-in-progress commit;
- layout: a blank second line, and body lines of at most `body_max` characters except trailers,
  indented lines and lines that are a URL;
- review: a trailer `Review:` that git itself parses (the last paragraph of the message);
- reference: a commit that changes a requirement of the SRS (its text, item or methods; not
  its verification), a hazard or risk control, or a software item names a change request (CR-NNNN) or a
  problem report (MDQ-PR-NNN) that exists in the repository, or a change request names it in
  its field Commits (the trace in either direction);
- merge: a merge commit has two parents and names what it merges.

Exit status: 0 if no commit breaks a rule, 1 if one does, 2 for a usage error or a range that
git cannot resolve (a shallow clone, for example).
"""
import json
import pathlib
import re
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from trace_matrix import parse_srs  # noqa: E402

POLICY = pathlib.Path("tools/commit_policy.json")
RULES = ("identity", "subject", "layout", "review", "reference", "merge")


# [snippet:trailers]
TOKEN = re.compile(r"^([A-Za-z0-9][A-Za-z0-9-]*)\s*:\s?(.*)$")
GIT_GENERATED = ("Signed-off-by: ", "(cherry picked from commit ")


def trailers(message):
    """The trailers of a commit message as git finds them: [(key, value)], in order.

    The trailer block is the last paragraph, never the first (the subject). It counts if every
    line in it is a trailer or a continuation (a line that starts with white space), or if it has
    a line git itself generates and at least a quarter of its lines are trailers.
    """
    lines = message.rstrip("\n").split("\n")
    while lines and not lines[-1].strip():
        lines.pop()
    start = len(lines)
    while start > 0 and lines[start - 1].strip():
        start -= 1
    title_end = next((i for i, line in enumerate(lines) if not line.strip()), len(lines))
    if start <= title_end:
        return []  # the last paragraph is the subject
    block = lines[start:]
    found, others, generated = [], 0, False
    for line in block:
        m = TOKEN.match(line)
        if line[:1].isspace() and found:
            key, value = found[-1]
            found[-1] = (key, value + " " + line.strip())
        elif m:
            found.append((m.group(1), m.group(2).strip()))
            generated = generated or line.startswith(GIT_GENERATED[0])
        elif line.startswith(GIT_GENERATED[1]):
            generated = True
            others += 1
        else:
            others += 1
    if found and (others == 0 or (generated and 3 * len(found) >= others)):
        return found
    return []
# [/snippet:trailers]


def git(root, *args):
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise ValueError(f"git {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout


FIELDS = ("%H", "%P", "%an", "%ae", "%cn", "%ce", "%B")


def commits(root, revision_range):
    """Every commit of the range, oldest first, with its parents, identities, message and files."""
    out = git(root, "log", "--reverse", "--format=" + "%x00".join(FIELDS) + "%x1e", revision_range)
    found = []
    for record in out.split("\x1e"):
        record = record.lstrip("\n")
        if not record:
            continue
        sha, parents, an, ae, cn, ce, body = record.split("\x00")
        parents = parents.split()
        base = parents[0] if parents else "4b825dc642cb6eb9a060e54bf8d69288fbee4904"  # empty tree
        files = git(root, "diff", "--name-only", "--no-renames", base, sha).split()
        found.append({"sha": sha, "parents": parents, "author": (an, ae), "committer": (cn, ce),
                      "message": body, "files": files, "base": base if parents else None})
    return found


def show(root, sha, path):
    """The text of a file at a commit, or "" where it does not exist."""
    if sha is None:
        return ""
    try:
        return git(root, "show", f"{sha}:{path}")
    except ValueError:
        return ""


# [snippet:controlled]
def controlled_changes(root, commit, controlled):
    """What a commit changes that the procedure puts under change control: the requirements
    whose text, item or methods change, are added or are removed, and the controlled files."""
    changes = [f for f in commit["files"] if f in controlled["files"]]
    srs = controlled["requirements"]
    if srs in commit["files"]:
        old = parse_srs(show(root, commit["base"], srs))[0]
        new = parse_srs(show(root, commit["sha"], srs))[0]
        changes += sorted(r for r in old.keys() | new.keys() if old.get(r) != new.get(r))
    return changes
# [/snippet:controlled]


# [snippet:rules]
def identity(commit, policy):
    bad = []
    for role in ("author", "committer"):
        name, address = commit[role]
        domain = address.rsplit("@", 1)[-1].lower()
        if not (domain in policy["identity_domains"]
                or address.lower().startswith(tuple(policy["identity_local_parts"]))):
            bad.append(f"the {role}'s address is not a no-reply address")
    return bad


def subject(commit, policy):
    first = commit["message"].split("\n", 1)[0]
    bad = []
    if not first.strip():
        bad.append("empty subject")
    if len(first) > policy["subject_max"]:
        bad.append(f"subject of {len(first)} characters (at most {policy['subject_max']})")
    if first.rstrip().endswith("."):
        bad.append("subject ends with a period")
    if re.match(r"(fixup!|squash!|amend!|wip\b)", first, re.I):
        bad.append("a fixup, squash or work-in-progress commit")
    return bad


def layout(commit, policy):
    lines = commit["message"].rstrip("\n").split("\n")
    bad = []
    if len(lines) > 1 and lines[1].strip():
        bad.append("no blank line after the subject")
    keys = {f"{k}:" for k, _ in trailers(commit["message"])}
    for n, line in enumerate(lines[2:], start=3):
        if (len(line) > policy["body_max"] and not line[:1].isspace()
                and not re.fullmatch(r"\S*https?://\S+", line)
                and not any(line.startswith(k) for k in keys)):
            bad.append(f"line {n} has {len(line)} characters (at most {policy['body_max']})")
    return bad


def review(commit, policy):
    if len(commit["parents"]) > 1:
        return []  # a merge is reviewed with its branch (rule merge)
    keys = [k for k, _ in trailers(commit["message"])]
    if policy["review_trailer"] in keys:
        return []
    if re.search(rf"^{policy['review_trailer']}:", commit["message"], re.M):
        return [f"'{policy['review_trailer']}:' is not in the trailer block (git does not parse it)"]
    return [f"no '{policy['review_trailer']}:' trailer"]


def reference(commit, policy, known):
    if len(commit["parents"]) > 1:
        return []
    controlled = commit.get("controlled", [])
    if not controlled or any(commit["sha"].startswith(h) for h in known["commits"]):
        return []
    named = set(re.findall(policy["references"], commit["message"]))
    if not named:
        more = f" and {len(controlled) - 1} more" if len(controlled) > 1 else ""
        return [f"changes {controlled[0]}{more} (under change control) and names no change "
                "request or problem report"]
    missing = sorted(named - known["names"])
    return [f"names {', '.join(missing)}, which the repository does not have"] if missing else []


def merge(commit, policy):
    if len(commit["parents"]) < 2:
        return []
    bad = []
    if len(commit["parents"]) > 2:
        bad.append(f"an octopus merge of {len(commit['parents'])} parents")
    if not re.match(r"Merge\b", commit["message"]):
        bad.append("a merge whose subject does not say what it merges")
    return bad
# [/snippet:rules]


def known_references(root):
    """{"names": the change requests and problem reports the repository has, "commits": the
    abbreviated hashes that change requests list in their field Commits}."""
    root = pathlib.Path(root)
    names, listed = set(), set()
    for p in (root / "docs/regulatory/changes").glob("CR-*.md"):
        if m := re.match(r"CR-\d{4}", p.name):
            names.add(m.group(0))
            row = re.search(r"^\|\s*Commits\s*\|(.*)\|\s*$", p.read_text(), re.M)
            if row:
                listed |= set(re.findall(r"\b[0-9a-f]{7,40}\b", row.group(1)))
    reports = root / "docs/regulatory/problem-reports.json"
    if reports.exists():
        names |= set(re.findall(r"MDQ-PR-\d{3}", reports.read_text()))
    return {"names": names, "commits": listed}


def check(commit, policy, known, rules=RULES):
    """[(rule, problem)] for one commit."""
    found = []
    for rule in rules:
        fn = globals()[rule]
        problems = fn(commit, policy, known) if rule == "reference" else fn(commit, policy)
        found += [(rule, p) for p in problems]
    return found


def accepted(policy, sha, rule):
    return any(sha.startswith(a["commit"]) and a["rule"] == rule for a in policy["accepted"])


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    all_rules = "--all-rules" in argv
    policy_path = None
    if "--policy" in argv:
        i = argv.index("--policy")
        policy_path = pathlib.Path(argv[i + 1])
        args.remove(argv[i + 1])
    if not args:
        print(__doc__.split("\n\n")[1].strip(), file=sys.stderr)
        return 2
    root = pathlib.Path(args[0])
    policy = json.loads((policy_path or root / POLICY).read_text())
    revision_range = args[1] if len(args) > 1 else f"{policy['since']}..HEAD"
    try:
        found = commits(root, revision_range)
    except ValueError as e:
        print(f"check_commits: {e} (a shallow clone needs the whole history: fetch-depth 0)",
              file=sys.stderr)
        return 2
    known = known_references(root)
    counts, problems = {r: 0 for r in RULES}, 0
    rules = RULES if all_rules else [r for r in RULES if r in policy["rules"]]
    for c in found:
        c["controlled"] = controlled_changes(root, c, policy["controlled"])
        broken = set()
        for rule, text in check(c, policy, known, rules):
            if not all_rules and accepted(policy, c["sha"], rule):
                continue
            broken.add(rule)
            problems += 1
            if not all_rules:
                print(f"{c['sha'][:12]} {rule}: {text}")
        for rule in broken:
            counts[rule] += 1
    if all_rules:
        print(f"{len(found)} commits; commits that break each rule: "
              + ", ".join(f"{r} {n}" for r, n in counts.items()))
    print(f"commit policy {policy['version']}: {len(found)} commits, {problems} problem(s)")
    return 1 if problems and not all_rules else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
