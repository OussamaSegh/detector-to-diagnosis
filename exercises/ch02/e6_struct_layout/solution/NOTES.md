# Where the padding was (x86-64 System V ABI)

Starter layout:

| Member | Offset | Size | Padding before |
|---|---|---|---|
| bool bias_on | 0 | 1 | |
| double singles_rate_hz | 8 | 8 | 7 (align to 8) |
| uint16_t block_id | 16 | 2 | |
| float temperature_c | 20 | 4 | 2 (align to 4) |
| bool alarm | 24 | 1 | |
| uint32_t bias_mv | 28 | 4 | 3 (align to 4) |
| uint8_t fw_revision | 32 | 1 | |
| tail | 33 | | 7 (size must be a multiple of 8) |

19 padding bytes out of 40. Ordering members by decreasing alignment removes all but the
3 bytes of tail padding. Check offsets with `offsetof`, `pahole` (from the `dwarves`
package) on the object file, or Clang's `-Xclang -fdump-record-layouts`.

If such a struct goes on the wire, do not send it with `memcpy`: padding bytes have
unspecified values (possibly leaking stack contents) and layout depends on the ABI. Write
an explicit serializer, as for MDQ-P1.
