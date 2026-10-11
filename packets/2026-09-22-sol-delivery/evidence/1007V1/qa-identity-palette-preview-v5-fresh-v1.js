// Actual Ego Lite Profile2/space2. Reuse frozen normal preview; never save/re-render.
const fs = await import("node:fs/promises"), crypto = await import("node:crypto");
const root = globalThis.CI_WORKFLOW_ROOT;
if (!root) throw new Error("Explicit English root required");
const candidate = root + "/.artifacts/1007-identity-palette-preview-v5";
const out = root + "/.artifacts/1007-identity-palette-preview-v5-fresh-qa-v1";
const bytes = await fs.readFile(candidate + "/actual.json");
const digest = crypto.createHash("sha256").update(bytes).digest("hex");
if (digest !== "08e6c0f6753ae632b8453fae5cdb88d86d5bf9b9fdc206b382b4624e2cf1e72c")
  throw new Error("Pinned preview changed");
const manifest = JSON.parse(bytes);
await fs.mkdir(out);
const task = await taskSpace(2), page = task.page("p1"), results = [];
const settle = async () => {
  await page.waitForFunction(() => document.readyState === "complete" && document.fonts.status === "loaded");
  await page.evaluate(() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))));
};
const open = async (report, relative) => {
  const html = await fs.readFile(`${candidate}/${report}/${relative}`);
  if (crypto.createHash("sha256").update(html).digest("hex") !== manifest.reports[report].render_hashes[relative])
    throw new Error("Normal-entry rendered bytes changed");
  await page.goto(`file://${candidate}/${report}/${relative}`);
  await settle();
};
const inspect = async () => await page.evaluate(() => ({
  viewport:innerWidth, documentWidth:document.documentElement.scrollWidth,
  visibleIds:(window.__B_VISIBLE_ROW_IDS__ || []).slice().sort(),
  charts:[...new Set([...document.querySelectorAll("[data-grid-span] .kz-chart-table tbody tr")]
    .filter(e=>e.style.display!=="none" && e.closest("[data-grid-span]").getBoundingClientRect().width>0).map(e=>e.dataset.rowId))].sort(),
  groups:(window.__CHART_GROUPS__ || []).map(g => window.__PRESENTATION_PLAN__(g)),
  cards:[...document.querySelectorAll("[data-grid-span]")].filter(e=>e.getBoundingClientRect().width>0).map(e => ({
    span:Number(e.dataset.gridSpan),count:Number(e.dataset.observationCount),
    width:e.getBoundingClientRect().width,height:e.getBoundingClientRect().height,
    title:e.querySelector("h3")?.innerText,
    legend:[...e.querySelectorAll(".kz-chart-legend__item")].map(i=>i.innerText),
    legendColors:[...e.querySelectorAll(".kz-chart-legend__swatch")].map(i=>getComputedStyle(i).backgroundColor),
    series:(window.echarts.getInstanceByDom(e.querySelector("[id^=kz-chart-]"))?.getOption().series || []).map(s=>({name:s.name,color:s.itemStyle.color,points:s.data.filter(p=>p._row_id && p.value!==null).map(p=>({id:p._row_id,value:p.value,color:p.itemStyle.color}))})),
  })),
}));
const activate = async (selector) => {
  await page.focus(selector);
  await page.keyboard.press("Enter");
};
const cardShot = async (name) => {
  const y = await page.evaluate(() => [...document.querySelectorAll("[data-grid-span]")].find(e=>e.getBoundingClientRect().width>0).getBoundingClientRect().top - 135);
  await page.mouse.move(600,500);
  await page.mouse.wheel(0,y,{label:"inspect actual comparison cards"});
  await settle();
  await page.screenshot({path:`${out}/${name}.png`});
};
for (const width of [1440,1600,1920,2560]) {
  await page.cdp("Emulation.setDeviceMetricsOverride",{width,height:1000,deviceScaleFactor:1,mobile:false});
  await open("A","overview.html");
  const a = await page.evaluate(()=>({width:innerWidth,documentWidth:document.documentElement.scrollWidth,
    products:new Set([...document.querySelectorAll(".kz-a-landscape-product")].map(e=>e.dataset.productId)).size}));
  await page.screenshot({path:`${out}/A-firstfold-${width}.png`});
  await open("B","baseline-demographics.html");
  const target = await page.evaluate(() => window.__FILTER_ROWS__.filter(r =>
    r.trial==="nct04501666" && r.element==="年龄、Continuous｜标准差" &&
    r.group==="来源组：Nemolizumab（登记原文，未译）").map(r=>r.id));
  if (target.length!==1 || target[0]!=="ctgov-baseline-fact_e84b3f00d17482917b19ed41")
    throw new Error("Explicit source-derived sparse case identity changed");
  const dense = await inspect();
  await page.screenshot({path:`${out}/B-firstfold-${width}.png`});
  await cardShot(`B-dense-card-${width}`);
  await activate("#kz-filter-panel > summary");
  await activate('button[data-filter-dimension="trial"][data-filter-value="nct04501666"]');
  await settle();
  const studyFiltered = await inspect();
  await activate('button[data-filter-dimension="element"][data-filter-value="年龄、Continuous｜标准差"]');
  await activate('button[data-filter-dimension="group"][data-filter-value="来源组：Nemolizumab（登记原文，未译）"]');
  await settle();
  const sparse = await inspect();
  await activate("#kz-filter-panel > summary");
  await cardShot(`B-filtered-single-card-${width}`);
  const hit = 'button[data-chart-evidence-open]';
  await page.focus(hit);
  await page.keyboard.press("Enter");
  await page.waitForFunction(()=>window.__EVIDENCE_DRAWER__.isOpen());
  const evidence = await page.evaluate(()=>({
    rowId:window.__EVIDENCE_DRAWER__.getOpenRowId(),
    text:document.querySelector("#kz-evidence-view").innerText,
    links:[...document.querySelectorAll("#kz-evidence-view a")].map(e=>e.href),
  }));
  await page.screenshot({path:`${out}/B-single-source-${width}.png`});
  await page.keyboard.press("Escape");
  const returned = await page.evaluate(()=>!window.__EVIDENCE_DRAWER__.isOpen() &&
    document.activeElement===document.querySelector('button[data-chart-evidence-open]'));
  const failures = [];
  const denseColors=Object.fromEntries(dense.cards.flatMap(c=>c.series.flatMap(s=>s.points.map(p=>[p.id,p.color]))));
  for(const card of studyFiltered.cards)for(const series of card.series)for(const point of series.points)
    if(denseColors[point.id]!==point.color) failures.push("Source identity color changed after filtering");
  if(dense.cards.some(c=>new Set(c.legendColors).size<2)) failures.push("Source identities have indistinguishable legends");
  if (a.products!==38 || a.documentWidth>width+1) failures.push("A viewport/product reachability");
  if (dense.documentWidth>width+1 || dense.charts.length!==48 || dense.cards.some(c=>c.span!==6))
    failures.push("B dense viewport/count/half-width geometry");
  if (dense.cards[0].legend.length!==5 || !dense.cards[0].legend.some(l=>l.includes("Nemolizumab")) ||
      !dense.cards[0].legend.some(l=>l.includes("Dupilumab"))) failures.push("Actual source-group legend");
  if (sparse.charts.length!==1 || sparse.cards.length!==1 || sparse.cards[0].span>6)
    failures.push("Filtered single observation failed compact geometry");
  if (evidence.rowId!==sparse.charts[0] || !evidence.text.includes("原来源原文") || !returned)
    failures.push("Exact source and real-trigger Esc focus");
  results.push({width,a,dense,studyFiltered,sparse,evidence,returned,failures});
  await fs.writeFile(out+"/progress.json",JSON.stringify({state:"PARTIAL_NOT_FINAL",results},null,2));
}
const proof={state:results.some(r=>r.failures.length)?"SCOPED_BEHAVIOR_FAILED":"SCOPED_BEHAVIOR_PASSED_VISUAL_REVIEW_PENDING",
  candidateManifestSha256:digest,profileId:"Profile 2",spaceId:2,
  profileCreation:"Native Ego Lite new-profile UI, no data import or sign-in; user expressly authorized",
  previousAttempt:"Frozen v4 QA v3 retained harness failures caused by counting hidden cards/rows; actual pixels exposed all-orange identity legends. This NEW normal-rendered v5 uses current visible-card/row predicates, original results untouched.",
  source_generation:manifest.source_generation,results,sourceWrites:0,saves:0,currentChanges:0,
  limits:"Pinned preview only; four dense and filter-to-single states/source focus, not full science, all-pages visual, new current, sharing or three hosts."};
await fs.writeFile(out+"/actual.json",JSON.stringify(proof,null,2));
console.log(JSON.stringify({state:proof.state,widths:results.length,failures:results.flatMap(r=>r.failures)}));
