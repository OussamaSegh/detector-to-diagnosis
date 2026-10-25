# Exercise 17.5: notes on the solution

The starter's three mistakes:

- **Text instead of addresses.** `starts_with("127.")` accepts `127.0.0.1.nip.io`, a name that
  can resolve to any address. Comparing with `"::1"` misses `0:0:0:0:0:0:0:1`, the same
  address. Parsing with `inet_pton` and comparing bytes removes both classes of error.
- **Names.** `localhost` is a name, and a name resolves to what the resolver says: `/etc/hosts`,
  which an administrator or a container image can change, and on some systems a DNS query. A
  security check must decide on the address the server will bind, not on a name that may change
  between the check and the bind. The server binds numeric addresses only.
- **TLS as authentication.** TLS without tokens is an encrypted channel to anyone; it protects
  the commands from eavesdroppers, not the scan from strangers. Beyond loopback both are needed,
  and `--no-auth` is refused there.

The IPv4-mapped form (`::ffff:127.0.0.1`) is what an IPv6 socket that accepts IPv4 connections
shows for a local IPv4 client; treating it as loopback is right, treating `::ffff:10.0.0.1` as
loopback would not be. The wildcards `0.0.0.0` and `::` are not loopback: they are every
interface, including the loopback one.

A NUL byte in the middle of the input is the classic difference between a `string_view` and the
C string that `inet_pton` sees: `"127.0.0.1\0garbage"` would be read as `127.0.0.1` if it were
passed with `.data()`. The solution copies to a `std::string` and refuses an embedded NUL.
