// SPDX-License-Identifier: MIT
// Python bindings of the C++ projector (Chapter 29, ADR 0024): the module recon_cpp, built with
// pybind11. Its Projector has the interface of tools/recon/project.py's Projector, so the same
// tests and the same OSEM run on both.
//
// The boundary is where a Python mistake becomes a C++ crash, so every array is checked here:
// its dtype, its number of dimensions, its shape and its views (SRS-REC-005). An array of another
// dtype or layout is converted (a copy), never reinterpreted. The computation runs without the
// GIL, on copies the C++ owns or on arrays this call keeps alive.
#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>  // std::optional and std::vector from None and lists

#include <cstddef>
#include <optional>
#include <stdexcept>
#include <string>
#include <vector>

#include "recon/joseph.hpp"

namespace py = pybind11;

namespace {

// C-contiguous float64, converting if it must ("forcecast"): what the C++ reads.
using Array = py::array_t<double, py::array::c_style | py::array::forcecast>;

// [snippet:check]
void require_shape(const Array& a, const char* what, std::size_t rows, std::size_t cols) {
  if (a.ndim() != 2 || static_cast<std::size_t>(a.shape(0)) != rows ||
      static_cast<std::size_t>(a.shape(1)) != cols) {
    std::string got;
    for (py::ssize_t d = 0; d < a.ndim(); ++d) {
      got += (d != 0 ? " x " : "") + std::to_string(a.shape(d));
    }
    throw py::value_error(std::string(what) + " must be " + std::to_string(rows) + " x " +
                          std::to_string(cols) + ", got " + (got.empty() ? "a scalar" : got));
  }
}

std::vector<std::size_t> view_list(const recon::JosephProjector& p,
                                   const std::optional<std::vector<long long>>& views) {
  std::vector<std::size_t> out;
  if (!views) {
    out.resize(p.views());
    for (std::size_t v = 0; v < out.size(); ++v) out[v] = v;
    return out;
  }
  out.reserve(views->size());
  for (const long long v : *views) {
    if (v < 0 || static_cast<std::size_t>(v) >= p.views()) {
      throw py::index_error("view " + std::to_string(v) + " of " + std::to_string(p.views()));
    }
    out.push_back(static_cast<std::size_t>(v));
  }
  return out;
}
// [/snippet:check]

class Projector {
 public:
  Projector(const Array& s_mm, const Array& phi, std::size_t n, double pixel_mm, unsigned threads)
      : p_(make(s_mm, phi, n, pixel_mm)), threads_(threads) {}

  // [snippet:forward]
  Array forward(const Array& image, const std::optional<std::vector<long long>>& views) const {
    require_shape(image, "image", p_.n(), p_.n());
    const std::vector<std::size_t> vs = view_list(p_, views);
    Array out({static_cast<py::ssize_t>(vs.size()), static_cast<py::ssize_t>(p_.bins())});
    {
      // The arrays stay alive (this call holds them); no Python object is touched meanwhile.
      py::gil_scoped_release release;
      p_.forward({image.data(), static_cast<std::size_t>(image.size())}, vs,
                 {out.mutable_data(), static_cast<std::size_t>(out.size())}, threads_);
    }
    return out;
  }
  // [/snippet:forward]

  Array back(const Array& sino, const std::optional<std::vector<long long>>& views) const {
    const std::vector<std::size_t> vs = view_list(p_, views);
    require_shape(sino, "sinogram", vs.size(), p_.bins());
    Array out({static_cast<py::ssize_t>(p_.n()), static_cast<py::ssize_t>(p_.n())});
    {
      py::gil_scoped_release release;
      p_.back({sino.data(), static_cast<std::size_t>(sino.size())}, vs,
              {out.mutable_data(), static_cast<std::size_t>(out.size())}, threads_);
    }
    return out;
  }

  std::size_t n() const { return p_.n(); }
  double pixel_mm() const { return p_.pixel_mm(); }
  py::tuple shape() const { return py::make_tuple(p_.views(), p_.bins()); }
  unsigned threads() const { return threads_; }

 private:
  static recon::JosephProjector make(const Array& s_mm, const Array& phi, std::size_t n,
                                     double pixel_mm) {
    if (s_mm.ndim() != 2) {
      throw py::value_error("s_mm must be views x bins");
    }
    const auto views = static_cast<std::size_t>(s_mm.shape(0));
    const auto bins = static_cast<std::size_t>(s_mm.shape(1));
    require_shape(phi, "phi", views, bins);
    return {{s_mm.data(), views * bins}, {phi.data(), views * bins}, views, bins, n, pixel_mm};
  }

  recon::JosephProjector p_;
  unsigned threads_;
};

}  // namespace

PYBIND11_MODULE(recon_cpp, m) {
  m.doc() = "The C++ projector of tools/recon (Chapter 29): Joseph's method and its adjoint.";
  py::class_<Projector>(m, "Projector")
      .def(py::init<const Array&, const Array&, std::size_t, double, unsigned>(), py::arg("s_mm"),
           py::arg("phi"), py::arg("n") = 128, py::arg("pixel_mm") = 2.0, py::arg("threads") = 0)
      .def("forward", &Projector::forward, py::arg("image"), py::arg("views") = py::none(),
           "The line integrals of every line, or of the given views only.")
      .def("back", &Projector::back, py::arg("sino"), py::arg("views") = py::none(),
           "The adjoint: each line's value spread over its pixels with its weights.")
      .def_property_readonly("n", &Projector::n)
      .def_property_readonly("pixel_mm", &Projector::pixel_mm)
      .def_property_readonly("shape", &Projector::shape)
      .def_property_readonly("threads", &Projector::threads);
  // std::invalid_argument and std::out_of_range from the C++ become ValueError and IndexError.
}
