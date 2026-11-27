# The session, condensed

This session is reconstructed for the book. The change was written to hold defects that
MiniDAQ really had, and the dialogue is shortened to the steps that matter. It works from this
record alone: you do not need an agent to do the exercise.

**Person:** Implement `change/SPEC.md` in `push_guard.py`.

**Agent:** I'll keep a table of the refused options with their reasons: `--all`, `--mirror`,
`--tags`, `--delete` and `-d`, `--force` and `-f`, and `--force-with-lease`, matched with or
without an `=value`. Then each refspec: a leading `+` forces, and the destination, the part
after the colon if there is one, must be the session's branch or `main`.

*(edits `push_guard.py`: the diff is `change/agent.patch`)*

**Agent:** Tests:

```text
test_own_branch_allowed .............. ok
test_main_allowed .................... ok
test_other_branch_refused ............ ok
test_force_refused ................... ok
test_force_with_lease_refused ........ ok
test_delete_refused .................. ok
test_plus_refspec_refused ............ ok
test_all_tags_mirror_refused ......... ok
Ran 8 tests in 0.002s  OK
```

Every forcing and deleting option of `git push` is in the table, and the refspec handles the
`+` form, so the guard covers all of them.

**Person:** I'll review it.
