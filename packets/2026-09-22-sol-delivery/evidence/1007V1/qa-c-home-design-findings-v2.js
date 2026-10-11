// Same frozen candidate; v1 asked for a non-existent REPORT_C global.
// Production C publishes filter rows and evidence views, not the Python payload.
const fs=await import('node:fs/promises'),path=await import('node:path');
const crypto=await import('node:crypto');
const raw=await fs.readFile(path.join(workflowRoot,
 'packets/2026-09-22-sol-delivery/evidence/1007V1/qa-c-home-design-findings-v1.js'));
if(crypto.createHash('sha256').update(raw).digest('hex')!==
 '4f3b8d1732ad1218395f66ca99ca7f9494d20281d8c7d918eacf20d199d96a6a')
 throw Error('Frozen original instrument changed');
const source=raw.toString()
 .replace("path.join(root,'c-qa')","path.join(root,'c-qa-v2')")
 .replace('window.REPORT_C.observations','window.__FILTER_ROWS__')
 .replace('observations.map(r=>r.row_id)','observations.map(r=>r.id)')
 .replace('window.__EVIDENCE_DRAWER__&&window.REPORT_C',
  'window.__EVIDENCE_DRAWER__&&Array.isArray(window.__FILTER_ROWS__)');
await new(Object.getPrototypeOf(async function(){}).constructor)(
 'taskSpace','workflowRoot',source)(taskSpace,workflowRoot);
