# Cybersecurity: IEC 81001-5-1 and the FDA {#ch17}

::: box-why
Until this chapter, anyone who could reach MiniDAQ's control port could stop a scan. That was
written down as hazard H-08 in Chapter 15, with the only probability in the risk file that was not
acceptable, and as problem report MDQ-PR-008 since Chapter 6. A scanner is a networked computer in a
hospital, and regulators now treat its security as part of its safety: the FDA can refuse to accept
a submission for a "cyber device" that lacks a security plan and an SBOM, the EU MDR asks for
protection against unauthorized access, and IEC 81001-5-1 extends IEC 62304 with the security
activities. This chapter teaches the security activities of the life cycle from a developer's side:
threat modeling with data flow diagrams, STRIDE and attack trees; turning threats into requirements;
authentication, authorization, TLS and secure defaults in C++ with OpenSSL; testing that the
controls work; and the SBOM, vulnerability scanning, triage and disclosure that keep a released
product secure. MiniDAQ's control API gets tokens, roles and TLS 1.3, and H-08 is closed.
:::

**A day in the life.** A hospital that is evaluating the scanner sends its IT security
questionnaire, together with the output of its network scanner, which was pointed at a demo unit for
an afternoon. One line is highlighted: port 7700 open, plain text, no authentication. The IT
security officer asks four questions. Who can connect to it? What can they do? Where is your SBOM?
How do you tell us about vulnerabilities? You know the answers, and you do not like the first two:
anyone on the acquisition PC, and everything, including stop a running scan. The port is bound to
loopback, so the network scanner reached it only because the demo unit had been reconfigured for a
remote console. By the end of the week you have a threat model that lists who could attack the
control API and how, a change request that adds tokens, roles and TLS, and a server that refuses to
listen on the network without them. The SBOM now lists OpenSSL with the exact package version, and a
CI job checks it against vulnerability databases every night. The questionnaire's answers point at
documents instead of promises, and the next scan of the demo unit finds a port that answers only to
a TLS 1.3 handshake.

## Learning objectives {.unnumbered}

After this chapter you can:

1. Explain how a security risk becomes a safety risk, what IEC 81001-5-1 adds to IEC 62304, and what
   the FDA's premarket cybersecurity guidance, section 524B of the FD&C Act and the EU MDR expect of
   a manufacturer.
2. Threat-model a software system: draw a data flow diagram with trust boundaries, analyze each
   element with STRIDE, and use an attack tree to find what is left once the controls are in place.
3. Turn threats into security requirements and implement the common controls in C++: bearer tokens
   stored as hashes, roles that fail closed, TLS 1.3 with certificate verification, and secure
   defaults.
4. Verify security controls with tests that reproduce the attack, fuzzing with a security property,
   static analysis and independent penetration testing, and link them to the risk file.
5. Produce an SBOM that a scanner can match, triage the findings of a vulnerability scan in VEX
   states, and describe coordinated vulnerability disclosure.

## Prerequisites and estimated time {.unnumbered}

Chapter 6 (the control API and its protocol), Chapter 7 (fuzzing, static analysis and the SBOM),
Chapter 14 (software items and SOUP) and Chapter 15 (the risk file and H-08). The code uses OpenSSL
3; you do not need to know it beforehand. The exercises are in Python and C++. Reading: about 3
hours. Exercises: 7 to 9 hours. Milestone: 4 hours. In the 10-week schedule this chapter is the end
of week 6; if time is short, do Exercises 17.1 to 17.3 and leave the extras.

## Security in the medical device life cycle

### The intuition

Safety asks what happens when the software fails by accident; security asks what happens when
someone makes it fail on purpose. For a medical device the two meet at the same harm. H-08 in
MiniDAQ's risk file is a security threat (an unauthorized party controls the acquisition) whose
consequence is a safety harm (a scan stopped and repeated, with its dose; or a scan acquired with
altered settings, and a quantitation error). That is how a security risk becomes a safety risk: an
attack is one more cause in the sequence of events of a hazard, next to a defect or a hardware
fault.

Two things make the attacker different from a random fault. The probability is not a property of the
software, because an attacker chooses the weakest point and comes back; that is why security risk
assessment rates exploitability (how much skill, access and time an attack needs) rather than
failure rates. And the environment changes after release: a vulnerability that nobody knew about on
release day is found in a library two years later, and the device in the field is suddenly less safe
than the one you verified. Security is therefore not a feature you add once; it is a set of
activities across the life cycle, including after release, and the standards are organized
accordingly.

### IEC 81001-5-1 and its neighbors

IEC 81001-5-1:2021, *Health software and health IT systems safety, effectiveness and security:
Part 5-1: Security: Activities in the product life cycle*, is to security what IEC 62304 is to
software safety. It was derived from IEC 62443-4-1, the secure development standard for industrial
automation, and adapted to health software, and it is written to sit on top of IEC 62304: its
clauses follow the same life cycle (development, maintenance, risk management, configuration
management, problem resolution) and add the security activities to each (verify: the clause
numbering against your copy). In a team that already follows IEC 62304, the standard does not ask
for a second process. It asks for more in the same places:

- **Planning.** The development plan names the security activities, the people and their training,
  and the security risk management process. Section 9 of MiniDAQ's threat model
  (`docs/regulatory/security/threat-model.md`) lists its reviews.
- **Requirements.** Security requirements, derived from a threat model and from the intended
  environment of use, are part of the software requirements. MiniDAQ's are SRS-SEC-001 to 009.
- **Architecture and design.** A defense-in-depth design, with the trust boundaries and the
  interfaces that cross them documented, and secure design principles such as least privilege and
  secure defaults.
- **Implementation and verification.** Secure coding standards, static analysis, and security
  testing: tests of the security requirements, tests for known vulnerabilities, fuzzing, and
  penetration testing by people independent of the developers.
- **Release and maintenance.** Documentation for secure installation and use (what the site must
  do), an SBOM, monitoring of vulnerabilities in the software and its SOUP, and a process to receive
  and handle vulnerability reports.

The standard also asks for a security risk management process that feeds the safety risk management
of ISO 14971. The technical report AAMI TIR57 describes how; in MiniDAQ the link is direct: the
threat model's mitigations are risk controls of H-08, and the threats that rely on the site appear
as information for safety (RC-25).

### The FDA and the EU

The FDA's guidance *Cybersecurity in Medical Devices: Quality System Considerations and Content of
Premarket Submissions* (final in September 2023, updated in 2025; verify: the current revision)
describes what a submission must show: a security risk management report with the threat model, the
security architecture with its views, an SBOM, the testing done and its results, the vulnerabilities
known at submission and their assessment, and the plan for the product's life after release. Since
March 2023, section 524B of the Federal Food, Drug, and Cosmetic Act makes part of this law for a
"cyber device": a device that includes software, can connect to the internet, and could be
vulnerable to cybersecurity threats. Its manufacturer must submit a plan to monitor, identify and
address vulnerabilities after release, including coordinated vulnerability disclosure; must have
processes that give reasonable assurance of cybersecurity, with updates and patches; and must
provide an SBOM that includes commercial, open-source and off-the-shelf components. A scanner whose
acquisition PC is on the hospital network is very likely a cyber device (assumption: confirm with
team how the NeuroLF has been classified).

In the EU, the MDR's general safety and performance requirements in Annex I ask for software
developed according to the state of the art "taking into account the principles of development life
cycle, risk management, including information security" (section 17.2), for minimum IT security
requirements, "including protection against unauthorised access" (section 17.4), and for devices
that protect "as far as possible, against unauthorised access that could hamper the device from
functioning as intended" (section 18.8). The guidance MDCG 2019-16 explains how notified bodies read
these requirements, and it expects the same artifacts as the FDA in different words: a security risk
assessment, security requirements, verification, information for the user, and post-market
surveillance of vulnerabilities.

For your daily work the regulatory detail matters less than the convergence. Every authority asks
for a threat model, security requirements traced to tests, an SBOM, a vulnerability process and
documentation that tells the site what it must do. The rest of this chapter builds each of them for
MiniDAQ.

::: box-mistakes
- **Treating security as an IT topic.** The hospital's IT department secures its network; it cannot
  secure your control API. Security requirements of the device are design inputs, like its
  performance.
- **A second process.** A separate "security life cycle" next to IEC 62304, with its own documents
  and reviews, drifts away from the code within a release. Put the security activities into the
  plan, the SRS, the risk file and the change control you already have.
- **Probability from defect rates.** An attacker does not fail at random. Estimate how exploitable a
  threat is, and keep the probability of harm in the risk file for what the controls leave.
- **Only before release.** Most of a device's life is after release, and so are most of its
  vulnerabilities. A security plan without monitoring, triage and updates is half a plan.
:::

## Threat modeling

### The intuition

A threat model answers four questions, in the formulation that Adam Shostack made popular: what are
we working on, what can go wrong, what are we going to do about it, and did we do a good enough job?
The first needs a picture of the system that shows where data comes from and where it goes, and
where it crosses from a part you trust to a part you do not. The second needs a method, because
people asked to "think like an attacker" think of the attack they saw last week. The third is
requirements. The fourth is review and testing.

The picture is a data flow diagram (DFD) with four kinds of elements: external entities (people and
systems outside your control), processes (your code), data stores (files, databases) and data flows
(the connections between them). Trust boundaries are drawn where the level of trust changes: between
the network and the acquisition PC, between one user's files and another's. Threats live mostly on
the boundaries, because that is where untrusted input enters and trusted data leaves.

### MiniDAQ's data flow diagram

```{.dot include="docs/regulatory/security/dataflow.dot" caption="MiniDAQ's data flow diagram for the threat model. Dashed: the boundary of the operator's account on the acquisition PC." width="100%"}
```

MiniDAQ has two external entities (control clients and the detector's readout boards), one process
(`minidaq_server`), four data stores (configuration, tokens and keys, list-mode files and run
records, the audit trail) and two flows that cross a boundary: the control API on TCP and the
readout link on UDP. The diagram is a Graphviz file, `docs/regulatory/security/dataflow.dot`, whose
node names are the element identifiers of the threat list, so a check can tell when the two
disagree. Keep the diagram at this level. A DFD with every class of the code in it is a design
diagram that no reviewer can threat-model; one with only "client" and "server" hides the stores
where the secrets live.

### STRIDE

STRIDE, from Loren Kohnfelder and Praerit Garg at Microsoft, is a mnemonic for six categories of
threat, each the violation of one security property:

| Category | Violates | Example for MiniDAQ |
|---|---|---|
| Spoofing | Authentication | A process connects to the control port and sends `stop` as if it were the console. |
| Tampering | Integrity | A machine on the network changes the coincidence window in a `configure` request. |
| Repudiation | Non-repudiation | An operator denies having stopped a scan, and nothing shows otherwise. |
| Information disclosure | Confidentiality | An eavesdropper reads a token and replays it. |
| Denial of service | Availability | Clients that connect and say nothing hold all eight client slots. |
| Elevation of privilege | Authorization | A dashboard's read-only token is used to stop a scan. |

Not every category applies to every kind of element. An external entity can be spoofed and can
repudiate; a process can suffer all six; a data store can be tampered with, disclosed or made
unavailable, and repudiation applies where it holds logs; a data flow can be tampered with, read or
interrupted. Applying STRIDE per element means walking the diagram and asking, for each element and
each category that applies, whether the threat exists and what happens if it is realized. The result
for MiniDAQ is `docs/regulatory/security/threats.json`: 9 elements, 34 threats. Each threat has a
status: mitigated (requirements of the SRS counter it, and their tests pass), environment (the site
counters it, under a stated assumption), accepted (with the reason), or not applicable (with the
reason). Of the 34, 20 are mitigated, 6 rely on the environment, 5 are accepted and 3 are not
applicable.

The threat list is data so that a tool can check what is mechanical, the same way the risk file was
in Chapter 15. `tools/check_threats.py`, run as the test `docs.threats`, checks that every element
is analyzed for every category that applies to its kind:

```{.python include="tools/check_threats.py" snippet="coverage"}
```

and that each status carries its evidence: a mitigated threat names requirements that exist and are
verified, an environment threat names the risk control that tells the site what to do, an accepted
or not applicable threat says why:

```{.python include="tools/check_threats.py" snippet="status"}
```

The check cannot tell whether a threat is missing, or whether a mitigation is good enough. Those are
the questions of the review, and the check frees the review to ask them instead of counting
categories.

### A worked example: the threats that changed the design

Most of the 34 entries confirm what the earlier chapters built: the 64 KiB request limit against an
endless request line (T-11), the integrity verdict against a flood of readout datagrams (T-18), the
effective configuration in every file against a tampered configuration (T-19). A few changed the
design of this chapter:

- **T-01 and T-02, spoofing a client.** Any local process could send `stop`. This is H-08 itself,
  and the reason for tokens and roles.
- **T-06, spoofing the server.** If clients send a token, then a program that listens on the port
  before `minidaq_server` does collects tokens. Over the network, the client must therefore verify
  the server before it sends anything secret, which is TLS with certificate verification. On
  loopback without TLS the threat remains for a PC with several users, and the threat model says so.
- **T-10, denial of service by idle clients.** Eight client slots, and no reason for a client to
  ever leave. An authentication deadline closes connections that do not authenticate in time.
- **T-25, disclosure of tokens.** Tokens on disk must be readable only by their owner, the server
  must not store them at all, and the audit trail must never record one, not even a mistyped one,
  which is often one character away from a real token.
- **T-12, elevation through a later command.** Whoever adds a `calibrate` command next year will
  not think about roles. So the role of a command the authorization code does not know is the
  strictest, not the most permissive.

Three threats are mitigated only in part, and their remainder is recorded as a gap: list-mode files
carry a CRC that detects damage but not a deliberate change with a recomputed CRC (T-27); the audit
trail is appended and flushed but can be rewritten by its own user (T-31); a shared token names a
group, not a person (T-03). Writing a gap down is not an admission of failure. It is the input to
the next change request, and the evidence that the residual risk was considered rather than missed.

### Attack trees

STRIDE finds threats one element at a time. An attack tree starts from the attacker's goal and asks
how to reach it: the root is the goal, each inner node is either an OR (any child will do) or an AND
(all children are needed), and each leaf is a step that is either blocked by something or open. The
tree for H-08's goal, stop or reconfigure a running scan, is in section 4 of the threat model
(`docs/regulatory/security/threat-model.md`). Its first branch reads: send `stop` on the control
API, which needs both reaching the port (from a local process, or from the network) and holding an
operator token (by guessing one, using an observer token, reading one on the network, posing as the
server, reading a token file, adding a token, taking one from a log).

A tree becomes useful once its leaves are marked and you compute with it. Written as data, with each
leaf naming the requirements or site assumptions that block it, two questions have exact answers.
Which attacks are left when every control is in place? And which single control, if it failed, would
open a new attack? Exercise 17.4 writes that evaluator. On MiniDAQ's tree it gives a result that the
drawing hides: with every security requirement verified and every assumption held, one attack is
left, and it is not a security control's failure at all. Any user of the PC can fill the disk; the
run then fails with a write fault. The scan is not silently wrong, which is the safety requirement
of H-01, but it is lost. The threat model records it as a gap with an environment measure (a
partition or quota of its own for the data), and the evaluator shows that seven of the eight
requirements in the tree each open an attack by themselves if they fail, which is what defense in
depth looks like when you measure it.

The MITRE and MDIC *Playbook for Threat Modeling Medical Devices* (2021) walks through these
techniques with medical examples, and is the best first reading after this chapter.

::: box-mistakes
- **A diagram of the code.** A DFD is about data and trust, not classes. If it does not fit on a
  page, it is at the wrong level.
- **Threats without status.** A list of threats is not a threat model until each one says what
  happens about it, with evidence. "Mitigated" without a requirement is an opinion.
- **Only the network.** The first draft of every threat model is about attackers on the network. For
  MiniDAQ, the local user who shares the PC, the token file in a backup and the disk that fills up
  were the threats that changed the design.
- **Accepting elevation of privilege.** A threat that lets someone do what their role does not
  allow, marked "accepted", is a requirement that nobody wanted to write.
- **Modeling once.** The threat model is a design document: every change that adds an interface, a
  store or a flow updates it in the same change.
:::

## Security requirements and controls

### From threats to requirements

Each mitigated threat needs requirements that say what the software does, testably, without saying
how. MiniDAQ's are in a new section of the SRS:

| ID | In short | Threats |
|---|---|---|
| SRS-SEC-001 | Commands other than `hello` and `auth` need an authenticated connection. | T-01 |
| SRS-SEC-002 | An unknown token closes the connection and is recorded, without the token. | T-01, T-03, T-25, T-33 |
| SRS-SEC-003 | An observer may only read the status; refusals are recorded. | T-02, T-12 |
| SRS-SEC-004 | A connection that does not authenticate within 10 s is closed. | T-10 |
| SRS-SEC-005 | No start without tokens unless explicit; beyond loopback, TLS and tokens. | T-01, T-14 |
| SRS-SEC-006 | With TLS, only TLS 1.3, and no answer without a completed handshake. | T-13, T-14 |
| SRS-SEC-007 | The client verifies the server's certificate and name before it sends a token. | T-06, T-13 |
| SRS-SEC-008 | The token store keeps only hashes and refuses files that others can write. | T-23 |
| SRS-SEC-009 | The start-up token has 256 random bits and is readable only by its user. | T-25 |

They implement four new risk controls of H-08 (RC-21 to RC-24); the fifth, RC-25, is the text of
section 6 of the threat model, which tells the site what it must protect. With them, H-08's
probability of harm after control is P2 instead of P4, the residual risk is acceptable and the
hazard is closed: controlling a scan now needs an operator token, which an attacker can only get
through the operator's own account on the acquisition PC. The design decisions behind the
requirements are in ADR 0014 (`docs/adr/0014-control-api-authentication-and-tls.md`), which compared
four options: mutual TLS with client certificates, bearer tokens over TLS, a Unix domain socket with
the kernel's peer credentials, and SSH port forwarding. Tokens over TLS won because they work
remotely and locally, need no certificate authority for every client, and keep the secure
configuration inside MiniDAQ, where its tests can check it.

### Authentication: tokens stored as hashes

A bearer token is a random secret that the client presents; whoever bears it is authenticated.
MiniDAQ's tokens are 32 bytes from OpenSSL's `RAND_bytes`, written as `mdq_` and 64 hex digits. The
prefix is not decoration: it lets secret scanners, such as the ones that code hosting platforms run
on every push, recognize a leaked token. The server never stores a token. Its token file holds a
name, a role and the SHA-256 hash of each token:

```{.cpp include="minidaq/include/minidaq/control/access.hpp" snippet="tokens"}
```

Storing hashes means that a copy of the server's token file, in a backup or a support bundle, does
not let anyone in. A fast hash is enough because the token has 256 bits of entropy: there is nothing
to guess. Passwords, which people choose and which have far less entropy, need a slow hash (Argon2,
scrypt, bcrypt) for the same purpose; using one here would only slow the server down.

The comparison deserves attention. `std::string`'s `==` stops at the first byte that differs, and a
loop that returns at the first match stops at the matching entry. Both make the response time depend
on the secret, and timing differences over a network are measurable with enough repetitions. The
check hashes the presented token, so the attacker does not control the bytes that are compared, then
compares with every entry, with OpenSSL's constant-time `CRYPTO_memcmp`, without an early exit:

```{.cpp include="minidaq/src/control/access.cpp" snippet="check"}
```

The token file is loaded with `O_NOFOLLOW`, and refused if it is a symbolic link, belongs to another
user, or is writable by anyone else (SRS-SEC-008): whoever can write the file can add an operator. A
client authenticates once per connection, with `{"cmd": "auth", "token": ...}`, and the protocol
layer records the result in the audit trail under the token's name, never the token:

```{.cpp include="minidaq/src/control/control_protocol.cpp" snippet="auth"}
```

### Authorization: roles that fail closed

Two roles are enough for MiniDAQ: an observer may read the status, an operator may also configure,
start, stop and reset. The function that maps a command to the role it needs is three lines, and the
third is the important one:

```{.cpp include="minidaq/src/control/access.cpp" snippet="roles"}
```

A command that the function does not know needs the operator role. When someone adds `calibrate`
next year and forgets about roles, the command is protected until someone decides otherwise; with
the opposite default it would be open to everyone, including observers, until someone notices. This
is "fail closed", and Exercise 17.2 shows how easily access control code ends up failing open. The
check sits in the protocol layer, before any command is executed, and keeps `handle_request`
independent of the transport, as ADR 0003 required: it sees a `Session`, not a socket.

```{.cpp include="minidaq/src/control/control_protocol.cpp" snippet="authorize"}
```

### TLS 1.3 and certificate verification

A token in plain text on the network is a token for anyone who can capture packets. TLS encrypts and
authenticates the connection; for MiniDAQ the configuration is short, because TLS 1.3 removed most
of what TLS 1.2 let you get wrong. Every TLS 1.3 cipher suite provides forward secrecy and
authenticated encryption, so the only decision is to refuse older versions:

```{.cpp include="minidaq/src/control/tls.cpp" snippet="context"}
```

Session tickets and resumption are turned off: control connections are rare and long-lived, and
resumption adds state and a class of bugs (the package review in the SOUP list found one,
CVE-2024-2511, that concerns exactly this setting). The client is where most TLS mistakes are made,
because a client that does not verify the server's certificate gets encryption to whoever answers.
MiniDAQ's client loads the CA certificates it trusts, sets the host name or IP address it expects,
sends a DNS name in the handshake (SNI), and only then connects; `SSL_VERIFY_PEER` makes the
handshake fail if the chain or the name does not match:

```{.cpp include="minidaq/src/control/tls.cpp" snippet="connect"}
```

The order matters for SRS-SEC-007: the token is sent in the first request after the handshake, so a
server that fails verification never sees it. Client certificates are not used: they would
authenticate the client's machine, and the token already authenticates the client's role. The server
uses TLS on non-blocking sockets in its single `poll()` loop, which means that a TLS read can need a
socket write (and the reverse) during the handshake; the details are in `control_server.cpp`, and
the test `ControlServer.ServesOnlyTls13Clients` sends three requests in one TLS record and offers a
TLS 1.2 handshake to check them.

### Secure defaults

A control that the user must turn on is a control that will be off on some sites. MiniDAQ's server
checks its own configuration before it listens:

```{.cpp include="minidaq/src/control/control_server.cpp" snippet="secure_defaults"}
```

Without a token file it does not run unauthenticated. It makes a start-up operator token, writes it
with mode 0600 into a directory of mode 0700 (refusing a directory that is a link or belongs to
another user, which is what an attacker would prepare in `/tmp`), and `minidaq_ctl` of the same user
finds it there. The commands of the earlier chapters therefore keep working without a flag, and only
the same user can use them. A session, recorded against `minidaq_server`:

```text
$ minidaq_server --port 7713
minidaq_server: control API on 127.0.0.1:7713 (plain TCP, token in
$XDG_RUNTIME_DIR/minidaq/minidaq-7713.token; state idle)
$ stat -c '%A %n' $XDG_RUNTIME_DIR/minidaq $XDG_RUNTIME_DIR/minidaq/*
drwx------ /run/user/1000/minidaq
-rw------- /run/user/1000/minidaq/minidaq-7713.token
$ minidaq_ctl --port 7713 status                  (no token option: the file above is used)
```

(The run directory is written as `$XDG_RUNTIME_DIR` and shown as `/run/user/1000`, its usual value;
the session ran with a temporary one.) When the server stops, it removes the token file.

A program that does not authenticate meets the new protocol (API 2.0; a 1.x client is refused,
because it would otherwise appear to connect and then fail on every command):

```text
-> {"api": "2.0", "id": 1, "cmd": "stop"}
<- {"api":"2.0","error":{"code":"unauthenticated","message":"authenticate first (\"auth\")"},
    "id":1,"ok":false,"state":"idle"}
-> {"api": "1.1", "id": 2, "cmd": "status"}
<- {"api":"2.0","error":{"code":"unsupported_api","message":"this server speaks API 2.0"},
    "id":2,"ok":false,"state":"idle"}
-> {"api": "2.0", "id": 3, "cmd": "auth", "token": "mdq_0000...0000"}
<- {"api":"2.0","error":{"code":"unauthenticated","message":"unknown token; the connection is
    closed"},"id":3,"ok":false,"state":"idle"}
-> {"api": "2.0", "id": 4, "cmd": "stop"}
<- (connection closed)                                     (line breaks added, token shortened)
```

For a dashboard, the administrator makes an observer token with `minidaq_ctl new-token dashboard
observer`, which prints the token for the dashboard and the line for the server's token file. With
that file, a second server (`minidaq_server --port 7712 --tokens tokens.json --audit audit.jsonl`)
lets the dashboard read the status; when the dashboard tries to stop the run, the server refuses and
the audit trail names it:

```text
$ minidaq_ctl --port 7712 --token-file dash.token stop
{ "api": "2.0", "error": { "code": "forbidden", "message": "\"stop\" needs the role operator" },
  "id": 1, "ok": false, "state": "idle" }                       (exit status 1; reformatted)
$ grep refused audit.jsonl
{"action":"stop","detail":"refused: role","ok":false,"time":"2026-10-25T12:06:43.736Z",
 "who":"dashboard@tcp:127.0.0.1:35866"}
```

Turning authentication off needs `--no-auth`, and is refused anywhere but loopback. Binding to any
address outside `127.0.0.0/8` needs both TLS and tokens. A connection that has neither finished the
handshake nor authenticated after 10 s is closed. The secure configuration is the default, and the
insecure one takes an explicit, visible decision that the server prints at start-up.

### Least privilege and updates

Two more controls belong to the same family and are mostly the platform's. Least privilege: the
server needs no root rights, so it runs as an ordinary user, which limits what an attacker who finds
a memory error in it can do; the real-time settings of Chapter 4 need capabilities, not root, and
Chapter 25 configures them for the installed system. Signed updates: whoever can replace
`minidaq_server` controls the scanner (T-07), so software reaches the PC through signed packages
whose signature the package manager verifies; MiniDAQ's part is the SBOM that says what should be
installed, and Chapters 25 and 32 deploy and package it.

::: box-mistakes
- **A client that does not verify.** `SSL_VERIFY_NONE` "for now", or a verification callback that
  returns 1, gives encryption to an impostor. Test the failure: a server signed by another CA and a
  wrong host name must both be refused, before the token is sent.
- **Secrets in logs.** A refused token is logged "for debugging", and the log is shipped to support.
  Log the token's name, or nothing.
- **Comparing secrets with `==`.** Use the library's constant-time comparison, on hashes, over every
  entry.
- **Failing open.** A default branch that allows, an unknown role that becomes a real one, an error
  in loading the token file that falls back to "no authentication". Make the strict path the
  default, and make the server refuse to start rather than start insecurely.
- **Forgetting the signal.** Writing to a connection that the peer has closed raises `SIGPIPE`,
  whose default action ends the process. MiniDAQ's first TLS test died silently this way when a
  client dropped a refused connection; the server now blocks the signal in its thread, and the
  client ignores it. A remote client that can kill the server by disconnecting is a denial of
  service.
:::

## Verifying security

### Tests that reproduce the attack

The tests of SRS-SEC-001 to 009 check each requirement, but the risk file asks a different question
for each risk control: is it effective? For RC-21 and RC-22 the answer is a test that reproduces the
sequence of events of H-08, an intruder who connects while a scan runs and tries everything short of
an operator token, and shows that the scan goes on:

```{.cpp include="minidaq/tests/unit/test_security.cpp" snippet="effectiveness"}
```

The list of attacks is the attack tree's branches written as requests: no token, an old API version,
an empty token, an observer token with a `stop` smuggled after a newline, and the hash of the
operator's token (in case the server compared hashes with what the client sent). For RC-23 the test
`ControlServer.TheTokenNeverCrossesTheNetworkInClear` puts a relay between client and server that
copies every byte, as an eavesdropper on the network would, and checks that neither the token nor
the commands appear in what it saw; the same relay in front of a server without TLS reads the token,
which is why RC-23 exists. These tests are named as effectiveness evidence in `hazards.json`, and
`docs.risk` fails if they disappear.

### Fuzzing with a security property

Chapter 7's protocol fuzzer checked that no input crashes the server or breaks the framing. A crash
is the easiest property to check, and on its own a weak security test: the attack that matters most
is a request that succeeds when it should not. The fuzzer now runs each input as one
connection against a server with tokens, and aborts if a command succeeds without the role it needs:

```{.cpp include="fuzz/fuzz_protocol.cpp" snippet="property"}
```

Half the inputs connect to a server whose only token is an observer's, so that the fuzzer explores
the observer's side of the boundary too; the seed corpus contains an authenticated `configure` and
an observer's `status`. A property like this turns the fuzzer from a crash finder into a test of the
authorization logic over inputs nobody would write by hand.

The crash check still earned its place, hours after this chapter's code went in. On the next commit
the CI job `fuzz-smoke` stopped with `type must be string, but is number`. An `auth` request whose
token was a number, `{"cmd":"auth","token":5}`, made `req.value("token", std::string{})` throw:
nlohmann's `value()` returns the default when the key is missing, but throws when the key holds
another type. Nothing caught the exception, and the server ended. One line from anyone who can
connect, before authentication, stops a running scan: a denial of service that the tokens do not
prevent, because it happens before them. The 60-second local run while this chapter was written had
not reached that input; another 60 seconds on GitHub did. Problem report MDQ-PR-013 records it, and
the handler above now reads the token only when it is a string.

It was the second time. In Chapter 7 a number too large for a `double` ended the configuration
reader the same way (MDQ-PR-001), and that fix was local. Two problems with one cause call for a
CAPA (Chapter 16), and CAPA-0003 asks what let the second one through: nothing tested the types of a
request's fields. A fuzzer finds such an input by chance and in time; a test can try them all on
every change. Requirement SRS-CTL-034 says that the protocol answers every JSON object whatever its
fields' types, and its test sends each field with every JSON type, for every command and every kind
of client, 1,760 requests:

```{.cpp include="minidaq/tests/unit/test_control_protocol.cpp" snippet="type_confusion"}
```

Rule 3.5 of the coding standard now says how to read untrusted JSON. The lesson is wider than one
library: when a fuzzer finds a bug, ask which test would have found it every time, and write that
test too.

### Static analysis, review and penetration testing

The static analysis of Chapter 7 runs over the new code, and it found one issue while it was
written: OpenSSL's `SSL_set_tlsext_host_name` is a macro with an old-style cast, which `-Werror`
rejects; the client calls `SSL_ctrl` with the same arguments instead. Static analysis finds classes
of defects; it does not know that a role check is missing. That is the reviewer's job, and the
threat model gives the review its questions: does this change add an element, a flow or a store, and
which STRIDE categories does it reach?

Penetration testing is the last layer: people who did not write the software, with the threat model
and the documentation, try to break it. It finds what the authors' model missed, because the
authors' blind spots are in the model too. MiniDAQ has not been penetration tested, and its threat
model says so; for a device, the FDA expects the results of such testing in the submission, and a
penetration test is planned before the first clinical release (assumption: confirm with team who
performs it for the NeuroLF).

::: box-mistakes
- **Testing the happy path of security.** "The operator can log in" is not a security test. The
  security test is that everyone else cannot, in every way the threat model lists.
- **Fuzzing for crashes only.** Add the property that matters: no command succeeds without its role,
  no response contains a secret.
- **Convenient accessors on untrusted input.** `json.value("token", std::string{})` looks like a
  safe default and throws on a number. Check the type, then read; let a test send every type.
- **Mocking the crypto in the security tests.** The tests of the controls must use the real TLS
  library and real certificates (MiniDAQ's tests make a throw-away CA with P-256 keys). A mock
  proves that the mock works.
- **The developers' penetration test.** Testing your own design finds your own assumptions. Plan an
  independent test, and give the testers the threat model.
:::

## The SBOM and vulnerability management

### What the SBOM must contain

Chapter 7 generated a CycloneDX SBOM from the dependencies pinned in `cmake/Dependencies.cmake`. The
NTIA's minimum elements (2021) name what each entry needs: supplier, component name, version, other
unique identifiers, the dependency relationship, the author of the SBOM data and a timestamp. The
FDA's guidance asks in addition for each component's level of support and end-of-support date, and
for the known vulnerabilities with their assessment, which the SBOM itself does not have to carry
but the submission does.

OpenSSL changed what MiniDAQ's SBOM must do. It is not pinned and built by MiniDAQ but taken from
the target system, as a platform library: `find_package(OpenSSL 3.0 REQUIRED)`, linked privately
into `minidaq_control` only. A vulnerability scanner can only match what the SBOM identifies
exactly, and here "OpenSSL 3.0.13" is not exact: Ubuntu 24.04 ships OpenSSL 3.0.13 with dozens of
security fixes backported, and a scanner that sees only the upstream version reports every fixed
vulnerability as open. The SBOM therefore records the installed package, with the distribution in
its package URL:

```{.python include="tools/make_sbom.py" snippet="platform"}
```

On the build machine, the entry reads
`pkg:deb/ubuntu/libssl3t64@3.0.13-0ubuntu3.16?arch=amd64&upstream=openssl&distro=ubuntu-24.04`. A
scanner then uses the distribution's own security data, which knows which fixes the package
contains. Where there is no package manager, the generator falls back to the upstream version with a
CPE identifier.

### Scanning and triage

The CI job `vulnerability-scan` matches the SBOM against public vulnerability databases with Grype,
pinned to a released version, every time the main branch changes. The database is downloaded at each
run, so a vulnerability published tonight fails tomorrow's build until someone decides on it. That
"someone decides" is the part that tools cannot do. A scanner reports what a database says about a
component's version; it does not know whether MiniDAQ uses the affected function. Every finding
therefore needs a decision, recorded in `docs/regulatory/security/vulnerability-triage.json` in the
analysis states of CycloneDX's vulnerability exploitability exchange (VEX): `not_affected`, with a
justification from a fixed list (the code is not present, or not reachable, or needs a configuration
MiniDAQ does not use); `exploitable`, with a response (update, workaround); `in_triage`; `resolved`
or `false_positive`. `tools/vuln_triage.py` applies the decisions to the scan's report and fails on
the cases that would hide a problem:

```{.python include="tools/vuln_triage.py" snippet="rules"}
```

A finding without a decision fails, an exploitable high or critical finding without a fix date or
past it fails, and a high or critical finding may not stay in triage. A decision that no finding
matches any more (the component was updated) is reported as stale. The tool also writes the
decisions as a CycloneDX VEX document, which is the form in which a manufacturer can tell a hospital
which reported vulnerabilities affect the device.

The first run on GitHub reported no vulnerabilities at all. That is the result you want, and the one
to distrust most, because a scanner that cannot match a component also reports nothing: a misspelled
package URL, a distribution the database does not know, a database that failed to load. So the job
has a negative control. It scans a copy of the SBOM in which OpenSSL is the original noble package,
`3.0.13-0ubuntu3`, which later security updates fixed, and fails if that scan finds nothing. A clean
report then means "matched and fixed", not "never matched". Any check that passes by finding nothing
deserves a control that shows it can fail.

The first review of OpenSSL as SOUP was done this way, by hand, from the package's own changelog: 44
security updates between `0ubuntu3.1` and `0ubuntu3.16`, grouped by the feature they affect. Most
concern features MiniDAQ never uses (DTLS, CMS, PKCS#12, CMP, OCSP). A handful concern exactly what
it does use: X.509 name checks in the client (CVE-2024-6119), ASN.1 parsing of certificates, TLS 1.3
session handling with `SSL_OP_NO_TICKET` (CVE-2024-2511), which MiniDAQ sets. All are fixed in the
installed package, and the review's decision is a requirement on the platform: MiniDAQ 0.3 needs
that package version or later. The record is in the SOUP list (`docs/regulatory/soup-list.md`), and
it marks with *verify* what could not be checked against the OpenSSL project's own advisories from
the build environment.

### Coordinated disclosure

Some vulnerabilities are found by people outside the company: researchers, hospital security teams,
customers. Coordinated vulnerability disclosure is the process that turns their report into a fix
before it turns into an exploit: a published channel for reports, an acknowledgment, an assessment,
a fix, and a disclosure date agreed with the reporter, followed by an advisory that names the
affected and fixed versions. ISO/IEC 29147 describes the disclosure side and ISO/IEC 30111 the
handling inside the company, and section 524B makes such a process law for cyber devices. MiniDAQ's
`SECURITY.md` says where to report, and the threat model's section 8 describes the steps; for a real
device, the contact, the response times and the advisories are the manufacturer's (assumption:
confirm with team your company's process).

An incoming vulnerability is a problem report like any other, evaluated for its hazards (Chapter
15), fixed through a change request (Chapter 16), and verified by a regression test and a scan that
no longer reports it. The difference is the clock: a disclosure date is fixed, and the people who
need the fix are in hospitals.

::: box-mistakes
- **An SBOM that a scanner cannot match.** A component without an exact version or package URL is
  matched wrongly or not at all. Record what is installed, including the distribution's version.
- **Scanning without triage.** A red scan that everyone ignores, or a scanner with a suppression
  list that nobody reviews, is worse than no scan: it trains the team to ignore it. Every finding
  gets a decision with a reason, a date and a name.
- **"Not affected" without reading.** "We do not use that feature" is a claim to check in the code,
  not a reflex. For a critical finding, read the advisory's affected function and its fix.
- **No way to report.** A researcher who cannot find whom to tell will publish instead.
:::

## The change: CR-0004

All of this went into MiniDAQ through one change request, CR-0004
(`docs/regulatory/changes/CR-0004-control-api-security.md`), and its impact analysis is a good
summary of what a security change touches. Requirements: SRS-SEC-001 to 009, and the tests of the
control API repeated because they now authenticate first. Software items: a new item `access`, class
B, and `minidaq_ctl` reclassified from A to B. In Chapter 14 the client was class A because the
server validated everything it sent; now it holds an operator token and must verify the server
before sending it, so a defect in it can hand the token to an impostor. Risk: H-08 closed with RC-21
to RC-25. SOUP: OpenSSL, new, as a platform library with its own review. Interfaces: API 2.0, a
breaking change, with the new command `auth`, the error codes `unauthenticated` and `forbidden`, and
new files for tokens. Documents: ADR 0014, the SRS, the architecture description, the SOUP list, the
threat model, the known anomalies (MDQ-PR-008 closed). Regulatory: a change to the device's security
controls, whose significance regulatory affairs assesses.

The reclassification of `minidaq_ctl` is the part that surprises people. Security changes the
argument for segregation: a client in its own process could be class A as long as the worst it could
do was send a wrong command that the server would reject. Holding a secret changes what its failure
can cause, and so its class.

::: box-regulated
What the regulated setting adds to this chapter's examples:

- The threat model, the security requirements, the security test results, the SBOM and the
  vulnerability assessment are parts of the premarket submission (FDA) and of the technical
  documentation (EU MDR); they are written to be read by a reviewer who has never seen the code.
- The security risk assessment uses exploitability, not failure rates, and feeds the safety risk
  file; a vulnerability that can lead to harm is evaluated as a hazard (Chapter 15), with the
  manufacturer's own scales (assumption: confirm with team which scale the NeuroLF uses, for example
  CVSS with a medical device rubric).
- The hospital receives documentation for secure installation and operation, often in the MDS2
  form (*Manufacturer Disclosure Statement for Medical Device Security*), and the site's
  responsibilities are written there, not only in the threat model.
- After release, vulnerabilities in the device and its SOUP are monitored, triaged and fixed within
  times the manufacturer commits to, and a vulnerability with a risk to patients can lead to a field
  safety corrective action and a report to the authorities.
- Security testing includes an independent penetration test before release, and its findings are
  closed or justified in the release record.
:::

::: box-askteam
1. Is the NeuroLF classified as a cyber device under section 524B, and which of its interfaces does
   the submission's threat model cover?
2. Where are the security risk assessment and the threat model kept, and how do they link to the ISO
   14971 risk file?
3. Which scale is used to rate exploitability, and who decides on a vulnerability's severity for the
   device?
4. Who runs the vulnerability monitoring of the SBOM after release, and how fast must a high finding
   be triaged and fixed?
5. Who performs the penetration tests, and when were the last results reviewed?
:::

## Exercises {.unnumbered}

**Exercise 17.1 (M): Threat model a status page before it is built.** *Goal:* the service team asks
for a read-only status page that the scanner room's display can show (`GET /status` over HTTPS);
model its threats with STRIDE before anyone writes it, and finish the checker that keeps such a
model honest. This is the plan's threat-modeling exercise applied to the next interface, since the
control API's own model is the worked example. *Starter:* `exercises/ch17/e1_threat_model/` (the
diagram check of `tools/check_threats.py` with TODOs for coverage and status rules, a draft with two
threats, one of them wrong, and the proposed requirements DASH-001 to DASH-008). *Acceptance:*
`tests/test_threats.py` passes: the checker reports missing categories, mitigations without proposed
requirements, environment threats without an assumption and accepted threats without a reason; your
model passes it, has at least 10 threats, and mitigates elevation through the page, disclosure on
the wire, spoofing of the display and denial of service by slow clients with the right requirements.
Then answer in `NOTES.md` which requirement you would drop, which is missing, and whether the page
is worth its threats. *Time:* 2 hours.

**Exercise 17.2 (M): A token store that fails closed.** *Goal:* write the core of MiniDAQ's
authentication yourself, the role of each command and a store of token digests, without OpenSSL; the
TLS part of the plan's exercise is the chapter's worked example. *Starter:*
`exercises/ch17/e2_token_roles/` (works for the happy path and has the four classic defects of
access control code: it fails open for unknown commands, gives an unknown role a real one, accepts
malformed and duplicate entries, and compares with `==` and an early return). *Acceptance:*
`tests/test_access.cpp` passes: unknown commands and near misses need the operator role; the parser
refuses empty files, unknown roles, malformed digests, extra fields and duplicates with the line
number; `check()` calls the comparison once per entry for every token and refuses malformed tokens
before hashing them. Then answer in `NOTES.md` why the tests count comparisons instead of measuring
time, and what that does not prove. *Time:* 90 minutes.

**Exercise 17.3 (E): Triage a vulnerability scan.** *Goal:* the CI job reported six findings for
MiniDAQ's SBOM, with made-up identifiers; decide each one in VEX states, and finish the rules that
check decisions. This is the plan's scanning exercise: the scan itself runs in the CI job of this
chapter. *Starter:* `exercises/ch17/e3_vuln_triage/` (the triage tool as a module without the rules
for `not_affected`, `exploitable` and `in_triage`, the scan report and the advisories).
*Acceptance:* `tests/test_triage.py` passes: justifications, responses and fix dates are required
where the rules say; your decisions cover every finding, mark the TLS server and host name defects
exploitable, the DTLS defect not reachable and GoogleTest's not present, and say why the SAX defect
does not reach MiniDAQ. Then answer in `NOTES.md` what you would check before signing the decision
on the critical finding. *Time:* 1 hour.

**Exercise 17.4 (M, extra): Compute what an attack tree says.** *Goal:* write the evaluator that
finds the minimal attacks left once a tree's leaves are marked, and the controls whose failure alone
opens an attack; check it against the threat model's tree, then draw your own for changing a scan's
data unnoticed. *Starter:* `exercises/ch17/e4_attack_tree/` (TODOs for the evaluator, the threat
model's tree as JSON, and the root of your tree). *Acceptance:* `tests/test_attack_tree.py` passes:
OR and AND nodes and minimization are right; on the threat model's tree, filling the disk is the
only attack left with every control and assumption, the operator's account appears without the
assumptions, and the critical requirements are found; your tree has at least five leaves, names
SRS-LMF-006 and a site assumption, is closed with every control and open without the assumptions.
Then answer in `NOTES.md` whether a disk that anyone can fill is a security or a safety problem.
*Time:* 2 hours.

**Exercise 17.5 (H, extra): Secure defaults for IPv4 and IPv6.** *Goal:* write the start-up check of
SRS-SEC-005 for IPv4 and IPv6, where "loopback" has more spellings than `127.0.0.1`. *Starter:*
`exercises/ch17/e5_secure_bind/` (recognizes loopback by its text, accepts `localhost`, and lets TLS
stand in for authentication). *Acceptance:* `tests/test_bind_check.cpp` passes: all of
`127.0.0.0/8`, `::1` in any spelling and IPv4-mapped loopback are loopback; wildcards, names, text
with spaces or a NUL byte and anything not exactly numeric are not; beyond loopback both tokens and
TLS are required and `--no-auth` is refused. Then answer in `NOTES.md` why accepting `localhost` is
a defect. *Time:* 2 hours.

## MiniDAQ milestone: threat model, security requirements, authenticated control API {.unnumbered}

::: box-milestone
**Goal.** MiniDAQ has a threat model with a data flow diagram, a checked STRIDE analysis and an
attack tree; security requirements in the SRS, traced to tests; a control API that authenticates
with tokens, authorizes by role and offers TLS 1.3, with secure defaults; OpenSSL as reviewed SOUP
in the SBOM; a vulnerability scan in CI with recorded triage; and H-08 closed. **Start:** tag
`ch16`. **End:** tag `ch17`.
:::

1. Write `docs/regulatory/security/threat-model.md`, `threats.json` and `dataflow.dot`, and add
   `tools/check_threats.py` and the test `docs.threats`.
2. Add SRS-SEC-001 to 009 and the risk controls RC-21 to RC-25 of H-08; record CR-0004 and ADR 0014.
3. Implement `control/access` (tokens, roles, the start-up token) and `control/tls` (TLS 1.3 server
   and verifying client) on OpenSSL 3; add the `Session` to `handle_request`, the security checks
   and the authentication deadline to `ControlServer`, and the options to `minidaq_server` and
   `minidaq_ctl`, with API 2.0.
4. Write the security tests, with the effectiveness tests of RC-21 to RC-23, a throw-away CA for the
   TLS tests and the eavesdropping relay, and the fuzzer's authorization property.
5. Add OpenSSL to the SOUP list with its review, and as a platform component to the SBOM; add the CI
   job `vulnerability-scan`, `tools/vuln_triage.py` with its test, and `SECURITY.md`.
6. Reclassify `minidaq_ctl`, add the item `access`, update the architecture description and close
   MDQ-PR-008; add Exercises 17.1 to 17.5.

**Definition of done.** `ci/run_all.sh` is green on all six presets and static analysis reports
nothing; `docs.risk` shows no open hazard; `docs.threats` fails when you delete a threat that is the
only one of its category for an element; the server refuses to bind `0.0.0.0` without TLS and
tokens; a `stop` without an operator token never stops a running scan; the token never appears in
the relay's capture or the audit trail; the CI vulnerability scan runs and every finding has a
decision. Tag `ch17`.

## Check yourself {.unnumbered}

1. How does a security risk become a safety risk? Answer with H-08's sequence of events.
2. What must the SBOM contain, and why does MiniDAQ's record the Ubuntu package version of OpenSSL
   rather than the upstream version?
3. Name the four kinds of element in a data flow diagram and the STRIDE categories that apply to
   each.
4. Why does the server store hashes of tokens, and why is SHA-256 enough here when passwords need a
   slow hash?
5. What does "fail closed" mean for `required_role()`, and what would have happened with the
   opposite default?
6. Why must the client verify the server's certificate before it sends its token? What does an
   unverified TLS connection protect against, and what not?
7. Why did the control API's major version change to 2.0 instead of 1.2?
8. Why was `minidaq_ctl` reclassified from class A to class B?
9. A scanner reports a critical vulnerability in a library you use. Which questions do you answer
   before you mark it `not_affected`, and which justification do you choose if the code is in the
   library but MiniDAQ never calls it?
10. What does section 524B of the FD&C Act require of a manufacturer of a cyber device?
11. Which threats in MiniDAQ's threat model rely on the site, and how does the risk file make sure
    the site is told?
12. Why is a fuzzer that only looks for crashes a weak security test, and what property does
    MiniDAQ's protocol fuzzer check now?

## Summary {.unnumbered}

- A security threat becomes a safety risk when an attack is a cause in a hazard's sequence of
  events; H-08, an unauthorized party controlling the acquisition, was MiniDAQ's only unacceptable
  risk.
- IEC 81001-5-1 adds security activities to the IEC 62304 life cycle; the FDA's guidance and section
  524B, and the EU MDR's Annex I, expect a threat model, security requirements, testing, an SBOM and
  post-market vulnerability management.
- A threat model is a data flow diagram with trust boundaries, a STRIDE analysis per element in
  which every threat has a status with evidence, and attack trees that show what is left; MiniDAQ's
  has 34 threats, a checker, and recorded gaps.
- Security requirements SRS-SEC-001 to 009 implement risk controls RC-21 to RC-24; RC-25 tells the
  site what it must protect. H-08 is closed at S2/P2.
- Tokens are random, stored as hashes and compared in constant time; roles fail closed; TLS 1.3 with
  a verifying client protects them on the network; the server refuses insecure configurations.
- Security controls are verified by tests that reproduce the attack, a fuzzer with an authorization
  property, static analysis, review against the threat model, and independent penetration testing.
- The SBOM must identify what is installed exactly enough for a scanner; every finding of the scan
  gets a VEX decision with a reason, and vulnerabilities are disclosed in coordination.
- One change request, CR-0004, carried the change: new SOUP, a new item, a reclassified client, a
  breaking API version, and the documents that say why.

## Further reading {.unnumbered}

- IEC 81001-5-1:2021, *Health software and health IT systems safety, effectiveness and security:
  Part 5-1: Security: Activities in the product life cycle*.
- U.S. Food and Drug Administration, *Cybersecurity in Medical Devices: Quality System
  Considerations and Content of Premarket Submissions*, guidance, September 2023, and its later
  revision (verify: the current revision and date).
- Federal Food, Drug, and Cosmetic Act, section 524B, *Ensuring cybersecurity of devices*, added by
  the Consolidated Appropriations Act, 2023.
- Medical Device Coordination Group, MDCG 2019-16 rev. 1, *Guidance on Cybersecurity for medical
  devices* (2020).
- MITRE and MDIC, *Playbook for Threat Modeling Medical Devices* (2021).
- Adam Shostack, *Threat Modeling: Designing for Security*, Wiley, 2014.
- AAMI TIR57:2016, *Principles for medical device security: Risk management*.
- NTIA, *The Minimum Elements for a Software Bill of Materials (SBOM)*, July 2021.
- ISO/IEC 29147:2018, *Vulnerability disclosure*, and ISO/IEC 30111:2019, *Vulnerability handling
  processes*.
- OWASP CycloneDX, *Vulnerability Exploitability Exchange (VEX)*, in the CycloneDX 1.5
  specification.
