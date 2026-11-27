# Task given to the agent

Implement `refusals(command, own_branch)` in `push_guard.py`, the hook every shell command of
an agent passes before it runs. For each `git push` in the command line (commands may be
joined with `&&`, `||`, `;` or `|`), return a reason to refuse it if it:

- pushes to a branch other than `own_branch` and `main`;
- pushes every branch, ref or tag at once (`--all`, `--mirror`, `--tags`);
- deletes a remote branch, in any of the forms git accepts;
- forces a push, in any of the forms git accepts.

"Any of the forms git accepts" means git's own syntax (`git help push`), not only the long
options. Return an empty list to allow the command. Add tests.
