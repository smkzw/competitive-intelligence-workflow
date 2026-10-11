// Reuse native download/import actions, not previous candidate results.
const fs = await import('node:fs/promises');
const crypto = await import('node:crypto');
const root = globalThis.CI_WORKFLOW_ROOT;
if (!root) throw Error('Explicit English root required');
const previous = root + '/packets/2026-09-22-sol-delivery/evidence/1007V1/qa-current30-config-v1.js';
const bytes = await fs.readFile(previous);
const expected = globalThis.CI_WORKFLOW_CONFIG_RECIPE_SHA256;
if (!expected || crypto.createHash('sha256').update(bytes).digest('hex') !== expected)
  throw Error('Previous native instrument hash must be explicitly pinned');
let source = bytes.toString();
source = source.replaceAll('1007-comparison-reading-current30-v1', '1007-abc-reading-current33-v1')
  .replaceAll('1007-current30-config-v1', '1007-current33-config-v1')
  .replaceAll('!==30', '!==33').replaceAll('revision:30', 'revision:33')
  .replaceAll('Verified current30 required', 'Verified current33 required');
await new (Object.getPrototypeOf(async function() {}).constructor)('taskSpace', source)(taskSpace);
