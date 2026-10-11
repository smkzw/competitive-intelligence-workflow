// Preserve v1's actual instrument failure: it opened the default age question,
// then incorrectly expected pruritus records. Select the intended question
// through the actual native UI; no production edits or candidate re-render.
const fs = await import("node:fs/promises");
const root = globalThis.CI_WORKFLOW_ROOT;
const original = await fs.readFile(root +
  "/packets/2026-09-22-sol-delivery/evidence/1007V1/qa-b-reading-hierarchy-preview-v1.js", "utf8");
const anchor = 'await ready(true); const matched = await inspect("comparison");';
if (!original.includes(anchor)) throw Error("Frozen QA interface changed");
const followup = original.replaceAll('out + "/qa', 'out + "/qa-v2')
  .replaceAll('out + `/qa/', 'out + `/qa-v2/')
  .replace(anchor, 'await ready(true); await page.selectOption("[data-comparison-column]", ' +
    '"efficacy::q-pruritus-nrs-ge4-improvement"); await ready(true); ' +
    'const matched = await inspect("comparison");');
await import("data:text/javascript;base64," + Buffer.from(followup).toString("base64"));
