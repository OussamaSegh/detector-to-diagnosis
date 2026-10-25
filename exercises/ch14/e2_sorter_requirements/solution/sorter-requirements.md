# Coincidence sorter: software requirements (Exercise 14.2)

Item: sorter. Defaults in parentheses are MiniDAQ's (Chapter 10); a requirement states the
behavior, the configuration states the numbers.

| ID | Requirement | Item | Method |
|---|---|---|---|
| SRS-SRT-101 | The sorter shall pair two singles whose time difference is less than or equal to the configured coincidence window in ps (default 4000 ps). | sorter | T |
| SRS-SRT-102 | The sorter shall not pair two singles whose time difference exceeds the coincidence window by 1 ps or more. | sorter | T |
| SRS-SRT-103 | The sorter shall report the earlier single of a coincidence as its first single and the time difference as the later time minus the earlier. | sorter | T |
| SRS-SRT-104 | When the window mode is `fixed`, the sorter shall close a window at the opening single's time plus the window width, whatever singles arrive inside it. | sorter | T |
| SRS-SRT-105 | When the window mode is `per_single`, the sorter shall open a window at every single that passes the energy gate. | sorter | T |
| SRS-SRT-106 | When a window holds more than two singles and the multiples policy is `kill_all`, the sorter shall discard the whole window and count it by its number of singles. | sorter | T |
| SRS-SRT-107 | When a window holds more than two singles and the multiples policy is `take_all_goods`, the sorter shall output every pair of the window that passes the geometry cuts. | sorter | T |
| SRS-SRT-108 | When a window holds more than two singles and the multiples policy is `take_winner_of_goods`, the sorter shall output the good pair with the highest summed energy. | sorter | T |
| SRS-SRT-109 | The sorter shall pass to coincidence search only singles whose energy is inside the inclusive energy window in keV (default 435 to 585 keV). | sorter | T |
| SRS-SRT-110 | The sorter shall reject a pair whose crystals are fewer than the configured minimum of sectors apart, counting the 24 sectors around the ring with wraparound. | sorter | T |
| SRS-SRT-111 | When a field-of-view radius is configured, the sorter shall reject a pair whose line of response passes farther from the scanner axis than the configured field-of-view radius in mm. | sorter | T |
| SRS-SRT-112 | When a nonzero delay is configured, the sorter shall open a delayed window at the configured delay in ps after each opening single (default 100000 ps) and output its pairs as delayed coincidences. | sorter | T |
| SRS-SRT-113 | The sorter shall apply the same window width, multiples policy and geometry cuts to the delayed window as to the prompt window. | sorter | T |
| SRS-SRT-114 | The sorter shall count and drop a single that is earlier than the previous single it received. | sorter | T |
| SRS-SRT-115 | The sorter shall produce the same coincidences in the same order for every division of the same input into batches. | sorter | T |
| SRS-SRT-116 | The sorter shall output coincidences in the time order of their first singles. | sorter | T |
| SRS-SRT-117 | The sorter's counters shall account for every single received as rejected by energy, out of order, alone, or in a window of a counted size. | sorter | T |
| SRS-SRT-118 | The sorter shall refuse a configuration whose window is outside 1 to 1,000,000 ps, whose nonzero delay does not exceed the window, or whose energy window is empty or not finite. | sorter | T |
| SRS-SRT-119 | The sorter shall refuse a minimum sector difference above 12 sectors and a field-of-view radius that is not inside the 150 mm ring radius. | sorter | T |
| SRS-SRT-120 | The sorter shall output a coincidence at the latest when it receives a single inside the energy window that is more than the window plus the delay later than the coincidence's first single. | sorter | T |
| SRS-SRT-121 | The sorter shall process at least 30,000,000 singles/s on one core of the reference machine with the `hardened` preset. | sorter | M |
| SRS-SRT-122 | When a window holds more than two singles and the multiples policy is `keep_if_only_one_good`, the sorter shall output its good pair only if exactly one pair of the window is good. | sorter | T |
