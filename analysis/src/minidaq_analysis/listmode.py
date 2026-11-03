# SPDX-License-Identifier: MIT
"""MDQ-L1 list-mode files (docs/formats/mdq-l1.md) through a memory map.

``tools/recon/listmode.py`` reads a whole file into memory, which is right for the 2D
reconstruction of a short run. A run of the scanner is many segments of up to 1 GiB each, more
than the memory of the laptop it is analyzed on. Here a file is mapped, not read: the operating
system pages in the bytes that are touched and may drop them again. Opening a file reads only the
file header and the 32-byte header of each block. The records are numpy views of the mapped bytes,
decoded one chunk of whole blocks at a time, so the memory a pass over a run needs is set by the
chunk size, not by the run.

The reader is strict, as the reconstruction's is: a file that is not intact is an error, not a
partial result. Recovering a damaged run is a separate step that needs a person (MDQ-L1 section 7,
Exercise 12.5).
"""
from __future__ import annotations

import json
import mmap
import pathlib
import zlib
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import numpy as np
import numpy.typing as npt

FILE_MAGIC = b"MDQL\r\n\x1a\n"
BLOCK_MAGIC = b"MDQB"
MAX_METADATA_BYTES = 1 << 20
MAX_BLOCK_RECORDS = 65_536
FLAG_END_OF_RUN = 1
FLAG_END_OF_FILE = 2
TAG_CRYSTAL = 0x7FFF
DELAYED_BIT = 0x8000
ENERGY_LSB_KEV = 1.0 / 32.0

# [snippet:dtypes]
# One record, exactly as it is on disk: little-endian fields, no padding, 16 bytes.
RECORD = np.dtype([("time_offset", "<u4"), ("crystal_a", "<u2"), ("crystal_b", "<u2"),
                   ("dt_ps", "<i4"), ("energy_a", "<u2"), ("energy_b", "<u2")])
# One block header, 32 bytes.
BLOCK_HEADER = np.dtype([("magic", "S4"), ("sequence", "<u4"), ("record_count", "<u4"),
                         ("flags", "<u4"), ("base_time_ps", "<i8"), ("payload_crc", "<u4"),
                         ("header_crc", "<u4")])
# [/snippet:dtypes]
assert RECORD.itemsize == 16 and BLOCK_HEADER.itemsize == 32


class FormatError(ValueError):
    """A file that is not a complete, intact MDQ-L1 file."""


@dataclass(frozen=True)
class Coincidences:
    """Decoded coincidences, one array per field, all of the same length. Tags are left out.

    time_ps is the earlier single's time, crystal_a the earlier single's crystal and crystal_b the
    later one's; dt_ps is the later time minus the earlier, so it is never negative, and a delayed
    coincidence's dt_ps includes the delay."""

    time_ps: npt.NDArray[np.int64]
    crystal_a: npt.NDArray[np.int32]
    crystal_b: npt.NDArray[np.int32]
    delayed: npt.NDArray[np.bool_]
    dt_ps: npt.NDArray[np.int32]
    energy_a_kev: npt.NDArray[np.float32]
    energy_b_kev: npt.NDArray[np.float32]

    def __len__(self) -> int:
        return int(self.time_ps.size)

    def select(self, mask: npt.NDArray[np.bool_]) -> Coincidences:
        return Coincidences(*(getattr(self, f)[mask] for f in _FIELDS))

    @staticmethod
    def concatenate(parts: list[Coincidences]) -> Coincidences:
        if not parts:
            return decode(np.zeros(0, dtype=RECORD), np.zeros(0, dtype=np.int64))[0]
        return Coincidences(*(np.concatenate([getattr(p, f) for p in parts]) for f in _FIELDS))


_FIELDS = ("time_ps", "crystal_a", "crystal_b", "delayed", "dt_ps", "energy_a_kev",
           "energy_b_kev")


# [snippet:decode]
def decode(records: npt.NDArray[np.void],
           base_ps: npt.NDArray[np.int64]) -> tuple[Coincidences, int]:
    """(coincidences, number of tags) of raw records and each record's block base time."""
    a = records["crystal_a"]
    crystal = a & np.uint16(~DELAYED_BIT & 0xFFFF)
    event = crystal != TAG_CRYSTAL
    tags = int(event.size - np.count_nonzero(event))
    r, base, a, crystal = records[event], base_ps[event], a[event], crystal[event]
    return Coincidences(
        time_ps=base + r["time_offset"].astype(np.int64),
        crystal_a=crystal.astype(np.int32),
        crystal_b=r["crystal_b"].astype(np.int32),
        delayed=(a & np.uint16(DELAYED_BIT)) != 0,
        dt_ps=r["dt_ps"].astype(np.int32),
        energy_a_kev=r["energy_a"].astype(np.float32) * np.float32(ENERGY_LSB_KEV),
        energy_b_kev=r["energy_b"].astype(np.float32) * np.float32(ENERGY_LSB_KEV),
    ), tags
# [/snippet:decode]


@dataclass(frozen=True)
class BlockIndex:
    """Where each block's records are: byte offset of the first record, count and base time."""

    offset: npt.NDArray[np.int64]
    count: npt.NDArray[np.int64]
    base_time_ps: npt.NDArray[np.int64]


def _pad8(n: int) -> int:
    return (n + 7) & ~7


class ListModeFile:
    """One MDQ-L1 file, mapped read-only. Use it as a context manager, or call close().

    Opening checks the file header and walks the block headers; with verify=True (the default) it
    also checks every block's payload CRC, which reads the whole file once, sequentially."""

    def __init__(self, path: str | pathlib.Path, verify: bool = True) -> None:
        self.path = pathlib.Path(path)
        with open(self.path, "rb") as f:
            size = f.seek(0, 2)
            if size < 40:
                raise FormatError(f"{self.path}: {size} bytes, shorter than a file header")
            self._map = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            self.metadata, self.header_bytes = self._read_header()
            self.index, self.closing_flags = self._walk_blocks(verify)
        except BaseException:
            self.close()
            raise

    def close(self) -> None:
        # A numpy view of the records still held by a caller keeps the map open (mmap refuses to
        # close under exported buffers); the map then closes when the last view goes.
        try:
            self._map.close()
        except BufferError:
            pass

    def __enter__(self) -> ListModeFile:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    @property
    def records_total(self) -> int:
        return int(self.index.count.sum())

    @property
    def ends_run(self) -> bool:
        return self.closing_flags == FLAG_END_OF_RUN

    def _u32(self, at: int) -> int:
        return int.from_bytes(self._map[at:at + 4], "little")

    def _read_header(self) -> tuple[dict[str, Any], int]:
        m = self._map
        if m[:8] != FILE_MAGIC:
            raise FormatError(f"{self.path}: not an MDQ-L1 file")
        major = int.from_bytes(m[8:10], "little")
        if major != 1:
            raise FormatError(f"{self.path}: format version {major}, this reader reads 1")
        header_bytes, meta_bytes = self._u32(12), self._u32(16)
        if meta_bytes > MAX_METADATA_BYTES or header_bytes != 40 + _pad8(meta_bytes):
            raise FormatError(f"{self.path}: header size {header_bytes} for metadata of "
                              f"{meta_bytes} bytes")
        if len(m) < header_bytes:
            raise FormatError(f"{self.path}: shorter than its header")
        if self._u32(header_bytes - 8) != zlib.crc32(m[:header_bytes - 8]):
            raise FormatError(f"{self.path}: file header CRC")
        if self._u32(20) != 0 or self._u32(24) != RECORD.itemsize or self._u32(28) != 0:
            raise FormatError(f"{self.path}: flags, record size or reserved field")
        try:
            meta = json.loads(bytes(m[32:32 + meta_bytes]).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            raise FormatError(f"{self.path}: metadata is not JSON: {e}") from None
        if not isinstance(meta, dict):
            raise FormatError(f"{self.path}: metadata is not a JSON object")
        return meta, header_bytes

    # [snippet:walk]
    def _walk_blocks(self, verify: bool) -> tuple[BlockIndex, int]:
        offsets: list[int] = []
        counts: list[int] = []
        bases: list[int] = []
        at, seq, size = self.header_bytes, 0, len(self._map)
        closing = 0
        while at < size:
            if closing:
                raise FormatError(f"{self.path}: data after the closing block, at byte {at}")
            if at + 32 > size:
                raise FormatError(f"{self.path}: block {seq} at byte {at}: header cut short")
            h = np.frombuffer(self._map, dtype=BLOCK_HEADER, count=1, offset=at)[0]
            where = f"{self.path}: block {seq} at byte {at}"
            if h["magic"] != BLOCK_MAGIC or int(h["header_crc"]) != zlib.crc32(
                    self._map[at:at + 28]):
                raise FormatError(f"{where}: no intact block header")
            n, flags = int(h["record_count"]), int(h["flags"])
            if int(h["sequence"]) != seq:
                raise FormatError(f"{where}: sequence number {int(h['sequence'])}")
            if n > MAX_BLOCK_RECORDS or flags & ~(FLAG_END_OF_RUN | FLAG_END_OF_FILE):
                raise FormatError(f"{where}: record count {n} or flags {flags:#x}")
            end = at + 32 + RECORD.itemsize * n
            if end > size:
                raise FormatError(f"{where}: {n} records do not fit in the file")
            if verify and int(h["payload_crc"]) != zlib.crc32(self._map[at + 32:end]):
                raise FormatError(f"{where}: records CRC")
            if n == 0:
                if flags in (FLAG_END_OF_RUN, FLAG_END_OF_FILE):
                    closing = flags
            else:
                offsets.append(at + 32)
                counts.append(n)
                bases.append(int(h["base_time_ps"]))
            at, seq = end, seq + 1
        if not closing:
            raise FormatError(f"{self.path}: no closing block: the file was not completed")
        return BlockIndex(np.array(offsets, dtype=np.int64), np.array(counts, dtype=np.int64),
                          np.array(bases, dtype=np.int64)), closing
    # [/snippet:walk]

    def block_records(self, i: int) -> npt.NDArray[np.void]:
        """The raw records of block i: a read-only view of the mapped file, no copy."""
        return np.frombuffer(self._map, dtype=RECORD, count=int(self.index.count[i]),
                             offset=int(self.index.offset[i]))

    # [snippet:chunks]
    def chunks(self, max_records: int = 1 << 20) -> Iterator[tuple[Coincidences, int]]:
        """(coincidences, tags) of consecutive whole blocks, about max_records records at a time
        (one block more when a single block is larger)."""
        if max_records < 1:
            raise ValueError("max_records must be at least 1")
        i, nblocks = 0, len(self.index.count)
        while i < nblocks:
            j, n = i, 0
            while j < nblocks and (j == i or n + int(self.index.count[j]) <= max_records):
                n += int(self.index.count[j])
                j += 1
            records = np.concatenate([self.block_records(k) for k in range(i, j)])
            base = np.repeat(self.index.base_time_ps[i:j], self.index.count[i:j])
            yield decode(records, base)
            i = j
    # [/snippet:chunks]

    def coincidences(self) -> Coincidences:
        """Every coincidence of the file, decoded into memory (about 30 bytes per record)."""
        return Coincidences.concatenate([c for c, _ in self.chunks()])


class Run:
    """A whole run: its run record (``<prefix>-<run>.run.json``) and the files it lists."""

    def __init__(self, record_path: str | pathlib.Path) -> None:
        self.record_path = pathlib.Path(record_path)
        self.record: dict[str, Any] = json.loads(self.record_path.read_text())
        if self.record.get("format") != "MDQ-L1 run record":
            raise FormatError(f"{self.record_path}: not an MDQ-L1 run record")
        files = self.record.get("files")
        if not isinstance(files, list) or not files:
            raise FormatError(f"{self.record_path}: the run has no files")
        self.files = [self.record_path.parent / str(f) for f in files]

    def chunks(self, max_records: int = 1 << 20,
               verify: bool = True) -> Iterator[tuple[Coincidences, int]]:
        """The run's coincidences in time order, file after file. Every file but the last must
        end with 'end of file', the last with 'end of run'."""
        for k, path in enumerate(self.files):
            with ListModeFile(path, verify=verify) as f:
                last = k == len(self.files) - 1
                if f.ends_run != last:
                    raise FormatError(f"{path}: closing flag does not match its place in the run")
                yield from f.chunks(max_records)

    def coincidences(self) -> Coincidences:
        return Coincidences.concatenate([c for c, _ in self.chunks()])
