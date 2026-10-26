# Talking to hardware from Linux {#ch22}

::: box-why
A PET DAQ does more than receive data. It sets the bias voltage of every SiPM, the thresholds of
every channel, the delays that align the boards in time, and it reads temperatures, currents and
error flags, many times a second, for as long as the scanner is on. All of that goes through
registers: words at fixed addresses on a board, defined by the firmware team and reached from
Linux through a driver, a mapped region of a PCIe device, or a slow serial bus. Getting a
register access wrong is not a performance problem. It writes a bias into a threshold, clears an
error flag nobody has seen, or leaves a detector biased while it overheats. And the bias itself
is a calibration: a SiPM's gain moves with its temperature by more than one percent per degree,
so software that does not follow the temperature changes every energy the scanner measures. This
chapter teaches how Linux gives a program access to hardware, why memory-mapped I/O needs
`volatile` and barriers where threads need atomics, how a register map becomes typed C++ from one
specification, what the slow-control buses and sensors of a detector are, and how software fails
safe when hardware stops answering. MiniDAQ gets all of it, tested against a simulated board at
simulated time.
:::

**A day in the life.** It is 14:10 on a Tuesday, and the physicist who runs the daily quality
control shows you two energy spectra of the same phantom, one from 8:00 and one from 13:30. The
afternoon photopeak sits at 486 keV instead of 511, and the count rate in the energy window is a few
percent lower. Nothing in the logs says anything went wrong. You ask for the temperatures of the
detector blocks: the room's air conditioning failed at 11:00, and the blocks went from 25 to 29 °C.
At 34 mV per degree, four degrees raised the breakdown voltage of every SiPM by 136 mV, and with the
bias fixed, the overvoltage fell from 2.70 V to 2.56 V: 5% less gain, a photopeak 5% lower, and an
energy window that now cuts off part of it. The bias supply was doing exactly what it was told. The
software was the part that should have told it something else, and the part that should have said,
in the status of every run, that the detectors were not at their calibrated temperature. By the
evening you have written two requirements: the bias follows the temperature, and a run does not
start, or does not go on, while a board is outside its limits. The rest of this chapter is how to
meet them.

## Learning objectives {.unnumbered}

After this chapter you can:

1. Explain how Linux exposes hardware to a user-space program (device files, sysfs, UIO, VFIO,
   `mmap` and `ioctl`) and choose between a kernel driver and user-space access.
2. Access memory-mapped registers correctly: why every access must be a `volatile` load or
   store, why C++ atomics are not the tool for device memory, where barriers are needed, and why
   a PCIe write may not have arrived yet.
3. Generate a type-safe register map from one specification, so that the compiler refuses a
   write to a read-only register and a read-modify-write of a write-1-to-clear register.
4. Describe the slow-control buses and sensors of a detector (I2C, SPI, UART, GPIO) and decode a
   sensor's register from its datasheet.
5. Write a slow-control loop that keeps a SiPM's overvoltage constant, inside limits, with
   warnings, alarms and latched faults.
6. Design timeouts, retries and a fail-safe state for hardware that stops answering, and test
   all of it without hardware.

## Prerequisites and estimated time {.unnumbered}

Chapter 3 (threads, atomics and the memory model), Chapter 6 (ports and adapters), Chapter 8
(SiPMs, energy resolution and the energy window), Chapter 9 (the readout link), Chapter 15 (the
hazard analysis) and Chapter 18 (test doubles). Reading: about 3.5 hours. Exercises: 6 to 8
hours. Milestone: 6 hours. If time is short, do Exercises 22.2 and 22.3 and leave 22.4 for later.

## How Linux gives a program its hardware

### The intuition

A user-space program cannot touch hardware. Its addresses are virtual, the kernel decides what
they map to, and a device's registers are mapped nowhere until somebody asks. There are two ways
to ask. A kernel driver owns the device, and the program talks to the driver through a device
file: `read`, `write` and `ioctl` on `/dev/something`, each a system call that the driver turns
into register accesses. Or the kernel maps the device's registers into the program's address
space, and the program accesses them directly, with no system call per access. The first is
safer and slower; the second is fast and leaves every mistake to you. A DAQ uses both, often for
the same board: the data path through a driver that does DMA, the slow control through mapped
registers or a serial bus.

### The device model in five paths

Linux describes every device it knows in sysfs, a file system that the kernel generates.
`/sys/bus/pci/devices/` lists PCI devices by bus address (`0000:03:00.0`); each has its vendor and
device IDs, the driver bound to it, and one file per memory region (`resource0`, `resource1`,
...), which a program with the right permissions can `mmap`. `/dev/` holds the device files that
drivers create: `/dev/i2c-1` for an I2C bus, `/dev/spidev0.0` for a SPI device, `/dev/ttyUSB0` for
a serial port, `/dev/gpiochip0` for a GPIO controller, `/dev/uio0` for a device given to user
space. `/sys/class/hwmon/` collects the temperature, voltage and fan sensors that kernel drivers
already read for you.

The rule of thumb for which to use:

- **A kernel driver exists and does what you need** (a hwmon sensor, a network card, a USB-serial
  adapter): use its device file or its sysfs attributes. You get the driver's locking, its error
  handling and its maintenance by others.
- **Registers only, no DMA, no interrupts that must be fast**: map them from user space. On a
  PCI device, the `resourceN` file in sysfs, or the UIO framework (`uio_pci_generic` for PCI, or a
  platform device on an embedded board) which also delivers interrupts: a `read` of the 4-byte
  counter from `/dev/uioN` blocks until the next interrupt.
- **DMA from user space**: VFIO, which puts the device behind the IOMMU so that a wrong address in
  a descriptor cannot overwrite the kernel's memory. UIO has no such protection, and a device that
  does DMA through UIO can write anywhere in memory.
- **Anything that must be fast and safe at once, and that other software also uses**: a kernel
  driver, written with the firmware team, reviewed, and maintained as part of the product.

::: box-regulated
A kernel driver runs with every privilege of the kernel; a bug in it can corrupt any process,
including the one that writes the patient's data. In IEC 62304 terms it is a software item of
the highest class of anything in the system, and the segregation argument of Chapter 14 ("the
data path cannot be corrupted by the GUI") no longer holds for it. A user-space driver over UIO
or VFIO keeps the defect inside one process. Keep the code that runs in the kernel as small as
the hardware allows, and prefer frameworks that the kernel already maintains (assumption: confirm
with team whether the product ships its own kernel modules and how they are verified).
:::

### `mmap` and what it gives you

`mmap(nullptr, size, PROT_READ | PROT_WRITE, MAP_SHARED, fd, offset)` on a device file returns a
pointer through which loads and stores reach the device. The size is rounded to whole pages, the
offset must be a multiple of the page size, and for UIO the offset selects which of the device's
regions you get (region N at N times the page size). A `resourceN` file of a PCI device is mapped
uncached; a `resourceN_wc` file, where it exists, is mapped write-combining, for memory such as a
frame buffer where the order and size of writes do not matter. Registers are never write-combined.

MiniDAQ's `MmioBus` opens the file with `O_SYNC`, which on these files asks for an uncached
mapping, and checks the size and the offset before it maps:

```{.cpp include="minidaq/include/minidaq/hw/mmio_bus.hpp" snippet="mmio"}
```

Nothing in this code needs root if the device file's permissions allow it, and that is the point:
a udev rule gives the acquisition service's user access to exactly one device, and nothing else
on the machine (Chapter 25).

## Memory-mapped I/O

### Why every access is `volatile`

The compiler optimizes memory accesses on the assumption that memory is memory: a value stored
stays there until the program stores another, and nobody else is looking. Under that assumption a
load whose value is already known can be removed, two stores to the same address can become one,
and a loop that reads a status register until a bit is set can read it once. For device registers
every one of those assumptions is false. Reading `status` asks the device a question; reading it
twice asks twice. Writing `1` to a reset bit and then `0` is two commands, not one. Some reads have
side effects (a FIFO register returns the next word and advances), and some writes clear flags.

`volatile` is the C++ word for "this access is observable behavior": the compiler emits every
volatile access the program performs, in the program's order relative to the other volatile
accesses, with the size the type says. That is exactly what device registers need, and it is all
`volatile` does:

```{.cpp include="minidaq/src/hw/mmio_bus.cpp" snippet="mmio-access"}
```

The value is read into a local `const std::uint32_t` before it goes into the `Expected`: one
volatile load, whose result is then an ordinary value. An earlier version passed
`base_[address / 4]` straight to the `Expected`, and the compiler refused it: the constructor takes
its argument by reference, and a reference to a non-volatile type cannot bind to a volatile
object. The local copy also makes the one access visible in the source.

### Why not atomics

Chapter 3 said that `volatile` is not for threads, and that remains true: `volatile` does not make
an access indivisible between threads and does not order other memory accesses around it. The
converse is true too: atomics are not for devices. The C++ memory model describes how threads
communicate through memory, and it allows a compiler to merge two adjacent relaxed atomic stores
to the same object into one, or remove an atomic load whose value cannot be observed differently,
because no thread could tell. A device can tell. Compilers rarely do these transformations today,
but the standard permits them, and a register access whose correctness depends on what compilers
rarely do is a defect waiting for an upgrade. Use `volatile` for device memory, atomics for
memory shared between threads, and if a variable is both (a register that two threads access),
use `volatile` for the access and a mutex for the threads.

### Barriers

`volatile` orders volatile accesses as the compiler emits them. The processor may still reorder
them on their way to the device. On x86-64, accesses to uncached memory are performed in program
order, so a compiler barrier is enough. On AArch64, device memory mapped with the usual attributes
keeps accesses to the same device in order, but a store to a device may still be reordered with a
store to normal memory: the classic case is a DMA descriptor written to RAM followed by a doorbell
register that tells the device to read it. The device must not see the doorbell before the
descriptor, and on AArch64 that takes a `dmb` (data memory barrier) between the two stores. The
Linux kernel's `writel` includes such a barrier and `writel_relaxed` does not; in user space you
write it yourself:

```cpp
void write_barrier() noexcept {
#if defined(__x86_64__)
  asm volatile("" ::: "memory");          // compiler barrier: x86 keeps stores in order
#elif defined(__aarch64__)
  asm volatile("dmb oshst" ::: "memory"); // stores before it are visible before stores after it
#else
#error "write_barrier() needs the store barrier of this architecture"
#endif
}
```

The `#error` is deliberate. A barrier that silently does nothing on a new architecture is a defect
that passes every test on the old one.

### Posted writes

A PCIe write is posted: the processor hands it to the bus and continues, and the write reaches the
device some time later. A read from the same device cannot overtake earlier writes to it, so the
standard way to know that a write has arrived is to read a register of the same device afterwards.
Two consequences matter in a DAQ. Timing a write ("the bias was enabled at time t") measures when
the processor issued it, not when the board executed it. And a write to a device that has gone
(unplugged, powered off, or fallen off the link after an error) does not fail: it disappears. The
read that follows returns all ones, `0xFFFFFFFF`, which is what a PCIe read of a missing device
returns. That is why MiniDAQ reads the board's identity register at the start of every cycle and
treats all ones as "the device may have gone", not as data.

::: box-mistakes
- Accessing registers through a plain pointer. The code works in a debug build and fails at `-O2`,
  where the compiler removes the second read of a status register.
- Using `std::atomic` on mapped device memory, or `memcpy` to copy a block of registers. Neither
  guarantees the size, the number or the order of the accesses the device sees.
- Reading a 32-bit register as two 16-bit halves, or a 64-bit counter as two 32-bit words without
  a latch: the value can change between the halves.
- A read-modify-write of a register whose bits clear when written as 1. Writing the value back
  clears every flag that was set, including the ones you have not handled.
- Trusting a write because it returned. On PCIe it returned before it arrived, and a lost device
  loses it without an error.
:::

## Register maps from one specification

### The intuition

A board's register map is an interface between two teams, and like the readout word format of
Chapter 9 it changes. The firmware team adds a register, moves a field, makes a bit
write-1-to-clear. If the software has its own copy of the map, written by hand from a PDF, the
two drift apart, and the first sign is a board that does something strange. The cure is the same
as for any duplicated knowledge: one source, from which both sides are generated. Industry has
standard formats for it, SystemRDL 2.0 (Accellera) and IP-XACT (IEEE 1685), with compilers that
generate firmware, C headers and documents. For a few dozen registers a simpler format and a
small generator do the same job, and that is what MiniDAQ uses. If your firmware team already has
a SystemRDL or IP-XACT description, generate from that instead.

### The specification

MiniDAQ's front-end board (FEB) is a simulated board with one bias channel, one temperature sensor
and eleven registers. Its map is a TOML file, read by Python's standard library:

```toml
[[register]]
name = "control"
address = 0x008
access = "rw"
reset = 0x00000000
description = "Switches; the bias supply ramps to BIAS_SETPOINT when BIAS_ENABLE is set."
fields = [
  { name = "bias_enable", lsb = 0, width = 1, description = "1: the bias supply is on" },
  { name = "trigger_enable", lsb = 1, width = 1, description = "1: the board sends data" },
  { name = "soft_reset", lsb = 31, width = 1, description = "Write 1: reset; reads as 0" },
]
```

Four kinds of access cover nearly every register: `ro` (read only: identity, status, measured
values), `rw` (settings that read back what was written), `wo` (commands whose reads mean nothing)
and `rw1c` (flags that the hardware sets and software clears by writing 1 to them; writing 0
leaves a flag alone, so software can clear exactly the flags it has handled). The generator,
`tools/regmap_gen.py`, checks the specification before it writes anything: addresses aligned and
distinct, fields inside 32 bits and not overlapping, a reset value with no bit outside the fields.
It writes a C++ header and a Markdown table (`docs/hw/feb-register-map.md`), and the test
`docs.regmap` fails while either differs from what the specification generates. The generator
is a tool whose output is compiled into the product, a class T3 tool in the terms of Chapter 20,
so it has its own tests and an entry in the tool list.

### Types that know their access

The generated header turns each register into a type and each field into a nested type:

```cpp
struct Control : Register<0x008, Access::rw, 0x00000000> {
  struct BiasEnable : Field<Control, 0, 1> {};
  struct TriggerEnable : Field<Control, 1, 1> {};
  struct SoftReset : Field<Control, 31, 1> {};
};
```

`Register` and `Field` carry the address, the access, the position and the width as compile-time
constants, and compute masks from them:

```{.cpp include="minidaq/include/minidaq/hw/register.hpp" snippet="types"}
```

The accesses are templates constrained by the access of the register:

```{.cpp include="minidaq/include/minidaq/hw/register.hpp" snippet="access"}
```

`write<feb::Status>(bus, 0)` does not compile, because `Status` is read only;
`write_field<feb::ErrorFlags::Overcurrent>(bus, 0)` does not compile, because a read-modify-write
of a write-1-to-clear register would clear every flag; `clear<feb::ErrorFlags>(bus, mask)` is how
flags are cleared. The test file proves these claims with `static_assert`s on concepts that ask
whether a call would compile, so a change that loosened a constraint fails the build. Every
access goes through `RegisterBus`, the port of this chapter:

```{.cpp include="minidaq/include/minidaq/hw/register.hpp" snippet="bus"}
```

Two operations, both of which can fail and say so. An `MmioBus` fails on an address outside its
mapped region; a bus that talks I2C fails on a missing acknowledgment; a simulated board fails
however a test tells it to. Nothing throws: a register access is often in a loop that runs ten
times a second for days, and its failures are expected events, not exceptions.

### Testing a register layer

Three kinds of test cover the layer. The generated map is checked against its specification
(addresses, accesses and reset values, by iterating the generated table). The field arithmetic is
checked bit by bit, including a signed field: the temperature register holds a 16-bit two's
complement number in 1/128 °C, and `0xF380` must decode to −25.0 °C. And `MmioBus` is tested on
real mapped memory: a `memfd` (an anonymous file in memory) stands in for a device's region,
mapped by the same code, so that the test checks that each access is one load or store at the
right offset and that an access outside the region or not aligned is refused. A `memfd` does not
behave like a device, but it shows that the code computes the right addresses and touches nothing
else.

## Slow-control buses and sensors

### What is on a detector board

Besides the data path, a detector board carries a slow-control world: temperature sensors next to
the SiPMs and on the electronics, the bias supply (a DC-DC converter with a DAC for its setpoint
and an ADC that measures its output and current), voltage monitors, perhaps a fan controller and
an EEPROM with the board's serial number and calibration. These parts talk over buses that are
slow, cheap and simple:

- **I2C**: two wires, addressed devices, typically 100 or 400 kbit/s. Sensors, DACs, EEPROMs. A
  device that is absent or busy does not acknowledge its address, and the access fails
  immediately. Linux exposes a bus as `/dev/i2c-N`.
- **SPI**: four wires, a chip-select per device, several Mbit/s, no acknowledgment at all: a
  missing device returns whatever the data line floats to. ADCs, DACs, flash memories.
  `/dev/spidevB.C`.
- **UART**: a serial line to a microcontroller or a power supply with its own command language.
  `/dev/ttyS0`, `/dev/ttyUSB0`.
- **GPIO**: single pins: a power-good signal, an enable line, a reset. Linux's interface is the
  character device `/dev/gpiochipN` with the libgpiod library; the older sysfs interface
  (`/sys/class/gpio`) is deprecated.

On many boards the FPGA or a microcontroller owns these buses and presents the results as
registers, as MiniDAQ's simulated board does. Either way, somewhere a piece of code reads a
sensor's register and turns bits into a temperature, and it must do so from the datasheet, not
from memory.

### Reading a sensor from its datasheet

Take the Texas Instruments TMP117, a digital temperature sensor on I2C that detector boards use
for its accuracy. Its datasheet says: the temperature result is register `0x00`, 16 bits, two's
complement, 7.8125 m°C per bit (1/128 °C); the configuration is register `0x01`; the device ID
register `0x0F` reads `0x0117` in its low 12 bits. And, in a sentence that is easy to miss:
following a reset, the temperature register reads −256 °C (`0x8000`) until the first conversion
is complete. A slow control that reads the sensor right after power-up and believes the number
sees a detector at −256 °C and, if it compensates the bias for it, sets a bias 9.5 V lower than
it should (281 degrees at 34 mV per degree), or, if it is clamped, the lowest bias it allows.
Exercise 22.3 decodes this sensor, and the decoder's first job is to recognize a reading that is
not a temperature.

The same reasoning applies to every sensor: check its identity before you trust it, know what it
reads before it has measured anything, and know the range it can physically report. MiniDAQ does
not believe a temperature below 5 °C: a detector in a scanner room is never that cold, and a
reading that low is a broken sensor, a missing one, or a register that was never written.

## Keeping the gain constant

### The physics in one line

Chapter 8 introduced the SiPM: an array of avalanche photodiodes biased above their breakdown
voltage, whose gain is proportional to the overvoltage, the bias minus the breakdown voltage. The
breakdown voltage rises with temperature. For the SiPM this book models, the Hamamatsu
S14160-3050HS, the datasheet gives a breakdown voltage of 38 V at 25 °C, a temperature
coefficient of 34 mV/°C, a recommended operating voltage 2.7 V above breakdown and a gain of
2.5 × 10^6^ there. (Other SiPMs differ: onsemi's J-Series, for example, has a breakdown voltage
near 24.5 V and 21.5 mV/°C. The law is the same, the numbers are the board's.) At a fixed bias,
one degree warmer takes 34 mV off a 2.7 V overvoltage: 1.3% of gain per degree. The fix is to let
the bias follow the temperature:

  V_bias(T) = V_bd(25 °C) + k · (T − 25 °C) + V_ov

with k = 34 mV/°C and V_ov = 2.7 V. At 25 °C that is 40.7 V; at 30 °C, 40.87 V.

This assumes the temperature the sensor reads is the temperature of the SiPMs, which is only
approximately true: a sensor on the board lags the SiPMs and misses the gradient across them. The
compensation removes most of the drift; the energy calibration and the daily quality control
remove the rest, and a hazard analysis has to say how much is left (H-10 below).

### MiniDAQ's slow control

`SlowControl` runs a cycle every 100 ms on its own thread. For each board it reads the identity,
the temperature, the status, the error flags, the measured bias and the bias current; checks each
against its limits; computes the bias for the temperature; clamps it to fixed limits (36 to
43 V); and writes a new setpoint only if it moved by at least 5 mV, about 0.15 °C, so that a
noisy sensor does not make the supply chatter. The settings are a plain struct:

```{.cpp include="minidaq/include/minidaq/hw/slow_control.hpp" snippet="settings"}
```

The cycle for one board is the heart of the chapter, and it is short enough to read whole:

```{.cpp include="minidaq/src/hw/slow_control.cpp" snippet="step-board"}
```

Read it for its order. Everything is read before anything is decided, and one failed read makes
the whole cycle of that board a failure: deciding from half a cycle's readings is how a
controller acts on a temperature from one moment and a current from another. The identity is
checked before any other register is believed. The temperature is checked before it is used. The
board's own findings (its overtemperature trip, its overcurrent flag, its supply fault) come
before the software's. Only then is a bias computed, and on a board that has just been powered up
or recovered, the ramp rate and the setpoint are written before the supply is enabled, so that it
never drives a setpoint left from before.

### Warnings, alarms and hysteresis

Temperature has three levels. At 35 °C the board is in warning: the status says so, an operator
can act, and the acquisition goes on. The warning clears only below 34 °C, one degree of
hysteresis, so that a temperature that hovers at 35.0 does not flood the operator with warnings
that come and go. At 40 °C the board is in alarm, which is a fault: the bias goes off and stays
off. These numbers are this book's (assumption: confirm with team); the shape (a warning with
hysteresis, an alarm that latches, a reading that is not believed) is common to every slow
control you will see.

### Latching, and who clears a fault

A fault latches: once a board's state is `fault`, it stays there, with its bias off, until an
operator acknowledges it, even if the cause goes away. The alternative, a fault that clears itself
when the temperature drops, makes a board that overheats every few minutes cycle its bias on and
off during a scan, and the run's data a mixture of good and bad periods that nobody decided to
keep. An acknowledgment is a decision by a person who has seen the fault. In MiniDAQ it is the
`reset` command after a fault: it clears the board's sticky error flags, powers the board up
again, and if the cause is still there the fault latches again in the next cycle.

The acknowledgment has a subtlety that a test found. `reset` acknowledges, and the service
immediately goes back to `idle`; the slow control processes the acknowledgment in its next cycle,
up to 100 ms later. In between, the copy of the state that readers see still shows the old fault,
and the service's monitor, which checks for hardware faults every few milliseconds, moved the
service straight back to `fault`. The fix is a sequence number: each acknowledgment increments a
counter, each cycle publishes the counter it has processed, and a fault published by a cycle
that has not seen the latest acknowledgment is not reported.

### Faults and the fail-safe state

`latch` is the only way into the fault state, and it does three things: it records why, it
records a `hw_fault` event in the flight recorder of Chapter 21 with the board and the cause, and
it switches the board's bias off. The fail-safe state of a SiPM is unbiased: an unbiased detector
produces no data, which the run's integrity verdict reports, and cannot be damaged by its own
current. The switch-off is best effort. A board that does not answer cannot be told anything, and
then its own protection is all that is left, which is why the simulated board, like a real one,
switches its bias off by itself above 60 °C whatever the software does. Software is one layer of
protection, not the only one.

The causes, each with its test:

| Cause | Detected by | Why it matters |
|---|---|---|
| No answer | 3 cycles in a row with a failed access | The bias is no longer controlled |
| Wrong identity | `board_id` magic is not `0x4D51`; all ones means the device may have gone | Every other register is meaningless |
| Temperature | 40 °C or above, or below 5 °C | Gain far from calibration, or a broken sensor |
| Board overtemperature | The board's own trip flag | The hardware has already acted |
| Overcurrent | Flag, or more than 500 µA | A damaged SiPM, a short, or light in the gantry |
| Supply | The board says its supply cannot hold the setpoint | The overvoltage is wrong |
| Not reached | The bias has not reached the setpoint within the ramp time plus 2 s | A supply or a readback that is broken |

The last row is the one that is easiest to forget. A supply that ramps at 1 V/s needs 40.7 s from
zero; a slow control that declared a fault after a fixed 5 s would fault every board at every
power-up, and one that never checked would wait forever for a supply that is stuck. The deadline
is computed from the distance and the rate when the board leaves the ready state, plus a grace
period.

::: box-mistakes
- Retrying a failed write until it succeeds, inside the cycle. A board that does not answer then
  holds the whole slow control, and every other board goes uncontrolled with it. Count failures
  across cycles instead, and give up on one board, not on all.
- A timeout without an action. "The supply did not answer" must lead somewhere: a fault, a bias
  off, a status an operator sees.
- A fault that clears itself. The data of a run with intermittent faults is a mixture nobody chose.
- Treating the software limit as the protection. The board's own limits, set in hardware or
  firmware, protect the detector when the software is gone.
- Computing the bias from a temperature that was never measured: the sensor's reset value, a zero
  from a register that failed to read, or the last good value from an hour ago.
:::

## Hardware in the service

### A port that lives longer than a run

Chapter 6 gave the acquisition service ports for its detector and its sink, created fresh for
every run. The hardware is different: the bias must be controlled whether or not a run is going
on, from the moment the server starts until it stops. `HardwarePort` is a port the service is
given once, with five operations: whether every board is ready, the latched fault if any,
acknowledge, the boards' state, and a description. The service uses it in three places. `start`
refuses with `device_error` while a board is not ready, with the reason. The monitor thread checks
for a hardware fault in every state but `fault`: during a run, the run stops with the fault
source `hw`; outside a run the service goes to `fault` at once, so that an operator sees a board
that failed overnight before the first patient, not after. And `reset` after a fault acknowledges
it. The status gains a `hardware` field with every board's state, temperature, setpoints, measured
bias, current and fault, and because the run record is the status at the end of the run, every
run records the state of its detectors (control API 2.2, a minor version, because the field is
new and nothing else changes).

The adapter, `SlowControlHardware`, builds the buses from a hardware description (a JSON file
given to the server with `--hardware`, parsed as strictly as the acquisition configuration of
Chapter 6), starts the slow control and switches every bias off when the server shuts down. For
simulated boards, the description can make a board's temperature follow a file, so that a system
test, or a demonstration, warms a detector by writing a number:

```json
{"schema_version": "1.0", "backend": "simulated", "period_ms": 20,
 "bias": {"ramp_v_per_s": 50.0},
 "boards": [{"slot": 0, "temperature_file": "/tmp/feb0-temperature.txt"}, {"slot": 1}]}
```

### Testing without hardware, at simulated time

`FakeBoard` is a board as a program: its eleven registers with their access rules, a supply that
moves towards its setpoint at the programmed rate, the board's own overtemperature trip, and four
modes of failure (none, unresponsive, vanished, weak supply). Its time is a function its owner
gives:

```{.cpp include="minidaq/src/hw/fake_board.cpp" snippet="fake-physics"}
```

In a unit test, time is a variable the test advances. A ramp from 0 to 40.7 V at 1 V/s takes 41
seconds of simulated time and no real time at all, so a test can check the ramp, the deadline and
the moment a fault latches to the cycle, deterministically, in microseconds. The tests of the slow
control read like its requirements: it keeps the overvoltage constant as the temperature moves; it
never sets a bias outside its limits; it writes the ramp rate and the setpoint before it enables
the supply (checked by a bus that records the order of the writes); it warns with hysteresis and
switches the bias off at the alarm; it latches a fault for each way a board fails; an acknowledged
fault clears only when its cause has gone. One test runs the real thread with the steady clock, to
check that the thread starts and stops; every other test calls `step()` with a time it chooses.

The service is tested with the real adapter and simulated boards, a temperature file and a
period of 10 ms, and a system test does the same with the shipped programs: a server with two
simulated boards, a run, a file rewritten to 41.5 °C, and then the checks an operator would make.
The run stops with `hw: board 0 (slot 0): temperature 41.50 C is at or above the alarm limit 40.0
C`; board 0 is in fault and board 1 is still ready; the flight recorder holds the `hw_fault`
event and the run's fault with source `hardware`; a reset while the board is still hot does not
hold; after it has cooled, a reset, a new configuration and a run succeed, and the run record
shows both boards ready with the setpoints their temperatures ask for.

::: box-regulated
The slow control implements risk controls of a hazard that did not exist in MiniDAQ before: H-10,
detector gain drifts with temperature. Its sequence is the scene at the start of this chapter; its
harm is a quantitative value or an artifact that contributes to a wrong diagnosis. The controls
are the compensation (RC-26), the faults that switch the bias off (RC-27), and the service that
takes no data while a board is not ready or has a fault and records each board's state with every
run (RC-28). Each control traces to requirements (SRS-HW-001 to SRS-HW-007) and each requirement
to tests, through the same tools as in Part III. The change itself went through change request
CR-0008 with its impact analysis, and the design decision is ADR 0017. The software controls a
high-voltage supply now; whether its limits and its switch-off belong in the scanner's hardware
safety concept under IEC 60601-1 as well is a system decision, recorded as an assumption.
:::

## Timeouts, retries and the order of failure

Hardware fails in a few ways, and each has its symptom and its answer:

- **It does not answer.** I2C: no acknowledgment, at once. A microcontroller behind a UART: no
  reply, after your timeout. PCIe: all ones. Count failures over cycles and give up after a
  number that tolerates a glitch (MiniDAQ: 3 cycles, 300 ms) but not a dead board.
- **It answers wrongly.** An SPI device that is missing returns all zeros or all ones, never an
  error; a sensor returns its reset value; a register reads a value outside its field's range.
  Check identities and plausibility, not only error codes.
- **It answers late.** A slow bus, a busy microcontroller, a supply that ramps. Distinguish "late"
  from "never" with a deadline computed from what the hardware should take.
- **It answers, and does not do what it said.** A supply that reports its setpoint and does not
  reach it. Measure the effect (the bias monitor), not the command.

A retry is the right answer only for a failure that is transient and an operation that is
idempotent. Writing a setpoint again is idempotent; clearing a flag is not, if the flag was set
again in between; a FIFO read that failed halfway may have consumed a word. Bound every retry, in
count and in time, and never retry inside a loop that also serves other boards. And decide the
fail-safe state before writing the code: for a bias supply it is off; for a cooling fan it is on;
for a data link it is "stop and report". The fail-safe state of each output is a design decision
that belongs in the hazard analysis, not in a `catch` block.

::: box-askteam
1. Who owns the register map of each board, in which format, and how does a change reach the
   software? Is the software's copy generated, and is the map versioned with the firmware?
2. How does the acquisition PC reach the boards' registers: a kernel driver, UIO, VFIO, a
   microcontroller over a serial link, or registers inside the data stream?
3. Which SiPMs and which bias supplies does the scanner use, with which temperature coefficient,
   overvoltage and limits? Where does the temperature for compensation come from, and how far is
   the sensor from the SiPMs?
4. What does each board do by itself when it overheats or loses its controller, and at which
   thresholds? Is that verified as part of the hardware?
5. Which faults stop an acquisition, which only warn, and who may acknowledge a fault?
6. Is there a hardware-in-the-loop bench with real boards, and which tests run on it?
:::

## Exercises {.unnumbered}

**Exercise 22.1 (M): Generate a register map.** *Goal:* write a generator that checks a register
map in TOML and writes a C++ header of constants (address, mask and shift of every field).
*Starter:* `exercises/ch22/e1_regmap/starter/regmap.py`. *Acceptance:* `tests/test_regmap.py`
passes: misaligned and duplicate addresses, overlapping fields, fields outside 32 bits and reset
values outside the fields are refused with the register's name; the header defines the right
constants, compiles, and a C++ check of it against a fake register block passes when a compiler
is available. Then answer in `NOTES.md` what a type per register gives that constants do not.
*Time:* 60 minutes.

**Exercise 22.2 (M): A bias controller with limits and alarms.** *Goal:* write the decision of one
slow-control cycle for one board: the bias for the temperature, clamped to limits, a warning with
hysteresis, an alarm that latches until acknowledged, and a reading that is not believed.
*Starter:* `exercises/ch22/e2_bias_control/starter/bias_controller.cpp`. *Acceptance:*
`tests/test_bias_controller.cpp` passes: the law and its limits, the update step, the hysteresis
of the warning, the latch and its acknowledgment, and a temperature that is NaN or below the
minimum. Then answer in `NOTES.md` why the alarm latches and the warning does not. *Time:* 60
minutes.

**Exercise 22.3 (E): Decode a temperature sensor.** *Goal:* decode the temperature and the device
ID registers of a TMP117 as its datasheet describes them, and refuse the reading it gives before
its first conversion. *Starter:* `exercises/ch22/e3_tmp117/starter/tmp117.cpp`. *Acceptance:*
`tests/test_tmp117.cpp` passes: the datasheet's example values, negative temperatures, the
byte order of an I2C read, the reset value `0x8000`, and an identity check that ignores the
revision bits. *Time:* 30 minutes.

**Exercise 22.4 (H): Fail safe when a supply stops answering.** *Goal:* write the guard around a
bias supply with a command interface: bounded retries of idempotent commands only, a deadline for
reaching the setpoint, a fail-safe state that is entered once and left only by an
acknowledgment, and an honest report when even the switch-off cannot be confirmed. *Starter:*
`exercises/ch22/e4_supply_guard/starter/supply_guard.cpp`. *Acceptance:*
`tests/test_supply_guard.cpp` passes with a scripted supply that times out, refuses, answers late,
and reports a voltage it does not reach. Then answer in `NOTES.md` which commands of the supply
you would retry and which not, and why. *Time:* 90 minutes.

## MiniDAQ milestone: the detectors stay at their gain {.unnumbered}

::: box-milestone
**Goal.** MiniDAQ reaches front-end boards through typed registers generated from one
specification, over a memory-mapped bus or a simulated board; a slow control keeps every board's
overvoltage constant as its temperature changes and latches faults with the bias off; the service
takes no data while a board is not ready or has a fault, and every run records its detectors'
state.
**Start:** tag `ch21`. **End:** tag `ch22`.
:::

1. Write change request CR-0008 and ADR 0017 before the code; add hazard H-10 with RC-26 to
   RC-28, the requirements SRS-HW-001 to SRS-HW-010 (SRS version 11) and the software item `hw`.
2. Write `hw/feb.toml` and `tools/regmap_gen.py` with its tests; generate
   `minidaq/hw/feb_regs.hpp` and `docs/hw/feb-register-map.md`, and add the test `docs.regmap`
   and the tool list entry TL-25.
3. Add `minidaq/hw/register.hpp` with the compile-time checks of its access rules, `MmioBus` with
   its tests on a `memfd`, and `FakeBoard` with its tests.
4. Add `SlowControl` with its tests at simulated time, and the `hw_fault` event of the flight
   recorder.
5. Add `HardwarePort`, the hardware description and `SlowControlHardware`; make the service
   refuse a start, stop a run and acknowledge on reset; add the `hardware` status field (API 2.2)
   and `minidaq_server --hardware`.
6. Add the service tests with simulated boards and the system test `system.hardware`.
7. Add Exercises 22.1 to 22.4.

**Definition of done.** `ci/run_all.sh` is green on all six presets and static analysis reports
nothing; the trace matrix shows every SRS-HW requirement tested; H-10 is closed in the risk file;
the system test stops a run on a hot board and recovers after an acknowledgment; every starter of
the chapter fails. Tag `ch22`.

## Check yourself {.unnumbered}

1. When do you access a device through a kernel driver, through UIO, and through VFIO? What does
   VFIO protect against that UIO does not?
2. Name three transformations a compiler may make to ordinary memory accesses that would break a
   register access. Which one does `volatile` forbid, and which does it not address?
3. Why is `std::atomic` the wrong tool for device memory, although it is the right one between
   threads?
4. On AArch64, a program writes a DMA descriptor to RAM and then rings a doorbell register. What
   can go wrong without a barrier, and which barrier fixes it?
5. A write to a PCIe register returned. Has the device executed it? How do you find out, and what
   does a read return if the device has gone?
6. Why must a write-1-to-clear register never be written with a read-modify-write? How does
   MiniDAQ make that a compile error?
7. A TMP117 reads `0x8000` right after power-up. What does a slow control that believes it do to
   the bias of a 34 mV/°C SiPM?
8. A detector warms from 24 to 28 °C at a fixed bias of 40.7 V. By how much do its overvoltage and
   its gain change, and what happens to the counts in a fixed energy window?
9. Why does a temperature warning have hysteresis and an alarm latch? What would go wrong with a
   latching warning, and with an alarm that clears itself?
10. Why does the slow control read every register of a board before it decides anything?
11. A supply ramps at 1 V/s. Why is a fixed 5-second deadline for "bias ready" wrong, and how does
    MiniDAQ compute its deadline?
12. Which of these may be retried: writing a setpoint, clearing an error flag, reading a FIFO?
    Why?
13. The service acknowledged a fault and went to idle, and 10 ms later went back to fault although
    the cause was gone. What happened, and how does a sequence number fix it?

## Summary {.unnumbered}

- Linux gives a program its hardware through device files, sysfs and `mmap`: a kernel driver for
  what must be shared, fast and safe; UIO or a PCI resource file for registers from user space;
  VFIO for DMA from user space behind the IOMMU.
- Device registers are accessed with `volatile`, one load or store per access, never with plain
  pointers, atomics or `memcpy`. Barriers order device stores against memory stores where the
  architecture needs it; a missing barrier is an `#error`, not a no-op.
- A PCIe write is posted: it may not have arrived, a lost device loses it silently, and a read of a
  lost device returns all ones.
- A register map has one source, from which the C++ and the document are generated and checked.
  In MiniDAQ each register and field is a type, and the compiler refuses an access the register
  does not allow.
- Sensors are read from their datasheets, with their identities checked and their reset values
  recognized; a reading that cannot be physical is a fault, not a temperature.
- A SiPM's bias follows its temperature to keep the gain constant: 34 mV/°C on 2.7 V of
  overvoltage is 1.3% of gain per degree. MiniDAQ's slow control does it every 100 ms, inside
  fixed limits, with a 5 mV update step.
- Warnings have hysteresis; alarms and faults latch, switch the bias off and wait for an operator.
  The board's own protection is the last layer, not the software.
- The service takes no data while a board is not ready or has a fault, stops a run on a hardware
  fault, and records every board's state in the run record (API 2.2). Everything is tested with a
  simulated board at simulated time.

## Further reading {.unnumbered}

- J. Corbet, A. Rubini and G. Kroah-Hartman, *Linux Device Drivers*, 3rd edition, O'Reilly, 2005,
  free online at lwn.net/Kernel/LDD3/: chapter 9, communicating with hardware (I/O memory and
  barriers). The kernel has changed since; the principles have not.
- The Linux kernel documentation, docs.kernel.org: "The Userspace I/O HOWTO" (UIO), "VFIO -
  Virtual Function I/O", "Linux kernel memory barriers" and "Bus-Independent Device Accesses"
  (`readl`, `writel` and their relaxed forms).
- Arm Limited, *Arm Architecture Reference Manual for A-profile architecture*: memory types and
  attributes, and the `DMB` and `DSB` instructions.
- PCI-SIG, *PCI Express Base Specification*: the ordering rules for posted and non-posted
  transactions.
- Accellera, *SystemRDL 2.0 Register Description Language*, and IEEE 1685 (IP-XACT).
- Texas Instruments, *TMP117 High-Accuracy, Low-Power, Digital Temperature Sensor*, datasheet
  SNOSD82: the temperature result and device ID registers.
- Hamamatsu Photonics, *MPPC (multi-pixel photon counter) S14160/S14161 series*, datasheet:
  breakdown voltage, temperature coefficient and recommended overvoltage.
- onsemi, *J-Series SiPM sensors*, datasheet: the same quantities for another family.
- The libgpiod project, git.kernel.org/pub/scm/libs/libgpiod: the GPIO character device library.
