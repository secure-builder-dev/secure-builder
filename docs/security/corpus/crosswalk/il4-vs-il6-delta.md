# IL4 → IL6 Baseline Delta (800-53B High − Moderate)

> **STATUS: VENDORED** — derived set difference of the OSCAL Moderate and High profiles.
> Basis: 800-53B High − Moderate membership. Doc version 5.2.0 · retrieved 2026-08-11.
> This is the 800-53 control-baseline delta only. The DoD CC SRG IL4→IL6 overlay
> (mission-owner / CSP responsibilities, jurisdiction, connectivity) is layered separately
> once `../disa/srg/cloud-computing-srg.md` is vendored — see that file for SRG-level deltas.
> Provenance/currency: `../MANIFEST.md`.

Moderate (IL4): **287** · High (IL6): **370** · Added at IL6: **83** · Removed: **0**.

## Controls added when moving IL4 → IL6

### AC — Access Control

- AC-2(11) — Usage Conditions
- AC-2(12) — Account Monitoring for Atypical Usage
- AC-4(4) — Flow Control of Encrypted Information
- AC-6(3) — Network Access to Privileged Commands
- AC-10 — Concurrent Session Control
- AC-18(4) — Restrict Configurations by Users
- AC-18(5) — Antennas and Transmission Power Levels

### AU — Audit and Accountability

- AU-5(1) — Storage Capacity Warning
- AU-5(2) — Real-time Alerts
- AU-6(5) — Integrated Analysis of Audit Records
- AU-6(6) — Correlation with Physical Monitoring
- AU-9(2) — Store on Separate Physical Systems or Components
- AU-9(3) — Cryptographic Protection
- AU-10 — Non-repudiation
- AU-12(1) — System-wide and Time-correlated Audit Trail
- AU-12(3) — Changes by Authorized Individuals

### CA — Assessment, Authorization, and Monitoring

- CA-2(2) — Specialized Assessments
- CA-3(6) — Transfer Authorizations
- CA-8 — Penetration Testing
- CA-8(1) — Independent Penetration Testing Agent or Team

### CM — Configuration Management

- CM-3(1) — Automated Documentation, Notification, and Prohibition of Changes
- CM-3(6) — Cryptography Management
- CM-4(1) — Separate Test Environments
- CM-5(1) — Automated Access Enforcement and Audit Records
- CM-6(1) — Automated Management, Application, and Verification
- CM-6(2) — Respond to Unauthorized Changes
- CM-8(2) — Automated Maintenance
- CM-8(4) — Accountability Information

### CP — Contingency Planning

- CP-2(2) — Capacity Planning
- CP-2(5) — Continue Mission and Business Functions
- CP-3(1) — Simulated Events
- CP-4(2) — Alternate Processing Site
- CP-6(2) — Recovery Time and Recovery Point Objectives
- CP-7(4) — Preparation for Use
- CP-8(3) — Separation of Primary and Alternate Providers
- CP-8(4) — Provider Contingency Plan
- CP-9(2) — Test Restoration Using Sampling
- CP-9(3) — Separate Storage for Critical Information
- CP-9(5) — Transfer to Alternate Storage Site
- CP-10(4) — Restore Within Time Period

### IA — Identification and Authentication

- IA-2(5) — Individual Authentication with Group Authentication
- IA-12(4) — In-person Validation and Verification

### IR — Incident Response

- IR-2(1) — Simulated Events
- IR-2(2) — Automated Training Environments
- IR-4(4) — Information Correlation
- IR-4(11) — Integrated Incident Response Team
- IR-5(1) — Automated Tracking, Data Collection, and Analysis

### MA — Maintenance

- MA-2(2) — Automated Maintenance Activities
- MA-4(3) — Comparable Security and Sanitization
- MA-5(1) — Individuals Without Appropriate Access

### MP — Media Protection

- MP-6(1) — Review, Approve, Track, Document, and Verify
- MP-6(2) — Equipment Testing
- MP-6(3) — Nondestructive Techniques

### PE — Physical and Environmental Protection

- PE-3(1) — System Access
- PE-6(4) — Monitoring Physical Access to Systems
- PE-8(1) — Automated Records Maintenance and Review
- PE-11(1) — Alternate Power Supply — Minimal Operational Capability
- PE-13(2) — Suppression Systems — Automatic Activation and Notification
- PE-15(1) — Automation Support
- PE-18 — Location of System Components

### PS — Personnel Security

- PS-4(2) — Automated Actions

### RA — Risk Assessment

- RA-5(4) — Discoverable Information

### SA — System and Services Acquisition

- SA-4(5) — System, Component, and Service Configurations
- SA-16 — Developer-provided Training
- SA-17 — Developer Security and Privacy Architecture and Design
- SA-21 — Developer Screening

### SC — System and Communications Protection

- SC-3 — Security Function Isolation
- SC-7(18) — Fail Secure
- SC-7(21) — Isolation of System Components
- SC-12(1) — Availability
- SC-24 — Fail in Known State

### SI — System and Information Integrity

- SI-4(10) — Visibility of Encrypted Communications
- SI-4(12) — Automated Organization-generated Alerts
- SI-4(14) — Wireless Intrusion Detection
- SI-4(20) — Privileged Users
- SI-4(22) — Unauthorized Network Services
- SI-5(1) — Automated Alerts and Advisories
- SI-6 — Security and Privacy Function Verification
- SI-7(2) — Automated Notifications of Integrity Violations
- SI-7(5) — Automated Response to Integrity Violations
- SI-7(15) — Code Authentication

### SR — Supply Chain Risk Management

- SR-9 — Tamper Resistance and Detection
- SR-9(1) — Multiple Stages of System Development Life Cycle
