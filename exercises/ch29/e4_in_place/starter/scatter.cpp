// SPDX-License-Identifier: MIT
// Exercise 29.4: write into the caller's array, without a copy and without the GIL.
//
// scatter_add(values, index, out) adds values[k] to out[index[k]] for every k, in the caller's
// own array `out`, as a backprojection adds each line's value to its pixels. It returns None.
#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>

#include <cstdint>

namespace py = pybind11;

namespace {

using In = py::array_t<double, py::array::c_style | py::array::forcecast>;
using Index = py::array_t<std::int64_t, py::array::c_style | py::array::forcecast>;

// `out` is converted like the inputs, so any array is accepted.
void scatter_add(const In& values, const Index& index, In out) {
  const double* v = values.data();
  const std::int64_t* idx = index.data();
  double* o = out.mutable_data();
  for (py::ssize_t k = 0; k < values.size(); ++k) {
    o[idx[k]] += v[k];
  }
}

}  // namespace

PYBIND11_MODULE(scatter, m) {
  m.def("scatter_add", &scatter_add, py::arg("values"), py::arg("index"), py::arg("out"),
        "out[index[k]] += values[k] for every k, in place.");
}
