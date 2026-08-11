// xccdf-stig-to-md.mjs — vendor a DISA STIG / SRG from its XCCDF XML benchmark into
// markdown, one section per rule (STIG-ID — title; severity; discussion; check; fix),
// with provenance.
//
// STATUS: VERIFIED against the DISA Application Security & Development STIG V6R4
// (U_ASD_STIG_V6R4_Manual-xccdf.xml, 286 rules, benchmark date 01 Oct 2025) on 2026-08-11.
// No control text is authored here — every field is extracted verbatim from the XCCDF and
// XML-entity-decoded. Still spot-check >=2 rules against the source for any NEW benchmark,
// since DISA XCCDF shapes can vary slightly by product.
//
// Discovery note: the public.cyber.mil download *catalog* is a Salesforce/reCAPTCHA portal
// (not scriptable), but individual archives are direct-downloadable from
// dl.dod.cyber.mil/wp-content/uploads/stigs/zip/U_<SHORT>_V<v>R<r>_STIG.zip once the exact
// short code + version is known.
//
// Dependency-free (no XML library) so an air-gapped refresh needs only Node. The parser
// targets DISA's regular <Group><Rule>…</Rule></Group> structure; if DISA changes the
// shape, adjust the extractors below rather than hand-editing output.
//
// Usage: node scripts/vendor/xccdf-stig-to-md.mjs <benchmark.xml> <out.md> "<Doc Title>" "<Provenance doc id>" [retrievedDate]

import { readFileSync, writeFileSync } from 'node:fs';

const [, , xmlPath, outPath, docTitle, provId, retrievedArg] = process.argv;
if (!xmlPath || !outPath || !docTitle || !provId) {
  console.error('usage: node xccdf-stig-to-md.mjs <benchmark.xml> <out.md> "<Doc Title>" "<Prov doc id>" [retrieved]');
  process.exit(1);
}
const RETRIEVED = retrievedArg || 'unspecified';
const xml = readFileSync(xmlPath, 'utf8');

// Tag-name boundary: the name must not be followed by a word char or hyphen, so that
// e.g. `check-content` never matches the sibling self-closing `check-content-ref`.
const NB = '(?![\\w-])';

function decode(s) {
  if (s == null) return '';
  return s
    .replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, '$1')
    .replace(/&lt;/g, '<').replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"').replace(/&apos;/g, "'")
    .replace(/&#(\d+);/g, (_, d) => String.fromCodePoint(+d))
    .replace(/&#x([0-9a-f]+);/gi, (_, h) => String.fromCodePoint(parseInt(h, 16)))
    .replace(/&amp;/g, '&'); // amp last
}
// first captured inner text of <tag ...>inner</tag>, namespace-agnostic
function inner(block, tag) {
  const re = new RegExp(`<(?:[\\w.-]+:)?${tag}${NB}[^>]*>([\\s\\S]*?)</(?:[\\w.-]+:)?${tag}>`, 'i');
  const m = block.match(re);
  return m ? m[1] : null;
}
function attr(openTag, name) {
  const m = openTag.match(new RegExp(`${name}\\s*=\\s*"([^"]*)"`, 'i'));
  return m ? m[1] : null;
}
// extract all top-level blocks for a tag (handles simple, non-recursive DISA nesting of Rules within Groups)
function blocks(src, tag) {
  const out = [];
  const open = new RegExp(`<(?:[\\w.-]+:)?${tag}${NB}[^>]*>`, 'gi');
  const close = new RegExp(`</(?:[\\w.-]+:)?${tag}>`, 'gi');
  let m;
  while ((m = open.exec(src))) {
    close.lastIndex = open.lastIndex;
    const c = close.exec(src);
    if (!c) break;
    out.push({ openTag: m[0], body: src.slice(open.lastIndex, c.index), start: m.index });
    open.lastIndex = c.index + c[0].length;
  }
  return out;
}

// benchmark-level metadata
const benchTitle = decode(inner(xml, 'title')) || docTitle;
const releaseInfo =
  (xml.match(/Release:\s*[^<\n]+/i) || [])[0] ||
  (inner(xml, 'plain-text') ? decode(inner(xml, 'plain-text')) : null) ||
  '(release string not found)';
const benchVersion = decode(inner(xml, 'version')) || '(version not found)';
const relNum = (String(releaseInfo).match(/Release:\s*(\d+)/i) || [])[1];
// Combined DISA-style label, e.g. "V6R4", when both version and release are present.
const verLabel = /^\d+$/.test(benchVersion) && relNum ? `V${benchVersion}R${relNum}` : benchVersion;

const rules = [];
for (const rule of blocks(xml, 'Rule')) {
  const b = rule.body;
  const stigId = decode(inner(b, 'version')) || attr(rule.openTag, 'id') || '(no id)';
  const title = decode(inner(b, 'title')) || '';
  const severity = attr(rule.openTag, 'severity') || 'unspecified';
  const descRaw = decode(inner(b, 'description') || '');
  const vulnDisc = (descRaw.match(/<VulnDiscussion>([\s\S]*?)<\/VulnDiscussion>/i) || [])[1] || descRaw;
  const checkBlock = inner(b, 'check');
  const checkContent = checkBlock ? decode(inner(checkBlock, 'check-content') || '') : '';
  const fixtext = decode(inner(b, 'fixtext') || '');
  rules.push({ stigId, title, severity, vulnDisc: vulnDisc.trim(), checkContent: checkContent.trim(), fixtext: fixtext.trim() });
}

const out = [];
out.push(`# ${docTitle}`);
out.push('');
out.push('> **STATUS: VENDORED** — verbatim rule text extracted from the official DISA XCCDF benchmark.');
out.push(`> **Benchmark title:** ${benchTitle}`);
out.push(`> **Version/Release:** ${verLabel} (${String(releaseInfo).trim()})`);
out.push(`> **Generation:** XCCDF XML → markdown via \`scripts/vendor/xccdf-stig-to-md.mjs\`. Retrieved ${RETRIEVED}.`);
out.push(`> Provenance/currency ledger: \`../../MANIFEST.md\`. ${rules.length} rules.`);
out.push('');
for (const r of rules) {
  out.push(`## ${r.stigId} — ${r.title}`);
  out.push('');
  out.push(`**Severity:** ${r.severity}`);
  out.push('');
  if (r.vulnDisc) { out.push(`**Discussion:** ${r.vulnDisc}`); out.push(''); }
  if (r.checkContent) { out.push('**Check:**'); out.push(''); out.push('```'); out.push(r.checkContent); out.push('```'); out.push(''); }
  if (r.fixtext) { out.push('**Fix:**'); out.push(''); out.push('```'); out.push(r.fixtext); out.push('```'); out.push(''); }
  out.push(`**Provenance:** ${provId} · ${r.stigId} · ${verLabel}`);
  out.push('');
}
writeFileSync(outPath, out.join('\n'));
console.log(`${outPath}: ${rules.length} rules  (benchmark: ${benchTitle})`);
