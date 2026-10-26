// SPDX-License-Identifier: MIT
// MiniDAQ - typed registers of a device (Chapter 22).
//
// A register map says, for every register, its address, who may read and write it, and the
// fields inside it. Code that writes `bus.write32(0x08, 0x3)` knows none of that: a wrong
// address, a write to a read-only register or a read-modify-write of a register whose bits
// clear when written are all compiled without a word. Here each register is a type with its
// address and access in it, each field a type with its position, and the functions below
// accept only what the access allows. The types are generated from the board's specification
// (tools/regmap_gen.py), so the C++ and the specification cannot disagree.
//
// The bus is an interface: MmioBus maps the device's memory (UIO or a PCIe BAR), FakeBoard
// simulates a board in memory for tests. Every access can fail (a board that does not answer, a
// bus error), and the result says so; nothing here throws.
#pragma once

#include <concepts>
#include <cstdint>
#include <string_view>

#include "minidaq/core/expected.hpp"

namespace minidaq::hw {

enum class Access : std::uint8_t {
  ro,    // read only; writes are refused at compile time
  rw,    // read and write
  wo,    // write only: reads return 0 on the device, so reading is refused at compile time
  rw1c,  // read; writing 1 to a bit clears it, writing 0 leaves it
};

enum class HwErrc : std::uint8_t {
  ok,
  timeout,      // the device did not answer in time
  bus_error,    // the access failed (SIGBUS on a vanished device, an I2C NACK, ...)
  bad_address,  // outside the device's register space, or not aligned
};

[[nodiscard]] std::string_view to_string(HwErrc e) noexcept;

struct HwError {
  HwErrc code = HwErrc::ok;
  std::uint32_t address = 0;
  friend bool operator==(const HwError&, const HwError&) = default;
};

// The outcome of a write: no value, maybe an error.
struct [[nodiscard]] HwStatus {
  HwError error{};
  [[nodiscard]] bool ok() const noexcept { return error.code == HwErrc::ok; }
  explicit operator bool() const noexcept { return ok(); }
};

// [snippet:bus]
// 32-bit register accesses to one device. Implementations decide what an access is (a volatile
// load from mapped memory, a transaction on a bus, a simulation) and report every failure.
class RegisterBus {
 public:
  virtual ~RegisterBus() = default;
  [[nodiscard]] virtual Expected<std::uint32_t, HwError> read32(std::uint32_t address) = 0;
  virtual HwStatus write32(std::uint32_t address, std::uint32_t value) = 0;
};
// [/snippet:bus]

// [snippet:types]
template <std::uint32_t Address, Access A, std::uint32_t Reset = 0>
struct Register {
  static_assert(Address % 4 == 0, "registers are 32-bit aligned");
  static constexpr std::uint32_t address = Address;
  static constexpr Access access = A;
  static constexpr std::uint32_t reset = Reset;
};

template <typename Reg, unsigned Lsb, unsigned Width, bool Signed = false>
struct Field {
  static_assert(Width >= 1 && Lsb + Width <= 32, "a field lies inside its 32-bit register");
  using reg = Reg;
  static constexpr unsigned lsb = Lsb;
  static constexpr unsigned width = Width;
  static constexpr bool is_signed = Signed;
  static constexpr std::uint32_t max = Width == 32 ? 0xFFFF'FFFFU : (1U << Width) - 1U;
  static constexpr std::uint32_t mask = max << Lsb;

  // The field's bits of a register value, right-aligned.
  [[nodiscard]] static constexpr std::uint32_t get(std::uint32_t word) noexcept {
    return (word & mask) >> Lsb;
  }
  // The field as a signed number (two's complement of Width bits).
  [[nodiscard]] static constexpr std::int32_t get_signed(std::uint32_t word) noexcept
    requires Signed
  {
    const std::uint32_t raw = get(word);
    const std::uint32_t sign = 1U << (Width - 1);
    return static_cast<std::int32_t>(raw ^ sign) - static_cast<std::int32_t>(sign);
  }
  // `word` with the field set to `value`; a value wider than the field is cut to its bits,
  // which fits() lets a caller check first.
  [[nodiscard]] static constexpr std::uint32_t set(std::uint32_t word,
                                                   std::uint32_t value) noexcept {
    return (word & ~mask) | ((value << Lsb) & mask);
  }
  [[nodiscard]] static constexpr bool fits(std::uint32_t value) noexcept { return value <= max; }
};
// [/snippet:types]

// One row of a generated map's table, for dumps and simulators.
struct RegisterInfo {
  std::string_view name;
  std::uint32_t address;
  Access access;
  std::uint32_t reset;
};

template <typename R>
concept Readable = R::access == Access::ro || R::access == Access::rw || R::access == Access::rw1c;
template <typename R>
concept Writable = R::access == Access::rw || R::access == Access::wo;
template <typename R>
concept ReadModifyWrite = R::access == Access::rw;
template <typename R>
concept WriteOneToClear = R::access == Access::rw1c;

// [snippet:access]
template <typename R>
  requires Readable<R>
[[nodiscard]] Expected<std::uint32_t, HwError> read(RegisterBus& bus) {
  return bus.read32(R::address);
}

template <typename F>
  requires Readable<typename F::reg>
[[nodiscard]] Expected<std::uint32_t, HwError> read_field(RegisterBus& bus) {
  auto word = bus.read32(F::reg::address);
  if (!word) {
    return Unexpected{word.error()};
  }
  return F::get(*word);
}

template <typename R>
  requires Writable<R>
HwStatus write(RegisterBus& bus, std::uint32_t value) {
  return bus.write32(R::address, value);
}

// Read, change one field, write back. Only for rw registers: on an rw1c register the write back
// would clear every flag that was set, and a wo register cannot be read.
template <typename F>
  requires ReadModifyWrite<typename F::reg>
HwStatus write_field(RegisterBus& bus, std::uint32_t value) {
  auto word = bus.read32(F::reg::address);
  if (!word) {
    return {word.error()};
  }
  return bus.write32(F::reg::address, F::set(*word, value));
}

// Clears the flags in `bits` (a mask of the register's bits) of an rw1c register, and only those.
template <typename R>
  requires WriteOneToClear<R>
HwStatus clear(RegisterBus& bus, std::uint32_t bits) {
  return bus.write32(R::address, bits);
}
// [/snippet:access]

}  // namespace minidaq::hw
