/* C 类门户联动：页面/模块筛选、URL 恢复、试验身份装饰；不计算科学事实。 */
(function () {
  "use strict";

  var started = false;

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
    status.textContent = selected
      ? "已选 " + selected + " 项，显示 " + visible + " 条记录"
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
        var pid = el.getAttribute("data-product-id");
        var tid = el.getAttribute("data-trial-id");
        var show = true;
        if (productFilter.length && pid) {
          show = productFilter.indexOf(pid) !== -1;
        }
        if (show && trialFilter.length && tid) {
          show = trialFilter.indexOf(tid) !== -1;
        }
        el.style.display = show ? "" : "none";
      }
    } else {
      var keyed2 = document.querySelectorAll('[data-product-id][style], [data-trial-id][style]');
      for (var r = 0; r < keyed2.length; r += 1) keyed2[r].style.display = "";
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
    if (!cChart || !chartState.rows.length) return;
    var visible = chartState.rows.filter(function (row) {
      return matches(String(row.row_id), state);
    });
    if (!visible.length) visible = chartState.rows.slice();
    var kind = chartState.kind;
    var option = kind === "sample-size-bar" ? sampleOption(visible)
      : kind === "criteria-comparison" ? criteriaCountOption(visible)
      : kind === "visit-timeline" ? timelineOption(visible)
      : kind === "evidence-coverage" ? evidenceOption(visible)
      : matrixOption(visible, kind);
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
  var chartState = {rows: [], kind: "", chart: null};

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

  function trialLabel(row) {
    var id = String(row.trial_display_id || "试验");
    var product = String(row.product_zh || "");
    var name = String(row.trial_zh || "");
    if (name.indexOf("奈莫利珠单抗") !== -1) name = "奈莫利珠单抗研究";
    if (product.length > 14) product = product.slice(0, 13) + "…";
    if (name.length > 12) name = name.slice(0, 11) + "…";
    var identity = product && product !== name ? product + "\n" + id : id;
    return name && name !== id ? identity + "\n" + name : identity;
  }


  function tooltipHtml(row) {
    if (!row) return "";
    return [
      "<strong>" + String(row.product_zh || "产品未列示") + "</strong>",
      String(row.trial_display_id || row.trial_zh || "试验"),
      row.trial_zh && row.trial_zh !== row.trial_display_id ? String(row.trial_zh) : "",
      String(row.field_family_zh || "设计事实"),
      String(row.element_zh || row.display_label_zh || "设计要素"),
      String(row.value === null || row.value === undefined ? row.status || "未公开" : row.value),
      row.scale ? "量表：" + String(row.scale) : "",
      row.time && row.time !== "时间点未列示" ? "时间点：" + String(row.time) : "",
      row.group_zh && row.group_zh !== "组别未细分" ? "组别：" + String(row.group_zh) : ""
    ].filter(Boolean).join("<br>");
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

  function matrixOption(rows, kind) {
    var trialIds = uniqueValues(rows, "trial_display_id");
    var compactTrialAxis = kind === "core-design-matrix";
    var trialLabels = trialIds.map(function (trialId) {
      var row = rows.find(function (item) { return item.trial_display_id === trialId; });
      return compactTrialAxis ? trialId : trialLabel(row || {trial_display_id: trialId});
    });
    var elements = uniqueValues(rows, "element_zh");
    var data = rows.map(function (row) {
      var reported = row.disclosure_state === "reported_value" || row.disclosure_state === "reported_zero";
      return {
        value: [
          trialIds.indexOf(String(row.trial_display_id || "未列示")),
          elements.indexOf(String(row.element_zh || "未列示")),
          reported ? 1 : 0
        ],
        rowId: row.row_id,
        row: row,
        itemStyle: {
          color: reported
            ? (elements.indexOf(String(row.element_zh || "")) % 2 ? "#FFF8EC" : "#FFF1D6")
            : "#EEF1F5",
          borderColor: "#FFFFFF",
          borderWidth: 3
        }
      };
    });
    return {
      animationDuration: 280,
      grid: {
        left: 178,
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
          rotate: compactTrialAxis && trialIds.length > 8
            ? 48
            : (trialIds.length > 3 ? 24 : 0),
          fontSize: 12,
          width: compactTrialAxis ? 90 : 160,
          overflow: "break",
          lineHeight: 15,
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
          fontSize: 12,
          width: 150,
          overflow: "break",
          lineHeight: 15
        }
      },
      series: [{
        name: "设计事实",
        type: "heatmap",
        data: data,
        label: {
          show: true,
          color: "#243650",
          fontSize: 12,
          lineHeight: 14,
          // 独立视觉复核（typography/charts）：单元格长文本限宽截断，
          // 完整内容保留在 tooltip 与同源数据表
          width: compactTrialAxis ? 86 : Math.min(150, Math.max(72, Math.round(640 / Math.max(1, trialIds.length)))),
          overflow: "truncate",
          formatter: function (p) {
            return p.data.value[2] ? matrixLabel(p.data.row) : "未公开";
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
          fontSize: 13,
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
    var rows = visibleChartRows();
    window.__C_VISIBLE_CHART_ROW_IDS__ = rows.map(function (row) {
      return String(row.row_id);
    });
    var kind = chartKind(window.__C_PAGE_ID__ || "");
    if (cChart) {
      cChart.dispose();
      cChart = null;
    }
    host.innerHTML = "";
    var title = document.createElement("div");
    title.className = "kz-c-chart-title";
    title.textContent = {
      "sample-size-bar": "各试验样本量",
      "visit-timeline": "关键评估与随访时间",
      "endpoint-timepoint-matrix": "主要终点与评估时间",
      "treatment-structure-matrix": "分组、干预与给药结构",
      "design-choice-matrix": "关键设计选择",
      "evidence-coverage": "设计信息公开情况",
      "criteria-comparison": "人群标准结构比较",
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
      chart.textContent = "当前筛选条件下暂无可显示的设计信息";
      return;
    }
    var elementCount = uniqueValues(rows, "element_zh").length;
    var matrixHeight = kind === "criteria-comparison"
      ? rows.length * 36 + 88
      : elementCount * (elementCount <= 4 ? 58 : 66) + 150;
    chart.style.height = Math.max(360, Math.min(1800, matrixHeight)) + "px";
    chartState.rows = rows.slice();
    chartState.kind = kind;
    chartState.chart = chart;
    cChart = window.echarts.init(chart, null, {renderer: "svg"});
    var option = kind === "sample-size-bar"
        ? sampleOption(rows)
      : kind === "criteria-comparison"
        ? criteriaCountOption(rows)
      : kind === "visit-timeline"
        ? timelineOption(rows)
        : kind === "evidence-coverage"
            ? evidenceOption(rows)
            : matrixOption(rows, kind);
    cChart.setOption(option);
    cChart.on("click", function (params) {
      var rowId = params.data && params.data.rowId;
      var drawer = window.__EVIDENCE_DRAWER__;
      if (rowId && drawer && typeof drawer.openByRowId === "function") {
        drawer.openByRowId(rowId, chart);
      }
    });
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
    removeSharedHash();
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
    window.addEventListener("resize", function () {
      if (cChart) cChart.resize();
    });
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
})();
