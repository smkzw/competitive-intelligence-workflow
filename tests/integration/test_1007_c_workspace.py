"""C overview summary ↔ first-level all-study design-precedent comparison.

Root-cause RED family for FR20 on portal C:

- homepage keeps an independent problem summary
- ``?view=comparison`` must activate the existing source-comparison /
  matrix-query surface (keyword + selected-study columns + full clauses)
- not a second framework and not a bare link to the raw long table

Calls ordinary production renderer helpers and the real ``report-c.js`` startup
inside a Node DOM harness. Synthetic fixture bytes are not clinical or
browser-pixel acceptance.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from ci_workflow.renderers.portal import report_c

ROOT = Path(__file__).resolve().parents[2]
REPORT_DATA = ROOT / "fixtures/positive/c-atopic-dermatitis/inputs/report-data.json"
ASSET_JS = ROOT / "src/ci_workflow/renderers/portal/assets/report-c.js"
ASSET_CSS = ROOT / "src/ci_workflow/renderers/portal/assets/report-c.css"
BASE_TMPL = ROOT / "src/ci_workflow/renderers/portal/templates/c/base.html.j2"
PAGE_TMPL = ROOT / "src/ci_workflow/renderers/portal/templates/c/page.html.j2"
PAGE_ID = "overview"
SEARCH_QUERY = "EASI"
SAFE_MARKER = "<script>bad-source</script>"
LAST_ROW_ID = "c-nct05149313-statistical"
MISSING_STATE = "not_publicly_disclosed"

_DEDICATED_HARNESS = r"""
const fs = require("node:fs");
const vm = require("node:vm");
const data = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const initialSearch = process.argv[3] === undefined ? "?view=comparison" : process.argv[3];

function makeNode(tag) {
  const node = {
    tagName: String(tag || "div").toUpperCase(),
    children: [],
    attrs: {},
    style: {},
    className: "",
    parentNode: null,
    hidden: false,
    checked: false,
    disabled: false,
    value: "",
    type: "",
    textContent: "",
    classList: {
      add(name) { node.className = (node.className + " " + name).trim(); },
      remove(name) {
        node.className = node.className
          .split(/\s+/)
          .filter((item) => item && item !== name)
          .join(" ");
      },
      contains(name) {
        return node.className.split(/\s+/).filter(Boolean).includes(name);
      },
    },
    setAttribute(k, v) {
      node.attrs[k] = String(v);
      if (k === "class") node.className = String(v);
      if (k === "id") node.attrs.id = String(v);
    },
    getAttribute(k) {
      if (k === "class") return node.className || null;
      return Object.prototype.hasOwnProperty.call(node.attrs, k) ? node.attrs[k] : null;
    },
    removeAttribute(k) { delete node.attrs[k]; },
    appendChild(child) {
      if (child.parentNode) {
        child.parentNode.children = child.parentNode.children.filter((item) => item !== child);
      }
      child.parentNode = node;
      node.children.push(child);
      return child;
    },
    replaceChildren(...items) {
      node.children = [];
      items.forEach((item) => node.appendChild(item));
    },
    addEventListener(type, fn) { node.attrs["on:" + type] = fn; },
    querySelector(sel) { return queryAll(node, sel)[0] || null; },
    querySelectorAll(sel) { return enhance(queryAll(node, sel)); },
    closest(sel) {
      let cur = node;
      while (cur) {
        if (matches(cur, sel)) return cur;
        cur = cur.parentNode;
      }
      return null;
    },
  };
  Object.defineProperty(node, "id", {
    get() { return node.attrs.id || ""; },
    set(value) { node.attrs.id = String(value || ""); },
  });
  Object.defineProperty(node, "innerHTML", {
    get() { return ""; },
    set(value) {
      if (value === "") node.children = [];
    },
  });
  return node;
}

function enhance(list) {
  list.forEach = Array.prototype.forEach;
  list.map = Array.prototype.map;
  list.filter = Array.prototype.filter;
  list.find = Array.prototype.find;
  return list;
}

function matches(node, sel) {
  if (!node || !sel) return false;
  if (sel.startsWith("#")) return node.getAttribute("id") === sel.slice(1);
  const tagClassAttrEq = sel.match(
    /^([a-z0-9-]+)\.([a-z0-9_-]+)\[([^=\]]+)=["']?([^"'\]]+)["']?\]$/i
  );
  if (tagClassAttrEq) {
    return node.tagName === tagClassAttrEq[1].toUpperCase()
      && node.classList.contains(tagClassAttrEq[2])
      && node.getAttribute(tagClassAttrEq[3]) === tagClassAttrEq[4];
  }
  const tagClassAttr = sel.match(/^([a-z0-9-]+)\.([a-z0-9_-]+)\[([^\]]+)\]$/i);
  if (tagClassAttr) {
    return node.tagName === tagClassAttr[1].toUpperCase()
      && node.classList.contains(tagClassAttr[2])
      && node.getAttribute(tagClassAttr[3]) != null;
  }
  const tagClass = sel.match(/^([a-z0-9-]+)\.([a-z0-9_-]+)$/i);
  if (tagClass) {
    return node.tagName === tagClass[1].toUpperCase()
      && node.classList.contains(tagClass[2]);
  }
  const classAttrEq = sel.match(/^\.([a-z0-9_-]+)\[([^=\]]+)=["']?([^"'\]]+)["']?\]$/i);
  if (classAttrEq) {
    return node.classList.contains(classAttrEq[1])
      && node.getAttribute(classAttrEq[2]) === classAttrEq[3];
  }
  const classAttr = sel.match(/^\.([a-z0-9_-]+)\[([^\]]+)\]$/i);
  if (classAttr) {
    return node.classList.contains(classAttr[1]) && node.getAttribute(classAttr[2]) != null;
  }
  if (sel.startsWith(".")) return node.classList.contains(sel.slice(1));
  const attrEq = sel.match(/^([a-z0-9-]*)\[([^=\]]+)=["']?([^"'\]]+)["']?\]$/i);
  if (attrEq) {
    if (attrEq[1] && node.tagName !== attrEq[1].toUpperCase()) return false;
    return node.getAttribute(attrEq[2]) === attrEq[3];
  }
  const attr = sel.match(/^([a-z0-9-]*)\[([^\]]+)\]$/i);
  if (attr) {
    if (attr[1] && node.tagName !== attr[1].toUpperCase()) return false;
    return node.getAttribute(attr[2]) != null;
  }
  if (/^[a-z0-9-]+$/i.test(sel)) return node.tagName === sel.toUpperCase();
  return false;
}

function queryAll(root, sel) {
  if (sel.includes(" ")) {
    const parts = sel.trim().split(/\s+/);
    let frontier = [root];
    parts.forEach((part) => {
      const next = [];
      frontier.forEach((node) => {
        (function walk(n) {
          if (n !== node && matches(n, part)) next.push(n);
          (n.children || []).forEach(walk);
        })(node);
      });
      frontier = next;
    });
    return frontier;
  }
  const out = [];
  (function walk(node) {
    if (matches(node, sel)) out.push(node);
    (node.children || []).forEach(walk);
  })(root);
  return out;
}

function makeDocument() {
  const doc = makeNode("document");
  doc.body = makeNode("body");
  doc.documentElement = makeNode("html");
  doc.documentElement.appendChild(doc.body);
  doc.appendChild(doc.documentElement);
  doc.readyState = "complete";
  doc.createElement = makeNode;
  doc.createTextNode = (text) => {
    const node = makeNode("#text");
    node.textContent = String(text || "");
    return node;
  };
  doc.getElementById = (id) => queryAll(doc, "#" + id)[0] || null;
  doc.querySelector = (sel) => queryAll(doc, sel)[0] || null;
  doc.querySelectorAll = (sel) => enhance(queryAll(doc, sel));
  doc.addEventListener = () => {};
  return doc;
}

function makeWindow(doc) {
  const timers = [];
  let href = "https://example.test/overview.html";
  let search = "";
  const win = {
    document: doc,
    location: {
      get href() { return href + search; },
      set href(next) {
        const url = new URL(String(next), "https://example.test/");
        href = url.origin + url.pathname;
        search = url.search;
      },
      get search() { return search; },
      set search(next) { search = next || ""; },
      hash: "",
    },
    history: {
      replaceState(_, __, next) {
        const url = new URL(String(next), "https://example.test/overview.html");
        href = url.origin + url.pathname;
        search = url.search;
      },
    },
    echarts: {
      init() {
        win.__ECHARTS_INIT_COUNT__ = (win.__ECHARTS_INIT_COUNT__ || 0) + 1;
        throw new Error("echarts blocked");
      },
    },
    __ECHARTS_INIT_COUNT__: 0,
    addEventListener() {},
    setTimeout(fn) { timers.push(fn); return timers.length; },
    clearTimeout() {},
    _flushTimers() { while (timers.length) timers.shift()(); },
    URL, URLSearchParams, console,
  };
  doc.defaultView = win;
  win.window = win;
  return win;
}

function buildSkeleton(doc, page) {
  const body = doc.body;
  body.className = "kz-c-site kz-c-site--overview";
  body.attrs = {};
  body.setAttribute = function (k, v) { this.attrs[k] = String(v); };
  body.getAttribute = function (k) {
    return Object.prototype.hasOwnProperty.call(this.attrs, k) ? this.attrs[k] : null;
  };
  const head = body.appendChild(doc.createElement("header"));
  head.className = "kz-c-page-head";
  const taskTitle = head.appendChild(doc.createElement("h1"));
  taskTitle.setAttribute("data-c-task-title", "");
  taskTitle.textContent = "首页";
  const homeNav = body.appendChild(doc.createElement("a"));
  homeNav.setAttribute("data-c-summary-nav", "");
  homeNav.setAttribute("aria-current", "page");
  const conclusions = doc.createElement("section");
  conclusions.className = "kz-b-conclusions";
  conclusions.setAttribute("data-c-summary-only", "");
  conclusions.textContent = "核心结论";
  body.appendChild(conclusions);
  const entry = doc.createElement("section");
  entry.className = "kz-c-comparison-entry";
  const action = doc.createElement("a");
  action.setAttribute("data-c-enter-comparison", "");
  action.setAttribute("href", "overview.html?view=comparison");
  action.textContent = "打开全研究横比";
  entry.appendChild(action);
  body.appendChild(entry);
  const panel = doc.createElement("details");
  panel.setAttribute("id", "kz-filter-panel");
  const filterSummary = doc.createElement("span");
  filterSummary.setAttribute("data-filter-summary", "");
  panel.appendChild(filterSummary);
  const filterStatus = doc.createElement("span");
  filterStatus.setAttribute("data-filter-status", "");
  panel.appendChild(filterStatus);
  const reset = doc.createElement("button");
  reset.setAttribute("type", "button");
  reset.setAttribute("data-filter-reset", "");
  panel.appendChild(reset);
  body.appendChild(panel);
  const workbenchTools = doc.createElement("div");
  workbenchTools.className = "kz-c-section-heading";
  body.appendChild(workbenchTools);
  const module = doc.createElement("div");
  module.setAttribute("id", "kz-chart-module");
  const visuals = doc.createElement("div");
  visuals.setAttribute("id", "kz-c-chart-visuals");
  module.appendChild(visuals);
  const matrix = doc.createElement("section");
  matrix.className = "kz-c-design-matrix-section";
  matrix.textContent = "研究 × 设计要素横向矩阵";
  module.appendChild(matrix);
  const table = doc.createElement("table");
  table.className = "kz-chart-table";
  const tbody = doc.createElement("tbody");
  page.table_rows.forEach((row) => {
    const tr = doc.createElement("tr");
    tr.className = "kz-chart-table__row";
    tr.setAttribute("data-row-id", String(row.row_id));
    tr.setAttribute("data-trial-id", String(row.trial_id || ""));
    tr.setAttribute("data-product-id", String(row.product_id || ""));
    const td = doc.createElement("td");
    td.className = "kz-chart-table__cell";
    td.setAttribute("data-evidence-open", String(row.row_id));
    td.textContent = String(row.value == null ? "" : row.value);
    tr.appendChild(td);
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  module.appendChild(table);
  body.appendChild(module);
}

function dispatch(node, event) {
  const fn = node.attrs && node.attrs["on:" + event.type];
  if (typeof fn === "function") fn(event);
}

function runContext(search, page) {
  const doc = makeDocument();
  buildSkeleton(doc, page);
  const win = makeWindow(doc);
  win.location.search = search;
  win.__CHART_GROUPS__ = page.chart_groups;
  win.__C_ROW_DIMENSIONS__ = page.row_dimensions;
  win.__C_FILTER_DIMENSIONS__ = page.filter_dimensions;
  win.__C_PAGE_ID__ = page.page_id;
  win.__C_PAGE_TITLE__ = "首页";
  win.__C_SITE_PREFIX__ = "";
  win.__PRESENTATION_PLAN__ = function () {
    throw new Error("comparison view must not fall back to ECharts presentation");
  };
  vm.runInNewContext(
    fs.readFileSync(page.asset_path, "utf8"),
    {
      window: win,
      document: doc,
      URL,
      URLSearchParams,
      console,
      setTimeout: win.setTimeout,
      clearTimeout: win.clearTimeout,
    },
    { filename: page.asset_path }
  );
  win._flushTimers();
  return { doc, win };
}

function collectText(node) {
  let text = node.textContent || "";
  (node.children || []).forEach((child) => { text += collectText(child); });
  return text;
}

function snapshot(ctx) {
  const doc = ctx.doc;
  const defs = doc.querySelectorAll("[data-criterion-row-id]").map((node) => {
    const evidence = node.querySelectorAll("[data-evidence-open]");
    const original = node.querySelector(".kz-c-criteria-original");
    const revision = node.querySelector(".kz-c-criteria-revision");
    const summary = node.querySelector("summary");
    const scripts = node.querySelectorAll("script");
    return {
      row_id: node.getAttribute("data-criterion-row-id"),
      ordinal: node.getAttribute("data-criterion-ordinal"),
      trial_id: node.getAttribute("data-criterion-trial-id"),
      product_id: node.getAttribute("data-criterion-product-id"),
      current_state: node.getAttribute("data-criterion-current-state") || "",
      review_state: node.getAttribute("data-criterion-review-state") || "",
      disclosure_state: node.getAttribute("data-criterion-disclosure-state") || "",
      summary: summary ? collectText(summary) : null,
      text: collectText(node),
      original_text: original ? collectText(original) : null,
      revision_text: revision ? collectText(revision) : null,
      evidence_count: evidence.length,
      evidence_row_id: evidence.length ? evidence[0].getAttribute("data-evidence-open") : null,
      has_summary: Boolean(summary),
      script_child_count: scripts.length,
    };
  });
  const visibleTableRows = doc.querySelectorAll(".kz-chart-table__row[data-row-id]")
    .filter((node) => node.style.display !== "none")
    .map((node) => node.getAttribute("data-row-id"));
  const tables = doc.querySelectorAll("table.kz-c-criteria-table");
  const title = doc.querySelector(".kz-c-chart-title");
  const search = doc.getElementById("kz-c-criteria-search");
  const status = doc.querySelector(".kz-c-criteria-status");
  const last = doc.querySelector('[data-criterion-row-id="' + data.last_row_id + '"]');
  return {
    table_count: tables.length,
    table_present: tables.length === 1,
    study_headers: doc.querySelectorAll("[data-criteria-study]").map((node) => ({
      trial_id: node.getAttribute("data-criteria-study"),
      scope: node.getAttribute("scope"),
      text: collectText(node),
    })),
    ordinal_row_headers: doc.querySelectorAll("table.kz-c-criteria-table th[scope=row]")
      .map((node) => collectText(node)),
    status_text: status ? collectText(status) : "",
    search_value: search ? search.value : null,
    checkboxes: doc.querySelectorAll(".kz-c-criteria-choices input").map((node) => ({
      value: node.value,
      checked: node.checked,
    })),
    defs,
    visible_table_rows: visibleTableRows,
    url_search: ctx.win.location.search,
    title_text: title ? collectText(title) : "",
    echarts_calls: ctx.win.__ECHARTS_INIT_COUNT__ || 0,
    last_reachable: Boolean(last && last.querySelector(".kz-c-criteria-original")),
    body_view: doc.body.getAttribute("data-c-view"),
    task_title: collectText(doc.querySelector("[data-c-task-title]")),
    summary_hidden: doc.querySelector("[data-c-summary-only]").hidden,
    summary_nav: doc.querySelector("[data-c-summary-nav]").getAttribute("aria-current"),
    advanced_filter_parent: doc.getElementById("kz-filter-panel").parentNode.className,
  };
}

function searchFor(ctx, value) {
  const input = ctx.doc.getElementById("kz-c-criteria-search");
  if (!input) throw new Error("missing #kz-c-criteria-search");
  input.value = value;
  dispatch(input, { type: "input" });
  ctx.win._flushTimers();
}

function setStudyChecked(ctx, trialId, checked) {
  const box = ctx.doc.querySelectorAll(".kz-c-criteria-choices input")
    .find((item) => item.value === trialId);
  if (!box) throw new Error("missing study checkbox " + trialId);
  box.checked = checked;
  dispatch(box, { type: "change" });
  ctx.win._flushTimers();
}

const out = { ok: true, snapshots: {} };
try {
  const A = runContext(initialSearch, data);
  out.snapshots.initial = snapshot(A);
  if (initialSearch === "") {
    process.stdout.write(JSON.stringify(out));
    process.exit(0);
  }
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
    "?view=comparison&criteria_q=" + encodeURIComponent(data.search_query)
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


def _overview_payload() -> dict[str, Any]:
    data = report_c.ReportCPortalData.model_validate_json(REPORT_DATA.read_bytes())
    observations = report_c._page_observations(data, PAGE_ID)
    groups = json.loads(
        report_c._json(report_c._chart_groups(data, observations, page_id=PAGE_ID, title="首页"))
    )
    table_rows = json.loads(
        report_c._json(report_c._table_rows(data, observations, page_id=PAGE_ID))
    )
    _, dimensions = report_c._filter_dimensions_for_rows(data, observations)
    rows = [dict(row) for row in groups[0]["rows"]]
    assert rows, "overview must project design observations"
    assert rows[-1]["row_id"] == LAST_ROW_ID

    rows[0] = dict(rows[0])
    rows[0]["source_text"] = SAFE_MARKER + " complete clause body"
    rows[0]["value"] = SAFE_MARKER
    rows[0]["review_state"] = "user_modified"
    cleared = dict(rows[1])
    cleared["disclosure_state"] = "user_cleared"
    cleared["value"] = None
    rows[1] = cleared
    missing = next(row for row in rows if row["disclosure_state"] == MISSING_STATE)
    numeric = next(row for row in rows if row.get("numeric_value") is not None)
    groups[0]["rows"] = rows
    return {
        "asset_path": str(ASSET_JS),
        "page_id": PAGE_ID,
        "chart_groups": groups,
        "table_rows": table_rows,
        "row_dimensions": json.loads(report_c._json(dimensions)),
        "filter_dimensions": json.loads(report_c._json(tuple(report_c._FILTER_DIMENSION_LABELS))),
        "first_trial": str(rows[0]["trial_display_id"]),
        "search_query": SEARCH_QUERY,
        "ordinal_query": "no-clause-should-match-this-1007-control-token",
        "safe_row_id": str(rows[0]["row_id"]),
        "cleared_row_id": str(cleared["row_id"]),
        "missing_row_id": str(missing["row_id"]),
        "numeric_row_id": str(numeric["row_id"]),
        "last_row_id": LAST_ROW_ID,
        "last_source_text": str(rows[-1].get("source_text") or "").strip(),
        "all_row_ids": [str(row["row_id"]) for row in rows],
    }


def _run_harness(tmp_path: Path, payload: dict[str, Any], *, search: str) -> dict[str, Any]:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node DOM harness unavailable for C workspace JS family")
    harness_path = tmp_path / "harness.cjs"
    harness_path.write_text(_DEDICATED_HARNESS, encoding="utf-8")
    payload_path = tmp_path / "payload.json"
    original = json.dumps(payload, ensure_ascii=False).encode()
    payload_path.write_bytes(original)
    completed = subprocess.run(
        [node, str(harness_path), str(payload_path), search],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr + "\n" + completed.stdout[:4000]
    result = json.loads(completed.stdout)
    assert result.get("ok"), result.get("error")
    assert payload_path.read_bytes() == original
    return result


def _defs_by_row(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["row_id"]: item for item in snapshot["defs"]}


def _row_ids(snapshot: dict[str, Any]) -> list[str]:
    return [item["row_id"] for item in snapshot["defs"]]


@pytest.fixture(scope="module")
def payload() -> dict[str, Any]:
    return _overview_payload()


@pytest.fixture(scope="module")
def comparison_harness(
    tmp_path_factory: pytest.TempPathFactory, payload: dict[str, Any]
) -> dict[str, Any]:
    return _run_harness(
        tmp_path_factory.mktemp("c-1007-workspace"),
        payload,
        search="?view=comparison",
    )


def test_overview_summary_and_comparison_entry_are_distinct_renderer_tasks(
    tmp_path: Path,
) -> None:
    data = report_c.ReportCPortalData.model_validate_json(REPORT_DATA.read_bytes())
    site = tmp_path / "site"
    report_c.render_report_c_site(data, site)
    overview = (site / "overview.html").read_text(encoding="utf-8")

    assert "核心结论" in overview
    assert "比较范围" in overview
    assert re.search(r'href="[^"]*overview\.html\?view=comparison"', overview)
    assert "全研究横比" in overview
    assert "data-c-enter-comparison" in overview
    assert "data-c-comparison-nav" in overview
    assert "kz-c-comparison-entry" in overview

    base = BASE_TMPL.read_text(encoding="utf-8")
    page = PAGE_TMPL.read_text(encoding="utf-8")
    assert "data-c-comparison-nav" in base
    assert "comparison_href" in base
    assert "data-c-enter-comparison" in page
    assert "kz-c-comparison-entry" in page


def test_comparison_view_uses_source_comparison_not_echarts_or_raw_matrix_alone(
    payload: dict[str, Any], comparison_harness: dict[str, Any]
) -> None:
    initial = comparison_harness["snapshots"]["initial"]
    assert initial["table_present"] is True
    assert initial["table_count"] == 1
    assert initial["search_value"] == ""
    assert sorted(_row_ids(initial)) == sorted(payload["all_row_ids"])
    assert initial["last_reachable"] is True
    assert initial["title_text"] == "全研究横比"
    assert initial["echarts_calls"] == 0
    assert initial["body_view"] == "comparison"
    # designMode rows are field labels (not the inclusion-criteria "登记原文" band).
    headers = "".join(initial["ordinal_row_headers"])
    assert "登记原文" not in headers
    assert "入选标准" in headers or "主要终点" in headers
    assert len(initial["study_headers"]) == 4


def test_comparison_has_one_task_heading_and_no_duplicate_summary(
    comparison_harness: dict[str, Any],
) -> None:
    initial = comparison_harness["snapshots"]["initial"]
    assert initial["task_title"] == "全研究横比"
    assert initial["summary_hidden"] is True
    assert initial["summary_nav"] == "false"
    assert initial["advanced_filter_parent"] == "kz-c-section-heading"
    # Matrix membership, source details and the return-summary link stay intact.
    assert initial["table_present"] and initial["last_reachable"]


def test_home_summary_does_not_render_long_clause_heatmap(
    tmp_path: Path, payload: dict[str, Any],
) -> None:
    result = _run_harness(tmp_path, payload, search="")
    initial = result["snapshots"]["initial"]
    assert initial["body_view"] == "summary"
    assert initial["summary_hidden"] is False
    assert initial["echarts_calls"] == 0
    assert initial["summary_nav"] == "page"


def test_empty_query_last_clause_study_reload_and_clear_states(
    payload: dict[str, Any], comparison_harness: dict[str, Any]
) -> None:
    snapshots = comparison_harness["snapshots"]
    defs = _defs_by_row(snapshots["initial"])
    assert payload["last_row_id"] in defs
    assert defs[payload["last_row_id"]]["original_text"] == payload["last_source_text"]
    assert defs[payload["last_row_id"]]["evidence_row_id"] == payload["last_row_id"]

    safe = defs[payload["safe_row_id"]]
    assert SAFE_MARKER in (safe["original_text"] or "")
    assert SAFE_MARKER in safe["text"]
    assert safe["script_child_count"] == 0
    assert safe["current_state"] == "user_modified"

    cleared = defs[payload["cleared_row_id"]]
    assert cleared["current_state"] == "user_cleared"
    assert "用户清除" in (cleared["revision_text"] or "")
    assert "None" not in cleared["text"]

    missing = defs[payload["missing_row_id"]]
    assert missing["disclosure_state"] == MISSING_STATE
    assert (missing["original_text"] or "").strip() != "0"

    numeric = defs[payload["numeric_row_id"]]
    assert numeric["evidence_row_id"] == payload["numeric_row_id"]
    assert numeric["has_summary"] is True

    assert snapshots["ordinal"]["defs"] == []
    assert "0" in snapshots["ordinal"]["status_text"]

    first = payload["first_trial"]
    unchecked = snapshots["unchecked"]
    assert first not in [item["trial_id"] for item in unchecked["study_headers"]]
    assert f"criteria_hide={first}" in unchecked["url_search"]

    restore = snapshots["restore"]
    assert restore["search_value"] == SEARCH_QUERY
    boxes = {item["value"]: item["checked"] for item in restore["checkboxes"]}
    assert boxes[first] is False
    assert "view=comparison" in restore["url_search"]


def test_personal_query_contract_exposes_criteria_keys_on_comparison_view(
    tmp_path: Path, payload: dict[str, Any]
) -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node DOM harness unavailable")
    probe = r"""
const fs = require("node:fs");
const vm = require("node:vm");
const assert = require("node:assert/strict");
const page = JSON.parse(fs.readFileSync(process.argv[1], "utf8"));
const source = fs.readFileSync(page.asset_path, "utf8");
function el() {
  return {
    children: [], style: {}, attrs: {}, classList: { add() {} },
    setAttribute(k,v){this.attrs[k]=String(v);}, getAttribute(k){return this.attrs[k]||null;},
    appendChild(c){this.children.push(c); return c;}, addEventListener(){},
    querySelector(){return null;}, querySelectorAll(){return [];}, textContent: "",
    replaceChildren(){this.children=[];},
  };
}
const body = el();
body.setAttribute = function(k,v){ this.attrs[k]=String(v); };
body.getAttribute = function(k){ return this.attrs[k] || null; };
body.attrs = {};
const doc = {
  body, documentElement: el(), readyState: "complete",
  createElement: el, getElementById(){return null;},
  querySelector(){return null;}, querySelectorAll(){return [];},
  addEventListener(){},
};
const win = {
  location: { href: "https://example.test/overview.html?view=comparison",
    search: "?view=comparison", hash: "" },
  history: { replaceState(){} },
  document: doc,
  __CHART_GROUPS__: page.chart_groups,
  __C_ROW_DIMENSIONS__: page.row_dimensions,
  __C_FILTER_DIMENSIONS__: page.filter_dimensions,
  __C_PAGE_ID__: "overview",
  __C_PAGE_TITLE__: "首页",
  __C_SITE_PREFIX__: "",
  echarts: { init(){ throw new Error("no echarts"); } },
  addEventListener(){},
  setTimeout(fn){ fn(); return 1; },
  clearTimeout(){},
  URL, URLSearchParams, console,
};
doc.defaultView = win; win.window = win;
vm.runInNewContext(source, {window: win, document: doc, URL, URLSearchParams, console,
  setTimeout: win.setTimeout, clearTimeout: win.clearTimeout}, {filename: page.asset_path});
const values = win.__C_PERSONAL_QUERY_VALUES__();
assert.ok(Object.prototype.hasOwnProperty.call(values, "criteria_q"));
assert.ok(Object.prototype.hasOwnProperty.call(values, "criteria_hide"));
assert.ok(values.criteria_hide[page.first_trial]);
process.stdout.write(JSON.stringify({ok:true}));
"""
    payload_path = tmp_path / "personal-payload.json"
    payload_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    result = subprocess.run(
        ["node", "-e", probe, str(payload_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["ok"] is True


def test_css_keeps_comparison_reading_floor_and_hides_summary_matrix_in_comparison_view() -> None:
    css = ASSET_CSS.read_text(encoding="utf-8")
    js = ASSET_JS.read_text(encoding="utf-8")
    assert "全研究横比" in js
    assert "wantsFullStudyComparison" in js or 'get("view") === "comparison"' in js
    assert ".kz-c-comparison-entry" in css
    assert ".kz-c-site[data-c-view=" in css
    assert re.search(
        r"\.kz-c-criteria-table__cell\s*\{[^}]*font-size:\s*1rem",
        css,
        re.S,
    )
