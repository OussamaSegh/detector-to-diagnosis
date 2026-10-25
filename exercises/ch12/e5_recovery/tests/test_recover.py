# SPDX-License-Identifier: MIT
import json
import os
import shutil
import struct
import tempfile
import unittest
import zlib

import recover as rc

RUN = "minidaq-20261025T101500Z"


def block(seq, records, flags=0):
    """records: (time_ps, crystal_a, crystal_b) in time order."""
    base = records[0][0] if records else 0
    payload = b"".join(struct.pack("<IHHiHH", t - base, a, b, 100, 16352, 16352) for t, a, b in records)
    head = struct.pack("<4sIIIqI", b"MDQB", seq, len(records), flags, base, zlib.crc32(payload))
    return head + struct.pack("<I", zlib.crc32(head)) + payload


def file_header(segment):
    meta = json.dumps({"format": "MDQ-L1", "file": {"segment": segment, "run_name": RUN}}).encode()
    meta += bytes(-len(meta) % 8)
    head = b"MDQL\r\n\x1a\n" + struct.pack("<HHIIIII", 1, 0, 40 + len(meta), len(meta), 0, 16, 0) + meta
    return head + struct.pack("<II", zlib.crc32(head), 0)


class Writer:
    """Writes segments the way the sink does: blocks of `per_block` records, 1 us apart."""

    def __init__(self, directory, per_block=50):
        self.dir, self.per_block, self.t = directory, per_block, 0

    def records(self):
        out = []
        for _ in range(self.per_block):
            self.t += 1_000_000
            out.append((self.t, self.t % 1000, (self.t // 1000) % 1000 + 1000))
        return out

    def segment(self, n, blocks, closing=rc.END_OF_FILE, part=False):
        data = file_header(n) + b"".join(block(i, self.records()) for i in range(blocks))
        if closing:
            data += block(blocks, [], closing)
        name = f"{RUN}-{n:04d}.mdql" + (".part" if part else "")
        with open(os.path.join(self.dir, name), "wb") as f:
            f.write(data)
        return name


def read_run(directory):
    """An independent check: (records, flags of each file's last block, torn bytes) per file."""
    out = {}
    for name in sorted(os.listdir(directory)):
        with open(os.path.join(directory, name), "rb") as f:
            data = f.read()
        pos, n, flags = struct.unpack_from("<I", data, 12)[0], 0, None
        while pos + 32 <= len(data):
            _m, _s, k, fl, _b, pcrc, hcrc = struct.unpack_from("<4sIIIqII", data, pos)
            end = pos + 32 + 16 * k
            if zlib.crc32(data[pos : pos + 28]) != hcrc or end > len(data) or zlib.crc32(data[pos + 32 : end]) != pcrc:
                break
            n, flags, pos = n + k, fl, end
        out[name] = (n, flags, len(data) - pos)
    return out


def slurp(path):
    with open(path, "rb") as f:
        return f.read()


def snapshot(directory):
    return {n: slurp(os.path.join(directory, n)) for n in sorted(os.listdir(directory))}


class Recover(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="mdq-recover-")
        self.w = Writer(self.dir)

    def tearDown(self):
        shutil.rmtree(self.dir)

    def only(self):
        reports = rc.recover(self.dir)
        self.assertEqual(len(reports), 1)
        return reports[0]

    def test_a_clean_run_is_left_alone(self):
        self.w.segment(0, 4)
        self.w.segment(1, 4)
        self.w.segment(2, 2, closing=rc.END_OF_RUN)
        before = snapshot(self.dir)
        r = self.only()
        self.assertEqual((r.segments, r.records, r.clean, r.actions, r.problems), (3, 500, True, [], []))
        self.assertEqual(snapshot(self.dir), before)

    def test_a_torn_last_block_is_cut_and_the_run_closed(self):
        self.w.segment(0, 4)
        name = self.w.segment(1, 3, closing=0, part=True)
        with open(os.path.join(self.dir, name), "ab") as f:
            f.write(block(3, self.w.records())[:500])  # the crash: half a block on the disk
        r = self.only()
        self.assertEqual(r.problems, [])
        self.assertEqual(r.records, 350)
        files = read_run(self.dir)
        self.assertEqual(sorted(files), [f"{RUN}-0000.mdql", f"{RUN}-0001.mdql"], "renamed, nothing left over")
        self.assertEqual(files[f"{RUN}-0001.mdql"], (150, rc.END_OF_RUN, 0), "cut at the last intact block")
        again = self.only()
        self.assertEqual((again.clean, again.actions, again.records), (True, [], 350), "recovering twice is harmless")

    def test_a_block_of_the_right_length_is_not_enough(self):
        # A power loss can leave the block's length on the disk and not its contents.
        self.w.segment(0, 2)
        name = self.w.segment(1, 2, closing=0, part=True)
        b = bytearray(block(2, self.w.records()))
        b[32:] = bytes(len(b) - 32)
        with open(os.path.join(self.dir, name), "ab") as f:
            f.write(bytes(b))
        r = self.only()
        self.assertEqual(r.records, 200)
        self.assertEqual(read_run(self.dir)[f"{RUN}-0001.mdql"], (100, rc.END_OF_RUN, 0))

    def test_closed_but_not_renamed(self):
        # The crash came between the closing block and the rename.
        self.w.segment(0, 3, closing=rc.END_OF_RUN, part=True)
        r = self.only()
        self.assertEqual(r.records, 150)
        data = slurp(os.path.join(self.dir, f"{RUN}-0000.mdql"))
        self.assertEqual(data.count(b"MDQB"), 4, "three blocks and one closing block, not two")

    def test_a_header_that_never_made_it(self):
        self.w.segment(0, 3)
        with open(os.path.join(self.dir, f"{RUN}-0001.mdql.part"), "wb") as f:
            f.write(file_header(1)[:20])
        r = self.only()
        self.assertEqual((r.segments, r.records, r.problems), (1, 150, []))
        self.assertEqual(sorted(os.listdir(self.dir)), [f"{RUN}-0000.mdql"])
        self.assertFalse(r.clean, "the run ended in a crash, not with an end of run")

    def test_a_missing_segment_stops_everything(self):
        self.w.segment(0, 2)
        self.w.segment(2, 2)
        self.w.segment(3, 1, closing=0, part=True)
        before = snapshot(self.dir)
        r = self.only()
        self.assertTrue(any("0001" in p for p in r.problems), r.problems)
        self.assertEqual(snapshot(self.dir), before, "a run with a hole needs a person, not a repair")

    def test_two_partial_files(self):
        self.w.segment(0, 2, closing=0, part=True)
        self.w.segment(1, 2, closing=0, part=True)
        before = snapshot(self.dir)
        r = self.only()
        self.assertNotEqual(r.problems, [])
        self.assertEqual(snapshot(self.dir), before)

    def test_a_damaged_complete_file(self):
        name = self.w.segment(0, 3)
        self.w.segment(1, 1, closing=0, part=True)
        path = os.path.join(self.dir, name)
        data = bytearray(slurp(path))
        data[-200] ^= 0x10
        with open(path, "wb") as f:
            f.write(bytes(data))
        before = snapshot(self.dir)
        r = self.only()
        self.assertTrue(any(name in p for p in r.problems), r.problems)
        self.assertEqual(snapshot(self.dir), before)

    def test_dry_run(self):
        self.w.segment(0, 2, closing=0, part=True)
        before = snapshot(self.dir)
        r = rc.recover(self.dir, dry_run=True)[0]
        self.assertEqual(len(r.actions), 1)
        self.assertEqual(snapshot(self.dir), before)


if __name__ == "__main__":
    unittest.main()
