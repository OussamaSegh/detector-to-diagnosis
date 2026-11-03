# MiniDAQ calibration table, version 1.0

Version 1 of this specification (MiniDAQ 0.6.0-dev), for schema version 1.0.
Status: Accepted (ADR 0021). Implementation: `minidaq/include/minidaq/processing/calibration.hpp`
and `minidaq/include/minidaq/config/calibration_file.hpp` (the reader, C++), `tools/calib/table.py`
(the writer, Python). Requirements: SRS-CAL-001 to 007.

The words MUST, MUST NOT, SHOULD and MAY are used as in RFC 2119.

## 1. Purpose and scope

A calibration table holds, for each crystal of one scanner, the curve from the energy code that
the front-end board reports to an energy in keV, and the delay of the crystal's timing channel.
The calibration procedure (`python3 -m tools.calib`, Chapter 26) writes it from a calibration
acquisition; `minidaq_server` reads it when an acquisition is configured with it and applies it
to every single. A table belongs to one scanner, identified by its serial number, and is valid
for a limited time.

## 2. Encoding

A table is one JSON document (RFC 8259) in UTF-8, at most 8 MiB. Every key below is required, and
a reader MUST refuse a document with a key that this specification does not define, at any level.

| Key | Type | Meaning |
|---|---|---|
| `schema_version` | string | `"1.0"`. A reader of version 1.x MUST refuse another major version and a minor version newer than its own. |
| `id` | string, not empty | The table's identifier, for example `CAL-0002`. |
| `version` | integer, 1 to 4294967295 | One more than the previous table of the same scanner. |
| `scanner_serial` | string, not empty | The serial number of the scanner the table was made for. |
| `created_utc` | string | When the table was made: `YYYY-MM-DDTHH:MM:SSZ`. |
| `valid_until_utc` | string | When it expires, in the same form. A reader MUST refuse an expired table. |
| `reference_temperature_c` | number, -40 to 125 | The detector temperature during the calibration acquisition. |
| `procedure` | string, not empty | The procedure and its version, for example `CP-026 version 1`. |
| `crystals` | integer | The number of crystals: 18,432 for MiniDAQ's scanner. A reader MUST refuse another number. |
| `energy` | object | `a_kev`, `b_kev` and `q_kev`: arrays of `crystals` numbers each. |
| `time` | object | `offset_ps`: an array of `crystals` integers. |
| `crc32` | string | The CRC-32 of the coefficients (section 4), as 8 lowercase hexadecimal digits. |

Entry `i` of each array belongs to crystal `i`, the crystal number of the readout word (ring times
384 plus the transaxial index).

## 3. Meaning of the coefficients

For a single of crystal `i` with energy code `c` (0 to 2047) and time `t` in ps:

    E = a_kev[i] + b_kev[i] c + q_kev[i] c^2           (keV)
    t_corrected = t - offset_ps[i]                     (ps)

Each coefficient is a 32-bit IEEE 754 float, each offset a signed 32-bit integer: a reader converts
each number of the document to that type and MUST refuse a number that does not fit (an energy
coefficient beyond the float range, an offset beyond 32 bits, a fraction). A writer SHOULD write
each coefficient as the decimal number that is exactly its float value, so that every reader gets
the same bits.

The identity table, which changes nothing, has `a = 0`, `b = 0.5`, `q = 0` and offset 0 for every
crystal. A reader MUST refuse an entry outside what a working detector can have:

| Check | Limit |
|---|---|
| Gain, `b / 0.5 keV` | 0.5 to 2 |
| Energy at code 0, `a` | within 100 keV of 0 |
| Monotonic | `b + 2 q 2047 > 0`: the energy rises with the code up to the top |
| Curvature at the top, `q 2047 / b` | -0.4 to 1.5: a saturating SiPM bends the curve up |
| Delay, `offset_ps` | within 5,000 ps of 0 |

These limits bound a sane table; the procedure's acceptance criteria are tighter (SRS-CAL-007).

## 4. The CRC

The CRC is that of section 2 of the [MDQ-L1 specification](mdq-l1.md) (CRC-32 as in zlib) over 16
bytes per crystal, in crystal order: `a`, `b` and `q` as little-endian IEEE 754 floats and the
offset as a little-endian two's complement integer (Python: `struct.pack("<fffi", a, b, q, t)`).
It is computed over the values as converted (section 3), so it also detects a number that a
writer and a reader would round differently. A reader MUST refuse a table whose CRC differs.

The identity table's CRC is `6c696a72`.

The CRC detects damage and editing by hand. It is not a signature: anyone who can write the file
can write a matching CRC. The table's authenticity rests on who can write to the configuration
directory (threat model, Chapter 17).

## 5. Use

The acquisition configuration (schema 1.4) names the table and the scanner:

```json
"calibration": { "file": "/etc/minidaq/calibration/CAL-0002.json",
                 "scanner_serial": "MDQ-REF-0001", "drift_tolerance_percent": 2.0 }
```

The server reads the table when the acquisition is configured and refuses the configuration if
the table is refused, was made for another scanner serial or has expired (SRS-CAL-001, 004). The
status and the run record then name the table by `id`, `version`, `scanner_serial`,
`created_utc`, `valid_until_utc`, `reference_temperature_c`, `procedure` and `crc32` (SRS-CAL-005);
without a table they say `{"id": "identity"}`.

## 6. Document history

| Version | Change |
|---|---|
| 1 | First version (Chapter 26). |
