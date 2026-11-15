# 0034. Signed run records with the digests of their files, signed calibration tables and reports

Date: 2026-11-15
Status: Accepted

## Context

Every list-mode block and every calibration table carries a CRC-32, which detects damage. It does
not detect a deliberate change: whoever can write the files can change a record and recompute the
CRC. The threat model records it as two gaps (T-27 for the run's files and the QC reports, T-54
for the tables), with the remedy named: a signature, as for update bundles (ADR 0020). The
question is what to sign, with which key, and what the readers check.

## Options

1. **What to sign.** Each list-mode file with its own signature; a keyed hash (HMAC) per block;
   or the run record, which already lists the run's files, extended with each file's size and
   SHA-256.
2. **How to hash the data.** Read the files again at the end of the run; or hash each file in the
   sink while writing it.
3. **Keys.** A symmetric key (HMAC), which every verifier must hold and could then forge with; or
   an Ed25519 key pair, the private half only on the acquisition PC, the public halves wherever
   runs, tables or reports are checked.
4. **Calibration tables.** Sign them in the procedure and verify in the server always, or only
   when the site installs keys.

## Decision

- **Sign the run record** (option 1, the third): one signature vouches for the whole run, the
  data through its digests and the counters that the integrity verdict reads. A record that is
  changed, a file that is changed, missing or added to the list fails.
- **Hash while writing** (option 2, the second), in the sink's I/O thread: a run of gigabytes is
  not read twice, and the bytes hashed are the bytes written.
- **Ed25519 key pairs** (option 3, the second), as for updates: a verifier cannot sign. The key is
  read once at start-up, so a missing or wrong key stops the server instead of the first run
  ending unsigned.
- **Only when the site installs keys** (option 4, the second): without `--signing-key` or
  `--calibration-keys` MiniDAQ behaves as before, so that existing sites and tests change nothing
  until they decide how to hold the keys.
- One implementation of Ed25519 and SHA-256 in C++, `control/signing.cpp`, shared with the update
  tool; the Python tools use the `openssl` command line, so no new dependency.

## Consequences

### Positive

- A run, a table or a report changed after it was signed no longer verifies, whatever CRC it
  carries; the QC refuses a run it cannot verify instead of reporting on it.
- The cost is one SHA-256 pass over data already in memory, in the thread that writes it.

### Negative

- The private key lies on the acquisition PC, readable by the server's account. Whoever controls
  that account can sign what they like; the signature shows that MiniDAQ's account wrote the
  run, not that the account was not misused. A hardware key store would raise the bar
  (assumption: confirm with team how keys are held).
- A crash between the record and its signature leaves a run that does not verify: loud, but the
  run must then be judged by the site's procedure.
- Signing is off by default, so a site that does not configure it keeps the gap of section 7.
