# MiniDAQ software requirements specification

Version 5 (MiniDAQ 0.3.0-dev, Chapter 17). Status: draft for review.

This document states what MiniDAQ's software shall do, one testable requirement per row. It
follows the content that IEC 62304 expects of software requirements (functional and
performance requirements, inputs and outputs, interfaces, alarms and faults, security, data
definitions, and requirements that implement risk controls) for a teaching project. It is not
a document of the manufacturer's quality management system and does not reproduce the standard.

## 1. How to read this document

- **ID** is permanent. A withdrawn requirement keeps its ID with the text "Withdrawn"; an ID
  is never reused. Test code names the requirement it verifies with a comment
  `// REQ: SRS-AREA-nnn` (or `# REQ:` in Python).
- **Item** is the software item that implements the requirement, as named in the
  [architecture description](../architecture/architecture.md#4-software-items-and-layers).
- **Method** is how the requirement is verified: T (test), A (analysis), I (inspection),
  D (demonstration), M (measurement). A requirement verified other than by test names its
  evidence in [section 3](#3-verification-other-than-test).
- The [trace matrix](trace-matrix.md) is generated from this file and the tags in the tests by
  `tools/trace_matrix.py`. The test `docs.trace` fails if a T requirement has no test, a test names a
  requirement that does not exist, or the committed matrix is out of date. The test
  `docs.srs` runs `tools/req_lint.py` on this file.
- Numbers marked as assumptions in the [performance budget](../performance-budget.md) are
  book-level numbers (assumption: confirm with team); the product's numbers come from the
  system requirements of the scanner.
- Requirements that implement a risk control are listed with their controls in the trace
  matrix, from the [hazard analysis](risk/hazards.json) (Chapter 15).

## 2. Requirements

### 2.1 Core types (CORE)

| ID | Requirement | Item | Method |
|---|---|---|---|
| SRS-CORE-001 | The core types shall represent times as integer picoseconds and energies in keV as distinct types, so that adding a time to an energy does not compile and arithmetic within one unit is exact. | core | T |

### 2.2 Data formats (FMT)

| ID | Requirement | Item | Method |
|---|---|---|---|
| SRS-FMT-001 | The raw single format shall store a single in 16 bytes from which the parser restores the time, crystal and energy unchanged. | format | T |
| SRS-FMT-002 | The raw single parser shall reject a record that is shorter than 16 bytes, has a negative time, a crystal outside the scanner, or an energy that is not finite or outside 0 to 2000 keV, and return the reason. | format | T |
| SRS-FMT-010 | The packed single format MDQ-P1 shall pack crystal, energy code and time code into 64 bits without overlapping fields. | format | T |
| SRS-FMT-011 | The packed single codec shall restore the crystal exactly and the time and energy within one quantization step of their codes. | format | T |
| SRS-FMT-012 | The time unwrapper shall reconstruct the full time across any number of wraps of the time code, provided consecutive singles are less than half a wrap period apart. | format | T |
| SRS-FMT-013 | The packed single decoder shall count and drop every word whose crystal ID is outside the scanner. | format | T |

### 2.3 Readout link (RDO)

| ID | Requirement | Item | Method |
|---|---|---|---|
| SRS-RDO-001 | The MDQ-R1 packet codec shall encode and decode the header fields and the payload words of a readout packet unchanged, in little-endian byte order. | format | T |
| SRS-RDO-002 | The MDQ-R1 packet decoder shall reject every datagram that is too short or has a wrong magic number, version, flags, word count, length or reserved field, and return the reason. | format | T |
| SRS-RDO-003 | The sequence tracker shall compute the distance between packet sequence numbers modulo 2^32 packets, so that ordering is correct across the wrap of the counter. | readout | T |
| SRS-RDO-004 | The sequence tracker shall deliver packets in sequence order, holding at most the configured reorder window of packets. | readout | T |
| SRS-RDO-005 | When a gap in the sequence lasts longer than the configured hold time or exceeds the reorder window, the sequence tracker shall declare the missing packets lost, count them, deliver the packets that follow, and count and discard duplicates. | readout | T |
| SRS-RDO-006 | When the sequence jumps beyond the maximum gap, or a run of consecutive packets is stale relative to the delivered sequence, the sequence tracker shall resynchronize to the new numbering and count the resynchronization instead of counting the jump as loss. | readout | T |
| SRS-RDO-007 | When the link loses, reorders and duplicates packets, the sequence tracker shall deliver the words in order, declare lost exactly the packets that were lost, and count every duplicate as stale. | readout | T |
| SRS-RDO-010 | The UDP detector adapter shall refuse an address that is not a numeric IPv4 address and report the port it bound. | readout | T |
| SRS-RDO-011 | The UDP detector adapter shall deliver the words of the packets in sequence order and count every rejected datagram by reason and every lost packet. | readout | T |
| SRS-RDO-012 | When the configuration selects the UDP source, the acquisition service shall acquire from the network, report the link counters in its status, and release the previous run's port before it opens the next run's. | service | T |

### 2.4 Pipeline (PIPE)

| ID | Requirement | Item | Method |
|---|---|---|---|
| SRS-PIPE-001 | The single-producer single-consumer ring shall deliver items in the order they were pushed and report full and empty correctly. | pipeline | T |
| SRS-PIPE-002 | The single-producer single-consumer ring shall deliver every item exactly once when producer and consumer run on different threads. | pipeline | T |
| SRS-PIPE-003 | The multi-producer multi-consumer queue shall deliver every item exactly once with four producers and two consumers. | pipeline | T |
| SRS-PIPE-004 | The batch channel shall deliver every batch published before it was closed, even when the consumer observes the close before the last batch. | pipeline | T |
| SRS-PIPE-010 | The acquisition pipeline shall produce the same coincidences as the single-threaded reference implementation for the same input. | pipeline | T |
| SRS-PIPE-011 | When a downstream stage cannot keep up, the acquisition pipeline shall drop data only at the source, by the configured overflow policy, and count every dropped word. | pipeline | T |
| SRS-PIPE-012 | When a stop is requested, the acquisition pipeline shall process all data already read by the source before its stages finish. | pipeline | T |

### 2.5 Real-time behavior (RT)

| ID | Requirement | Item | Method |
|---|---|---|---|
| SRS-RT-001 | The real-time profile reader shall parse every key of a profile (CPU, policy, priority, memory locking, stack prefaulting) and reject unknown keys and invalid values with their line number. | rt | T |
| SRS-RT-002 | The real-time support shall pin the calling thread to a requested CPU and report an error when the CPU is not available. | rt | T |
| SRS-RT-003 | The real-time support shall prefault the stack of a thread, so that touching the prefaulted region causes no further page faults. | rt | T |
| SRS-RT-010 | The acquisition pipeline shall record the latency of each stage and from source to writer in histograms that any thread can read during the run. | pipeline | T |
| SRS-RT-011 | The acquisition pipeline shall apply the real-time profile to its stage threads before `start()` returns and report the settings that were granted. | pipeline | T |
| SRS-RT-012 | When the source reports when its data was due, the acquisition pipeline shall measure end-to-end latency from that time, not from when the data was read. | pipeline | T |

### 2.6 Performance (PERF)

| ID | Requirement | Item | Method |
|---|---|---|---|
| SRS-PERF-001 | The stream decoder shall not allocate memory after it has been constructed. | pipeline | T |
| SRS-PERF-010 | The latency histogram shall report every percentile within a relative error of 1/128 of the value, and never below the exact value. | metrics | T |
| SRS-PERF-020 | The acquisition pipeline shall sustain 10,000,000 singles/s with a margin of at least 2 times on the reference machine with the `hardened` preset. | pipeline | M |
| SRS-PERF-021 | The list-mode sink shall sustain at least 3,000,000 coincidences/s with the `close` fsync policy on the reference machine. | output | M |

### 2.7 Processing (PROC, SRT, MRG, SNO, CNT)

| ID | Requirement | Item | Method |
|---|---|---|---|
| SRS-PROC-001 | The energy filter shall give the same result as the reference loop for every kernel and every batch size, including sizes that are not a multiple of the vector width. | processing | T |
| SRS-SRT-001 | The coincidence sorter shall pair two singles whose time difference is less than or equal to the coincidence window, and report the earlier single first. | sorter | T |
| SRS-SRT-002 | The coincidence sorter shall support a fixed window, opened by the first single and not extended, and a window per single, as configured. | sorter | T |
| SRS-SRT-003 | The coincidence sorter shall resolve windows with more than two singles by the configured multiples policy: kill all, take all good pairs, take the good pair with the highest summed energy, or keep the good pair only if it is the only one. | sorter | T |
| SRS-SRT-004 | The coincidence sorter shall reject a pair whose crystals are fewer than the configured minimum of sectors apart, or whose line of response passes outside the configured field-of-view radius in mm. | sorter | T |
| SRS-SRT-005 | The coincidence sorter shall pass only singles inside the inclusive energy window in keV, and count singles that arrive out of time order and drop them. | sorter | T |
| SRS-SRT-006 | When a nonzero delay is configured, the coincidence sorter shall form delayed coincidences from a second window opened at the configured delay in ps after each opening single, using the same window width and multiples policy as the prompt window. | sorter | T |
| SRS-SRT-007 | The coincidence sorter shall reject a configuration with a window outside 1 to 1,000,000 ps, a nonzero delay that does not exceed the window, an energy window that is empty or not finite, a sector difference above 12 sectors, or a field-of-view radius that is not inside the ring. | sorter | T |
| SRS-SRT-008 | The coincidence sorter shall produce the same coincidences whatever the sizes of the batches it receives. | sorter | T |
| SRS-SRT-009 | The coincidence sorter's counters shall account for every single it receives: rejected by energy, out of order, alone, or in a window of a counted size. | sorter | T |
| SRS-SRT-010 | When configured like the simulator's reference counter, the coincidence sorter shall find exactly the prompts that the reference counter finds in the simulator's ground truth. | sorter | T |
| SRS-SRT-011 | The coincidence sorter's delayed window shall estimate the randoms among the prompts to within 15% at 40 MBq. | sorter | T |
| SRS-SRT-012 | When the take-winner-of-goods policy finds good pairs with equal summed energy, the coincidence sorter shall keep the pair with the earliest first single, and among those the earliest second single. | sorter | T |
| SRS-MRG-001 | The stream merger shall merge the time-ordered streams of several boards into one time-ordered stream, whatever the sizes of the chunks it receives. | merger | T |
| SRS-MRG-002 | The stream merger shall release a single only when every board has delivered a later single or a time marker. | merger | T |
| SRS-MRG-003 | When one board falls behind the others by more than the configured maximum skew in µs, the stream merger shall drop and count only that board's late singles. | merger | T |
| SRS-MRG-004 | The stream merger shall count and drop a single that is earlier than one its board already delivered or promised, and refuse a configuration with zero boards. | merger | T |
| SRS-MRG-005 | The stream merger shall release singles with equal times from different boards in an order fixed by the singles' time order and then by board. | merger | T |
| SRS-SNO-001 | The sinogram histogrammer shall give every transaxial line of response its own bin, at the radial position and angle of that line. | processing | T |
| SRS-SNO-002 | The sinogram histogrammer shall accept exactly the lines of response that the coincidence sorter's field-of-view cut accepts. | processing | T |
| SRS-SNO-003 | The sinogram histogrammer shall sort ring pairs into single-slice rebinning slices and a michelogram, and reject ring differences above the configured maximum. | processing | T |
| SRS-SNO-004 | The sinogram histogrammer shall place time-of-flight bins along the line of response from the time difference, and subtract the delay from delayed coincidences. | processing | T |
| SRS-SNO-005 | The sinogram histogrammer shall draw a point source as a sinusoid whose amplitude in mm is the source's distance from the axis. | processing | T |
| SRS-CNT-001 | The count-rate calculator shall compute prompts, the scatter fraction and the noise-equivalent count rate from the trues, scatters and randoms rates. | processing | T |

### 2.8 Simulation and replay (SIM, DTM)

These requirements belong to items that produce test data. They are part of the shipped
server today (section 4 of the architecture description explains the consequence).

| ID | Requirement | Item | Method |
|---|---|---|---|
| SRS-SIM-002 | The paced source shall never deliver a word before the time it is due. | sim | T |
| SRS-SIM-003 | The paced source shall give each word a due time that follows its configured rate from the moment of the first read. | sim | T |
| SRS-SIM-004 | The paced source shall report the words that are due but not yet read as its backlog. | sim | T |
| SRS-SIM-010 | The physics model shall compute the energy of a Compton-scattered photon from its angle within 0.000000001 keV of the Compton formula. | sim | T |
| SRS-SIM-011 | The physics model shall give the linear attenuation coefficient of water at 511 keV as 0.0096 per mm within 0.0001 per mm. | sim | T |
| SRS-SIM-012 | The detector simulator shall reject a configuration with a source outside the ring or with any parameter that is not finite or outside its range. | sim | T |
| SRS-SIM-013 | The detector simulator shall produce the same stream from the same seed. | sim | T |
| SRS-SIM-014 | The detector simulator shall produce singles in time order with valid crystals and energies. | sim | T |
| SRS-SIM-015 | The detector simulator shall reproduce the axial acceptance of a point source at the center within 0.005 of the geometric fraction. | sim | T |
| SRS-SIM-016 | The detector simulator shall produce photopeak singles with a mean of 511 keV within 1 keV and an energy resolution of 12% FWHM within 0.3%. | sim | T |
| SRS-SIM-017 | The detector simulator shall produce true pairs whose time difference has a FWHM of 300 ps within 10 ps. | sim | T |
| SRS-SIM-018 | The detector simulator shall scatter photons in the phantom so that the scatter fraction exceeds 20% in a 100 to 1000 keV window and falls below 70% of that value in a 435 to 650 keV window. | sim | T |
| SRS-SIM-019 | The detector simulator shall produce trues that grow linearly and randoms that grow with the square of the activity. | sim | T |
| SRS-SIM-020 | The replay source shall loop over a recording with times shifted by the recording's length, so that its output stays in time order. | sim | T |
| SRS-SIM-021 | The replay source shall replay a recording at its real-time rate or at a configured rate in words/s, paced like the paced source. | sim | T |
| SRS-DTM-001 | The non-paralyzable dead-time model shall lose every single that arrives while its unit is busy, without extending the dead time. | sim | T |
| SRS-DTM-002 | The paralyzable dead-time model shall restart the dead time with every arrival, recorded or lost. | sim | T |
| SRS-DTM-003 | When pile-up is enabled, the dead-time model shall add the energy of a lost single to the recorded single that made the unit busy. | sim | T |
| SRS-DTM-004 | The dead-time model shall keep one independent dead time per block or per crystal, as configured. | sim | T |
| SRS-DTM-005 | The dead-time model shall produce its output in time order whatever the sizes of the chunks it receives. | sim | T |
| SRS-DTM-006 | The dead-time model's recorded rates shall agree with the analytical non-paralyzable and paralyzable formulas within 1%. | sim | T |
| SRS-DTM-007 | The dead-time correction shall return the true rate from a recorded rate for both models, and report that no true rate exists above the paralyzable maximum. | sim | T |
| SRS-DTM-008 | The dead-time model shall reject a dead time that is not positive or longer than 100 µs, and an unknown model name. | sim | T |

### 2.9 Configuration (CFG)

| ID | Requirement | Item | Method |
|---|---|---|---|
| SRS-CFG-001 | The configuration reader shall give every key that a document omits its documented default, and accept every older minor schema version of the same major version. | config | T |
| SRS-CFG-002 | The configuration reader shall reject a document without a schema version, with another major version, with a newer minor version, or with a version that is not a string of the form MAJOR.MINOR. | config | T |
| SRS-CFG-003 | The configuration reader shall reject every unknown key, with a suggestion when a known key is close to it. | config | T |
| SRS-CFG-004 | The configuration reader shall report every type and range error of a document at once, each with the JSON Pointer of the value. | config | T |
| SRS-CFG-010 | The configuration reader shall read the UDP source settings and reject a port number above `65535`, a reorder window that is not a power of two, and a run duration for a non-synthetic source. | config | T |
| SRS-CFG-011 | The configuration reader shall accept only sorter settings that form a valid coincidence sorter configuration, and apply them to the sorter. | config | T |
| SRS-CFG-012 | The configuration reader shall read the output settings, select no output when the section is absent, and reject an unknown fsync policy, a prefix containing '/', and an empty directory. | config | T |

### 2.10 Control (CTL)

| ID | Requirement | Item | Method |
|---|---|---|---|
| SRS-CTL-001 | The acquisition service shall reject a command that is illegal in the current state with the error code `illegal_transition`, leave the state unchanged, and record the rejection in the audit trail. | service | T |
| SRS-CTL-002 | The acquisition state machine shall make every state reachable from idle and lead from every other state to the fault state on the `error` event. | service | T |
| SRS-CTL-010 | The acquisition service shall run an acquisition from configure through start and stop back to configured, with stage counters that account for every word read. | service | T |
| SRS-CTL-011 | When a port reports a fault, the acquisition service shall stop the run, enter the fault state, report the fault in its status, and accept only `reset` until the fault is cleared. | service | T |
| SRS-CTL-012 | When the sort stage counts singles that arrived out of time order, the acquisition service shall end the run in the fault state and report the number of late singles. | service | T |
| SRS-CTL-013 | When the sink cannot make a run durable at its close, the acquisition service shall end the run in the fault state instead of reporting a clean stop. | service | T |
| SRS-CTL-020 | The control protocol shall answer every command with `ok`, the state and the request's `id` unchanged, and give errors a code from the protocol's list with details. | protocol | T |
| SRS-CTL-021 | The control server shall answer a request longer than the 64 KiB limit with an error, close only that connection, and keep serving other clients. | protocol | T |
| SRS-CTL-022 | The control protocol shall reject another major API version, malformed JSON, invalid UTF-8 and requests without a command, and accept newer minor versions and unknown fields. | protocol | T |
| SRS-CTL-023 | When a control client disconnects during a run, the acquisition service shall continue the run. | protocol | T |
| SRS-CTL-030 | The acquisition service shall report in its status whether the run's data is complete, list every nonzero loss counter, and report a run with a fault as incomplete. | service | T |
| SRS-CTL-031 | When a run ends without a fault but with a nonzero loss counter, the acquisition service shall record every nonzero loss counter in the audit trail. | service | T |
| SRS-CTL-032 | The control server shall record every configure, start, stop and reset command, accepted or rejected, in the audit trail with the client's address and port. | protocol | T |
| SRS-CTL-033 | The control server's status shall have exactly the top-level fields that its API version defines, each field marked as always present in every status. | protocol | T |
| SRS-CTL-034 | The control protocol shall answer every request that is one JSON object with one response line, whatever the type of each of its fields, and keep serving other requests. | protocol | T |

### 2.11 List-mode format (LMF)

| ID | Requirement | Item | Method |
|---|---|---|---|
| SRS-LMF-001 | The CRC-32 implementation shall compute the IEEE 802.3 CRC-32, with the check value 0xCBF43926 for "123456789", for every length, alignment and split of its input. | core | T |
| SRS-LMF-002 | The CRC-32 implementation shall detect every single-bit and double-bit error in a 256-byte block and every burst error of up to 32 bits. | core | T |
| SRS-LMF-003 | The MDQ-L1 codec shall restore a file header's metadata exactly, pad the header to a multiple of 8 bytes, and reject a header with any changed byte or an unknown major version. | format | T |
| SRS-LMF-004 | The MDQ-L1 codec shall store coincidences and tags in one record stream and restore every field exactly, except energies, which it restores within their quantum of 1/32 keV. | format | T |
| SRS-LMF-005 | The MDQ-L1 block writer shall close a block when it is full, when a record's time is 2^32 ps or more after the block's first, or when a record is earlier than the previous one. | format | T |
| SRS-LMF-006 | The MDQ-L1 reader shall return every record of an intact file, lose only the damaged block when a byte is changed, and resynchronize after a damaged block header. | format | T |
| SRS-LMF-007 | The MDQ-L1 reader shall read a truncated file up to its last complete block and report the truncation, and stop at a damaged file header. | format | T |
| SRS-LMF-008 | The MDQ-L1 reader shall read a file written from the specification by an independent implementation. | format | T |

### 2.12 Output (OUT)

| ID | Requirement | Item | Method |
|---|---|---|---|
| SRS-OUT-001 | The list-mode sink shall write every coincidence it receives and, at the close of a run, give each file its final name. | output | T |
| SRS-OUT-002 | The list-mode sink shall start a new file so that no file exceeds the configured size, end each file with a closing block, and lose or repeat no coincidence at a file boundary. | output | T |
| SRS-OUT-003 | The list-mode sink shall make each file durable (fsync of the file, rename without replacing, fsync of the directory) before the file has its final name, for every fsync policy. | output | T |
| SRS-OUT-004 | The list-mode sink shall complete short writes. | output | T |
| SRS-OUT-005 | When a write fails, the list-mode sink shall report a fault with the system's error message, keep the file's `.part` name, and return its buffers to the writer. | output | T |
| SRS-OUT-006 | When the disk is slower than the data, the list-mode sink shall make the writer wait for a free buffer instead of dropping data. | output | T |
| SRS-OUT-007 | The list-mode sink shall write a partly filled block at the latest after the configured maximum block delay in ms. | output | T |
| SRS-OUT-008 | The list-mode sink shall refuse to open with an empty run name, a file size smaller than one block, or a file that already exists. | output | T |
| SRS-OUT-009 | When the configuration selects list-mode output, the acquisition service shall write real files that the reader reads back completely. | output | T |
| SRS-OUT-010 | The list-mode sink shall store the run record, the service's final status, next to the run's files. | output | T |
| SRS-OUT-011 | The list-mode sink shall store the run's integrity verdict in the run record. | output | T |
| SRS-OUT-012 | The list-mode sink shall state in every file's metadata whether its data is simulated, and the effective configuration with its defaults. | output | T |

### 2.13 Security (SEC)

The control API's security requirements (Chapter 17), from the threat model
([threat-model.md](security/threat-model.md)); they implement risk controls RC-21 to RC-24 of hazard H-08.

| ID | Requirement | Item | Method |
|---|---|---|---|
| SRS-SEC-001 | The control server shall refuse every command except `hello` and `auth`, with the error code `unauthenticated`, on a connection that has not authenticated with a valid token. | protocol | T |
| SRS-SEC-002 | The control server shall close a connection after an `auth` with an unknown token, and record the refusal in the audit trail with the client's address and without the token. | protocol | T |
| SRS-SEC-003 | The control server shall allow a client with the observer role only `hello`, `auth` and `status`, refuse other commands with the error code `forbidden`, and record each refusal in the audit trail. | protocol | T |
| SRS-SEC-004 | The control server shall close a connection that has not completed the TLS handshake and authenticated within the authentication deadline, 10 s by default. | protocol | T |
| SRS-SEC-005 | The control server shall refuse to start without a token store unless authentication is turned off explicitly, or on an address outside `127.0.0.0/8` without both TLS and a token store. | protocol | T |
| SRS-SEC-006 | When TLS is configured, the control server shall accept only `TLS 1.3` connections and answer no client that does not complete the handshake. | access | T |
| SRS-SEC-007 | The control client shall verify the server's certificate against the CA it trusts and against the name or address it connected to before it sends a token. | access | T |
| SRS-SEC-008 | The token store shall keep only the SHA-256 hashes of tokens and refuse a token file that is a symbolic link, belongs to another user, or is writable by another user. | access | T |
| SRS-SEC-009 | The server shall make its start-up token from 256 bits of the operating system's random generator and write it to a file that only its user can read, in a directory that only its user can use. | access | T |

## 3. Verification other than test

| ID | Method | Evidence |
|---|---|---|
| SRS-PERF-020 | M | [Performance budget](../performance-budget.md): whole pipeline 11.6 ns per single (86 M words/s), margin 8.6 times at 10 M singles/s; hardened builds within noise (`measurements/ch07/`). Re-measure on the acquisition PC. |
| SRS-PERF-021 | M | [Performance budget](../performance-budget.md), list-mode writer section: about 19 M coincidences/s with fsync on the reference machine (`measurements/ch12/`), against the 2.7 M coincidences/s that the pair stage produces at 70 M singles/s. |

## 4. Changes

| Version | Change |
|---|---|
| 1 | First version (Chapter 14), from the requirement tags of Chapters 1 to 12. Added SRS-CFG-004, SRS-PERF-020 and SRS-PERF-021, which had tests or measurements without an ID. |
| 2 | Chapter 15: requirements of the risk controls for silent data loss and for the audit of control actions (SRS-CTL-030 to SRS-CTL-032, SRS-OUT-011, SRS-OUT-012), SRS-FMT-013, a counter the integrity verdict relies on, and SRS-SRT-012, a gap found by the sorter's FMEA. |
| 3 | Chapter 16: SRS-CTL-033, the status fields of API 1.1 (ADR 0013, CR-0003, problem report MDQ-PR-012). |
| 4 | Chapter 17: security requirements SRS-SEC-001 to SRS-SEC-009, from the threat model (ADR 0014, CR-0004, problem report MDQ-PR-008). |
| 5 | Part III review: SRS-CTL-034, after an `auth` whose token was a number ended the server (problem report MDQ-PR-013, CAPA-0003). |
