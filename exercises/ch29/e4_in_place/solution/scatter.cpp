// SPDX-License-Identifier: MIT
// Exercise 29.4, a solution: write into the caller's array, without a copy and without the GIL.
//
// scatter_add(values, index, out) adds values[k] to out[index[k]] for every k, in the caller's
// own array `out`, as a backprojection adds each line's value to its pixels. It returns None.
#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>

#include <cstdint>
#include <string>

namespace py = pybind11;

namespace {

// The inputs may be converted: a copy of an input changes nothing the caller sees.
using In = py::array_t<double, py::array::c_style | py::array::forcecast>;
using Index = py::array_t<std::int64_t, py::array::c_style | py::array::forcecast>;

// The output may not: a converted copy would take the sums and be thrown away. So `out` arrives
// as any object, and is accepted only if it is a NumPy array that is already what the C++
// writes: float64, C-contiguous and writeable. Then the C++ writes the caller's own memory.
py::array writable_float64(const py::object& obj) {
  if (!py::isinstance<py::array>(obj)) {
    throw py::type_error("out must be a NumPy array, got " +
                         std::string(py::str(py::type::of(obj).attr("__name__"))));
  }
  auto out = py::reinterpret_borrow<py::array>(obj);
  if (!out.dtype().is(py::dtype::of<double>())) {
    throw py::value_error("out must be float64, got " + std::string(py::str(out.dtype())));
  }
  if ((out.flags() & py::array::c_style) == 0) {
    throw py::value_error("out must be C-contiguous: a converted copy would not reach you");
  }
  if (!out.writeable()) {
    throw py::value_error("out is read-only");
  }
  return out;
}

void scatter_add(const In& values, const Index& index, const py::object& out_obj) {
  if (values.ndim() != 1 || index.ndim() != 1 || values.size() != index.size()) {
    throw py::value_error("values and index must be one-dimensional and of the same length");
  }
  py::array out = writable_float64(out_obj);
  auto* o = static_cast<double*>(out.mutable_data());
  const py::ssize_t n = out.size();
  const double* v = values.data();
  const std::int64_t* idx = index.data();
  // Every index is checked before the first write, so a refused call changes nothing.
  for (py::ssize_t k = 0; k < index.size(); ++k) {
    if (idx[k] < 0 || idx[k] >= n) {
      throw py::index_error("index[" + std::to_string(k) + "] = " + std::to_string(idx[k]) +
                            ", out has " + std::to_string(n) + " elements");
    }
  }
  // The arrays stay alive (this call holds them), and no Python object is touched meanwhile.
  py::gil_scoped_release release;
  for (py::ssize_t k = 0; k < index.size(); ++k) {
    o[idx[k]] += v[k];
  }
}

}  // namespace

PYBIND11_MODULE(scatter, m) {
  m.def("scatter_add", &scatter_add, py::arg("values"), py::arg("index"), py::arg("out"),
        "out[index[k]] += values[k] for every k, in place.");
}
