// SPDX-License-Identifier: MIT
#include "minidaq/config/acquisition_config.hpp"

#include <algorithm>
#include <bit>
#include <charconv>
#include <cmath>
#include <initializer_list>
#include <limits>
#include <set>

#include <nlohmann/json.hpp>

#include "object_reader.hpp"

namespace minidaq::config {
namespace {

using nlohmann::json;

using detail::ObjectReader;
using detail::parse_version;

constexpr double max_rate_hz = 1e9;

}  // namespace

Expected<AcquisitionConfig, ConfigErrors> config_from_json(const json& doc) {
  ConfigErrors errors;
  AcquisitionConfig c;
  ObjectReader top{doc, "", errors};

  // [snippet:version]
  std::string version;
  top.get("schema_version", version);
  if (doc.is_object() && !doc.contains("schema_version")) {
    errors.push_back({"/schema_version", "is required"});
  } else if (!version.empty()) {
    if (!parse_version(version, c.schema_major, c.schema_minor)) {
      errors.push_back({"/schema_version", "must look like \"1.0\""});
    } else if (c.schema_major != supported_major) {
      errors.push_back({"/schema_version", "major version " + std::to_string(c.schema_major) +
                                                " is not supported (this program reads " +
                                                std::to_string(supported_major) + ".x)"});
    } else if (c.schema_minor > supported_minor) {
      errors.push_back({"/schema_version", "written for a newer MiniDAQ (" + version + " > " +
                                                std::to_string(supported_major) + "." +
                                                std::to_string(supported_minor) + ")"});
    }
  }
  // [/snippet:version]
  top.get("description", c.description);
  top.get("rt_profile", c.rt_profile);
  top.get("stop_after_s", c.stop_after_s, 0.0, 7.0 * 24 * 3600);

  if (const json* src = top.object("source")) {
    ObjectReader r{*src, top.child("source"), errors};
    r.get("type", c.source.type, {"synthetic", "udp"});
    r.get("rate_hz", c.source.rate_hz, 1.0, max_rate_hz);
    r.get("pair_fraction", c.source.pair_fraction, 0.0, 1.0);
    r.get("seed", c.source.seed, std::uint64_t{0}, std::numeric_limits<std::uint64_t>::max());
    if (const json* u = r.object("udp")) {
      ObjectReader ur{*u, r.child("udp"), errors};
      auto& udp = c.source.udp;
      ur.get("address", udp.address);
      // Read as 64 bits and narrow after the range check: get<std::uint16_t>()
      // would wrap 70000 to 4464 before the check could see it.
      std::uint64_t port = udp.port;
      ur.get("port", port, std::uint64_t{0}, std::uint64_t{65535});
      udp.port = static_cast<std::uint16_t>(port);
      ur.get("receive_buffer_bytes", udp.receive_buffer_bytes, std::size_t{1} << 16, std::size_t{1} << 30);
      ur.get("reorder_window_packets", udp.reorder_window_packets, std::size_t{1}, std::size_t{4096});
      if (!std::has_single_bit(udp.reorder_window_packets)) {
        errors.push_back({"/source/udp/reorder_window_packets", "must be a power of two"});
      }
      ur.get("max_hold_us", udp.max_hold_us, std::int64_t{1}, std::int64_t{1'000'000});
      ur.finish();
    }
    r.finish();
  }
  if (const json* p = top.object("pipeline")) {
    ObjectReader r{*p, top.child("pipeline"), errors};
    r.get("batch_size", c.pipeline.batch_size, std::size_t{1}, std::size_t{1} << 20);
    r.get("batches_per_channel", c.pipeline.batches_per_channel, std::size_t{2}, std::size_t{4096});
    r.get("coincidence_window_ps", c.pipeline.coincidence_window_ps, std::int64_t{1}, std::int64_t{1'000'000});
    std::string overflow = c.pipeline.overflow == OverflowPolicy::block ? "block" : "drop";
    r.get("overflow", overflow, {"block", "drop"});
    c.pipeline.overflow = overflow == "drop" ? OverflowPolicy::drop : OverflowPolicy::block;
    r.get("max_batch_delay_us", c.pipeline.max_batch_delay_us, std::int64_t{1}, std::int64_t{1'000'000});
    r.finish();
  }
  if (const json* so = top.object("sorter")) {
    ObjectReader r{*so, top.child("sorter"), errors};
    auto& st = c.sorter;
    r.get("delay_ps", st.delay_ps, std::int64_t{0}, std::int64_t{1'000'000'000});
    r.get("mode", st.mode, {"fixed", "per_single"});
    r.get("multiples", st.multiples, {"kill_all", "take_all_goods", "take_winner_of_goods", "keep_if_only_one_good"});
    r.get("energy_low_kev", st.energy_low_kev, 0.0, 10'000.0);
    r.get("energy_high_kev", st.energy_high_kev, 0.0, 10'000.0);
    std::uint64_t sectors = st.min_sector_difference;  // 64 bits first, as for the UDP port
    r.get("min_sector_difference", sectors, std::uint64_t{0}, std::uint64_t{12});
    st.min_sector_difference = static_cast<std::uint32_t>(sectors);
    r.get("fov_radius_mm", st.fov_radius_mm, 0.0, 149.0);
    r.finish();
  }
  if (const json* o = top.object("output")) {
    ObjectReader r{*o, top.child("output"), errors};
    auto& out = c.output;
    r.get("type", out.type, {"none", "listmode"});
    r.get("directory", out.directory);
    r.get("prefix", out.prefix);
    r.get("max_file_mb", out.max_file_mb, std::uint64_t{1}, std::uint64_t{1} << 20);
    r.get("fsync", out.fsync, {"none", "close", "interval"});
    std::uint64_t every = out.fsync_every_blocks;
    r.get("fsync_every_blocks", every, std::uint64_t{1}, std::uint64_t{1} << 20);
    out.fsync_every_blocks = static_cast<std::uint32_t>(every);
    std::uint64_t records = out.records_per_block;
    r.get("records_per_block", records, std::uint64_t{1}, std::uint64_t{65536});
    out.records_per_block = static_cast<std::uint32_t>(records);
    std::uint64_t buffers = out.buffers;
    r.get("buffers", buffers, std::uint64_t{2}, std::uint64_t{65536});
    out.buffers = static_cast<std::uint32_t>(buffers);
    r.get("max_block_delay_ms", out.max_block_delay_ms, std::int64_t{1}, std::int64_t{60'000});
    r.finish();
    if (out.directory.empty()) {
      errors.push_back({"/output/directory", "must not be empty"});
    }
    if (out.prefix.empty() || out.prefix.find('/') != std::string::npos) {
      errors.push_back({"/output/prefix", "must be non-empty and contain no '/'"});
    }
  }
  top.finish();
  // Rules that involve two values, reported at the value a user would change.
  if (c.sorter.delay_ps != 0 && c.sorter.delay_ps <= c.pipeline.coincidence_window_ps) {
    errors.push_back({"/sorter/delay_ps", "must be 0 (off) or more than /pipeline/coincidence_window_ps"});
  }
  if (c.sorter.energy_low_kev > c.sorter.energy_high_kev) {
    errors.push_back({"/sorter/energy_low_kev", "must not exceed /sorter/energy_high_kev"});
  }
  if (c.source.type == "udp" && c.stop_after_s > 0) {
    // stop_after_s is turned into a word count from rate_hz, which a network
    // source does not have: stop a UDP run with the stop command.
    errors.push_back({"/stop_after_s", "is supported only for source type \"synthetic\""});
  }
  if (!errors.empty()) {
    return Unexpected{std::move(errors)};
  }
  return c;
}

Expected<AcquisitionConfig, ConfigErrors> parse_config(std::string_view json_text) {
  // The control plane may use exceptions; the parser's message has the position.
  json doc;
  try {
    doc = json::parse(json_text, nullptr, /*allow_exceptions=*/true, /*ignore_comments=*/true);
  } catch (const json::exception& e) {
    // Not only parse_error: a number too large for a double ("1e999") is an
    // out_of_range exception. Found by fuzz/fuzz_config (Chapter 7).
    return Unexpected{ConfigErrors{{"", std::string{"not valid JSON: "} + e.what()}}};
  }
  return config_from_json(doc);
}

json to_json(const AcquisitionConfig& c) {
  return json{
      {"schema_version", std::to_string(c.schema_major) + "." + std::to_string(c.schema_minor)},
      {"description", c.description},
      {"source",
       {{"type", c.source.type},
        {"rate_hz", c.source.rate_hz},
        {"pair_fraction", c.source.pair_fraction},
        {"seed", c.source.seed},
        {"udp",
         {{"address", c.source.udp.address},
          {"port", c.source.udp.port},
          {"receive_buffer_bytes", c.source.udp.receive_buffer_bytes},
          {"reorder_window_packets", c.source.udp.reorder_window_packets},
          {"max_hold_us", c.source.udp.max_hold_us}}}}},
      {"pipeline",
       {{"batch_size", c.pipeline.batch_size},
        {"batches_per_channel", c.pipeline.batches_per_channel},
        {"coincidence_window_ps", c.pipeline.coincidence_window_ps},
        {"overflow", c.pipeline.overflow == OverflowPolicy::drop ? "drop" : "block"},
        {"max_batch_delay_us", c.pipeline.max_batch_delay_us}}},
      {"sorter",
       {{"delay_ps", c.sorter.delay_ps},
        {"mode", c.sorter.mode},
        {"multiples", c.sorter.multiples},
        {"energy_low_kev", c.sorter.energy_low_kev},
        {"energy_high_kev", c.sorter.energy_high_kev},
        {"min_sector_difference", c.sorter.min_sector_difference},
        {"fov_radius_mm", c.sorter.fov_radius_mm}}},
      {"output",
       {{"type", c.output.type},
        {"directory", c.output.directory},
        {"prefix", c.output.prefix},
        {"max_file_mb", c.output.max_file_mb},
        {"fsync", c.output.fsync},
        {"fsync_every_blocks", c.output.fsync_every_blocks},
        {"records_per_block", c.output.records_per_block},
        {"buffers", c.output.buffers},
        {"max_block_delay_ms", c.output.max_block_delay_ms}}},
      {"rt_profile", c.rt_profile},
      {"stop_after_s", c.stop_after_s},
  };
}

std::string format_errors(const ConfigErrors& errors) {
  std::string out;
  for (const auto& e : errors) {
    out += (e.path.empty() ? std::string{"(document)"} : e.path) + ": " + e.message + "\n";
  }
  return out;
}

PipelineConfig to_pipeline_config(const AcquisitionConfig& c) {
  PipelineConfig p;
  p.batch_size = c.pipeline.batch_size;
  p.batches_per_channel = c.pipeline.batches_per_channel;
  p.sorter.window = Picoseconds{c.pipeline.coincidence_window_ps};
  p.sorter.delay = Picoseconds{c.sorter.delay_ps};
  // The parser accepted only known names, so these cannot fail.
  p.sorter.mode = parse_window_mode(c.sorter.mode).value();
  p.sorter.multiples = parse_multiples_policy(c.sorter.multiples).value();
  p.sorter.energy_low_kev = c.sorter.energy_low_kev;
  p.sorter.energy_high_kev = c.sorter.energy_high_kev;
  p.sorter.min_sector_difference = c.sorter.min_sector_difference;
  p.sorter.fov_radius_mm = c.sorter.fov_radius_mm;
  p.source_overflow = c.pipeline.overflow;
  p.max_batch_delay = std::chrono::microseconds{c.pipeline.max_batch_delay_us};
  if (c.stop_after_s > 0) {
    p.total_words = static_cast<std::uint64_t>(std::llround(c.stop_after_s * c.source.rate_hz));
  }
  return p;
}

}  // namespace minidaq::config
