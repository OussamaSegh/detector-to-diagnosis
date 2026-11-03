// SPDX-License-Identifier: MIT
// Exercise 29.1: a C++ function behind a Python boundary that checks what it is given.
//
// scale_rows(a, factors) returns a new array, a[i, j] * factors[i], for a two-dimensional `a`
// and one factor per row.
#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>

#include <string>

namespace py = pybind11;

namespace {

// [snippet:array]
// C-contiguous float64: an array of another dtype or layout is converted to a new one, so the
// loop below may index it as rows of cols values.
using Array = py::array_t<double, py::array::c_style | py::array::forcecast>;
// [/snippet:array]

std::string shape_of(const py::array& a) {
  std::string s = "(";
  for (py::ssize_t d = 0; d < a.ndim(); ++d) {
    s += (d != 0 ? ", " : "") + std::to_string(a.shape(d));
  }
  return s + (a.ndim() == 1 ? ",)" : ")");
}

Array scale_rows(const Array& a, const Array& factors) {
  if (a.ndim() != 2) {
    throw py::value_error("a must be 2-dimensional, got shape " + shape_of(a));
  }
  if (factors.ndim() != 1 || factors.shape(0) != a.shape(0)) {
    throw py::value_error("factors must hold one value per row of a, " +
                          std::to_string(a.shape(0)) + ", got shape " + shape_of(factors));
  }
  Array out({a.shape(0), a.shape(1)});  // a new array: the caller's is not changed
  const auto in = a.unchecked<2>();
  const auto f = factors.unchecked<1>();
  auto o = out.mutable_unchecked<2>();
  {
    py::gil_scoped_release release;  // no Python object is touched in the loop
    for (py::ssize_t i = 0; i < in.shape(0); ++i) {
      for (py::ssize_t j = 0; j < in.shape(1); ++j) {
        o(i, j) = in(i, j) * f(i);
      }
    }
  }
  return out;
}

}  // namespace

PYBIND11_MODULE(rows, m) {
  m.def("scale_rows", &scale_rows, py::arg("a"), py::arg("factors"),
        "a[i, j] * factors[i], as a new array.");
}
