// Reuse a frozen instrument, but execute every entry of the new committed generation.
// Explicit production controls and genuine ancestor scrolling; no prior PASS reuse.
const fs = await import('node:fs/promises'), crypto = await import('node:crypto');
const root = globalThis.CI_WORKFLOW_ROOT;
if (!root) throw Error('Explicit English root required');
const bytes = await fs.readFile(root +
  '/packets/2026-09-22-sol-delivery/evidence/1007V1/qa-current33-offline-v3.js');
const digest = data => crypto.createHash('sha256').update(data).digest('hex');
if (digest(bytes) !== 'e7e37e6119448fc1167bb8ecc6fec7fc53fa1648125c3a5e597f896aa98ddceb')
  throw Error('Frozen explicit-control instrument changed');
let source = bytes.toString();
function replaceOne(old, updated) {
  if (source.split(old).length !== 2) throw Error('Instrument marker not unique: ' + old);
  source = source.replace(old, updated);
}
const start = source.indexOf("const priorBytes = await fs.readFile(out + '/offline-actual-v1.json');");
const end = source.indexOf('const receipt = out +');
if (start < 0 || end <= start) throw Error('Prior-candidate recovery block missing');
source = source.slice(0, start) + source.slice(end);
replaceOne('pages:prior.pages', 'pages:[]');
replaceOne('recovery:{prior_sha256:digest(priorBytes),completed_same_candidate_entries:1,newly_executed_entries:0}',
  'recovery:{completed_same_candidate_entries:0,newly_executed_entries:0}');
replaceOne("actual.revision !== '33'", 'actual.revision !== String(selected.report_revision)');
replaceOne('  await page.click(trigger);', `
  await page.evaluate(s => document.querySelector(s).scrollIntoView({block:'center',inline:'nearest'}), trigger);
  await page.evaluate(() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))));
  await page.click(trigger);
`);
replaceOne("const receipt = out + '/offline-actual-v3.json';",
  "const receipt = out + '/offline-actual-v1.json';");
source = source.replaceAll('current33', 'current34').replaceAll('CURRENT33', 'CURRENT34')
  .replaceAll('revision:33', 'revision:34').replaceAll('!== 33', '!== 34')
  .replaceAll('-r33.png', '-r34.png');
if (source.includes('prior.') || source.includes('priorBytes') || source.includes("!== '33'"))
  throw Error('Old-candidate reuse or hard-coded report revision retained');
await new (Object.getPrototypeOf(async function() {}).constructor)('taskSpace', source)(taskSpace);
