# 0014. Control API authentication with bearer tokens and roles, over TLS 1.3

Date: 2026-10-25
Status: Accepted

## Context

Until Chapter 17 any process that could connect to the control port could stop a scan or
change its settings (hazard H-08, preliminary hazard HZ-4). ADR 0003 left authentication and
encryption for later and kept the server on loopback, which protects against the network but
not against other users of the acquisition PC, and makes remote consoles impossible. The threat
model ([threat-model.md](../regulatory/security/threat-model.md)) asks for: authentication of
every client before any command that changes the acquisition; a read-only role for dashboards;
confidentiality and integrity on the network; and defaults that cannot expose the port by
mistake. The control plane is low-rate, so the cost of cryptography does not matter; what
matters is how much new code and SOUP it brings, and how easily it is misconfigured.

## Options

1. **Mutual TLS.** Every client has a certificate; the server checks it against a CA, and the
   certificate's subject is the identity. Strong and standard, but every client needs a key
   pair and a certificate, issued and renewed by a CA that the site must run, and a role must
   be mapped from a certificate field.
2. **Bearer tokens over TLS.** The server has a certificate; clients send a random token in an
   `auth` command after the handshake. Tokens are issued by writing a hash into a file. A token
   can be stolen and replayed, so it must never cross the network in clear and must be stored
   with care.
3. **A Unix domain socket with peer credentials.** The kernel tells the server the client's
   user id (`SO_PEERCRED`), and file permissions decide who may connect. No secrets at all,
   but local only: a remote console would need a second mechanism.
4. **SSH port forwarding.** Keep the server on loopback and let the site's SSH provide
   authentication and encryption. No new code, but every local user is still trusted, and
   whether the port is protected depends on a configuration outside MiniDAQ.

## Decision

Option 2, with OpenSSL 3 for TLS and for the hashes and the random generator (new SOUP, change
request CR-0004):

- **Tokens.** 32 bytes from `RAND_bytes`, written as `mdq_` and 64 hex digits. The server's
  token file holds `{"name", "role", "sha256"}` entries, never tokens; `TokenStore` refuses a
  file that is a symbolic link, belongs to another user or is writable by others, and compares
  a token's hash with every entry with `CRYPTO_memcmp`. A token is sent once per connection,
  in `{"cmd": "auth", "token": ...}`; an unknown token closes the connection and is recorded in
  the audit trail, without the token. `minidaq_ctl new-token NAME ROLE` makes a token and
  prints the line for the token file.
- **Roles.** `observer` may use `status`; `operator` may use every command. `required_role()`
  gives a command it does not know the operator role, so a new command is protected by
  default. The error codes `unauthenticated` and `forbidden` are added.
- **TLS.** Version 1.3 only, no session resumption. The client verifies the server's
  certificate against a CA file and the host name or IP address it connected to, and only
  then sends its token. Client certificates are not used.
- **Secure defaults.** Without a token file the server makes a start-up operator token and
  writes it, mode 0600 in a directory of mode 0700, where `minidaq_ctl` of the same user finds
  it; turning authentication off (`--no-auth`) is allowed only on loopback; binding outside
  `127.0.0.0/8` requires TLS and tokens; a connection that has not finished the handshake and
  authenticated within 10 s is closed.
- **API 2.0.** A client of API 1.x would get `unauthenticated` for every command, so the major
  version changes: the server refuses 1.x requests with `unsupported_api`, and `hello`
  reports `"auth": "token"` or `"none"`.
- **Layers.** `access` and `tls` are adapters in `minidaq_control`; OpenSSL is linked
  privately and no OpenSSL header appears in MiniDAQ's public headers. `handle_request` stays
  transport-independent: it receives a `Session` that holds the client's identity.

Requirements SRS-SEC-001 to SRS-SEC-009; risk controls RC-21 to RC-24 of H-08.

## Consequences

### Positive

- Controlling a scan needs an operator token, and a dashboard's token cannot stop one. The
  residual risk of H-08 is an attacker who already runs as the operator.
- A remote console is possible, and safe by construction: the server refuses to listen on the
  network without TLS and tokens.
- Local use keeps working without configuration, through the start-up token file.
- OpenSSL is the TLS library of the platform, updated by the operating system's security
  updates; MiniDAQ does not pin or build it.

### Negative

- A new SOUP item, and the most security-critical one: its vulnerabilities must be followed
  (threat-model.md, section 8), and its version is the platform's, so it is recorded at build
  time rather than pinned.
- Bearer tokens can be copied: protecting the token files is the site's task (RC-25).
- Breaking change: every client must move to API 2.0 and authenticate; scripts written for
  1.x fail with `unsupported_api` until they do.
- On loopback without TLS a token can be collected by a process of another user that binds the
  port first (threat-model.md, section 7); a Unix domain socket (option 3) would close that gap
  and may be added for local clients.
- The certificate and the CA are the site's to issue and renew; an expired certificate stops
  remote control until it is replaced.
