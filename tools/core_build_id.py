#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prints the build ID of a program as a core dump of it recorded it (Chapter 21).

A core dump says which files the process had mapped (the NT_FILE note) and, for each ELF file
mapped from its start, holds the first page of it, where the linker puts the build ID note. This
tool finds the program's mapping, reads its ELF header and notes from the core's memory, and
prints the build ID in hex. tools/postmortem.sh compares it with the program's and the debug
file's, because a core opened with another build shows plausible and wrong stacks.

Usage: core_build_id.py CORE [PROGRAM]. PROGRAM, a path or a file name, chooses the mapping;
without it, the first file mapped at offset 0. Exit status 0 with the ID, 1 if there is none.
Only 64-bit little-endian cores (x86-64, AArch64).
"""
import pathlib
import struct
import sys

PT_LOAD, PT_NOTE = 1, 4
NT_FILE, NT_GNU_BUILD_ID = 0x46494C45, 3


def notes(data):
    """(name, type, desc) of each note in a note segment."""
    at = 0
    while at + 12 <= len(data):
        namesz, descsz, kind = struct.unpack_from("<III", data, at)
        name = data[at + 12: at + 12 + namesz].rstrip(b"\0")
        desc_at = at + 12 + ((namesz + 3) & ~3)
        yield name, kind, data[desc_at: desc_at + descsz]
        at = desc_at + ((descsz + 3) & ~3)


def program_headers(data, phoff, phnum, phentsize):
    for i in range(phnum):
        p_type, _flags, p_offset, p_vaddr, _paddr, p_filesz, p_memsz, _align = struct.unpack_from(
            "<IIQQQQQQ", data, phoff + i * phentsize)
        yield p_type, p_offset, p_vaddr, p_filesz, p_memsz


class Core:
    def __init__(self, path):
        self.data = pathlib.Path(path).read_bytes()
        if self.data[:4] != b"\x7fELF" or self.data[4] != 2 or self.data[5] != 1:
            raise ValueError(f"{path}: not a 64-bit little-endian ELF file")
        e_type, = struct.unpack_from("<H", self.data, 16)
        if e_type != 4:
            raise ValueError(f"{path}: an ELF file, but not a core dump")
        phoff, = struct.unpack_from("<Q", self.data, 32)
        phentsize, phnum = struct.unpack_from("<HH", self.data, 54)
        self.segments = list(program_headers(self.data, phoff, phnum, phentsize))

    def memory(self, address, size):
        """`size` bytes of the process's memory at `address`, or None if the core lacks them."""
        for p_type, p_offset, p_vaddr, p_filesz, _ in self.segments:
            if p_type == PT_LOAD and p_vaddr <= address and address + size <= p_vaddr + p_filesz:
                return self.data[p_offset + address - p_vaddr: p_offset + address - p_vaddr + size]
        return None

    def files(self):
        """(start address, file name) of each file mapping that begins at the file's offset 0."""
        for p_type, p_offset, _, p_filesz, _ in self.segments:
            if p_type != PT_NOTE:
                continue
            for name, kind, desc in notes(self.data[p_offset: p_offset + p_filesz]):
                if name != b"CORE" or kind != NT_FILE:
                    continue
                count, _page = struct.unpack_from("<QQ", desc, 0)
                ranges = [struct.unpack_from("<QQQ", desc, 16 + 24 * i) for i in range(count)]
                names = desc[16 + 24 * count:].split(b"\0")
                for (start, _end, page_offset), fname in zip(ranges, names):
                    if page_offset == 0:
                        yield start, fname.decode(errors="replace")


# [snippet:build_id]
def build_id(core, program=None):
    for start, fname in core.files():
        if program and fname != program and pathlib.Path(fname).name != pathlib.Path(program).name:
            continue
        header = core.memory(start, 64)
        if header is None or header[:4] != b"\x7fELF":
            continue  # the core did not keep this file's first page
        phoff, = struct.unpack_from("<Q", header, 32)
        phentsize, phnum = struct.unpack_from("<HH", header, 54)
        table = core.memory(start + phoff, phentsize * phnum)
        if table is None:
            continue
        phdrs = list(program_headers(table, 0, phnum, phentsize))
        # The load bias: where the first segment landed, against where the file says it goes.
        first = min(p_vaddr for p_type, _, p_vaddr, _, _ in phdrs if p_type == PT_LOAD)
        bias = start - (first & ~0xFFF)
        for p_type, _, p_vaddr, p_filesz, _ in phdrs:
            seg = core.memory(bias + p_vaddr, p_filesz) if p_type == PT_NOTE else None
            for name, kind, desc in notes(seg or b""):
                if name == b"GNU" and kind == NT_GNU_BUILD_ID:
                    return fname, desc.hex()
        if program:
            return fname, None
    return None, None
# [/snippet:build_id]


def main(argv):
    if len(argv) not in (2, 3):
        print(__doc__.strip().splitlines()[-3], file=sys.stderr)
        return 2
    try:
        fname, bid = build_id(Core(argv[1]), argv[2] if len(argv) == 3 else None)
    except (OSError, ValueError, struct.error) as e:
        print(f"core_build_id: {e}", file=sys.stderr)
        return 2
    if bid is None:
        print(f"core_build_id: no build ID for {fname or 'the program'} in {argv[1]}", file=sys.stderr)
        return 1
    print(bid)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
