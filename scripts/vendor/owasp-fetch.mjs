// owasp-fetch.mjs — vendor OWASP standards from their official GitHub repos.
// Concatenates the verbatim markdown of the controlling chapters into one corpus file
// per standard, with a provenance header pinned to the exact commit SHA fetched.
//
// No text is authored: every section body is the verbatim upstream markdown. This script
// only adds a provenance header and a "Source file:" line before each vendored chapter.
//
// Usage: node scripts/vendor/owasp-fetch.mjs <corpus-owasp-dir> [retrievedDate]
// Requires network at run time (fetches from raw.githubusercontent.com pinned to a SHA).

import { writeFileSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';

const [, , outDir, retrievedArg] = process.argv;
if (!outDir) { console.error('usage: node owasp-fetch.mjs <corpus-owasp-dir> [retrieved]'); process.exit(1); }
const RETRIEVED = retrievedArg || 'unspecified';
const UA = { 'User-Agent': 'secure-builder-corpus-vendor' };

const SOURCES = [
  {
    out: 'top-10.md',
    title: 'OWASP Top 10 — 2021',
    doc: 'OWASP Top 10:2021',
    repo: 'OWASP/Top10', dir: '2021/docs/en',
    files: [
      'A00_2021_Introduction.md',
      'A01_2021-Broken_Access_Control.md', 'A02_2021-Cryptographic_Failures.md',
      'A03_2021-Injection.md', 'A04_2021-Insecure_Design.md',
      'A05_2021-Security_Misconfiguration.md', 'A06_2021-Vulnerable_and_Outdated_Components.md',
      'A07_2021-Identification_and_Authentication_Failures.md', 'A08_2021-Software_and_Data_Integrity_Failures.md',
      'A09_2021-Security_Logging_and_Monitoring_Failures.md', 'A10_2021-Server-Side_Request_Forgery_(SSRF).md',
      'A11_2021-Next_Steps.md',
    ],
  },
  {
    out: 'asvs.md',
    title: 'OWASP Application Security Verification Standard (ASVS) 5.0',
    doc: 'OWASP ASVS v5.0',
    repo: 'OWASP/ASVS', dir: '5.0/en',
    files: [
      '0x03-What-is-the-ASVS.md',
      '0x10-V1-Encoding-and-Sanitization.md', '0x11-V2-Validation-and-Business-Logic.md',
      '0x12-V3-Web-Frontend-Security.md', '0x13-V4-API-and-Web-Service.md',
      '0x14-V5-File-Handling.md', '0x15-V6-Authentication.md',
      '0x16-V7-Session-Management.md', '0x17-V8-Authorization.md',
      '0x18-V9-Self-contained-Tokens.md', '0x19-V10-OAuth-and-OIDC.md',
      '0x20-V11-Cryptography.md', '0x21-V12-Secure-Communication.md',
      '0x22-V13-Configuration.md', '0x23-V14-Data-Protection.md',
      '0x24-V15-Secure-Coding-and-Architecture.md', '0x25-V16-Security-Logging-and-Error-Handling.md',
      '0x26-V17-WebRTC.md',
    ],
  },
  {
    out: 'llm-top-10.md',
    title: 'OWASP Top 10 for LLM Applications — v2.0 (2025)',
    doc: 'OWASP Top 10 for LLM Applications v2.0 (2025)',
    repo: 'OWASP/www-project-top-10-for-large-language-model-applications', dir: '2_0_vulns',
    files: [
      'LLM00_Preface.md',
      'LLM01_PromptInjection.md', 'LLM02_SensitiveInformationDisclosure.md',
      'LLM03_SupplyChain.md', 'LLM04_DataModelPoisoning.md',
      'LLM05_ImproperOutputHandling.md', 'LLM06_ExcessiveAgency.md',
      'LLM07_SystemPromptLeakage.md', 'LLM08_VectorAndEmbeddingWeaknesses.md',
      'LLM09_Misinformation.md', 'LLM10_UnboundedConsumption.md',
    ],
  },
  {
    out: 'masvs.md',
    title: 'OWASP Mobile Application Security Verification Standard (MASVS) v2',
    doc: 'OWASP MASVS v2',
    repo: 'OWASP/masvs', dir: 'Document',
    files: [
      '03-Using_the_MASVS.md',
      '05-MASVS-STORAGE.md', '06-MASVS-CRYPTO.md', '07-MASVS-AUTH.md', '08-MASVS-NETWORK.md',
      '09-MASVS-PLATFORM.md', '10-MASVS-CODE.md', '11-MASVS-RESILIENCE.md', '12-MASVS-PRIVACY.md',
    ],
  },
];

async function ghJson(url) {
  const r = await fetch(url, { headers: { ...UA, Accept: 'application/vnd.github+json' } });
  if (!r.ok) throw new Error(`${url} -> ${r.status}`);
  return r.json();
}
async function raw(repo, sha, path) {
  const url = `https://raw.githubusercontent.com/${repo}/${sha}/${path}`;
  const r = await fetch(url, { headers: UA });
  if (!r.ok) throw new Error(`${url} -> ${r.status}`);
  return r.text();
}

mkdirSync(outDir, { recursive: true });
const summary = [];

for (const s of SOURCES) {
  const repoMeta = await ghJson(`https://api.github.com/repos/${s.repo}`);
  const branch = repoMeta.default_branch;
  const commit = await ghJson(`https://api.github.com/repos/${s.repo}/commits/${branch}`);
  const sha = commit.sha;
  const shortSha = sha.slice(0, 12);

  const out = [];
  out.push(`# ${s.title}`);
  out.push('');
  out.push('> **STATUS: VENDORED** — verbatim chapter markdown from the official OWASP repository.');
  out.push(`> **Source:** \`github.com/${s.repo}\` · dir \`${s.dir}\` · branch \`${branch}\` @ commit \`${shortSha}\`.`);
  out.push(`> **Retrieved:** ${RETRIEVED}. Provenance/currency ledger: \`../MANIFEST.md\`.`);
  out.push(`> Concatenation of the standard's controlling chapters; each chapter is prefixed with its`);
  out.push(`> upstream source filename. Content is verbatim OWASP text (CC BY-SA / OWASP license).`);
  out.push('');
  out.push('---');
  out.push('');

  for (const f of s.files) {
    const body = await raw(s.repo, sha, `${s.dir}/${f}`);
    out.push(`<!-- vendored from ${s.repo}/${s.dir}/${f} @ ${shortSha} -->`);
    out.push('');
    out.push(body.trimEnd());
    out.push('');
    out.push('---');
    out.push('');
  }
  out.push(`**Provenance:** ${s.doc} · ${s.repo}@${shortSha} · retrieved ${RETRIEVED}.`);
  out.push('');

  writeFileSync(join(outDir, s.out), out.join('\n'));
  summary.push(`${s.out}: ${s.files.length} chapters @ ${shortSha} (branch ${branch})`);
}

console.log(summary.join('\n'));
