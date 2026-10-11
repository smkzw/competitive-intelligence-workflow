// Preserve v1 instrument failure; verify the actual SVG opener, not a hidden button.
const fs=await import('node:fs/promises'),path=await import('node:path');
const crypto=await import('node:crypto');
const raw=await fs.readFile(path.join(workflowRoot,
 'packets/2026-09-22-sol-delivery/evidence/1007V1/qa-ab-task-geometry-v1.js'));
if(crypto.createHash('sha256').update(raw).digest('hex')!==
 'c04e007e285d6751f6ab14f7ad73a9997ab1a671335c68520af136c05b59b450')
 throw Error('Frozen v1 instrument evidence changed');
let source=raw.toString().replaceAll('.artifacts/1007-ab-task-geometry-v1',
 '.artifacts/1007-abc-task-geometry-v2')
 .replace("join('')!=='AB'","join('')!=='ABC'")
 .replace('run.states.push({label,...measured});','measured.label=label;run.states.push(measured);')
 .replace("const el=document.querySelector('#kz-chart-0');el.scrollIntoView({block:'center'});",
  "const original=window.__EVIDENCE_DRAWER__.openByRowId;"+
  "window.__QA_B_OPEN_COUNT__=0;window.__EVIDENCE_DRAWER__.openByRowId=function(id,trigger){"+
  "window.__QA_B_TRIGGER__=trigger;window.__QA_B_OPEN_ID__=id;window.__QA_B_OPEN_COUNT__++;"+
  "return original.apply(this,arguments);};"+
  "const el=document.querySelector('#kz-chart-0');el.scrollIntoView({block:'center'});")
 .replace("id:document.activeElement.getAttribute('data-chart-evidence-open')",
  "id:window.__QA_B_OPEN_ID__,count:window.__QA_B_OPEN_COUNT__,"+
  "sameTrigger:document.activeElement===window.__QA_B_TRIGGER__,"+
  "triggerConnected:!!window.__QA_B_TRIGGER__&&window.__QA_B_TRIGGER__.isConnected,"+
  "triggerVisible:!!window.__QA_B_TRIGGER__&&window.__QA_B_TRIGGER__.checkVisibility(),"+
  "tag:document.activeElement.tagName")
 .replace("!source.focus.closed||source.focus.id!==target.id",
  "!source.focus.closed||source.focus.id!==target.id||source.focus.count!==1||"+
  "(source.focus.triggerConnected&&source.focus.triggerVisible&&!source.focus.sameTrigger)");
await new(Object.getPrototypeOf(async function(){}).constructor)(
 'taskSpace','workflowRoot',source)(taskSpace,workflowRoot);
