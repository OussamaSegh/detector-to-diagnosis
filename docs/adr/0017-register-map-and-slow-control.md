# 0017. Registers generated from one specification, a bus interface, and a slow-control loop that owns the bias

Date: 2026-10-26
Status: Accepted

## Context

Chapter 22 connects MiniDAQ to the front-end boards. Two kinds of traffic go to a board: the data
stream (the readout link of Chapter 9) and register accesses, which set the bias of the SiPMs,
read temperatures and switch functions on and off. The registers are defined by the firmware, and
the definitions change as the firmware does; a register at the wrong address in the software is a
defect that compiles, runs, and writes a bias into a threshold.

The bias must also follow the temperature. A SiPM's breakdown voltage rises by about 34 mV per
degree (the model this book uses, a Hamamatsu S14160-3050HS; other SiPMs are between about 20 and
35 mV per degree), so a fixed bias loses gain as the detector warms (hazard H-10). Something must
read each board's temperature, set its bias, and decide what to do when a board does not answer or
cannot hold its bias, and that something runs in the class B server process.

## Options

1. **Hand-written register constants** (`constexpr uint32_t BIAS_SETPOINT = 0x020;` and masks) in
   a header, kept in step with the firmware's documentation by review. Simple; every embedded
   project starts there. Nothing stops a write to a read-only register or a read-modify-write of
   a write-1-to-clear register, and nothing notices when the header and the firmware drift apart.
2. **A vendor or open-source register tool** (SystemRDL compilers, IP-XACT generators). Complete,
   and the firmware team may already use one. New SOUP and new tool qualification for a few
   dozen registers, and an input language that the software team must learn.
3. **One small specification and a generator of MiniDAQ's own**, writing typed C++ (a type per
   register and per field, its access checked by the compiler) and a document; a `RegisterBus`
   interface with a memory-mapped implementation and a simulated board; a slow-control loop on
   its own thread that owns the bias of every board and reports to the service through a port.

## Decision

Option 3.

- `hw/feb.toml` is the single source of the front-end board's registers. `tools/regmap_gen.py`
  (TOML, read with Python's standard `tomllib`, so no new package) checks it and writes
  `minidaq/include/minidaq/hw/feb_regs.hpp` and `docs/hw/feb-register-map.md`; the test
  `docs.regmap` fails while either is out of date. If the firmware team keeps its map in another
  format, the generator reads that instead and the rest stays.
- `Register<Address, Access, Reset>` and `Field<Register, Lsb, Width, Signed>` carry the map in
  the type system; `read`, `write`, `write_field` and `clear` are constrained by concepts, so a
  write to a read-only register, a read of a write-only one and a read-modify-write of a
  write-1-to-clear register do not compile.
- `RegisterBus` has two operations, `read32` and `write32`, returning an error instead of
  throwing. `MmioBus` maps a UIO device or a PCI resource file and accesses it through a
  `volatile` pointer, one load or store per access, with a store barrier where the architecture
  needs one; `FakeBoard` simulates a board, its ramping supply, its protection and its faults.
- `SlowControl` runs one cycle per 100 ms on its own thread: it reads every board, computes
  V_bd(T) + V_ov inside fixed limits, writes the setpoint when it moved by 5 mV or more, and
  latches a fault per board, switching that board's bias off. Faults stay latched until an
  operator acknowledges them (`reset` after a fault). Readers get a copy of the state under a
  mutex; only the cycle writes it.
- The service sees the hardware through `HardwarePort`: it refuses `start` while a board is not
  ready and stops a run with fault source `hw` when a fault latches, in any state. The status and
  the run record carry the boards' state (`hardware`, control API 2.2).

## Consequences

### Positive

- The register map is reviewed once, as a specification, and the compiler checks every use of it.
  A change of the map is a change of one file, and the generated header shows it in the diff.
- Every behavior of the slow control is tested without hardware, at simulated time: a ramp of
  forty seconds takes microseconds, and each way a board fails is a line of a test.
- The fail-safe state is explicit: a fault switches the bias off, and the server switches every
  bias off at shutdown.

### Negative

- MiniDAQ owns a generator, which is a class T3 tool (TL-25): its output is compiled into the
  product, so it is tested like code.
- The simulated board is a model. Its timing, its protection threshold and its fault behavior
  are this book's assumptions; the integration with a real board is a separate verification
  (assumption: confirm with team).
- Compensation from a temperature sensor on the board corrects the average temperature of the
  board, not each SiPM's: a gradient across a board, or a sensor far from the SiPMs, leaves a
  residual gain spread that the energy calibration has to absorb.
- A cycle of 100 ms on a few dozen boards is a few hundred register accesses per second. Through
  a slow bus (I2C to a sensor, for example), the cycle time grows with the number of boards and
  must be measured on the real system.
