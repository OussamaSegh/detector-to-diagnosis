// SPDX-License-Identifier: MIT
#include "minidaq/hw/mmio_bus.hpp"

#include <fcntl.h>
#include <sys/mman.h>
#include <unistd.h>

#include <cerrno>
#include <cstring>

namespace minidaq::hw {

void write_barrier() noexcept {
#if defined(__x86_64__)
  asm volatile("" ::: "memory");
#elif defined(__aarch64__)
  asm volatile("dmb oshst" ::: "memory");
#else
#error "write_barrier() needs the store barrier of this architecture"
#endif
}

MmioBus::MmioBus(volatile std::uint32_t* base, std::size_t size, int fd_to_close)
    : base_{base}, size_{size}, fd_to_close_{fd_to_close} {}

MmioBus::~MmioBus() {
  // NOLINTNEXTLINE(cppcoreguidelines-pro-type-const-cast): munmap takes the address as void*
  (void)::munmap(const_cast<std::uint32_t*>(base_), size_);
  if (fd_to_close_ >= 0) {
    (void)::close(fd_to_close_);
  }
}

namespace {

Expected<volatile std::uint32_t*, std::string> map_region(int fd, std::size_t size,
                                                          std::size_t offset) {
  const auto page = static_cast<std::size_t>(::sysconf(_SC_PAGESIZE));
  if (size == 0 || size % 4 != 0) {
    return Unexpected{std::string{"the size must be a positive multiple of 4"}};
  }
  if (offset % page != 0) {
    return Unexpected{"the offset must be a multiple of the page size (" + std::to_string(page) +
                      ")"};
  }
  void* p =
      ::mmap(nullptr, size, PROT_READ | PROT_WRITE, MAP_SHARED, fd, static_cast<off_t>(offset));
  if (p == MAP_FAILED) {
    // NOLINTNEXTLINE(concurrency-mt-unsafe): opened once, at startup
    return Unexpected{std::string{"mmap: "} + std::strerror(errno)};
  }
  return static_cast<volatile std::uint32_t*>(p);
}

}  // namespace

Expected<std::unique_ptr<MmioBus>, std::string> MmioBus::open(const std::string& path,
                                                              std::size_t size,
                                                              std::size_t offset) {
  // O_SYNC: on the sysfs resource files of x86 this asks for an uncached mapping.
  const int fd = ::open(path.c_str(), O_RDWR | O_SYNC | O_CLOEXEC);
  if (fd < 0) {
    // NOLINTNEXTLINE(concurrency-mt-unsafe): opened once, at startup
    return Unexpected{path + ": " + std::strerror(errno)};
  }
  auto base = map_region(fd, size, offset);
  if (!base) {
    (void)::close(fd);
    return Unexpected{path + ": " + base.error()};
  }
  return std::unique_ptr<MmioBus>(new MmioBus(*base, size, fd));
}

Expected<std::unique_ptr<MmioBus>, std::string> MmioBus::map(int fd, std::size_t size,
                                                             std::size_t offset) {
  auto base = map_region(fd, size, offset);
  if (!base) {
    return Unexpected{base.error()};
  }
  return std::unique_ptr<MmioBus>(new MmioBus(*base, size, -1));
}

// [snippet:mmio-access]
Expected<std::uint32_t, HwError> MmioBus::read32(std::uint32_t address) {
  if (address % 4 != 0 || std::size_t{address} + 4 > size_) {
    return Unexpected{HwError{HwErrc::bad_address, address}};
  }
  // One volatile load: emitted exactly once, never merged, cached in a register or moved
  // across another volatile access.
  const std::uint32_t value =
      base_[address / 4];  // NOLINT(cppcoreguidelines-pro-bounds-pointer-arithmetic)
  return value;
}

HwStatus MmioBus::write32(std::uint32_t address, std::uint32_t value) {
  if (address % 4 != 0 || std::size_t{address} + 4 > size_) {
    return {HwError{HwErrc::bad_address, address}};
  }
  base_[address / 4] = value;  // NOLINT(cppcoreguidelines-pro-bounds-pointer-arithmetic)
  return {};
}
// [/snippet:mmio-access]

}  // namespace minidaq::hw
