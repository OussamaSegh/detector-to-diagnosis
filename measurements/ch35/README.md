# Chapter 35 measurements: the DICOM export

`dicom.txt` is the output of `python3 measurements/ch35/dicom.py measurements/ch35/dicom.txt`
(about 30 s), with numpy, pydicom 3.0.2 and pynetdicom 3.0.4 from `analysis/requirements.lock`.
Its input is the phantom image of Chapter 33 (`measurements/ch33/e2e/image.npy`, OSEM, 128 x 128
pixels of 2 mm) and the three JSON files of this directory, which are also examples of the
inputs of `tools/pacs.py export`. The order is synthetic: no real patient's data is used anywhere
in the repository.

What it shows:

1. One PET Image object of 34,480 bytes, 32,768 of them pixels; pydicom reads it and its values
   equal this package's.
2. The largest quantization error is half a slope (0.4999), 7.6e-6 of the image's maximum. In a
   47-slice volume with one slice ten times hotter, a slope per slice keeps the median relative
   error inside the object at 1.8e-5 in every slice; one slope for the volume makes it 2.4e-4 in
   the cold slices, 14 times larger.
3. The slope of the phantom image is 1.43e-7: six decimals would write `0.000000`.
4. The cylinder's centroid is at (0.12, -0.30, 0) mm in patient coordinates, within a sixth of a
   pixel of the axis.
5. A 47-slice series (1.6 MB of data sets) is stored on loopback in a median of 58 to 66 ms,
   whatever the maximum PDU length from 4 KiB to no limit; pynetdicom's storage provider takes
   158 to 171 ms for the same series. The PDU length barely matters on loopback.
   **Found while measuring:** the first version did not set TCP_NODELAY and took 2.07 s,
   44 ms per instance, 36 times longer: the small final PDU of each message waited for the
   acknowledgment of the previous one, which the receiver delays (Nagle's algorithm meeting
   delayed acknowledgments).
   The line "sender WITHOUT TCP_NODELAY" repeats that measurement; `tools/test_dicom.py` now
   checks that the option is set.
6. An association aborted after 20 instances leaves 20 sent and 27 pending; after a second export
   of the same image (same UIDs) and a resend, the archive holds 47 instances, not 67.
7. pydicom 3.0.2 reads, without a warning, a sequence item whose tag was written as one 32-bit
   integer (the bytes `00 E0 FE FF` instead of `FE FF 00 E0`), a mistake this package's first
   version made; this package's reader refuses it. The independent reader is lenient by design:
   it finds disagreements, not every violation.

The times are of the book's virtual machine and vary from run to run; the ratios are the point.
