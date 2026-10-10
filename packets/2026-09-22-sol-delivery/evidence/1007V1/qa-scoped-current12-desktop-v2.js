// Real Ego184 UI only. Exclusive evidence; no source edits, save or network manipulation.
const fs = await import("node:fs/promises");
const root = "/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow";
const output = root + "/.artifacts/1007-scoped-current12-desktop-v2-source-filter-recovery-v1";
const verified = JSON.parse(await fs.readFile(root + "/.artifacts/1007-scoped-ab-current-refresh-v2/verified.json", "utf8"));
if (verified.current_revision !== 12) throw new Error("Current12 verification required");
await fs.mkdir(output); // Existing attempt is never overwritten or blindly rerun.
const page = (await taskSpace(184)).page("p2");
const run = {space:184,revision:12,generation:verified.generation_sha256,
  created_at:new Date().toISOString(),states:[],failures:[],visual_owner_review:"NOT_RUN",
  fresh_browser:false,scientific_release:"NOT_RUN",writes_or_saves:0,
  prior_attempt:".artifacts/1007-scoped-current12-desktop-v2/actual.json",
  recovery:"Original zero-state auth failure and three actual A1440 states retained. Clear belongs to source-proven dupilumab, not selected nemolizumab; source check resets through normal navigation, not altered facts/assertions."};
const same = (a,b) => JSON.stringify([...new Set(a)].sort()) === JSON.stringify([...new Set(b)].sort());
async function capture(kind,width,state) {
  const observed = await page.evaluate(({kind,state}) => {
    const host = document.querySelector("#full-study-comparison");
    const table = host.querySelector("table");
    const workspace = window[kind === "A" ? "__A_COMPARISON_WORKSPACE__" : "__B_COMPARISON_WORKSPACE__"];
    const ids = JSON.parse(host.dataset.queryRowIds), permitted = new Set(ids);
    const columns = JSON.parse(host.dataset.columnIds);
    const question = document.querySelector(kind === "A" ? "[data-a-comparison-question]" : "[data-comparison-column]").value;
    const expected = cols => [...new Set(cols.flatMap(c=>Object.values(c.cells).flat()).filter(id=>permitted.has(id)))];
    const drawer = document.querySelector(kind === "A" ? "#data-basis-panel" : "#kz-evidence-drawer");
    const buttons = [...table.querySelectorAll("button")].filter(b=>b.dataset.evidenceRowId || b.dataset.rowId);
    return {kind,state,width:innerWidth,height:innerHeight,revision:document.body.dataset.currentRevision,
      document_width:document.documentElement.scrollWidth,query_count:ids.length,
      visible_ids:JSON.parse(host.dataset.displayedRowIds),expected_visible:expected(workspace.columns.filter(c=>columns.includes(c.id))),
      question_ids:JSON.parse(host.dataset.questionRowIds),expected_question:expected(workspace.columns.filter(c=>c.question_id===question)),
      fonts:buttons.map(b=>parseFloat(getComputedStyle(b).fontSize)),
      clipped:buttons.filter(b=>b.scrollWidth>b.clientWidth+1 || b.scrollHeight>b.clientHeight+1).length,
      table_top:table.getBoundingClientRect().top,table_rows:table.tBodies[0].rows.length,
      source_open:!drawer.hidden,source:state === "source" ? drawer.textContent : null,
      generation:JSON.parse(document.querySelector("#ci-current-edit").textContent).generation};
  }, {kind,state});
  if (observed.revision !== "12" || observed.generation !== run.generation || observed.document_width>width)
    run.failures.push(`${kind}/${width}/${state}: version or page overflow`);
  if (!same(observed.visible_ids,observed.expected_visible) || !same(observed.question_ids,observed.expected_question))
    run.failures.push(`${kind}/${width}/${state}: typed query scope`);
  if (observed.fonts.some(n=>n<16) || observed.clipped)
    run.failures.push(`${kind}/${width}/${state}: font or clipped facts`);
  if (state === "source" && (!observed.source_open || !observed.source.includes("-48.32") || !observed.source.includes("用户清除")))
    run.failures.push(`${kind}/${width}/source: original source or user clear disclosure`);
  observed.screenshot = `${kind}-${width}-${state}-r12.png`;
  await page.screenshot({path:output+"/"+observed.screenshot});
  run.states.push(observed);
  await fs.writeFile(output+"/actual.json",JSON.stringify(run,null,2));
  console.log(JSON.stringify({kind,width,state,rows:observed.table_rows,facts:observed.visible_ids.length}));
}
try {
  await page.goto("http://127.0.0.1:65033/?fact=ctgov-atomic-fact_4ac6d0c427e87d71a7f35b51",{timeout:120000});
  await page.waitForSelector("#input-value",{state:"visible"});
  run.editor_entry = await page.evaluate(()=>{const envelope=JSON.parse(document.querySelector("#facts").textContent);return {revision:envelope.revision,facts:Object.keys(envelope.facts).length};});
  if (run.editor_entry.revision!==12 || run.editor_entry.facts!==1144) throw new Error("Actual current editor mismatch");
  const prior=JSON.parse(await fs.readFile(root+"/.artifacts/1007-scoped-current12-desktop-v2-initial-session-v1/actual.json","utf8"));
  if(prior.generation!==run.generation || prior.states.length!==3 || prior.failures.length) throw new Error("Prior same-candidate scope mismatch");
  run.completed_prior_states=prior.states;
  for (const kind of ["A","B"]) for (const [width,height] of [[1440,900],[1600,900],[1920,1080],[2560,1440]]) {
    await page.cdp("Emulation.setDeviceMetricsOverride",{width,height,deviceScaleFactor:1,mobile:false});
    const entry = kind === "A" ? "clinical-portfolio.html" : "overview.html";
    await page.goto(`http://127.0.0.1:65033/reports/${run.generation}/${kind}/${entry}?view=comparison&cmp=efficacy%3A%3Aq-iga-success-0-or-1-and-ge2-reduction`,{timeout:120000});
    await page.waitForSelector("#full-study-comparison tbody button",{state:"visible"});
    await page.evaluate(()=>window.scrollTo(0,0));
    const resumeSource=kind==="A" && width===1440;
    if(!resumeSource) await capture(kind,width,"sparse");
    const selector = kind === "A" ? "[data-a-comparison-question]" : "[data-comparison-column]";
    await page.selectOption(selector,"efficacy::q-pruritus-nrs-ge4-improvement");
    if(!resumeSource) await capture(kind,width,"dense");
    if (kind === "A") {
      await page.click("details[data-comparison-disclosure] > summary");
      await page.click('[data-filter-dimension="product"] > summary');
      await page.click('[data-filter-dimension="product"] [data-filter-value="Nemolizumab"]');
      await page.click('[data-filter-dimension="product"] > summary');
      await page.click("details[data-comparison-disclosure] > summary");
    } else {
      await page.click(".kz-b-filter-bar details[data-comparison-disclosure] > summary");
      await page.click('.kz-b-filter-quick [data-filter-value="nemolizumab"]');
      await page.click(".kz-b-filter-bar details[data-comparison-disclosure] > summary");
    }
    if(!resumeSource) await capture(kind,width,"filtered_sparse");
    await page.goto(`http://127.0.0.1:65033/reports/${run.generation}/${kind}/${entry}?view=comparison&cmp=efficacy%3A%3Aq-wi-nrs-percent-change`,{timeout:120000});
    await page.waitForSelector("#full-study-comparison tbody button",{state:"visible"});
    const trigger = kind === "A" ? '[data-evidence-row-id="eff-030c369a7ea60f719d66"]' : '[data-row-id="eff-030c369a7ea60f719d66"]';
    await page.click("#full-study-comparison "+trigger);
    await page.waitForFunction(kind=>!document.querySelector(kind === "A" ? "#data-basis-panel" : "#kz-evidence-drawer").hidden,kind);
    await capture(kind,width,"source");
    await page.keyboard.press("Escape");
    run.states.at(-1).focus_restored = await page.evaluate(trigger=>document.activeElement.matches(trigger),trigger);
    if (!run.states.at(-1).focus_restored) run.failures.push(`${kind}/${width}: Escape focus`);
  }
  run.execution = "COMPLETED_29_NEW_PLUS_3_SAME_CANDIDATE_ACTUAL_CURRENT12_AB_STATES";
} catch(error) {run.execution="FAILED_NOT_ACCEPTED";run.error=String(error);throw error;}
finally {run.finished_at=new Date().toISOString();await fs.writeFile(output+"/actual.json",JSON.stringify(run,null,2));}
console.log(JSON.stringify({execution:run.execution,states:run.states.length,failures:run.failures}));
