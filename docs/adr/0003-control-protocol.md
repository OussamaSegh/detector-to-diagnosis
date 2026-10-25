# 0003. Control protocol: newline-delimited JSON over TCP

Date: 2026-10-24
Status: Accepted

## Context

Operators, scripts, the test harness and later a GUI must configure, start, stop and
monitor an acquisition. The control plane is low-rate (a few requests per second) and must
never compete with the acquisition threads. It must be versioned so that clients and server
can be upgraded separately, it must be scriptable and easy to inspect during debugging, and
every dependency we add is SOUP that we must qualify and maintain (Chapter 14). The first
deployment is a single PC; remote access and authentication come with the cybersecurity work
of Chapter 17.

A second question is who owns an acquisition. If the run belongs to the client session that
started it, a crashed GUI, a closed laptop or a network hiccup stops a patient scan.

## Options

1. **gRPC** (HTTP/2 + Protocol Buffers). Typed schema with generated clients, streaming,
   deadlines, TLS. Brings a large dependency tree (gRPC, protobuf, abseil, and their build
   systems), and requests are not readable without tools.
2. **REST/JSON over HTTP.** Universal tooling (curl, browsers), but needs an HTTP server
   library, and monitoring by polling is all it offers without additions such as
   server-sent events.
3. **ZeroMQ** (REQ/REP plus PUB for telemetry). Messaging patterns, reconnection and framing
   for free; one more C library to qualify, and its patterns have sharp edges (a REQ socket
   that loses a reply is stuck until it is recreated).
4. **Newline-delimited JSON (NDJSON) over plain TCP.** One request per line, one response
   per line. No dependency beyond the JSON library we already use for configuration
   (ADR 0004); testable with `nc`; we must write the framing and the server loop ourselves.

## Decision

Option 4, with these rules:

- Every response carries `"api": "MAJOR.MINOR"` (`1.0` at this decision; `1.1` since [ADR 0013](0013-versioned-status-fields.md)), and clients should send it in
  every request. A request with a different major version is refused with
  `unsupported_api`; a request without `api` is read as the server's own version. Within a major version, new
  commands and new fields are added only in minor versions, and unknown fields are ignored,
  so an older server tolerates a newer client and the reverse.
- A request's `"id"` is echoed unchanged. Errors are `{"code", "message"}` with a fixed set
  of codes (`bad_request`, `unsupported_api`, `unknown_command`, `illegal_transition`,
  `config_error`, `device_error`, `busy`).
- Requests are limited to 64 KiB; a longer line closes the connection, since the stream
  cannot be resynchronized safely.
- The server binds to 127.0.0.1 by default and serves at most 8 clients from one thread.
- **The acquisition belongs to the service, not to a connection.** A client that
  disconnects is recorded in the audit trail and changes nothing else; any client can stop
  the run. Stopping on disconnect would be a separate, explicit feature (a lease with a
  heartbeat) if a risk analysis ever asks for it.

The message layer (`handle_request`) is independent of the transport, so moving to gRPC or
HTTP later replaces the server, not the service or the protocol tests.

## Consequences

### Positive

- No new SOUP; the protocol is readable in logs and with `nc localhost 7700`.
- Clients in any language are a few lines of code (MiniDAQ's own `minidaq_ctl` is one).
- A control client crash cannot stop or corrupt an acquisition.

### Negative

- No schema-generated client types: compatibility is enforced by tests and review, not by
  a compiler.
- No authentication or encryption yet; binding to another interface is a deliberate,
  documented configuration change until Chapter 17.
- We own the framing and server code (and its fuzzing, Chapter 7), and telemetry is polled
  through `status` rather than streamed.
