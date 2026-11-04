# SPDX-License-Identifier: MIT
"""The data elements this package writes or reads (Chapter 35): tag, value representation (VR) and
keyword, as in the data dictionary of the DICOM standard, part 6.

A data element is named by its tag, a group and an element number, written (gggg,eeee) and kept
here as one integer 0xggggeeee. Explicit VR transfer syntaxes carry the VR in the data set; the
Implicit VR one, which DIMSE commands always use, does not, and a reader takes it from a
dictionary such as this one. tools/test_dicom.py checks every row against pydicom's dictionary.
"""

# [snippet:dictionary]
ELEMENTS = {
    # Command group (part 7): always Implicit VR Little Endian.
    0x00000000: ("UL", "CommandGroupLength"),
    0x00000002: ("UI", "AffectedSOPClassUID"),
    0x00000100: ("US", "CommandField"),
    0x00000110: ("US", "MessageID"),
    0x00000120: ("US", "MessageIDBeingRespondedTo"),
    0x00000700: ("US", "Priority"),
    0x00000800: ("US", "CommandDataSetType"),
    0x00000900: ("US", "Status"),
    0x00000902: ("LO", "ErrorComment"),
    0x00001000: ("UI", "AffectedSOPInstanceUID"),
    # File meta information (part 10): always Explicit VR Little Endian.
    0x00020000: ("UL", "FileMetaInformationGroupLength"),
    0x00020001: ("OB", "FileMetaInformationVersion"),
    0x00020002: ("UI", "MediaStorageSOPClassUID"),
    0x00020003: ("UI", "MediaStorageSOPInstanceUID"),
    0x00020010: ("UI", "TransferSyntaxUID"),
    0x00020012: ("UI", "ImplementationClassUID"),
    0x00020013: ("SH", "ImplementationVersionName"),
    # [/snippet:dictionary]
    0x00080005: ("CS", "SpecificCharacterSet"),
    0x00080008: ("CS", "ImageType"),
    0x00080012: ("DA", "InstanceCreationDate"),
    0x00080013: ("TM", "InstanceCreationTime"),
    0x00080016: ("UI", "SOPClassUID"),
    0x00080018: ("UI", "SOPInstanceUID"),
    0x00080020: ("DA", "StudyDate"),
    0x00080021: ("DA", "SeriesDate"),
    0x00080022: ("DA", "AcquisitionDate"),
    0x00080030: ("TM", "StudyTime"),
    0x00080031: ("TM", "SeriesTime"),
    0x00080032: ("TM", "AcquisitionTime"),
    0x00080050: ("SH", "AccessionNumber"),
    0x00080060: ("CS", "Modality"),
    0x00080070: ("LO", "Manufacturer"),
    0x00080090: ("PN", "ReferringPhysicianName"),
    0x00080100: ("SH", "CodeValue"),
    0x00080102: ("SH", "CodingSchemeDesignator"),
    0x00080104: ("LO", "CodeMeaning"),
    0x00080201: ("SH", "TimezoneOffsetFromUTC"),
    0x0008103E: ("LO", "SeriesDescription"),
    0x00081090: ("LO", "ManufacturerModelName"),
    0x00100010: ("PN", "PatientName"),
    0x00100020: ("LO", "PatientID"),
    0x00100030: ("DA", "PatientBirthDate"),
    0x00100040: ("CS", "PatientSex"),
    0x00180031: ("LO", "Radiopharmaceutical"),
    0x00180050: ("DS", "SliceThickness"),
    0x00181000: ("LO", "DeviceSerialNumber"),
    0x00181020: ("LO", "SoftwareVersions"),
    0x00181074: ("DS", "RadionuclideTotalDose"),
    0x00181075: ("DS", "RadionuclideHalfLife"),
    0x00181076: ("DS", "RadionuclidePositronFraction"),
    0x00181078: ("DT", "RadiopharmaceuticalStartDateTime"),
    0x00181181: ("CS", "CollimatorType"),
    0x00181242: ("IS", "ActualFrameDuration"),
    0x00185100: ("CS", "PatientPosition"),
    0x0020000D: ("UI", "StudyInstanceUID"),
    0x0020000E: ("UI", "SeriesInstanceUID"),
    0x00200010: ("SH", "StudyID"),
    0x00200011: ("IS", "SeriesNumber"),
    0x00200013: ("IS", "InstanceNumber"),
    0x00200032: ("DS", "ImagePositionPatient"),
    0x00200037: ("DS", "ImageOrientationPatient"),
    0x00200052: ("UI", "FrameOfReferenceUID"),
    0x00201040: ("LO", "PositionReferenceIndicator"),
    0x00201041: ("DS", "SliceLocation"),
    0x00280002: ("US", "SamplesPerPixel"),
    0x00280004: ("CS", "PhotometricInterpretation"),
    0x00280010: ("US", "Rows"),
    0x00280011: ("US", "Columns"),
    0x00280030: ("DS", "PixelSpacing"),
    0x00280051: ("CS", "CorrectedImage"),
    0x00280100: ("US", "BitsAllocated"),
    0x00280101: ("US", "BitsStored"),
    0x00280102: ("US", "HighBit"),
    0x00280103: ("US", "PixelRepresentation"),
    0x00281052: ("DS", "RescaleIntercept"),
    0x00281053: ("DS", "RescaleSlope"),
    0x00540016: ("SQ", "RadiopharmaceuticalInformationSequence"),
    0x00540081: ("US", "NumberOfSlices"),
    0x00540300: ("SQ", "RadionuclideCodeSequence"),
    0x00540304: ("SQ", "RadiopharmaceuticalCodeSequence"),
    0x00540410: ("SQ", "PatientOrientationCodeSequence"),
    0x00540412: ("SQ", "PatientOrientationModifierCodeSequence"),
    0x00540414: ("SQ", "PatientGantryRelationshipCodeSequence"),
    0x00541000: ("CS", "SeriesType"),
    0x00541001: ("CS", "Units"),
    0x00541002: ("CS", "CountsSource"),
    0x00541100: ("CS", "RandomsCorrectionMethod"),
    0x00541101: ("LO", "AttenuationCorrectionMethod"),
    0x00541102: ("CS", "DecayCorrection"),
    0x00541103: ("LO", "ReconstructionMethod"),
    0x00541105: ("LO", "ScatterCorrectionMethod"),
    0x00541300: ("DS", "FrameReferenceTime"),
    0x00541321: ("DS", "DecayFactor"),
    0x00541330: ("US", "ImageIndex"),
    0x7FE00010: ("OW", "PixelData"),
}

TAGS = {keyword: tag for tag, (_, keyword) in ELEMENTS.items()}


def tag(keyword):
    """The tag of a keyword of this dictionary; KeyError for any other."""
    return TAGS[keyword]


def vr(tag_):
    """The VR of a tag of this dictionary; KeyError for any other."""
    return ELEMENTS[tag_][0]


def name(tag_):
    """'(gggg,eeee) Keyword', for messages."""
    keyword = ELEMENTS.get(tag_, ("", "unknown"))[1]
    return f"({tag_ >> 16:04X},{tag_ & 0xFFFF:04X}) {keyword}"
