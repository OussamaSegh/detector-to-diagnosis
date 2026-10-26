// SPDX-License-Identifier: MIT
// MiniDAQ - registers in mapped device memory (Chapter 22).
//
// A PCIe board exposes its registers in a BAR; the kernel lets a user-space program map it,
// through a UIO device (/dev/uioN, map N at offset N * page size) or the BAR's sysfs file
// (/sys/bus/pci/devices/DDDD:BB:DD.F/resource0), or through VFIO for a program that also needs
// DMA and interrupts with an IOMMU. Once mapped, a register is a 32-bit location that the
// program reads and writes with ordinary instructions. Two things make it different from
// memory:
//   - Every access has an effect the compiler cannot see: a read of a status register can
//     change it, a write starts something. The accesses go through a volatile pointer, so the
//     compiler emits each of them, once, in program order.
//   - The processor may still reorder them against ordinary memory (a descriptor written to
//     RAM before the doorbell write that tells the device to read it). write_barrier() orders
//     every earlier store before every later store as the device sees them.
// volatile is not a tool for threads; std::atomic is. Here it is the right tool, and the only
// one: the C++ memory model says nothing about devices.
#pragma once

#include <cstddef>
#include <cstdint>
#include <memory>
#include <string>

#include "minidaq/core/expected.hpp"
#include "minidaq/hw/register.hpp"

namespace minidaq::hw {

// Orders every store before it ahead of every store after it, as a device sees them: a
// compiler barrier on x86-64, whose stores to normal and uncached memory are not reordered with
// each other; dmb oshst on AArch64 (what Linux's dma_wmb() is there).
void write_barrier() noexcept;

// [snippet:mmio]
class MmioBus final : public RegisterBus {
 public:
  // Maps `size` bytes of `path` from byte `offset` (a multiple of the page size).
  [[nodiscard]] static Expected<std::unique_ptr<MmioBus>, std::string> open(const std::string& path,
                                                                            std::size_t size,
                                                                            std::size_t offset = 0);
  // The same for an open file descriptor, which the bus does not close (tests map a memfd).
  [[nodiscard]] static Expected<std::unique_ptr<MmioBus>, std::string> map(int fd, std::size_t size,
                                                                           std::size_t offset = 0);
  ~MmioBus() override;
  MmioBus(const MmioBus&) = delete;
  MmioBus& operator=(const MmioBus&) = delete;
  MmioBus(MmioBus&&) = delete;
  MmioBus& operator=(MmioBus&&) = delete;

  [[nodiscard]] Expected<std::uint32_t, HwError> read32(std::uint32_t address) override;
  HwStatus write32(std::uint32_t address, std::uint32_t value) override;

 private:
  MmioBus(volatile std::uint32_t* base, std::size_t size, int fd_to_close);
  volatile std::uint32_t* base_;
  std::size_t size_;
  int fd_to_close_;
};
// [/snippet:mmio]

}  // namespace minidaq::hw
