# Exercise 17.5 (H): Secure defaults for IPv4 and IPv6

**Goal.** The control server decides at start-up whether its address and its configuration are
safe: no tokens without an explicit `--no-auth`, and beyond loopback both tokens and TLS
(SRS-SEC-005). MiniDAQ supports only IPv4 so far. Write the check for IPv4 and IPv6, where
"loopback" has more spellings than `127.0.0.1`.

**Time.** 2 hours.

**Starter.** `starter/bind_check.cpp` recognizes loopback by its text, accepts `localhost`, and
lets TLS stand in for authentication beyond loopback.

**Acceptance** (`tests/test_bind_check.cpp`, run as `ch17/e5_secure_bind/<variant>/...`):
- `is_loopback()` is true for all of `127.0.0.0/8`, for `::1` in any spelling, and for
  IPv4-mapped loopback (`::ffff:127.0.0.1`); false for the wildcards `0.0.0.0` and `::`, for
  host names, for text with spaces or a NUL byte, and for anything that is not exactly a
  numeric address.
- `check_bind()` refuses a non-numeric address with a message that says so, refuses a
  configuration without tokens unless authentication is turned off explicitly, and beyond
  loopback requires tokens and TLS and refuses `--no-auth`.

Then answer in `NOTES.md`: why is accepting `localhost` a defect, when it resolves to
`127.0.0.1` on every machine you have seen?

**Hints.** Let `inet_pton` decide what an address is; it needs a NUL-terminated string, and a
`string_view` may contain a NUL. Compare IPv6 addresses as 16 bytes, never as text.
