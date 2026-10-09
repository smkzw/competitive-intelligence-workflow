/* C 类门户联动：页面/模块筛选、URL 恢复、试验身份装饰；不计算科学事实。 */
(function () {
  "use strict";

  var started = false;
  var criteriaParams = new URLSearchParams(window.location.search || "");
  var criteriaSearchQuery = criteriaParams.get("criteria_q") || "";
  var excludedCriteriaTrials = {};
  criteriaParams.getAll("criteria_hide").forEach(function (trialId) {
    excludedCriteriaTrials[trialId] = true;
  });

  function writeCriteriaUrl() {
    var url = new URL(window.location.href);
    if (criteriaSearchQuery.trim()) url.searchParams.set("criteria_q", criteriaSearchQuery);
    else url.searchParams.delete("criteria_q");
    url.searchParams.delete("criteria_hide");
    Object.keys(excludedCriteriaTrials).sort().forEach(function (trialId) {
      if (excludedCriteriaTrials[trialId]) url.searchParams.append("criteria_hide", trialId);
    });
    window.history.replaceState({}, "", url.href);
  }

  function filterDimensions() {
    var declared = window.__C_FILTER_DIMENSIONS__ || [];
    var result = [];
    var seen = {};
    for (var i = 0; i < declared.length; i += 1) {
      var dimension = String(declared[i] || "");
      if (dimension && !seen[dimension]) {
        seen[dimension] = true;
        result.push(dimension);
      }
    }
    var buttons = document.querySelectorAll("button[data-filter-dimension]");
    for (var j = 0; j < buttons.length; j += 1) {
      var buttonDimension = buttons[j].getAttribute("data-filter-dimension") || "";
      if (buttonDimension && !seen[buttonDimension]) {
        seen[buttonDimension] = true;
        result.push(buttonDimension);
      }
    }
    return result;
  }

  function valuesFor(params, key) {
    var values = params.getAll(key);
    var result = [];
    var seen = {};
    for (var i = 0; i < values.length; i += 1) {
      var value = String(values[i] || "");
      if (value && !seen[value]) {
        seen[value] = true;
        result.push(value);
      }
    }
    return result;
  }

  function selectedState() {
    var params = new URLSearchParams(window.location.search || "");
    var state = {};
    var dimensions = filterDimensions();
    for (var i = 0; i < dimensions.length; i += 1) {
      state[dimensions[i]] = valuesFor(params, dimensions[i]);
    }
    return state;
  }

  function knownValues(dimension) {
    var buttons = document.querySelectorAll(
      'button[data-filter-dimension="' + dimension + '"][data-filter-value]'
    );
    var values = {};
    for (var i = 0; i < buttons.length; i += 1) {
      values[buttons[i].getAttribute("data-filter-value")] = true;
    }
    return values;
  }

  function sanitizeState(state) {
    var result = {};
    var dimensions = filterDimensions();
    for (var i = 0; i < dimensions.length; i += 1) {
      var dimension = dimensions[i];
      var known = knownValues(dimension);
      var values = state[dimension] || [];
      result[dimension] = [];
      for (var j = 0; j < values.length; j += 1) {
        if (known[values[j]]) result[dimension].push(values[j]);
      }
    }
    return result;
  }

  function applyButtonState(state) {
    var buttons = document.querySelectorAll(
      "button[data-filter-dimension][data-filter-value]"
    );
    for (var i = 0; i < buttons.length; i += 1) {
      var dimension = buttons[i].getAttribute("data-filter-dimension");
      var value = buttons[i].getAttribute("data-filter-value");
      var selected = state[dimension] || [];
      var active = selected.indexOf(value) !== -1;
      buttons[i].setAttribute("aria-pressed", active ? "true" : "false");
    }
  }

  function rowDimensions(rowId) {
    var all = window.__C_ROW_DIMENSIONS__ || {};
    return all[String(rowId)] || {};
  }

  function rowRecord(rowId) {
    var groups = window.__CHART_GROUPS__ || [];
    for (var i = 0; i < groups.length; i += 1) {
      var rows = groups[i].rows || [];
      for (var j = 0; j < rows.length; j += 1) {
        if (String(rows[j].row_id) === String(rowId)) return rows[j];
      }
    }
    return null;
  }

  function decorateRows() {
    var pageTrialMarker = document.querySelector(".kz-c-page-head[data-trial-id]");
    var rows = document.querySelectorAll(".kz-chart-table__row[data-row-id]");
    for (var i = 0; i < rows.length; i += 1) {
      var rowId = rows[i].getAttribute("data-row-id");
      var record = rowRecord(rowId) || {};
      var dimensions = rowDimensions(rowId);
      if (record.trial_id && !pageTrialMarker) {
        rows[i].setAttribute("data-trial-id", String(record.trial_id));
      }
      if (record.product_id) {
        rows[i].setAttribute("data-product-id", String(record.product_id));
      }
      var keys = Object.keys(dimensions);
      for (var j = 0; j < keys.length; j += 1) {
        if (dimensions[keys[j]]) {
          rows[i].setAttribute("data-filter-" + keys[j], dimensions[keys[j]]);
        }
      }
    }
  }

  function matches(rowId, state) {
    var dimensions = rowDimensions(rowId);
    var keys = filterDimensions();
    for (var i = 0; i < keys.length; i += 1) {
      var selected = state[keys[i]] || [];
      if (selected.length && selected.indexOf(dimensions[keys[i]] || "") === -1) {
        return false;
      }
    }
    return true;
  }

  function visibleRowIds() {
    var rows = document.querySelectorAll(".kz-chart-table__row[data-row-id]");
    var result = [];
    for (var i = 0; i < rows.length; i += 1) {
      if (rows[i].style.display !== "none") {
        result.push(rows[i].getAttribute("data-row-id"));
      }
    }
    return result;
  }
  function selectedCount(state) {
    var keys = filterDimensions();
    var count = 0;
    for (var i = 0; i < keys.length; i += 1) {
      count += (state[keys[i]] || []).length;
    }
    return count;
  }

  function matrixCellRowIds(cell) {
    var raw = cell.getAttribute("data-row-ids") || "";
    return raw.split(/\s+/).filter(Boolean);
  }

  function matrixCellMatches(cell, state) {
    var rowIds = matrixCellRowIds(cell);
    if (!rowIds.length) return selectedCount(state) === 0;
    for (var i = 0; i < rowIds.length; i += 1) {
      if (matches(rowIds[i], state)) return true;
    }
    return false;
  }

  function applyMatrixState(state) {
    var cells = document.querySelectorAll("[data-matrix-cell]");
    for (var i = 0; i < cells.length; i += 1) {
      cells[i].style.display = matrixCellMatches(cells[i], state) ? "" : "none";
    }
    var rows = document.querySelectorAll("[data-matrix-field-row]");
    for (var j = 0; j < rows.length; j += 1) {
      var visibleCell = rows[j].querySelector("[data-matrix-cell]:not([style*='display: none'])");
      var body = rows[j].closest("[data-matrix-group]");
      var collapsed = body && body.getAttribute("data-matrix-collapsed") === "true";
      rows[j].style.display = visibleCell && !collapsed ? "" : "none";
    }
    var groups = document.querySelectorAll("[data-matrix-group]");
    for (var g = 0; g < groups.length; g += 1) {
      var groupRows = groups[g].querySelectorAll("[data-matrix-field-row]");
      var hasVisibleRow = false;
      for (var r = 0; r < groupRows.length; r += 1) {
        var groupCell = groupRows[r].querySelector("[data-matrix-cell]:not([style*='display: none'])");
        if (groupCell) {
          hasVisibleRow = true;
          break;
        }
      }
      var groupHeader = groups[g].querySelector("[data-matrix-group-row]");
      if (groupHeader) groupHeader.style.display = hasVisibleRow ? "" : "none";
    }
    var headers = document.querySelectorAll("th[data-matrix-trial]");
    for (var h = 0; h < headers.length; h += 1) {
      var trialId = headers[h].getAttribute("data-matrix-trial");
      var visibleTrialCell = document.querySelector(
        '[data-matrix-cell][data-matrix-trial="' + trialId + '"]:not([style*="display: none"])'
      );
      headers[h].style.display = visibleTrialCell ? "" : "none";
    }
  }

  function updateStatus(state) {
    var keys = filterDimensions();
    var selected = 0;
    for (var i = 0; i < keys.length; i += 1) {
      selected += (state[keys[i]] || []).length;
    }
    var summary = document.querySelector("[data-filter-summary]");
    if (summary) {
      summary.textContent = selected ? "已选 " + selected + " 项" : "未设置筛选";
    }
    var status = document.querySelector("[data-filter-status]");
    if (!status) return;
    var visible = visibleRowIds().length;
    var criteriaActive = usesSourceComparison(window.__C_PAGE_ID__ || "") &&
      (criteriaSearchQuery.trim() || Object.keys(excludedCriteriaTrials).some(function (trialId) {
        return excludedCriteriaTrials[trialId];
      }));
    status.textContent = selected
      ? "已选 " + selected + " 项，显示 " + visible + " 条记录"
      : criteriaActive
        ? "显示当前检索记录（" + visible + " 条）"
        : "显示全部可用记录（" + visible + " 条）";
  }

  function applyState(state) {
    var rows = document.querySelectorAll(".kz-chart-table__row[data-row-id]");
    for (var i = 0; i < rows.length; i += 1) {
      var rowId = rows[i].getAttribute("data-row-id");
      var show = matches(rowId, state);
      rows[i].style.display = show ? "" : "none";
    }
    // 独立复核修复：设计矩阵/明细表按 data-product-id / data-trial-id 联动显隐
    var productFilter = state["product"] || [];
    var trialFilter = state["trial"] || [];
    if (productFilter.length || trialFilter.length) {
      var keyed = document.querySelectorAll("[data-product-id], [data-trial-id]");
      for (var k = 0; k < keyed.length; k += 1) {
        var el = keyed[k];
        // A row's complete query result is authoritative. A second product/
        // trial-only pass must not restore null-product or other-axis misses.
        var keyedRowId = el.getAttribute("data-row-id");
        if (keyedRowId) {
          el.style.display = matches(keyedRowId, state) ? "" : "none";
          continue;
        }
        var pid = el.getAttribute("data-product-id");
        var tid = el.getAttribute("data-trial-id");
        var show = true;
        if (productFilter.length && pid !== null) {
          show = productFilter.indexOf(pid) !== -1;
        }
        if (show && trialFilter.length && tid) {
          show = trialFilter.indexOf(tid) !== -1;
        }
        el.style.display = show ? "" : "none";
      }
    } else {
      // 独立视觉复核（v60 interaction）：当其他维度（如 element）有筛选时，
      // 不重置 keyed 元素——重置会覆盖 element 维度的行隐藏效果
      var hasOtherFilter = false;
      var allKeys = filterDimensions();
      for (var fi = 0; fi < allKeys.length; fi++) {
        var fk = allKeys[fi];
        if (fk !== "product" && fk !== "trial" && state[fk] && state[fk].length) {
          hasOtherFilter = true;
          break;
        }
      }
      if (!hasOtherFilter) {
        var keyed2 = document.querySelectorAll('[data-product-id][style], [data-trial-id][style]');
        for (var r = 0; r < keyed2.length; r += 1) keyed2[r].style.display = "";
      }
    }
    applyMatrixState(state);
    if (
      window.__CHART_SYNC__ &&
      typeof window.__CHART_SYNC__.syncWithFilter === "function"
    ) {
      window.__CHART_SYNC__.syncWithFilter();
    }
    updateChartFromState(state);
    updateStatus(state);
  }

  // 独立视觉复核（v57 charts_tables）：筛选变化后按状态重绘 ECharts——
  // 此前只过滤表格行，图表 series 恒不更新
  function updateChartFromState(state) {
    if (!cChart) return;
    var visible = chartState.rows.filter(function (row) {
      return matches(String(row.row_id), state);
    });
    if (!visible.length) {
      cChart.clear();
      if (chartState.chart && !chartState.emptyNote) {
        var emptyNote = document.createElement("p");
        emptyNote.className = "kz-c-evidence-hint";
        emptyNote.textContent = "当前筛选无匹配记录；调整或清除筛选后可重新查看。";
        chartState.chart.appendChild(emptyNote);
        chartState.emptyNote = emptyNote;
      }
      return;
    }
    if (chartState.emptyNote) {
      chartState.emptyNote.remove();
      chartState.emptyNote = null;
    }
    var kind = chartState.kind;
    var option = kind === "sample-size-bar" ? sampleOption(visible)
      : kind === "criteria-comparison" ? criteriaCountOption(visible)
      : kind === "visit-timeline" ? timelineOption(visible)
      : kind === "evidence-coverage" ? evidenceOption(visible)
      : matrixOption(visible, kind, chartState.chart && chartState.chart.clientWidth ? chartState.chart.clientWidth : 900);
    if (option && option.__no_discrimination) {
      cChart.clear();
      var host2 = chartState.chart;
      if (host2) {
        host2.innerHTML = "";
        var note = document.createElement("p");
        note.className = "kz-c-evidence-hint";
        note.textContent = option._note;
        host2.appendChild(note);
      }
      return;
    }
    cChart.setOption(option, true);
  }

  function writeFilterUrl(state) {
    var url = new URL(window.location.href);
    var dimensions = filterDimensions();
    for (var i = 0; i < dimensions.length; i += 1) {
      url.searchParams.delete(dimensions[i]);
    }
    for (var d = 0; d < dimensions.length; d += 1) {
      var dimension = dimensions[d];
      var values = state[dimension] || [];
      for (var j = 0; j < values.length; j += 1) {
        url.searchParams.append(dimension, values[j]);
      }
    }
    url.hash = "";
    window.history.replaceState({}, "", url.href);
  }

  function writeFocusUrl(rowId) {
    var url = new URL(window.location.href);
    if (rowId) url.searchParams.set("focus", String(rowId));
    else url.searchParams.delete("focus");
    url.hash = "";
    window.history.replaceState({}, "", url.href);
  }

  function bindFilterButtons() {
    var buttons = document.querySelectorAll(
      "button[data-filter-dimension][data-filter-value]"
    );
    for (var i = 0; i < buttons.length; i += 1) {
      (function (button) {
        button.addEventListener("click", function () {
          var state = selectedState();
          var dimension = button.getAttribute("data-filter-dimension");
          var value = button.getAttribute("data-filter-value");
          if (!state[dimension]) state[dimension] = [];
          var index = state[dimension].indexOf(value);
          if (index === -1) state[dimension].push(value);
          else state[dimension].splice(index, 1);
          applyButtonState(state);
          applyState(state);
          // 独立复核：延迟重跑确保最终行显隐状态正确（其他 handler 可能
          // 修改行可见性），防止覆盖
          setTimeout(function() { applyState(state); }, 0);
          writeFilterUrl(state);
        });
      })(buttons[i]);
    }
    var reset = document.querySelector("[data-filter-reset]");
    if (reset) {
      reset.addEventListener("click", function () {
        var state = {};
        var dimensions = filterDimensions();
        for (var i = 0; i < dimensions.length; i += 1) state[dimensions[i]] = [];
        applyButtonState(state);
        applyState(state);
        writeFilterUrl(state);
      });
    }
  }
  function bindMatrixGroupToggles() {
    var toggles = document.querySelectorAll("[data-matrix-group-toggle]");
    for (var i = 0; i < toggles.length; i += 1) {
      (function (toggle) {
        toggle.addEventListener("click", function () {
          var groupId = toggle.getAttribute("data-matrix-group-toggle") || "";
          var group = document.querySelector('[data-matrix-group="' + groupId + '"]');
          if (!group) return;
          var collapsed = group.getAttribute("data-matrix-collapsed") === "true";
          group.setAttribute("data-matrix-collapsed", collapsed ? "false" : "true");
          toggle.setAttribute("aria-expanded", collapsed ? "true" : "false");
          applyMatrixState(selectedState());
        });
      })(toggles[i]);
    }
  }

  function bindEvidenceTriggers() {
    document.addEventListener("click", function (event) {
      var trigger = event.target && event.target.closest
        ? event.target.closest("[data-evidence-open]")
        : null;
      if (!trigger) return;
      var rowId = trigger.getAttribute("data-evidence-open");
      var drawer = window.__EVIDENCE_DRAWER__;
      if (rowId && drawer && typeof drawer.openByRowId === "function") {
        event.preventDefault();
        drawer.openByRowId(rowId, trigger);
      }
    });
  }

  function restoreFocusFromUrl() {
    var params = new URLSearchParams(window.location.search || "");
    var focus = params.get("focus");
    var api = window.__EVIDENCE_DRAWER__;
    if (!focus || !api || typeof api.hasView !== "function" || !api.hasView(focus)) {
      return;
    }
    window.setTimeout(function () {
      if (window.__EVIDENCE_DRAWER__ && window.__EVIDENCE_DRAWER__.hasView(focus)) {
        window.__EVIDENCE_DRAWER__.openByRowId(focus, null);
      }
    }, 0);
  }

  function removeSharedHash() {
    if (!window.location.hash) return;
    var url = new URL(window.location.href);
    url.hash = "";
    window.history.replaceState({}, "", url.href);
  }

  var cChart = null;
  var sharedPresentationPlan = window.__PRESENTATION_PLAN__;
  var chartState = {rows: [], kind: "", chart: null};
  var chartContainerWidth = 0;

  function uniqueValues(rows, key) {
    var values = [];
    var seen = {};
    for (var i = 0; i < rows.length; i += 1) {
      var value = String(rows[i][key] || "未列示");
      if (!seen[value]) {
        seen[value] = true;
        values.push(value);
      }
    }
    return values;
  }

  function allChartRows() {
    var groups = window.__CHART_GROUPS__ || [];
    var rows = [];
    for (var i = 0; i < groups.length; i += 1) {
      var groupRows = groups[i].rows || [];
      for (var j = 0; j < groupRows.length; j += 1) rows.push(groupRows[j]);
    }
    return rows;
  }

  function visibleChartRows() {
    var visible = {};
    var tableRows = document.querySelectorAll(".kz-chart-table__row[data-row-id]");
    for (var i = 0; i < tableRows.length; i += 1) {
      if (tableRows[i].style.display !== "none") {
        visible[tableRows[i].getAttribute("data-row-id")] = true;
      }
    }
    return allChartRows().filter(function (row) {
      return visible[String(row.row_id)];
    });
  }

  function chartKind(pageId) {
    if (pageId === "trial-profile") return "core-design-matrix";
    if (pageId.indexOf("trial-") === 0) return "trial-design-summary";
    if (pageId === "overview") return "core-design-matrix";
    if (pageId === "design-map") return "core-design-matrix";
    if (pageId === "sample-analysis-statistics") return "sample-size-bar";
    if (pageId === "visit-duration-followup") return "visit-timeline";
    if (pageId === "endpoint-timepoint-matrix") return "endpoint-timepoint-matrix";
    if (pageId === "treatment-arms") return "treatment-structure-matrix";
    if (pageId === "design-patterns") return "design-choice-matrix";
    if (
      pageId === "population-disease-definition" ||
      pageId === "inclusion-criteria" ||
      pageId === "exclusion-criteria"
    ) return "criteria-comparison";
    return "design-fact-matrix";
  }

  function wantsFullStudyComparison(pageId) {
    // FR20 first-level all-study design-precedent comparison lives on the C
    // homepage as a distinct task from the independent summary bullets.
    pageId = pageId || window.__C_PAGE_ID__ || "";
    if (pageId !== "overview") return false;
    return new URLSearchParams(window.location.search || "").get("view") === "comparison";
  }

  function usesSourceComparison(pageId) {
    pageId = pageId || window.__C_PAGE_ID__ || "";
    if (wantsFullStudyComparison(pageId)) return true;
    return pageId === "inclusion-criteria" || pageId === "exclusion-criteria" ||
      pageId === "endpoint-timepoint-matrix" || pageId === "population-disease-definition" ||
      pageId === "treatment-arms" || pageId === "sample-analysis-statistics" ||
      chartKind(pageId) === "design-fact-matrix" ||
      chartKind(pageId) === "trial-design-summary";
  }

  function syncComparisonChrome() {
    var active = wantsFullStudyComparison();
    if (document.body && document.body.setAttribute) {
      document.body.setAttribute("data-c-view", active ? "comparison" : "summary");
    }
    var nav = document.querySelector("[data-c-comparison-nav]");
    if (nav) {
      nav.setAttribute("aria-current", active ? "page" : "false");
      if (active) nav.classList.add("site-header__nav-item--active");
      else nav.classList.remove("site-header__nav-item--active");
    }
    if (window.__C_PAGE_ID__ === "overview") {
      var summaryTitle = window.__C_PAGE_TITLE__ || "首页";
      var taskTitle = document.querySelector("[data-c-task-title]");
      if (taskTitle) taskTitle.textContent = active ? "全研究横比" : summaryTitle;
      var summaryOnly = document.querySelectorAll("[data-c-summary-only]");
      for (var i = 0; i < summaryOnly.length; i += 1) summaryOnly[i].hidden = active;
      var summaryNav = document.querySelector("[data-c-summary-nav]");
      if (summaryNav) {
        summaryNav.setAttribute("aria-current", active ? "false" : "page");
        if (active) summaryNav.classList.remove("site-header__nav-item--active");
        else summaryNav.classList.add("site-header__nav-item--active");
      }
      var lead = document.querySelector("[data-c-task-lead]");
      if (lead) lead.textContent = active
        ? "检索设计条款、选择研究并列核对；已知差异与未解项保留，不把并列描述当成临床等价。"
        : lead.getAttribute("data-c-summary-text") || "";
      var copy = document.querySelector(".kz-c-comparison-entry__copy");
      if (copy) copy.hidden = active;
      // Keep the existing advanced filters available without a separate
      // full-width chrome row ahead of the comparison. No query is changed.
      var filters = document.getElementById("kz-filter-panel");
      var tools = document.querySelector(".kz-c-section-heading");
      if (active && filters && tools && filters.parentNode !== tools) {
        tools.appendChild(filters);
      }
      if (typeof document.title === "string") {
        var prefix = document.title.indexOf(" - ");
        document.title = (active ? "全研究横比" : summaryTitle)
          + (prefix === -1 ? "" : document.title.slice(prefix));
      }
    }
    var entry = document.querySelector(".kz-c-comparison-entry");
    var action = document.querySelector("[data-c-enter-comparison]");
    if (entry && action) {
      if (active) {
        entry.setAttribute("data-c-comparison-active", "true");
        action.textContent = "返回首页摘要";
        action.setAttribute(
          "href",
          (window.__C_SITE_PREFIX__ || "") + "overview.html"
        );
      } else {
        entry.removeAttribute("data-c-comparison-active");
        action.textContent = "打开全研究横比";
        action.setAttribute(
          "href",
          (window.__C_SITE_PREFIX__ || "") + "overview.html?view=comparison"
        );
      }
    }
  }

  function trialLabel(row) {
    var id = String(row.trial_display_id || "试验");
    // 轴标签优先中文名；英文别名仍在来源和完整资料中可查。
    var product = String(row.product_zh || "")
      .replace(/（[A-Za-z][A-Za-z0-9 .-]*）$/, "");
    var name = String(row.trial_zh || "");
    if (name.indexOf("奈莫利珠单抗") !== -1) name = "奈莫利珠单抗研究";
    if (product.length > 18) product = product.slice(0, 17) + "…";
    if (name.length > 14) name = name.slice(0, 13) + "…";
    var identity = product && product !== name ? product + "\n" + id : id;
    return name && name !== id ? identity + "\n" + name : identity;
  }


  function escapeTooltipHtml(value) {
    return String(value == null ? "" : value).replace(/[&<>"']/g, function (character) {
      return {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[character];
    });
  }

  function tooltipHtml(row) {
    if (!row) return "";
    var fields = [
      String(row.trial_display_id || row.trial_zh || "试验"),
      row.trial_zh && row.trial_zh !== row.trial_display_id ? String(row.trial_zh) : "",
      String(row.field_family_zh || "设计事实"),
      String(row.element_zh || row.display_label_zh || "设计要素"),
      String(row.value === null || row.value === undefined ? row.status || "未公开" : row.value),
      row.scale ? "量表：" + String(row.scale) : "",
      row.time && row.time !== "时间点未列示" ? "时间点：" + String(row.time) : "",
      row.group_zh && row.group_zh !== "组别未细分" ? "组别：" + String(row.group_zh) : ""
    ];
    return "<strong>" + escapeTooltipHtml(row.product_zh || "产品未列示") + "</strong>"
      + fields.filter(Boolean).map(function (value) {
        return "<br>" + escapeTooltipHtml(value);
      }).join("");
  }

  function matrixLabel(row) {
    var value = String(
      row.value === null || row.value === undefined
        ? row.status || "未公开"
        : row.value
    );
    var separator = value.indexOf("；") !== -1 ? "；" : value.indexOf(" ") !== -1 ? " " : "";
    var units = separator ? value.split(separator).filter(Boolean) : [value];
    var lineLength = 18;
    var maxLines = 5;
    var lines = [];
    var current = "";
    units.forEach(function (unit) {
      var candidate = current ? current + separator + unit : unit;
      if (current && candidate.length > lineLength) {
        lines.push(current);
        current = unit;
      } else {
        current = candidate;
      }
    });
    if (current) lines.push(current);
    var wrapped = [];
    lines.forEach(function (line) {
      while (line.length > lineLength) {
        wrapped.push(line.slice(0, lineLength));
        line = line.slice(lineLength);
      }
      if (line) wrapped.push(line);
    });
    if (wrapped.length > maxLines) {
      wrapped = wrapped.slice(0, maxLines);
      wrapped[maxLines - 1] = wrapped[maxLines - 1].slice(0, lineLength - 1) + "…";
    }
    return wrapped.join("\n");
  }

  function matrixOption(rows, kind, containerWidth) {
    var trialIds = uniqueValues(rows, "trial_display_id");
    var compactTrialAxis = kind === "core-design-matrix";
    var gridLeft = Math.min(178, Math.max(96, Math.round(containerWidth * 0.32)));
    var cellWidth = (containerWidth - gridLeft - 18) / Math.max(1, trialIds.length);
    var readableCore = compactTrialAxis && trialIds.length <= 4 && cellWidth >= 180;
    var coreLabelWidth = Math.min(300, Math.floor(cellWidth - 20));
    var trialLabels = trialIds.map(function (trialId) {
      var row = rows.find(function (item) { return item.trial_display_id === trialId; });
      return compactTrialAxis ? trialId : trialLabel(row || {trial_display_id: trialId});
    });
    var elements = uniqueValues(rows, "element_zh");
    // 独立视觉复核（v59 hierarchy/charts）：同坐标多行聚合为一个单元格并
    // 标注"共N条明细"，tooltip 展开全部 rowId——图表与同源数据表行数可对应
    var cellMap = {};
    var cellOrder = [];
    rows.forEach(function (row) {
      var x = trialIds.indexOf(String(row.trial_display_id || "未列示"));
      var y = elements.indexOf(String(row.element_zh || "未列示"));
      var key = x + ":" + y;
      if (!cellMap[key]) {
        cellMap[key] = { x: x, y: y, rows: [] };
        cellOrder.push(cellMap[key]);
      }
      cellMap[key].rows.push(row);
    });
    var data = cellOrder.map(function (cell) {
      var primary = cell.rows[0];
      var reported = cell.rows.some(function (row) {
        return row.disclosure_state === "reported_value" || row.disclosure_state === "reported_zero";
      });
      return {
        value: [cell.x, cell.y, reported ? 1 : 0],
        rowId: primary.row_id,
        row: primary,
        rowCount: cell.rows.length,
        rowIds: cell.rows.map(function (row) { return row.row_id; }),
        itemStyle: {
          color: reported
            ? (cell.y % 2 ? "#FFF8EC" : "#FFF1D6")
            : "#EEF1F5",
          borderColor: "#FFFFFF",
          borderWidth: 3
        }
      };
    });
    return {
      animationDuration: 280,
      grid: {
        // 独立视觉复核（v59 format）：左边距按容器宽响应式，窄视口不再
        // 挤压绘图区至不可读
        left: gridLeft,
        right: 18,
        top: 28,
        bottom: compactTrialAxis ? 88 : (trialIds.length > 3 ? 104 : 72)
      },
      tooltip: {
        trigger: "item",
        confine: true,
        formatter: function (p) { return tooltipHtml(p.data.row); }
      },
      xAxis: {
        type: "category",
        data: trialLabels,
        axisLine: {lineStyle: {color: "#C9D0DA"}},
        axisTick: {show: false},
        axisLabel: {
          color: "#405066",
          interval: 0,
          rotate: readableCore ? 0 : compactTrialAxis && trialIds.length > 8
            ? 48 : (trialIds.length > 3 ? 24 : 0),
          fontSize: 16,
          width: readableCore ? 160 : compactTrialAxis ? 90 : 160,
          overflow: "break",
          lineHeight: 23,
          margin: 14
        }
      },
      yAxis: {
        type: "category",
        data: elements,
        axisLine: {show: false},
        axisTick: {show: false},
        axisLabel: {
          color: "#243650",
          fontWeight: 600,
          fontSize: 16,
          width: 150,
          overflow: "break",
          lineHeight: 23
        }
      },
      series: [{
        name: "设计事实",
        type: "heatmap",
        data: data,
        label: {
          show: true,
          color: "#243650",
          fontSize: 16,
          lineHeight: 23,
          // 独立视觉复核（typography/charts）：单元格长文本限宽截断，
          // 完整内容保留在 tooltip 与同源数据表
          width: readableCore ? coreLabelWidth : compactTrialAxis
            ? 86 : Math.min(150, Math.max(72, Math.round(640 / Math.max(1, trialIds.length)))),
          overflow: "break",
          formatter: function (p) {
            if (!p.data.value[2]) return "未公开";
            var base = matrixLabel(p.data.row);
            // 独立复核 C r40（issue-3）：计数是"本格聚合的登记明细数"，
            // 前置括注与标签显式分隔，不再误读为该终点有 N 条
            return p.data.rowCount > 1
              ? "〔本格聚合" + p.data.rowCount + "条登记明细〕\n" + base
              : base;
          }
        },
        emphasis: {itemStyle: {shadowBlur: 12, shadowColor: "rgba(36,54,80,.25)"}}
      }]
    };
  }

  function sampleOption(rows) {
    var samples = rows.filter(function (row) { return Number.isFinite(Number(row.numeric_value)); });
    return {
      animationDuration: 320,
      grid: {left: 112, right: 52, top: 20, bottom: 42},
      tooltip: {trigger: "item", confine: true, formatter: function (p) { return tooltipHtml(p.data.row); }},
      xAxis: {type: "value", name: "计划或实际样本量（例）", splitLine: {lineStyle: {color: "#EEF1F5"}}},
      yAxis: {
        type: "category",
        data: samples.map(function (row) { return row.trial_display_id; }),
        axisLine: {show: false},
        axisTick: {show: false},
        axisLabel: {color: "#243650", fontWeight: 600}
      },
      series: [{
        type: "bar",
        barWidth: 22,
        data: samples.map(function (row, index) {
          return {value: Number(row.numeric_value), row: row, rowId: row.row_id, itemStyle: {color: index === 0 ? "#F59E0B" : "#C47A0A", borderRadius: [0, 6, 6, 0]}};
        }),
        label: {show: true, position: "right", color: "#243650", fontWeight: 700}
      }]
    };
  }

  function criteriaCountOption(rows) {
    // 独立视觉复核（copy_zh/charts_tables）：本图语义是"每试验公开条目数"。
    // 文本型行（如入选标准原文）没有数值，此前被 Number(...)||0 伪造成 0 值柱，
    // 造成图表与同源数据表行数不一致且出现空墙；现按试验聚合公开条目计数。
    function conciseTrialLabel(row) {
      var product = String(row.product_zh || "产品未列示").split("（")[0];
      var trial = String(row.trial_display_id || row.trial_zh || "试验未列示");
      return product + "｜" + trial;
    }
    var byTrial = {};
    var trialOrder = [];
    rows.forEach(function (row) {
      var label = conciseTrialLabel(row);
      if (!byTrial.hasOwnProperty(label)) {
        byTrial[label] = {label: label, count: 0, sample: row};
        trialOrder.push(label);
      }
      byTrial[label].count += 1;
    });
    var aggregated = trialOrder.map(function (label) { return byTrial[label]; });
    rows = aggregated.map(function (item) {
      var row = Object.assign({}, item.sample, {value: item.count, numeric_value: item.count});
      row.__entry_count = item.count;
      return row;
    });
    // 会商 #10（C r41 issue-5）：每试验恰好 1 条定义时柱图无区分度——
    // 上游改为渲染"设计定义对照"说明并保表，不再绘制全 1 柱
    var noDiscrimination = aggregated.length > 0 && aggregated.every(function (item) { return item.count === 1; });
    if (noDiscrimination) {
      return {
        __no_discrimination: true,
        _note: "当前页面每项研究仅登记 1 条人群/疾病定义条目，条目数柱状图不具区分度；本页改以同源数据表逐项呈现各研究的登记定义原文，请在下方表格中对照查看。"
      };
    }
    return {
      animationDuration: 300,
      grid: {left: 250, right: 58, top: 22, bottom: 38, containLabel: false},
      tooltip: {
        trigger: "item",
        confine: true,
        formatter: function (p) {
          var cnt = p.data.row && p.data.row.__entry_count;
          return tooltipHtml(p.data.row) + "<br>公开条目：" + String(p.data.value) + "条" + (cnt ? "（按试验聚合）" : "");
        }
      },
      xAxis: {
        type: "value",
        name: "公开条目（条）",
        minInterval: 1,
        splitLine: {lineStyle: {color: "#EEF1F5"}},
        axisLabel: {color: "#405066"}
      },
      yAxis: {
        type: "category",
        inverse: true,
        data: rows.map(conciseTrialLabel),
        axisLine: {show: false},
        axisTick: {show: false},
        axisLabel: {
          color: "#243650",
          fontSize: 16,
          lineHeight: 16,
          width: 220,
          overflow: "break"
        }
      },
      series: [{
        name: "公开条目",
        type: "bar",
        barMaxWidth: 22,
        data: rows.map(function (row, index) {
          return {
            value: Number(row.numeric_value || row.value || 0),
            row: row,
            rowId: row.row_id || "trial-aggregate",
            itemStyle: {
              color: index % 2 ? "#F5B64D" : "#F59E0B",
              borderRadius: [0, 5, 5, 0]
            }
          };
        }),
        label: {
          show: true,
          position: "right",
          formatter: "{c}",
          color: "#243650",
          fontWeight: 700
        },
        emphasis: {
          focus: "self",
          itemStyle: {shadowBlur: 8, shadowColor: "rgba(36,54,80,.24)"}
        }
      }]
    };
  }

  // R24-146 有界执行及 R24-154 主线程修复：只消费领域十轴实例键，
  // 包括原始父路径；角色或标题相似不构成组合依据，跨研究永不配对。
  function isEndpointField(row) {
    return /^primary_endpoint_|^secondary_endpoint_/.test(String(row.element || ""));
  }

  function endpointRoleOf(row) {
    var match = /^(primary|secondary)_endpoint_/.exec(String(row.element || ""));
    return match ? match[1] + "_endpoint" : "";
  }

  function endpointRoleLabelZh(role) {
    return { "primary_endpoint": "主要终点", "secondary_endpoint": "次要终点" }[role]
      || "终点实例";
  }

  // 入排标准「研究列登记原文对照表」：不做语义配对、不改写原文与当前值；
  // 序号按各研究登记原文顺序一次确定，检索、勾选、清空都不重排。
  function renderCriteriaSources(chart, rows, designMode) {
    chart.setAttribute("role", "region");
    chart.classList.add("kz-c-chart-canvas--criteria-sources");
    chart.style.height = "auto";

    var note = document.createElement("p");
    note.className = "kz-c-criteria-note";
    note.textContent = designMode
      ? "按设计要素与研究并列来源条款；同类字段不代表终点、人群或时间窗等价。"
        + "同一研究内，终点的定义、时间点与完整定义原文只在显式实例身份完整一致时"
        + "组合为一个终点实例；实例上下文缺失或矛盾时保持独立列示并给出原因，"
        + "不同研究之间不按序号或标题配对。各观察分别保留，不汇总或取第一条；"
        + "可检索当前内容与完整原文，并核对来源。检索未命中的同实例事实以上下文"
        + "标记展示，不计入命中条数。"
      : "按研究并列各条登记原文，仅作原始记录逐一对照；"
      + "不按并列位置推断条款等价，序号是各研究登记原文顺序编号，不代表排名或临床可比。"
      + "点击条款可读全文，来源按钮可核对登记记录。";
    if (designMode) {
      var method = document.createElement("details");
      method.className = "kz-c-criteria-method";
      var methodSummary = document.createElement("summary");
      methodSummary.textContent = "条款组合与检索说明（并列不代表临床等价）";
      method.appendChild(methodSummary);
      method.appendChild(note);
    } else {
      chart.appendChild(note);
    }

    var toolbar = document.createElement("div");
    toolbar.className = "kz-c-criteria-toolbar";
    var label = document.createElement("label");
    label.setAttribute("for", "kz-c-criteria-search");
    label.textContent = "检索原文";
    var search = document.createElement("input");
    search.id = "kz-c-criteria-search";
    search.type = "search";
    search.placeholder = designMode
      ? "主题、关键词、产品或试验号"
      : "关键词、产品或试验号";
    search.value = criteriaSearchQuery;
    label.appendChild(search);
    toolbar.appendChild(label);
    var status = document.createElement("span");
    status.className = "kz-c-criteria-status";
    status.setAttribute("role", "status");
    toolbar.appendChild(status);
    chart.appendChild(toolbar);

    var byTrial = {};
    var trialOrder = [];
    rows.forEach(function (row) {
      var key = String(row.trial_display_id || row.trial_zh || "试验未列示");
      if (!byTrial[key]) {
        byTrial[key] = [];
        trialOrder.push(key);
      }
      byTrial[key].push(row);
    });
    var trialIds = trialOrder.slice().sort();
    var pageRows = allChartRows();
    var studyMeta = {};
    var definitionsByTrial = {};
    trialIds.forEach(function (trialId) {
      var trialRows = byTrial[trialId];
      studyMeta[trialId] = {
        product: String(trialRows[0].product_zh || "产品未列示")
      };
      // 稳定序号以整页登记原文顺序为基准，一次确定：页面维度筛选、检索、
      // 勾选与清空都只筛选可见条目，不重新编号。
      var originalOrder = {};
      var ordinalCursor = 0;
      pageRows.forEach(function (row) {
        if (String(row.trial_display_id || row.trial_zh || "试验未列示") !== trialId) return;
        ordinalCursor += 1;
        originalOrder[String(row.row_id)] = ordinalCursor;
      });
      definitionsByTrial[trialId] = trialRows.map(function (row, index) {
        return {
          row: row,
          ordinal: originalOrder[String(row.row_id)] || index + 1
        };
      });
    });

    var choice = document.createElement("details");
    choice.className = "kz-c-criteria-choose";
    var choiceSummary = document.createElement("summary");
    choiceSummary.textContent = "选择并列研究（" + trialIds.length + "）";
    choice.appendChild(choiceSummary);
    var choices = document.createElement("div");
    choices.className = "kz-c-criteria-choices";
    trialIds.forEach(function (trialId) {
      var checkboxLabel = document.createElement("label");
      var checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.value = trialId;
      checkbox.checked = excludedCriteriaTrials[trialId] !== true;
      checkbox.addEventListener("change", function () {
        excludedCriteriaTrials[trialId] = !checkbox.checked;
        writeCriteriaUrl();
        draw();
      });
      checkboxLabel.appendChild(checkbox);
      checkboxLabel.appendChild(document.createTextNode(trialId));
      choices.appendChild(checkboxLabel);
    });
    choice.appendChild(choices);
    toolbar.appendChild(choice);
    if (designMode) toolbar.appendChild(method);

    var region = document.createElement("div");
    region.className = "kz-c-criteria-table-region";
    chart.appendChild(region);

    function searchableText(row, trialId) {
      return [row.product_zh, trialId, row.trial_zh, row.source_text, row.original_text,
        row.value, row.element_zh, row.field_family_zh, row.source_topic_zh, row.time,
        row.group_zh, row.cohort_zh, row.scale, row.source_version_id]
        .map(function (value) { return String(value || ""); }).join(" ").toLocaleLowerCase();
    }

    function applyCurrentState(item, row) {
      var currentState = row.disclosure_state === "user_cleared"
        ? "user_cleared"
        : row.review_state === "user_modified" ? "user_modified" : "";
      if (!currentState) return;
      item.setAttribute("data-criterion-current-state", currentState);
      var revision = document.createElement("p");
      revision.className = "kz-c-criteria-revision";
      revision.textContent = currentState === "user_cleared"
        ? "当前值：用户清除，待重新核实"
        : "当前修订（未独立复核）：" + String(row.value == null ? row.status || "待核" : row.value);
      item.appendChild(revision);
    }

    function buildDefinition(def, trialId, contextOnly) {
      var row = def.row;
      var item = document.createElement("li");
      item.className = "kz-c-criteria-item";
      item.setAttribute("data-criterion-row-id", String(row.row_id));
      item.setAttribute("data-criterion-ordinal", String(def.ordinal));
      item.setAttribute("value", String(def.ordinal));
      item.setAttribute("data-criterion-trial-id", String(row.trial_id || ""));
      item.setAttribute("data-criterion-product-id", String(row.product_id || ""));
      item.setAttribute("data-criterion-review-state", String(row.review_state || ""));
      item.setAttribute("data-criterion-disclosure-state", String(row.disclosure_state || ""));
      if (row.source_version_id) {
        item.setAttribute("data-criterion-source-version-id", String(row.source_version_id));
      }
      if (contextOnly) {
        // 检索命中同实例其他事实时，未命中兄弟仅作标记上下文：
        // 不计入命中条数、不进入完整表可见行，仍可读原文与来源。
        item.setAttribute("data-criterion-context-only", "true");
        var contextNote = document.createElement("p");
        contextNote.className = "kz-c-criteria-context-note";
        contextNote.textContent = "同实例上下文（未匹配当前检索词），仅帮助阅读，不计入命中条数。";
        item.appendChild(contextNote);
      }
      applyCurrentState(item, row);
      if (designMode && row.disclosure_state !== "user_cleared") {
        var current = document.createElement("p");
        current.className = "kz-c-design-source-value";
        var valueText = String(row.value == null ? row.status || "当前值待核" : row.value);
        var element = String(row.element || "");
        // Full descriptions already remain verbatim in the native disclosure and
        // source drawer. Do not duplicate paragraphs on the reading surface or
        // invent a clinical summary. User edits remain explicitly visible.
        current.textContent = row.source_topic_zh && row.review_state !== "user_modified"
          ? "来源条款：" + String(row.source_topic_zh)
          : /_description$/.test(element) && row.review_state !== "user_modified"
          ? "完整定义：展开下方原文与限定条件"
          : /_timepoint$/.test(element) ? "评估时间点：" + valueText : valueText;
        item.appendChild(current);
      }
      var detail = document.createElement("details");
      detail.className = "kz-c-criteria-def-fold";
      var summary = document.createElement("summary");
      var sourceText = String(row.source_text || row.original_text || "").trim();
      var preview = sourceText.replace(/\s+/g, " ");
      summary.textContent = designMode ? "完整原文与限定条件（" + String(def.ordinal) + "）"
        : "登记原文 " + String(def.ordinal) + "｜" +
          (preview ? preview.slice(0, 80) + (preview.length > 80 ? "…" : "") : "原文待核");
      var original = document.createElement("div");
      original.className = "kz-c-criteria-original";
      original.textContent = sourceText || "原文未在本数据包提供；请核对下方完整表与来源。";
      var provenance = document.createElement("p");
      provenance.className = "kz-c-criteria-provenance";
      var provenanceParts = [
        (designMode ? "来源：" : "登记记录：") +
          String(row.source_location_zh || "来源定位见数据依据")
      ];
      var trialRef = String(row.trial_display_id || row.trial_id || "");
      if (trialRef) provenanceParts.push(trialRef + " · " + studyMeta[trialId].product);
      if (row.source_version_id) {
        provenanceParts.push("来源编号 " + String(row.source_version_id));
      }
      provenance.textContent = provenanceParts.join("｜");
      detail.appendChild(summary);
      detail.appendChild(original);
      if (row.source_context_note_zh) {
        var continuationNote = document.createElement("p");
        continuationNote.className = "kz-c-criteria-provenance";
        continuationNote.textContent = String(row.source_context_note_zh);
        detail.appendChild(continuationNote);
      }
      detail.appendChild(provenance);
      item.appendChild(detail);
      var source = document.createElement("button");
      source.type = "button";
      source.className = "kz-c-criteria-source";
      source.setAttribute("data-evidence-open", String(row.row_id));
      source.setAttribute("data-row-id", String(row.row_id));
      source.textContent = row.source_context_note_zh ? "查看来源与跨页前后文" : "查看来源";
      item.appendChild(source);
      return item;
    }

    // 终点实例组合：只信投影的显式实例键。实例序号在可见性过滤之前按页面
    // 登记顺序一次确定，检索、勾选、清空都不重排。
    function composeEndpointBlocks(roleDefs, matchedByRow) {
      var blocks = [];
      var byInstance = {};
      roleDefs.forEach(function (def) {
        var inst = def.row.endpoint_instance || null;
        var id = inst && inst.instance_id ? String(inst.instance_id) : null;
        if (!id) {
          blocks.push({
            instanceId: null,
            defs: [def],
            complete: false,
            conflict: false,
            reason: inst && inst.reason_zh ? String(inst.reason_zh) : "",
          });
          return;
        }
        var block = byInstance[id];
        if (!block) {
          block = {
            instanceId: id,
            defs: [],
            complete: inst.complete !== false,
            conflict: inst.conflict === true,
            reason: inst.reason_zh ? String(inst.reason_zh) : "",
          };
          byInstance[id] = block;
          blocks.push(block);
        }
        block.defs.push(def);
      });
      blocks.forEach(function (block, index) { block.ordinal = index + 1; });
      return blocks.filter(function (block) {
        return block.defs.some(function (def) {
          return matchedByRow[String(def.row.row_id)];
        });
      });
    }

    function buildInstanceBlock(block, trialId, matchedByRow) {
      var item = document.createElement("li");
      item.className = "kz-c-endpoint-instance";
      item.setAttribute("data-endpoint-instance", "");
      if (block.instanceId) {
        item.setAttribute("data-endpoint-instance-id", block.instanceId);
        item.setAttribute("data-endpoint-complete", block.complete ? "true" : "false");
      } else {
        item.setAttribute("data-endpoint-standalone", "true");
        item.setAttribute("data-endpoint-complete", "false");
      }
      item.setAttribute("data-endpoint-conflict", block.conflict ? "true" : "false");
      item.setAttribute("data-endpoint-ordinal", String(block.ordinal));
      item.setAttribute("data-endpoint-role-zh", block.roleZh);
      var heading = document.createElement("p");
      heading.className = "kz-c-endpoint-instance__heading";
      heading.textContent = block.roleZh + " " + String(block.ordinal)
        + "（" + String(block.defs.length) + " 条登记事实）";
      item.appendChild(heading);
      if (block.reason) {
        var reason = document.createElement("p");
        reason.className = "kz-c-endpoint-instance__reason";
        reason.textContent = block.reason;
        item.appendChild(reason);
      }
      var list = document.createElement("ol");
      list.className = "kz-c-criteria-defs";
      block.defs.forEach(function (def) {
        list.appendChild(
          buildDefinition(def, trialId, !matchedByRow[String(def.row.row_id)])
        );
      });
      item.appendChild(list);
      return item;
    }

    function buildTable(shownTrials, matchedByRow, query) {
      var wrap = document.createElement("div");
      wrap.className = "kz-c-criteria-table-wrap";
      wrap.setAttribute("role", "region");
      wrap.setAttribute("tabindex", "0");
      wrap.setAttribute("aria-label", designMode
        ? "按设计要素与研究并列的来源条款对照表；可横向滚动查看全部研究列"
        : "按研究并列的登记原文对照表；可横向滚动查看全部研究列");
      var table = document.createElement("table");
      table.className = "kz-c-criteria-table" + (designMode ? " kz-c-criteria-table--design" : "");
      if (designMode) table.style.minWidth = Math.max(1, shownTrials.length) * 300 + 168 + "px";
      var caption = document.createElement("caption");
      caption.className = "kz-c-criteria-table-caption";
      caption.textContent = designMode
        ? "设计要素与完整来源条款（同一研究内实例身份完整一致时组合终点实例；"
          + "同类字段并列不代表临床等价；编号保留本研究条款顺序）"
        : "各研究登记原文逐条对照（按各研究登记顺序编号；并列仅为原始记录对照）";
      table.appendChild(caption);
      var thead = document.createElement("thead");
      var headRow = document.createElement("tr");
      var ordinalTh = document.createElement("th");
      ordinalTh.className = "kz-c-criteria-table__ordinal-th";
      ordinalTh.setAttribute("scope", "col");
      ordinalTh.setAttribute("id", "kz-c-criteria-ordinal-column");
      ordinalTh.textContent = designMode ? "设计要素" : "登记原文";
      headRow.appendChild(ordinalTh);
      shownTrials.forEach(function (trialId, index) {
        var th = document.createElement("th");
        th.className = "kz-c-criteria-table__study-th kz-c-criteria-trial";
        th.setAttribute("scope", "col");
        th.setAttribute("id", "kz-c-criteria-study-" + String(index + 1));
        th.setAttribute("data-criteria-study", trialId);
        var idSpan = document.createElement("span");
        idSpan.className = "kz-c-criteria-table__trial-id";
        idSpan.textContent = trialId;
        th.appendChild(idSpan);
        var productSpan = document.createElement("span");
        productSpan.className = "kz-c-criteria-table__trial-product";
        productSpan.textContent = studyMeta[trialId].product;
        th.appendChild(productSpan);
        headRow.appendChild(th);
      });
      thead.appendChild(headRow);
      table.appendChild(thead);
      var tbody = document.createElement("tbody");
      var matched = {};
      var endpointRoles = [];
      shownTrials.forEach(function (trialId) {
        matched[trialId] = [];
        definitionsByTrial[trialId].forEach(function (def) {
          if (!matchedByRow[String(def.row.row_id)]) return;
          matched[trialId].push(def);
          if (designMode && isEndpointField(def.row)) {
            var role = endpointRoleOf(def.row);
            if (role && endpointRoles.indexOf(role) === -1) endpointRoles.push(role);
          }
        });
      });
      endpointRoles.forEach(function (role) {
        var bodyRow = document.createElement("tr");
        bodyRow.className = "kz-c-criteria-table__row";
        var rowHeader = document.createElement("th");
        rowHeader.className = "kz-c-criteria-table__ordinal-cell";
        rowHeader.setAttribute("scope", "row");
        var headerId = "kz-c-criteria-ordinal-row-endpoint-" + role;
        rowHeader.setAttribute("id", headerId);
        rowHeader.textContent = endpointRoleLabelZh(role) + "实例";
        bodyRow.appendChild(rowHeader);
        shownTrials.forEach(function (trialId, index) {
          var td = document.createElement("td");
          td.className = "kz-c-criteria-table__cell";
          td.setAttribute("headers", headerId + " kz-c-criteria-study-" + String(index + 1));
          var roleDefs = definitionsByTrial[trialId].filter(function (def) {
            return endpointRoleOf(def.row) === role;
          });
          var blocks = composeEndpointBlocks(roleDefs, matchedByRow);
          if (!blocks.length) {
            var emptyCell = document.createElement("p");
            emptyCell.className = "kz-c-criteria-cell-empty";
            emptyCell.textContent = query
              ? "本列无匹配的该类终点实例"
              : "本列未列示该类终点实例";
            td.appendChild(emptyCell);
          } else {
            var list = document.createElement("ol");
            list.className = "kz-c-endpoint-instances";
            blocks.forEach(function (block) {
              block.roleZh = endpointRoleLabelZh(role);
              list.appendChild(buildInstanceBlock(block, trialId, matchedByRow));
            });
            td.appendChild(list);
          }
          bodyRow.appendChild(td);
        });
        tbody.appendChild(bodyRow);
      });
      var elements = designMode ? uniqueValues(shownTrials.flatMap(function (trialId) {
        return matched[trialId].filter(function (def) { return !isEndpointField(def.row); })
          .map(function (def) { return def.row; });
      }), "element") : [null];
      elements.forEach(function (element, elementIndex) {
      var bodyRow = document.createElement("tr");
      bodyRow.className = "kz-c-criteria-table__row";
      var rowHeader = document.createElement("th");
      rowHeader.className = "kz-c-criteria-table__ordinal-cell";
      rowHeader.setAttribute("scope", "row");
      var headerId = "kz-c-criteria-ordinal-row" + (designMode ? "-" + elementIndex : "");
      rowHeader.setAttribute("id", headerId);
      var sectionRow = designMode && rows.find(function (row) {
        return String(row.element || "未列示") === element;
      });
      rowHeader.textContent = sectionRow ? String(sectionRow.element_zh || element)
        : "登记原文（按各研究登记顺序逐条列出）";
      bodyRow.appendChild(rowHeader);
      shownTrials.forEach(function (trialId, index) {
        var td = document.createElement("td");
        td.className = "kz-c-criteria-table__cell";
        td.setAttribute(
          "headers",
          headerId + " kz-c-criteria-study-" + String(index + 1)
        );
        var matchedDefs = designMode ? matched[trialId].filter(function (def) {
          return String(def.row.element || "未列示") === element;
        }) : matched[trialId];
        if (!matchedDefs.length) {
          var emptyCell = document.createElement("p");
          emptyCell.className = "kz-c-criteria-cell-empty";
          emptyCell.textContent = designMode ? "该研究在本查询范围未列示此类条款"
            : query ? "本列无匹配原文" : "本列未列示登记原文";
          td.appendChild(emptyCell);
        } else {
          var list = document.createElement("ol");
          list.className = "kz-c-criteria-defs";
          matchedDefs.forEach(function (def) {
            list.appendChild(buildDefinition(def, trialId));
          });
          td.appendChild(list);
        }
        bodyRow.appendChild(td);
      });
      tbody.appendChild(bodyRow);
      });
      table.appendChild(tbody);
      wrap.appendChild(table);
      return wrap;
    }

    function draw() {
      region.replaceChildren();
      var query = criteriaSearchQuery.trim().toLocaleLowerCase();
      var shownTrials = trialIds.filter(function (trialId) {
        return excludedCriteriaTrials[trialId] !== true;
      });
      // 精确同一 Q：命中按事实判定。同实例未命中兄弟仅在可见实例块内以
      // 上下文标记展示，不进入命中集合、计数或完整表可见行。
      var matchedByRow = {};
      var shownRows = [];
      var shownStudies = 0;
      var matchedTrials = [];
      var unmatchedSelected = [];
      shownTrials.forEach(function (trialId) {
        definitionsByTrial[trialId].forEach(function (def) {
          var isMatch = !query || searchableText(def.row, trialId).indexOf(query) !== -1;
          if (!isMatch) return;
          matchedByRow[String(def.row.row_id)] = true;
          shownRows.push(def.row);
        });
        var studyMatched = definitionsByTrial[trialId].some(function (def) {
          return matchedByRow[String(def.row.row_id)];
        });
        if (studyMatched) {
          shownStudies += 1;
          matchedTrials.push(trialId);
        } else if (query) {
          unmatchedSelected.push(trialId);
        }
      });
      // 无命中不是取消研究选择，也不是来源无数据。检索中的空列只从阅读
      // 表面收起，明确保留其选择和 ID；清空关键词恢复原先列顺序及所有事实。
      if (unmatchedSelected.length) {
        var unmatched = document.createElement("p");
        unmatched.className = "kz-c-criteria-note";
        unmatched.setAttribute("data-criteria-unmatched-selected", "");
        unmatched.textContent = "本次检索无命中，保留选择并暂收起空列："
          + unmatchedSelected.join("、") + "；清空关键词可恢复研究列。";
        region.appendChild(unmatched);
      }
      if (!shownRows.length) {
        var empty = document.createElement("p");
        empty.className = "kz-c-criteria-empty";
        empty.textContent = "当前关键词与所选研究下没有匹配原文；可清空检索或重新选择研究。";
        region.appendChild(empty);
      } else {
        region.appendChild(buildTable(query ? matchedTrials : shownTrials, matchedByRow, query));
      }
      status.textContent = "当前可达 " + shownStudies + " 项研究、" + shownRows.length +
        (designMode ? " 条设计观察" : " 组登记原文");
      window.__C_VISIBLE_CHART_ROW_IDS__ = shownRows.map(function (row) {
        return String(row.row_id);
      });
      var shownIds = {};
      window.__C_VISIBLE_CHART_ROW_IDS__.forEach(function (rowId) {
        shownIds[rowId] = true;
      });
      var tableRows = document.querySelectorAll(".kz-chart-table__row[data-row-id]");
      for (var i = 0; i < tableRows.length; i += 1) {
        tableRows[i].style.display = shownIds[tableRows[i].getAttribute("data-row-id")] ? "" : "none";
      }
      updateStatus(sanitizeState(selectedState()));
    }
    search.addEventListener("input", function () {
      criteriaSearchQuery = search.value;
      writeCriteriaUrl();
      draw();
    });
    draw();
  }

  function timelineOption(rows) {
    var trials = uniqueValues(rows, "trial_display_id");
    var times = uniqueValues(rows, "time");
    return {
      animationDuration: 300,
      grid: {left: 112, right: 36, top: 24, bottom: 74},
      tooltip: {trigger: "item", confine: true, formatter: function (p) { return tooltipHtml(p.data.row); }},
      xAxis: {type: "category", data: times, axisLabel: {rotate: times.length > 3 ? 22 : 0, color: "#405066"}},
      yAxis: {type: "category", data: trials, axisLine: {show: false}, axisTick: {show: false}},
      series: [{
        type: "scatter",
        symbolSize: 18,
        itemStyle: {color: "#F59E0B", borderColor: "#FFFFFF", borderWidth: 2},
        data: rows.map(function (row) {
          return {value: [times.indexOf(String(row.time || "时间点未列示")), trials.indexOf(String(row.trial_display_id || "未列示"))], row: row, rowId: row.row_id};
        })
      }]
    };
  }

  function evidenceOption(rows) {
    var trials = uniqueValues(rows, "trial_display_id");
    function count(trial, reported) {
      return rows.filter(function (row) {
        var isReported = row.disclosure_state === "reported_value" || row.disclosure_state === "reported_zero";
        return row.trial_display_id === trial && isReported === reported;
      }).length;
    }
    return {
      animationDuration: 280,
      color: ["#F59E0B", "#D9DEE7"],
      tooltip: {trigger: "axis", axisPointer: {type: "shadow"}},
      legend: {bottom: 0, data: ["已公开", "未公开"]},
      grid: {left: 112, right: 34, top: 20, bottom: 48},
      xAxis: {type: "value", name: "设计要素数"},
      yAxis: {type: "category", data: trials, axisLine: {show: false}, axisTick: {show: false}},
      series: [
        {name: "已公开", type: "bar", stack: "total", data: trials.map(function (trial) { return count(trial, true); })},
        {name: "未公开", type: "bar", stack: "total", data: trials.map(function (trial) { return count(trial, false); })}
      ]
    };
  }

  function renderCChart() {
    var host = document.getElementById("kz-c-chart-visuals");
    if (!host || !window.echarts) return;
    syncComparisonChrome();
    var criteriaPage = window.__C_PAGE_ID__ === "inclusion-criteria" ||
      window.__C_PAGE_ID__ === "exclusion-criteria";
    // A local keyword/choice hides table rows, but must not become the input
    // universe for the next redraw: clearing the search restores every match.
    var sourceComparison = usesSourceComparison(window.__C_PAGE_ID__ || "");
    var rows = sourceComparison
      ? allChartRows().filter(function (row) {
          return matches(String(row.row_id), sanitizeState(selectedState()));
        })
      : visibleChartRows();
    window.__C_VISIBLE_CHART_ROW_IDS__ = rows.map(function (row) {
      return String(row.row_id);
    });
    var kind = chartKind(window.__C_PAGE_ID__ || "");
    if (cChart) {
      cChart.dispose();
      cChart = null;
    }
    chartState = {rows: [], kind: "", chart: null};
    host.innerHTML = "";
    // FR20: the landing summary and full-source comparison are distinct
    // tasks. Do not paint long clauses into a redundant homepage heatmap;
    // all observations remain in the explicit comparison query and payload.
    if (window.__C_PAGE_ID__ === "overview" && !wantsFullStudyComparison()) return;
    var title = document.createElement("div");
    title.className = "kz-c-chart-title";
    title.textContent = wantsFullStudyComparison()
      ? "全研究横比"
      : {
      "sample-size-bar": "样本量与统计分析原文对照",
      "visit-timeline": "关键评估与随访时间",
      "endpoint-timepoint-matrix": "主要终点与评估时间",
      "treatment-structure-matrix": "分组、干预与给药结构",
      "design-choice-matrix": "关键设计选择",
      "evidence-coverage": "设计信息公开情况",
      "criteria-comparison": "人群标准登记原文对照",
      "core-design-matrix": "核心设计事实比较",
      "trial-design-summary": "本试验全部设计字段",
      "design-fact-matrix": "设计事实比较"
    }[kind] || "试验设计比较";
    host.appendChild(title);
    var chart = document.createElement("div");
    chart.className = "kz-c-chart-canvas";
    chart.setAttribute("data-chart-type", kind);
    chart.setAttribute("role", "img");
    chart.setAttribute("aria-label", title.textContent);
    host.appendChild(chart);
    if (!rows.length) {
      chart.style.height = "auto";
      chart.setAttribute("role", "status");
      host.setAttribute("data-grid-span", "12");
      chart.textContent = "当前筛选条件下暂无可显示的设计信息";
      return;
    }
    if (sourceComparison) {
      host.setAttribute("data-grid-span", "12");
      renderCriteriaSources(chart, rows, !criteriaPage);
      return;
    }
    if (kind === "design-choice-matrix" && rows.every(function (row) {
      return row.disclosure_state === "reported_value" || row.disclosure_state === "reported_zero";
    })) {
      // Every heatmap cell would have the same disclosure color. Show the
      // substantive design choices instead; every observation remains linked.
      chart.setAttribute("data-chart-type", "design-choice-summary");
      chart.setAttribute("role", "region");
      chart.classList.add("kz-c-chart-canvas--design-summary");
      host.setAttribute("data-grid-span", "12");
      var note = document.createElement("p");
      note.className = "kz-c-design-summary__note";
      note.textContent = "这些研究均已公开所列设计要素；按研究对照具体定义，点击任一条查看来源。";
      chart.appendChild(note);
      var grid = document.createElement("div");
      grid.className = "kz-c-design-summary__grid";
      var trialIds = uniqueValues(rows, "trial_display_id");
      trialIds.forEach(function (trialId) {
        var trialRows = rows.filter(function (row) {
          return String(row.trial_display_id || "") === trialId;
        });
        var card = document.createElement("section");
        card.className = "kz-c-design-summary__trial";
        var heading = document.createElement("h3");
        heading.textContent = String(trialRows[0].product_zh || "产品未列示")
          + "｜" + String(trialId || "试验未列示");
        card.appendChild(heading);
        var list = document.createElement("ul");
        trialRows.forEach(function (row) {
          var item = document.createElement("li");
          var button = document.createElement("button");
          button.type = "button";
          button.setAttribute("data-evidence-open", String(row.row_id));
          button.setAttribute("data-row-id", String(row.row_id));
          button.textContent = String(row.element_zh || row.display_label_zh || "设计要素")
            + "：" + String(row.value == null ? row.status || "未列示" : row.value);
          item.appendChild(button);
          list.appendChild(item);
        });
        card.appendChild(list);
        grid.appendChild(card);
      });
      chart.appendChild(grid);
      return;
    }
    if (typeof sharedPresentationPlan !== "function") {
      chart.setAttribute("role", "status");
      chart.textContent = "图形组件未就绪；完整设计资料仍可在下方查阅";
      return;
    }
    var option = kind === "sample-size-bar"
        ? sampleOption(rows)
      : kind === "criteria-comparison"
        ? criteriaCountOption(rows)
      : kind === "visit-timeline"
        ? timelineOption(rows)
        : kind === "evidence-coverage"
            ? evidenceOption(rows)
            : matrixOption(rows, kind, chart && chart.clientWidth ? chart.clientWidth : 900);
    var glyphCount = 0;
    var paintedLines = 1;
    (option.series || []).forEach(function (series) {
      glyphCount += (series.data || []).length;
      if (series.label && typeof series.label.formatter === "function") {
        (series.data || []).forEach(function (point) {
          paintedLines = Math.max(paintedLines,
            String(series.label.formatter({data: point})).split("\n").length);
        });
      }
    });
    var plan = sharedPresentationPlan({rows: rows, design_layout: {
      kind: kind, x_labels: option.xAxis.data || [], y_labels: option.yAxis.data || [],
      row_height: Math.max(32, paintedLines * 23 + 12),
      axis_inset: Number(option.grid.top || 0) + Number(option.grid.bottom || 0),
      glyph_count: glyphCount, series_count: option.series.length
    }});
    host.setAttribute("data-grid-span", String(plan.grid_span));
    host.setAttribute("data-observation-count", String(plan.observation_count));
    chart.style.height = plan.target_height + "px";
    chartState.rows = rows.slice();
    chartState.kind = kind;
    chartState.chart = chart;
    chartContainerWidth = chart.clientWidth;
    cChart = window.echarts.init(chart, null, {renderer: "svg"});
    cChart.setOption(option);
    cChart.on("click", function (params) {
      var rowId = params.data && params.data.rowId;
      var drawer = window.__EVIDENCE_DRAWER__;
      if (rowId && drawer && typeof drawer.openByRowId === "function") {
        drawer.openByRowId(rowId, chart);
      }
    });
  }

  function resizeCChart() {
    if (!cChart || !chartState.chart) return;
    var width = chartState.chart.clientWidth;
    cChart.resize();
    // Width-driven matrix redraw must reuse the current query filter.
    // Reconstructing from chartState.rows alone restores excluded studies and
    // can repaint a chart that updateChartFromState already cleared.
    if (chartState.kind === "core-design-matrix" && width > 0
        && width !== chartContainerWidth) {
      chartContainerWidth = width;
      updateChartFromState(sanitizeState(selectedState()));
    }
  }

  function placeDesignPathsBetweenChartAndTable() {
    var paths = document.getElementById("kz-design-paths");
    var module = document.getElementById("kz-chart-module");
    var table = module && module.querySelector(".kz-chart-table");
    if (!paths || !module || !table) return;
    var anchor = table.closest(".kz-complete-table") || table;
    if (anchor.parentNode === module) module.insertBefore(paths, anchor);
  }

  function start() {
    if (started) return;
    started = true;
    // Personal reuse may restore the URL after this script was loaded, but
    // before the first render. Read the current query rather than stale input.
    var restoredCriteria = new URLSearchParams(window.location.search || "");
    criteriaSearchQuery = restoredCriteria.get("criteria_q") || "";
    excludedCriteriaTrials = {};
    restoredCriteria.getAll("criteria_hide").forEach(function (trialId) {
      excludedCriteriaTrials[trialId] = true;
    });
    removeSharedHash();
    syncComparisonChrome();
    decorateRows();
    renderCChart();
    placeDesignPathsBetweenChartAndTable();
    var state = sanitizeState(selectedState());
    applyButtonState(state);
    applyState(state);
    bindFilterButtons();
    bindMatrixGroupToggles();
    bindEvidenceTriggers();
    document.addEventListener("kz-evidence-drawer-change", function (event) {
      var detail = (event && event.detail) || {};
      writeFocusUrl(detail.openRowId || "");
    });
    restoreFocusFromUrl();
    window.addEventListener("resize", resizeCChart);
    if (typeof ResizeObserver === "function") {
      var observer = new ResizeObserver(resizeCChart);
      var chartHost = document.getElementById("kz-c-chart-visuals");
      if (chartHost) observer.observe(chartHost);
      window.addEventListener("pagehide", function () { observer.disconnect(); }, {once: true});
    }
  }

  function scheduleStart() {
    window.setTimeout(start, 0);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", scheduleStart);
  } else {
    scheduleStart();
  }

  window.__CHART_SYNC__ = {
    presentationPlan: sharedPresentationPlan,
    syncWithFilter: renderCChart,
    clearSelection: function () {},
    selectByRowId: function () {},
    supportedChartTypes: function () {
      return [
        "core-design-matrix",
        "trial-design-summary",
        "design-fact-matrix",
        "criteria-comparison",
        "treatment-structure-matrix",
        "endpoint-timepoint-matrix",
        "visit-timeline",
        "sample-size-bar",
        "design-choice-matrix",
        "evidence-coverage"
      ];
    }
  };
  window.__C_PERSONAL_QUERY_VALUES__ = function () {
    if (!usesSourceComparison(window.__C_PAGE_ID__ || "")) return {};
    var trials = Object.create(null);
    allChartRows().forEach(function (row) {
      if (row.trial_display_id) trials[String(row.trial_display_id)] = true;
    });
    return {criteria_q: null, criteria_hide: trials};
  };
})();
