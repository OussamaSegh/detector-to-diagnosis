# Exercise 32.4: notes on the solution

## 1. What the starter accepted

Everything. The tampered archive changes `value * gain` into `value * gain + 1` in `scale.hpp`;
without `URL_HASH`, FetchContent downloads and extracts whatever is at the URL, and the program
would have printed `scaled 11` once the warning was dealt with. Nothing in the configure or the
build output says the dependency changed. With the hash, the download step stops before
extracting: "SHA256 hash of ... does not match expected value", with the expected and the actual
hash.

A `GIT_TAG v1.0` pins a name. Anyone with push rights to the upstream repository can move a tag
to another commit (`git tag -f`, `git push --force --tags`), and a mirror or a compromised
account can serve a different commit under it. A commit hash, like an archive hash, names the
bytes; only that kind of pin identifies the version the SOUP list reviewed.

## 2. SYSTEM

Before: tinylib's directory reaches the compiler as `-I.../_deps/tinylib-src/include`; after:
as `-isystem .../_deps/tinylib-src/include`. GCC and Clang do not report warnings in headers
found through a system include directory, so `-Wconversion` stays silent inside `scale.hpp` while
it still applies to every line of `main.cpp` (the third test). The narrowing in tinylib is still
there: it is that library's behavior, reviewed when the item was added to the SOUP list, with
its known anomalies, and watched by the vulnerability scan of the SBOM. Our warnings are a check
of our code against our coding standard; SOUP is accepted on evidence of a different kind.

A pragma around the include would also have silenced it, but in every file that includes the
header, and it would hide a warning in our own code on the same line. Dropping `-Werror` or
`-Wconversion` passes the build and fails the third test.

## 3. Trust on first use

The hash pins whatever bytes it was computed from. If the archive had already been replaced when
it was first downloaded, the pin keeps the replaced one, reproducibly. Before recording a new
pin, compare it with what the upstream publishes independently of the download: the checksum on
its release page, or better its signature (a signed tag or a detached signature on the
archive, checked against a key obtained separately), and record in the SOUP entry where the
hash was checked. A second person reviewing the change to `cmake/Dependencies.cmake` checks the
same, which is why a change of pin is a change request and not a routine commit.
