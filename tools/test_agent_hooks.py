#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Tests of the agent's hooks, tools/hooks/agent_command.py and tools/hooks/agent_edit.py
(roadmap 2.2.0, Theme P2; CR-0036): each hook run as the agent runs it, with its JSON on stdin,
in a scratch repository."""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
COMMAND = ROOT / "tools/hooks/agent_command.py"
EDIT = ROOT / "tools/hooks/agent_edit.py"


def run(hook, event, root, env=None):
    return subprocess.run([sys.executable, "-B", str(hook), "--root", str(root)],
                          input=json.dumps(event), capture_output=True, text=True,
                          env={**os.environ, **(env or {})})


class Repo(unittest.TestCase):
    def setUp(self):
        self.dir = pathlib.Path(tempfile.mkdtemp()).resolve()
        self.repo = self.dir / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "claude/work", str(self.repo)], check=True)

    def tearDown(self):
        shutil.rmtree(self.dir)


class Command(Repo):
    def judged(self, command, branch=None):
        env = {"MINIDAQ_SESSION_BRANCH": branch} if branch else {"MINIDAQ_SESSION_BRANCH": ""}
        r = run(COMMAND, {"tool_name": "Bash", "tool_input": {"command": command}}, self.repo, env)
        self.assertIn(r.returncode, (0, 2), r.stderr)
        return r.returncode, r.stderr

    def assertAllowed(self, command, **kw):
        code, err = self.judged(command, **kw)
        self.assertEqual(code, 0, f"{command!r} refused: {err}")

    def assertRefused(self, command, rule, **kw):
        code, err = self.judged(command, **kw)
        self.assertEqual(code, 2, f"{command!r} allowed")
        self.assertIn(rule, err)

    def test_writes_inside_the_repository_and_the_temporary_dirs_are_allowed(self):

        # REQ: SRS-AI-008
        for c in ["echo x > build/log.txt", f"echo x > {self.repo}/notes.txt", "cp a b",
                  "mkdir -p /tmp/scratch", "rm -rf /tmp/x", "make 2>/dev/null",
                  f"tee {self.repo}/out.txt < in", "ls -la /etc", "cat /etc/hostname"]:
            self.assertAllowed(c)

    def test_a_write_outside_the_repository_is_refused_with_its_rule(self):

        # REQ: SRS-AI-008
        outside = "/srv/elsewhere.txt"  # judged, never written
        for c in [f"echo x > {outside}", f"echo x >> {outside}", f"cp a {outside}",
                  "mv build /srv/b", "rm -rf /srv", "touch ~/.bashrc",
                  f"ls && tee {outside} < a", f"FOO=1 rm {outside}", "sudo mkdir /srv/d"]:
            self.assertRefused(c, "outside the repository")

    def test_a_machines_writable_directories_come_from_the_environment(self):
        code, err = self.judged("cp out.pdf /srv/shared/out.pdf")
        self.assertEqual(code, 2, err)
        r = run(COMMAND, {"tool_name": "Bash", "tool_input": {"command": "cp out.pdf /srv/shared/out.pdf"}},
                self.repo, {"MINIDAQ_AGENT_WRITABLE": "/opt/x:/srv/shared", "MINIDAQ_SESSION_BRANCH": ""})
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_a_path_that_climbs_out_of_the_repository_is_outside(self):
        climb = "/".join([".."] * len(self.repo.parts))
        self.assertRefused(f"echo x > {self.repo}/{climb}/srv/escaped", "outside the repository")

    def test_pushes_to_the_sessions_branch_and_main_are_allowed(self):

        # REQ: SRS-AI-008
        for c in ["git push origin HEAD", "git push -u origin claude/work",
                  "git push origin HEAD:main", "git push origin HEAD:refs/heads/main",
                  f"git -C {self.repo} push origin claude/work", "git status && git push origin main"]:
            self.assertAllowed(c)

    def test_the_session_branch_comes_from_the_environment_first(self):
        self.assertAllowed("git push origin feature/x", branch="feature/x")
        self.assertRefused("git push origin claude/work", "only the session's branch",
                           branch="feature/x")

    def test_a_push_to_another_branch_is_refused(self):

        # REQ: SRS-AI-008
        for c in ["git push origin release/2.0", "git push origin HEAD:release/2.0",
                  "git fetch && git push origin other"]:
            self.assertRefused(c, "only the session's branch")

    def test_a_forced_or_bulk_push_is_refused(self):

        # REQ: SRS-AI-008
        for c, rule in [("git push --force origin main", "forces a push"),
                        ("git push -f origin HEAD", "forces a push"),
                        ("git push origin +HEAD:main", "forces a push"),
                        ("git push --tags origin", "tags.txt"),
                        ("git push --all origin", "every branch"),
                        ("git push origin --delete claude/work", "deletes")]:
            self.assertRefused(c, rule)

    def test_a_delete_by_empty_source_or_a_force_among_short_options_is_refused(self):
        # Found by the review of 2.2.0: both were allowed.
        # REQ: SRS-AI-008
        for c, rule in [("git push origin :main", "deletes"),
                        ("git push origin :claude/work", "deletes"),
                        ("git push -fu origin main", "forces a push"),
                        ("git push -uf origin claude/work", "forces a push"),
                        ("git push -ud origin claude/work", "deletes")]:
            self.assertRefused(c, rule, branch="claude/work")
        self.assertAllowed("git push -u origin claude/work", branch="claude/work")

    def test_other_tools_and_bad_input_are_allowed(self):
        r = run(COMMAND, {"tool_name": "Read", "tool_input": {"file_path": "/etc/x"}}, self.repo)
        self.assertEqual(r.returncode, 0)
        r = subprocess.run([sys.executable, "-B", str(COMMAND), "--root", str(self.repo)],
                           input="not json", capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)


@unittest.skipUnless(shutil.which("clang-format-18") or shutil.which("clang-format"),
                     "clang-format is not installed")
class Edit(Repo):
    UGLY = "int  f( int x ){return x+1;}\n"

    def setUp(self):
        super().setUp()
        shutil.copy(ROOT / ".clang-format", self.repo / ".clang-format")

    def edited(self, name, text, path=None):
        f = self.repo / name
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text)
        r = run(EDIT, {"tool_name": "Edit", "tool_input": {"file_path": str(path or f)}}, self.repo)
        return r, f.read_text()

    def test_an_edited_cpp_file_is_formatted(self):

        # REQ: SRS-AI-009
        r, text = self.edited("src/a.cpp", self.UGLY)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotEqual(text, self.UGLY)
        self.assertIn("return x + 1;", text)

    def test_a_relative_path_is_read_from_the_repository(self):
        r, text = self.edited("src/b.hpp", self.UGLY, path="src/b.hpp")
        self.assertIn("return x + 1;", text)

    def test_other_files_are_left_as_they_are(self):

        # REQ: SRS-AI-009
        for name in ["notes.md", "tool.py", "data.json"]:
            r, text = self.edited(name, self.UGLY)
            self.assertEqual((r.returncode, text), (0, self.UGLY), name)

    def committed(self, name, text):
        f = self.repo / name
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text)
        subprocess.run(["git", "add", name], cwd=self.repo, check=True)
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid",
                        "commit", "-q", "-m", "old", "--no-verify"], cwd=self.repo, check=True)

    OLD = "int  f( int x ){return x+1;}\nint  g( int y ){return y+1;}\nint  h( int z ){return z+1;}\n"

    def test_an_edit_of_one_line_in_an_unformatted_file_changes_that_line_only(self):

        # REQ: SRS-AI-009
        self.committed("src/old.cpp", self.OLD)
        edit = self.OLD.replace("return y+1;", "return y+2;")
        r, text = self.edited("src/old.cpp", edit)
        self.assertEqual(r.returncode, 0, r.stderr)
        before, after = self.OLD.splitlines(), text.splitlines()
        self.assertEqual(after[0], before[0])
        self.assertEqual(after[-1], before[-1])
        self.assertNotIn("int  g( int y ){return y+2;}", after)
        self.assertIn("return y + 2;", text)
        self.assertEqual(text.count("return x+1;") + text.count("return z+1;"), 2)

    def test_a_tracked_file_without_a_change_is_left_as_it_is(self):
        self.committed("src/same.cpp", self.OLD)
        r, text = self.edited("src/same.cpp", self.OLD)
        self.assertEqual((r.returncode, text), (0, self.OLD))

    def test_a_cpp_file_outside_the_repository_is_left_as_it_is(self):
        f = self.dir / "outside.cpp"
        f.write_text(self.UGLY)
        r = run(EDIT, {"tool_name": "Write", "tool_input": {"file_path": str(f)}}, self.repo)
        self.assertEqual((r.returncode, f.read_text()), (0, self.UGLY))


if __name__ == "__main__":
    unittest.main()
