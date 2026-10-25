# CR-0004: Authentication, roles and TLS for the control API (API 2.0), with OpenSSL as SOUP

| Field | Value |
|---|---|
| Status | implemented |
| Requested | 2026-10-25, by the software lead |
| Source | problem report MDQ-PR-008; hazard H-08 (Chapter 15); threat model (Chapter 17) |
| Decision | approved, 2026-10-25, software lead and risk manager |
| Commits | ff0f415 |

## Description

The control server requires every client to authenticate with a bearer token before any command
except `hello` and `auth`, and authorizes each command by the token's role (observer or
operator). Optionally, and necessarily for any address outside loopback, it serves TLS 1.3 only,
and `minidaq_ctl` verifies the server's certificate before it sends its token. Without a token
file the server makes a start-up token that only its user can read. The control API becomes
version 2.0. OpenSSL 3, the platform's library, is used for TLS, SHA-256 and random numbers.
Design: ADR 0014.

## Reason

Any process that can reach the control port can stop a scan or change its settings (MDQ-PR-008,
hazard H-08, S2/P4, not acceptable). H-08 is the only open hazard of the risk file, and the
software may not be released for use beyond a test bench while it is open (MDQ-PR-008's
decision). Writing TLS and the cryptographic primitives ourselves would be far riskier than
using a maintained library.

## Impact analysis

### Requirements

New: SRS-SEC-001 to SRS-SEC-009 (SRS section 2.13, version 4). Changed in effect, not in text:
SRS-CTL-032, whose audit records now name the token as well as the address. Verification
repeated: SRS-CTL-020 to SRS-CTL-023 and SRS-CTL-032, whose tests now authenticate first.

### Software items and safety class

New item `access` (tokens, roles, the start-up token, the TLS wrapper), class B, because a defect
in it can let an unauthorized party stop a scan (HZ-4). Changed: `protocol` (authentication and
authorization, class B unchanged), `server` (class B unchanged) and `ctl`, reclassified from A to
B: it now holds an operator token and verifies the server, so a defect in it can disclose a
token (HZ-4). `ctl` gets the class B activities from this change on: detailed design in ADR 0014
and the unit tests of `access`, which it uses for everything security-relevant.

### Risk

H-08: new controls RC-21 to RC-25; probability after control P2, residual risk acceptable
(S2/P2), status closed. RC-18 (the audit trail) is unchanged and now names the token. No other
hazard changes: the acquisition threads do not use the new code.

### SOUP

New: OpenSSL 3 (`libssl`, `libcrypto`), taken from the target system and found with
`find_package(OpenSSL 3.0 REQUIRED)`; on the build machine 3.0.13, Ubuntu package
`3.0.13-0ubuntu3.16`. It is linked only into `minidaq_control`, privately, and no OpenSSL header
appears in MiniDAQ's public headers. SOUP list version 4 records its requirements, its known
anomalies and the vulnerability review; the SBOM lists it as a platform component.

### Interfaces and data formats

The control API becomes 2.0, a breaking change: 1.x requests are refused with `unsupported_api`,
because a 1.x client that does not authenticate would get `unauthenticated` for every command.
New command `auth`; new error codes `unauthenticated` and `forbidden`; `hello` reports
`"auth"`. New files: the server's token file (`{"tokens": [...]}`) and the start-up token file.
New options of `minidaq_server` (`--tokens`, `--tls-cert`, `--tls-key`, `--no-auth`) and of
`minidaq_ctl` (`--token-file`, `--tls-ca`, the subcommand `new-token`). The list-mode format and
the configuration schema do not change.

### Documents

ADR 0014 (new) and ADR 0003; the ADR index; SRS version 4; the trace matrix; the risk file
(hazards.json); the threat model (new: threat-model.md, threats.json, dataflow.dot); the SOUP
list version 4; the architecture description (the `access` item, the class of `ctl`);
software-items.json; layers.json; the design-file index; MDQ-PR-008 closed; the known-anomalies
list; the CHANGELOG; the book's chapters that show `minidaq_ctl` sessions.

### Regulatory

The intended use does not change. The change adds security controls to an interface and closes a
hazard; for a product on the market, a change to cybersecurity controls is assessed for its
significance and for the FDA's cybersecurity expectations (assumption: confirm with regulatory
affairs).

## Verification

TokenStore.LoadsHashesAndRefusesUnsafeFiles, Secrets.StartupTokenIsPrivate,
ControlServer.CommandsNeedAnAuthenticatedClient, ControlServer.AnUnknownTokenClosesTheConnection,
ControlServer.ObserversMayOnlyReadTheStatus, ControlServer.ClosesConnectionsThatDoNotAuthenticate,
ControlServer.RefusesInsecureConfigurations, ControlServer.ServesOnlyTls13Clients,
TlsStream.ClientVerifiesTheServer, ControlProtocol.AuthenticationInTheProtocolLayer,
ControlServer.AnIntruderCannotStopARunningScan, ControlServer.TheTokenNeverCrossesTheNetworkInClear;
the protocol fuzz target with its authorization property; the tests docs.risk, docs.threats,
docs.trace, docs.soup and architecture.items; all six CI presets and static analysis.

## Decision

Approved by the software lead and the risk manager on 2026-10-25: the change closes the only open
hazard, uses the platform's maintained TLS library instead of new code, and the break of API 1.x
is the price of not letting unauthenticated clients appear to work.
