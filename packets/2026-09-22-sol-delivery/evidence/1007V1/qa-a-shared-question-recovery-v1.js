// Same frozen A/B candidate: repair only the A instrument selector and receipts.
// B24+4+4 states already terminal PASS; never rerun or overwrite that evidence.
const fs = await import("node:fs/promises");
const crypto = await import("node:crypto");
const path = await import("node:path");
const candidateRelative = ".artifacts/1007-ab-shared-question-preview-v2";
const raw = await fs.readFile(path.join(workflowRoot,
  "packets/2026-09-22-sol-delivery/evidence/1007V1/qa-ab-shared-question-preview-v2.js"));
if(crypto.createHash("sha256").update(raw).digest("hex") !==
   "f33d8fdbda1ba26d3ef565bcd86b1ca00d084dc03a7a3927d30620869b2d81d6")
  throw Error("Original failed A instrument changed");
const start=raw.toString().indexOf("const out = path.join(workflowRoot, candidateRelative");
if(start<0)throw Error("A-only recovery boundary missing");
let source=raw.toString().slice(start)
  .replace('candidateRelative, "a-qa"','candidateRelative, "a-qa-v2"')
  .replace('source.evidence=evidence;source.clicked=target;',
    'run.states[run.states.length-1].evidence=evidence;run.states[run.states.length-1].clicked=target;')
  .replace('source.focus=focus;', 'run.states[run.states.length-1].focus=focus;')
  .replace('await page.click("details[data-comparison-disclosure] > summary");\n'+
    '    await page.click("button[data-filter-dimension=product][data-filter-value=Nemolizumab]");',
    'await page.evaluate(()=>document.querySelector("details[data-comparison-disclosure] > summary")'+
    '.scrollIntoView({block:"center"}));'+
    'if(!await page.evaluate(()=>document.querySelector("details[data-comparison-disclosure]").open))'+
    'await page.click("details[data-comparison-disclosure] > summary");'+
    'await page.waitForFunction(()=>document.querySelector("[data-filter-dimension=product] '+
    'button[data-filter-value=Nemolizumab]").checkVisibility());'+
    'await page.click("[data-filter-dimension=product] button[data-filter-value=Nemolizumab]");');
await new(Object.getPrototypeOf(async function(){}).constructor)(
  "taskSpace","workflowRoot","candidateRelative","fs","path",source)(
    taskSpace,workflowRoot,candidateRelative,fs,path);
