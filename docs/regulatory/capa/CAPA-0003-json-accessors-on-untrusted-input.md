# CAPA-0003: JSON accessors that throw, used on untrusted input

| Field | Value |
|---|---|
| Status | implemented |
| Opened | 2026-10-25, by the software lead (Part III review) |
| Source | MDQ-PR-001, MDQ-PR-013 |
| Owner | software lead |
| Effectiveness check | release 0.4.0 |

## Problem

The CI job `fuzz-smoke` crashed `fuzz_protocol` on commit `dcb701a`, the first commit after Chapter
17 (MDQ-PR-013). One request line from a client that has not authenticated,
`{"cmd":"auth","token":5}`, ended `minidaq_server` with `nlohmann::json::type_error`: the handler
read the token with `req.value("token", std::string{})`, which throws when the key is present with
another type, and nothing between the handler and `main` catches it. The 60-second local campaign
for Chapter 17 had not reached the input; the CI campaign of the next commit did. Before the release
it was found, but it is the second time the same library behavior escaped on untrusted input: in
Chapter 7 a number too large for a `double` ended the configuration reader (MDQ-PR-001), and that
fix was local.

## Investigation

Every call in `minidaq/src`, `minidaq/apps` and `minidaq/include` of the nlohmann accessors that
throw on a wrong type or a missing key (`value(key, default)` with a typed default, `get<T>()`,
`get_ref<T>()`, `at()`) was read, 21 places before the correction (four of them `value()` with a
JSON default, which cannot throw on a type), and each classified by where its JSON comes from:

- **Control requests (untrusted, long-running process):** `control_protocol.cpp` reads `api`
  and `cmd` after `is_string()` checks on the same line or the line before; `token` was the one
  unchecked read. `configure` checks that `config` is present, and the configuration reader
  (`acquisition_config.cpp`) checks every type before it reads a value and catches
  `json::exception` since MDQ-PR-001.
- **Token file (untrusted, read at start-up):** `access.cpp` checks every field's type before
  `get<std::string>()`.
- **Server responses in `minidaq_ctl` and list-mode metadata in `minidaq_listmode`
  (untrusted, one-shot tools):** a wrong type throws, and `main` catches `std::exception`, prints
  it and exits with status 2. A tool that stops with a message on a malformed input is the
  intended behavior; no change.
- **Documents MiniDAQ writes itself (trusted):** the run record in `acquisition_service.cpp` and
  the status read by `run_integrity.cpp`, both built by the same process.

The protocol fuzz target found the defect, as rule 3.4 of the coding standard intends. What let it
reach a commit is that the protocol layer had no test of field types at all: the tests sent
well-typed requests and a few malformed lines, and SRS-CTL-022 asks for malformed JSON to be
rejected, not for well-formed JSON of unexpected types to be answered.

## Root cause

The coding standard's rules on untrusted input cover parsing, size and paths, but say nothing about
reading values from a parsed document, where the library's convenient accessors throw on a wrong
type. Nothing required a test that every field of a request may have any type, so the property was
checked only by a fuzzer, which finds such inputs by chance and in time, not on every change.

## Correction

`authenticate()` reads the token only when it is a string; any other value is an unknown token, so
the request is refused and the connection closed (SRS-SEC-002). The input is in the seed corpus
(`fuzz/corpus/protocol/auth_wrong_types`).

## Corrective action

Rule 3.5 of `docs/coding-standard.md`: a value from an untrusted JSON document is read after its
type is checked (`find` or `contains`, then `is_string()` and the like), never with `value(key,
default)` or `get<T>()` alone; a long-running process never lets a JSON exception escape a request.
Requirement SRS-CTL-034 (`docs/regulatory/srs.md`, version 5): the protocol answers every request
that is one JSON object, whatever the type of each field. Its test
`ControlProtocol.EveryFieldOfEveryTypeIsAnswered` (`minidaq/tests/unit/test_control_protocol.cpp`)
sends each field the protocol reads (`api`, `id`, `cmd`, `token`, `config`) with eleven values of
every JSON type, for every command and for an anonymous client, an operator, an observer and a
server without authentication: 1,760 requests, deterministic, on every change.

## Preventive action

The other parsers of untrusted input already check types (the token file) or are one-shot tools that
report the error (investigation). A catch of every exception around `handle_request` in the server
(`minidaq/src/control/control_server.cpp`) was considered and not made: an exception in the middle
of a command could leave the acquisition service in a state that no test has seen, and ending the
process keeps the files written so far readable (H-03, H-05), which is the safer failure. Rule 3.5
asks review to add any new request field to the field list of the test.

## Verification of the actions

All six presets and static analysis pass. The new test and the extended tests
`ControlProtocol.AuthenticationInTheProtocolLayer` and
`ControlServer.AnUnknownTokenClosesTheConnection` fail on the code before the correction (the new
with exactly the CI crash) and pass after it. No requirement or risk control is weakened: a token
that is not a string was never valid.

## Effectiveness check

Criterion: no JSON exception escapes in any fuzz target, in CI or in the 10-minute release
campaigns, and no problem report of this cause, between this CAPA and the release of 0.4.0. Due:
release 0.4.0. Result: filled in at the check.

## Closure

Not closed: the effectiveness check is due at release 0.4.0.
