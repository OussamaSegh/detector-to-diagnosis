// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <nlohmann/json.hpp>

#include "minidaq/control/run_integrity.hpp"

using namespace minidaq::control;
using nlohmann::json;

namespace {

// A status as AcquisitionService::status() reports it after a clean run.
json clean_status() {
  return json::parse(R"({
    "state": "configured", "fault": null,
    "detector_counters": {"packets_received": 10, "packets_lost": 0, "packets_stale": 3,
                          "sequence_resyncs": 0, "rejected_bad_magic": 0, "rejected_too_short": 0},
    "sink_counters": {"coincidences": 5, "invalid": 0, "time_resets": 0, "energies_clamped": 0,
                      "blocks_dropped": 0},
    "stages": [{"name": "source", "dropped": 0, "filtered": 0}, {"name": "decode", "dropped": 0, "filtered": 0},
               {"name": "sort", "dropped": 0, "filtered": 4}],
    "late_singles": 0,
    "sorter": {"singles_in": 20, "energy_rejected": 4, "out_of_order": 0}
  })");
}

}  // namespace

TEST(RunIntegrity, ACleanRunIsComplete) {
  // REQ: SRS-CTL-030
  const json v = assess_integrity(clean_status());
  EXPECT_EQ(v["complete"], true);
  EXPECT_TRUE(v["losses"].empty());
}

TEST(RunIntegrity, EveryLossCounterMakesTheRunIncomplete) {
  // REQ: SRS-CTL-030
  for (const char* ptr : {"/detector_counters/packets_lost", "/detector_counters/sequence_resyncs",
                          "/detector_counters/rejected_bad_magic", "/stages/0/dropped", "/stages/1/dropped",
                          "/stages/1/filtered", "/stages/2/dropped",
                          "/late_singles", "/sorter/out_of_order", "/sink_counters/invalid",
                          "/sink_counters/energies_clamped", "/sink_counters/blocks_dropped"}) {
    json s = clean_status();
    s[json::json_pointer{ptr}] = 2U;
    const json v = assess_integrity(s);
    EXPECT_EQ(v["complete"], false) << ptr;
    ASSERT_EQ(v["losses"].size(), 1U) << ptr;
    EXPECT_EQ(v["losses"][0]["counter"], ptr);
    EXPECT_EQ(v["losses"][0]["count"], 2);
  }
}

TEST(RunIntegrity, CountersThatAreNotLossesDoNotCount) {
  // REQ: SRS-CTL-030
  // Stale packets are duplicates, or packets already counted as lost; energy
  // rejection is selection and time resets are ordering, not loss. The sort
  // stage filters by energy and order, which the sorter's own counters split.
  json s = clean_status();
  s["stages"][2]["filtered"] = 100U;
  s["detector_counters"]["packets_stale"] = 100U;
  s["sorter"]["energy_rejected"] = 100U;
  s["sink_counters"]["time_resets"] = 100U;
  EXPECT_EQ(assess_integrity(s)["complete"], true);
}

TEST(RunIntegrity, AFaultMakesTheRunIncompleteWithoutALossCounter) {
  // REQ: SRS-CTL-030
  json s = clean_status();
  s["fault"] = "sink: write: No space left on device";
  const json v = assess_integrity(s);
  EXPECT_EQ(v["complete"], false);
  EXPECT_TRUE(v["losses"].empty());
}

TEST(RunIntegrity, ALossCounterOfAnotherTypeCountsAsALoss) {
  // REQ: SRS-CTL-030
  json s = clean_status();
  s["late_singles"] = "unknown";
  EXPECT_EQ(assess_integrity(s)["complete"], false);
  s["late_singles"] = -1;
  EXPECT_EQ(assess_integrity(s)["complete"], false);
}

TEST(RunIntegrity, MissingPortsCountAsNoLoss) {
  // REQ: SRS-CTL-030
  EXPECT_EQ(assess_integrity(json::parse(R"({"state": "idle", "fault": null})"))["complete"], true);
}
