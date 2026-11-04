# SPDX-License-Identifier: MIT
"""MiniDAQ's images, out to the hospital: DICOM files and DICOM network storage (Chapter 35).

The package turns a reconstructed image (tools/recon, Chapters 28 to 30) into a series of PET
Image objects and sends it to a picture archive (PACS) with the DICOM C-STORE service. It is tool
TL-44: a teaching implementation of the parts of the standard that a scanner's export needs, not
a general DICOM toolkit:

- dictionary: the data elements the package writes or reads, with their value representations;
- encode: data sets in Explicit VR Little Endian (and Implicit VR Little Endian, which DIMSE
  commands use), the DICOM file format with its meta information, and a strict reader of both;
- uid: unique identifiers under the 2.25 root, derived from a UUID, some of them from content so
  that exporting the same image twice gives the same identifiers;
- pet: a PET Image series from an image volume, the order of the study and the acquisition, with
  the checks that refuse a series a reader could misfile or misread;
- net: the DICOM upper layer (associations, P-DATA) and the C-ECHO and C-STORE services, as a
  service class user;
- scp: a small storage service class provider for tests, with faults to inject;
- outbox: a store-and-forward queue that keeps every instance until the archive has stored it.

Only the Python standard library and numpy. pydicom and pynetdicom are used by the tests alone,
as independent readers and peers (tools/test_dicom.py); nothing of them is needed to export.
"""
