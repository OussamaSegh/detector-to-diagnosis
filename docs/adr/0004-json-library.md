# 0004. JSON library for the control plane

Date: 2026-10-24
Status: Accepted

## Context

Configuration files (Chapter 6) and the control protocol (ADR 0003) are JSON. Parsing JSON
by hand is a classic source of security defects, so we use a library, which makes it SOUP:
it must be identified by exact version, its anomalies reviewed, and it must be kept out of
the hot path, where neither its allocations nor its exceptions are acceptable. Throughput is
not a concern: documents are kilobytes, a few per second.

## Options

1. **nlohmann/json.** Header-only, MIT license, a widely used and heavily tested library
   with an expressive API; allocates freely and reports errors with exceptions.
2. **RapidJSON or simdjson.** Much faster parsers; APIs are lower-level, and their speed
   buys nothing at control-plane rates.
3. **Boost.JSON.** Good performance and allocator control, but pulls in part of Boost.
4. **A hand-written parser.** No dependency, and a large, permanently owned attack surface.

## Decision

nlohmann/json, pinned to v3.11.3 and fetched by URL with a SHA-256 hash (or found with
`find_package(nlohmann_json 3.11)` when `MINIDAQ_USE_SYSTEM_DEPS` is on). It is linked only
by `minidaq_control` and the control applications, never by `minidaq_core`, so the build
itself enforces that the hot path does not depend on it. All parsing goes through
functions that catch the library's exceptions and return errors as values
(`parse_config`, `handle_request`).

## Consequences

### Positive

- Readable configuration and protocol code; one dependency for both uses.
- The core library stays free of JSON, allocations from parsing and exceptions.

### Negative

- Exceptions inside the control plane must be caught at its boundary; a missed one would
  terminate the server, so the parsers are fuzzed (Chapter 7).
- Heavy templates increase compile time of the files that include it; include
  `<nlohmann/json_fwd.hpp>` in headers.
- Another SOUP item to track in the SOUP list and the SBOM (Chapters 7 and 14).
