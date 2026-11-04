# SPDX-License-Identifier: MIT
"""DICOM data sets and files, written and read (Chapter 35).

A data set is a dictionary {tag: Element(vr, value)}; `Dataset` adds access by keyword. Values are
Python values: a string or a list of strings for the text VRs (a list is a value multiplicity
above one, written with a backslash between the values), a number or a list of numbers for DS,
IS and the binary numbers, bytes for OB and OW, and a list of data sets for a sequence (SQ).

The writer is strict where the standard is strict: elements in ascending tag order, every value
of even length (UI padded with a zero byte, other text with a space), no value longer than its
VR allows, CS made of capitals, digits, space and underscore, UI of digits and dots, DS and IS
within their 16 and 12 characters. A value that breaks a rule is an error, never truncated:
a truncated identifier or number is a different identifier or number.

The reader takes Explicit VR Little Endian and Implicit VR Little Endian, sequences and items of
defined and undefined length, and nothing else; it refuses an odd length, a length past the end
of its input and nesting deeper than MAX_DEPTH, because the archive or the network that gives it
bytes is not trusted.
"""
import collections
import math
import re
import struct

from . import dictionary

EXPLICIT_LE = "1.2.840.10008.1.2.1"
IMPLICIT_LE = "1.2.840.10008.1.2"
LONG_VRS = {"OB", "OD", "OF", "OL", "OV", "OW", "SQ", "SV", "UC", "UN", "UR", "UT", "UV"}
TEXT_VRS = {"AE", "AS", "CS", "DA", "DS", "DT", "IS", "LO", "LT", "PN", "SH", "ST", "TM", "UC",
            "UI", "UR", "UT"}
MAX_LENGTH = {"AE": 16, "AS": 4, "CS": 16, "DA": 8, "DS": 16, "DT": 26, "IS": 12, "LO": 64,
              "LT": 10240, "PN": 64, "SH": 16, "ST": 1024, "TM": 14, "UI": 64}
SINGLE_VALUED = {"LT", "ST", "UT", "UR"}  # a backslash is text in these, not a separator
CHARSET_VRS = {"LO", "LT", "PN", "SH", "ST", "UC", "UT"}  # affected by Specific Character Set
BINARY = {"US": "H", "SS": "h", "UL": "I", "SL": "i", "FL": "f", "FD": "d", "AT": None}
CS_CHARS = re.compile(r"^[A-Z0-9 _]*$")
UI_CHARS = re.compile(r"^[0-9.]*$")
ITEM, ITEM_END, SEQUENCE_END = 0xFFFEE000, 0xFFFEE00D, 0xFFFEE0DD
UNDEFINED = 0xFFFFFFFF
MAX_DEPTH = 8
CHARSETS = {"": "ascii", "ISO_IR 6": "ascii", "ISO_IR 100": "latin-1", "ISO_IR 192": "utf-8"}

Element = collections.namedtuple("Element", "vr value")


class DicomError(ValueError):
    """A data set or a file that breaks a rule of the standard or of this package."""


class Dataset(dict):
    """{tag: Element}, with access by keyword: ds.set("Rows", 128); ds.get("Rows")."""

    def set(self, keyword, value, vr=None):
        t = dictionary.tag(keyword)
        self[t] = Element(vr or dictionary.vr(t), value)
        return self

    def get(self, keyword, default=None):
        e = super().get(dictionary.tag(keyword))
        return default if e is None else e.value

    def has(self, keyword):
        return dictionary.tag(keyword) in self


# [snippet:format_ds]
def format_ds(x):
    """A Decimal String (DS) for x: the most significant digits that fit in 16 characters. A DS
    is text, at most 16 characters; whatever reads the file reads this string, not x, so code
    that computes with the value must compute with float(format_ds(x))."""
    x = float(x)
    if not math.isfinite(x):
        raise DicomError(f"a DS cannot hold {x}")
    for digits in range(16, 0, -1):
        s = f"{x:.{digits}g}"
        if len(s) <= 16:
            return s
    raise DicomError(f"{x} does not fit in a DS")  # not reached: '-1e-308' is 7 characters
# [/snippet:format_ds]


def format_is(n):
    """An Integer String (IS): at most 12 characters, within a signed 32-bit integer."""
    if isinstance(n, bool) or int(n) != n or not -2**31 <= int(n) < 2**31:
        raise DicomError(f"an IS cannot hold {n}")
    return str(int(n))


def _values(value):
    return list(value) if isinstance(value, (list, tuple)) else [value]


def _text(tag, vr, value, encoding):
    """The bytes of a text element, before padding."""
    parts = []
    for v in _values(value):
        if vr == "DS" and not isinstance(v, str):
            v = format_ds(v)
        elif vr == "IS" and not isinstance(v, str):
            v = format_is(v)
        v = str(v)
        if vr not in SINGLE_VALUED and "\\" in v:
            raise DicomError(f"{dictionary.name(tag)}: a backslash inside one value")
        if vr == "CS" and not CS_CHARS.match(v):
            raise DicomError(f"{dictionary.name(tag)}: {v!r} is not a CS "
                             "(capitals, digits, space, underscore)")
        if vr == "UI" and not UI_CHARS.match(v):
            raise DicomError(f"{dictionary.name(tag)}: {v!r} is not a UID")
        try:
            b = v.encode(encoding if vr in CHARSET_VRS else "ascii")
        except UnicodeEncodeError as e:
            raise DicomError(f"{dictionary.name(tag)}: {v!r} needs a Specific Character Set "
                             f"that can encode it ({e.reason})") from None
        limit = MAX_LENGTH.get(vr)
        if vr == "PN":  # the limit applies to each component group (alphabetic=ideographic=...)
            if any(len(g) > limit for g in b.split(b"=")):
                raise DicomError(f"{dictionary.name(tag)}: a name group over {limit} bytes")
        elif limit is not None and len(b) > limit:
            raise DicomError(f"{dictionary.name(tag)}: {len(b)} bytes, the {vr} limit is {limit}")
        parts.append(b)
    return b"\\".join(parts)


def _value_bytes(tag, vr, value, explicit, encoding):
    if vr == "SQ":
        out = bytearray()
        for item in value:
            body = encode_dataset(item, explicit, encoding)
            out += struct.pack("<HHI", ITEM >> 16, ITEM & 0xFFFF, len(body)) + body
        return bytes(out)
    if vr in TEXT_VRS:
        b = _text(tag, vr, value, encoding)
        return b + (b"\0" if vr == "UI" else b" ") * (len(b) % 2)
    if vr in ("OB", "OW", "UN"):
        b = bytes(value)
        if vr == "OW" and len(b) % 2:
            raise DicomError(f"{dictionary.name(tag)}: OW of odd length")
        return b + b"\0" * (len(b) % 2)
    if vr in BINARY and BINARY[vr]:
        try:
            return struct.pack("<" + BINARY[vr] * len(_values(value)), *_values(value))
        except struct.error as e:
            raise DicomError(f"{dictionary.name(tag)}: {value!r} is not a {vr} ({e})") from None
    raise DicomError(f"{dictionary.name(tag)}: VR {vr} is not supported")


# [snippet:encode_element]
def encode_element(tag, vr, value, explicit=True, encoding="ascii"):
    """One data element: tag, VR (explicit only), length, value. Explicit VR has two header forms:
    a 2-byte length for most VRs, and 2 reserved bytes and a 4-byte length for the VRs that can
    be long (LONG_VRS). Implicit VR has no VR and always a 4-byte length."""
    body = _value_bytes(tag, vr, value, explicit, encoding)
    head = struct.pack("<HH", tag >> 16, tag & 0xFFFF)
    if not explicit:
        return head + struct.pack("<I", len(body)) + body
    if vr in LONG_VRS:
        return head + vr.encode() + b"\0\0" + struct.pack("<I", len(body)) + body
    if len(body) > 0xFFFF:
        raise DicomError(f"{dictionary.name(tag)}: {len(body)} bytes do not fit a {vr}")
    return head + vr.encode() + struct.pack("<H", len(body)) + body
# [/snippet:encode_element]


def charset_of(ds, inherited="ascii"):
    """The Python codec for a data set's Specific Character Set (0008,0005)."""
    e = dict.get(ds, 0x00080005) if isinstance(ds, dict) else None
    if e is None:
        return inherited
    term = e.value if isinstance(e.value, str) else (e.value[0] if e.value else "")
    if term not in CHARSETS:
        raise DicomError(f"Specific Character Set {term!r} is not supported")
    return CHARSETS[term]


def encode_dataset(ds, explicit=True, encoding="ascii"):
    """Every element of ds, in ascending tag order (the standard requires it)."""
    encoding = charset_of(ds, encoding)
    return b"".join(encode_element(t, e.vr, e.value, explicit, encoding)
                    for t, e in sorted(ds.items()))


def group_length(tag_, body):
    """The group length element (gggg,0000) for an encoded group: a UL, explicit VR."""
    return encode_element(tag_, "UL", len(body))


# [snippet:write_file]
def file_bytes(ds, implementation_uid, implementation_name="MINIDAQ"):
    """The DICOM file of a data set (part 10): a 128-byte preamble, 'DICM', the file meta
    information (group 0002, always Explicit VR Little Endian, led by its group length) and the
    data set in the transfer syntax the meta information names, here Explicit VR Little Endian."""
    meta = Dataset()
    meta.set("FileMetaInformationVersion", b"\0\1")
    meta.set("MediaStorageSOPClassUID", ds.get("SOPClassUID"))
    meta.set("MediaStorageSOPInstanceUID", ds.get("SOPInstanceUID"))
    meta.set("TransferSyntaxUID", EXPLICIT_LE)
    meta.set("ImplementationClassUID", implementation_uid)
    meta.set("ImplementationVersionName", implementation_name)
    body = encode_dataset(meta)
    return (b"\0" * 128 + b"DICM" + group_length(0x00020000, body) + body
            + encode_dataset(ds, explicit=True))
# [/snippet:write_file]


def _decode_value(tag, vr, raw, explicit, encoding, depth):
    if vr == "SQ":
        return _decode_items(raw, explicit, encoding, depth + 1)[0]
    if vr in TEXT_VRS:
        codec = encoding if vr in CHARSET_VRS else "ascii"
        try:
            text = raw.decode(codec)
        except UnicodeDecodeError:
            raise DicomError(f"{dictionary.name(tag)}: not {codec}") from None
        text = text.rstrip("\0 ") if vr == "UI" else text.rstrip(" ")
        if vr in SINGLE_VALUED or "\\" not in text:
            return text.strip(" \0") if vr in ("DS", "IS", "UI", "CS", "DA", "TM", "DT") else text
        parts = text.split("\\")  # a value multiplicity above one: a list, as written
        if vr in ("DS", "IS", "UI", "CS", "DA", "TM", "DT", "AE", "AS"):
            parts = [v.strip(" \0") for v in parts]
        return parts
    if vr in BINARY and BINARY[vr]:
        size = struct.calcsize(BINARY[vr])
        if len(raw) % size:
            raise DicomError(f"{dictionary.name(tag)}: {len(raw)} bytes are not a {vr}")
        values = struct.unpack("<" + BINARY[vr] * (len(raw) // size), raw)
        return values[0] if len(values) == 1 else values
    return bytes(raw)


def _read_length(buf, pos, n):
    if pos + n > len(buf):
        raise DicomError(f"truncated at byte {pos}")
    return struct.unpack_from("<H" if n == 2 else "<I", buf, pos)[0], pos + n


def _decode_items(buf, explicit, encoding, depth, pos=0, end=None):
    """(list of item data sets, position after the sequence) of a sequence's value."""
    if depth > MAX_DEPTH:
        raise DicomError(f"sequences nested deeper than {MAX_DEPTH}")
    end = len(buf) if end is None else end
    items = []
    while pos < end:
        if pos + 8 > len(buf):
            raise DicomError(f"truncated item at byte {pos}")
        tag = (struct.unpack_from("<H", buf, pos)[0] << 16) | struct.unpack_from("<H", buf, pos + 2)[0]
        length = struct.unpack_from("<I", buf, pos + 4)[0]
        pos += 8
        if tag == SEQUENCE_END:
            return items, pos
        if tag != ITEM:
            raise DicomError(f"expected an item at byte {pos - 8}, found {tag:08X}")
        if length == UNDEFINED:
            ds, pos = _decode(buf, explicit, encoding, depth, pos, None, until_item_end=True)
        else:
            if pos + length > len(buf):
                raise DicomError(f"item of {length} bytes past the end at byte {pos}")
            ds, _ = _decode(buf, explicit, encoding, depth, pos, pos + length)
            pos += length
        items.append(ds)
    return items, pos


def _decode(buf, explicit, encoding, depth, pos, end, until_item_end=False):
    ds = Dataset()
    end = len(buf) if end is None else end
    previous = -1
    while pos < end:
        if pos + 8 > len(buf):
            raise DicomError(f"truncated element at byte {pos}")
        tag = (struct.unpack_from("<H", buf, pos)[0] << 16) | struct.unpack_from("<H", buf, pos + 2)[0]
        if tag == ITEM_END and until_item_end:
            return ds, pos + 8
        if explicit and tag >> 16 != 0xFFFE:
            vr = buf[pos + 4:pos + 6].decode("ascii", "replace")
            if vr in LONG_VRS:
                length, pos = _read_length(buf, pos + 8, 4)
            else:
                length, pos = _read_length(buf, pos + 6, 2)
        else:
            vr = dictionary.ELEMENTS.get(tag, ("UN",))[0]
            length, pos = _read_length(buf, pos + 4, 4)
        if tag <= previous:
            raise DicomError(f"{dictionary.name(tag)} after {dictionary.name(previous)}: "
                             "elements must ascend")
        previous = tag
        if length == UNDEFINED:
            if vr not in ("SQ", "UN"):
                raise DicomError(f"{dictionary.name(tag)}: undefined length for VR {vr} "
                                 "(encapsulated data is not supported)")
            value, pos = _decode_items(buf, explicit, encoding, depth + 1, pos)
            ds[tag] = Element("SQ", value)
            continue
        if length % 2:
            raise DicomError(f"{dictionary.name(tag)}: odd length {length}")
        if pos + length > end:
            raise DicomError(f"{dictionary.name(tag)}: {length} bytes past the end at byte {pos}")
        value = _decode_value(tag, vr, buf[pos:pos + length], explicit, encoding, depth)
        ds[tag] = Element(vr, value)
        if tag == 0x00080005:
            encoding = charset_of(ds, encoding)
        pos += length
    if until_item_end:
        raise DicomError("item of undefined length without its end")
    return ds, pos


def decode_dataset(buf, explicit=True, encoding="ascii"):
    """A data set from bytes in Explicit (explicit=True) or Implicit VR Little Endian."""
    return _decode(memoryview(bytes(buf)).tobytes(), explicit, encoding, 0, 0, None)[0]


def read_file_bytes(buf):
    """(meta, data set) of a DICOM file. Refuses a file without the preamble and 'DICM', without
    its group length, or in a transfer syntax other than Explicit VR Little Endian."""
    if len(buf) < 132 or buf[128:132] != b"DICM":
        raise DicomError("not a DICOM file: no 'DICM' after the 128-byte preamble")
    if buf[132:136] != b"\x02\x00\x00\x00" or buf[136:138] != b"UL":
        raise DicomError("the file meta information does not start with its group length")
    meta_length = struct.unpack_from("<I", buf, 140)[0]
    meta_end = 144 + meta_length
    if meta_end > len(buf):
        raise DicomError("the file meta information is longer than the file")
    meta = _decode(buf, True, "ascii", 0, 144, meta_end)[0]
    if any(t >> 16 != 0x0002 for t in meta):
        raise DicomError("an element outside group 0002 in the file meta information")
    syntax = meta.get("TransferSyntaxUID")
    if syntax != EXPLICIT_LE:
        raise DicomError(f"transfer syntax {syntax} is not supported (only {EXPLICIT_LE})")
    return meta, _decode(buf, True, "ascii", 0, meta_end, None)[0]


def split(value):
    """The values of a text element as a list ('a\\b' gives ['a', 'b']; '' gives [])."""
    if value is None or value == "":
        return []
    return value.split("\\") if isinstance(value, str) else list(_values(value))
