// SPDX-License-Identifier: MIT
// Exercise 31.3: the per-crystal timing histogram in C++, behind a Python boundary.
//
// histogram(crystal, dt_ps, crystals, lo_ps, bin_ps, bins) returns (counts, outside): counts is a
// new uint32 array of shape (crystals, bins) where counts[c, k] is the number of entries of
// crystal c with lo_ps + k * bin_ps <= dt < lo_ps + (k + 1) * bin_ps; outside counts the entries
// whose time falls outside the bins.
#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>

#include <cstdint>
#include <string>

namespace py = pybind11;

namespace {

using Int32Array = py::array_t<std::int32_t, py::array::c_style>;
using Counts = py::array_t<std::uint32_t>;

py::tuple histogram(const Int32Array& crystal, const Int32Array& dt, std::int64_t crystals,
                    std::int64_t lo_ps, std::int64_t bin_ps, std::int64_t bins) {
  if (crystal.ndim() != 1 || dt.ndim() != 1 || crystal.shape(0) != dt.shape(0)) {
    throw py::value_error("crystal and dt_ps must be one-dimensional and of the same length");
  }
  if (crystals < 1 || bins < 1 || bin_ps < 1) {
    throw py::value_error("crystals, bins and bin_ps must be at least 1");
  }
  Counts counts({crystals, bins});
  auto out = counts.mutable_unchecked<2>();
  const auto c = crystal.unchecked<1>();
  const auto t = dt.unchecked<1>();
  std::int64_t outside = 0;
  for (py::ssize_t i = 0; i < crystals; ++i) {
    for (py::ssize_t k = 0; k < bins; ++k) {
      out(i, k) = 0;
    }
  }
  for (py::ssize_t i = 0; i < c.shape(0); ++i) {
    const std::int64_t id = c(i);
    if (id < 0 || id >= crystals) {
      throw py::value_error("entry " + std::to_string(i) + ": crystal not in the scanner");
    }
    const std::int64_t k = (std::int64_t{t(i)} - lo_ps) / bin_ps;
    if (k < 0 || k >= bins) {
      ++outside;
    } else {
      ++out(id, k);
    }
  }
  return py::make_tuple(counts, outside);
}

}  // namespace

PYBIND11_MODULE(dthist, m) {
  m.def("histogram", &histogram, py::arg("crystal"), py::arg("dt_ps"), py::arg("crystals"),
        py::arg("lo_ps"), py::arg("bin_ps"), py::arg("bins"),
        "(counts[crystals, bins], outside): each crystal's histogram of dt_ps.");
  // Whether the module was compiled with optimization (NDEBUG): the speed test is only
  // meaningful then (CAPA-0001, MDQ-PR-047).
#ifdef NDEBUG
  m.attr("optimized") = true;
#else
  m.attr("optimized") = false;
#endif
}
