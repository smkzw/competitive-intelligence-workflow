"""R24 C 类入排标准：研究列登记原文对照表的最小 Node DOM 行为验收。

验收对象是生产资产 ``report-c.js`` 中真实执行的 ``renderCriteriaSources`` 渲染路径：
测试在一个最小 Node DOM 沙箱里加载真实文件、注入由生产函数生成的
``__CHART_GROUPS__`` 数据，驱动真实的关键词检索、研究勾选与 URL 状态，
再对真实 DOM 结果断言。没有对文本格式的伪装测试，也不启动浏览器。

数据来源：
- 基础行来自 ``fixtures/positive/c-atopic-dermatitis/inputs/report-data.json``，
  经生产 ``_page_observations`` / ``_chart_groups`` / ``_table_rows`` 计算，
  与页面内嵌结构一致。该 fixture 是合成开发输入，不是已接受的真实来源证据。
- 为覆盖「同一研究多条登记原文」的序号稳定性，测试为 NCT02260986 追加一条
  形态与生产行完全一致的补充条目；为覆盖用户修订/用户清除的当前值可见性，
  仅切换两条既有行的 ``review_state`` / ``disclosure_state``。这些补充只用于
  DOM 行为验收，不改变任何科学类型或数值，也不代表来源事实。

RED 前置：本文件先于 repair 编写，用于记录修复前真实失败；修复后同一行为族
必须整体转绿。浏览器/视觉验收仍由父级在真实 Chromium/WebKit 中执行。
"""

from __future__ import annotations

import importlib
import json
import re
import shutil
import subprocess
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
REPORT_DATA = ROOT / "fixtures/positive/c-atopic-dermatitis/inputs/report-data.json"
ASSET_JS = ROOT / "src/ci_workflow/renderers/portal/assets/report-c.js"
ASSET_CSS = ROOT / "src/ci_workflow/renderers/portal/assets/report-c.css"
PAGE_ID = "inclusion-criteria"

AUGMENTED_ROW_ID = "c-nct02260986-inclusion-2"
ORDINAL_QUERY = "Documented recent history"
MUTATED_ROW_ID = "c-nct03985943-inclusion"
CLEARED_ROW_ID = "c-nct05149313-inclusion"
FIRST_TRIAL_LABEL = "NCT02260986"
SEARCH_QUERY = "EASI"
NOTE_REQUIRED_PHRASE = "不按并列位置推断条款等价"


def _module() -> ModuleType:
    return importlib.import_module("ci_workflow.renderers.portal.report_c")


def _search_hits(rows: list[dict[str, Any]], query: str) -> list[str]:
    needle = query.casefold()
    hits: list[str] = []
    for row in rows:
        searchable = " ".join(
            str(row.get(key) or "")
            for key in ("product_zh", "trial_display_id", "trial_zh", "source_text")
        ).casefold()
        if needle in searchable:
            hits.append(str(row["row_id"]))
    return hits


def _expected_ordinals(rows: list[dict[str, Any]]) -> dict[str, int]:
    counters: dict[str, int] = {}
    ordinals: dict[str, int] = {}
    for row in rows:
        trial = str(row.get("trial_display_id") or row.get("trial_zh") or "试验未列示")
        counters[trial] = counters.get(trial, 0) + 1
        ordinals[str(row["row_id"])] = counters[trial]
    return ordinals


def _harness_payload() -> dict[str, Any]:
    module = _module()
    raw = json.loads(REPORT_DATA.read_text(encoding="utf-8"))
    data = module.ReportCPortalData.model_validate(raw)
    observations = module._page_observations(data, PAGE_ID)
    groups = json.loads(
        module._json(module._chart_groups(data, observations, page_id=PAGE_ID, title="入选标准"))
    )
    table_rows = json.loads(module._json(module._table_rows(data, observations, page_id=PAGE_ID)))
    _, dimensions = module._filter_dimensions_for_rows(data, observations)
    dimensions = json.loads(module._json(dimensions))
    filter_dimensions = json.loads(module._json(tuple(module._FILTER_DIMENSION_LABELS)))

    group = dict(groups[0])
    rows = [dict(row) for row in group["rows"]]
    by_id = {str(row["row_id"]): row for row in rows}

    # 同一研究的第二条登记原文：验证检索命中第 2 条时序号仍稳定为 2。
    seed = by_id["c-nct02260986-inclusion"]
    augmented = dict(seed)
    augmented["row_id"] = AUGMENTED_ROW_ID
    augmented["source_text"] = (
        "Documented recent history of moderate-to-severe atopic dermatitis before enrollment."
    )
    augmented["value"] = "入组前有中重度特应性皮炎近期病史记录（开发用补充条目）"
    rows.insert(1, augmented)

    # 当前值状态：只切换可见状态，不改变登记原文。
    by_id[MUTATED_ROW_ID]["review_state"] = "user_modified"
    by_id[MUTATED_ROW_ID]["value"] = "研究者修订：EASI ≥16（当前值）"
    by_id[CLEARED_ROW_ID]["disclosure_state"] = "user_cleared"

    group["rows"] = rows
    groups = [group]

    table_rows = list(table_rows)
    augmented_table = dict(table_rows[0])
    augmented_table["row_id"] = AUGMENTED_ROW_ID
    augmented_table["table_item_id"] = AUGMENTED_ROW_ID
    augmented_table["value"] = augmented["value"]
    table_rows.insert(1, augmented_table)
    for row in table_rows:
        row_id = str(row.get("row_id"))
        if row_id == MUTATED_ROW_ID:
            row["review_state"] = "user_modified"
            row["value"] = by_id[MUTATED_ROW_ID]["value"]
        elif row_id == CLEARED_ROW_ID:
            row["disclosure_state"] = "user_cleared"

    augmented_dimensions = dict(dimensions["c-nct02260986-inclusion"])
    dimensions = dict(dimensions)
    dimensions[AUGMENTED_ROW_ID] = augmented_dimensions

    return {
        "asset_path": str(ASSET_JS),
        "chart_groups": groups,
        "table_rows": table_rows,
        "row_dimensions": dimensions,
        "filter_dimensions": filter_dimensions,
        "first_trial": FIRST_TRIAL_LABEL,
        "ordinal_query": ORDINAL_QUERY,
        "search_query": SEARCH_QUERY,
        "augmented_row_id": AUGMENTED_ROW_ID,
        "source_texts": {str(row["row_id"]): str(row["source_text"]) for row in rows},
        "expected_ordinals": {
            row_id: str(value) for row_id, value in _expected_ordinals(rows).items()
        },
    }


HARNESS_JS = r"""
"use strict";

const fs = require("fs");
const vm = require("vm");

const data = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));

/* ---------------- minimal DOM ---------------- */

class TextNode {
  constructor(text, doc) {
    this.nodeType = 3;
    this.textContent = String(text);
    this.parentNode = null;
    this.doc = doc;
  }
}

function makeStyle(el) {
  const store = {};
  const sync = function () {
    const parts = [];
    Object.keys(store).forEach(function (key) {
      const value = store[key];
      if (value === "" || value === null || value === undefined) return;
      parts.push(key.replace(/[A-Z]/g, function (m) { return "-" + m.toLowerCase(); })
        + ": " + value + ";");
    });
    if (parts.length) el.setAttribute("style", parts.join(" "));
    else el.removeAttribute("style");
  };
  return new Proxy(store, {
    get: function (target, prop) { return target[prop]; },
    set: function (target, prop, value) {
      if (typeof prop === "symbol") { target[prop] = value; return true; }
      target[prop] = value;
      sync();
      return true;
    },
  });
}

class ElementNode {
  constructor(tag, doc) {
    this.nodeType = 1;
    this.tagName = String(tag).toUpperCase();
    this.doc = doc;
    this._attrs = Object.create(null);
    this._children = [];
    this._listeners = Object.create(null);
    this.parentNode = null;
    this.style = makeStyle(this);
    this.value = "";
    this.checked = false;
    this.type = "";
    this.placeholder = "";
    this.open = false;
    this.clientWidth = 0;
    this.scrollWidth = 0;
  }

  setAttribute(name, value) { this._attrs[String(name)] = String(value); }
  getAttribute(name) {
    const key = String(name);
    return Object.prototype.hasOwnProperty.call(this._attrs, key) ? this._attrs[key] : null;
  }
  hasAttribute(name) {
    return Object.prototype.hasOwnProperty.call(this._attrs, String(name));
  }
  removeAttribute(name) { delete this._attrs[String(name)]; }
  appendChild(node) {
    if (node.parentNode) node.parentNode.removeChild(node);
    node.parentNode = this;
    this._children.push(node);
    return node;
  }
  append() {
    const nodes = Array.prototype.slice.call(arguments);
    nodes.forEach((node) => this.appendChild(node));
  }
  removeChild(node) {
    const index = this._children.indexOf(node);
    if (index !== -1) { this._children.splice(index, 1); node.parentNode = null; }
    return node;
  }
  replaceChildren() {
    const nodes = Array.prototype.slice.call(arguments);
    this._children.slice().forEach((child) => this.removeChild(child));
    nodes.forEach((node) => this.appendChild(node));
  }
  insertBefore(node, reference) {
    if (!reference) return this.appendChild(node);
    if (node.parentNode) node.parentNode.removeChild(node);
    const index = this._children.indexOf(reference);
    node.parentNode = this;
    if (index === -1) this._children.push(node);
    else this._children.splice(index, 0, node);
    return node;
  }
  addEventListener(type, listener) {
    (this._listeners[type] = this._listeners[type] || []).push(listener);
  }
  removeEventListener(type, listener) {
    const list = this._listeners[type] || [];
    const index = list.indexOf(listener);
    if (index !== -1) list.splice(index, 1);
  }
  dispatchEvent(event) { dispatch(this, event); return true; }
  querySelector(selector) {
    const found = this.querySelectorAll(selector);
    return found.length ? found[0] : null;
  }
  querySelectorAll(selector) {
    const groups = parseSelector(selector);
    const out = [];
    visit(this, function (node) {
      if (matchesAny(node, groups)) out.push(node);
    });
    return out;
  }
  closest(selector) {
    const groups = parseSelector(selector);
    let node = this;
    while (node && node.nodeType === 1) {
      if (matchesAny(node, groups)) return node;
      node = node.parentNode;
    }
    return null;
  }
  matches(selector) { return matchesAny(this, parseSelector(selector)); }
  get children() { return this._children.filter((child) => child.nodeType === 1); }
  get childNodes() { return this._children.slice(); }
  get firstChild() { return this._children[0] || null; }
  get id() { return this.getAttribute("id") || ""; }
  set id(value) { this.setAttribute("id", String(value)); }
  get className() { return this.getAttribute("class") || ""; }
  set className(value) { this.setAttribute("class", String(value)); }
  get classList() {
    const self = this;
    const read = function () {
      return String(self.getAttribute("class") || "").split(/\s+/).filter(Boolean);
    };
    const write = function (list) {
      if (list.length) self.setAttribute("class", list.join(" "));
      else self.removeAttribute("class");
    };
    return {
      add: function (name) {
        const list = read();
        if (list.indexOf(name) === -1) { list.push(name); write(list); }
      },
      remove: function (name) { write(read().filter((item) => item !== name)); },
      contains: function (name) { return read().indexOf(name) !== -1; },
      toggle: function (name) {
        if (read().indexOf(name) === -1) { this.add(name); return true; }
        this.remove(name);
        return false;
      },
    };
  }
}

Object.defineProperty(ElementNode.prototype, "textContent", {
  get: function () { return collectText(this); },
  set: function (value) {
    this._children.slice().forEach((child) => this.removeChild(child));
    if (value !== "" && value !== null && value !== undefined) {
      this.appendChild(this.doc.createTextNode(String(value)));
    }
  },
});

Object.defineProperty(ElementNode.prototype, "innerHTML", {
  get: function () { return null; },
  set: function (value) {
    if (value === "" || value === null || value === undefined) {
      this.replaceChildren();
      return;
    }
    throw new Error("harness innerHTML 只支持清空操作");
  },
});

function collectText(node) {
  if (node.nodeType === 3) return String(node.textContent);
  let out = "";
  node._children.forEach(function (child) { out += collectText(child); });
  return out;
}

function visit(node, fn) {
  node._children.forEach(function (child) {
    if (child.nodeType === 1) { fn(child); visit(child, fn); }
  });
}

function dispatch(target, event) {
  const evt = event || {};
  if (!evt.type) throw new Error("事件缺少 type");
  if (!evt.target) evt.target = target;
  if (!evt.preventDefault) evt.preventDefault = function () {};
  if (!evt.stopPropagation) evt.stopPropagation = function () {};
  let node = target;
  while (node) {
    const listeners = node._listeners && node._listeners[evt.type];
    if (listeners) {
      listeners.slice().forEach(function (listener) { listener.call(node, evt); });
    }
    node = node.parentNode || null;
  }
  const doc = target.doc;
  if (doc) {
    const docListeners = doc.listeners[evt.type];
    if (docListeners) {
      docListeners.slice().forEach(function (listener) { listener.call(doc, evt); });
    }
  }
}

/* ---------------- tiny selector engine ---------------- */

function matchingParen(text, start) {
  let depth = 0;
  for (let i = start; i < text.length; i += 1) {
    if (text[i] === "(") depth += 1;
    else if (text[i] === ")") {
      depth -= 1;
      if (depth === 0) return i;
    }
  }
  throw new Error("未闭合的 :not( ：" + text);
}

function parseAttrToken(text) {
  const match = /^([^\s=*\]]+)\s*(\*?=)?\s*(.*)$/.exec(text);
  if (!match) throw new Error("无法解析属性选择器：[" + text + "]");
  let value = match[3] || "";
  if (
    value.length >= 2
    && ((value[0] === '"' && value[value.length - 1] === '"')
      || (value[0] === "'" && value[value.length - 1] === "'"))
  ) {
    value = value.slice(1, -1);
  }
  return { name: match[1], op: match[2] || "", value: value };
}

function parseCompound(text) {
  const compound = { tag: null, id: null, classes: [], attrs: [], notAttrs: [] };
  let rest = text;
  const tagMatch = /^[A-Za-z][\w-]*/.exec(rest);
  if (tagMatch) {
    compound.tag = tagMatch[0].toLowerCase();
    rest = rest.slice(tagMatch[0].length);
  }
  while (rest.length) {
    if (rest[0] === ".") {
      const match = /^\.([\w-]+)/.exec(rest);
      if (!match) throw new Error("无法解析类选择器：" + text);
      compound.classes.push(match[1]);
      rest = rest.slice(match[0].length);
    } else if (rest[0] === "#") {
      const match = /^#([\w-]+)/.exec(rest);
      if (!match) throw new Error("无法解析 id 选择器：" + text);
      compound.id = match[1];
      rest = rest.slice(match[0].length);
    } else if (rest[0] === "[") {
      const end = rest.indexOf("]");
      if (end === -1) throw new Error("未闭合的属性选择器：" + text);
      compound.attrs.push(parseAttrToken(rest.slice(1, end)));
      rest = rest.slice(end + 1);
    } else if (rest.indexOf(":not(") === 0) {
      const end = matchingParen(rest, 0);
      const inner = rest.slice(5, end);
      if (inner[0] !== "[" || inner[inner.length - 1] !== "]") {
        throw new Error("仅支持 :not([attr...]) ：" + text);
      }
      compound.notAttrs.push(parseAttrToken(inner.slice(1, -1)));
      rest = rest.slice(end + 1);
    } else {
      throw new Error("不支持的选择器片段：" + rest);
    }
  }
  return compound;
}

function parseSelector(selector) {
  return String(selector).split(",").map(function (group) {
    const parts = [];
    let combinator = null;
    let buffer = "";
    const flush = function () {
      if (buffer.trim()) {
        parts.push({ combinator: combinator, compound: parseCompound(buffer.trim()) });
      }
      buffer = "";
    };
    for (let i = 0; i < group.length; i += 1) {
      const ch = group[i];
      if (ch === ">") { flush(); combinator = "child"; continue; }
      if (/\s/.test(ch)) {
        flush();
        if (!combinator) combinator = "descendant";
        continue;
      }
      buffer += ch;
    }
    flush();
    if (!parts.length) throw new Error("空选择器：" + selector);
    return parts;
  });
}

function matchCompound(node, compound) {
  if (!node || node.nodeType !== 1) return false;
  if (compound.tag && node.tagName.toLowerCase() !== compound.tag) return false;
  if (compound.id && node.getAttribute("id") !== compound.id) return false;
  for (const name of compound.classes) {
    if (!node.classList.contains(name)) return false;
  }
  for (const attr of compound.attrs) {
    const value = node.getAttribute(attr.name);
    if (value === null) return false;
    if (attr.op === "=" && value !== attr.value) return false;
    if (attr.op === "*=" && value.indexOf(attr.value) === -1) return false;
  }
  for (const attr of compound.notAttrs) {
    const value = node.getAttribute(attr.name);
    if (value === null) continue;
    if (attr.op === "*=") {
      if (value.indexOf(attr.value) !== -1) return false;
    } else if (attr.op === "=") {
      if (value === attr.value) return false;
    } else {
      return false;
    }
  }
  return true;
}

function matchesGroup(node, parts) {
  let index = parts.length - 1;
  if (!matchCompound(node, parts[index].compound)) return false;
  let cursor = node;
  index -= 1;
  while (index >= 0) {
    const step = parts[index + 1];
    if (step.combinator === "child") {
      cursor = cursor.parentNode;
      if (!matchCompound(cursor, parts[index].compound)) return false;
    } else {
      cursor = cursor.parentNode;
      let found = false;
      while (cursor && cursor.nodeType === 1) {
        if (matchCompound(cursor, parts[index].compound)) { found = true; break; }
        cursor = cursor.parentNode;
      }
      if (!found) return false;
    }
    index -= 1;
  }
  return true;
}

function matchesAny(node, groups) {
  return groups.some((parts) => matchesGroup(node, parts));
}

/* ---------------- document / window ---------------- */

function isAttached(node, doc) {
  let cursor = node;
  while (cursor.parentNode) cursor = cursor.parentNode;
  return cursor === doc.documentElement || cursor === doc;
}

function makeDocument() {
  const doc = {
    readyState: "complete",
    _all: [],
    listeners: Object.create(null),
    createElement(tag) {
      const el = new ElementNode(tag, doc);
      doc._all.push(el);
      return el;
    },
    createTextNode(text) { return new TextNode(text, doc); },
    getElementById(id) {
      // 与浏览器语义一致：已脱离文档的元素不会被 document.getElementById 命中。
      return doc._all.find(
        (el) => el.getAttribute("id") === id && isAttached(el, doc)
      ) || null;
    },
    querySelectorAll(selector) {
      const groups = parseSelector(selector);
      return doc._all.filter((el) => isAttached(el, doc) && matchesAny(el, groups));
    },
    querySelector(selector) {
      const found = doc.querySelectorAll(selector);
      return found.length ? found[0] : null;
    },
    addEventListener(type, listener) {
      (doc.listeners[type] = doc.listeners[type] || []).push(listener);
    },
    dispatchEvent(event) {
      const list = doc.listeners[event.type];
      if (list) list.slice().forEach((listener) => listener.call(doc, event));
      return true;
    },
  };
  const html = doc.createElement("html");
  const body = doc.createElement("body");
  html.appendChild(body);
  doc.documentElement = html;
  doc.body = body;
  return doc;
}

function makeWindow(doc) {
  const timers = [];
  const win = {
    document: doc,
    location: { href: "file:///harness/index.html", search: "", hash: "" },
    history: {
      replaceState(state, title, url) {
        const parsed = new URL(url, win.location.href);
        win.location.href = parsed.href;
        win.location.search = parsed.search;
        win.location.hash = parsed.hash;
      },
    },
    setTimeout(fn) { timers.push(fn); return timers.length; },
    clearTimeout() {},
    addEventListener(type, listener) {
      (win._listeners[type] = win._listeners[type] || []).push(listener);
    },
    removeEventListener() {},
    matchMedia() {
      return { matches: false, addEventListener() {}, removeEventListener() {} };
    },
    getComputedStyle() { return {}; },
    innerWidth: 1600,
    innerHeight: 900,
    scrollY: 0,
    _listeners: Object.create(null),
    _flushTimers() {
      let guard = 0;
      while (timers.length && guard < 1000) {
        guard += 1;
        timers.shift()();
      }
    },
  };
  win.window = win;
  return win;
}

/* ---------------- page skeleton (mirrors base.html + page.html.j2) ---------------- */

function buildSkeleton(doc, page) {
  const body = doc.body;
  const head = doc.createElement("header");
  head.className = "kz-c-page-head";
  body.appendChild(head);

  const panel = doc.createElement("details");
  panel.setAttribute("id", "kz-filter-panel");
  panel.className = "kz-c-filter-panel";
  const panelSummary = doc.createElement("summary");
  panelSummary.textContent = "筛选条件";
  panel.appendChild(panelSummary);
  const filters = doc.createElement("div");
  filters.className = "kz-c-filters";
  const summary = doc.createElement("span");
  summary.setAttribute("data-filter-summary", "");
  summary.textContent = "未设置筛选";
  filters.appendChild(summary);
  const reset = doc.createElement("button");
  reset.setAttribute("type", "button");
  reset.setAttribute("data-filter-reset", "");
  reset.textContent = "清除筛选";
  filters.appendChild(reset);
  const status = doc.createElement("span");
  status.setAttribute("data-filter-status", "");
  status.setAttribute("aria-live", "polite");
  status.textContent = "显示全部可用记录";
  filters.appendChild(status);
  panel.appendChild(filters);
  body.appendChild(panel);

  const module = doc.createElement("div");
  module.setAttribute("id", "kz-chart-module");
  module.className = "kz-chart-module";
  const visuals = doc.createElement("div");
  visuals.setAttribute("id", "kz-c-chart-visuals");
  visuals.className = "kz-c-chart-visuals";
  module.appendChild(visuals);

  const table = doc.createElement("table");
  table.className = "kz-chart-table";
  table.setAttribute("aria-label", "完整表格");
  const thead = doc.createElement("thead");
  const headRow = doc.createElement("tr");
  ["试验编号", "设计要素", "内容", "数据依据"].forEach(function (label) {
    const th = doc.createElement("th");
    th.className = "kz-chart-table__th";
    th.setAttribute("scope", "col");
    th.textContent = label;
    headRow.appendChild(th);
  });
  thead.appendChild(headRow);
  table.appendChild(thead);
  const tbody = doc.createElement("tbody");
  page.table_rows.forEach(function (row) {
    const tr = doc.createElement("tr");
    tr.className = "kz-chart-table__row";
    tr.setAttribute("data-row-id", String(row.row_id));
    tr.setAttribute("data-table-item-id", String(row.table_item_id || row.row_id));
    tr.setAttribute("data-trial-id", String(row.trial_id || ""));
    tr.setAttribute("data-product-id", String(row.product_id || ""));
    tr.setAttribute("tabindex", "0");
    const cell = doc.createElement("td");
    cell.className = "kz-chart-table__cell";
    cell.setAttribute("data-evidence-open", String(row.row_id));
    cell.setAttribute("data-row-id", String(row.row_id));
    cell.textContent = String(row.value == null ? "" : row.value);
    tr.appendChild(cell);
    const action = doc.createElement("td");
    action.className = "kz-chart-table__cell";
    const button = doc.createElement("button");
    button.setAttribute("type", "button");
    button.className = "kz-c-evidence-button";
    button.setAttribute("data-evidence-open", String(row.row_id));
    button.setAttribute("data-row-id", String(row.row_id));
    button.textContent = "查看依据";
    action.appendChild(button);
    tr.appendChild(action);
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  module.appendChild(table);
  body.appendChild(module);
}

/* ---------------- context runner ---------------- */

function runContext(search, page) {
  const doc = makeDocument();
  buildSkeleton(doc, page);
  const win = makeWindow(doc);
  win.location.href = "file:///harness/index.html" + search;
  win.location.search = search;
  win.__CHART_GROUPS__ = page.chart_groups;
  win.__C_ROW_DIMENSIONS__ = page.row_dimensions;
  win.__C_FILTER_DIMENSIONS__ = page.filter_dimensions;
  win.__C_PAGE_ID__ = "inclusion-criteria";
  win.__C_PAGE_TITLE__ = "入选标准";
  win.__SNAPSHOT_ID__ = "harness";
  win.__ROW_SET_DIGEST__ = "harness";
  win.echarts = {
    init() { throw new Error("入排标准页不应初始化 ECharts"); },
  };
  const sandbox = {
    window: win,
    document: doc,
    URL: URL,
    URLSearchParams: URLSearchParams,
    console: console,
    setTimeout: win.setTimeout,
    clearTimeout: win.clearTimeout,
  };
  const context = vm.createContext(sandbox);
  const source = fs.readFileSync(page.asset_path, "utf8");
  vm.runInContext(source, context, { filename: page.asset_path });
  win._flushTimers();
  return { doc: doc, win: win };
}

/* ---------------- snapshot ---------------- */

function snapshot(ctx) {
  const doc = ctx.doc;
  const defs = doc.querySelectorAll("[data-criterion-row-id]").map(function (node) {
    const evidence = node.querySelectorAll("[data-evidence-open]");
    const original = node.querySelector(".kz-c-criteria-original");
    const revision = node.querySelector(".kz-c-criteria-revision");
    const summary = node.querySelector("summary");
    return {
      row_id: node.getAttribute("data-criterion-row-id"),
      ordinal: node.getAttribute("data-criterion-ordinal"),
      trial_id: node.getAttribute("data-criterion-trial-id"),
      product_id: node.getAttribute("data-criterion-product-id"),
      current_state: node.getAttribute("data-criterion-current-state") || "",
      review_state: node.getAttribute("data-criterion-review-state") || "",
      disclosure_state: node.getAttribute("data-criterion-disclosure-state") || "",
      summary: summary ? summary.textContent : null,
      text: node.textContent,
      original_text: original ? original.textContent : null,
      revision_text: revision ? revision.textContent : null,
      evidence_count: evidence.length,
      evidence_row_id: evidence.length ? evidence[0].getAttribute("data-evidence-open") : null,
      has_summary: Boolean(summary),
    };
  });
  const visibleTableRows = doc.querySelectorAll(".kz-chart-table__row[data-row-id]")
    .filter((node) => node.style.display !== "none")
    .map((node) => node.getAttribute("data-row-id"));
  const tables = doc.querySelectorAll("table.kz-c-criteria-table");
  const wrap = doc.querySelector(".kz-c-criteria-table-wrap");
  const note = doc.querySelector(".kz-c-criteria-note");
  const status = doc.querySelector(".kz-c-criteria-status");
  const search = doc.getElementById("kz-c-criteria-search");
  return {
    table_count: tables.length,
    table_present: tables.length === 1,
    study_headers: doc.querySelectorAll("[data-criteria-study]").map(function (node) {
      return {
        trial_id: node.getAttribute("data-criteria-study"),
        scope: node.getAttribute("scope"),
        text: node.textContent,
      };
    }),
    ordinal_row_headers: doc.querySelectorAll("table.kz-c-criteria-table th[scope=row]")
      .map((node) => node.textContent),
    wrap: wrap ? {
      role: wrap.getAttribute("role"),
      tabindex: wrap.getAttribute("tabindex"),
      aria_label: wrap.getAttribute("aria-label"),
    } : null,
    note_text: note ? note.textContent : "",
    status_text: status ? status.textContent : "",
    search_value: search ? search.value : null,
    checkboxes: doc.querySelectorAll(".kz-c-criteria-choices input").map(function (node) {
      return { value: node.value, checked: node.checked };
    }),
    defs: defs,
    visible_table_rows: visibleTableRows,
    url_search: ctx.win.location.search,
  };
}

function searchFor(ctx, value) {
  const input = ctx.doc.getElementById("kz-c-criteria-search");
  if (!input) throw new Error("缺少检索输入框 #kz-c-criteria-search");
  input.value = value;
  dispatch(input, { type: "input" });
  ctx.win._flushTimers();
}

function setStudyChecked(ctx, trialId, checked) {
  const boxes = ctx.doc.querySelectorAll(".kz-c-criteria-choices input");
  const box = boxes.find((item) => item.value === trialId);
  if (!box) throw new Error("缺少研究勾选框：" + trialId);
  box.checked = checked;
  dispatch(box, { type: "change" });
  ctx.win._flushTimers();
}

/* ---------------- driver ---------------- */

const out = { ok: true, snapshots: {}, expected_row_ids: [] };
try {
  if (!fs.existsSync(data.asset_path)) {
    throw new Error("缺少生产资产：" + data.asset_path);
  }
  out.expected_row_ids = data.chart_groups[0].rows.map((row) => String(row.row_id));
  const A = runContext("", data);
  out.snapshots.initial = snapshot(A);
  searchFor(A, data.search_query);
  out.snapshots.search = snapshot(A);
  searchFor(A, "");
  out.snapshots.clear = snapshot(A);
  searchFor(A, data.ordinal_query);
  out.snapshots.ordinal = snapshot(A);
  searchFor(A, "");
  out.snapshots.ordinal_clear = snapshot(A);
  setStudyChecked(A, data.first_trial, false);
  out.snapshots.unchecked = snapshot(A);
  searchFor(A, data.search_query);
  out.snapshots.unchecked_search = snapshot(A);
  searchFor(A, "");
  out.snapshots.unchecked_clear = snapshot(A);
  setStudyChecked(A, data.first_trial, true);
  out.snapshots.rechecked = snapshot(A);
  const B = runContext(
    "?criteria_q=" + encodeURIComponent(data.search_query)
      + "&criteria_hide=" + encodeURIComponent(data.first_trial),
    data
  );
  out.snapshots.restore = snapshot(B);
} catch (error) {
  out.ok = false;
  out.error = String(error && error.stack ? error.stack : error);
}
process.stdout.write(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def payload() -> dict[str, Any]:
    return _harness_payload()


@pytest.fixture(scope="module")
def harness(tmp_path_factory: pytest.TempPathFactory, payload: dict[str, Any]) -> dict[str, Any]:
    node = shutil.which("node")
    if node is None:
        pytest.skip("需要 Node.js 执行 C 门户最小 DOM 行为测试；未安装则无法覆盖该行为族")
    work = tmp_path_factory.mktemp("r24-c-precedent-table")
    harness_path = work / "harness.cjs"
    harness_path.write_text(HARNESS_JS, encoding="utf-8")
    payload_path = work / "payload.json"
    payload_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    completed = subprocess.run(
        [node, str(harness_path), str(payload_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, (
        "Node DOM 沙箱异常退出：\n" + completed.stderr + "\n" + completed.stdout[:2000]
    )
    result = json.loads(completed.stdout)
    if not result.get("ok"):
        pytest.fail("加载生产 report-c.js 失败：" + str(result.get("error")), pytrace=False)
    return result


def _defs_by_row(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["row_id"]: item for item in snapshot["defs"]}


def _row_ids(snapshot: dict[str, Any]) -> list[str]:
    return [item["row_id"] for item in snapshot["defs"]]


def _ordinals(snapshot: dict[str, Any]) -> dict[str, str]:
    return {
        item["row_id"]: item["ordinal"] for item in snapshot["defs"] if item["ordinal"] is not None
    }


# ---------------------------------------------------------------------------
# 根行为族：真实 DOM 中的研究列表格、稳定序号、检索/勾选/URL 完整性
# ---------------------------------------------------------------------------


def test_criteria_precedent_table_is_study_column_table_with_stable_ordinals(
    payload: dict[str, Any], harness: dict[str, Any]
) -> None:
    initial = harness["snapshots"]["initial"]
    rows = payload["chart_groups"][0]["rows"]
    expected_ids = [str(row["row_id"]) for row in rows]

    assert initial["table_present"] is True
    assert initial["table_count"] == 1
    assert initial["wrap"] is not None
    assert initial["wrap"]["role"] == "region"
    assert initial["wrap"]["tabindex"] == "0"
    assert initial["wrap"]["aria_label"]

    trial_ids = sorted({str(row["trial_display_id"]) for row in rows})
    headers = initial["study_headers"]
    assert [item["trial_id"] for item in headers] == trial_ids
    assert all(item["scope"] == "col" for item in headers)
    assert len(headers) == 4

    assert sorted(_row_ids(initial)) == sorted(expected_ids)
    assert len(initial["defs"]) == len(expected_ids)

    ordinals = _ordinals(initial)
    assert ordinals == payload["expected_ordinals"]

    for item in initial["defs"]:
        expected_ordinal = payload["expected_ordinals"][item["row_id"]]
        assert item["summary"] is not None
        assert "登记原文 " + expected_ordinal in item["summary"]
        assert item["original_text"] == payload["source_texts"][item["row_id"]]
        assert item["text"].find(payload["source_texts"][item["row_id"]]) != -1
        assert item["evidence_count"] == 1
        assert item["evidence_row_id"] == item["row_id"]

    assert NOTE_REQUIRED_PHRASE in initial["note_text"]
    assert "原始记录" in initial["note_text"]
    assert "登记原文（" in "".join(initial["ordinal_row_headers"])
    assert sorted(initial["visible_table_rows"]) == sorted(expected_ids)


def test_criteria_precedent_table_search_and_study_choices_stay_integrity(
    payload: dict[str, Any], harness: dict[str, Any]
) -> None:
    snapshots = harness["snapshots"]
    rows = payload["chart_groups"][0]["rows"]
    all_ids = [str(row["row_id"]) for row in rows]
    easi_hits = _search_hits(rows, SEARCH_QUERY)
    assert len(easi_hits) >= 2, easi_hits
    augmented_hits = _search_hits(rows, ORDINAL_QUERY)
    first_trial_row_ids = [
        str(row["row_id"]) for row in rows if str(row["trial_display_id"]) == FIRST_TRIAL_LABEL
    ]
    remaining = [row_id for row_id in all_ids if row_id not in first_trial_row_ids]

    # 初始与检索后：原始序号不因检索重排。
    initial = snapshots["initial"]
    search = snapshots["search"]
    assert sorted(_row_ids(search)) == sorted(easi_hits)
    assert _ordinals(search) == {
        row_id: payload["expected_ordinals"][row_id] for row_id in easi_hits
    }
    assert sorted(search["visible_table_rows"]) == sorted(easi_hits)

    clear = snapshots["clear"]
    assert sorted(_row_ids(clear)) == sorted(all_ids)
    assert _ordinals(clear) == payload["expected_ordinals"]
    assert sorted(clear["visible_table_rows"]) == sorted(all_ids)
    assert _ordinals(clear) == _ordinals(initial)

    # 命中同一研究的第 2 条登记原文时，序号保持 2 而不是重排为 1。
    ordinal = snapshots["ordinal"]
    assert _row_ids(ordinal) == augmented_hits
    assert payload["augmented_row_id"] in augmented_hits
    assert ordinal["defs"][0]["ordinal"] == "2"
    assert "登记原文 2" in ordinal["defs"][0]["summary"]
    assert sorted(ordinal["visible_table_rows"]) == sorted(augmented_hits)

    ordinal_clear = snapshots["ordinal_clear"]
    assert sorted(_row_ids(ordinal_clear)) == sorted(all_ids)
    assert _ordinals(ordinal_clear) == payload["expected_ordinals"]

    # 取消勾选一项研究：只移除该研究的列与该研究的完整表行，序号不变。
    unchecked = snapshots["unchecked"]
    assert sorted(_row_ids(unchecked)) == sorted(remaining)
    assert FIRST_TRIAL_LABEL not in [item["trial_id"] for item in unchecked["study_headers"]]
    assert sorted(unchecked["visible_table_rows"]) == sorted(remaining)
    unchecked_boxes = {item["value"]: item["checked"] for item in unchecked["checkboxes"]}
    assert unchecked_boxes[FIRST_TRIAL_LABEL] is False
    assert all(
        checked is True
        for trial_label, checked in unchecked_boxes.items()
        if trial_label != FIRST_TRIAL_LABEL
    )
    assert "criteria_hide=" + FIRST_TRIAL_LABEL in unchecked["url_search"]

    # 勾选之外再检索，再清空：检索行恢复，研究勾选不丢失。
    unchecked_search = snapshots["unchecked_search"]
    expected_unchecked_hits = [row_id for row_id in easi_hits if row_id not in first_trial_row_ids]
    assert sorted(_row_ids(unchecked_search)) == sorted(expected_unchecked_hits)
    unchecked_clear = snapshots["unchecked_clear"]
    assert sorted(_row_ids(unchecked_clear)) == sorted(remaining)
    assert _ordinals(unchecked_clear) == {
        row_id: payload["expected_ordinals"][row_id] for row_id in remaining
    }
    boxes_after_clear = {item["value"]: item["checked"] for item in unchecked_clear["checkboxes"]}
    assert boxes_after_clear[FIRST_TRIAL_LABEL] is False
    assert "criteria_q=" not in unchecked_clear["url_search"]

    rechecked = snapshots["rechecked"]
    assert sorted(_row_ids(rechecked)) == sorted(all_ids)
    boxes_rechecked = {item["value"]: item["checked"] for item in rechecked["checkboxes"]}
    assert all(boxes_rechecked.values())
    assert "criteria_hide=" not in rechecked["url_search"]


def test_criteria_precedent_table_keeps_current_edit_visible_and_reachable(
    payload: dict[str, Any], harness: dict[str, Any]
) -> None:
    search = harness["snapshots"]["search"]
    defs = _defs_by_row(search)

    mutated = defs[MUTATED_ROW_ID]
    assert mutated["current_state"] == "user_modified"
    assert mutated["review_state"] == "user_modified"
    assert mutated["revision_text"] is not None
    assert "当前修订" in mutated["revision_text"]
    assert mutated["original_text"] == payload["source_texts"][MUTATED_ROW_ID]
    assert mutated["revision_text"] != mutated["original_text"]
    assert mutated["evidence_count"] == 1

    cleared = defs[CLEARED_ROW_ID]
    assert cleared["current_state"] == "user_cleared"
    assert cleared["disclosure_state"] == "user_cleared"
    assert cleared["revision_text"] is not None
    assert "用户清除" in cleared["revision_text"]
    assert cleared["original_text"] == payload["source_texts"][CLEARED_ROW_ID]
    assert cleared["evidence_count"] == 1

    # 清空检索后当前值与原文依旧逐条可达，不能被检索状态改写。
    clear = harness["snapshots"]["clear"]
    defs_after = _defs_by_row(clear)
    assert defs_after[MUTATED_ROW_ID]["current_state"] == "user_modified"
    assert defs_after[CLEARED_ROW_ID]["current_state"] == "user_cleared"
    assert defs_after[MUTATED_ROW_ID]["original_text"] == payload["source_texts"][MUTATED_ROW_ID]
    assert defs_after[CLEARED_ROW_ID]["original_text"] == payload["source_texts"][CLEARED_ROW_ID]


def test_criteria_precedent_table_restores_from_url_state(
    payload: dict[str, Any], harness: dict[str, Any]
) -> None:
    restore = harness["snapshots"]["restore"]
    rows = payload["chart_groups"][0]["rows"]
    first_trial_row_ids = [
        str(row["row_id"]) for row in rows if str(row["trial_display_id"]) == FIRST_TRIAL_LABEL
    ]
    expected_hits = [
        row_id for row_id in _search_hits(rows, SEARCH_QUERY) if row_id not in first_trial_row_ids
    ]

    assert restore["search_value"] == SEARCH_QUERY
    assert sorted(_row_ids(restore)) == sorted(expected_hits)
    assert sorted(restore["visible_table_rows"]) == sorted(expected_hits)
    boxes = {item["value"]: item["checked"] for item in restore["checkboxes"]}
    assert boxes[FIRST_TRIAL_LABEL] is False
    assert len(restore["checkboxes"]) == 4
    assert len(restore["study_headers"]) == 3
    assert FIRST_TRIAL_LABEL not in [item["trial_id"] for item in restore["study_headers"]]


# ---------------------------------------------------------------------------
# 相关 GREEN 组：样式合同与既有消费者标记
# ---------------------------------------------------------------------------


def _css_block(css: str, selector: str) -> str:
    match = re.search(r"(?m)^" + re.escape(selector) + r"\s*\{([^}]*)\}", css)
    assert match is not None, f"report-c.css 缺少样式块：{selector}"
    return match.group(1)


def test_criteria_precedent_table_css_contract() -> None:
    css = ASSET_CSS.read_text(encoding="utf-8")

    wrap = _css_block(css, ".kz-c-criteria-table-wrap")
    assert "overflow-x: auto" in wrap
    assert "max-width: 100%" in wrap or "max-width:100%" in wrap
    assert "overflow: hidden" not in wrap
    assert "overflow-y: visible" in wrap

    table = _css_block(css, ".kz-c-criteria-table")
    assert "width: max-content" in table or "width:max-content" in table
    assert "min-width: 100%" in table or "min-width:100%" in table

    cells = _css_block(css, ".kz-c-criteria-table__cell")
    assert "min-width: 300px" in cells or "min-width:300px" in cells
    assert "font-size: 1rem" in cells or "font-size:1rem" in cells
    assert "overflow-wrap: anywhere" in cells or "overflow-wrap:anywhere" in cells

    study_th = _css_block(css, ".kz-c-criteria-table__study-th")
    assert "min-width: 300px" in study_th or "min-width:300px" in study_th
    assert "font-size: 1rem" in study_th or "font-size:1rem" in study_th

    ordinal = _css_block(css, ".kz-c-criteria-table__ordinal-cell")
    assert "position: sticky" in ordinal or "position:sticky" in ordinal
    assert "left: 0" in ordinal or "left:0" in ordinal


def test_criteria_surface_keeps_existing_consumers_wired() -> None:
    source = ASSET_JS.read_text(encoding="utf-8")

    for token in (
        "kz-c-criteria-search",
        "kz-c-criteria-choose",
        "kz-c-criteria-choices",
        "kz-c-criteria-item",
        "kz-c-criteria-trial",
        "kz-c-criteria-revision",
        "kz-c-criteria-original",
        "kz-c-criteria-source",
        "criteria_q",
        "criteria_hide",
        "renderCriteriaSources",
        NOTE_REQUIRED_PHRASE,
    ):
        assert token in source, token

    # 既有验收合同（不因本次修复改写）：矩阵相关精确字符串仍保留。
    # 说明：tests/acceptance/test_report_c.py 另有一处对 2026-10-03 之前版本的
    # 期望字符串（`return p.data.value[2] ? ...`）当前已与源码不符，属修复前
    # 既有失败，本测试不复述该过期期望，也不改写既有验收。
    assert '"core-design-matrix": "核心设计事实比较"' in source
    assert "compactTrialAxis ? trialId : trialLabel" in source
