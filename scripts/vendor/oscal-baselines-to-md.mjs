// oscal-baselines-to-md.mjs — vendor the NIST SP 800-53B Moderate (IL4) and High (IL6)
// baselines from the OSCAL profiles, plus the IL4→IL6 delta (High − Moderate).
//
// Membership only: the profiles are authoritative for WHICH controls are in each
// baseline; the control text itself lives in the 800-53r5 family files. Control IDs and
// titles are read from the OSCAL catalog + profiles — nothing is authored here.
//
// Usage: node scripts/vendor/oscal-baselines-to-md.mjs \
//          <catalog.json> <moderate-profile.json> <high-profile.json> <out-53b-dir> <crosswalk-dir> [retrievedDate]

import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';

const [, , catalogPath, modPath, highPath, outB, outX, retrievedArg] = process.argv;
if (!catalogPath || !modPath || !highPath || !outB || !outX) {
  console.error('usage: node oscal-baselines-to-md.mjs <catalog> <moderate> <high> <out-53b-dir> <crosswalk-dir> [retrieved]');
  process.exit(1);
}
const RETRIEVED = retrievedArg || 'unspecified';

const catalog = JSON.parse(readFileSync(catalogPath, 'utf8')).catalog;

// id -> {label, title, family}
const meta = new Map();
for (const g of catalog.groups) {
  const fam = g.id.toUpperCase();
  const walk = (cc) => {
    const label = (cc.props || []).find((p) => p.name === 'label' && !p.class)?.value || cc.id.toUpperCase();
    meta.set(cc.id, { label, title: cc.title, family: fam, famTitle: g.title });
    for (const s of cc.controls || []) walk(s);
  };
  for (const c of g.controls) walk(c);
}

function idsOf(profilePath) {
  const p = JSON.parse(readFileSync(profilePath, 'utf8')).profile;
  const ids = [];
  for (const imp of p.imports || []) for (const ic of imp['include-controls'] || []) ids.push(...(ic['with-ids'] || []));
  return { ids, version: p.metadata.version, title: p.metadata.title };
}

const mod = idsOf(modPath);
const high = idsOf(highPath);

// stable family order from the catalog
const FAM_ORDER = catalog.groups.map((g) => g.id.toUpperCase());
function byFamily(ids) {
  const m = new Map();
  for (const id of ids) {
    const info = meta.get(id);
    if (!info) throw new Error(`baseline id not in catalog: ${id}`);
    if (!m.has(info.family)) m.set(info.family, []);
    m.get(info.family).push(info);
  }
  return m;
}

function render(title, statusNote, ids, version) {
  const grouped = byFamily(ids);
  const out = [];
  out.push(`# ${title}`);
  out.push('');
  out.push('> **STATUS: VENDORED** — control-ID membership generated from the NIST OSCAL 800-53B profile.');
  out.push('> Membership only; control text is in `../sp-800-53r5/controls/<FAMILY>.md`.');
  out.push(`> ${statusNote}`);
  out.push(`> Doc version ${version} · retrieved ${RETRIEVED}. Provenance/currency: \`../../MANIFEST.md\`.`);
  out.push('');
  out.push(`Total controls + enhancements in baseline: **${ids.length}**.`);
  out.push('');
  for (const fam of FAM_ORDER) {
    if (!grouped.has(fam)) continue;
    const rows = grouped.get(fam);
    out.push(`## ${fam} — ${rows[0].famTitle}`);
    out.push('');
    for (const r of rows) out.push(`- ${r.label} — ${r.title}`);
    out.push('');
  }
  return out.join('\n').replace(/\n{3,}/g, '\n\n').trimEnd() + '\n';
}

mkdirSync(outB, { recursive: true });
mkdirSync(outX, { recursive: true });

writeFileSync(
  join(outB, 'baseline-moderate-il4.md'),
  render(
    'NIST SP 800-53B — Moderate Baseline (IL4)',
    'IL4 (CUI) maps to the 800-53 Rev 5 **Moderate** control baseline (per DoD CC SRG); the SRG adds overlay controls beyond this set — see `../../disa/srg/cloud-computing-srg.md`.',
    mod.ids,
    mod.version
  )
);

writeFileSync(
  join(outB, 'baseline-high-il6.md'),
  render(
    'NIST SP 800-53B — High Baseline (IL6)',
    'IL6 (SECRET) maps to the 800-53 Rev 5 **High** control baseline (per DoD CC SRG); the SRG adds overlay controls beyond this set — see `../../disa/srg/cloud-computing-srg.md`.',
    high.ids,
    high.version
  )
);

// delta: High − Moderate (controls added when moving IL4 -> IL6)
const modSet = new Set(mod.ids);
const added = high.ids.filter((id) => !modSet.has(id));
const highSet = new Set(high.ids);
const removed = mod.ids.filter((id) => !highSet.has(id)); // expected empty (High ⊇ Moderate)

const dx = [];
dx.push('# IL4 → IL6 Baseline Delta (800-53B High − Moderate)');
dx.push('');
dx.push('> **STATUS: VENDORED** — derived set difference of the OSCAL Moderate and High profiles.');
dx.push(`> Basis: 800-53B High − Moderate membership. Doc version ${high.version} · retrieved ${RETRIEVED}.`);
dx.push('> This is the 800-53 control-baseline delta only. The DoD CC SRG IL4→IL6 overlay');
dx.push('> (mission-owner / CSP responsibilities, jurisdiction, connectivity) is layered separately');
dx.push('> once `../disa/srg/cloud-computing-srg.md` is vendored — see that file for SRG-level deltas.');
dx.push('> Provenance/currency: `../MANIFEST.md`.');
dx.push('');
dx.push(`Moderate (IL4): **${mod.ids.length}** · High (IL6): **${high.ids.length}** · Added at IL6: **${added.length}** · Removed: **${removed.length}**.`);
dx.push('');
dx.push('## Controls added when moving IL4 → IL6');
dx.push('');
const addedByFam = byFamily(added);
for (const fam of FAM_ORDER) {
  if (!addedByFam.has(fam)) continue;
  const rows = addedByFam.get(fam);
  dx.push(`### ${fam} — ${rows[0].famTitle}`);
  dx.push('');
  for (const r of rows) dx.push(`- ${r.label} — ${r.title}`);
  dx.push('');
}
if (removed.length) {
  dx.push('## Controls in Moderate but not High (should be empty; investigate if not)');
  dx.push('');
  for (const id of removed) dx.push(`- ${meta.get(id).label} — ${meta.get(id).title}`);
  dx.push('');
}
writeFileSync(join(outX, 'il4-vs-il6-delta.md'), dx.join('\n').replace(/\n{3,}/g, '\n\n').trimEnd() + '\n');

console.log(`moderate: ${mod.ids.length}  high: ${high.ids.length}  added@IL6: ${added.length}  removed: ${removed.length}`);
console.log(`profile versions — moderate: ${mod.version}  high: ${high.version}`);
