// SPDX-License-Identifier: MIT
// Fuzz target: the calibration table file (Chapter 26; its own target since release 0.7.0).
//
// A table has 18,432 values per array and a CRC-32 over them, so random text never gets past the
// array checks. The first byte therefore chooses between two modes:
//
//   even: the rest of the input is the file's text. Property: a rejection always says why; an
//         accepted table has one entry per crystal, passes CalibrationTable::make() again, and its
//         CRC is that of its coefficients.
//   odd:  the rest is a list of edits to a valid table (one coefficient, one text field of the
//         header, the CRC left stale, or one byte of the written text overwritten). The target
//         writes the edited table as the procedure would and reads it back. Property: unless the
//         text was overwritten, the reader accepts exactly when make() accepts the edited values
//         and the CRC is right, and an accepted table has exactly the values written.
#include <array>
#include <charconv>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <string_view>
#include <type_traits>
#include <utility>
#include <vector>

#include "minidaq/config/calibration_file.hpp"
#include "minidaq/core/crc32.hpp"
#include "minidaq/core/geometry.hpp"

namespace {

using minidaq::CalibrationInfo;
using minidaq::CalibrationTable;
using minidaq::CrystalCalibration;
constexpr std::size_t n = minidaq::ScannerGeometry::num_crystals;

[[noreturn]] void fail() { std::abort(); }

std::string hex32(std::uint32_t v) {
  std::array<char, 9> buf{};
  (void)std::snprintf(buf.data(), buf.size(), "%08x", v);
  return std::string{buf.data()};
}

// Reads the input front to back; past the end every value is zero.
struct Bytes {
  const std::uint8_t* p;
  std::size_t left;
  [[nodiscard]] bool empty() const { return left == 0; }
  std::uint8_t u8() {
    if (left == 0) {
      return 0;
    }
    --left;
    return *p++;
  }
  std::uint32_t u32() {
    std::uint32_t v = 0;
    for (int i = 0; i < 4; ++i) {
      v = (v << 8U) | u8();
    }
    return v;
  }
};

void check_accepted(const CalibrationTable& t) {
  if (t.crystals().size() != n) {
    fail();
  }
  const std::vector<CrystalCalibration> k(t.crystals().begin(), t.crystals().end());
  if (minidaq::crc32(minidaq::canonical_bytes(k)) != t.crc32()) {
    fail();
  }
  if (!CalibrationTable::make(t.info(), k)) {
    fail();  // the reader accepted values that the table's own checks refuse
  }
}

int raw_mode(std::string_view text) {
  const auto r = minidaq::config::parse_calibration(text);
  if (!r) {
    if (r.error().empty()) {
      fail();  // rejected without saying why
    }
    return 0;
  }
  check_accepted(*r);
  return 0;
}

void json_string(std::string& out, std::string_view s) {
  out += '"';
  for (const char c : s) {
    const auto u = static_cast<unsigned char>(c);
    if (c == '"' || c == '\\') {
      out += '\\';
      out += c;
    } else if (u < 0x20U) {
      std::array<char, 8> buf{};
      (void)std::snprintf(buf.data(), buf.size(), "\\u%04x", u);
      out += buf.data();
    } else {
      out += c;
    }
  }
  out += '"';
}

// As the procedure writes a coefficient: the float widened to a double, in the shortest text that
// reads back as that double, with ".0" when it would look like an integer (so -0.0 stays negative).
// A value that is not finite comes out as "nan" or "inf", which is not JSON and must be refused.
template <typename T>
void number(std::string& out, T v) {
  std::array<char, 32> buf{};
  if constexpr (std::is_floating_point_v<T>) {
    const auto [end, ec] =
        std::to_chars(buf.data(), buf.data() + buf.size(), static_cast<double>(v));
    if (ec != std::errc{}) {
      fail();
    }
    const std::string_view t{buf.data(), static_cast<std::size_t>(end - buf.data())};
    out += t;
    if (t.find_first_of(".eEn") == std::string_view::npos) {
      out += ".0";
    }
  } else {
    const auto [end, ec] = std::to_chars(buf.data(), buf.data() + buf.size(), v);
    if (ec != std::errc{}) {
      fail();
    }
    out.append(buf.data(), end);
  }
}

template <typename T>
void array(std::string& out, const char* key, const std::vector<CrystalCalibration>& k,
           T CrystalCalibration::*member) {
  out += '"';
  out += key;
  out += "\":[";
  for (std::size_t i = 0; i < k.size(); ++i) {
    if (i != 0) {
      out += ',';
    }
    number(out, k[i].*member);
  }
  out += ']';
}

std::string write_table(const CalibrationInfo& info, const std::vector<CrystalCalibration>& k,
                        const std::string& crc) {
  std::string out = R"({"schema_version":"1.0","id":)";
  json_string(out, info.id);
  out += ",\"version\":" + std::to_string(info.version) + ",\"scanner_serial\":";
  json_string(out, info.scanner_serial);
  out += ",\"created_utc\":";
  json_string(out, info.created_utc);
  out += ",\"valid_until_utc\":";
  json_string(out, info.valid_until_utc);
  out += ",\"reference_temperature_c\":25.0,\"procedure\":";
  json_string(out, info.procedure);
  out += ",\"crystals\":" + std::to_string(n) + ",\"energy\":{";
  array(out, "a_kev", k, &CrystalCalibration::a_kev);
  out += ',';
  array(out, "b_kev", k, &CrystalCalibration::b_kev);
  out += ',';
  array(out, "q_kev", k, &CrystalCalibration::q_kev);
  out += "},\"time\":{";
  array(out, "offset_ps", k, &CrystalCalibration::time_offset_ps);
  out += "},\"crc32\":\"" + crc + "\"}";
  return out;
}

// Printable ASCII only: other bytes are the raw mode's business (the JSON reader refuses text that
// is not UTF-8, which make() would not know about).
std::string short_text(Bytes& in) {
  const std::size_t len = in.u8() % 24U;
  std::string s;
  for (std::size_t i = 0; i < len; ++i) {
    s += static_cast<char>(0x20 + in.u8() % 95);
  }
  return s;
}

int edit_mode(Bytes in) {
  CalibrationInfo info{
      "CAL-0001",        1, "MDQ-REF-0001", "2026-11-03T08:00:00Z", "2026-12-03T08:00:00Z", 25.0,
      "CP-026 version 1"};
  std::vector<CrystalCalibration> k(n);
  bool stale_crc = false;
  std::vector<std::pair<std::uint32_t, std::uint8_t>> overwrites;
  for (int ops = 0; ops < 64 && !in.empty(); ++ops) {
    const std::uint8_t op = in.u8() % 9U;
    const std::size_t i = ((std::size_t{in.u8()} << 8U) | in.u8()) % n;
    switch (op) {
      case 0:
      case 1:
      case 2: {
        const std::uint32_t bits = in.u32();
        float v = 0.0F;
        std::memcpy(&v, &bits, sizeof v);
        // Half the time a value near a real one, so that the limits are reached from inside.
        if ((bits & 1U) != 0U) {
          v = static_cast<float>(static_cast<std::int32_t>(bits) % 4096) / 64.0F;
        }
        (op == 0 ? k[i].a_kev : op == 1 ? k[i].b_kev : k[i].q_kev) = v;
        break;
      }
      case 3:
        k[i].time_offset_ps = static_cast<std::int32_t>(in.u32());
        if ((k[i].time_offset_ps & 1) != 0) {
          k[i].time_offset_ps %= 6000;
        }
        break;
      case 4:
        info.id = short_text(in);
        break;
      case 5:
        info.scanner_serial = short_text(in);
        break;
      case 6:
        (i % 2 == 0 ? info.created_utc : info.valid_until_utc) = short_text(in);
        break;
      case 7:
        stale_crc = true;
        break;
      default:
        overwrites.emplace_back(in.u32(), in.u8());
        break;
    }
  }
  // Whether the table holds a value that is not finite is a property of the values it ends with: a
  // later edit can overwrite a NaN (MDQ-PR-057).
  bool finite = true;
  for (const auto& c : k) {
    finite = finite && std::isfinite(c.a_kev) && std::isfinite(c.b_kev) && std::isfinite(c.q_kev);
  }
  const std::uint32_t good = minidaq::crc32(minidaq::canonical_bytes(k));
  const std::uint32_t written = stale_crc ? good ^ 0x5a5a5a5aU : good;
  std::string text = write_table(info, k, hex32(written));
  for (const auto& [pos, byte] : overwrites) {
    text[pos % text.size()] = static_cast<char>(byte);
  }

  const auto r = minidaq::config::parse_calibration(text);
  if (!r && r.error().empty()) {
    fail();
  }
  if (r) {
    check_accepted(*r);
  }
  if (!overwrites.empty()) {
    return 0;  // the text may be anything now: only the properties of raw_mode hold
  }
  const bool expected = finite && !stale_crc && CalibrationTable::make(info, k).has_value();
  if (r.has_value() != expected) {
    fail();
  }
  if (r) {
    if (!(r->info() == info)) {
      fail();
    }
    for (std::size_t j = 0; j < n; ++j) {
      if (!(r->crystals()[j] == k[j])) {
        fail();  // a value did not survive writing and reading
      }
    }
  }
  return 0;
}

}  // namespace

extern "C" int LLVMFuzzerTestOneInput(const std::uint8_t* data, std::size_t size) {
  if (size == 0) {
    return 0;
  }
  if ((data[0] & 1U) == 0U) {
    return raw_mode({reinterpret_cast<const char*>(data + 1), size - 1});
  }
  return edit_mode(Bytes{data + 1, size - 1});
}
