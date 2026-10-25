# SPDX-License-Identifier: MIT
"""Exercise 12.5: put a directory of list-mode files back in order after a crash.

The list-mode sink writes each file as <prefix>-<run>-<NNNN>.mdql.part and
renames it to .mdql once its closing block is written and synced, so after a
crash a run is some complete segments and at most one .part file, the segment
that was being written, which ends with a block that may be torn. recover()
makes such a run readable again without losing a record that was on the disk,
and refuses to touch a directory that is not in a state a crash can produce.

    python3 recover.py DIR [--dry-run]
"""
import dataclasses
import os
import re
import struct
import sys
import zlib

FILE_MAGIC = b"MDQL\r\n\x1a\n"
BLOCK_MAGIC = b"MDQB"
END_OF_RUN = 0x1
END_OF_FILE = 0x2
NAME = re.compile(r"^(?P<run>.+)-(?P<segment>[0-9]{4})\.mdql(?P<part>\.part)?$")


def header_size(data):
    """The file header's size, None if it is torn (the file is shorter than its header),
    or raises ValueError if it is complete and damaged."""
    if len(data) < 40 or len(data) < struct.unpack_from("<I", data, 12)[0]:
        return None
    header_bytes = struct.unpack_from("<I", data, 12)[0]
    if data[:8] != FILE_MAGIC or struct.unpack_from("<H", data, 8)[0] != 1:
        raise ValueError("not an MDQ-L1 version 1 file")
    if zlib.crc32(data[: header_bytes - 8]) != struct.unpack_from("<I", data, header_bytes - 8)[0]:
        raise ValueError("damaged file header")
    return header_bytes


def closing_block(sequence, flags):
    """An empty block: what the sink writes last in every file."""
    head = struct.pack("<4sIIIqI", BLOCK_MAGIC, sequence, 0, flags, 0, zlib.crc32(b""))
    return head + struct.pack("<I", zlib.crc32(head))


@dataclasses.dataclass
class Prefix:
    end: int = 0          # bytes of the file that are header and complete, intact blocks
    blocks: int = 0       # intact blocks, the closing block included
    records: int = 0
    last_flags: int = 0   # of the last intact block
    torn: bool = False    # bytes after `end` that are not an intact block


# [snippet:prefix]
def intact_prefix(data, header_bytes):
    """How much of a file can be trusted: its blocks in order from the header, up to the
    first one that is incomplete or damaged."""
    p = Prefix(end=header_bytes)
    pos = header_bytes
    while pos < len(data):
        if len(data) - pos < 32:
            break
        magic, seq, n, flags, _base, pcrc, hcrc = struct.unpack_from("<4sIIIqII", data, pos)
        end = pos + 32 + 16 * n
        if (magic != BLOCK_MAGIC or zlib.crc32(data[pos : pos + 28]) != hcrc or seq != p.blocks
                or end > len(data) or zlib.crc32(data[pos + 32 : end]) != pcrc):
            break
        p.blocks, p.records, p.last_flags = p.blocks + 1, p.records + n, flags
        pos = p.end = end
        if flags & (END_OF_RUN | END_OF_FILE):
            break  # nothing may follow a closing block
    p.torn = p.end < len(data)
    return p
# [/snippet:prefix]


@dataclasses.dataclass
class RunReport:
    run: str
    segments: int = 0
    records: int = 0
    clean: bool = False          # the run had ended with an end-of-run block before this call
    actions: list = dataclasses.field(default_factory=list)   # what this call changed, or would
    problems: list = dataclasses.field(default_factory=list)  # for a person; if any, nothing was changed


def _sync_dir(directory):
    fd = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _check_run(directory, run, files):
    """Reads every file of one run; returns (report, plan) where plan lists the repairs."""
    rep, plan = RunReport(run), []
    segments = sorted(files)
    parts = [s for s in segments if files[s]]
    if len(parts) > 1:
        rep.problems.append(f"{len(parts)} partial files ({', '.join(f'{s:04d}' for s in parts)}): "
                            "a crash leaves at most one")
    if parts and parts[0] != segments[-1]:
        rep.problems.append(f"segment {parts[0]:04d} is partial but a later segment exists")
    missing = sorted(set(range(segments[-1] + 1)) - set(segments))
    if missing:
        rep.problems.append("missing segment" + ("s " if len(missing) > 1 else " ")
                            + ", ".join(f"{s:04d}" for s in missing))
    for s in segments:
        name = f"{run}-{s:04d}.mdql" + (".part" if files[s] else "")
        path = os.path.join(directory, name)
        with open(path, "rb") as f:
            data = f.read()
        try:
            hb = header_size(data)
        except ValueError as e:
            rep.problems.append(f"{name}: {e}")
            continue
        if hb is None:
            if files[s] and s == segments[-1]:
                plan.append(("remove", path, None))  # created, header not yet written: no records
                rep.actions.append(f"remove {name}: torn header, no records")
            else:
                rep.problems.append(f"{name}: shorter than its header")
            continue
        p = intact_prefix(data, hb)
        rep.segments += 1
        rep.records += p.records
        closed = bool(p.last_flags & (END_OF_RUN | END_OF_FILE)) and p.blocks > 0
        if not files[s]:
            if p.torn or not closed:
                rep.problems.append(f"{name}: a complete file that does not end with an intact closing block")
            elif p.last_flags & END_OF_RUN and s != segments[-1]:
                rep.problems.append(f"{name}: the run ended here but later segments exist")
            elif s == segments[-1] and p.last_flags & END_OF_RUN:
                rep.clean = True
            continue
        if closed:  # crashed between the closing block and the rename
            plan.append(("finish", path, (p.end, None)))
            rep.actions.append(f"rename {name}: already closed")
        else:
            plan.append(("finish", path, (p.end, closing_block(p.blocks, END_OF_RUN))))
            what = f"cut {len(data) - p.end} bytes, " if p.torn else ""
            rep.actions.append(f"recover {name}: {what}{p.records} records kept, end of run added")
    return rep, plan


def recover(directory, dry_run=False):
    """One report per run in `directory`, in name order."""
    runs = {}
    for name in sorted(os.listdir(directory)):
        m = NAME.match(name)
        if m:
            runs.setdefault(m["run"], {})[int(m["segment"])] = m["part"] is not None
    reports = []
    for run, files in runs.items():
        rep, plan = _check_run(directory, run, files)
        reports.append(rep)
        if rep.problems or dry_run:
            continue
        # [snippet:repair]
        for action, path, arg in plan:
            if action == "remove":
                os.unlink(path)
            else:
                end, closing = arg
                with open(path, "r+b") as f:
                    f.truncate(end)
                    if closing:
                        f.seek(end)
                        f.write(closing)
                    f.flush()
                    os.fsync(f.fileno())
                final = path[: -len(".part")]
                os.link(path, final)  # fails if the name exists: never replace a file
                os.unlink(path)
            _sync_dir(directory)
        # [/snippet:repair]
    return reports


def main(argv):
    if len(argv) < 2:
        print(__doc__.strip().splitlines()[-1].strip(), file=sys.stderr)
        return 2
    bad = False
    for r in recover(argv[1], dry_run="--dry-run" in argv):
        state = "clean" if r.clean else "problems" if r.problems else "recovered" if r.actions else "ended early"
        print(f"{r.run}: {r.segments} segments, {r.records} records, {state}")
        for line in r.actions:
            print(f"  {'would ' if '--dry-run' in argv else ''}{line}")
        for line in r.problems:
            print(f"  PROBLEM {line}")
        bad = bad or bool(r.problems)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
