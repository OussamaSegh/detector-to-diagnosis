# SPDX-License-Identifier: MIT
"""Exercise 36.5 (A): tests of the agent's push guard, from git push's own syntax: options,
short options together, and the forms of a refspec."""
import unittest

OWN = "claude/feature-x"


class Audit(unittest.TestCase):
    subject = None  # set by tests/test_audit.py

    def allowed(self, command):
        self.assertEqual(self.subject.refusals(command, OWN), [], command)

    def refused(self, command):
        self.assertTrue(self.subject.refusals(command, OWN), command)

    def test_pushes_of_the_sessions_branch_and_main_are_allowed(self):
        self.allowed(f"git push -u origin {OWN}")
        self.allowed(f"git push origin HEAD:{OWN}")
        self.allowed("git push origin main")
        self.allowed(f"git -C repo push origin {OWN}")
        self.allowed("git status && git log -1")

    def test_a_push_to_another_branch_is_refused(self):
        self.refused("git push origin release/2.0")
        self.refused(f"git push origin {OWN}:release/2.0")

    def test_each_forcing_option_is_refused(self):
        for opt in ("--force", "-f", "--force-with-lease", "--force-with-lease=main:abc"):
            with self.subTest(opt=opt):
                self.refused(f"git push {opt} origin {OWN}")

    def test_short_options_given_together_are_each_an_option(self):
        for opt in ("-fu", "-uf", "-vf", "-du"):
            with self.subTest(opt=opt):
                self.refused(f"git push {opt} origin {OWN}")
        self.allowed(f"git push -uv origin {OWN}")

    def test_a_refspec_with_a_plus_forces(self):
        self.refused(f"git push origin +{OWN}")

    def test_every_form_of_delete_is_refused(self):
        self.refused("git push --delete origin main")
        self.refused("git push -d origin main")
        self.refused("git push origin :main")
        self.refused(f"git push origin :{OWN}")

    def test_pushes_of_everything_are_refused(self):
        for opt in ("--all", "--mirror", "--tags"):
            with self.subTest(opt=opt):
                self.refused(f"git push {opt} origin")

    def test_a_push_hidden_after_another_command_is_judged(self):
        self.refused(f"git add -A && git commit -m x && git push -fu origin {OWN}")
