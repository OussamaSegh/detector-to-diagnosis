# Exercise 17.3: the advisories behind tests/scan.json

The identifiers are made up; each advisory is modeled on a real kind of defect.

- **EX-2026-0101** (OpenSSL, high). A TLS 1.3 server that receives a crafted ClientHello can be
  made to allocate memory without limit, before any authentication. Fixed in the next package.
- **EX-2026-0102** (OpenSSL, high). Out-of-bounds read when a DTLS 1.2 server processes a
  fragmented handshake message. Fixed in the next package.
- **EX-2026-0103** (OpenSSL, medium). A client that verifies a server certificate's host name
  can crash on a certificate with a crafted subject alternative name. Fixed in the next package.
- **EX-2026-0104** (OpenSSL, low). Timing side channel in SM2 signature generation on some ARM
  processors. No fix planned by the distribution.
- **EX-2026-0105** (nlohmann/json, critical). Use after free in the SAX parser when the handler
  throws an exception. No release with a fix yet.
- **EX-2026-0106** (GoogleTest, medium). A death test can leave a child process running when its
  parent is killed. Fixed in 1.16.0.

What MiniDAQ uses is in `docs/regulatory/soup-list.md` and `docs/regulatory/security/threat-model.md`
of the repository: TLS 1.3 only, server and client; no DTLS; P-256 or the site's certificates on
x86-64 PCs; nlohmann/json through `json::parse` of strings, never the SAX interface; GoogleTest
only in tests, which are not shipped.
