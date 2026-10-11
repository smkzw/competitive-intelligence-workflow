// Resume the same frozen candidate after a hidden-detail-table instrument error.
const fs = await import('node:fs/promises');
const crypto = await import('node:crypto');
const root = globalThis.CI_WORKFLOW_ROOT;
if (!root) throw Error('Explicit English root required');
const bytes = await fs.readFile(root +
  '/packets/2026-09-22-sol-delivery/evidence/1007V1/qa-current33-offline-v1.js');
if (crypto.createHash('sha256').update(bytes).digest('hex') !==
    '3a34738f3acc229bc5701e7e28922e822702c7954e82741e7dddc1c22b814d45')
  throw Error('V1 instrument changed');
const marker = 'await new (Object.getPrototypeOf(async function() {}).constructor)';
const insert = `
source = source.replace('offline-actual-v1.json', 'offline-actual-v2.json')
  .replace('"#full-study-comparison table"', '"#full-study-comparison [data-primary-comparison-table]"')
  .replace('async function persist(){', \`
const priorBytes = await fs.readFile(out + '/offline-actual-v1.json');
const prior = JSON.parse(priorBytes);
if (prior.revision !== 33 || prior.state !== 'FAILED_NOT_ACCEPTED' ||
    prior.failures.length || prior.pages.length !== 1 ||
    prior.pages[0].tag !== 'A' || prior.pages[0].kind !== 'A' ||
    prior.export_proof_sha256 !== run.export_proof_sha256 || !prior.network_restored)
  throw Error('Only exact same-candidate completed A entry may resume');
run.pages = prior.pages;
run.recovery = {prior_sha256:crypto.createHash('sha256').update(priorBytes).digest('hex'),
  completed_same_candidate_entries:1, newly_executed_entries:0};
async function persist(){\`)
  .replace('const selected=manifest.reports[kind];', \`
if (run.pages.some(p => p.tag === tag && p.kind === kind)) continue;
const selected=manifest.reports[kind];\`)
  .replace('run.pages.push({tag,kind,actual,traffic,reading,original,edited,screenshot});await persist();',
    'run.pages.push({tag,kind,actual,traffic,reading,original,edited,screenshot});run.recovery.newly_executed_entries++;await persist();');
`;
const source = bytes.toString().replace(marker, insert + marker);
if (source === bytes.toString()) throw Error('V1 integration marker missing');
await new (Object.getPrototypeOf(async function() {}).constructor)('taskSpace', source)(taskSpace);
