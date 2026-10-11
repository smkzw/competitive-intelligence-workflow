// Existing Ego2/p1. New normal A candidate, no save/edit/share or old-suite replay.
const fs=await import("node:fs/promises"),path=await import("node:path");
const crypto=await import("node:crypto");
const raw=await fs.readFile(path.join(workflowRoot,
 "packets/2026-09-22-sol-delivery/evidence/1007V1/qa-a-shared-question-current-v1.js"));
if(crypto.createHash("sha256").update(raw).digest("hex")!==
 "d2aae27911cf63c368ba896d87ff7abc54221cc799e4b4ff4c402f2c1457f1ac")
 throw Error("Original A task instrument changed");
const actual=JSON.parse(await fs.readFile(path.join(workflowRoot,
 ".artifacts/1007-a-unmatched-reading-v1/actual.json"),"utf8"));
if(actual.reports.A.pages!==49||actual.current_writes!==0)
 throw Error("Normal readonly render must be terminal before browser QA");
let source=raw.toString().replaceAll(".artifacts/1007-ab-shared-question-preview-v3",
 ".artifacts/1007-a-unmatched-reading-v1")
 .replace('candidateRelative, "a-qa-v2"','candidateRelative, "a-qa"')
 .replace("window.__QA_A_SOURCE_TRIGGER__=document.elementFromPoint(x,y);",
 "const original=window.__A_COMPARISON_EVIDENCE__;"+
 "window.__A_COMPARISON_EVIDENCE__=function(id,trigger){"+
 "window.__QA_A_SOURCE_TRIGGER__=trigger;return original(id,trigger);};");
const marker='    const target=await page.evaluate(()=>{';
if(!source.includes(marker))throw Error("Frozen A insertion point changed");
source=source.replace(marker,`
    async function readingState(){return await page.evaluate(()=>{
      const h=document.querySelector('#full-study-comparison');
      const trs=[...h.querySelectorAll('tbody tr')];
      return {matched:JSON.parse(h.dataset.matchedStudyIds),
        unmatched:JSON.parse(h.dataset.unmatchedStudyIds),
        all:trs.map(t=>t.dataset.studyId),
        visible:trs.filter(t=>getComputedStyle(t).display!=='none').map(t=>t.dataset.studyId),
        count:Number(h.querySelector('[data-comparison-unmatched-count]').textContent),
        checked:h.querySelector('[data-comparison-unmatched-toggle]').checked,
        focus:document.activeElement.hasAttribute('data-comparison-unmatched-toggle')};
    });}
    const before=await readingState();dense.nativeReading=before;
    if(before.matched.length!==3||before.unmatched.length!==43||before.count!==43||
      before.all.length!==46||before.visible.join('|')!==before.matched.join('|'))
      run.failures.push(width+':default empty research wall or removed membership');
    await page.evaluate(()=>document.querySelector('[data-comparison-unmatched-toggle]')
      .scrollIntoView({block:'center'}));
    await page.focus('[data-comparison-unmatched-toggle]');
    await page.keyboard.press('Space');
    const expanded=await record('expanded');expanded.nativeReading=await readingState();
    if(!expanded.nativeReading.checked||!expanded.nativeReading.focus||
      expanded.nativeReading.visible.length!==46||
      expanded.displayedIds.join('|')!==dense.displayedIds.join('|'))
      run.failures.push(width+':native expand changed query or lost research');
    await page.keyboard.press('Space');
    const collapsed=await readingState();expanded.collapse=collapsed;
    if(collapsed.checked||!collapsed.focus||collapsed.visible.join('|')!==before.visible.join('|'))
      run.failures.push(width+':native collapse failed');
`+marker);
const filterMarker='    if(filtered.displayedIds.length!==4||filtered.groups.length!==1)';
source=source.replace(filterMarker,`
    filtered.nativeReading=await readingState();
    if(filtered.nativeReading.checked||filtered.nativeReading.visible.join('|')!==
      filtered.nativeReading.matched.join('|'))
      run.failures.push(width+':filtered empty research shown or matched study missing');
`+filterMarker);
await new(Object.getPrototypeOf(async function(){}).constructor)(
 "taskSpace","workflowRoot",source)(taskSpace,workflowRoot);
