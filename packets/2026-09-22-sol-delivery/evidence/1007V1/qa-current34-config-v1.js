// All three current HTTP contexts; A/C immutable report33 retained, B is report34.
const fs = await import('node:fs/promises'), crypto = await import('node:crypto');
const root = globalThis.CI_WORKFLOW_ROOT, port = Number(globalThis.CI_WORKFLOW_EDITOR_PORT);
if (!root || !Number.isSafeInteger(port)) throw Error('Explicit root/owned port required');
const bytes = await fs.readFile(root +
  '/packets/2026-09-22-sol-delivery/evidence/1007V1/qa-current30-config-v1.js');
if (crypto.createHash('sha256').update(bytes).digest('hex') !==
    'ef3b4d0d9b2529f3f61572f005ffdf260b87fc57ca460abaecbc529c868915fa')
  throw Error('Frozen native instrument changed');
const page = (await taskSpace(2)).page('p1');
await page.goto(`http://127.0.0.1:${port}/`, {timeout:120000});
await page.waitForSelector('#search', {state:'visible',timeout:120000});
const source = bytes.toString()
  .replaceAll('1007-comparison-reading-current30-v1', '1007-b-opener-current34-v1')
  .replaceAll('1007-current30-config-v1', '1007-current34-config-v1')
  .replaceAll('!==30', '!==34').replaceAll('revision:30', 'revision:34')
  .replaceAll('Verified current30 required', 'Verified current34 required');
await new (Object.getPrototypeOf(async function() {}).constructor)('taskSpace', source)(taskSpace);
