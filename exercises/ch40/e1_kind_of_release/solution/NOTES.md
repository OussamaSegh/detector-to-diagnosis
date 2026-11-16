# Exercise 40.1: notes

The starter fails five of the seven tests: it calls a fix that changes a format or breaks a
client a patch, it looks at the first change of a release only, and `1.3.2` plus a minor release
gives it `1.4.2`. The plain cases pass, which is why the rule looks easy.

Design choices:

- Ask what the change does, not why it was made. The reason (a problem report) says nothing
  about what a site must do to install it; the effects (a new field, a renamed one) do.
- Check the largest effect first: breaking, then adding, then fixing. The starter's order,
  fixing first, is the bug the tests are written to catch.
- One release takes the largest kind of its changes: a single compatible addition makes the
  whole release minor, which is why fixes for an old line are kept apart from new work (a
  maintenance branch).
- `next_version` refuses what is not a released version: the next version of a development
  version is decided when it is released, not computed.
