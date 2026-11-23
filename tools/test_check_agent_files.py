#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Tests of tools/check_agent_files.py (roadmap 2.2.0, Theme P2; CR-0036; TL-52): a scratch
repository with one agent file of each kind that passes, and each kind of defect added to it."""
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import check_agent_files as caf  # noqa: E402

AGENT = """---
name: reviewer
description: Reviews a change's traceability. Reports; does not edit.
tools: Read, Grep, Glob
version: 2
owner: software lead
---

Read `docs/srs.md` and run nothing. The tests are listed by `ctest -R docs.trace`.

## Document history

| Version | Change |
|---|---|
| 1 | First version. |
| 2 | Names the SRS. |
"""
SKILL = """---
name: checks
description: Runs the checks.
allowed-tools: Read Bash(tools/release_checks.sh *)
version: 1
owner: software lead
---

1. Run `tools/release_checks.sh OUT 600 resume`.
2. Read `exercises/chNN/` for nothing in particular.

## Document history

| Version | Change |
|---|---|
| 1 | First version. |
"""
CONTEXT = """# Context

Version 1 (2.2.0-dev). Owner: software lead.

Build with `cmake --preset debug`; the requirements are in `docs/srs.md`.

```
python3 tools/release_checks.sh
```

## Document history

| Version | Change |
|---|---|
| 1 | First version. |
"""
SETTINGS = {
    "permissions": {
        "allow": ["Bash(ctest *)", "Bash(python3 tools/*)"],
        "deny": ["Read(./.env)", "Read(./.env.*)", "Bash(git push --force *)",
                 "Bash(git push -f *)", "Bash(sudo *)", "Bash(curl *)", "Bash(wget *)",
                 "Bash(pip install *)"],
        "ask": ["Bash(git push *)"],
    },
    "hooks": {
        "PreToolUse": [{"matcher": "Bash", "hooks": [
            {"type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR\"/tools/hooks/agent_command.py"}]}],
        "PostToolUse": [{"matcher": "Edit|Write", "hooks": [
            {"type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR\"/tools/hooks/agent_edit.py"}]}],
    },
}
REGISTER = """# Agent files

Version 1. Owner: software lead.

| File | Kind | Version | Owner |
|---|---|---|---|
| `CLAUDE.md` | context | 1 | software lead |
| `.claude/settings.json` | settings | 1 | software lead |
| `.claude/agents/reviewer.md` | agent | 2 | software lead |
| `.claude/skills/checks/SKILL.md` | skill | 1 | software lead |

## Document history

| Version | Change |
|---|---|
| 1 | First version. |
"""


class AgentFiles(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        files = {
            "docs/srs.md": "srs\n", "tools/release_checks.sh": "#!/bin/sh\n",
            "tools/hooks/agent_command.py": "", "tools/hooks/agent_edit.py": "",
            "exercises/ch01/e1/README.md": "", "CMakeLists.txt": "add_test(NAME docs.trace COMMAND x)\n",
            "CLAUDE.md": CONTEXT, ".claude/README.md": REGISTER,
            ".claude/settings.json": json.dumps(SETTINGS, indent=2),
            ".claude/agents/reviewer.md": AGENT, ".claude/skills/checks/SKILL.md": SKILL,
        }
        for rel, text in files.items():
            (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.root / rel).write_text(text)
        self.git("init", "-q")
        self.git("add", ".")
        self.git("commit", "-q", "-m", "base")

    def tearDown(self):
        shutil.rmtree(self.root)

    def git(self, *args):
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid",
                        "-C", str(self.root), *args], check=True, capture_output=True)

    def edit(self, rel, old, new):
        f = self.root / rel
        text = f.read_text()
        self.assertIn(old, text)
        f.write_text(text.replace(old, new, 1))

    def problems(self, since=None):
        return caf.check(self.root, since)[1]

    def assertFound(self, fragment, since=None):
        errors = self.problems(since)
        self.assertTrue(any(fragment in e for e in errors), f"{fragment!r} not in {errors}")

    def test_good_files_pass(self):

        # REQ: SRS-AI-007
        found, errors = caf.check(self.root)
        self.assertEqual(errors, [])
        self.assertEqual(sorted(found.values()), ["agent", "context", "register", "settings", "skill"])

    def test_a_required_field_missing_is_reported(self):

        # REQ: SRS-AI-007
        self.edit(".claude/agents/reviewer.md", "owner: software lead\n", "")
        self.assertFound("frontmatter lacks 'owner'")

    def test_a_file_without_frontmatter_is_reported(self):
        self.edit(".claude/skills/checks/SKILL.md", "---\nname", "name")
        self.assertFound("no frontmatter")

    def test_a_name_other_than_the_files_is_reported(self):
        self.edit(".claude/agents/reviewer.md", "name: reviewer", "name: checker")
        self.assertFound("is not the file's name 'reviewer'")

    def test_a_version_that_the_history_does_not_end_with_is_reported(self):
        self.edit(".claude/agents/reviewer.md", "version: 2", "version: 3")
        self.assertFound("history table ends with 2")

    def test_a_path_that_does_not_exist_is_reported(self):

        # REQ: SRS-AI-007
        self.edit("CLAUDE.md", "`docs/srs.md`", "`docs/sds.md`")
        self.assertFound("CLAUDE.md:5: docs/sds.md does not exist")

    def test_a_path_in_a_fenced_block_is_checked(self):
        self.edit("CLAUDE.md", "tools/release_checks.sh", "tools/release_check.sh")
        self.assertFound("tools/release_check.sh does not exist")

    def test_a_pattern_that_matches_nothing_is_reported(self):
        self.edit(".claude/skills/checks/SKILL.md", "exercises/chNN/", "exercises/chNN/eNN_x/")
        self.assertFound("nothing matches exercises/chNN/eNN_x")

    def test_a_test_that_is_not_defined_is_reported(self):

        # REQ: SRS-AI-007
        self.edit(".claude/agents/reviewer.md", "ctest -R docs.trace", "ctest -R docs.tracing")
        self.assertFound("no test named docs.tracing")

    def test_a_tool_outside_the_kinds_list_is_reported(self):

        # REQ: SRS-AI-007
        self.edit(".claude/agents/reviewer.md", "tools: Read, Grep, Glob", "tools: Read, Edit, Bash")
        self.assertFound("allows Edit, which a agent may not")
        self.assertFound("allows Bash, which a agent may not")

    def test_a_tool_list_in_yaml_form_is_read(self):
        self.edit(".claude/agents/reviewer.md", "tools: Read, Grep, Glob",
                  "tools:\n  - Read\n  - Write")
        self.assertFound("allows Write")

    def test_a_skill_may_run_only_its_listed_commands(self):
        self.edit(".claude/skills/checks/SKILL.md", "Bash(tools/release_checks.sh *)",
                  "Bash(tools/release_checks.sh *) Bash(git push *)")
        self.assertFound("allows Bash(git push *), which a skill may not")

    def test_a_subagent_may_not_change_its_permission_mode(self):
        self.edit(".claude/agents/reviewer.md", "owner: software lead",
                  "owner: software lead\npermissionMode: bypassPermissions")
        self.assertFound("sets permissionMode")

    def test_a_broad_permission_is_reported(self):

        # REQ: SRS-AI-007
        for rule in ["Bash", "Bash(*)", "Bash(sudo apt *)", "Bash(git push *)", "WebFetch",
                     "Write(/etc/*)", "Read(~/.ssh/*)", "Bash(pip install x)"]:
            with self.subTest(rule=rule):
                data = json.loads(json.dumps(SETTINGS))
                data["permissions"]["allow"].append(rule)
                (self.root / ".claude/settings.json").write_text(json.dumps(data))
                self.assertFound(f"allows {rule}, which the policy forbids")

    def test_a_missing_deny_rule_and_a_wide_mode_are_reported(self):
        data = json.loads(json.dumps(SETTINGS))
        data["permissions"]["deny"].remove("Bash(curl *)")
        data["permissions"]["defaultMode"] = "bypassPermissions"
        (self.root / ".claude/settings.json").write_text(json.dumps(data))
        self.assertFound("does not deny Bash(curl *)")
        self.assertFound("default mode bypassPermissions")

    def test_a_missing_hook_or_a_hook_script_that_does_not_exist_is_reported(self):
        data = json.loads(json.dumps(SETTINGS))
        del data["hooks"]["PostToolUse"]
        data["hooks"]["PreToolUse"][0]["hooks"][0]["command"] = "python3 tools/hooks/gone.py"
        (self.root / ".claude/settings.json").write_text(json.dumps(data))
        self.assertFound("no PostToolUse hook runs tools/hooks/agent_edit.py")
        self.assertFound("tools/hooks/gone.py, which does not exist")

    def test_secrets_addresses_and_absolute_paths_are_reported(self):

        # REQ: SRS-AI-007
        address = "someone" + "@" + "company-name.ch"
        key = "ghp_" + "a1" * 15
        for line, what in [(f"Mail {address}.", "an e-mail address"),
                           (f"Use {key} to push.", "a GitHub token"),
                           ("-----BEGIN RSA " + "PRIVATE KEY-----", "a private key"),
                           ("password = hunter2hunter2", "a credential"),
                           ("Files are in /home/someone/repo.", "/home/someone/repo"),
                           ("Or C:\\Users\\someone.", "an absolute path")]:
            with self.subTest(what=what):
                self.edit("CLAUDE.md", "## Document history", f"{line}\n\n## Document history")
                self.assertFound(what)
                self.edit("CLAUDE.md", f"{line}\n\n", "")

    def test_placeholders_and_noreply_addresses_are_not_reported(self):
        self.edit("CLAUDE.md", "## Document history",
                  "Commit as t@example.invalid or a noreply@" + "example.org address; scratch in /tmp.\n\n"
                  "## Document history")
        self.assertEqual(self.problems(), [])

    def test_the_register_lists_every_file_at_its_version(self):
        self.edit(".claude/README.md", "| `.claude/skills/checks/SKILL.md` | skill | 1 | software lead |\n", "")
        self.assertFound("does not list .claude/skills/checks/SKILL.md")
        self.edit(".claude/README.md", "reviewer.md` | agent | 2", "reviewer.md` | agent | 1")
        self.assertFound("at version 1, the file is at 2")

    def test_a_register_row_for_a_file_that_does_not_exist_is_reported(self):
        (self.root / ".claude/agents/reviewer.md").unlink()
        self.assertFound("lists .claude/agents/reviewer.md, which does not exist")

    def test_a_changed_file_needs_a_new_version(self):
        data = json.loads(json.dumps(SETTINGS))
        data["permissions"]["allow"].append("Bash(cmake *)")
        (self.root / ".claude/settings.json").write_text(json.dumps(data, indent=2))
        self.assertFound("changed since HEAD and still at version 1", since="HEAD")
        self.edit(".claude/README.md", "settings.json` | settings | 1", "settings.json` | settings | 2")
        self.assertEqual(self.problems(since="HEAD"), [])

    def test_frontmatter_reads_folded_values_and_lists(self):
        fm = caf.frontmatter("---\nname: x\ndescription: >\n  two\n  lines\ntools:\n  - Read\n---\nbody")
        self.assertEqual(fm, {"name": "x", "description": "two lines", "tools": ["Read"]})
        self.assertIsNone(caf.frontmatter("---\nname: x\n"))

    def test_no_agent_files_is_no_problem(self):
        shutil.rmtree(self.root / ".claude")
        (self.root / "CLAUDE.md").unlink()
        self.assertEqual(self.problems(), [])


if __name__ == "__main__":
    unittest.main()
