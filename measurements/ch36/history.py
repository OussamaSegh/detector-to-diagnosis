#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Chapter 36 measurements: MiniDAQ's own history under the commit policy.

    python3 measurements/ch36/history.py OUT_TEXT [ROOT]

Needs a whole clone (fetch-depth 0) with the tags. Sections:
1. the history: commits, merges, the first-parent line, identities and tags;
2. the commit policy over the whole history and from the first change request on, per rule;
3. the rule reference with whole files under control and with requirements under control;
4. the line "Review:" as written, and as git parses it;
5. the width of subjects and bodies;
6. content addressing: an object's name computed by hand, and what a changed byte does;
7. the time the check takes.
No address, name or message of a commit is printed: the counts are enough.
"""
import hashlib
import json
import pathlib
import re
import statistics
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "tools"))
import check_commits as cc  # noqa: E402

FILE_LEVEL = ["docs/regulatory/srs.md", "docs/regulatory/risk/",
              "docs/architecture/software-items.json", "docs/regulatory/soup-list.md",
              "docs/regulatory/security/threat-model.md"]


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True,
                          check=True).stdout


def main(out_path, root):
    lines = []
    say = lines.append
    policy = json.loads((root / "tools/commit_policy.json").read_text())
    head = git(root, "rev-parse", "--short=7", "HEAD").strip()
    every = cc.commits(root, "HEAD")
    known = cc.known_references(root)
    for c in every:
        c["controlled"] = cc.controlled_changes(root, c, policy["controlled"])
    first_cr = git(root, "log", "--reverse", "--format=%H", "--",
                   "docs/regulatory/changes/CR-0001*").split()[0]
    after = set(git(root, "rev-list", f"{first_cr}^..HEAD").split())

    say(f"Chapter 36: MiniDAQ's history at {head} under commit policy {policy['version']}")
    say(f"git {git(root, 'version').split()[-1]}")
    say("")

    say("1. The history")
    merges = [c for c in every if len(c["parents"]) > 1]
    line = git(root, "rev-list", "--first-parent", "HEAD").split()
    idents = {c["author"] for c in every} | {c["committer"] for c in every}
    tags = git(root, "tag").split()
    annotated = [t for t in tags if git(root, "cat-file", "-t", t).strip() == "tag"]
    say(f"commits {len(every)}, merges {len(merges)}, on the first-parent line {len(line)}")
    say(f"distinct identities (author or committer): {len(idents)}")
    say(f"tags {len(tags)}, annotated {len(annotated)}")
    say(f"commits since the first change request (CR-0001): {len(after)}")
    say("")

    say("2. The policy, commits that break each rule (accepted exceptions not applied)")
    for label, subset in (("whole history", every),
                          ("since CR-0001", [c for c in every if c["sha"] in after])):
        counts = {r: 0 for r in cc.RULES}
        for c in subset:
            for rule in {r for r, _ in cc.check(c, policy, known)}:
                counts[rule] += 1
        say(f"  {label:14s} ({len(subset)} commits): "
            + ", ".join(f"{r} {n}" for r, n in counts.items()))
    web = [c for c in merges if cc.identity(c, policy)]
    say(f"  merges whose identity is not a no-reply address: {len(web)} of {len(merges)}")
    say("")

    say("3. The rule reference: what is under control")
    for label, subset in (("whole history", every),
                          ("since CR-0001", [c for c in every if c["sha"] in after])):
        file_level = req_level = 0
        for c in subset:
            if len(c["parents"]) > 1:
                continue
            ok = (re.search(policy["references"], c["message"])
                  or any(c["sha"].startswith(h) for h in known["commits"]))
            if not ok and any(f.startswith(tuple(FILE_LEVEL)) for f in c["files"]):
                file_level += 1
            if cc.reference(c, policy, known):
                req_level += 1
        say(f"  {label:14s}: five documents as whole files {file_level} commits without a "
            f"reference; requirements, hazards and items {req_level}")
    say("")

    say("4. The review line")
    with_line = [c for c in every if re.search(r"^Review:", c["message"], re.M)]
    parsed_ours = [c for c in with_line if "Review" in dict(cc.trailers(c["message"]))]
    parsed_git = [s for s in git(root, "log", "--format=%H%x00%(trailers:key=Review,valueonly)%x1e",
                                 "HEAD").split("\x1e") if s.strip().split("\x00")[-1].strip()]
    say(f"commits with a line 'Review:' {len(with_line)} of {len(every)}; in the trailer block, "
        f"by this tool {len(parsed_ours)}, by git log %(trailers) {len(parsed_git)}")
    say("")

    say("5. Widths")
    subjects = [len(c["message"].split("\n", 1)[0]) for c in every]
    bodies = [max((len(x) for x in c["message"].split("\n")[2:]
                   if x and not cc.TOKEN.match(x)), default=0) for c in every]
    bodies = [b for b in bodies if b]
    say(f"subject: median {statistics.median(subjects):.0f}, longest {max(subjects)}, over 72 "
        f"{sum(s > 72 for s in subjects)}")
    say(f"longest body line per commit: median {statistics.median(bodies):.0f}, over 72 "
        f"{sum(b > 72 for b in bodies)} of {len(bodies)} commits with a body")
    say("")

    say("6. Content addressing")
    path = "VERSION"
    data = (root / path).read_bytes()
    mine = hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()
    theirs = git(root, "hash-object", path).strip()
    say(f"{path}: sha1('blob {len(data)}\\0' + content) = {mine[:12]}, git hash-object "
        f"{theirs[:12]}, equal: {mine == theirs}")
    changed = bytearray(data)
    changed[0] ^= 1
    other = hashlib.sha1(b"blob %d\0" % len(changed) + bytes(changed)).hexdigest()
    differ = sum(a != b for a, b in zip(bytes.fromhex(mine), bytes.fromhex(other)))
    say(f"one bit changed: {other[:12]}, {differ} of 20 bytes of the name differ")
    fmt = git(root, "rev-parse", "--show-object-format").strip()
    say(f"object format of this repository: {fmt}")
    say("")

    say("7. Time")
    times = []
    for _ in range(3):
        t = time.perf_counter()
        subprocess.run([sys.executable, str(root / "tools/check_commits.py"), str(root), "HEAD",
                        "--all-rules"], capture_output=True, check=True)
        times.append(time.perf_counter() - t)
    say(f"check_commits.py over the whole history ({len(every)} commits): median "
        f"{statistics.median(times):.2f} s of 3")

    pathlib.Path(out_path).write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else HERE / "history.txt",
         pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else HERE.parent.parent)
