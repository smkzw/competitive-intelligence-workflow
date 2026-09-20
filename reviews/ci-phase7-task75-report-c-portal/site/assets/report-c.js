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
    if (
      window.__CHART_SYNC__ &&
      typeof window.__CHART_SYNC__.syncWithFilter === "function"
    ) {
      window.__CHART_SYNC__.syncWithFilter();
    }
    updateStatus(state);
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
    if (pageId === "sample-analysis-statistics") return "sample-size-bar";
    if (pageId === "visit-duration-followup") return "visit-timeline";
    if (pageId === "endpoint-timepoint-matrix") return "endpoint-timepoint-matrix";
    if (pageId === "treatment-arms") return "treatment-structure-matrix";
    if (pageId === "design-patterns") return "design-choice-matrix";
    if (pageId === "evidence-versions-limitations") return "evidence-coverage";
    if (
      pageId === "population-disease-definition" ||
      pageId === "inclusion-criteria" ||
      pageId === "exclusion-criteria"
    ) return "criteria-comparison";
    return "design-fact-matrix";
  }

  function trialLabel(row) {
    var id = String(row.trial_display_id || "试验");
    var name = String(row.trial_zh || "");
    if (name.indexOf("奈莫利珠单抗") !== -1) name = "奈莫利珠单抗研究";
    if (name.length > 12) name = name.slice(0, 11) + "…";
    return name && name !== id ? id + "\n" + name : id;
  }

  function coreDesignRows(rows) {
    var fields = [
      "target_population",
      "dosing_regimen",
      "primary_endpoint_definition",
      "planned_or_actual_sample_size"
    ];
    return rows.filter(function (row) {
      return fields.indexOf(String(row.element || "")) !== -1;
    });
  }

  function tooltipHtml(row) {
    if (!row) return "";
    return [
      "<strong>" + String(row.trial_display_id || row.trial_zh || "试验") + "</strong>",
      String(row.element_zh || row.display_label_zh || "设计要素"),
      String(row.value === null || row.value === undefined ? row.status || "未公开" : row.value),
      row.time && row.time !== "时间点未列示" ? "时间点：" + String(row.time) : ""
    ].filter(Boolean).join("<br>");
  }

  function matrixOption(rows, kind) {
    if (kind === "core-design-matrix" || kind === "trial-design-summary") {
      rows = coreDesignRows(rows);
    }
    var trialIds = uniqueValues(rows, "trial_display_id");
    var trialLabels = trialIds.map(function (trialId) {
      var row = rows.find(function (item) { return item.trial_display_id === trialId; });
      return trialLabel(row || {trial_display_id: trialId});
    });
    var elements = uniqueValues(rows, "element_zh");
    function compactFact(row) {
      var value = String(row.value === null || row.value === undefined ? row.status || "未公开" : row.value);
      var clinicalStructure = (
        kind === "core-design-matrix" ||
        kind === "trial-design-summary" ||
        kind === "treatment-structure-matrix"
      );
      var lineLength = clinicalStructure ? 18 : elements.length <= 2 ? 18 : elements.length <= 4 ? 14 : 8;
      var maxLines = clinicalStructure ? 4 : elements.length <= 4 ? 3 : 2;
      var separator = value.indexOf("；") !== -1 ? "；" : value.indexOf(" ") !== -1 ? " " : "";
      var units = separator ? value.split(separator).filter(Boolean) : [value];
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
    var data = rows.map(function (row) {
      var reported = row.disclosure_state === "reported_value" || row.disclosure_state === "reported_zero";
      return {
        value: [elements.indexOf(String(row.element_zh || "未列示")), trialIds.indexOf(String(row.trial_display_id || "未列示")), reported ? 1 : 0],
        rowId: row.row_id,
        row: row,
        itemStyle: {
          color: reported ? (trialIds.indexOf(String(row.trial_display_id || "")) % 2 ? "#FFF8EC" : "#FFF1D6") : "#EEF1F5",
          borderColor: "#FFFFFF",
          borderWidth: 3
        }
      };
    });
    return {
      animationDuration: 280,
      grid: {left: 146, right: 18, top: 24, bottom: elements.length > 5 ? 76 : 54},
      tooltip: {trigger: "item", confine: true, formatter: function (p) { return tooltipHtml(p.data.row); }},
      xAxis: {
        type: "category",
        data: elements,
        axisLine: {lineStyle: {color: "#C9D0DA"}},
        axisTick: {show: false},
        axisLabel: {color: "#405066", interval: 0, rotate: elements.length > 6 ? 24 : 0, fontSize: 11}
      },
      yAxis: {
        type: "category",
        data: trialLabels,
        axisLine: {show: false},
        axisTick: {show: false},
        axisLabel: {color: "#243650", fontWeight: 600, fontSize: 11, lineHeight: 15}
      },
      series: [{
        name: kind,
        type: "heatmap",
        data: data,
        label: {
          show: true,
          color: "#243650",
          fontSize: elements.length <= 2 ? 12 : elements.length <= 4 ? 11 : 10,
          lineHeight: elements.length <= 2 ? 16 : 14,
          formatter: function (p) {
            if (!p.data.value[2]) return "未公开";
            return compactFact(p.data.row);
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
      "core-design-matrix": "核心设计差异",
      "trial-design-summary": "本试验核心设计",
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
    chart.style.height = Math.max(280, Math.min(360, uniqueValues(rows, "trial_display_id").length * 52 + 150)) + "px";
    cChart = window.echarts.init(chart, null, {renderer: "svg"});
    var option = kind === "sample-size-bar"
      ? sampleOption(rows)
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
    if (paths && module && table) module.insertBefore(paths, table);
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
