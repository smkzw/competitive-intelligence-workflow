// V3 explicit controls retained; scroll all real ancestors before a pointer action.
// No force-click, dispatchEvent, mutation of facts or visibility overrides.
const fs = await import('node:fs/promises'), crypto = await import('node:crypto');
const root = globalThis.CI_WORKFLOW_ROOT;
if (!root) throw Error('Explicit English root required');
const bytes = await fs.readFile(root +
  '/packets/2026-09-22-sol-delivery/evidence/1007V1/qa-current33-offline-v3.js');
if (crypto.createHash('sha256').update(bytes).digest('hex') !==
    'e7e37e6119448fc1167bb8ecc6fec7fc53fa1648125c3a5e597f896aa98ddceb')
  throw Error('Frozen V3 instrument changed');
const action = '  await page.click(trigger);';
if (!bytes.toString().includes(action)) throw Error('Explicit source action marker missing');
const source = bytes.toString().replace('offline-actual-v3.json', 'offline-actual-v4.json')
  .replace(action, `
  await page.evaluate(s => document.querySelector(s).scrollIntoView({block:'center',inline:'nearest'}), trigger);
  await page.evaluate(() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))));
  await page.click(trigger);
`);
await new (Object.getPrototypeOf(async function() {}).constructor)('taskSpace', source)(taskSpace);
