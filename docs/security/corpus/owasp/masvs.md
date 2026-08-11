# OWASP Mobile Application Security Verification Standard (MASVS) v2

> **STATUS: VENDORED** — verbatim chapter markdown from the official OWASP repository.
> **Source:** `github.com/OWASP/masvs` · dir `Document` · branch `master` @ commit `c0db792d4820`.
> **Retrieved:** 2026-08-11. Provenance/currency ledger: `../MANIFEST.md`.
> Concatenation of the standard's controlling chapters; each chapter is prefixed with its
> upstream source filename. Content is verbatim OWASP text (CC BY-SA / OWASP license).

---

<!-- vendored from OWASP/masvs/Document/03-Using_the_MASVS.md @ c0db792d4820 -->

# The Mobile Application Security Verification Standard

The Mobile Application Security Verification Standard (MASVS) is a comprehensive security standard developed by the Open Worldwide Application Security Project (OWASP). This framework provides a clear and concise set of guidelines and best practices for assessing and enhancing the security of mobile applications. The MASVS is designed to be used as a metric, guidance, and baseline for mobile app security verification, serving as a valuable resource for developers, application owners, and security professionals.

The objective of the MASVS is to establish a high level of confidence in the security of mobile apps by providing a set of controls that address the most common mobile application security issues. These controls were developed with a focus on providing guidance during all phases of mobile app development and testing, and to be used as a baseline for mobile app security verification during procurement.

By adhering to the controls outlined in the OWASP MASVS, organizations can ensure that their mobile applications are built with security in mind, reducing the risk of security breaches and protecting sensitive user data. Whether used as a metric, guidance, or baseline, the OWASP MASVS is an invaluable tool for enhancing the security of mobile applications.

The OWASP MASVS is a living document and is regularly updated to reflect the changing threat landscape and new attack vectors. As such, it's important to [stay up-to-date](https://mas.owasp.org/MASVS/) with the latest version of the standard and adapt security measures accordingly.

## Mobile Application Security Model

The standard is divided into various groups that represent the most critical areas of the mobile attack surface. These control groups, labeled **MASVS-XXXXX**, provide guidance and standards for the following areas:

- **MASVS-STORAGE:** Secure storage of sensitive data on a device (data-at-rest).
- **MASVS-CRYPTO:** Cryptographic functionality used to protect sensitive data.
- **MASVS-AUTH:** Authentication and authorization mechanisms used by the mobile app.
- **MASVS-NETWORK:** Secure network communication between the mobile app and remote endpoints (data-in-transit).
- **MASVS-PLATFORM:** Secure interaction with the underlying mobile platform and other installed apps.
- **MASVS-CODE:** Security best practices for data processing and keeping the app up-to-date.
- **MASVS-RESILIENCE:** Resilience to reverse engineering and tampering attempts.
- **MASVS-PRIVACY:** Privacy controls to protect user privacy.

Each of these control groups contains individual controls labeled **MASVS-XXXXX-Y**, which provide specific guidance on the particular security measures that need to be implemented to meet the standard.

## MAS Testing Profiles

The MAS project has traditionally provided three verification levels (L1, L2 and R), which were revisited during the MASVS refactoring in 2023, and have been reworked as ["MAS Testing Profiles"](https://mas.owasp.org/MASTG/0x03b-Testing-Profiles/) and moved over to the OWASP MASTG. These profiles are now aligned with the [NIST OSCAL (Open Security Controls Assessment Language)](https://pages.nist.gov/OSCAL/) standard, which is a comprehensive catalog of security controls that can be used to secure information systems.

By aligning with OSCAL, the MASVS provides a more flexible and comprehensive approach to security testing. OSCAL provides a standard format for security control information, which allows for easier sharing and reuse of security controls across different systems and organizations. This allows for a more efficient use of resources and a more targeted approach to mobile app security testing.

However, it is important to note that implementing these profiles fully or partially should be a risk-based decision made in consultation with business owners. The profiles should be tailored to the specific security risks and requirements of the mobile application being developed, and any deviations from the recommended controls should be carefully justified and documented.

## Assumptions

When using the MASVS, it's important to keep in mind the following assumptions:

- The MASVS is not a substitute for following secure development best practices, such as secure coding or secure SDLC. These practices should be followed holistically in your development process and the MASVS complements them specifically for mobile apps.
- The MASVS assumes that you've followed the relevant standards of your industry and country for all elements of your app's ecosystem, such as backend servers, IoT, and other companion devices.
- The MASVS is designed to evaluate the security of mobile apps that can be analyzed statically by obtaining the app package, dynamically by running it on a potentially compromised device, and also considers any network-based attacks such as MITM.

While the OWASP MASVS is an invaluable tool for enhancing the security of mobile applications, it cannot guarantee absolute security. It should be used as a baseline for security requirements, but additional security measures should also be implemented as appropriate to address specific risks and threats to the mobile app.

### Security Architecture, Design and Threat Modeling for Mobile Apps

> The OWASP MASVS assumes that best practices for secure architecture, design, and threat modeling have been followed as a foundation.

Security must be a top priority throughout all stages of mobile app development, from the initial planning and design phase to deployment and ongoing maintenance. Developers need to follow secure development best practices and ensure that security measures are prioritized to protect sensitive data, comply with policies and regulations, and identify and address security issues that can be targeted by attackers.

While the MASVS and MASTG focuses on controls and technical test cases for app security assessments, non-technical aspects such as following best practices laid out by [OWASP Software Assurance Maturity Model (SAMM)](https://owaspsamm.org/model/) or [NIST.SP.800-218 Secure Software Development Framework (SSDF)](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-218.pdf) for secure architecture, design, and threat modeling are still important. The MASVS can also be used as reference and input for a threat model to raise awareness of potential attacks.

To ensure that these practices are followed, developers can provide documentation or evidence of adherence to these standards, such as design documents, threat models, and security architecture diagrams. Additionally, interviews can be conducted to collect information on adherence to these practices and provide an understanding of the level of compliance with these standards.

### Secure App Ecosystem

> The OWASP MASVS assumes other relevant security standards are also leveraged to ensure that all systems involved in the app's operation meet their applicable requirements.

Mobile apps often interact with multiple systems, including backend servers, third-party APIs, Bluetooth devices, cars, IoT devices, and more. Each of these systems may introduce their own security risks that must be considered as part of the mobile app's security design and threat modeling. For example, when interacting with a backend server, the [OWASP Application Security Verification Standard (ASVS)](https://owasp.org/www-project-application-security-verification-standard/) should be used to ensure that the server is secure and meets the required security standards. In the case of Bluetooth devices, the app should be designed to prevent unauthorized access, while for cars, the app should be designed to protect the user's data and ensure that there are no safety issues with the car's operation.

### Security Knowledge and Expertise

> The OWASP MASVS assumes a certain level of security knowledge and expertise among developers and security professionals using the standard. It's important to have a good understanding of mobile app security concepts, as well as the relevant tools and techniques used for mobile app security testing and assessment. To support this, the OWASP MAS project also provides the [OWASP Mobile Application Security Testing Guide (MASTG)](https://mas.owasp.org/MASTG/), which provides in-depth guidance on mobile app security testing and assessment.

Mobile app development is a rapidly evolving field, with new technologies, programming languages, and frameworks constantly emerging. It's essential for developers and security professionals to stay current with these developments, as well as to have a solid foundation in fundamental security principles.

OWASP SAMM provides a dedicated ["Education & Guidance"](https://owaspsamm.org/model/governance/education-and-guidance/) domain which aims to ensure that all stakeholders involved in the software development lifecycle are aware of the software security risks and are equipped with the knowledge and skills to mitigate these risks. This includes developers, testers, architects, project managers, executives, and other personnel involved in software development and deployment.

## Applicability of the MASVS

By adhering to the MASVS, businesses and developers can ensure that their mobile app are secure and meet industry-standard security requirements, regardless of the development approach used. This is the case for downloadable apps, as the project was traditionally focused on, but the MAS resources and guidelines are also applicable to other areas of the business such as preloaded applications and SDKs.

### Native Apps

Native apps are written in platform-specific languages, such as Java/Kotlin for Android or Objective-C/Swift for iOS.

### Cross-Platform and Hybrid Apps

Apps based on cross-platform (Flutter, React Native, Xamarin, Ionic, etc.) and hybrid (Cordova, PhoneGap, Framework7, Onsen UI, etc.) frameworks may be susceptible to platform-specific vulnerabilities that don't exist in native apps. For example, some JavaScript frameworks may introduce new security issues that don't exist in other programming languages. It is therefore essential to follow the security best practices of the used frameworks.

The MASVS is agnostic to the type of mobile application being developed. This means that the guidelines and best practices outlined in the MASVS can be applied to all types of mobile apps, including cross-platform and hybrid apps.

### Preloads

Preloaded apps are apps that are installed on a user's device at factory time and may have elevated privileges that leave users vulnerable to exploitative business practices. Given the large number of preloaded apps on an average user's device, it's important to measure their risk in a quantifiable way.

There are hundreds of preloads that may ship on a device, and as a result, automation is critical. A subset of MAS criteria that is automation-friendly may be a good basis.

### SDKs

SDKs play a vital role in the mobile app value chain, supplying code developers need to build faster, smarter, and more profitably. Developers rely on them heavily, with the average mobile app using 30 SDKs, and 90% of code sourced from third parties. While this widespread use delivers significant benefits to developers, it also propagates safety and security issues.

SDKs offer a variety of functionality, and should be regarded as an individual project. You should evaluate how the MASVS applies to the used SDKs to ensure the highest possible security testing coverage.

---

<!-- vendored from OWASP/masvs/Document/05-MASVS-STORAGE.md @ c0db792d4820 -->

# MASVS-STORAGE: Storage

Mobile applications handle a wide variety of sensitive data, such as personally identifiable information (PII), cryptographic material, secrets, and API keys, that often need to be stored locally. This sensitive data may be stored in private locations, such as the app's internal storage, or in public folders that are accessible by the user or other apps installed on the device. However, sensitive data can also be unintentionally stored or exposed to publicly accessible locations, typically as a side-effect of using certain APIs or system capabilities such as backups or logs.

This category is designed to help developers ensure that any sensitive data intentionally stored by the app is properly protected, regardless of the target location. It also covers unintentional leaks that can occur due to improper use of APIs or system capabilities.

---

<!-- vendored from OWASP/masvs/Document/06-MASVS-CRYPTO.md @ c0db792d4820 -->

# MASVS-CRYPTO: Cryptography

Cryptography is essential for mobile apps because mobile devices are highly portable and can be easily lost or stolen. This means that an attacker who gains physical access to a device can potentially access all the sensitive data stored on it, including passwords, financial information, and personally identifiable information. Cryptography provides a means of protecting this sensitive data by encrypting it so that it cannot be easily read or accessed by an unauthorized user.

The purpose of the controls in this category is to ensure that the verified app uses cryptography according to industry best practices, which are typically defined in external standards such as [NIST.SP.800-175B](https://csrc.nist.gov/publications/detail/sp/800-175b/rev-1/final) and [NIST.SP.800-57](https://csrc.nist.gov/publications/detail/sp/800-57-part-1/rev-5/final). This category also focuses on the management of cryptographic keys throughout their lifecycle, including key generation, storage, and protection. Poor key management can compromise even the strongest cryptography, so it is crucial for developers to follow the recommended best practices to ensure the security of their users' sensitive data.

---

<!-- vendored from OWASP/masvs/Document/07-MASVS-AUTH.md @ c0db792d4820 -->

# MASVS-AUTH: Authentication and Authorization

Authentication and authorization are essential components of most mobile apps, especially those that connect to a remote service. These mechanisms provide an added layer of security and help prevent unauthorized access to sensitive user data. Although the enforcement of these mechanisms must be on the remote endpoint, it is equally important for the app to follow relevant best practices to ensure the secure use of the involved protocols.

Mobile apps often use different forms of authentication, such as biometrics, PIN, or multi-factor authentication code generators, to validate user identity. These mechanisms must be implemented correctly to ensure their effectiveness in preventing unauthorized access. Additionally, some apps may rely solely on local app authentication and may not have a remote endpoint. In such cases, it is critical to ensure that local authentication mechanisms are secure and implemented following industry best practices.

The controls in this category aim to ensure that the app implements authentication and authorization mechanisms securely, protecting sensitive user information and preventing unauthorized access. It is important to note that the security of the remote endpoint should also be validated using industry standards such as the [OWASP Application Security Verification Standard (ASVS)](https://owasp.org/www-project-application-security-verification-standard/).

---

<!-- vendored from OWASP/masvs/Document/08-MASVS-NETWORK.md @ c0db792d4820 -->

# MASVS-NETWORK: Network Communication

Secure networking is a critical aspect of mobile app security, particularly for apps that communicate over the network. In order to ensure the confidentiality and integrity of data in transit, developers typically rely on encryption and authentication of the remote endpoint, such as through the use of TLS. However, there are numerous ways in which a developer may accidentally disable the platform secure defaults or bypass them entirely by utilizing low-level APIs or third-party libraries.

This category is designed to ensure that the mobile app sets up secure connections under any circumstances. Specifically, it focuses on verifying that the app establishes a secure, encrypted channel for network communication. Additionally, this category covers situations where a developer may choose to trust only specific Certificate Authorities (CAs), which is commonly referred to as certificate pinning or public key pinning.

---

<!-- vendored from OWASP/masvs/Document/09-MASVS-PLATFORM.md @ c0db792d4820 -->

# MASVS-PLATFORM: Platform Interaction

The security of mobile apps heavily depends on their interaction with the mobile platform, which often involves exposing data or functionality intentionally through the use of platform-provided inter-process communication (IPC) mechanisms and WebViews to enhance the user experience. However, these mechanisms can also be exploited by attackers or other installed apps, potentially compromising the app's security.

Furthermore, sensitive data, such as passwords, credit card details, and one-time passwords in notifications, is often displayed in the app's user interface. It is essential to ensure that this data is not unintentionally leaked through platform mechanisms such as auto-generated screenshots or accidental disclosure through shoulder surfing or device sharing.

This category comprises controls that ensure the app's interactions with the mobile platform occur securely. These controls cover the secure use of platform-provided IPC mechanisms, WebView configurations to prevent sensitive data leakage and functionality exposure, and secure display of sensitive data in the app's user interface. By implementing these controls, mobile app developers can safeguard sensitive user information and prevent unauthorized access by attackers.

---

<!-- vendored from OWASP/masvs/Document/10-MASVS-CODE.md @ c0db792d4820 -->

# MASVS-CODE: Code Quality

Mobile apps have many data entry points, including the UI, IPC, network, and file system, which might receive data that has been inadvertently modified by untrusted actors. By treating this data as untrusted input and properly verifying and sanitizing it before use, developers can prevent classical injection attacks, such as SQL injection, XSS, or insecure deserialization. However, other common coding vulnerabilities, such as memory corruption flaws, are hard to detect in penetration testing but easy to prevent with secure architecture and coding practices. Developers should follow best practices such as the [OWASP Software Assurance Maturity Model (SAMM)](https://owaspsamm.org/model/) and [NIST.SP.800-218 Secure Software Development Framework (SSDF)](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-218.pdf) to avoid introducing these flaws in the first place.

This category covers coding vulnerabilities that arise from external sources such as app data entry points, the OS, and third-party software components. Developers should verify and sanitize all incoming data to prevent injection attacks and bypass of security checks. They should also enforce app updates and ensure that the app runs up-to-date platforms to protect users from known vulnerabilities.

---

<!-- vendored from OWASP/masvs/Document/11-MASVS-RESILIENCE.md @ c0db792d4820 -->

# MASVS-RESILIENCE: Resilience Against Reverse Engineering and Tampering

Defense-in-depth measures such as code obfuscation, anti-debugging, anti-tampering, and runtime application self-protection (RASP) can increase an app's resilience against reverse engineering and specific client-side attacks. They add multiple layers of security controls to the app, making it more difficult for attackers to modify code or extract sensitive information.

**The absence of these measures does not in itself constitute a vulnerability**. Instead, resilience controls provide additional protection against threat-specific attacks. **All apps must also fulfill the rest of the OWASP MASVS** controls according to their threat model.

## Business and Commercial Perspective

Resilience measures are particularly relevant when the app needs to protect business assets or deter client-side abuse. They can help mitigate risks such as:

- Theft or compromise of proprietary algorithms, trade secrets, customer data, AI or machine learning models  
- Fraud, cheating, or revenue leakage in online games, financial apps, or subscription models  
- Legal and reputational damage due to breach of contracts or regulations  
- Damage to brand reputation due to negative publicity or customer dissatisfaction

These controls aim to ensure the app is running on a trusted platform, detect or prevent tampering at runtime, and preserve the integrity of the app's intended functionality.

## Transparency and Open Audit Perspective

In some contexts, such as government, health, or other public-interest apps, resilience measures may not be ideal due to multiple reasons:

- It reduces transparency of what the compiled application is doing  
- Independent verification of the compiled application is more difficult  
- The diversity of smartphone operating systems can lead to false positives, potentially excluding legitimate users

In case these concerns are valid for the target application, we recommend applying the following principles:

- Open source distribution of source code for independent audits  
- Security must rely on verifiable design, strong cryptography, and server-side validation  
- Anti-tampering or obfuscation techniques must not be used as a substitute for proper security architecture  
- Controls should prevent cheating or malicious modification without hindering legitimate users and legitimate analysis or oversight

## Platform Lock-in

Runtime resilience controls focus on two things:

- The application and its own memory and files  
- The underlying OS

While verifying the integrity of the application itself is typically OS-agnostic, the same cannot be said for verifying the underlying OS. For example, while there is an open-source version of Android (AOSP), this is typically not the OS that is installed on consumer devices. Instead, many different flavors are developed with small differences in feature sets and security controls. Some examples include Google Android, HarmonyOS, FireOS, LineageOS, /e/OS, etc. By implementing flavor-specific detection mechanisms, the application may not function on any other flavor of Android. This results in a platform lock-in, possibly excluding legitimate users from using the application.  

Additionally, reliance on platform services such as Google Play Integrity API or Apple's App Attestation may further reinforce lock-in and limit accessibility for certain user groups.

## Malware and Testing Perspective

Resilience techniques can also be abused by malicious software. Malware authors often use code obfuscation, anti-debugging, and anti-tampering to:

- Conceal malicious functionality  
- Evade security tools or app store review  
- Frustrate researchers and hinder forensic analysis

For this reason, security testers must understand these techniques, know how to detect them, and practice bypassing them. This ensures that security assessments remain effective, and that defensive controls are distinguished from attempts to conceal harmful behavior.

---

<!-- vendored from OWASP/masvs/Document/12-MASVS-PRIVACY.md @ c0db792d4820 -->

# MASVS-PRIVACY: Privacy

The main goal of MASVS-PRIVACY is to provide a **baseline for user privacy**. It is not intended to cover all aspects of user privacy, especially when other standards and regulations such as ENISA or the GDPR already do that. We focus on the app itself, looking at what can be tested using information that's publicly available or found within the app through methods like static or dynamic analysis.

While some associated tests can be automated, others necessitate manual intervention due to the nuanced nature of privacy. For example, if an app collects data that it didn't mention in the app store or its privacy policy, it takes careful manual checking to spot this.

> **Note on "Data Collection and Sharing"**:For the MASTG tests, we treat "Collect" and "Share" in a unified manner. This means that whether the app is sending data to another server or transferring it to another app on the device, we view it as data that's potentially leaving the user's control. Validating what happens to the data on remote endpoints is challenging and often not feasible due to access restrictions and the dynamic nature of server-side operations. Therefore, this issue is outside of the scope of the MASVS.

**IMPORTANT DISCLAIMER**:

MASVS-PRIVACY is not intended to serve as an exhaustive or exclusive reference. While it provides valuable guidance on app-centric privacy considerations, it should never replace comprehensive assessments, such as a Data Protection Impact Assessment (DPIA) mandated by the General Data Protection Regulation (GDPR) or other pertinent legal and regulatory frameworks. Stakeholders are strongly advised to undertake a holistic approach to privacy, integrating MASVS-PRIVACY insights with broader assessments to ensure comprehensive data protection compliance. Given the specialized nature of privacy regulations and the complexity of data protection, these assessments are best conducted by privacy experts rather than security experts.

---

**Provenance:** OWASP MASVS v2 · OWASP/masvs@c0db792d4820 · retrieved 2026-08-11.
