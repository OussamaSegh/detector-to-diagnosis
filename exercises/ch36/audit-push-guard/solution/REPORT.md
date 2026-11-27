# Audit report: the agent's push guard (Exercise 36.5)

Not mergeable. Two of git's own forms get through: the guard knows git's options, not git's
syntax. Both are MiniDAQ's own defects, in its agent's command hook, found by the independent
review of release 2.2.0 (MDQ-PR-100).

## Defect 1: short options given together are not seen (MDQ-PR-100)

The table matches whole words. Git, like most command-line programs, reads `-fu` as `-f -u`,
so `git push -fu origin <branch>` forces a push, and the guard compares `-fu` with its table
and finds nothing. `-uf`, `-vf` and `-du` the same.

- *Test:* `test_short_options_given_together_are_each_an_option`.
- *Effect:* a forced push of the session's branch or of `main`: published history rewritten,
  which SDP section 5 forbids without a change request.
- *Correction:* a word of two or more letters after one `-` is several options: refuse it if
  any of its letters is a refused short option.

## Defect 2: a refspec with an empty source deletes, and is allowed (MDQ-PR-100)

`git push origin :main` pushes nothing to `main`, which deletes it. The guard takes the
destination, `main`, finds it allowed, and lets the command through. The specification says
"deletes a remote branch, in any of the forms git accepts"; the agent's table has only
`--delete` and `-d`.

- *Test:* `test_every_form_of_delete_is_refused`.
- *Effect:* the deletion of `main` on the remote by an agent that was only allowed to push to
  it.
- *Correction:* a refspec that starts with `:` is a delete.

## Verdict

Request changes. "Every option is in the table" is the agent's claim, and the specification
asked for every form git accepts: a guard against a program must be tested against that
program's grammar, which here is one page of `git help push`. A guard is also not a sandbox:
`eval` and a command built at run time get past any parser of the command line, which is why
the push rules live on the server too (branch protection).
