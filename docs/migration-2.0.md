# Migrating to MiniDAQ 2.0

MiniDAQ 2.0 changes two interfaces once, on purpose, so that their names are consistent from
here on: the control API becomes 3.0 and the acquisition configuration becomes schema 2.0
(CR-0030, ADR 0036). Old clients and old files are refused with a message that points here;
nothing old is read with a guess. The hardware description (1.1), the calibration table (1.0),
the list-mode format MDQ-L1 and the readout formats do not change.

## Acquisition configurations: schema 1.x to 2.0

Convert a file with the migration tool, which says what it changed and checks the result
against `docs/architecture/acquisition-config.schema.json`:

```text
tools/migrate_config.py old.json -o new.json
tools/migrate_config.py old.json --in-place     # comments, which JSON lacks, are removed
tools/migrate_config.py new.json --check        # validate a file against schema 2.0
```

| 1.x | 2.0 | Why |
|---|---|---|
| `"schema_version": "1.x"` | `"schema_version": "2.0"` | A 1.x file is refused, not read with defaults (hazard H-04). |
| `source.type` optional, default `"synthetic"` | `source.type` required; `source` required | A file that forgot its source made the server invent data (hazard H-06). |
| `stop_after_s` | `source.stop_after_s` | It applies only to the synthetic source. |
| `pipeline.coincidence_window_ps` | `sorter.window_ps` | The window is the sorter's, with its delay and energy window. |
| `output.max_file_mb` | `output.max_file_mib` | The sink multiplies by 2^20; the number does not change. |
| `rt_profile` | `rt_profile_file` | Like `calibration.file` and the hardware description's `temperature_file`. |

No default changes: a converted file gives the same run. The effective configuration that
`status`, the audit trail, the run record and the list-mode metadata copy uses the new names
from 2.0 on; files and records written earlier keep the old ones.

## Control clients: API 2.x to 3.0

Every request names the API it was written for, `"api": "3.0"` (any 3.x is accepted). A request
without `api`, or with another major version, is refused:

```text
-> {"id": 1, "cmd": "status"}
<- {"api":"3.1","error":{"code":"unsupported_api","message":"this server speaks API 3.1 and
    every request names it (\"api\"); see docs/migration-2.0.md"},"id":1,"ok":false,"state":"idle"}
```

| 2.x | 3.0 |
|---|---|
| `"api"` optional in a request | `"api"` required, major version 3 |
| `status.sorter` | `status.sorter_counters` |
| `status.hardware.describe` | `status.hardware.description` |
| `status.hardware.boards[].temperature` (normal, warning, alarm) | `status.hardware.boards[].temperature_level` |
| integrity loss counter `/sorter/out_of_order` | `/sorter_counters/out_of_order` |
| `configure` with a 1.x configuration | `configure` with a 2.0 configuration |

The commands, their parameters, the error codes and the other status fields do not change.
`minidaq_ctl` of 2.0 speaks 3.1.

## Additions in 2.0 that need no migration

Minor versions add and never rename, so a client of 3.0 and a file of 2.0 work unchanged with
these (ADR 0003):

| Interface | Addition |
|---|---|
| Control API 3.1 | `status.timing`: the time base monitor's limits and its latest evaluation, each block's level and offset, the blocks at alarm (Chapter 38, CR-0031); `status.hardware.boards[].clock_locked` and `clock_lock_losses` (register map 1.3); the integrity loss counters `/timing/alarm_intervals` and `/hardware/boards/N/clock_lock_losses` |
| Configuration schema 2.1 | the optional `timing_monitor` object; a 2.0 file is read as before |
| Register map 1.3 (firmware 1.4) | `clock_status` at 0x034; boards with firmware 1.2 and 1.3 are supported as before (ICD-FEB) |
| Audit trail | the event `clock_lock_lost` |

## Command-line options

| 1.x | 2.0 |
|---|---|
| `minidaq_sim --centre X,Y,Z` | `minidaq_sim --center X,Y,Z` |
| `minidaq_sim --max-file-mb N`, `writer_throughput --max-file-mb N` | `--max-file-mib N` |

## The product build

Since 2.0 the shipped server is built without the simulator (preset `product`, CR-0029). It
refuses a configuration with `"source": {"type": "synthetic"}` and a hardware description with
simulated boards; use the developer presets for simulated runs.
