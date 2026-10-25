# MiniDAQ: regulatory context

Version 2 (MiniDAQ 0.3.0-dev, Chapter 16). Status: draft for review.

This page places MiniDAQ, written as if it were the DAQ software of a dedicated brain PET
scanner ([intended use](intended-use.md)), in the regulations of the three markets such a
scanner from a Swiss manufacturer is sold in: the EU, the US and Switzerland. It is a teaching
example. The facts about regulations were checked in October 2026 and change; every one marked
"verify" must be checked against the current text before it is relied on. Nothing here
describes the manufacturer's actual regulatory strategy.

## 1. The device and its software

| Question | Answer for the scanner | Consequence for MiniDAQ |
|---|---|---|
| Is it a medical device? | Yes: an active device for diagnosis | MiniDAQ is part of it, not a device of its own |
| EU class | IIa: MDR Annex VIII, Rule 10, "intended to image in vivo distribution of radiopharmaceuticals" | Implementing rule 3.3: software that drives or influences a device is in the device's class, so IIa |
| US classification | 21 CFR 892.1200, emission computed tomography system, class II, product code KPS; market entry by 510(k) | Part of the 510(k), with the software documentation of FDA's 2023 guidance |
| Software documentation level (FDA) | Basic or Enhanced, decided for the whole device | assumption: confirm with team which level the NeuroLF's submission used |
| IEC 62304 software safety class | Decided per software system and item from the risk analysis (Chapter 14) | Proposed in the software development plan, not here |

A PET/CT would be class IIb in the EU (Rule 10, last paragraph: devices that emit ionizing
radiation for diagnostic radiology), and its DAQ software with it. A brain PET has no X-ray
source, so it stays in IIa.

## 2. European Union

- **Regulation.** Regulation (EU) 2017/745 (MDR). General safety and performance requirements
  in Annex I; section 17 covers electronic programmable systems and software (development to
  the state of the art, life cycle, risk management, information security, verification and
  validation). Technical documentation in Annexes II and III.
- **Conformity assessment.** For class IIa, a notified body assesses the quality management
  system and, on a representative basis, the technical documentation (Article 52(6), Annex IX;
  verify the route the notified body applies). The CE marking carries the notified body's
  number.
- **Economic operators.** A manufacturer outside the EU, such as a Swiss one, needs an
  authorized representative in the EU (Article 11). Every manufacturer needs a person
  responsible for regulatory compliance (Article 15).
- **Registration.** UDI and device registration in EUDAMED; the first four modules (actors,
  UDI and devices, notified bodies and certificates, market surveillance) are mandatory from
  28 May 2026, with devices already on the market to be registered by 28 November 2026
  (verify).
- **After the market.** A post-market surveillance plan and system (Articles 83 and 84), a
  periodic safety update report at least every two years for class IIa (Article 86), and
  serious-incident reports within 2, 10 or 15 days (Article 87). Trend reporting of
  non-serious incidents (Article 88).
- **Coming change.** On 16 December 2025 the Commission proposed a targeted revision of the
  MDR and IVDR (certificate validity, notified body procedures, the software rule, vigilance
  deadlines). It is in the legislative procedure and not expected to be adopted before 2027
  (verify: its status). Plan to the regulation in force.

## 3. United States

- **Pathway.** 510(k) premarket notification against a predicate PET system under 21 CFR
  892.1200 (class II). A change that could significantly affect safety or effectiveness needs a
  new 510(k); FDA's 2017 guidance on software changes says how to decide.
- **Quality system.** 21 CFR 820, the Quality Management System Regulation (QMSR), which
  incorporates ISO 13485:2016 by reference and applies from 2 February 2026.
- **Software documentation.** FDA guidance "Content of Premarket Submissions for Device
  Software Functions" (June 2023), with a Basic or Enhanced documentation level.
- **Cybersecurity.** Section 524B of the FD&C Act for "cyber devices", and FDA's premarket
  cybersecurity guidance (final 2023, updated June 2025; verify). Chapter 17.
- **After the market.** Medical device reports under 21 CFR 803: 30 calendar days, or 5 work
  days when remedial action is needed to prevent an unreasonable risk of substantial harm.
- **Establishment.** A foreign manufacturer registers its establishment, lists its devices and
  names a US agent (21 CFR 807).

## 4. Switzerland

- **Regulation.** The Medical Devices Ordinance (MedDO, SR 812.213), aligned with the MDR, under
  the Therapeutic Products Act; Swissmedic is the competent authority.
- **Since May 2021** the mutual recognition agreement (MRA) between the EU and Switzerland has
  not been updated for the MDR. Switzerland unilaterally accepts CE marking and EU notified
  bodies' certificates, while the EU treats Swiss manufacturers as third-country
  manufacturers: hence the EU authorized representative above. A non-Swiss manufacturer needs a
  Swiss authorized representative (CH-REP) on the label.
- **Registration.** Devices are registered in swissdamed: mandatory for new devices from
  1 July 2026, and for devices already on the market by 31 December 2026 (verify).
- **Coming change.** An updated MRA was signed in March 2026 and needs ratification on both
  sides, not expected to apply before late 2027 (verify). Separately, the Federal Council
  decided in April 2025 to prepare access for devices with FDA clearance (Motion 20.3211);
  the ordinance changes are pending (verify).

## 5. Standards applied

| Standard | Edition | Role | EU harmonised under the MDR? |
|---|---|---|---|
| ISO 13485 | 2016 (+A11:2021 as EN) | Quality management system | Yes |
| ISO 14971 | 2019 (+A11:2021 as EN) | Risk management | Yes |
| ISO/TR 24971 | 2020 | Guidance on applying ISO 14971 | No (a technical report) |
| IEC 62304 | 2006+A1:2015 | Software life cycle | No, at the time of writing (verify) |
| IEC 62366-1 | 2015+A1:2020 | Usability engineering | No, at the time of writing (verify) |
| IEC 60601-1 | 2005+A1:2012+A2:2020 | Basic safety and essential performance | Yes, in its EN edition (verify which) |
| IEC 81001-5-1 | 2021 | Security in the software life cycle | No, at the time of writing (verify) |

A standard that is not harmonised gives no presumption of conformity, but it is still the
state of the art that Annex I asks for, and notified bodies and FDA expect it. The map of how
these standards depend on each other is [standards-map.svg](standards-map.svg), drawn from
[standards-map.dot](standards-map.dot).

## 6. Where MiniDAQ's regulatory file lives

| Document | File | Chapter |
|---|---|---|
| Intended use | [intended-use.md](intended-use.md) | 13 |
| Regulatory context (this page) | regulatory-context.md | 13 |
| Software development plan, requirements, architecture, trace matrix | arrives with Chapter 14 | 14 |
| SOUP list | [soup-list.md](soup-list.md) | 7, 14 |
| Risk management file | arrives with Chapter 15 | 15 |
| Design history index, change control template | arrives with Chapter 16 | 16 |
| Threat model and security requirements | arrives with Chapter 17 | 17 |
| Architecture and decisions | [architecture](../architecture/architecture.md), [ADRs](../adr/README.md) | 6 and later |

## 7. What the DAQ gives post-market surveillance

Complaint handling and vigilance need facts, fast. MiniDAQ provides them with every run: the
configuration in every list-mode file, the run record with the counters of the link, the
sorter and the writer (`<prefix>-<run>.run.json`), the audit trail of control commands, and a
`simulated` flag that keeps test data from passing for measurements. A loss that no counter
records would be a defect in a risk control, and is treated as one.

## 8. Open questions

1. Which notified body, which conformity assessment route and which software documentation
   level apply to the NeuroLF, and who is its EU authorized representative?
2. Which IEC 62304 safety class has the NeuroLF's DAQ software, and on what risk argument?
3. In which markets beyond the EU, the US and Switzerland is it sold, with which additional
   requirements?
4. Which version of each standard does the technical documentation claim, and who updates the
   list when a new edition appears (IEC 62304 edition 2 is expected in 2028, verify)?

## Document history

| Version | Change |
|---|---|
| 1 | First version (Chapter 13). |
| 2 | This history (Chapter 16); the text is unchanged. |
