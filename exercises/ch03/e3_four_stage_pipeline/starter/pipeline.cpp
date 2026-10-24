// SPDX-License-Identifier: MIT
// Exercise 3.3 starter. Suggested structure:
//  1. Create three bounded queues (decode->sort, sort->pair, pair->write),
//     sized up front. minidaq::Channel<T> gives you pre-allocated batches.
//  2. Start four std::jthread objects, consumers first.
//  3. Each stage loops: receive a batch (or finish when the input is closed
//     and drained), process it while timing only the processing, publish,
//     update its StageReport. Each report is written by one thread only;
//     read them after joining the threads.
//  4. Close each output when the stage finishes so the next one can drain.
#include "pipeline.hpp"

namespace ex {

Result run_pipeline(std::span<const std::uint64_t> words, const Config& cfg, const WriteCallback& on_write) {
  Result r;
  r.stages = {StageReport{"decode"}, StageReport{"sort"}, StageReport{"pair"}, StageReport{"write"}};
  // TODO: build the pipeline.
  return r;
}

}  // namespace ex
