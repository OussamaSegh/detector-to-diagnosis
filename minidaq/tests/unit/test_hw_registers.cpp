// SPDX-License-Identifier: MIT
// Typed registers, the generated map of the front-end board, mapped memory and the simulated
// board (Chapter 22).
#include <gtest/gtest.h>
#include <sys/mman.h>
#include <unistd.h>

#include <cstdint>
#include <map>

#include "minidaq/hw/fake_board.hpp"
#include "minidaq/hw/feb_regs.hpp"
#include "minidaq/hw/mmio_bus.hpp"

using namespace minidaq;
using namespace minidaq::hw;

namespace {

// What each kind of register lets code do is decided at compile time. These are the claims of
// SRS-HW-008, checked by the compiler on every build.
template <typename R>
concept CanWrite = requires(RegisterBus& b) { write<R>(b, 0U); };
template <typename F>
concept CanWriteField = requires(RegisterBus& b) { write_field<F>(b, 0U); };
template <typename R>
concept CanRead = requires(RegisterBus& b) { read<R>(b); };
template <typename R>
concept CanClear = requires(RegisterBus& b) { clear<R>(b, 0U); };

static_assert(!CanWrite<feb::Status>, "a read-only register cannot be written");
static_assert(!CanWrite<feb::BoardId>);
static_assert(CanWrite<feb::BiasSetpoint>);
static_assert(!CanWriteField<feb::ErrorFlags::Overcurrent>,
              "a read-modify-write of a write-1-to-clear register would clear every flag");
static_assert(CanClear<feb::ErrorFlags>);
static_assert(!CanClear<feb::Control>);
static_assert(CanWriteField<feb::Control::BiasEnable>);
static_assert(CanRead<feb::ErrorFlags>);
struct WriteOnly : Register<0x100, Access::wo, 0> {};  // the map of this board has none
static_assert(!CanRead<WriteOnly>, "a write-only register reads as 0 on the device");
static_assert(CanWrite<WriteOnly>);

// A bus over a map, which records every access in order.
class RecordingBus final : public RegisterBus {
 public:
  std::map<std::uint32_t, std::uint32_t> mem;
  std::vector<std::string> log;
  Expected<std::uint32_t, HwError> read32(std::uint32_t a) override {
    log.push_back("r" + std::to_string(a));
    return mem[a];
  }
  HwStatus write32(std::uint32_t a, std::uint32_t v) override {
    log.push_back("w" + std::to_string(a) + "=" + std::to_string(v));
    mem[a] = v;
    return {};
  }
};

// A memfd of one page, mapped by MmioBus as a device's BAR would be.
struct MemfdBus {
  int fd = ::memfd_create("fake-bar", MFD_CLOEXEC);
  std::unique_ptr<MmioBus> bus;
  MemfdBus() {
    EXPECT_GE(fd, 0);
    EXPECT_EQ(::ftruncate(fd, 4096), 0);
    auto b = MmioBus::map(fd, 4096);
    EXPECT_TRUE(b) << b.error();
    bus = std::move(*b);
  }
  ~MemfdBus() { ::close(fd); }
  MemfdBus(const MemfdBus&) = delete;
  MemfdBus& operator=(const MemfdBus&) = delete;
  MemfdBus(MemfdBus&&) = delete;
  MemfdBus& operator=(MemfdBus&&) = delete;
};

}  // namespace

TEST(Registers, FieldsPutTheirBitsWhereTheMapSays) {
  // REQ: SRS-HW-008
  using V = feb::FwVersion;
  const std::uint32_t w = V::Patch::set(V::Minor::set(V::Major::set(0, 2), 7), 513);
  EXPECT_EQ(w, 0x0207'0201U);
  EXPECT_EQ(V::Major::get(w), 2U);
  EXPECT_EQ(V::Minor::get(w), 7U);
  EXPECT_EQ(V::Patch::get(w), 513U);
  // Setting a field leaves the others alone and cuts a value to the field's width.
  EXPECT_EQ(feb::Control::BiasEnable::set(0x8000'0002U, 1), 0x8000'0003U);
  EXPECT_EQ(feb::Threshold::Code::set(0, 0x1FFF), 0x0FFFU);
  EXPECT_FALSE(feb::Threshold::Code::fits(4096));
  EXPECT_TRUE(feb::Threshold::Code::fits(4095));
}

TEST(Registers, ATemperatureIsTwosComplementIn128thsOfADegree) {
  // REQ: SRS-HW-008
  using T = feb::Temperature::CelsiusQ7;
  EXPECT_EQ(T::get_signed(0x0C80), 25 * 128);  // 25.0 C
  EXPECT_EQ(T::get_signed(0xFF80), -128);      // -1.0 C
  EXPECT_EQ(T::get_signed(0x7FFF), 32767);     // the largest, 255.99 C
  EXPECT_EQ(T::get_signed(0x8000), -32768);    // the smallest
  EXPECT_EQ(T::get_signed(0xABCD'0C80U), 25 * 128) << "bits above the field are not part of it";
}

TEST(Registers, TheGeneratedMapMatchesItsSpecification) {
  // REQ: SRS-HW-008
  EXPECT_EQ(feb::registers.size(), 11U);
  EXPECT_EQ(feb::BoardId::Magic::get(feb::BoardId::reset), 0x4D51U);
  EXPECT_EQ(feb::Control::address, 0x008U);
  EXPECT_EQ(feb::Control::SoftReset::mask, 0x8000'0000U);
  EXPECT_EQ(feb::ErrorFlags::access, Access::rw1c);
  EXPECT_EQ(feb::BiasRampRate::reset, 1000U);
  std::uint32_t previous = 0;
  for (std::size_t i = 0; i < feb::registers.size(); ++i) {
    EXPECT_EQ(feb::registers[i].address % 4, 0U) << feb::registers[i].name;
    if (i > 0) {
      EXPECT_GT(feb::registers[i].address, previous) << feb::registers[i].name;
    }
    previous = feb::registers[i].address;
  }
}

TEST(Registers, AFieldWriteReadsTheRegisterAndWritesItBackOnce) {
  // REQ: SRS-HW-008
  RecordingBus bus;
  bus.mem[feb::Control::address] = 0x2;  // trigger on
  ASSERT_TRUE(write_field<feb::Control::BiasEnable>(bus, 1));
  EXPECT_EQ(bus.mem[feb::Control::address], 0x3U) << "the trigger stays on";
  EXPECT_EQ(bus.log, (std::vector<std::string>{"r8", "w8=3"}));
  bus.log.clear();
  ASSERT_TRUE(clear<feb::ErrorFlags>(bus, feb::ErrorFlags::Overcurrent::mask));
  EXPECT_EQ(bus.log, (std::vector<std::string>{"w16=1"}))
      << "a clear is one write, never a read first";
}

TEST(MmioBus, EachAccessIsOneLoadOrStoreAtTheRegistersOffset) {
  // REQ: SRS-HW-009
  MemfdBus m;
  ASSERT_TRUE(m.bus);
  ASSERT_TRUE(write<feb::BiasSetpoint>(*m.bus, 40'700));
  // The same memory seen through a second mapping, as the device would see it.
  void* p = ::mmap(nullptr, 4096, PROT_READ, MAP_SHARED, m.fd, 0);
  ASSERT_NE(p, MAP_FAILED);
  const auto* words = static_cast<const std::uint32_t*>(p);
  EXPECT_EQ(words[feb::BiasSetpoint::address / 4],
            40'700U);  // NOLINT(cppcoreguidelines-pro-bounds-pointer-arithmetic)
  ::munmap(p, 4096);
  auto v = read_field<feb::BiasSetpoint::Millivolts>(*m.bus);
  ASSERT_TRUE(v);
  EXPECT_EQ(*v, 40'700U);
}

TEST(MmioBus, RefusesAccessesOutsideTheMapOrNotAligned) {
  // REQ: SRS-HW-009
  MemfdBus m;
  ASSERT_TRUE(m.bus);
  EXPECT_EQ(m.bus->read32(4096).error(), (HwError{HwErrc::bad_address, 4096}));
  EXPECT_EQ(m.bus->read32(4094).error().code, HwErrc::bad_address);
  EXPECT_EQ(m.bus->read32(2).error().code, HwErrc::bad_address);
  EXPECT_EQ(m.bus->write32(4092, 1).error.code, HwErrc::ok);
  EXPECT_EQ(m.bus->write32(4093, 1).error.code, HwErrc::bad_address);
  EXPECT_FALSE(MmioBus::map(m.fd, 4096, 100)) << "the offset must be a multiple of the page size";
  EXPECT_FALSE(MmioBus::open("/nonexistent/uio9", 4096));
}

TEST(FakeBoard, RampsTheBiasAtTheProgrammedRateAndReportsReady) {
  // REQ: SRS-HW-002
  std::int64_t now = 0;
  FakeBoard board{3, [&] { return now; }};
  ASSERT_TRUE(write<feb::BiasRampRate>(board, 10'000));  // 10 V/s
  ASSERT_TRUE(write<feb::BiasSetpoint>(board, 40'000));
  EXPECT_DOUBLE_EQ(board.bias_volts(), 0.0) << "the setpoint alone does not switch the bias on";
  ASSERT_TRUE(write_field<feb::Control::BiasEnable>(board, 1));
  now += 2'000'000'000;  // 2 s: 20 V of 40
  auto status = read<feb::Status>(board);
  ASSERT_TRUE(status);
  EXPECT_EQ(feb::Status::BiasRamping::get(*status), 1U);
  EXPECT_EQ(feb::Status::BiasReady::get(*status), 0U);
  EXPECT_NEAR(*read_field<feb::BiasMonitor::Millivolts>(board), 20'000, 1);
  now += 2'000'000'000;
  status = read<feb::Status>(board);
  EXPECT_EQ(feb::Status::BiasReady::get(*status), 1U);
  EXPECT_EQ(feb::BoardId::Slot::get(*read<feb::BoardId>(board)), 3U);
}

TEST(FakeBoard, KeepsTheRulesOfEachRegister) {
  // REQ: SRS-HW-008
  std::int64_t now = 0;
  FakeBoard board{0, [&] { return now; }};
  board.set_temperature(61.0);  // the board's own protection trips and sets a sticky flag
  auto errors = read<feb::ErrorFlags>(board);
  EXPECT_EQ(feb::ErrorFlags::OvertempTrip::get(*errors), 1U);
  board.set_temperature(30.0);
  EXPECT_EQ(feb::ErrorFlags::OvertempTrip::get(*read<feb::ErrorFlags>(board)), 1U) << "sticky";
  ASSERT_TRUE(clear<feb::ErrorFlags>(board, feb::ErrorFlags::Overcurrent::mask));
  EXPECT_EQ(feb::ErrorFlags::OvertempTrip::get(*read<feb::ErrorFlags>(board)), 1U)
      << "only the written bit clears";
  ASSERT_TRUE(clear<feb::ErrorFlags>(board, feb::ErrorFlags::OvertempTrip::mask));
  EXPECT_EQ(*read<feb::ErrorFlags>(board), 0U);
  // A write to a read-only register changes nothing; SOFT_RESET resets and reads as 0.
  ASSERT_TRUE(board.write32(feb::BiasMonitor::address, 12'345));
  EXPECT_EQ(*read<feb::BiasMonitor>(board), 0U);
  ASSERT_TRUE(write<feb::Threshold>(board, 0x123));
  ASSERT_TRUE(write<feb::Control>(board, feb::Control::SoftReset::mask | 0x2));
  EXPECT_EQ(*read<feb::Control>(board), 0U);
  EXPECT_EQ(*read<feb::Threshold>(board), feb::Threshold::reset);
  EXPECT_EQ(board.read32(0x044).error().code, HwErrc::bad_address);
}

TEST(FakeBoard, FailsLikeRealBoardsFail) {
  // REQ: SRS-HW-004
  std::int64_t now = 0;
  FakeBoard board{1, [&] { return now; }};
  board.set_fault(BoardFault::unresponsive);
  EXPECT_EQ(read<feb::Status>(board).error(), (HwError{HwErrc::timeout, feb::Status::address}));
  EXPECT_EQ(write<feb::BiasSetpoint>(board, 1).error.code, HwErrc::timeout);
  board.set_fault(BoardFault::vanished);
  EXPECT_EQ(*read<feb::BoardId>(board), 0xFFFF'FFFFU) << "a PCIe read of a device that has gone";
  EXPECT_TRUE(write<feb::BiasSetpoint>(board, 1)) << "posted writes are lost without an error";
  board.set_fault(BoardFault::weak_supply);
  ASSERT_TRUE(write<feb::BiasRampRate>(board, 50'000));
  ASSERT_TRUE(write<feb::BiasSetpoint>(board, 40'000));
  ASSERT_TRUE(write_field<feb::Control::BiasEnable>(board, 1));
  now += 2'000'000'000;
  const auto status = *read<feb::Status>(board);
  EXPECT_EQ(feb::Status::BiasFault::get(status), 1U);
  EXPECT_EQ(feb::Status::BiasReady::get(status), 0U);
  EXPECT_NEAR(board.bias_volts(), 38.0, 0.001);
}
