"""R24-72 A 类安全性数值视图迁移到共享 ECharts 的生产家族回归。

只做真实函数级检查：Node 中加载打包 charts.js 与 report-a.js 源文件，
用最小 DOM/echarts 桩驱动真实 renderSafety/sync 生命周期，核对精确行 ID、
零值字形、facet 边界、翻页懒挂载与销毁；不做浏览器/视觉验收。
"""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "src/ci_workflow/renderers/portal/assets"
REPORT_A_JS = ASSETS / "report-a.js"
CHARTS_JS = ASSETS / "charts.js"
REPORT_A_CSS = ASSETS / "report-a.css"

_PROBE = r'''
"use strict";
const fs = require("node:fs");
const vm = require("node:vm");
const assert = require("node:assert/strict");

const reportPath = process.argv[2];
const chartsPath = process.argv[3];

function ok(condition, message) {
  assert.ok(condition, "SAFETY-ECHARTS: " + message);
}

/* ---------- 精确数值口径的合成安全行（形状与 report_a.py 展示行一致） ---------- */
const WINDOW_16 = "16周治疗期";
const PROPORTION_KEY = "any_teae|affirmed|unspecified|teae|unspecified||participants";
function projectRow(spec) {
  const p = Object.assign({
    kind: "participant_count",
    plot_unit: spec.unit || "人",
    plot_value: spec.value,
    numerator: spec.numerator === undefined ? null : spec.numerator,
    denominator: spec.denominator === undefined ? null : spec.denominator,
    estimand: spec.estimand || "安全性登记测量",
    window: spec.window || spec.time_window || WINDOW_16,
  }, spec.projection || {});
  const projection = {
    kind: p.kind,
    raw_value: spec.value,
    raw_unit: spec.unit || "人",
    plot_value: p.plot_value,
    plot_unit: p.plot_unit,
    numerator: p.numerator,
    denominator: p.denominator,
    direction: p.direction || "",
    window: p.window,
    estimand: p.estimand,
    renderable: spec.renderable !== false,
    unrenderable_reason:
      spec.renderable === false ? "group_product_relationship_unresolved" : null,
    size_value: null,
    size_basis: null,
    facet_key: [p.kind, p.plot_unit, p.direction || "", p.window, p.estimand].join("|"),
  };
  return {
    row_id: spec.row_id,
    product_id: spec.product_id || "p1",
    trial_id: spec.trial_id || "nct-1",
    category: spec.category || "治疗期间不良事件",
    term_key: spec.term_key || "any_teae",
    term: spec.term || "任何TEAE",
    term_label: spec.term_label || spec.term || "任何TEAE",
    measure_label: spec.measure_label === undefined
      ? (spec.term || "任何TEAE") : spec.measure_label,
    measure_context: spec.measure_context || "",
    arm: spec.arm || "治疗组",
    arm_detail: spec.arm_detail || spec.arm || "治疗组",
    time_window: spec.time_window || WINDOW_16,
    population: spec.population === undefined ? null : spec.population,
    unit: spec.unit || "人",
    value: spec.value,
    numerator: spec.numerator === undefined ? null : spec.numerator,
    denominator: spec.denominator === undefined ? null : spec.denominator,
    group_assignment_state: spec.group_assignment_state || "declared",
    semantic_filter_key: spec.semantic_filter_key || PROPORTION_KEY,
    measure_object: spec.measure_object || "participant_count",
    disclosure_state: "已公开",
    numeric_projection: projection,
  };
}
function round10(value) {
  return Math.round(value * 1e10) / 1e10;
}

const rows = [
  /* f1：同一口径的参与者比例 %，两条组别观察共享一个坐标面 */
  projectRow({
    row_id: "f1-treatment", value: round10(24 / 62 * 100), numerator: 24, denominator: 62,
    unit: "%", measure_object: "participant_proportion",
    projection: { kind: "participant_proportion", plot_value: 24 / 62 * 100, plot_unit: "%" },
  }),
  projectRow({
    row_id: "f1-control", value: round10(18 / 62 * 100), numerator: 18, denominator: 62,
    unit: "%", measure_object: "participant_proportion", arm: "对照组", arm_detail: "安慰剂",
    projection: { kind: "participant_proportion", plot_value: 18 / 62 * 100, plot_unit: "%" },
  }),
  /* f2：人数计数口径，含真实零值与不可绘制的未归属行 */
  projectRow({
    row_id: "f2-treatment", value: 2, numerator: 2, denominator: 62,
    term_key: "any_sae", term: "任何SAE", measure_label: "任何SAE", category: "严重不良事件",
    semantic_filter_key: "any_sae|affirmed|serious|teae_unknown|unspecified||participants",
  }),
  projectRow({
    row_id: "f2-zero", value: 0, numerator: 0, denominator: 62, arm: "队列 2", arm_detail: "队列 2",
    term_key: "any_sae", term: "任何SAE", measure_label: "任何SAE", category: "严重不良事件",
    semantic_filter_key: "any_sae|affirmed|serious|teae_unknown|unspecified||participants",
  }),
  projectRow({
    row_id: "nr-1", value: 9, numerator: 9, denominator: 62, arm: "队列 3", arm_detail: "队列 3",
    term_key: "any_sae", term: "任何SAE", measure_label: "任何SAE", category: "严重不良事件",
    semantic_filter_key: "any_sae|affirmed|serious|teae_unknown|unspecified||participants",
    group_assignment_state: "unknown", renderable: false,
  }),
  /* f3：与 f1 同试验同组别、但事件定义不同，必须是独立 facet 的单条观察 */
  projectRow({
    row_id: "f3-nasopharyngitis", value: round10(2 / 140 * 100), numerator: 2, denominator: 140,
    unit: "%", measure_object: "participant_proportion", term_key: "specific_ae",
    term: "鼻咽炎", measure_label: "鼻咽炎", category: "常见不良事件",
    semantic_filter_key: "specific_ae|affirmed|unspecified|teae|unspecified||participants",
    projection: { kind: "participant_proportion", plot_value: 2 / 140 * 100, plot_unit: "%" },
  }),
  /* f4：模型估计值（% 单位但不是概率刻度），两条组别观察 */
  projectRow({
    row_id: "f4-estimate-treatment", value: 0.2, unit: "%", measure_object: "adjusted_estimate",
    term_key: "aesi", term: "模型估计AESI发生率", measure_label: "模型估计AESI发生率",
    category: "特别关注不良事件", estimand: "模型估计应答率",
    semantic_filter_key: "aesi|affirmed|unspecified|teae_unknown|unspecified||participants",
    projection: {
      kind: "adjusted_estimate", plot_value: 0.2, plot_unit: "%",
      estimand: "模型估计应答率",
    },
  }),
  projectRow({
    row_id: "f4-estimate-control", value: 0.4, unit: "%", measure_object: "adjusted_estimate",
    term_key: "aesi", term: "模型估计AESI发生率", measure_label: "模型估计AESI发生率",
    category: "特别关注不良事件", estimand: "模型估计应答率", arm: "对照组", arm_detail: "安慰剂",
    semantic_filter_key: "aesi|affirmed|unspecified|teae_unknown|unspecified||participants",
    projection: {
      kind: "adjusted_estimate", plot_value: 0.4, plot_unit: "%",
      estimand: "模型估计应答率",
    },
  }),
  /* f6：同一事件定义、同一试验组别、同一观察窗，统计基础/单位不同 => 不得合并 */
  projectRow({
    row_id: "f6-count", value: 3, numerator: 3, denominator: 124, term_key: "aesi",
    term: "特别关注不良事件", measure_label: "特别关注不良事件", category: "特别关注不良事件",
    time_window: "12周治疗期", window: "12周治疗期",
    semantic_filter_key: "aesi|affirmed|unspecified|teae_unknown|unspecified||participants",
  }),
  projectRow({
    row_id: "f6-percent", value: round10(3 / 124 * 100), numerator: 3, denominator: 124,
    unit: "%", measure_object: "participant_proportion", term_key: "aesi",
    term: "特别关注不良事件", measure_label: "特别关注不良事件", category: "特别关注不良事件",
    time_window: "12周治疗期", window: "12周治疗期",
    semantic_filter_key: "aesi|affirmed|unspecified|teae_unknown|unspecified||participants",
    projection: { kind: "participant_proportion", plot_value: 3 / 124 * 100, plot_unit: "%" },
  }),
  /* f7：同一事件与单位，分析人群不同 => 不得合并 */
  projectRow({
    row_id: "f7-itt", value: 4, numerator: 4, denominator: 124, population: "ITT",
    term_key: "aesi", term: "特别关注不良事件", measure_label: "特别关注不良事件",
    category: "特别关注不良事件",
    semantic_filter_key: "aesi|affirmed|unspecified|teae_unknown|unspecified||participants",
  }),
  projectRow({
    row_id: "f7-safety-set", value: 5, numerator: 5, denominator: 124, population: "安全性分析集",
    term_key: "aesi", term: "特别关注不良事件", measure_label: "特别关注不良事件",
    category: "特别关注不良事件",
    semantic_filter_key: "aesi|affirmed|unspecified|teae_unknown|unspecified||participants",
  }),
  /* f8：同一事件与单位，观察窗不同 => 不得合并 */
  projectRow({
    row_id: "f8-week16", value: 6, numerator: 6, denominator: 124, time_window: WINDOW_16,
    term_key: "aesi", term: "特别关注不良事件", measure_label: "特别关注不良事件",
    category: "特别关注不良事件",
    semantic_filter_key: "aesi|affirmed|unspecified|teae_unknown|unspecified||participants",
  }),
  projectRow({
    row_id: "f8-week24", value: 7, numerator: 7, denominator: 124, time_window: "24周治疗期",
    window: "24周治疗期", term_key: "aesi", term: "特别关注不良事件",
    measure_label: "特别关注不良事件", category: "特别关注不良事件",
    semantic_filter_key: "aesi|affirmed|unspecified|teae_unknown|unspecified||participants",
  }),
  /* f9：另一产品，同事件 => 产品边界独立 */
  projectRow({
    row_id: "f9-other-product", product_id: "p2", trial_id: "nct-2", value: 9,
    numerator: 9, denominator: 90,
  }),
];
/* f5：同一 facet 的 56 条组别观察，用于翻页懒挂载；含真实零值 */
for (let index = 1; index <= 56; index += 1) {
  const suffix = String(index).padStart(2, "0");
  rows.push(projectRow({
    row_id: "f5-" + suffix, value: index - 1, numerator: index - 1, denominator: 100,
    arm: "队列 " + suffix, arm_detail: "队列 " + suffix, term_key: "severity_specific_teae",
    term: "任何轻度TEAE", measure_label: "任何轻度TEAE", category: "治疗期间不良事件",
    semantic_filter_key:
      "severity_specific_teae|affirmed|unspecified|teae|unspecified||participants",
  }));
}

const payload = {
  schema_version: "1.0",
  report_version: "v-probe",
  data_cutoff: "2026-09-06T23:59:59.999999+08:00",
  products: [
    { id: "p1", name: "泰瑞奇单抗", target: "示例靶点", modality: "单抗", phase: "III期" },
    { id: "p2", name: "安澜双抗", target: "示例靶点", modality: "双抗", phase: "II期" },
  ],
  trials: [
    { id: "nct-1", name: "示例试验一", display_id: "NCT-R24-001", phase: "III期", role: "核心" },
    { id: "nct-2", name: "示例试验二", display_id: "NCT-R24-002", phase: "II期", role: "核心" },
  ],
  safety: rows,
};

/* ---------- 最小 DOM 桩 ---------- */
function matchCompound(node, selector) {
  const tokenRe = /(^[a-zA-Z][\w-]*)|(\.[\w-]+)|(\[[^\]]+\])|(:not\(\[hidden\]\))/g;
  let consumed = "";
  let match;
  while ((match = tokenRe.exec(selector)) !== null) {
    consumed += match[0];
    const token = match[0];
    if (token === ":not([hidden])") {
      if (node.hidden) return false;
    } else if (token.startsWith(".")) {
      const own = String(node.className || "").split(/\s+/);
      if (!token.slice(1).split(".").every((name) => own.includes(name))) return false;
    } else if (token.startsWith("[")) {
      const body = token.slice(1, -1);
      const eq = body.indexOf("=");
      if (eq === -1) {
        if (node.getAttribute(body) === null) return false;
      } else {
        const name = body.slice(0, eq);
        let value = body.slice(eq + 1);
        if ((value.startsWith("'") && value.endsWith("'"))
            || (value.startsWith('"') && value.endsWith('"'))) {
          value = value.slice(1, -1);
        }
        const actual = node.getAttribute(name);
        if (actual === null || actual !== value) return false;
      }
    } else if (String(node.tagName).toLowerCase() !== token.toLowerCase()) {
      return false;
    }
  }
  return consumed === selector;
}
function matchParts(node, parts) {
  if (!matchCompound(node, parts[parts.length - 1])) return false;
  let cursor = node.parent;
  for (let index = parts.length - 2; index >= 0; index -= 1) {
    let ancestor = cursor;
    let matched = null;
    while (ancestor) {
      if (matchCompound(ancestor, parts[index])) { matched = ancestor; break; }
      ancestor = ancestor.parent;
    }
    if (!matched) return false;
    cursor = matched.parent;
  }
  return true;
}
function walk(node, visit) {
  for (const child of node.children) {
    visit(child);
    walk(child, visit);
  }
}
function queryAll(root, selector) {
  const found = [];
  for (const group of String(selector).split(",").map((part) => part.trim()).filter(Boolean)) {
    const parts = group.split(/\s+/).filter(Boolean);
    walk(root, (node) => {
      if (matchParts(node, parts) && !found.includes(node)) found.push(node);
    });
  }
  return found;
}
function makeElement(tag) {
  const element = {
    tagName: String(tag).toUpperCase(),
    children: [],
    parent: null,
    attributes: Object.create(null),
    style: { setProperty() {} },
    dataset: {},
    className: "",
    hidden: false,
    disabled: false,
    listeners: {},
    focused: false,
    clicked: false,
    ownText: "",
    appendChild(child) { child.parent = this; this.children.push(child); return child; },
    removeChild(child) {
      const index = this.children.indexOf(child);
      if (index >= 0) { this.children.splice(index, 1); child.parent = null; }
      return child;
    },
    insertBefore(child, reference) {
      child.parent = this;
      const index = reference ? this.children.indexOf(reference) : -1;
      if (index >= 0) this.children.splice(index, 0, child);
      else this.children.push(child);
      return child;
    },
    get firstChild() { return this.children.length ? this.children[0] : null; },
    setAttribute(name, value) { this.attributes[name] = String(value); },
    getAttribute(name) { return name in this.attributes ? this.attributes[name] : null; },
    hasAttribute(name) { return name in this.attributes; },
    removeAttribute(name) { delete this.attributes[name]; },
    addEventListener(type, handler) {
      (this.listeners[type] = this.listeners[type] || []).push(handler);
    },
    focus() { this.focused = true; },
    click() { this.clicked = true; },
    closest(selector) {
      let node = this;
      while (node) {
        if (matchCompound(node, selector)) return node;
        node = node.parent;
      }
      return null;
    },
    querySelectorAll(selector) { return queryAll(this, selector); },
    querySelector(selector) {
      const list = queryAll(this, selector);
      return list.length ? list[0] : null;
    },
    getClientRects() { return [{}]; },
    get textContent() {
      return this.ownText + this.children.map((child) => child.textContent).join("");
    },
    set textContent(value) {
      this.ownText = String(value == null ? "" : value);
      this.children = [];
    },
    get innerHTML() { return this.ownText; },
    set innerHTML(value) { if (value === "") { this.children = []; this.ownText = ""; } },
  };
  return element;
}

const documentStub = {
  readyState: "loading",
  listeners: {},
  createElement: makeElement,
  getElementById() { return null; },
  addEventListener(type, handler) {
    (this.listeners[type] = this.listeners[type] || []).push(handler);
  },
  querySelectorAll(selector) { return queryAll(this.body, selector); },
  querySelector(selector) {
    const list = queryAll(this.body, selector);
    return list.length ? list[0] : null;
  },
};
documentStub.body = makeElement("body");
const host = makeElement("div");
host.setAttribute("data-a-chart", "safety");
host.setAttribute("data-chart-id", "safety-full");
documentStub.body.appendChild(host);

const instances = [];
const resizeObservers = [];
const windowListeners = {};
function ResizeObserverStub(callback) {
  this.callback = callback;
  this.observed = [];
  resizeObservers.push(this);
}
ResizeObserverStub.prototype.observe = function observe(target) { this.observed.push(target); };
ResizeObserverStub.prototype.disconnect = function disconnect() { this.disconnected = true; };

const windowStub = {
  REPORT_A: payload,
  echarts: {
    init(target) {
      const instance = {
        el: target,
        handlers: {},
        option: null,
        disposed: false,
        on(type, handler) { this.handlers[type] = handler; },
        setOption(option) { this.option = option; },
        resize() { this.resized = (this.resized || 0) + 1; },
        isDisposed() { return this.disposed; },
        dispose() { this.disposed = true; },
      };
      instances.push(instance);
      return instance;
    },
  },
  ResizeObserver: ResizeObserverStub,
  innerWidth: 1440,
  location: { pathname: "/safety.html", search: "", href: "file:///safety.html",
    protocol: "file:", origin: "null" },
  history: { replaceState() {}, pushState() {} },
  localStorage: { getItem() { return null; }, setItem() {}, removeItem() {} },
  addEventListener(type, handler) {
    (windowListeners[type] = windowListeners[type] || []).push(handler);
  },
  setTimeout() { return 0; },
  clearTimeout() {},
};
const sandbox = {
  window: windowStub,
  document: documentStub,
  URLSearchParams,
  CSS: { escape: (value) => String(value) },
  ResizeObserver: ResizeObserverStub,
  Element: function Element() {},
  console,
};
vm.runInNewContext(fs.readFileSync(chartsPath, "utf8"), sandbox, { filename: chartsPath });
vm.runInNewContext(fs.readFileSync(reportPath, "utf8"), sandbox, { filename: reportPath });

/* ---------- 断言：真实函数产出的 DOM 与图形数据 ---------- */
const renderableIds = rows
  .filter((row) => row.numeric_projection && row.numeric_projection.renderable)
  .map((row) => row.row_id);
ok(renderableIds.length === 70, "probe fixture must keep 70 renderable facts");

const cells = host.querySelectorAll("[data-row-id]");
ok(cells.length === 70, "every renderable fact keeps one exact row-id cell, got " + cells.length);
const cellIds = new Set(cells.map((cell) => cell.getAttribute("data-row-id")));
ok(renderableIds.every((id) => cellIds.has(id)), "cell row ids must equal the source row ids");
ok(host.querySelector('[data-row-id="nr-1"]') === null,
  "unplottable/attribution-unknown fact must not appear as a plotted or zero-filled cell");

const sections = host.querySelectorAll(".kz-a-safety-observation-group");
function classTokens(node) { return String(node.className || "").split(/\s+/); }
function sectionFor(rowId) {
  const cell = host.querySelector('[data-row-id="' + rowId + '"]');
  ok(cell, rowId + " cell missing");
  let node = cell;
  while (node && !classTokens(node).includes("kz-a-safety-observation-group")) node = node.parent;
  ok(node, rowId + " section missing");
  return node;
}
function cellIdsOf(section) {
  return section.querySelectorAll("[data-row-id]")
    .map((cell) => cell.getAttribute("data-row-id")).sort();
}
function instanceFor(rowId) {
  const canvas = sectionFor(rowId).querySelector(".kz-a-safety-plot");
  if (!canvas) return null;
  return instances.find((instance) => instance.el === canvas) || null;
}
function optionRowIds(instance) {
  return instance.option.series[0].data.map((point) => point._row_id);
}
function optionValues(instance) {
  return instance.option.series[0].data.map((point) => point.value);
}

ok(sections.length === 12, "exact-facet sections must not be collapsed by the broad key, got "
  + sections.length);
ok(sections.every(
  (section) => section.querySelectorAll("[data-heat-label='product']").length === 1),
  "each facet section keeps exactly one product label");
ok(sections.every((section) => {
  const facetKey = section.getAttribute("data-facet-key");
  return typeof facetKey === "string" && facetKey.length > 0;
}), "each facet section exposes its exact numeric facet key");
ok(sections.every((section) => {
  const facetKey = section.getAttribute("data-facet-key");
  return section.querySelectorAll("[data-row-id]").every((cell) => {
    const source = rows.find((row) => row.row_id === cell.getAttribute("data-row-id"));
    return source && source.numeric_projection.facet_key === facetKey;
  });
}), "section facet key equals every member row's projection facet key");

/* 精确事件定义/限定词 + 统计基础/单位 + 人群 + 观察窗共同决定 facet */
assert.deepEqual(cellIdsOf(sectionFor("f1-treatment")), ["f1-control", "f1-treatment"]);
assert.deepEqual(cellIdsOf(sectionFor("f2-zero")), ["f2-treatment", "f2-zero"]);
ok(sectionFor("f3-nasopharyngitis") !== sectionFor("f1-treatment"),
  "same trial/arm with a different event definition must stay a separate facet");
assert.deepEqual(cellIdsOf(sectionFor("f3-nasopharyngitis")), ["f3-nasopharyngitis"]);
ok(sectionFor("f6-count") !== sectionFor("f6-percent"),
  "same event with a different statistical basis/unit must stay a separate facet");
ok(sectionFor("f7-itt") !== sectionFor("f7-safety-set"),
  "same event with a different population must stay a separate facet");
ok(sectionFor("f8-week16") !== sectionFor("f8-week24"),
  "same event with a different observation window must stay a separate facet");
ok(sectionFor("f9-other-product") !== sectionFor("f1-treatment"),
  "a different product cannot share the facet");
ok(cellIdsOf(sectionFor("f5-01")).length === 56,
  "one facet keeps all 56 same-basis observations as exact cells");

/* 单条观察直接列值；多条观察挂共享 ECharts */
ok(instanceFor("f3-nasopharyngitis") === null,
  "single observation keeps a compact direct value without an axis");
ok(sectionFor("f3-nasopharyngitis").querySelector(".kz-a-safety-plot") === null,
  "single observation must not mount a chart canvas");
const treatmentCell = host.querySelector('[data-row-id="f1-treatment"]');
ok(treatmentCell.querySelector(".kz-a-heat-value").textContent === "约38.7%",
  "compact direct value must stay exact, got "
  + treatmentCell.querySelector(".kz-a-heat-value").textContent);
ok(treatmentCell.textContent.includes("24/62人"), "numerator/denominator stays visible");
ok(String(treatmentCell.tagName).toLowerCase() === "button",
  "observation keeps its existing keyboard-accessible action button");
ok(treatmentCell.getAttribute("data-a-product-focus") === "p1",
  "observation keeps the existing product-context action identity");

const f1 = instanceFor("f1-treatment");
const f2 = instanceFor("f2-zero");
const f4 = instanceFor("f4-estimate-treatment");
const f5 = instanceFor("f5-01");
ok(f1 && f2 && f4 && f5, "multi-observation facets mount the shared chart renderer");
ok(instances.length === 4, "exactly the multi-observation facets mount charts, got "
  + instances.length);
assert.deepEqual(Array.from(optionRowIds(f1)).sort(), ["f1-control", "f1-treatment"]);
assert.deepEqual(Array.from(optionValues(f2)), [2, 0]);
ok(optionRowIds(f2).includes("f2-zero"), "zero-valued fact keeps its exact glyph row id");
ok(!optionRowIds(f2).includes("nr-1"), "unplottable fact is never filled with 0");
ok(f1.option.animation === false, "shared options stay non-animated");
ok(f1.option.xAxis.max({ min: 0, max: 24 / 62 * 100 }) === 100,
  "participant proportions keep the shared 0-100 scale");
ok(f4.option.xAxis.max({ min: 0, max: 0.4 }) < 1,
  "percent estimates are not stretched into a 0-100 probability axis");
ok(optionRowIds(f1).indexOf("f3-nasopharyngitis") === -1,
  "different facets never share one numeric axis");

/* 字形点击映射到精确行 ID 的既有产品上下文操作（当前页可见状态下） */
const f2Instance = instanceFor("f2-zero");
ok(typeof f2Instance.handlers.click === "function", "glyph click handler installed");
f2Instance.handlers.click({ data: { _row_id: "f2-zero" } });
const zeroCell = host.querySelector('[data-row-id="f2-zero"]');
const treatmentSaeCell = host.querySelector('[data-row-id="f2-treatment"]');
ok(zeroCell.focused === true && zeroCell.clicked === true,
  "glyph click focuses and activates the exact row action");
ok(treatmentSaeCell.focused !== true && treatmentSaeCell.clicked !== true,
  "no other row action is triggered by a glyph click");

/* 翻页懒挂载：只绘制当前页可见观察 */
const canvas = sectionFor("f1-treatment").querySelector(".kz-a-safety-plot");
ok(canvas.getAttribute("role") === "img" && canvas.getAttribute("aria-label"),
  "chart canvas keeps an accessible role and label");
ok(optionRowIds(f5).length === 46, "page one mounts only its visible observations, got "
  + optionRowIds(f5).length);
ok(!optionRowIds(f5).includes("f5-56"), "hidden-page observation is not plotted before paging");
ok(resizeObservers.some((observer) => observer.observed.includes(canvas)),
  "mounted charts are observed for resize");
const nav = host.querySelector(".kz-a-observation-pagination");
ok(nav, "pagination navigation present");
const nextButton = nav.children.find((child) => child.textContent === "下一页");
ok(nextButton && nextButton.listeners.click && nextButton.listeners.click.length,
  "next page action present");
nextButton.listeners.click[0]();
ok(f1.disposed === true && f2.disposed === true && f4.disposed === true,
  "charts dispose when their page leaves the visible set");
ok(f5.disposed === false && optionRowIds(f5).length === 10,
  "visible-page chart remounts only the page-two observations, got "
  + optionRowIds(f5).length);

/* pagehide 全量销毁 */
ok((windowListeners.pagehide || []).length >= 1, "pagehide dispose hook registered");
(windowListeners.pagehide || []).forEach((handler) => handler({}));
ok(instances.every((instance) => instance.disposed),
  "pagehide disposes every shared chart instance");

console.log("SAFETY-ECHARTS PROBE OK");
'''


def _run_probe(tmp_path: Path, source: str = _PROBE) -> subprocess.CompletedProcess[str]:
    probe = tmp_path / "safety_echarts_probe.js"
    probe.write_text(source, encoding="utf-8")
    return subprocess.run(
        ["node", str(probe), str(REPORT_A_JS), str(CHARTS_JS)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_r24_a_safety_views_render_through_the_shared_engine(tmp_path: Path) -> None:
    result = _run_probe(tmp_path)
    assert result.returncode == 0, result.stderr
    assert "SAFETY-ECHARTS PROBE OK" in result.stdout


def test_r24_a_count_without_n_is_not_a_null_ratio(tmp_path: Path) -> None:
    probe = _PROBE.replace(
        'vm.runInNewContext(fs.readFileSync(chartsPath, "utf8"), sandbox',
        'rows.find(r=>r.row_id==="f6-count").denominator=null;\n'
        'rows.find(r=>r.row_id==="f6-count").numeric_projection.denominator=null;\n'
        'vm.runInNewContext(fs.readFileSync(chartsPath, "utf8"), sandbox',
    )
    probe += (
        '\nconst nOnly=host.querySelector(\'[data-row-id="f6-count"]\').textContent;'
        '\nassert.ok(!nOnly.includes("null")&&!nOnly.includes("None"),nOnly);'
        '\nassert.ok(nOnly.includes("分母未列示"),nOnly);\n'
    )
    result = _run_probe(tmp_path, probe)
    assert result.returncode == 0, result.stderr


def test_r24_a_safety_renderer_replaces_manual_colour_with_shared_charts() -> None:
    source = REPORT_A_JS.read_text(encoding="utf-8")
    assert "function safetyEventLabel" in source, "safety facet helpers missing"
    body = source.split("function safetyEventLabel", 1)[1].split(
        "function updateMatrixTable", 1
    )[0]
    assert "presentationPlan" in body
    assert "syncEfficacyCharts" in body
    for duplicated_axis_logic in (
        "yAxis",
        "dataZoom",
        "visualMap",
        "seriesData",
        "style.background",
    ):
        assert duplicated_axis_logic not in body
    assert "color(" not in body
    assert "function color(" not in source
    assert "固定0至100" not in source
    assert "data-safety-layout" not in source
    for facet_contract in (
        "semantic_filter_key",
        "measure_context",
        "facet_key",
        "plot_unit",
        "population",
        "time_window",
    ):
        assert facet_contract in body, facet_contract
    shared_sync = source.split("function syncEfficacyCharts(host)", 1)[1]
    assert "buildBarOption" in shared_sync
    assert source.count("buildBarOption") == 1


def test_r24_a_safety_lifecycle_reuses_the_efficacy_hooks() -> None:
    source = REPORT_A_JS.read_text(encoding="utf-8")
    assert (
        'document.querySelectorAll(\'[data-a-chart="efficacy"], [data-a-chart="safety"]\')'
        in source
    )
    assert "disposeEfficacyCharts" in source
    assert "syncEfficacyCharts" in source
    assert "ResizeObserver" in source
    assert "host._observationSignature === signature" in source
    assert "event.data._row_id" in source
    assert source.count("window.echarts.init(") == 1
    assert "kz-a-safety-plot" in source


def test_r24_a_safety_chart_styles_are_defined_without_heat_layout() -> None:
    css = REPORT_A_CSS.read_text(encoding="utf-8")
    assert ".kz-a-safety-plot" in css
    assert ".kz-a-safety-observation-group" in css
    assert ".kz-a-safety-observations" in css
    assert "data-safety-layout" not in css
    assert "[data-a-chart=\"safety\"][data-safety-layout" not in css
