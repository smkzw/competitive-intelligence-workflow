// One affected reading slice; use the already authorized Ego space.
const root = "/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow";
const out = root + "/.artifacts/1007-b-expert-reading-preview-v1";
const fs = await import("node:fs/promises");
await fs.mkdir(out + "/qa");
const page = (await taskSpace(2)).page("p1");
await page.cdp("Emulation.setDeviceMetricsOverride", {
  width: 1920, height: 1080, deviceScaleFactor: 1, mobile: false,
});
const url = "file://" + out + "/B/overview.html";
const states = [];
for (const mode of ["home", "comparison"]) {
  await page.goto(url + (mode === "comparison" ? "?view=comparison&cmp=" +
    encodeURIComponent("efficacy::q-pruritus-nrs-ge4-improvement") : ""));
  await page.waitForFunction(() => document.fonts.status === "loaded" &&
    !!window.__CHART_SYNC__, undefined, {timeout: 120000});
  states.push(await page.evaluate(() => {
    const body = document.body.innerText;
    const forbidden = ["阅读边界", "证据限制", "条件与限制", "不等于",
      "不代表临床", "不构成", "数值共轴资格另判"];
    const host = document.querySelector("#full-study-comparison");
    return {mode: document.body.dataset.comparisonView, width: innerWidth,
      unwantedVisibleCopy: forbidden.filter(text => body.includes(text)),
      questionFacts: host.dataset.questionRowIds || "[]",
      shownFacts: host.dataset.displayedRowIds || "[]"};
  }));
  await page.screenshot({path: out + "/qa/B-" + mode + "-1920.png"});
}
await fs.writeFile(out + "/qa/actual.json", JSON.stringify({states,
  scope: "1920 home/comparison visible copy only; graph reconstruction is next"}, null, 2));
if (states.some(state => state.unwantedVisibleCopy.length)) throw Error("Defensive copy remains");
console.log(JSON.stringify(states));
