# The regulatory landscape for a PET scanner {#ch13}

::: box-why
The scanner your DAQ code runs in is a medical device on the European and the US markets.
Every line of DAQ code you write ships inside that frame: a regulation decides
the device's class, the class decides who must check the design before it is sold, and the
design must show, in documents someone else can read, that it is safe and does what it claims.
After it is sold, the same frame decides what happens when a hospital reports a problem, and
how fast. You will not file submissions yourself, but your requirements, your tests, your
change requests and your problem reports are the evidence those submissions are built from.
This chapter gives you the map: the EU Medical Device Regulation, the FDA's pathways, the Swiss
situation, the standards and how they depend on each other, and the obligations after the
market. It ends with MiniDAQ's first regulatory documents.
:::

**A day in the life.** It is your third week, and the change you are most proud of is ready: a
faster merger that cuts the sorter's latency by half. In the review, the quality engineer asks
three questions. Which requirements does the change touch? Has the risk analysis been looked
at, given that the merger decides which singles are late? And does the change need to be
reported to the notified body before release? You can answer the first: the requirement IDs are
in your tests. The second takes a call with the risk owner, who points out that a late single
is now dropped two milliseconds earlier than before, and asks for the test that shows the
counter still sees it. The third you cannot answer, and nobody expects you to: it goes to
regulatory affairs with your one-page impact analysis. By the end of the day the change is
approved, with one new test and a note in the change record that says why no notification was
needed. Nothing in the code changed after the review. What changed is that the organization can
now show why the code is safe to ship. That is the work this chapter prepares you for.

## Learning objectives {.unnumbered}

After this chapter you can:

1. Explain the EU Medical Device Regulation (MDR) 2017/745 at the level a software lead needs:
   its structure, the general safety and performance requirements, classification, notified
   bodies, conformity assessment and CE marking.
2. Explain the FDA's 510(k), De Novo and PMA pathways, place a PET scanner among them, and name
   what a premarket submission contains about software.
3. Name the standards that apply to a PET scanner's software, what each covers, and how they
   depend on each other, and tell a quality management standard from a life-cycle standard.
4. Describe the Swiss situation in one paragraph: the Medical Devices Ordinance, Swissmedic,
   the mutual recognition agreement and what it means for a Swiss manufacturer.
5. Describe post-market surveillance, vigilance and CAPA, and what DAQ software contributes to
   them.

## Prerequisites and estimated time {.unnumbered}

Chapter 6 (architecture and decision records), Chapter 7 (the SOUP list and the SBOM) and
Chapter 12 (the run record and the patient-data boundary). No physics or C++ is needed beyond
that, and the exercises are in Python. Reading: about 3 hours. Exercises: 5 hours. Milestone: 2
hours. In the 10-week schedule at the front of the book, this chapter is in week 2, the lighter
evenings next to Chapters 3 and 9.

## Why regulation shapes software

### The intuition

A regulator asks one question in many forms: *how do you know?* How do you know the scanner
measures what it claims? How do you know that a software change did not break it? How do you
know what went wrong when a hospital reports a problem? An engineer's answer ("I tested it", "I
looked at the code") is not enough, because the regulator cannot ask the engineer, the engineer
leaves, and the code changes. The answer must be in documents and records that someone else can
read years later: what the device is for, what it must do, how the design meets that, how it
was verified, what risks remain, and what happened after release.

That is why medical device regulation is mostly about process and evidence, and hardly ever
about code. It does not say "use a bounded queue". It says that the device must be safe, that
the software must be developed under a life cycle that manages risk, and that you must be able
to show it. The standards then describe a recognized way to do that. Your design decisions are
yours; what the frame adds is the obligation to make them deliberately, write them down, verify
them and keep them under control.

### Regulations, standards and guidance

Three kinds of document make up the frame, and they bind in different ways.

- **Regulations are law.** The EU MDR, the US Federal Food, Drug, and Cosmetic Act with its
  rules in Title 21 of the Code of Federal Regulations, and the Swiss Medical Devices Ordinance
  apply whether or not anyone reads them. They say what must be achieved and who is
  responsible, mostly in general terms.
- **Standards are agreed ways to meet the law.** ISO 13485, ISO 14971, IEC 62304 and the others
  are written by committees of industry, regulators and experts, and are voluntary in
  principle. In the EU, a standard that the Commission has *harmonised* gives a *presumption of
  conformity*: a device that meets it is presumed to meet the requirements of the regulation it
  covers. In the US, FDA *recognizes* consensus standards, and a manufacturer can declare
  conformity to them in a submission. In practice, the main standards are expected whether
  harmonised or not, because they are the state of the art.
- **Guidance explains how the regulator reads the law.** FDA guidance documents and the EU's
  Medical Device Coordination Group (MDCG) documents are not binding, but departing from them
  needs a reason that convinces a reviewer.

A fourth kind lives inside the company: the quality management system's procedures, which turn
all of this into "how we do it here". That is what you follow day to day (Chapter 16).

### What the manufacturer owns

The regulations put the obligations on the *manufacturer*: the legal entity that places the
device on the market under its name, whoever designed or built it. For your scanner that is
the company that sells it. The manufacturer defines the intended purpose, keeps the technical
documentation, runs the quality management system, monitors the device on the market and reports
incidents. Engineers do not carry these obligations personally, but every one of them is met with
engineering work: requirements, designs, test reports, problem reports. A useful test for any
document you write is to ask which obligation it serves.

## The EU Medical Device Regulation

### The shape of the regulation

Regulation (EU) 2017/745, the MDR, replaced the Medical Device Directive and has applied since
26 May 2021. As a regulation it applies directly in every member state, without national
transposition. It has ten chapters of articles (who must do what) and seventeen annexes (the
details). Five annexes matter most to a software lead:

| Annex | Content | Where you meet it |
|---|---|---|
| I | General safety and performance requirements (GSPR) | Every design input traces to them |
| II and III | Technical documentation, and post-market surveillance documentation | What your documents become part of |
| VIII | Classification rules | Why the scanner is class IIa |
| IX | Conformity assessment based on a quality management system and assessment of technical documentation | What the notified body audits |
| XIV | Clinical evaluation and post-market clinical follow-up | Where performance claims are justified |

### Annex I: the requirements a device must meet

Annex I lists the general safety and performance requirements. Chapter I of the annex is
general: the device must achieve its intended performance and be safe, risks must be reduced
as far as possible without adversely affecting the benefit-risk ratio, and risk management is a
continuous process over the device's life. Chapter II has requirements on design and
manufacture, and section 17 is the one written for software. It asks, in short, that:

- electronic programmable systems, including software, are designed to ensure repeatability,
  reliability and performance in line with their intended use, and that a single fault condition
  is handled by appropriate means;
- software is developed and manufactured according to the state of the art, taking into account
  the principles of the development life cycle, risk management including information security,
  verification and validation;
- the minimum requirements on hardware, IT networks and IT security measures are set out,
  including protection against unauthorized access.

Read that list again as a DAQ engineer. "Repeatability, reliability and performance" is the
count-rate performance of Chapter 11 and the validation of Chapter 10. "A single fault
condition" is the faulted run of Chapter 12 when an fsync fails. "State of the art ... life
cycle ... risk management ... verification" is IEC 62304 and ISO 14971, which is why those
standards matter even where they are not harmonised. "Minimum requirements on ... IT networks"
is the dedicated readout network that Chapter 9 assumed and that the intended use must state.

Other sections reach software too: Chapter III of Annex I covers the information supplied with
the device (labels and instructions for use, where software must be identifiable by its
version; verify the exact requirement for your device), and the requirements on devices with a
diagnostic or measuring function apply to any number the scanner reports.

### Classification

The class decides how much independent checking a device gets. The MDR has four classes, I,
IIa, IIb and III, and Annex VIII gives 22 rules for assigning them. Two of the annex's
implementing rules decide the DAQ software's class before any rule about software is read:

- *Implementing rule 3.3*: "Software, which drives a device or influences the use of a device,
  shall fall within the same class as the device. If the software is independent of any other
  device, it shall be classified in its own right."
- *Implementing rule 3.5*: if several rules, or several sub-rules of one rule, apply to the same
  device, the strictest rule and sub-rule resulting in the higher class apply.

The scanner itself is an active device for diagnosis, covered by Rule 10. Its first paragraph
reads, in part: "Active devices intended for diagnosis and monitoring are classified as class
IIa: ... if they are intended to image in vivo distribution of radiopharmaceuticals". A PET
scanner does exactly that. Its last paragraph puts "active devices intended to emit ionizing
radiation and intended for diagnostic or therapeutic radiology", and devices that control or
monitor them, in class IIb. A PET scanner emits no radiation of its own; the radiopharmaceutical
does.

### A worked example: three scanners and their software

Apply the rules to three devices.

1. **A dedicated brain PET scanner.** Rule 10, "image in vivo distribution of
   radiopharmaceuticals": class IIa. No other rule gives more.
2. **Its DAQ software.** It drives the scanner, so implementing rule 3.3 gives it the scanner's
   class: IIa. Rule 11, the software rule, would ask how serious the decisions are that the
   software informs, but Rule 11 classifies software in its own right, which this software is
   not.
3. **A PET/CT scanner.** Rule 10 applies twice: the PET part images radiopharmaceuticals (IIa),
   the CT part emits ionizing radiation for diagnosis (IIb). Implementing rule 3.5 takes the
   stricter: IIb. Its DAQ software, by rule 3.3, is IIb too, even though the DAQ software is the
   same kind of code as in the first scanner.

Two lessons follow. First, the class belongs to the device and its intended purpose, not to the
code: the same sorter would be IIa in one product and IIb in another. Second, the MDR class is
not the IEC 62304 software safety class (A, B or C), which comes from the risk analysis of each
software item (Chapter 14). A class IIa scanner can contain class C software, and engineers who
confuse the two systems make mistakes in both directions. Exercise 13.3 turns these rules into a
small model and tests it on these cases.

Standalone software is different. Reconstruction or quantification software sold on its own,
for scanners from several manufacturers, is classified by Rule 11: class IIa if it provides
information used for diagnostic decisions, IIb if such a decision can cause a serious
deterioration of health, III if it can cause death or an irreversible deterioration. MDCG
2019-11 explains how to tell software that is a medical device from software that is not, and
how Rule 11 applies (verify: the current revision of MDCG 2019-11).

### Conformity assessment and the CE marking

Before a device can carry the CE marking, its conformity with the regulation must be assessed.
For class I, the manufacturer declares it alone (with exceptions). From class IIa upward, a
*notified body* takes part: an independent organization designated by a member state and
listed in the EU's NANDO database, which audits the manufacturer and the device.

For a class IIa device, the usual route is Annex IX: the notified body audits the quality
management system (in practice against ISO 13485) and assesses the technical documentation of
representative devices (Article 52(6); verify the route your notified body applies). It then
issues certificates, carries out surveillance audits, including unannounced ones, and must
approve changes that could affect the device's safety and performance before they are
implemented (Annex IX, section 4.10; verify). The manufacturer then draws up the EU declaration
of conformity and affixes the CE marking with the notified body's number.

For software engineers, the notified body is concrete in three ways. Its auditors read your
design documents and trace samples from requirement to test. Its reviewers read the software
parts of the technical documentation. And its change procedure decides whether your next
release can ship on the date planned, which is why change impact analysis (Exercise 13.2) is an
engineering skill.

### Economic operators, people and registration

- **Authorized representative.** A manufacturer established outside the EU must appoint an
  authorized representative inside it (Article 11). Since May 2021 that includes Swiss
  manufacturers (see "Switzerland" below).
- **Person responsible for regulatory compliance.** Every manufacturer must have at least one
  (Article 15), with defined qualifications, who makes sure among other things that the
  technical documentation is up to date and that vigilance obligations are met.
- **Unique device identification (UDI).** Devices carry a UDI on the label and in the database.
  For software, the UDI rules decide which changes need a new identifier (verify: Annex VI, Part
  C, section 6.5 on software UDI).
- **EUDAMED.** The European database on medical devices. Its first four modules (actor
  registration, UDI and device registration, notified bodies and certificates, and market
  surveillance) became mandatory on 28 May 2026, after Commission Decision (EU) 2025/2371 under
  the gradual roll-out of Regulation (EU) 2024/1860; devices already on the market must be
  registered by 28 November 2026 (verify).

### The 2025 reform proposal

The MDR's first years were hard on manufacturers and notified bodies alike: long certification
queues, high costs and devices withdrawn from the market. Its date of application was postponed
by a year in 2020, and the transition deadlines for devices still certified under the old
directives were extended by Regulation (EU) 2023/607. On 16 December 2025 the Commission proposed a targeted revision of the MDR and the
in vitro diagnostic regulation. Among other things it would drop the five-year limit on
certificate validity in favor of continuous surveillance, adjust classification rules including
Rule 11, change notified body procedures and lengthen the general serious-incident reporting
deadline. It is in the ordinary legislative procedure, and adoption is not expected before 2027
(verify: its status when you read this). Until it is adopted and applies, plan to the
regulation in force, and expect the proposal to change on the way.

::: box-mistakes
- **Confusing the MDR class with the IEC 62304 safety class.** The first is the device's, from
  Annex VIII. The second is each software item's, from the risk analysis. A class IIa scanner
  can contain class C software items.
- **Classifying the code instead of the device.** The same sorter is class IIa in a PET scanner
  and IIb in a PET/CT, because the class follows the device's intended purpose.
- **Treating "not harmonised" as "not required".** A standard that gives no presumption of
  conformity is still the state of the art that Annex I asks for, and notified bodies expect it.
- **Assuming the notified body only looks at documents.** Auditors sample records: a test
  report, a code review, a problem report, a change request. If yours do not exist, the
  documents above them are not evidence.
- **Planning a release without the change procedure.** A change that needs the notified body's
  approval cannot ship until it has it. Find out early.
:::

## The United States

### Classification and pathways

The US classifies devices by type, not by rules. Each device type has a classification
regulation in 21 CFR parts 862 to 892, and its class (I, II or III) decides the pathway to the
market:

- **Premarket notification, 510(k).** For most class II devices. The manufacturer shows that the
  device is *substantially equivalent* to a legally marketed *predicate* device: the same
  intended use, and the same technological characteristics, or different ones that raise no new
  questions of safety and effectiveness. FDA clears the device; it does not "approve" it.
- **De Novo.** For a novel device of low to moderate risk with no predicate. If FDA grants it,
  the device type gets a new classification regulation, and the device becomes a possible
  predicate for later 510(k)s.
- **Premarket approval, PMA.** For class III devices: the manufacturer shows safety and
  effectiveness with valid scientific evidence, usually clinical data, and FDA approves it.

PET scanners are "emission computed tomography systems" under 21 CFR 892.1200, class II, with
the product code KPS, and reach the market by 510(k). FDA's public 510(k) database lists many
such clearances, often for PET/CT systems with a second product code for the CT. Dedicated
brain PET scanners are cleared the same way, under product code KPS; the database entry of your
own device names its predicate and its indications for use, and is worth reading early.

### What a submission says about software

FDA's guidance "Content of Premarket Submissions for Device Software Functions", issued in June
2023, replaced the guidance of 2005 and its "level of concern". A submission now has one of two
*documentation levels*:

- **Enhanced**, when a failure or flaw of any device software function could present a
  hazardous situation with a probable risk of death or serious injury, before risk controls are
  applied;
- **Basic**, otherwise.

The level decides how much detail goes into the submission, not how carefully the software is
developed: the guidance expects the same life cycle either way. The submission's software
section contains a documentation level evaluation, a software description, the risk management
file, the software requirements specification, the architecture with diagrams, the software
design specification (Enhanced), a description of the development, configuration management
and maintenance practices, test documentation, a version history and a list of unresolved
anomalies with their assessment. FDA states that conformity to IEC 62304 can support several of
these elements (verify: the guidance's list for each level).

Read that list as your backlog. Every item is something a DAQ team produces anyway if it works
well: the requirements of Chapter 14, the risk file of Chapter 15, the architecture of Chapter
6, the CI evidence of Chapter 20. The difference between a team that struggles with a
submission and one that does not is whether these exist as a by-product of the work.

### The quality system: QMSR

Since 2 February 2026 the US quality system regulation, 21 CFR 820, is the Quality Management
System Regulation (QMSR). It incorporates ISO 13485:2016 by reference, with some additions and
definitions of FDA's own, replacing the older Quality System Regulation and its separate design
control language. A company with a working ISO 13485 system is therefore close to the US
requirements, which was the point of the change. FDA inspects; it does not certify.

### After clearance: changes

A cleared device that changes may need a new 510(k). FDA's guidance "Deciding When to Submit a
510(k) for a Software Change to an Existing Device" (2017) guides the decision with a series of
questions: is the change only to strengthen cybersecurity, or only to restore the device to its
cleared specification? Does it introduce or change a cause of harm, or a risk control for a
hazardous situation that could cause significant harm? Could it significantly affect clinical
functionality or performance? A documented decision that no new 510(k) is needed is a normal
outcome; an undocumented one is a finding in the next inspection. For machine-learning
functions, FDA also accepts predetermined change control plans that are cleared in advance.

### Cybersecurity and reports

Since 2023, section 524B of the FD&C Act requires submissions for *cyber devices*, devices with
software that can connect to the internet and could be vulnerable, to include a plan for
monitoring and addressing vulnerabilities, a software bill of materials and evidence of secure
design. FDA's premarket cybersecurity guidance, final in 2023 and updated in June 2025, says
what it expects (verify). Chapter 17 covers this.

After the market, 21 CFR 803 requires *medical device reports*: within 30 calendar days of
becoming aware of information that a device may have caused or contributed to a death or
serious injury, or has malfunctioned in a way that would be likely to cause one if it
recurred; within 5 work days when remedial action is needed to prevent an unreasonable risk of
substantial harm, or when FDA asks. A foreign manufacturer also registers its establishment,
lists its devices and names a US agent (21 CFR 807).

::: box-mistakes
- **Saying "FDA approved" for a 510(k).** A 510(k) device is cleared; approval is the PMA's
  word. Marketing material and résumés get this wrong.
- **Choosing the documentation level to reduce the paperwork.** The level follows from the risk
  before controls. A Basic submission for software whose failure could seriously injure is a
  deficiency letter.
- **Treating the SBOM as a document for Chapter 17 only.** For a cyber device it is part of the
  submission, and it must match the shipped software.
- **No record for a "no new 510(k)" decision.** The decision is fine; the missing reasoning is
  the finding.
:::

## The standards map

### The documents and their roles

Seven standards and one technical report do most of the work for a PET scanner's software.

| Document | What it covers | In this book |
|---|---|---|
| ISO 13485:2016 | The quality management system: management responsibility, resources, design and development, purchasing, production, measurement, CAPA | Chapter 16 |
| ISO 14971:2019 | Risk management for medical devices: hazards, risk estimation and evaluation, risk controls, residual risk, production and post-production information | Chapter 15 |
| ISO/TR 24971:2020 | Guidance on applying ISO 14971 | Chapter 15 |
| IEC 62304:2006+A1:2015 | The life cycle of medical device software: development, maintenance, risk management, configuration management, problem resolution | Chapter 14 |
| IEC 62366-1:2015+A1:2020 | Usability engineering: use-related hazards and their evaluation | Chapters 14 and 15 |
| IEC 60601-1:2005+A1:2012+A2:2020 | Basic safety and essential performance of medical electrical equipment, including programmable systems | Chapters 19 and 25 |
| IEC 81001-5-1:2021 | Security activities in the health software life cycle | Chapter 17 |
| IEC 62443-4-1:2018 | Secure product development for industrial automation, the model for IEC 81001-5-1 | Chapter 17 |

The difference that matters most is between a *quality management system* standard and a
*life-cycle* standard. ISO 13485 describes the organization: how it controls documents, trains
people, buys parts, handles complaints and designs products in general. It says nothing
specific about software. IEC 62304 describes the processes for one kind of product, software:
what to plan, which activities to do for which safety class, what to record. IEC 62304 assumes
the organization around it has a quality management system and points to ISO 13485 as one way
to have it; ISO 13485 does not require IEC 62304, but an auditor checking design and
development of software will look for something equivalent.

### How they depend on each other

```{.dot include="book/src/diagrams/ch13-standards.dot" caption="The standards map. An arrow reads \"depends on\": requires is a normative reference, references an informative one, presumption the effect of harmonisation, guidance a technical report explaining a standard. Editions as of 2026." width="100%"}
```

The arrows tell you what you cannot do alone. IEC 62304 requires a risk management process that
complies with ISO 14971, so a software team cannot meet IEC 62304 without the risk file of
Chapter 15. IEC 60601-1 applies ISO 14971 to the whole electrical system and, for programmable
systems, makes the software life cycle of IEC 62304 apply. IEC 62366-1 finds use-related hazards
and feeds them to ISO 14971. IEC 81001-5-1 adds security activities to the life cycle that IEC
62304 defines, and borrows its process from IEC 62443-4-1. ISO 14971 sits in the middle: almost
everything depends on it, and it depends on nothing but the organization (verify each arrow
against clause 2, "Normative references", of the editions you work to).

### Harmonised, recognized and in force

Which of these standards are harmonised under the MDR changes by implementing decision. At the
time of writing the list contained EN ISO 13485:2016 with its 2021 amendment, EN ISO 14971:2019
with its 2021 amendment and EN 60601-1, but not EN 62304, EN 62366-1 or EN IEC 81001-5-1
(verify: the Commission's list of harmonised standards for the MDR). FDA's database of
recognized consensus standards lists IEC 62304, ISO 14971 and others with their recognized
editions.

Editions move slowly and then all at once. IEC 62304 dates from 2006, amended in 2015. A second
edition, which would extend its scope to health software in general and replace the three
safety classes with two levels of process rigor, has been in preparation for years; the IEC
currently expects publication in late 2028, and a transition period would follow (verify).
Until then, the 2006+A1:2015 edition is the one auditors expect. Who in your organization
watches for new editions, and decides when to move, is one of the questions to ask.

## Switzerland

Switzerland is not in the EU, and since May 2021 that has mattered for medical devices. The Medical
Devices Ordinance (MedDO, SR 812.213), under the Therapeutic Products Act, follows the MDR closely,
and Swissmedic is the competent authority. Until 2021 the mutual recognition agreement (MRA) between
the EU and Switzerland let devices certified on either side circulate freely. When the MDR began to
apply, the MRA was not updated, and the two sides now treat each other as third countries for
medical devices. Switzerland unilaterally accepts CE marking and certificates from EU notified
bodies, so EU devices reach the Swiss market with a Swiss authorized representative (CH-REP) on the
label. In the other direction, the EU treats a Swiss manufacturer as a third-country manufacturer:
it needs an EU authorized representative, an EU notified body and EUDAMED registration like any
manufacturer from outside the EU. For a Swiss manufacturer that is an everyday
fact: the CE marking comes from an EU notified body, and the EU authorized representative is on the
label.

Three developments are worth following (verify each). Devices on the Swiss market are
registered in Swissmedic's swissdamed database: mandatory for new devices from 1 July 2026,
and by 31 December 2026 for devices already on the market. An updated MRA was signed in March
2026 as part of the wider EU-Swiss package; it needs approval on both sides, possibly including
a Swiss referendum, and is not expected to apply before late 2027. And in April 2025 the Federal
Council decided how to implement Motion 20.3211, which asks that devices cleared by the FDA be
admitted to the Swiss market; the ordinance changes were still being prepared at the time of
writing.

## After the market

### Post-market surveillance

A device on the market is watched for its whole life. Under the MDR, the manufacturer runs a
post-market surveillance system proportionate to the risk class (Articles 83 and 84), with a
written plan, and collects and analyzes data on quality, performance and safety: complaints,
service reports, literature, registries, field data. For class IIa and above, the results go
into a periodic safety update report (PSUR, Article 86), updated at least every two years for
class IIa and every year for IIb and III, which the notified body reviews. For class I, a
post-market surveillance report is updated when necessary (Article 85). The findings flow back
into the risk management file, the clinical evaluation and the design.

### Vigilance

An *incident* is a malfunction or deterioration of a device's characteristics or performance,
an inadequacy of its information, or an undesirable side effect. A *serious incident* is one
that "directly or indirectly led, might have led or might lead to" a death, a temporary or
permanent serious deterioration of someone's health, or a serious public health threat (Article
2). Note "might have led": no harm needs to have happened. The manufacturer reports serious
incidents to the competent authority of the member state where they occurred, immediately after
establishing a causal relationship or that one is reasonably possible, and at the latest
(Article 87):

| Situation | Deadline from awareness |
|---|---|
| Serious public health threat | 2 days |
| Death or unanticipated serious deterioration of health | 10 days |
| Any other serious incident | 15 days |

An initial incomplete report may be followed by a complete one. Non-serious incidents and
expected side effects are not reported one by one, but a statistically significant increase in
their frequency or severity is, by *trend reporting* (Article 88). When the manufacturer acts in
the field to reduce a risk, by a software update, a modification, a recall or advice to users,
that is a *field safety corrective action*, announced to users in a field safety notice.

### A worked example: the missing quarter

On Thursday 7 January 2027 a hospital in Germany reports that an acquisition ended normally, but
the reconstruction looked noisy, and when the physicist checked, a quarter of the coincidences
expected for the activity were missing from the list-mode file. The scan had already been read
as normal. Walk through what happens.

1. **Is it a serious incident?** A normal read of a scan with a quarter of its data missing might
   have led to a missed diagnosis and a delayed treatment: a possible serious deterioration of
   health. It must be assessed as a potential serious incident, even though nobody knows yet
   whether harm occurred. Your procedure, not your opinion of the bug, decides; when in doubt the
   MDR expects a report within the deadline.
2. **Which clock?** No death and no known serious deterioration: the 15-day clock, from the day
   the manufacturer became aware. The report to the German authority is due by 22 January 2027.
3. **The US.** If the same software runs in the US, the event is assessed under 21 CFR 803: a
   malfunction that would be likely to contribute to a serious injury if it recurred is a 30-day
   report, due 6 February. If a field action is needed to stop the use of affected scanners, the
   five-day report applies: due Thursday 14 January.
4. **The engineering question.** Where were the coincidences lost? The run record of Chapter 12
   holds the counters of the link, the sorter and the writer. If a stage counted the loss, the
   question becomes why nobody saw the counter, which is a question about alarms and user
   information. If no stage counted it, a risk control failed silently, and that is the most
   serious finding of all. Either way, your problem report and the CAPA that follows rely on data
   the DAQ recorded at the time.

Exercise 13.4 turns the clocks into code and asks you to write this plan.

### CAPA and the way back to the code

Problems found after release, and serious ones before, go into the *corrective and preventive
action* (CAPA) process of the quality management system: investigate the root cause, correct
it, check that the correction worked, and look for the same cause elsewhere. A CAPA that ends
in a software change goes through the software maintenance process of IEC 62304 and the change
control of the quality system, with its own impact analysis, verification and, if the change
is significant, regulatory notification. Chapter 16 shows how to write one. What matters here
is the loop: field data comes back to the design, and the design's records must be good enough
to find the cause.

### What the DAQ gives post-market surveillance

DAQ software is unusually well placed to help. It sees every event the scanner measures, so it
can record, cheaply and at the time, the facts an investigation needs months later. MiniDAQ
already does much of this: the configuration in every list-mode file, the run record with the
counters of every stage, the audit trail of control commands, and the `simulated` flag. Each
of these is a design decision that serves a regulatory obligation, and each should be traceable
to the requirement it meets.

::: box-mistakes
- **Waiting for the root cause before reporting.** The clock starts when the manufacturer
  becomes aware, not when the investigation ends. Report on time, then complete.
- **"No patient was harmed, so it is not serious."** The definition includes incidents that
  might have led to harm.
- **Fixing it quietly.** A software change made to correct a field problem is a CAPA outcome
  and may be a field safety corrective action. It needs the records, not only the commit.
- **Logs nobody can read later.** A counter without a timestamp, a run without its
  configuration or a log rotated after a day cannot answer an investigator's question.
:::

## MiniDAQ's regulatory file

MiniDAQ is a learning project, not a medical device, and nothing in its repository claims
otherwise. From this chapter on, though, it carries a regulatory file written *as if* it were
the DAQ software of a brain PET scanner, because requirements, risks and tests are much easier
to learn with a definite product to trace them to. The file lives in `docs/regulatory/`, and
this chapter starts it with three documents.

**The intended-use statement** (`intended-use.md`) says what MiniDAQ is for, who uses it, for
which patients and where, how it works and what it is not. Everything else traces back to it.
Its most important sentence is the one that limits it: MiniDAQ produces no image and no
diagnostic information; its outputs are inputs to reconstruction, calibration and quality
control. That sentence decides, for example, that a lost coincidence is a hazard through the
image it degrades, which Chapter 15 will follow.

**The regulatory context** (`regulatory-context.md`) places the scanner in the three markets: its
class and why, the pathways, the standards and editions it applies, where each document of the
regulatory file lives, what the DAQ gives post-market surveillance, and the open questions.
Every fact about a regulation is marked *verify*, because they change.

**The standards map** (`standards-map.dot` and its SVG), the figure above, the same map as
Exercise 13.1's solution.

The test `docs.regulatory` (`tools/check_regulatory.py`) keeps them honest: the intended-use
statement must have every section a reviewer looks for and must say that MiniDAQ is not a
medical device, every relative link in the regulatory documents must resolve, the SVG must
contain every node of its source, and the map must agree with the exercise's solution. That is a
small thing, but it is the same idea as a trace matrix: a document that the build checks stays
true longer than one that nobody does.

::: box-regulated
What the regulatory landscape means for your daily work as a DAQ engineer:

- **Every design input traces to something.** A requirement for the sorter traces to the
  intended use, to a general safety and performance requirement of Annex I, or to a risk
  control. A requirement that traces to nothing is a preference.
- **Write for the auditor who arrives in three years.** Requirements, designs, test reports and
  change records must stand alone, name versions and say why.
- **Every change has an impact analysis.** Which requirements, which risks, which verification,
  and whether the notified body or the FDA must hear about it. You prepare it; regulatory
  affairs and the change control board decide.
- **Field problems come back to you.** Complaint investigations need the data the DAQ recorded.
  Design the counters and records for that day.
- **Know your class, and the other class.** The device's MDR class and FDA classification decide
  the regulatory route; the IEC 62304 safety class of each software item decides your process.
  They are different decisions with different owners.
- **The standards have editions.** Know which ones the technical documentation claims, and do
  not quote from memory a clause your organization's copy does not contain.
:::

::: box-askteam
1. Which notified body certifies your scanner, by which conformity assessment route, and how
   does its change notification procedure work for software releases? Who is the EU authorized
   representative?
2. Which documentation level did your scanner's FDA submission use for software, and which
   predicate device did the 510(k) cite?
3. What are the IEC 62304 safety classes of the DAQ's software items, and where is the argument
   written down?
4. Which editions of IEC 62304, ISO 14971 and IEC 81001-5-1 does the technical documentation
   claim, and who decides when to move to a new one?
5. How do field complaints reach the software team, and what data from the scanner does an
   investigation usually need? Has a DAQ problem ever been a vigilance case?
:::

## Exercises {.unnumbered}

**Exercise 13.1 (E): The standards map.** *Goal:* draw, as one Graphviz diagram, how the
regulations and standards that apply to a PET scanner's software depend on each other, with
labeled arrows for "requires", "references", "presumption" and "guidance". *Starter:*
`exercises/ch13/e1_standards_map/` (a map drawn from memory: documents missing, no editions, and
three edges that are wrong or point the wrong way). *Acceptance:* `tests/test_standards_map.py`
passes: every document of the chapter's map with its edition; one known label per edge; the ten
stated dependencies with the right labels; no edge from ISO 13485 or ISO 14971 to IEC 62304 and
none from the MDR to IEC 62304; only the regulation gives presumption; `dot -Tsvg` renders it.
Then explain in a comment why the arrow from IEC 62304 to ISO 13485 is only "references".
*Time:* 45 minutes.

**Exercise 13.2 (M): What a software change triggers.** *Goal:* write a one-page brief, "What a
software change in your scanner triggers, regulatory-wise", for moving the acquisition PC from
Ubuntu 22.04 to Ubuntu 24.04, with no change to the DAQ's source code. *Starter:*
`exercises/ch13/e2_change_brief/` (a draft a reviewer would send back: "no regulatory impact",
no affected items, unit tests only). *Acceptance:* `tests/test_brief.py` passes: ten sections in
order (change, software items affected, software safety class, risk, verification, EU, US,
Switzerland, documents to update, decision), none empty; at most 700 words; the SOUP, ISO 14971,
regression and latency tests, the notified body and technical documentation, FDA's 2017
software-change guidance and the CE marking each in its section; none of the claims a reviewer
rejects; a decision that names who decides. Then compare your reasoning with the solution's
`NOTES.md`. *Time:* 2 hours.

**Exercise 13.3 (E, extra): Which class is it?** *Goal:* encode the MDR classification rules
that decide a PET scanner's class, and its software's, in a small Python model. *Starter:*
`exercises/ch13/e3_classification/` (stops at the first rule that matches, puts all software in
IIa, forgets implementing rule 3.3). *Acceptance:* `tests/test_classify.py` passes: a brain PET
scanner is IIa by Rule 10, a CT scanner IIb, a PET/CT IIb with both rules reported; software
that drives a device takes its class; standalone software follows Rule 11 by the impact of the
decision it informs (IIa, IIb or III), monitoring software IIa or IIb, other software I; an
active device that no special rule covers is I. Then explain in `NOTES.md` which rule decides
the class of your scanner's reconstruction software if it is sold separately. *Time:* 45
minutes.

**Exercise 13.4 (M, extra): The vigilance clock.** *Goal:* turn the reporting deadlines of MDR
Article 87, 21 CFR 803 and the PSUR of Article 86 into tested code, and plan the reports for one
incident. *Starter:* `exercises/ch13/e4_vigilance_clock/` (one EU clock for every incident, work
days counted as calendar days, a yearly PSUR for every class). *Acceptance:*
`tests/test_vigilance.py` passes: 2, 10 and 15 calendar days in the EU by kind; 30 calendar
days or 5 work days in the US, skipping weekends and the federal holidays passed in; a PSUR every
24 months for IIa and 12 for IIb and III, none for class I; the plan earliest first. Then write
in `NOTES.md` the plan for the missing-quarter report of this chapter. *Time:* 1 hour.

## MiniDAQ milestone: an intended-use statement and a regulatory context page {.unnumbered}

::: box-milestone
**Goal.** MiniDAQ has the first documents of a regulatory file, written as if it were the DAQ
software of a brain PET scanner, and a test that keeps them complete. **Start:** tag `ch12`.
**End:** tag `ch13`.
:::

1. Write `docs/regulatory/intended-use.md`: intended purpose, intended users, patient
   population, use environment, principle of operation, contraindications and limitations,
   data, and what MiniDAQ is not, with every product-specific statement marked as an
   assumption.
2. Write `docs/regulatory/regulatory-context.md`: the scanner's and the software's class in the
   EU and the US and why, the pathways and quality system rules, the Swiss situation, the
   standards and editions applied with their harmonised status, where each document of the file
   lives, what the DAQ gives post-market surveillance, and the open questions.
3. Add the standards map, `docs/regulatory/standards-map.dot` and its SVG.
4. Add `tools/check_regulatory.py` and the CTest test `docs.regulatory`.
5. Add the exercises 13.1 to 13.4.

**Definition of done.** `ci/run_all.sh` is green on all six presets; `docs.regulatory` passes and
fails when a section of the intended-use statement is removed; every statement about a
regulation in the two documents is either sourced in the chapter or marked *verify*; a colleague
who has not read this chapter can answer from the two documents alone: what MiniDAQ is for, which
class the scanner is in and why, and which documents of the regulatory file exist yet. Tag `ch13`.

## Check yourself {.unnumbered}

1. What is the difference between a quality management system standard and a life-cycle
   standard? Give one example of each and say what each would ask about a sorter change.
2. Who decides the software safety class, and from what? How does it differ from the device's
   MDR class?
3. Why is a dedicated brain PET scanner class IIa under the MDR while a PET/CT is IIb? What
   class is the DAQ software in each, and which rule says so?
4. What does a harmonised standard give a manufacturer that a non-harmonised one does not, and
   why are the non-harmonised ones still expected?
5. What is a notified body, what does it do for a class IIa device, and when must it approve a
   change before release?
6. What do 510(k), De Novo and PMA have in common, and what decides which one applies? Which one
   does a PET scanner use?
7. What decides whether a submission's software documentation is Basic or Enhanced, and what
   does the level change?
8. Why does a Swiss manufacturer need an EU authorized representative, and what would the
   updated MRA change?
9. A hospital reports a scan with missing data and no known harm. Is it a serious incident? Which
   EU deadline applies, and when does the clock start?
10. Which data recorded by the DAQ would you want first when investigating that report, and why
    must they be recorded at the time of the scan?

## Summary {.unnumbered}

- Medical device regulation asks "how do you know?" and is answered with documents and records:
  intended use, requirements, design, verification, risk, and what happened after release.
- Regulations are law, standards are agreed ways to meet it (harmonised standards give
  presumption of conformity in the EU), and guidance explains how the regulator reads the law.
- Under the MDR a brain PET scanner is class IIa by Rule 10, and its DAQ software takes the
  device's class by implementing rule 3.3; a PET/CT is IIb.
- From class IIa upward a notified body audits the quality system, assesses the technical
  documentation and must approve significant changes; Annex I, section 17 is written for
  software.
- In the US a PET scanner is a class II device under 21 CFR 892.1200, cleared by 510(k); the
  2023 software guidance sets a Basic or Enhanced documentation level, and the QMSR has
  incorporated ISO 13485 since February 2026.
- ISO 14971 is at the center of the standards map: IEC 62304, IEC 60601-1 and IEC 62366-1
  require it; IEC 62304 only references ISO 13485; IEC 81001-5-1 extends IEC 62304.
- The MDR class of the device and the IEC 62304 safety class of each software item are separate
  decisions.
- Since 2021 the EU treats Swiss manufacturers as third-country manufacturers; Switzerland
  accepts CE marking unilaterally, and an updated MRA is not expected before late 2027.
- After the market, serious incidents are reported within 2, 10 or 15 days in the EU and 5 work
  or 30 calendar days in the US, counted from awareness; findings return to the design through
  CAPA.
- The DAQ is the best-placed component to record, at the time, the facts an investigation needs.

## Further reading {.unnumbered}

- Regulation (EU) 2017/745 on medical devices, consolidated version on EUR-Lex: Articles 2, 10,
  11, 15, 52, 83 to 88, and Annexes I, VIII and IX.
- MDCG 2019-11, "Guidance on qualification and classification of software in Regulation (EU)
  2017/745 and Regulation (EU) 2017/746", and MDCG 2021-24, "Guidance on classification of
  medical devices" (verify: the current revisions).
- MDCG 2023-3, "Questions and answers on vigilance terms and concepts as outlined in the
  Regulation (EU) 2017/745" (verify: the current revision).
- European Commission, proposal of 16 December 2025 for a regulation amending Regulations (EU)
  2017/745 and 2017/746, and its legislative file.
- US FDA, "Content of Premarket Submissions for Device Software Functions", guidance, June 2023.
- US FDA, "Deciding When to Submit a 510(k) for a Software Change to an Existing Device",
  guidance, October 2017.
- US FDA, "Cybersecurity in Medical Devices: Quality System Considerations and Content of
  Premarket Submissions", guidance, 2023, updated June 2025 (verify: the current version).
- 21 CFR 820 (Quality Management System Regulation), 21 CFR 803 (Medical Device Reporting) and
  21 CFR 892.1200 (emission computed tomography system), on the eCFR.
- US FDA, Premarket Notification 510(k) database, accessdata.fda.gov, searchable by product
  code (KPS for PET).
- Swiss Medical Devices Ordinance (MedDO, SR 812.213) on fedlex.admin.ch, and Swissmedic's pages
  on medical devices and swissdamed.
- Johner Institute, articles on the MDR, IEC 62304 and regulatory strategy (free online; a good
  second opinion, not a source of requirements).
