// SPDX-License-Identifier: MIT
// Exercise 29.1: a C++ function behind a Python boundary that checks what it is given.
//
// scale_rows(a, factors) returns a new array, a[i, j] * factors[i], for a two-dimensional `a`
// and one factor per row.
#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>

namespace py = pybind11;

namespace {

// Scales each row in place and returns the array: no copy, so it is fast.
py::array_t<double> scale_rows(py::array_t<double> a, const py::array_t<double>& factors) {
  const py::ssize_t rows = a.shape(0);
  const py::ssize_t cols = a.shape(1);
  double* data = a.mutable_data();
  const double* f = factors.data();
  for (py::ssize_t i = 0; i < rows; ++i) {
    for (py::ssize_t j = 0; j < cols; ++j) {
      data[(i * cols) + j] *= f[i];
    }
  }
  return a;
}

}  // namespace

PYBIND11_MODULE(rows, m) {
  m.def("scale_rows", &scale_rows, py::arg("a"), py::arg("factors"),
        "a[i, j] * factors[i], as a new array.");
}
