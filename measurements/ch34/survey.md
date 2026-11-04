# Codebase survey (history since 2026-10-01)

128 product source files.

## Software items

| Item | Class | Hazards | Files | Code lines | Commits | Changed lines | Requirements (by test, tagged) | Problem reports (open) |
|---|---|---|---:|---:|---:|---:|---:|---:|
| service | B | HZ-1, HZ-2, HZ-3 | 11 | 873 | 38 | 1,370 | 26 (25, 25) | 2 (1) |
| sim | B | HZ-3 | 13 | 947 | 24 | 1,478 | 26 (26, 26) | 3 (1) |
| sorter | B | HZ-1 | 2 | 310 | 11 | 481 | 13 (13, 13) | 4 (1) |
| hw | B | HZ-1, HZ-2 | 13 | 1,303 | 34 | 1,965 | 8 (8, 8) | 2 (0) |
| pipeline | B | HZ-1, HZ-2 | 7 | 801 | 23 | 1,358 | 16 (14, 14) | 1 (0) |
| core | B | HZ-1 | 16 | 762 | 21 | 1,208 | 5 (4, 4) | 0 (0) |
| protocol | B | HZ-2, HZ-4 | 4 | 532 | 21 | 1,023 | 13 (13, 13) | 3 (0) |
| config | B | HZ-3 | 5 | 597 | 16 | 1,143 | 9 (9, 9) | 3 (0) |
| readout | B | HZ-1 | 6 | 594 | 16 | 867 | 10 (10, 10) | 3 (0) |
| format | B | HZ-1 | 8 | 881 | 14 | 1,415 | 14 (14, 14) | 0 (0) |
| processing | B | HZ-1 | 9 | 748 | 13 | 1,173 | 7 (7, 7) | 0 (0) |
| output | B | HZ-1, HZ-3 | 4 | 579 | 11 | 830 | 15 (14, 14) | 0 (0) |
| server | B | HZ-2 | 1 | 210 | 8 | 333 | 2 (2, 2) | 0 (0) |
| rt | B | HZ-2 | 6 | 526 | 7 | 775 | 4 (4, 4) | 0 (0) |
| access | B | HZ-4 | 4 | 474 | 5 | 653 | 4 (4, 4) | 0 (0) |
| ctl | B | HZ-4 | 1 | 265 | 5 | 407 | 3 (3, 3) | 1 (0) |
| update | B | HZ-2, HZ-4 | 5 | 810 | 5 | 1,057 | 7 (7, 7) | 0 (0) |
| audit | B | - | 2 | 51 | 4 | 132 | 0 (0, 0) | 0 (0) |
| metrics | B | - | 2 | 208 | 3 | 302 | 1 (1, 1) | 0 (0) |
| merger | B | HZ-1 | 2 | 166 | 2 | 238 | 5 (5, 5) | 0 (0) |
| platform | B | HZ-2 | 2 | 144 | 2 | 235 | 4 (2, 2) | 1 (0) |
| tools | - | - | 5 | 1,108 | 18 | 1,493 | 27 (25, 25) | 12 (0) |

## Hotspots: commits times code lines

| File | Item | Commits | Code lines | Score |
|---|---|---:|---:|---:|
| `minidaq/src/control/acquisition_service.cpp` | service | 13 | 500 | 6,500 |
| `minidaq/apps/minidaq_sim.cpp` | tools | 9 | 476 | 4,284 |
| `minidaq/src/pipeline/acquisition_pipeline.cpp` | pipeline | 8 | 429 | 3,432 |
| `minidaq/src/control/listmode_sink.cpp` | output | 6 | 413 | 2,478 |
| `minidaq/src/hw/slow_control.cpp` | hw | 5 | 352 | 1,760 |
| `minidaq/src/config/acquisition_config.cpp` | config | 8 | 214 | 1,712 |
| `minidaq/apps/minidaq_server.cpp` | server | 8 | 210 | 1,680 |
| `minidaq/src/processing/coincidence_sorter.cpp` | sorter | 6 | 242 | 1,452 |
| `minidaq/src/control/control_server.cpp` | protocol | 5 | 270 | 1,350 |
| `minidaq/apps/minidaq_ctl.cpp` | ctl | 5 | 265 | 1,325 |

## The item map

Files no item claims: none.
Files two items claim (the first, by the longest prefix, owns them): `minidaq/include/minidaq/config/hardware_config.hpp` (hw, config), `minidaq/src/config/hardware_config.cpp` (hw, config).
Prefixes that claim no file: none.
Items with a requirement to be tested that no test names: none.
