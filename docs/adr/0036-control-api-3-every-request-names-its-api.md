# 0036. Control API 3.0: renamed fields, and every request names its API

Date: 2026-11-16
Status: Accepted

## Context

ADR 0003 made the control protocol versioned: every response carries the server's `api`, a
request with another major version is refused, and new fields come only with minor versions.
A request was allowed to leave `api` out, and then the server answered it as if it were
current. Since 1.0 the status has gained names that make a reader stop and guess
(`hardware.describe`, a verb among nouns; each board's `temperature`, which is a level beside
`temperature_c`; `sorter`, a counter group without the suffix of `detector_counters` and
`sink_counters`), and the acquisition configuration has the same kind of names (CR-0030). Each
could be fixed in a minor version only with an alias kept forever. The roadmap holds them for
2.0.0, so that they change once.

A rename is a major change, and a major change is safe only if an old client finds out. One
that names `"api": "2.5"` is refused. One that names no version is not: it would read the
status of 3.0, miss `sorter` and `describe`, and take their absence for zeros or for "no
hardware".

## Options

1. **Rename in 3.0; a request without `api` keeps being answered.** The old client that left
   `api` out reads renamed fields without noticing.
2. **Rename in 3.0, and refuse a request without `api`** (`unsupported_api`, with a message
   that names the migration note).
3. **Keep the old names as aliases beside the new ones.** No client breaks; every status
   carries both names for good, and the book teaches both.
4. **Do not rename.**

## Decision

Option 2. Control API 3.0 renames `status.hardware.describe` to `description`, each board's
`temperature` to `temperature_level` and `status.sorter` to `sorter_counters`, and every
request must carry `"api"` with major version 3: a request without it, or with another major
version, is refused with `unsupported_api` and the message "this server speaks API 3.0 and
every request names it ("api"); see docs/migration-2.0.md". Newer minor versions and unknown
fields stay accepted (ADR 0003). The same release moves the acquisition configuration to
schema 2.0, which refuses a 1.x file with a message that names `tools/migrate_config.py`.

## Consequences

### Positive

- A client of 2.x, whether it named its version or not, is refused at its first request, with
  the place to read what changed, instead of reading a status that lacks the fields it expects.
- The status's names are consistent and carry their meaning; the book teaches them without
  footnotes.
- `minidaq_ctl` and every test client name the version; the clients written for this book
  show the rule in every listing, and `tools/check_interfaces.py` keeps the book and the
  exercises free of old requests.

### Negative

- Every client must change, including scripts that sent requests by hand without `api`; the
  migration note lists every rename.
- A quick test with `nc` needs `"api": "3.0"` in each line.
