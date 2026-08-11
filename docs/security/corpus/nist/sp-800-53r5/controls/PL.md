# NIST SP 800-53 Rev 5 — PL (Planning)

> **STATUS: VENDORED** — verbatim control text generated from the NIST OSCAL catalog (JSON).
> Source & provenance: `../_source.md`. Master currency ledger: `../../../MANIFEST.md`.
> Doc version 5.2.0 · OSCAL 1.2.2 · catalog last-modified 2026-05-11T16:01:09.00000-00:00 · retrieved 2026-08-11.
> Statement + Discussion for every control/enhancement in the family; 800-53A assessment
> procedures are intentionally excluded. Placeholder brackets ([Assignment: …]/[Selection: …])
> are the standard OSCAL renderings of organization-defined parameters.

## PL-1 — Policy and Procedures

a. Develop, document, and disseminate to [Assignment: organization-defined personnel or roles]:
    1. [Selection (one or more): organization-level; mission/business process-level; system-level] planning policy that:
        (a) Addresses purpose, scope, roles, responsibilities, management commitment, coordination among organizational entities, and compliance; and
        (b) Is consistent with applicable laws, executive orders, directives, regulations, policies, standards, and guidelines; and
    2. Procedures to facilitate the implementation of the planning policy and the associated planning controls;
b. Designate an [Assignment: organization-defined official] to manage the development, documentation, and dissemination of the planning policy and procedures; and
c. Review and update the current planning:
    1. Policy [Assignment: organization-defined frequency] and following [Assignment: organization-defined events] ; and
    2. Procedures [Assignment: organization-defined frequency] and following [Assignment: organization-defined events].

**Discussion:** Planning policy and procedures for the controls in the PL family implemented within systems and organizations. The risk management strategy is an important factor in establishing such policies and procedures. Policies and procedures contribute to security and privacy assurance. Therefore, it is important that security and privacy programs collaborate on their development. Security and privacy program policies and procedures at the organization level are preferable, in general, and may obviate the need for mission level or system-specific policies and procedures. The policy can be included as part of the general security and privacy policy or be represented by multiple policies that reflect the complex nature of organizations. Procedures can be established for security and privacy programs, for mission/business processes, and for systems, if needed. Procedures describe how the policies or controls are implemented and can be directed at the individual or role that is the object of the procedure. Procedures can be documented in system security and privacy plans or in one or more separate documents. Events that may precipitate an update to planning policy and procedures include, but are not limited to, assessment or audit findings, security incidents or breaches, or changes in laws, executive orders, directives, regulations, policies, standards, and guidelines. Simply restating controls does not constitute an organizational policy or procedure.

**Related controls:** PM-9, PS-8, SI-12.

**Provenance:** NIST SP 800-53r5 · PL-1 · rev 5.2.0

## PL-2 — System Security and Privacy Plans

a. Develop security and privacy plans for the system that:
    1. Are consistent with the organization’s enterprise architecture;
    2. Explicitly define the constituent system components;
    3. Describe the operational context of the system in terms of mission and business processes;
    4. Identify the individuals that fulfill system roles and responsibilities;
    5. Identify the information types processed, stored, and transmitted by the system;
    6. Provide the security categorization of the system, including supporting rationale;
    7. Describe any specific threats to the system that are of concern to the organization;
    8. Provide the results of a privacy risk assessment for systems processing personally identifiable information;
    9. Describe the operational environment for the system and any dependencies on or connections to other systems or system components;
    10. Provide an overview of the security and privacy requirements for the system;
    11. Identify any relevant control baselines or overlays, if applicable;
    12. Describe the controls in place or planned for meeting the security and privacy requirements, including a rationale for any tailoring decisions;
    13. Include risk determinations for security and privacy architecture and design decisions;
    14. Include security- and privacy-related activities affecting the system that require planning and coordination with [Assignment: organization-defined individuals or groups] ; and
    15. Are reviewed and approved by the authorizing official or designated representative prior to plan implementation.
b. Distribute copies of the plans and communicate subsequent changes to the plans to [Assignment: organization-defined personnel or roles];
c. Review the plans [Assignment: organization-defined frequency];
d. Update the plans to address changes to the system and environment of operation or problems identified during plan implementation or control assessments; and
e. Protect the plans from unauthorized disclosure and modification.

**Discussion:** System security and privacy plans are scoped to the system and system components within the defined authorization boundary and contain an overview of the security and privacy requirements for the system and the controls selected to satisfy the requirements. The plans describe the intended application of each selected control in the context of the system with a sufficient level of detail to correctly implement the control and to subsequently assess the effectiveness of the control. The control documentation describes how system-specific and hybrid controls are implemented and the plans and expectations regarding the functionality of the system. System security and privacy plans can also be used in the design and development of systems in support of life cycle-based security and privacy engineering processes. System security and privacy plans are living documents that are updated and adapted throughout the system development life cycle (e.g., during capability determination, analysis of alternatives, requests for proposal, and design reviews). [Section 2.1](#c3397cc9-83c6-4459-adb2-836739dc1b94) describes the different types of requirements that are relevant to organizations during the system development life cycle and the relationship between requirements and controls.

Organizations may develop a single, integrated security and privacy plan or maintain separate plans. Security and privacy plans relate security and privacy requirements to a set of controls and control enhancements. The plans describe how the controls and control enhancements meet the security and privacy requirements but do not provide detailed, technical descriptions of the design or implementation of the controls and control enhancements. Security and privacy plans contain sufficient information (including specifications of control parameter values for selection and assignment operations explicitly or by reference) to enable a design and implementation that is unambiguously compliant with the intent of the plans and subsequent determinations of risk to organizational operations and assets, individuals, other organizations, and the Nation if the plan is implemented.

Security and privacy plans need not be single documents. The plans can be a collection of various documents, including documents that already exist. Effective security and privacy plans make extensive use of references to policies, procedures, and additional documents, including design and implementation specifications where more detailed information can be obtained. The use of references helps reduce the documentation associated with security and privacy programs and maintains the security- and privacy-related information in other established management and operational areas, including enterprise architecture, system development life cycle, systems engineering, and acquisition. Security and privacy plans need not contain detailed contingency plan or incident response plan information but can instead provide—explicitly or by reference—sufficient information to define what needs to be accomplished by those plans.

Security- and privacy-related activities that may require coordination and planning with other individuals or groups within the organization include assessments, audits, inspections, hardware and software maintenance, acquisition and supply chain risk management, patch management, and contingency plan testing. Planning and coordination include emergency and nonemergency (i.e., planned or non-urgent unplanned) situations. The process defined by organizations to plan and coordinate security- and privacy-related activities can also be included in other documents, as appropriate.

**Related controls:** AC-2, AC-6, AC-14, AC-17, AC-20, CA-2, CA-3, CA-7, CM-9, CM-13, CP-2, CP-4, IR-4, IR-8, MA-4, MA-5, MP-4, MP-5, PL-7, PL-8, PL-10, PL-11, PM-1, PM-7, PM-8, PM-9, PM-10, PM-11, RA-3, RA-8, RA-9, SA-5, SA-17, SA-22, SI-12, SR-2, SR-4.

**Provenance:** NIST SP 800-53r5 · PL-2 · rev 5.2.0

## PL-2(1) — Concept of Operations

**Withdrawn.** Incorporated into PL-7.

**Provenance:** NIST SP 800-53r5 · PL-2(1) · rev 5.2.0

## PL-2(2) — Functional Architecture

**Withdrawn.** Incorporated into PL-8.

**Provenance:** NIST SP 800-53r5 · PL-2(2) · rev 5.2.0

## PL-2(3) — Plan and Coordinate with Other Organizational Entities

**Withdrawn.** Incorporated into PL-2.

**Provenance:** NIST SP 800-53r5 · PL-2(3) · rev 5.2.0

## PL-3 — System Security Plan Update

**Withdrawn.** Incorporated into PL-2.

**Provenance:** NIST SP 800-53r5 · PL-3 · rev 5.2.0

## PL-4 — Rules of Behavior

a. Establish and provide to individuals requiring access to the system, the rules that describe their responsibilities and expected behavior for information and system usage, security, and privacy;
b. Receive a documented acknowledgment from such individuals, indicating that they have read, understand, and agree to abide by the rules of behavior, before authorizing access to information and the system;
c. Review and update the rules of behavior [Assignment: organization-defined frequency] ; and
d. Require individuals who have acknowledged a previous version of the rules of behavior to read and re-acknowledge [Selection (one or more): [Assignment: organization-defined frequency] ; when the rules are revised or updated].

**Discussion:** Rules of behavior represent a type of access agreement for organizational users. Other types of access agreements include nondisclosure agreements, conflict-of-interest agreements, and acceptable use agreements (see [PS-6](#ps-6) ). Organizations consider rules of behavior based on individual user roles and responsibilities and differentiate between rules that apply to privileged users and rules that apply to general users. Establishing rules of behavior for some types of non-organizational users, including individuals who receive information from federal systems, is often not feasible given the large number of such users and the limited nature of their interactions with the systems. Rules of behavior for organizational and non-organizational users can also be established in [AC-8](#ac-8) . The related controls section provides a list of controls that are relevant to organizational rules of behavior. [PL-4b](#pl-4_smt.b) , the documented acknowledgment portion of the control, may be satisfied by the literacy training and awareness and role-based training programs conducted by organizations if such training includes rules of behavior. Documented acknowledgements for rules of behavior include electronic or physical signatures and electronic agreement check boxes or radio buttons.

**Related controls:** AC-2, AC-6, AC-8, AC-9, AC-17, AC-18, AC-19, AC-20, AT-2, AT-3, CM-11, IA-2, IA-4, IA-5, MP-7, PS-6, PS-8, SA-5, SI-12.

**Provenance:** NIST SP 800-53r5 · PL-4 · rev 5.2.0

## PL-4(1) — Social Media and External Site/Application Usage Restrictions

Include in the rules of behavior, restrictions on:
(a) Use of social media, social networking sites, and external sites/applications;
(b) Posting organizational information on public websites; and
(c) Use of organization-provided identifiers (e.g., email addresses) and authentication secrets (e.g., passwords) for creating accounts on external sites/applications.

**Discussion:** Social media, social networking, and external site/application usage restrictions address rules of behavior related to the use of social media, social networking, and external sites when organizational personnel are using such sites for official duties or in the conduct of official business, when organizational information is involved in social media and social networking transactions, and when personnel access social media and networking sites from organizational systems. Organizations also address specific rules that prevent unauthorized entities from obtaining non-public organizational information from social media and networking sites either directly or through inference. Non-public information includes personally identifiable information and system account information.

**Related controls:** AC-22, AU-13.

**Provenance:** NIST SP 800-53r5 · PL-4(1) · rev 5.2.0

## PL-5 — Privacy Impact Assessment

**Withdrawn.** Incorporated into RA-8.

**Provenance:** NIST SP 800-53r5 · PL-5 · rev 5.2.0

## PL-6 — Security-related Activity Planning

**Withdrawn.** Incorporated into PL-2.

**Provenance:** NIST SP 800-53r5 · PL-6 · rev 5.2.0

## PL-7 — Concept of Operations

a. Develop a Concept of Operations (CONOPS) for the system describing how the organization intends to operate the system from the perspective of information security and privacy; and
b. Review and update the CONOPS [Assignment: organization-defined frequency].

**Discussion:** The CONOPS may be included in the security or privacy plans for the system or in other system development life cycle documents. The CONOPS is a living document that requires updating throughout the system development life cycle. For example, during system design reviews, the concept of operations is checked to ensure that it remains consistent with the design for controls, the system architecture, and the operational procedures. Changes to the CONOPS are reflected in ongoing updates to the security and privacy plans, security and privacy architectures, and other organizational documents, such as procurement specifications, system development life cycle documents, and systems engineering documents.

**Related controls:** PL-2, SA-2, SI-12.

**Provenance:** NIST SP 800-53r5 · PL-7 · rev 5.2.0

## PL-8 — Security and Privacy Architectures

a. Develop security and privacy architectures for the system that:
    1. Describe the requirements and approach to be taken for protecting the confidentiality, integrity, and availability of organizational information;
    2. Describe the requirements and approach to be taken for processing personally identifiable information to minimize privacy risk to individuals;
    3. Describe how the architectures are integrated into and support the enterprise architecture; and
    4. Describe any assumptions about, and dependencies on, external systems and services;
b. Review and update the architectures [Assignment: organization-defined frequency] to reflect changes in the enterprise architecture; and
c. Reflect planned architecture changes in security and privacy plans, Concept of Operations (CONOPS), criticality analysis, organizational procedures, and procurements and acquisitions.

**Discussion:** The security and privacy architectures at the system level are consistent with the organization-wide security and privacy architectures described in [PM-7](#pm-7) , which are integral to and developed as part of the enterprise architecture. The architectures include an architectural description, the allocation of security and privacy functionality (including controls), security- and privacy-related information for external interfaces, information being exchanged across the interfaces, and the protection mechanisms associated with each interface. The architectures can also include other information, such as user roles and the access privileges assigned to each role; security and privacy requirements; types of information processed, stored, and transmitted by the system; supply chain risk management requirements; restoration priorities of information and system services; and other protection needs.

[SP 800-160-1](#e3cc0520-a366-4fc9-abc2-5272db7e3564) provides guidance on the use of security architectures as part of the system development life cycle process. [OMB M-19-03](#c5e11048-1d38-4af3-b00b-0d88dc26860c) requires the use of the systems security engineering concepts described in [SP 800-160-1](#e3cc0520-a366-4fc9-abc2-5272db7e3564) for high value assets. Security and privacy architectures are reviewed and updated throughout the system development life cycle, from analysis of alternatives through review of the proposed architecture in the RFP responses to the design reviews before and during implementation (e.g., during preliminary design reviews and critical design reviews).

In today’s modern computing architectures, it is becoming less common for organizations to control all information resources. There may be key dependencies on external information services and service providers. Describing such dependencies in the security and privacy architectures is necessary for developing a comprehensive mission and business protection strategy. Establishing, developing, documenting, and maintaining under configuration control a baseline configuration for organizational systems is critical to implementing and maintaining effective architectures. The development of the architectures is coordinated with the senior agency information security officer and the senior agency official for privacy to ensure that the controls needed to support security and privacy requirements are identified and effectively implemented. In many circumstances, there may be no distinction between the security and privacy architecture for a system. In other circumstances, security objectives may be adequately satisfied, but privacy objectives may only be partially satisfied by the security requirements. In these cases, consideration of the privacy requirements needed to achieve satisfaction will result in a distinct privacy architecture. The documentation, however, may simply reflect the combined architectures.

[PL-8](#pl-8) is primarily directed at organizations to ensure that architectures are developed for the system and, moreover, that the architectures are integrated with or tightly coupled to the enterprise architecture. In contrast, [SA-17](#sa-17) is primarily directed at the external information technology product and system developers and integrators. [SA-17](#sa-17) , which is complementary to [PL-8](#pl-8) , is selected when organizations outsource the development of systems or components to external entities and when there is a need to demonstrate consistency with the organization’s enterprise architecture and security and privacy architectures.

**Related controls:** CM-2, CM-6, PL-2, PL-7, PL-9, PM-5, PM-7, RA-9, SA-3, SA-5, SA-8, SA-17, SC-7.

**Provenance:** NIST SP 800-53r5 · PL-8 · rev 5.2.0

## PL-8(1) — Defense in Depth

Design the security and privacy architectures for the system using a defense-in-depth approach that:
(a) Allocates [Assignment: organization-defined controls] to [Assignment: organization-defined locations and architectural layers] ; and
(b) Ensures that the allocated controls operate in a coordinated and mutually reinforcing manner.

**Discussion:** Organizations strategically allocate security and privacy controls in the security and privacy architectures so that adversaries must overcome multiple controls to achieve their objective. Requiring adversaries to defeat multiple controls makes it more difficult to attack information resources by increasing the work factor of the adversary; it also increases the likelihood of detection. The coordination of allocated controls is essential to ensure that an attack that involves one control does not create adverse, unintended consequences by interfering with other controls. Unintended consequences can include system lockout and cascading alarms. The placement of controls in systems and organizations is an important activity that requires thoughtful analysis. The value of organizational assets is an important consideration in providing additional layering. Defense-in-depth architectural approaches include modularity and layering (see [SA-8(3)](#sa-8.3) ), separation of system and user functionality (see [SC-2](#sc-2) ), and security function isolation (see [SC-3](#sc-3)).

**Related controls:** SC-2, SC-3, SC-29, SC-36.

**Provenance:** NIST SP 800-53r5 · PL-8(1) · rev 5.2.0

## PL-8(2) — Supplier Diversity

Require that [Assignment: organization-defined controls] allocated to [Assignment: organization-defined locations and architectural layers] are obtained from different suppliers.

**Discussion:** Information technology products have different strengths and weaknesses. Providing a broad spectrum of products complements the individual offerings. For example, vendors offering malicious code protection typically update their products at different times, often developing solutions for known viruses, Trojans, or worms based on their priorities and development schedules. By deploying different products at different locations, there is an increased likelihood that at least one of the products will detect the malicious code. With respect to privacy, vendors may offer products that track personally identifiable information in systems. Products may use different tracking methods. Using multiple products may result in more assurance that personally identifiable information is inventoried.

**Related controls:** SC-29, SR-3.

**Provenance:** NIST SP 800-53r5 · PL-8(2) · rev 5.2.0

## PL-9 — Central Management

Centrally manage [Assignment: organization-defined controls and related processes].

**Discussion:** Central management refers to organization-wide management and implementation of selected controls and processes. This includes planning, implementing, assessing, authorizing, and monitoring the organization-defined, centrally managed controls and processes. As the central management of controls is generally associated with the concept of common (inherited) controls, such management promotes and facilitates standardization of control implementations and management and the judicious use of organizational resources. Centrally managed controls and processes may also meet independence requirements for assessments in support of initial and ongoing authorizations to operate and as part of organizational continuous monitoring.

Automated tools (e.g., security information and event management tools or enterprise security monitoring and management tools) can improve the accuracy, consistency, and availability of information associated with centrally managed controls and processes. Automation can also provide data aggregation and data correlation capabilities; alerting mechanisms; and dashboards to support risk-based decision-making within the organization.

As part of the control selection processes, organizations determine the controls that may be suitable for central management based on resources and capabilities. It is not always possible to centrally manage every aspect of a control. In such cases, the control can be treated as a hybrid control with the control managed and implemented centrally or at the system level. The controls and control enhancements that are candidates for full or partial central management include but are not limited to: [AC-2(1)](#ac-2.1), [AC-2(2)](#ac-2.2), [AC-2(3)](#ac-2.3), [AC-2(4)](#ac-2.4), [AC-4(all)](#ac-4), [AC-17(1)](#ac-17.1), [AC-17(2)](#ac-17.2), [AC-17(3)](#ac-17.3), [AC-17(9)](#ac-17.9), [AC-18(1)](#ac-18.1), [AC-18(3)](#ac-18.3), [AC-18(4)](#ac-18.4), [AC-18(5)](#ac-18.5), [AC-19(4)](#ac-19.4), [AC-22](#ac-22), [AC-23](#ac-23), [AT-2(1)](#at-2.1), [AT-2(2)](#at-2.2), [AT-3(1)](#at-3.1), [AT-3(2)](#at-3.2), [AT-3(3)](#at-3.3), [AT-4](#at-4), [AU-3](#au-3), [AU-6(1)](#au-6.1), [AU-6(3)](#au-6.3), [AU-6(5)](#au-6.5), [AU-6(6)](#au-6.6), [AU-6(9)](#au-6.9), [AU-7(1)](#au-7.1), [AU-7(2)](#au-7.2), [AU-11](#au-11), [AU-13](#au-13), [AU-16](#au-16), [CA-2(1)](#ca-2.1), [CA-2(2)](#ca-2.2), [CA-2(3)](#ca-2.3), [CA-3(1)](#ca-3.1), [CA-3(2)](#ca-3.2), [CA-3(3)](#ca-3.3), [CA-7(1)](#ca-7.1), [CA-9](#ca-9), [CM-2(2)](#cm-2.2), [CM-3(1)](#cm-3.1), [CM-3(4)](#cm-3.4), [CM-4](#cm-4), [CM-6](#cm-6), [CM-6(1)](#cm-6.1), [CM-7(2)](#cm-7.2), [CM-7(4)](#cm-7.4), [CM-7(5)](#cm-7.5), [CM-8(all)](#cm-8), [CM-9(1)](#cm-9.1), [CM-10](#cm-10), [CM-11](#cm-11), [CP-7(all)](#cp-7), [CP-8(all)](#cp-8), [SC-43](#sc-43), [SI-2](#si-2), [SI-3](#si-3), [SI-4(all)](#si-4), [SI-7](#si-7), [SI-8](#si-8).

**Related controls:** PL-8, PM-9.

**Provenance:** NIST SP 800-53r5 · PL-9 · rev 5.2.0

## PL-10 — Baseline Selection

Select a control baseline for the system.

**Discussion:** Control baselines are predefined sets of controls specifically assembled to address the protection needs of a group, organization, or community of interest. Controls are chosen for baselines to either satisfy mandates imposed by laws, executive orders, directives, regulations, policies, standards, and guidelines or address threats common to all users of the baseline under the assumptions specific to the baseline. Baselines represent a starting point for the protection of individuals’ privacy, information, and information systems with subsequent tailoring actions to manage risk in accordance with mission, business, or other constraints (see [PL-11](#pl-11) ). Federal control baselines are provided in [SP 800-53B](#46d9e201-840e-440e-987c-2c773333c752) . The selection of a control baseline is determined by the needs of stakeholders. Stakeholder needs consider mission and business requirements as well as mandates imposed by applicable laws, executive orders, directives, policies, regulations, standards, and guidelines. For example, the control baselines in [SP 800-53B](#46d9e201-840e-440e-987c-2c773333c752) are based on the requirements from [FISMA](#0c67b2a9-bede-43d2-b86d-5f35b8be36e9) and [PRIVACT](#18e71fec-c6fd-475a-925a-5d8495cf8455) . The requirements, along with the NIST standards and guidelines implementing the legislation, direct organizations to select one of the control baselines after the reviewing the information types and the information that is processed, stored, and transmitted on the system; analyzing the potential adverse impact of the loss or compromise of the information or system on the organization’s operations and assets, individuals, other organizations, or the Nation; and considering the results from system and organizational risk assessments. [CNSSI 1253](#4e4fbc93-333d-45e6-a875-de36b878b6b9) provides guidance on control baselines for national security systems.

**Related controls:** PL-2, PL-11, RA-2, RA-3, SA-8.

**Provenance:** NIST SP 800-53r5 · PL-10 · rev 5.2.0

## PL-11 — Baseline Tailoring

Tailor the selected control baseline by applying specified tailoring actions.

**Discussion:** The concept of tailoring allows organizations to specialize or customize a set of baseline controls by applying a defined set of tailoring actions. Tailoring actions facilitate such specialization and customization by allowing organizations to develop security and privacy plans that reflect their specific mission and business functions, the environments where their systems operate, the threats and vulnerabilities that can affect their systems, and any other conditions or situations that can impact their mission or business success. Tailoring guidance is provided in [SP 800-53B](#46d9e201-840e-440e-987c-2c773333c752) . Tailoring a control baseline is accomplished by identifying and designating common controls, applying scoping considerations, selecting compensating controls, assigning values to control parameters, supplementing the control baseline with additional controls as needed, and providing information for control implementation. The general tailoring actions in [SP 800-53B](#46d9e201-840e-440e-987c-2c773333c752) can be supplemented with additional actions based on the needs of organizations. Tailoring actions can be applied to the baselines in [SP 800-53B](#46d9e201-840e-440e-987c-2c773333c752) in accordance with the security and privacy requirements from [FISMA](#0c67b2a9-bede-43d2-b86d-5f35b8be36e9), [PRIVACT](#18e71fec-c6fd-475a-925a-5d8495cf8455) , and [OMB A-130](#27847491-5ce1-4f6a-a1e4-9e483782f0ef) . Alternatively, other communities of interest adopting different control baselines can apply the tailoring actions in [SP 800-53B](#46d9e201-840e-440e-987c-2c773333c752) to specialize or customize the controls that represent the specific needs and concerns of those entities.

**Related controls:** PL-10, RA-2, RA-3, RA-9, SA-8.

**Provenance:** NIST SP 800-53r5 · PL-11 · rev 5.2.0
