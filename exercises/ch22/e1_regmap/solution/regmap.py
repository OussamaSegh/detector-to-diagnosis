# SPDX-License-Identifier: MIT
"""Exercise 22.1: a register map generator (solution)."""
import tomllib

ACCESS = ("ro", "rw", "wo", "rw1c")


class SpecError(Exception):
    pass


def load(text: str) -> dict:
    try:
        spec = tomllib.loads(text)
    except tomllib.TOMLDecodeError as e:
        raise SpecError(f"not valid TOML: {e}") from e
    name = spec.get("map", {}).get("name", "")
    if not str(name).isidentifier():
        raise SpecError("[map] needs a name that is a C++ identifier")
    addresses, names = {}, set()
    for r in spec.get("register", []):
        rname = r.get("name", "")
        if not str(rname).isidentifier() or rname in names:
            raise SpecError(f"register {rname!r}: the name must be a unique identifier")
        names.add(rname)
        addr = r.get("address")
        if not isinstance(addr, int) or addr < 0 or addr % 4:
            raise SpecError(f"register {rname}: the address must be a multiple of 4")
        if addr in addresses:
            raise SpecError(f"register {rname}: address 0x{addr:03X} is also register {addresses[addr]}")
        addresses[addr] = rname
        if r.get("access") not in ACCESS:
            raise SpecError(f"register {rname}: the access must be one of {', '.join(ACCESS)}")
        used, fnames = 0, set()
        for f in r.get("fields", []):
            fname, lsb, width = f.get("name", ""), f.get("lsb"), f.get("width")
            if not str(fname).isidentifier() or fname in fnames:
                raise SpecError(f"register {rname}: field {fname!r} needs a unique name")
            fnames.add(fname)
            if not isinstance(lsb, int) or not isinstance(width, int) or lsb < 0 or width < 1 or lsb + width > 32:
                raise SpecError(f"register {rname}: field {fname} is not inside bits 0 to 31")
            mask = ((1 << width) - 1) << lsb
            if used & mask:
                raise SpecError(f"register {rname}: field {fname} overlaps another field")
            used |= mask
        reset = r.get("reset", 0)
        if not isinstance(reset, int) or reset < 0 or reset & ~used:
            raise SpecError(f"register {rname}: the reset value sets bits outside every field")
    return spec


def header(spec: dict) -> str:
    out = ["// Generated from a register map specification. Do not edit.", "#pragma once", "",
           "#include <cstdint>", "", f"namespace {spec['map']['name']} {{", ""]
    for r in spec.get("register", []):
        reg = r["name"].upper()
        out.append(f"inline constexpr std::uint32_t {reg}_ADDR = 0x{r['address']:03X};")
        out.append(f"inline constexpr std::uint32_t {reg}_RESET = 0x{r.get('reset', 0):08X};")
        for f in r.get("fields", []):
            field = f"{reg}_{f['name'].upper()}"
            mask = ((1 << f["width"]) - 1) << f["lsb"]
            out.append(f"inline constexpr std::uint32_t {field}_SHIFT = {f['lsb']};")
            out.append(f"inline constexpr std::uint32_t {field}_MASK = 0x{mask:08X};")
        out.append("")
    out.append(f"}}  // namespace {spec['map']['name']}")
    return "\n".join(out) + "\n"
