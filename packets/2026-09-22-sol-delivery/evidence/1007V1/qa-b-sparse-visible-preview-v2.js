// Correct the Owner's query-scope assumption, never the clinical source data.
// Prior QA/source evidence is retained; the actual filtered facts are78/111,
// not the unrelated unresolved16 found elsewhere in the overview payload.
const fs = await import("node:fs/promises");
const path = await import("node:path");
const crypto = await import("node:crypto");
const base = path.join(workflowRoot,
  "packets/2026-09-22-sol-delivery/evidence/1007V1/qa-b-sparse-visible-preview-v1.js");
const raw = await fs.readFile(base);
if (crypto.createHash("sha256").update(raw).digest("hex") !==
    "6ca9d259e12d920ba5a7ec58fc1cb261c2ffd24c0e8cbed32178693052aa1ddc")
  throw Error("Historical failed recipe changed");
const before = `    if (!observed.rows.some(row => row.value === 111 && row.unit === 'Participants') ||
        !observed.rows.some(row => row.value === 16 && row.renderable === false))
      run.failures.push(width + ': raw count or unresolved statistic changed');`;
const after = `    const expected = {
      'eff-b6d4e0cb2fff2c4d2ef6':78, 'eff-e4be0438910551629263':111
    };
    if (observed.rows.length !== 2 || observed.rows.some(row =>
        expected[row.id] !== row.value || row.unit !== 'Participants' || row.renderable !== true))
      run.failures.push(width + ': source-qualified current observations changed');
    const rawTitleVisible = await page.evaluate(() => Array.from(document.querySelectorAll(
      '.kz-b-study-original-title')).some(el => el.getClientRects().length));
    if (rawTitleVisible) run.failures.push(width + ': raw study title leaked onto reading plane');`;
if (!raw.toString().includes(before)) throw Error("Expected probe boundary not found");
const source = raw.toString().replaceAll('.artifacts/1007-b-sparse-visible-preview-v1',
  '.artifacts/1007-b-sparse-visible-preview-v2').replace(before, after);
await new (Object.getPrototypeOf(async function(){}).constructor)(
  "taskSpace", "workflowRoot", source)(taskSpace, workflowRoot);
