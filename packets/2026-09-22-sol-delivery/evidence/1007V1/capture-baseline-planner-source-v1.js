// Read only normal preview presentation input in existing184/p2, not source/current mutation.
const fs = await import("node:fs/promises");
const page = (await taskSpace(184)).page("p2");
const root = globalThis.CI_WORKFLOW_ROOT;
if (!root) throw new Error("Explicit English project required");
if (!(await page.url()).includes("1007-baseline-landscape-preview-v3/B/baseline-demographics.html"))
  throw new Error("Wrong bound normal preview page");
const groups = await page.evaluate(() => window.__CHART_GROUPS__);
if (groups.length !== 4 || groups.reduce((n,g)=>n+g.rows.length,0)!==48)
  throw new Error("Actual demographics query changed");
await fs.writeFile(root+"/.artifacts/1007-baseline-planner-source-v1.json",JSON.stringify(groups,null,2),{flag:"wx"});
console.log(groups.map(g=>({title:g.title_zh,rows:g.rows.length,first:{
  trial:g.rows[0].trial_zh,identity:g.rows[0]._chart_identity_label,
  key:g.rows[0]._chart_identity_key,series:g.rows[0]._chart_series_key,
  context:g.rows[0]._chart_comparison_context_key}})));
