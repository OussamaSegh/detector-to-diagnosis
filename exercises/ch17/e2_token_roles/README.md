# Exercise 17.2 (M): A token store that fails closed

**Goal.** Write the core of `minidaq/control/access.cpp` yourself: the role each command needs
and a store of token digests, without OpenSSL. The digest and the comparison are passed in, so
the tests can count how often the comparison runs.

**Time.** 90 minutes.

**Starter.** `starter/access.cpp` works for the happy path and has the four classic defects of
access control code, each marked TODO: it fails open for an unknown command, it maps an unknown
role to a real one, it accepts malformed and duplicate entries, and it compares with `==` and
returns at the first match.

**Acceptance** (`tests/test_access.cpp`, run as `ch17/e2_token_roles/<variant>/...`):
- `required_role()` gives the operator role to every command but `hello`, `auth` and `status`,
  including commands it has never seen and near misses such as `"STATUS"`.
- `TokenStore::parse()` refuses an empty file, an unknown or misspelled role, a digest that is
  not 64 lowercase hex digits, extra fields, and a name or digest used twice, with the line
  number.
- `check()` calls the comparison once per entry for every token, matching or not, and refuses
  anything that is not `mdq_` and 64 hex digits before hashing it.

Then answer in `NOTES.md`: the tests count comparisons instead of measuring time. Why is that
the better test, and what does it not prove?

**Hints.** "Fail closed" means the default branch is the strictest one. A loop that returns
early tells an attacker, through time, where in the list the match was.
