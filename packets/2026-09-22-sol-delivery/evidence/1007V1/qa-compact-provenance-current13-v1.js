// Ego184 only; no saves, source writes or network manipulation. New candidate only.
const fs = await import("node:fs/promises");
const root = globalThis.CI_WORKFLOW_ROOT;
if (!root) throw new Error("Explicit CI_WORKFLOW_ROOT required");
const revision = Number(globalThis.CI_WORKFLOW_QA_REVISION || 13);
if (!Number.isSafeInteger(revision) || revision < 13) throw new Error("Explicit candidate revision required");
const output = root + `/.artifacts/1007-compact-provenance-current${revision}-desktop-v1`;
const verified = JSON.parse(await fs.readFile(root + `/.artifacts/1007-compact-provenance-current${revision}-v1/verified.json`, "utf8"));
if (verified.revision !== revision || verified.facts_unchanged !== 1144) throw new Error("Candidate verification required");
await fs.mkdir(output);
const page = (await taskSpace(184)).page("p2");
const run = {space:184,revision,generation:verified.generation,
  created_at:new Date().toISOString(),states:[],failures:[],visual_owner_review:"NOT_RUN",
  fresh_browser:false,scientific_release:"NOT_RUN",writes_or_saves:0,context_checks:[]};
const same = (a,b) => JSON.stringify([...new Set(a)].sort()) === JSON.stringify([...new Set(b)].sort());
async function capture(kind,width,state) {
  const observed = await page.evaluate(({kind,state}) => {
    const host = document.querySelector("#full-study-comparison"), table = host.querySelector("table");
    const workspace = window[kind === "A" ? "__A_COMPARISON_WORKSPACE__" : "__B_COMPARISON_WORKSPACE__"];
    const ids = JSON.parse(host.dataset.queryRowIds), permitted = new Set(ids);
    const columns = JSON.parse(host.dataset.columnIds);
    const question = document.querySelector(kind === "A" ? "[data-a-comparison-question]" : "[data-comparison-column]").value;
    const expected = cols => [...new Set(cols.flatMap(c=>Object.values(c.cells).flat()).filter(id=>permitted.has(id)))];
    const drawer = document.querySelector(kind === "A" ? "#data-basis-panel" : "#kz-evidence-drawer");
    const buttons = [...table.querySelectorAll("button")].filter(b=>b.dataset.evidenceRowId || b.dataset.rowId);
    const observations = [...table.querySelectorAll(".kz-comparison-observation")];
    return {kind,state,width:innerWidth,height:innerHeight,revision:document.body.dataset.currentRevision,
      document_width:document.documentElement.scrollWidth,query_count:ids.length,
      visible_ids:JSON.parse(host.dataset.displayedRowIds),expected_visible:expected(workspace.columns.filter(c=>columns.includes(c.id))),
      question_ids:JSON.parse(host.dataset.questionRowIds),expected_question:expected(workspace.columns.filter(c=>c.question_id===question)),
      fonts:buttons.map(b=>parseFloat(getComputedStyle(b).fontSize)),
      clipped:buttons.filter(b=>b.scrollWidth>b.clientWidth+1 || b.scrollHeight>b.clientHeight+1).length,
      table_top:table.getBoundingClientRect().top,table_rows:table.tBodies[0].rows.length,
      table_height:table.getBoundingClientRect().height,
      compact_observations:observations.filter(n=>n.classList.contains("kz-comparison-observation--compact")).length,
      identity_headers:table.querySelectorAll(".kz-comparison-identity-header").length,
      retained_labels:observations.every(n=>!!n.querySelector(".kz-comparison-fact__identity")?.textContent),
      closed_context_checks:observations.filter(n=>n.classList.contains("kz-comparison-observation--compact") && n.querySelector("details:not([open])")).map(n=>{
        const b=n.querySelector("button").getBoundingClientRect(),s=n.querySelector("summary").getBoundingClientRect();
        return {height:n.getBoundingClientRect().height,beside:s.top<b.bottom && b.top<s.bottom};
      }),
      source_count:document.querySelectorAll("#external-sources .portal-source-section__list > li").length,
      source_links:[...document.querySelectorAll("#external-sources a")].map(a=>a.href),
      source_open:!drawer.hidden,source:state === "source" ? drawer.textContent : null,
      generation:JSON.parse(document.querySelector("#ci-current-edit").textContent).generation};
  }, {kind,state});
  if (observed.revision !== String(revision) || observed.generation !== run.generation || observed.document_width>width)
    run.failures.push(`${kind}/${width}/${state}: version or page overflow`);
  if (!same(observed.visible_ids,observed.expected_visible) || !same(observed.question_ids,observed.expected_question))
    run.failures.push(`${kind}/${width}/${state}: typed query scope`);
  if (observed.fonts.some(n=>n<16) || observed.clipped || !observed.retained_labels)
    run.failures.push(`${kind}/${width}/${state}: font, clipped facts or missing labels`);
  if (revision >= 14 && observed.closed_context_checks.some(n=>!n.beside))
    run.failures.push(`${kind}/${width}/${state}: closed context adds another full row`);
  if (kind === "A" && (observed.source_count !== 20 || observed.source_links.length !== 20))
    run.failures.push(`${kind}/${width}/${state}: locked public sources`);
  if (state === "source" && (!observed.source_open || !observed.source.includes("-48.32") || !observed.source.includes("用户清除")))
    run.failures.push(`${kind}/${width}/source: original source or user clear disclosure`);
  observed.screenshot = `${kind}-${width}-${state}-r${revision}.png`;
  await page.screenshot({path:output+"/"+observed.screenshot});
  run.states.push(observed);
  await fs.writeFile(output+"/actual.json",JSON.stringify(run,null,2));
  console.log(JSON.stringify({kind,width,state,rows:observed.table_rows,facts:observed.visible_ids.length,compact:observed.compact_observations}));
}
try {
  await page.goto("http://127.0.0.1:65033/?fact=ctgov-atomic-fact_4ac6d0c427e87d71a7f35b51",{timeout:120000});
  await page.waitForSelector("#input-value",{state:"visible"});
  run.editor_entry = await page.evaluate(()=>{const envelope=JSON.parse(document.querySelector("#facts").textContent);return {revision:envelope.revision,facts:Object.keys(envelope.facts).length};});
  if (run.editor_entry.revision!==revision || run.editor_entry.facts!==1144) throw new Error("Actual current editor mismatch");
  async function resetFilters(kind) {
    const selector = kind === "A" ? "details[data-comparison-disclosure]" : ".kz-b-filter-bar details[data-comparison-disclosure]";
    if (!await page.evaluate(selector=>document.querySelector(selector).open,selector)) await page.click(selector+" > summary");
    await page.click("[data-filter-reset]");
    await page.click(selector+" > summary");
  }
  for (const kind of ["A","B"]) {
    const entry = kind === "A" ? "clinical-portfolio.html" : "overview.html";
    await page.goto(`http://127.0.0.1:65033/reports/${run.generation}/${kind}/${entry}?view=comparison&cmp=efficacy%3A%3Aq-iga-success-0-or-1-and-ge2-reduction`,{timeout:120000});
    await page.waitForSelector("#full-study-comparison tbody button",{state:"visible"});
    const selector = kind === "A" ? "[data-a-comparison-question]" : "[data-comparison-column]";
    for (const [width,height] of [[1440,900],[1600,900],[1920,1080],[2560,1440]]) {
    await page.cdp("Emulation.setDeviceMetricsOverride",{width,height,deviceScaleFactor:1,mobile:false});
    await resetFilters(kind);
    await page.selectOption(selector,"efficacy::q-iga-success-0-or-1-and-ge2-reduction");
    await page.evaluate(()=>window.scrollTo(0,0));
    await capture(kind,width,"sparse");
    await page.selectOption(selector,"efficacy::q-pruritus-nrs-ge4-improvement");
    await capture(kind,width,"dense");
    if (revision >= 14) {
      const context = ".kz-comparison-observation--compact summary >> nth=0";
      await page.focus(context); await page.keyboard.press("Enter");
      const check = await page.evaluate(()=>{
        const n=document.querySelector(".kz-comparison-observation--compact"),d=n.querySelector("details");
        return {open:d.open,width:d.getBoundingClientRect().width,available:n.getBoundingClientRect().width,
          paragraphs:d.querySelectorAll("p").length,font:parseFloat(getComputedStyle(d).fontSize)};
      });
      check.kind=kind; check.viewport=width;
      check.screenshot=`${kind}-${width}-dense-expanded-r${revision}.png`;
      await page.screenshot({path:output+"/"+check.screenshot});
      run.context_checks.push(check);
      if (!check.open || check.width<check.available-1 || !check.paragraphs || check.font<16)
        run.failures.push(`${kind}/${width}: expanded context width or keyboard`);
      await page.keyboard.press("Enter");
      await page.evaluate(()=>window.scrollTo(0,0));
    }
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
    await capture(kind,width,"filtered_sparse");
    await resetFilters(kind);
    await page.selectOption(selector,"efficacy::q-wi-nrs-percent-change");
    await page.waitForSelector("#full-study-comparison tbody button",{state:"visible"});
    const trigger = kind === "A" ? '[data-evidence-row-id="eff-030c369a7ea60f719d66"]' : '[data-row-id="eff-030c369a7ea60f719d66"]';
    await page.click("#full-study-comparison "+trigger);
    await page.waitForFunction(kind=>!document.querySelector(kind === "A" ? "#data-basis-panel" : "#kz-evidence-drawer").hidden,kind);
    await capture(kind,width,"source");
    await page.keyboard.press("Escape");
    run.states.at(-1).focus_restored = await page.evaluate(trigger=>document.activeElement.matches(trigger),trigger);
    if (!run.states.at(-1).focus_restored) run.failures.push(`${kind}/${width}: Escape focus`);
  }
  }
  run.execution = run.failures.length ? "COMPLETED_WITH_FAILURES_NOT_ACCEPTED" : `COMPLETED_32_ACTUAL_CURRENT${revision}_AB_STATES`;
} catch(error) {run.execution="FAILED_NOT_ACCEPTED";run.error=String(error);throw error;}
finally {run.finished_at=new Date().toISOString();await fs.writeFile(output+"/actual.json",JSON.stringify(run,null,2));}
console.log(JSON.stringify({execution:run.execution,states:run.states.length,failures:run.failures}));
