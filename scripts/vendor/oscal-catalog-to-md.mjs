// oscal-catalog-to-md.mjs — vendor NIST SP 800-53 Rev 5 from the OSCAL JSON catalog
// into per-family markdown, verbatim (statement + discussion), with provenance.
//
// Source of truth: NIST OSCAL control catalog (usnistgov/oscal-content),
//   NIST_SP-800-53_rev5_catalog.json.
// Renders only the SP 800-53 controlling text (statement + guidance/"Discussion").
// The 800-53A assessment procedures embedded in the same catalog
// (assessment-objective / assessment-method / assessment-objects) are intentionally
// EXCLUDED — this corpus carries controlling text a reviewer cites, not 800-53A.
//
// No text is authored here: every character of control prose comes from the catalog.
// The only strings this script introduces are the standard OSCAL placeholder renderings
// ("[Assignment: organization-defined ...]", "[Selection (one or more): ...]") and the
// structural labels the catalog itself supplies (a., 1., (a), etc.).
//
// Usage:  node scripts/vendor/oscal-catalog-to-md.mjs <catalog.json> <out-controls-dir> [retrievedDate]
// Offline, deterministic. Node 18+ (uses only built-ins).

import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';

const [, , catalogPath, outDir, retrievedArg] = process.argv;
if (!catalogPath || !outDir) {
  console.error('usage: node oscal-catalog-to-md.mjs <catalog.json> <out-controls-dir> [retrievedDate]');
  process.exit(1);
}
const RETRIEVED = retrievedArg || 'unspecified';

const catalog = JSON.parse(readFileSync(catalogPath, 'utf8')).catalog;
const DOC_VERSION = catalog.metadata.version;                 // e.g. "5.2.0"
const OSCAL_VERSION = catalog.metadata['oscal-version'];      // e.g. "1.2.2"
const LAST_MODIFIED = catalog.metadata['last-modified'];

// ---- global maps -----------------------------------------------------------
const paramById = new Map();   // param id -> param object
const labelById = new Map();   // control id -> display label (e.g. "AC-2(10)")

function displayLabel(ctrl) {
  // The label prop with no `class` is the human display label ("AC-1", "AC-2(10)").
  const props = ctrl.props || [];
  const plain = props.find((p) => p.name === 'label' && !p.class);
  return plain ? plain.value : (ctrl.id || '').toUpperCase();
}

function indexControl(ctrl) {
  labelById.set(ctrl.id, displayLabel(ctrl));
  for (const p of ctrl.params || []) paramById.set(p.id, p);
  for (const s of ctrl.controls || []) indexControl(s);
}
for (const g of catalog.groups) for (const c of g.controls) indexControl(c);

// ---- prose / parameter rendering -------------------------------------------
const INSERT_RE = /\{\{\s*insert:\s*param,\s*([A-Za-z0-9_.\-]+)\s*\}\}/g;

function renderParam(id) {
  const p = paramById.get(id);
  if (!p) throw new Error(`unresolved param insert: ${id}`); // fail loud — never fabricate
  if (p.select) {
    const how = p.select['how-many'] === 'one-or-more' ? ' (one or more)' : '';
    const choices = (p.select.choice || []).map((ch) => resolve(ch)).join('; ');
    return `[Selection${how}: ${choices}]`;
  }
  const lbl = p.label || '';
  return /^organization-defined/i.test(lbl)
    ? `[Assignment: ${lbl}]`
    : `[Assignment: organization-defined ${lbl}]`;
}

function resolve(text) {
  if (text == null) return '';
  return String(text).replace(INSERT_RE, (_, id) => renderParam(id));
}

// ---- control rendering ------------------------------------------------------
function renderItems(part, depth, out) {
  const indent = '    '.repeat(depth);
  const label = (part.props || []).find((p) => p.name === 'label');
  const lead = label ? `${label.value} ` : '';
  if (part.prose != null) out.push(`${indent}${lead}${resolve(part.prose)}`);
  for (const child of part.parts || []) renderItems(child, depth + 1, out);
}

function statusOf(ctrl) {
  return (ctrl.props || []).find((p) => p.name === 'status')?.value;
}

function fragToLabel(href) {
  // "#ac-2_smt.k" -> control id "ac-2" -> "AC-2"; "#pm-15" -> "PM-15"
  const frag = href.replace(/^#/, '');
  const cid = frag.split('_')[0];
  return labelById.get(cid) || cid.toUpperCase();
}

function renderControl(ctrl, out) {
  const label = displayLabel(ctrl);
  out.push(`## ${label} — ${ctrl.title}`);
  out.push('');

  if (statusOf(ctrl) === 'withdrawn') {
    const links = ctrl.links || [];
    const inc = links.filter((l) => l.rel === 'incorporated-into').map((l) => fragToLabel(l.href));
    const moved = links.filter((l) => l.rel === 'moved-to').map((l) => fragToLabel(l.href));
    let note = '**Withdrawn.**';
    if (inc.length) note += ` Incorporated into ${[...new Set(inc)].join(', ')}.`;
    if (moved.length) note += ` Moved to ${[...new Set(moved)].join(', ')}.`;
    out.push(note);
    out.push('');
    out.push(`**Provenance:** NIST SP 800-53r5 · ${label} · rev ${DOC_VERSION}`);
    out.push('');
    for (const s of ctrl.controls || []) renderControl(s, out);
    return;
  }

  const parts = ctrl.parts || [];
  const statement = parts.find((p) => p.name === 'statement');
  if (statement) {
    const lines = [];
    if (statement.prose != null) lines.push(resolve(statement.prose));
    for (const item of statement.parts || []) renderItems(item, 0, lines);
    // Preserve nested structure with a fenced-free indented block rendered as text.
    out.push(lines.join('\n'));
    out.push('');
  }

  const guidance = parts.find((p) => p.name === 'guidance');
  if (guidance && guidance.prose != null) {
    out.push(`**Discussion:** ${resolve(guidance.prose)}`);
    out.push('');
  }

  const related = (ctrl.links || [])
    .filter((l) => l.rel === 'related')
    .map((l) => fragToLabel(l.href));
  if (related.length) {
    out.push(`**Related controls:** ${[...new Set(related)].join(', ')}.`);
    out.push('');
  }

  out.push(`**Provenance:** NIST SP 800-53r5 · ${label} · rev ${DOC_VERSION}`);
  out.push('');

  for (const s of ctrl.controls || []) renderControl(s, out);
}

// ---- emit -------------------------------------------------------------------
mkdirSync(outDir, { recursive: true });
const indexRows = []; // [displayLabel, family, id]
let familyCount = 0, controlCount = 0;

for (const g of catalog.groups) {
  const fam = g.id.toUpperCase();
  const out = [];
  out.push(`# NIST SP 800-53 Rev 5 — ${fam} (${g.title})`);
  out.push('');
  out.push(`> **STATUS: VENDORED** — verbatim control text generated from the NIST OSCAL catalog (JSON).`);
  out.push(`> Source & provenance: \`../_source.md\`. Master currency ledger: \`../../../MANIFEST.md\`.`);
  out.push(`> Doc version ${DOC_VERSION} · OSCAL ${OSCAL_VERSION} · catalog last-modified ${LAST_MODIFIED} · retrieved ${RETRIEVED}.`);
  out.push(`> Statement + Discussion for every control/enhancement in the family; 800-53A assessment`);
  out.push(`> procedures are intentionally excluded. Placeholder brackets ([Assignment: …]/[Selection: …])`);
  out.push(`> are the standard OSCAL renderings of organization-defined parameters.`);
  out.push('');

  for (const ctrl of g.controls) {
    renderControl(ctrl, out);
    // index every control + enhancement
    (function idx(c) {
      indexRows.push([displayLabel(c), fam, c.id]);
      controlCount++;
      for (const s of c.controls || []) idx(s);
    })(ctrl);
  }

  writeFileSync(join(outDir, `${fam}.md`), out.join('\n').replace(/\n{3,}/g, '\n\n').trimEnd() + '\n');
  familyCount++;
}

// ---- catalog index ----------------------------------------------------------
indexRows.sort((a, b) => a[0].localeCompare(b[0], undefined, { numeric: true }));
const idx = [];
idx.push('# NIST SP 800-53r5 — Catalog Index');
idx.push('');
idx.push('> **STATUS: VENDORED** — control-ID → family-file lookup, generated with the family files.');
idx.push(`> Doc version ${DOC_VERSION} · OSCAL ${OSCAL_VERSION} · retrieved ${RETRIEVED}. Provenance: \`_source.md\`.`);
idx.push('> Cite by anchor, e.g. `controls/AC.md` → the `## AC-12 — …` section (AC-12 → controls/AC.md).');
idx.push('');
idx.push(`Families: ${catalog.groups.map((g) => g.id.toUpperCase()).join(' ')} (${familyCount}).`);
idx.push(`Controls + enhancements indexed: ${indexRows.length}.`);
idx.push('');
idx.push('| Control | Family file |');
idx.push('|---|---|');
for (const [label, fam] of indexRows) idx.push(`| ${label} | \`controls/${fam}.md\` |`);
idx.push('');
writeFileSync(join(outDir, '..', 'catalog-index.md'), idx.join('\n'));

console.log(`families: ${familyCount}`);
console.log(`controls+enhancements: ${controlCount}`);
console.log(`doc version: ${DOC_VERSION}  oscal: ${OSCAL_VERSION}  last-modified: ${LAST_MODIFIED}`);
