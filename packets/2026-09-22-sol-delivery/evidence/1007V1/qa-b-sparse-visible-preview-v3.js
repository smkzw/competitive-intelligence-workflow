// Same frozen v2 candidate, corrected visibility probe and new evidence folder.
// A closed details descendant can have a layout rect but checkVisibility=false.
// Actual prior PNG + native DOM inspection proved this; no product workaround.
const fs = await import("node:fs/promises");
const path = await import("node:path");
const crypto = await import("node:crypto");
const base = path.join(workflowRoot,
  "packets/2026-09-22-sol-delivery/evidence/1007V1/qa-b-sparse-visible-preview-v2.js");
const raw = await fs.readFile(base);
if (crypto.createHash("sha256").update(raw).digest("hex") !==
    "1275d118cc5047795814d2670eba5bfe35df88d53e68e87ccdf8ba3fcd48e25b")
  throw Error("Original visibility failure changed");
const suffix = `.replace(before, after)
  .replaceAll('el.getClientRects().length', 'el.checkVisibility()')
  .replaceAll('"qa"', '"qa-v2"')
  .replaceAll('qa/B-sparse-', 'qa-v2/B-sparse-')
  .replaceAll('qa/actual.json', 'qa-v2/actual.json');`;
if (!raw.toString().includes('.replace(before, after);')) throw Error('Probe boundary changed');
const source = raw.toString().replace('.replace(before, after);', suffix);
await new (Object.getPrototypeOf(async function(){}).constructor)(
  "taskSpace", "workflowRoot", source)(taskSpace, workflowRoot);
