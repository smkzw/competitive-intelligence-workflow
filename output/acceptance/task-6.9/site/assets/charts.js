/**
 * Task 4.4 — 离线 ECharts 九类图形、小多图与图表-表格双向联动。
 * 仅使用打包 ECharts；缺失行 value=null + status，不得转 0。
 */
(function () {
  "use strict";

  var ECHARTS_READY =
    typeof window.echarts !== "undefined" && typeof window.echarts.init === "function";

  var chartGroups = window.__CHART_GROUPS__ || [];
  var filterRows = window.__FILTER_ROWS__ || [];
  var rowSetDigest = window.__ROW_SET_DIGEST__ || "";
  var snapshotId = window.__SNAPSHOT_ID__ || "";

  var selectedRowId = null;
  var chartInstances = {};
  var chartRowMap = {};
  var chartRowIdsByGroup = {};
  var chartTypeByGroup = {};
  var rowElementMap = {};
  var optionCache = {};

  var CHART_TYPES = {
    bar: true,
    line: true,
    forest: true,
    heatmap: true,
    bubble: true,
    scatter_interval: true,
    timeline: true,
    radar: true,
    status_matrix: true
  };

  function disclosureLabelZh(state) {
    if (state === "not_publicly_disclosed") return "未公开";
    if (state === "not_reported") return "未报告";
    if (state === "not_applicable") return "不适用";
    if (state === "below_reporting_threshold") return "低于报告阈值";
    if (state === "unresolved_due_to_route") return "路径未解析";
    if (state === "conflicting" || state === "conflicting_sources") return "来源冲突";
    return "未公开";
  }

  function isRenderable(row) {
    return row && row.renderable !== false;
  }

  function armLabel(row) {
    if (row.category === "治疗组" || row.category === "对照组") return row.category;
    var gid = String(row.group_id || "");
    if (gid.indexOf("treat") !== -1) return "治疗组";
    if (gid.indexOf("ctrl") !== -1) return "对照组";
    return row.category || "";
  }

  function groupHasRenderable(group) {
    for (var i = 0; i < group.rows.length; i++) {
      if (isRenderable(group.rows[i])) return true;
    }
    return false;
  }

  function visibleRowIdsInDom() {
    var visible = [];
    var rows = document.querySelectorAll(".kz-chart-table__row");
    for (var i = 0; i < rows.length; i++) {
      if (rows[i].style.display !== "none") {
        visible.push(rows[i].getAttribute("data-row-id"));
      }
    }
    return visible;
  }

  function nullPoint(row) {
    var status = row.disclosure_state || "not_publicly_disclosed";
    return {
      value: null,
      status: status,
      statusLabel: disclosureLabelZh(status),
      itemStyle: { color: "#D1D5DB", opacity: 0.55 },
      label: {
        show: true,
        formatter: disclosureLabelZh(status),
        color: "#6B7280",
        fontSize: 14
      }
    };
  }

  function collectRowIds(group) {
    var ids = [];
    for (var i = 0; i < group.rows.length; i++) ids.push(group.rows[i].row_id);
    return ids;
  }

  function withMeta(option, rowIds) {
    option.animation = false;
    option._rowIds = rowIds;
    option._snapshotId = snapshotId;
    option._rowSetDigest = rowSetDigest;
    return option;
  }

  function buildBarOption(group) {
    var categories = [];
    var seriesData = [];
    var rowIds = collectRowIds(group);
    var unitLabel = "";
    var treatColor = "#FF9900";
    var ctrlColor = "#407AAA";
    for (var i = 0; i < group.rows.length; i++) {
      var row = group.rows[i];
      var arm = armLabel(row);
      categories.push(arm || row.display_label_zh || "");
      if (!unitLabel && row.unit) unitLabel = row.unit;
      if (!isRenderable(row)) seriesData.push(nullPoint(row));
      else {
        var v = row.numeric_value != null ? row.numeric_value : row.value;
        seriesData.push({
          value: v,
          status: null,
          itemStyle: { color: arm === "对照组" ? ctrlColor : treatColor },
          label: {
            show: true,
            position: v < 0 ? "insideBottom" : "top",
            formatter: String(v),
            color: v < 0 ? "#FFFFFF" : "#0F1115",
            fontSize: 14,
            fontWeight: 600
          }
        });
      }
    }
    return withMeta(
      {
        tooltip: { trigger: "item", show: false },
        grid: { left: 56, right: 24, top: 36, bottom: 48, containLabel: true },
        xAxis: {
          type: "category",
          data: categories,
          axisLabel: { interval: 0, hideOverlap: true, fontSize: 14 }
        },
        yAxis: {
          type: "value",
          name: unitLabel,
          axisLabel: { fontSize: 14 },
          scale: false,
          min: function (extent) {
            if (typeof group.y_axis_min === "number") return group.y_axis_min;
            return Math.min(0, extent.min);
          },
          max: function (extent) {
            if (typeof group.y_axis_max === "number") return group.y_axis_max;
            return Math.max(0, extent.max);
          },
          axisLine: { show: true, onZero: true },
          splitLine: { show: true }
        },
        series: [
          {
            name: "比较值",
            type: "bar",
            data: seriesData,
            barMaxWidth: 64,
            emphasis: {
              focus: "self",
              itemStyle: {
                borderColor: "#0F1115",
                borderWidth: 2,
                shadowBlur: 4,
                shadowColor: "rgba(15,17,21,0.16)"
              }
            }
          }
        ]
      },
      rowIds
    );
  }

  function buildLineOption(group) {
    var times = [];
    var seriesData = [];
    var rowIds = collectRowIds(group);
    for (var i = 0; i < group.rows.length; i++) {
      var row = group.rows[i];
      times.push(row.time || row.display_label_zh || "");
      if (!isRenderable(row)) seriesData.push(nullPoint(row));
      else {
        var v = row.numeric_value != null ? row.numeric_value : row.value;
        seriesData.push({ value: v, status: null });
      }
    }
    return withMeta(
      {
        tooltip: { trigger: "axis" },
        grid: { left: 56, right: 24, top: 40, bottom: 40, containLabel: true },
        xAxis: {
          type: "category",
          data: times,
          boundaryGap: false,
          axisLabel: { fontSize: 14 }
        },
        yAxis: {
          type: "value",
          scale: true,
          axisLabel: { fontSize: 14 },
          min: typeof group.y_axis_min === "number" ? group.y_axis_min : null,
          max: typeof group.y_axis_max === "number" ? group.y_axis_max : null
        },
        series: [{ name: "趋势", type: "line", data: seriesData, connectNulls: false }]
      },
      rowIds
    );
  }

  function buildForestOption(group) {
    var categories = [];
    var scatterData = [];
    var ciData = [];
    var rowIds = collectRowIds(group);
    for (var i = 0; i < group.rows.length; i++) {
      var row = group.rows[i];
      categories.push(row.display_label_zh || "");
      if (!isRenderable(row)) {
        scatterData.push({ value: null, status: row.disclosure_state });
        ciData.push({ value: [null, null, i], status: row.disclosure_state });
      } else {
        var effect = row.numeric_value != null ? row.numeric_value : row.effect;
        scatterData.push({ value: [effect, i], status: null });
        ciData.push({
          value: [row.ci_lower, row.ci_upper, i],
          status: null
        });
      }
    }
    return withMeta(
      {
        tooltip: { trigger: "item" },
        grid: { left: 120, right: 40, top: 24, bottom: 32, containLabel: true },
        xAxis: { type: "value", name: "效应值", axisLabel: { fontSize: 14 } },
        yAxis: {
          type: "category",
          data: categories,
          inverse: true,
          axisLabel: { fontSize: 14 }
        },
        series: [
          {
            name: "置信区间",
            type: "custom",
            renderItem: function (params, api) {
              var lower = api.value(0);
              var upper = api.value(1);
              var cat = api.value(2);
              if (lower == null || upper == null) return null;
              var p0 = api.coord([lower, cat]);
              var p1 = api.coord([upper, cat]);
              return {
                type: "group",
                children: [
                  {
                    type: "line",
                    shape: { x1: p0[0], y1: p0[1], x2: p1[0], y2: p1[1] },
                    style: { stroke: "#6B7280", lineWidth: 2 }
                  },
                  {
                    type: "line",
                    shape: { x1: p0[0], y1: p0[1] - 5, x2: p0[0], y2: p0[1] + 5 },
                    style: { stroke: "#6B7280", lineWidth: 2 }
                  },
                  {
                    type: "line",
                    shape: { x1: p1[0], y1: p1[1] - 5, x2: p1[0], y2: p1[1] + 5 },
                    style: { stroke: "#6B7280", lineWidth: 2 }
                  }
                ]
              };
            },
            data: ciData,
            encode: { x: [0, 1], y: 2 },
            z: 1
          },
          {
            name: "效应点",
            type: "scatter",
            data: scatterData,
            symbolSize: 10,
            itemStyle: { color: "#FF9900" },
            z: 2
          }
        ]
      },
      rowIds
    );
  }

  function buildHeatmapOption(group) {
    var events = [];
    var seriesData = [];
    var rowIds = collectRowIds(group);
    var maxAbs = 1;
    for (var i = 0; i < group.rows.length; i++) {
      var row = group.rows[i];
      events.push(row.event || row.display_label_zh || "");
      if (!isRenderable(row)) {
        seriesData.push({ value: [0, i, null], status: row.disclosure_state });
      } else {
        var matrix = row.value_matrix;
        var cell = Array.isArray(matrix) ? matrix[0] : matrix;
        var num = typeof cell === "number" ? cell : Number(cell);
        if (!isFinite(num)) num = null;
        if (num != null && Math.abs(num) > maxAbs) maxAbs = Math.abs(num);
        seriesData.push({ value: [0, i, num], status: null });
      }
    }
    return withMeta(
      {
        tooltip: { position: "top" },
        grid: { left: 100, right: 40, top: 24, bottom: 40, containLabel: true },
        xAxis: {
          type: "category",
          data: ["比较"],
          axisLabel: { fontSize: 14 }
        },
        yAxis: {
          type: "category",
          data: events,
          inverse: true,
          axisLabel: { fontSize: 14 }
        },
        visualMap: {
          min: -maxAbs,
          max: maxAbs,
          calculable: false,
          orient: "horizontal",
          left: "center",
          bottom: 0,
          inRange: { color: ["#DBEAFE", "#FF9900"] },
          show: true
        },
        series: [
          {
            name: "热图",
            type: "heatmap",
            data: seriesData,
            label: {
              show: true,
              formatter: function (p) {
                return p.value[2] == null
                  ? disclosureLabelZh(
                      (group.rows[p.value[1]] && group.rows[p.value[1]].disclosure_state) ||
                        "not_publicly_disclosed"
                    )
                  : String(p.value[2]);
              }
            }
          }
        ]
      },
      rowIds
    );
  }

  function buildBubbleOption(group) {
    var seriesData = [];
    var rowIds = collectRowIds(group);
    for (var i = 0; i < group.rows.length; i++) {
      var row = group.rows[i];
      if (!isRenderable(row)) {
        seriesData.push({
          value: null,
          status: row.disclosure_state,
          statusLabel: disclosureLabelZh(row.disclosure_state)
        });
      } else {
        seriesData.push({
          value: [row.x_value, row.y_value, row.size],
          status: null,
          symbolSize: Math.max(8, Math.min(48, Number(row.size) || 8))
        });
      }
    }
    return withMeta(
      {
        tooltip: { trigger: "item" },
        grid: { left: 56, right: 24, top: 32, bottom: 40, containLabel: true },
        xAxis: { type: "value", name: "横轴", axisLabel: { fontSize: 14 } },
        yAxis: {
          type: "value",
          name: "纵轴",
          scale: true,
          axisLabel: { fontSize: 14 }
        },
        series: [
          {
            name: "气泡",
            type: "scatter",
            data: seriesData,
            itemStyle: { color: "#FF9900", opacity: 0.75 }
          }
        ]
      },
      rowIds
    );
  }

  function buildScatterIntervalOption(group) {
    var categories = [];
    var centers = [];
    var intervals = [];
    var rowIds = collectRowIds(group);
    for (var i = 0; i < group.rows.length; i++) {
      var row = group.rows[i];
      categories.push(row.display_label_zh || "");
      if (!isRenderable(row)) {
        centers.push({ value: null, status: row.disclosure_state });
        intervals.push({ value: [null, null, i], status: row.disclosure_state });
      } else {
        var upper =
          row.ci_upper != null ? row.ci_upper : Number(row.center) + Number(row.ci_lower);
        var lower =
          row.ci_lower_abs != null
            ? row.ci_lower_abs
            : Number(row.center) - Math.abs(Number(row.ci_lower));
        centers.push({ value: [row.center, i], status: null });
        intervals.push({ value: [lower, upper, i], status: null });
      }
    }
    return withMeta(
      {
        tooltip: { trigger: "item" },
        grid: { left: 120, right: 40, top: 24, bottom: 32, containLabel: true },
        xAxis: { type: "value", name: "估计值", axisLabel: { fontSize: 14 } },
        yAxis: {
          type: "category",
          data: categories,
          inverse: true,
          axisLabel: { fontSize: 14 }
        },
        series: [
          {
            name: "区间",
            type: "custom",
            renderItem: function (params, api) {
              var lo = api.value(0);
              var hi = api.value(1);
              var cat = api.value(2);
              if (lo == null || hi == null) return null;
              var p0 = api.coord([lo, cat]);
              var p1 = api.coord([hi, cat]);
              return {
                type: "line",
                shape: { x1: p0[0], y1: p0[1], x2: p1[0], y2: p1[1] },
                style: { stroke: "#9CA3AF", lineWidth: 3 }
              };
            },
            data: intervals,
            encode: { x: [0, 1], y: 2 }
          },
          {
            name: "中心点",
            type: "scatter",
            data: centers,
            symbolSize: 9,
            itemStyle: { color: "#FF9900" }
          }
        ]
      },
      rowIds
    );
  }

  function buildTimelineOption(group) {
    var times = [];
    var seriesData = [];
    var rowIds = collectRowIds(group);
    for (var i = 0; i < group.rows.length; i++) {
      var row = group.rows[i];
      times.push(row.time || "");
      if (!isRenderable(row)) seriesData.push(nullPoint(row));
      else {
        var statusText = row.status || "";
        seriesData.push({
          value: i + 1,
          status: null,
          name: statusText,
          label: { show: true, formatter: statusText, position: "top", fontSize: 14 }
        });
      }
    }
    return withMeta(
      {
        tooltip: { trigger: "axis" },
        grid: { left: 40, right: 24, top: 48, bottom: 40, containLabel: true },
        xAxis: { type: "category", data: times, axisLabel: { fontSize: 14 } },
        yAxis: { type: "value", show: false, min: 0, max: group.rows.length + 1 },
        series: [
          {
            name: "时间线",
            type: "line",
            data: seriesData,
            symbol: "circle",
            symbolSize: 14,
            lineStyle: { color: "#FF9900", width: 2 },
            itemStyle: { color: "#FF9900" }
          }
        ]
      },
      rowIds
    );
  }

  function buildRadarOption(group) {
    var rowIds = collectRowIds(group);
    var indicators = [];
    var seriesData = [];
    var firstDims = null;
    for (var i = 0; i < group.rows.length; i++) {
      var row = group.rows[i];
      if (isRenderable(row) && Array.isArray(row.dimensions) && !firstDims) {
        firstDims = row.dimensions;
      }
    }
    if (!firstDims) firstDims = ["维度甲", "维度乙", "维度丙"];
    for (var d = 0; d < firstDims.length; d++) {
      indicators.push({ name: String(firstDims[d]), max: 100 });
    }
    for (var j = 0; j < group.rows.length; j++) {
      var r = group.rows[j];
      if (!isRenderable(r)) {
        seriesData.push({
          value: null,
          name: r.display_label_zh || "",
          status: r.disclosure_state,
          statusLabel: disclosureLabelZh(r.disclosure_state)
        });
      } else {
        seriesData.push({
          value: r.scores,
          name: r.display_label_zh || "",
          status: null
        });
      }
    }
    return withMeta(
      {
        tooltip: {},
        radar: { indicator: indicators },
        series: [{ name: "雷达", type: "radar", data: seriesData }]
      },
      rowIds
    );
  }

  function buildStatusMatrixOption(group) {
    var labels = [];
    var seriesData = [];
    var rowIds = collectRowIds(group);
    for (var i = 0; i < group.rows.length; i++) {
      var row = group.rows[i];
      labels.push(row.trial_zh || row.display_label_zh || "");
      if (!isRenderable(row)) {
        seriesData.push({ value: [0, i, null], status: row.disclosure_state });
      } else {
        var cov = row.coverage;
        var num = typeof cov === "number" ? cov : Number(cov);
        seriesData.push({ value: [0, i, isFinite(num) ? num : null], status: null });
      }
    }
    return withMeta(
      {
        tooltip: {
          formatter: function (p) {
            var row = group.rows[p.value[1]];
            if (!row) return "";
            if (!isRenderable(row)) return disclosureLabelZh(row.disclosure_state);
            return (row.status || "") + " · 覆盖 " + String(p.value[2]);
          }
        },
        grid: { left: 120, right: 40, top: 24, bottom: 32, containLabel: true },
        xAxis: {
          type: "category",
          data: ["状态"],
          axisLabel: { fontSize: 14 }
        },
        yAxis: {
          type: "category",
          data: labels,
          inverse: true,
          axisLabel: { fontSize: 14 }
        },
        visualMap: {
          min: 0,
          max: 1,
          show: false,
          inRange: { color: ["#F3F4F6", "#FF9900"] }
        },
        series: [
          {
            name: "状态矩阵",
            type: "heatmap",
            data: seriesData,
            label: {
              show: true,
              formatter: function (p) {
                var row = group.rows[p.value[1]];
                if (!row || !isRenderable(row)) {
                  return disclosureLabelZh(row && row.disclosure_state);
                }
                return String(row.status || "");
              }
            }
          }
        ]
      },
      rowIds
    );
  }

  function resolveChartType(group) {
    for (var i = 0; i < group.rows.length; i++) {
      var t = group.rows[i]._chart_type;
      if (t && CHART_TYPES[t]) return t;
    }
    return null;
  }

  function buildOption(group) {
    if (!group || !group.rows || group.rows.length === 0) return null;
    var chartType = resolveChartType(group);
    if (!chartType) {
      throw new Error("未知或未注册图形类型，失败关闭");
    }
    switch (chartType) {
      case "bar":
        return buildBarOption(group);
      case "line":
        return buildLineOption(group);
      case "forest":
        return buildForestOption(group);
      case "heatmap":
        return buildHeatmapOption(group);
      case "bubble":
        return buildBubbleOption(group);
      case "scatter_interval":
        return buildScatterIntervalOption(group);
      case "timeline":
        return buildTimelineOption(group);
      case "radar":
        return buildRadarOption(group);
      case "status_matrix":
        return buildStatusMatrixOption(group);
      default:
        throw new Error("未知图形类型：" + chartType);
    }
  }

  function renderArmLegend(container, group) {
    var seen = {};
    var arms = [];
    for (var i = 0; i < group.rows.length; i++) {
      var arm = armLabel(group.rows[i]);
      if (arm && !seen[arm]) {
        seen[arm] = true;
        arms.push(arm);
      }
    }
    if (!arms.length) return;
    var legend = document.createElement("div");
    legend.className = "kz-chart-legend";
    legend.setAttribute("aria-label", "组别图例");
    for (var j = 0; j < arms.length; j++) {
      var item = document.createElement("span");
      item.className = "kz-chart-legend__item";
      var swatch = document.createElement("span");
      swatch.className = "kz-chart-legend__swatch";
      swatch.style.background = arms[j] === "对照组" ? "#407AAA" : "#FF9900";
      item.appendChild(swatch);
      item.appendChild(document.createTextNode(arms[j]));
      legend.appendChild(item);
    }
    container.appendChild(legend);
  }

  function renderUndisclosedMessage(chartDiv) {
    chartDiv.classList.add("kz-chart-group__chart--undisclosed");
    chartDiv.style.height = "auto";
    chartDiv.style.minHeight = "0";
    var status = document.createElement("div");
    status.className = "kz-chart-undisclosed";
    status.setAttribute("role", "status");
    var p1 = document.createElement("p");
    p1.className = "kz-chart-undisclosed__title";
    p1.textContent = "该指标结果尚未公开";
    var p2 = document.createElement("p");
    p2.className = "kz-chart-undisclosed__hint";
    p2.textContent = "完整记录仍列于下方表格，便于核对来源与口径。";
    status.appendChild(p1);
    status.appendChild(p2);
    chartDiv.appendChild(status);
  }

  function renderChartContainer(container, groupIndex, group) {
    container.setAttribute("data-group-index", String(groupIndex));

    var title = document.createElement("h3");
    title.className = "kz-chart-group__title";
    var indicatorNames = [];
    var seenIndicators = {};
    for (var i = 0; i < group.rows.length; i++) {
      var indicatorName = String(group.rows[i].display_label_zh || "").trim();
      if (indicatorName && !seenIndicators[indicatorName]) {
        seenIndicators[indicatorName] = true;
        indicatorNames.push(indicatorName);
      }
    }
    var indicatorTitle = indicatorNames.length === 1 ? indicatorNames[0] : "多项可比指标";
    var dimensionTitle = group.title_zh || "";
    title.textContent =
      dimensionTitle && dimensionTitle !== "全部指标"
        ? indicatorTitle + "｜" + dimensionTitle
        : indicatorTitle;
    container.appendChild(title);
    if (groupHasRenderable(group) && resolveChartType(group) !== "status_matrix") {
      renderArmLegend(container, group);
    }

    var chartDiv = document.createElement("div");
    chartDiv.className = "kz-chart-group__chart";
    chartDiv.id = "kz-chart-" + groupIndex;
    var chartType = resolveChartType(group);
    if (chartType) chartDiv.setAttribute("data-chart-type", chartType);
    chartDiv.setAttribute("role", "img");
    chartDiv.setAttribute("aria-label", title.textContent + " 图形");
    if (!groupHasRenderable(group)) {
      renderUndisclosedMessage(chartDiv);
    } else {
      chartDiv.style.width = "100%";
      chartDiv.style.height = "340px";
    }
    container.appendChild(chartDiv);
    return chartDiv;
  }

  function renderTable(container, groupIndex, group) {
    var table = document.createElement("table");
    table.className = "kz-chart-table";
    table.id = "kz-table-" + groupIndex;
    table.setAttribute("data-group-index", String(groupIndex));

    var thead = document.createElement("thead");
    var headerRow = document.createElement("tr");
    var chartType = resolveChartType(group);
    var labelHeader = chartType === "status_matrix" ? "试验" : "指标名称";
    var valueHeader = chartType === "status_matrix" ? "试验状态" : "比较值";
    headerRow.innerHTML =
      '<th class="kz-chart-table__th">' + labelHeader + '</th>' +
      '<th class="kz-chart-table__th">组别</th>' +
      '<th class="kz-chart-table__th">' + valueHeader + '</th>' +
      '<th class="kz-chart-table__th">单位</th>' +
      '<th class="kz-chart-table__th">披露状态</th>';
    thead.appendChild(headerRow);
    table.appendChild(thead);

    var tbody = document.createElement("tbody");
    for (var i = 0; i < group.rows.length; i++) {
      var row = group.rows[i];
      var tr = document.createElement("tr");
      tr.className = "kz-chart-table__row";
      tr.setAttribute("data-row-id", row.row_id);
      tr.setAttribute("data-filter-row-id", row.row_id);
      tr.setAttribute("tabindex", "0");
      if (!isRenderable(row)) tr.classList.add("kz-chart-table__row--unrenderable");

      var tdLabel = document.createElement("td");
      tdLabel.className = "kz-chart-table__cell kz-chart-table__cell--label";
      tdLabel.textContent =
        chartType === "status_matrix"
          ? row.trial_zh || row.display_label_zh || ""
          : row.display_label_zh || "";
      tdLabel.setAttribute("data-evidence-field", "label");
      markEvidenceCell(tdLabel, row.row_id);
      tr.appendChild(tdLabel);

      var tdArm = document.createElement("td");
      tdArm.className = "kz-chart-table__cell kz-chart-table__cell--arm";
      tdArm.textContent = armLabel(row);
      tdArm.setAttribute("data-evidence-field", "group");
      markEvidenceCell(tdArm, row.row_id);
      tr.appendChild(tdArm);

      var tdValue = document.createElement("td");
      tdValue.className = "kz-chart-table__cell kz-chart-table__cell--value";
      if (!isRenderable(row)) {
        tdValue.textContent = "该指标结果尚未公开";
        tdValue.classList.add("kz-chart-table__cell--status");
      } else {
        var shown =
          row.numeric_value != null
            ? String(row.numeric_value)
            : row.value != null
              ? String(row.value)
              : row.effect != null
                ? String(row.effect)
                : row.status != null
                  ? String(row.status)
                  : Array.isArray(row.value_matrix)
                    ? String(row.value_matrix[0] == null ? "" : row.value_matrix[0])
                    : "";
        tdValue.textContent = shown;
      }
      tdValue.setAttribute("data-evidence-field", "value");
      markEvidenceCell(tdValue, row.row_id);
      tr.appendChild(tdValue);

      var tdUnit = document.createElement("td");
      tdUnit.className = "kz-chart-table__cell kz-chart-table__cell--unit";
      tdUnit.textContent = row.unit || "";
      tdUnit.setAttribute("data-evidence-field", "unit");
      markEvidenceCell(tdUnit, row.row_id);
      tr.appendChild(tdUnit);

      var tdStatus = document.createElement("td");
      tdStatus.className = "kz-chart-table__cell kz-chart-table__cell--disclosure";
      tdStatus.textContent = !isRenderable(row) ? "该指标结果尚未公开" : "已披露";
      if (!isRenderable(row)) tdStatus.classList.add("kz-chart-table__cell--unrenderable");
      tdStatus.setAttribute("data-evidence-field", "disclosure");
      markEvidenceCell(tdStatus, row.row_id);
      tr.appendChild(tdStatus);

      tbody.appendChild(tr);
      rowElementMap[row.row_id] = tr;
    }
    table.appendChild(tbody);
    container.appendChild(table);
    return table;
  }

  function markChartSelection(rowId) {
    var charts = document.querySelectorAll(".kz-chart-group__chart");
    for (var i = 0; i < charts.length; i++) {
      if (rowId) charts[i].setAttribute("data-selected-row-id", rowId);
      else charts[i].removeAttribute("data-selected-row-id");
      charts[i].classList.toggle("kz-chart-group__chart--has-selection", !!rowId);
    }
  }

  function clearSelection() {
    if (selectedRowId === null) {
      markChartSelection(null);
      return;
    }
    var prevEl = rowElementMap[selectedRowId];
    if (prevEl) prevEl.classList.remove("kz-chart-table__row--selected");
    var keys = Object.keys(chartInstances);
    for (var i = 0; i < keys.length; i++) {
      var inst = chartInstances[keys[i]];
      if (inst && !inst.isDisposed()) {
        inst.dispatchAction({ type: "downplay" });
        inst.dispatchAction({ type: "hideTip" });
      }
    }
    selectedRowId = null;
    markChartSelection(null);
  }

  function selectByRowId(rowId) {
    if (!rowId) return;
    if (selectedRowId === rowId) {
      clearSelection();
      return;
    }
    clearSelection();
    selectedRowId = rowId;
    var trEl = rowElementMap[rowId];
    if (trEl) {
      trEl.classList.add("kz-chart-table__row--selected");
      if (typeof trEl.scrollIntoView === "function") {
        trEl.scrollIntoView({ block: "nearest", behavior: "smooth" });
      }
    }
    var keys = Object.keys(chartRowMap);
    for (var i = 0; i < keys.length; i++) {
      var gIdx = keys[i];
      var idxMap = chartRowMap[gIdx];
      if (idxMap[rowId] !== undefined) {
        var inst = chartInstances[gIdx];
        if (inst && !inst.isDisposed()) {
          inst.dispatchAction({
            type: "highlight",
            seriesIndex: inst.getOption().series.length > 1 ? 1 : 0,
            dataIndex: idxMap[rowId]
          });
        }
        break;
      }
    }
    markChartSelection(rowId);
  }

  function activateRow(rowId, triggerEl) {
    var preserve =
      window.__EVIDENCE_DRAWER__ &&
      typeof window.__EVIDENCE_DRAWER__.hasView === "function" &&
      window.__EVIDENCE_DRAWER__.hasView(rowId);
    var x = window.scrollX;
    var y = window.scrollY;
    selectByRowId(rowId);
    if (preserve) {
      var api = window.__EVIDENCE_DRAWER__;
      if (triggerEl && triggerEl.setAttribute) {
        if (triggerEl.tabIndex === undefined || triggerEl.tabIndex < 0) {
          triggerEl.setAttribute("tabindex", "-1");
        }
      }
      api.openByRowId(rowId, triggerEl || null);
      window.scrollTo(x, y);
    }
  }

  function rowIndexFromClick(groupIndex, params) {
    var kind = chartTypeByGroup[groupIndex];
    if (
      (kind === "heatmap" || kind === "status_matrix") &&
      Array.isArray(params.value) &&
      typeof params.value[1] === "number"
    ) {
      return params.value[1];
    }
    return params.dataIndex;
  }

  function wireChartClick(groupIndex) {
    var inst = chartInstances[groupIndex];
    if (!inst) return;
    inst.off("click");
    inst.on("click", function (params) {
      var rowIds = chartRowIdsByGroup[groupIndex] || [];
      var idx = rowIndexFromClick(groupIndex, params);
      if (typeof idx === "number" && idx >= 0 && idx < rowIds.length) {
        var trigger = null;
        if (params.event && params.event.event && params.event.event.target) {
          trigger = params.event.event.target;
        }
        activateRow(rowIds[idx], trigger);
      }
    });
  }

  function markEvidenceCell(td, rowId) {
    td.setAttribute("data-evidence-open", rowId);
    td.setAttribute("tabindex", "0");
    td.setAttribute("role", "button");
    td.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        if (e.stopPropagation) e.stopPropagation();
        activateRow(rowId, td);
      }
    });
  }

  function wireTableRowClick(tr) {
    tr.addEventListener("click", function (e) {
      var rowId = tr.getAttribute("data-row-id");
      if (!rowId) return;
      var cell =
        e.target && e.target.closest ? e.target.closest("td") : null;
      activateRow(rowId, cell || tr);
    });
    tr.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        var rowId = tr.getAttribute("data-row-id");
        if (rowId) activateRow(rowId, tr);
        return;
      }
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        var vis = [];
        var all = document.querySelectorAll(".kz-chart-table__row");
        for (var i = 0; i < all.length; i++) {
          if (all[i].style.display !== "none") vis.push(all[i]);
        }
        var idx = vis.indexOf(tr);
        if (idx === -1) return;
        var next = e.key === "ArrowDown" ? vis[idx + 1] : vis[idx - 1];
        if (!next) return;
        next.focus();
        var nid = next.getAttribute("data-row-id");
        if (nid) activateRow(nid, next);
      }
    });
  }

  function allChartRowIds() {
    var ids = [];
    var keys = Object.keys(chartRowIdsByGroup).sort(function (a, b) {
      return Number(a) - Number(b);
    });
    for (var i = 0; i < keys.length; i++) {
      var list = chartRowIdsByGroup[keys[i]] || [];
      for (var j = 0; j < list.length; j++) ids.push(list[j]);
    }
    return ids;
  }

  function getVisibleRowIds() {
    if (!filterRows || !filterRows.length) return allChartRowIds();
    var visible = [];
    var anyFilterEl = false;
    for (var i = 0; i < filterRows.length; i++) {
      var el =
        document.getElementById("filter-row-" + filterRows[i].id) ||
        document.querySelector('[data-filter-row-id="' + filterRows[i].id + '"]');
      if (el) {
        anyFilterEl = true;
        if (el.style.display !== "none") visible.push(filterRows[i].id);
      }
    }
    if (!anyFilterEl) return allChartRowIds();
    return visible;
  }

  function syncChartWithFilter() {
    clearSelection();
    var visibleIds = getVisibleRowIds();
    var visibleSet = {};
    for (var v = 0; v < visibleIds.length; v++) visibleSet[visibleIds[v]] = true;

    var keys = Object.keys(rowElementMap);
    for (var t = 0; t < keys.length; t++) {
      var rid = keys[t];
      var tr = rowElementMap[rid];
      if (tr) tr.style.display = visibleSet[rid] ? "" : "none";
    }

    var gKeys = Object.keys(chartRowIdsByGroup);
    for (var i = 0; i < gKeys.length; i++) {
      var gIdx = gKeys[i];
      var rowIds = chartRowIdsByGroup[gIdx] || [];
      var sourceGroup = chartGroups[Number(gIdx)];
      var filteredRows = [];
      var anyVisible = false;
      for (var j = 0; sourceGroup && j < sourceGroup.rows.length; j++) {
        if (visibleSet[String(sourceGroup.rows[j].row_id)]) {
          anyVisible = true;
          filteredRows.push(sourceGroup.rows[j]);
        }
      }
      var wrapper = document.querySelector(
        '.kz-chart-module__group[data-group-index="' + gIdx + '"]'
      );
      if (!wrapper) {
        var chartEl = document.getElementById("kz-chart-" + gIdx);
        wrapper = chartEl ? chartEl.closest(".kz-chart-module__group") : null;
      }
      if (wrapper) wrapper.style.display = anyVisible ? "" : "none";
      var inst = chartInstances[gIdx];
      if (inst && !inst.isDisposed()) {
        inst.dispose();
        delete chartInstances[gIdx];
      }
      if (anyVisible && sourceGroup) {
        var chartEl = document.getElementById("kz-chart-" + gIdx);
        if (chartEl) {
          chartEl.innerHTML = "";
          var filteredGroup = {};
          var sourceKeys = Object.keys(sourceGroup);
          for (var sk = 0; sk < sourceKeys.length; sk++) {
            filteredGroup[sourceKeys[sk]] = sourceGroup[sourceKeys[sk]];
          }
          filteredGroup.rows = filteredRows;
          initGroupChart(chartEl, Number(gIdx), filteredGroup);
        }
      }
    }

    var moduleEl = document.getElementById("kz-chart-module");
    var emptyEl = document.getElementById("kz-chart-empty");
    var portalEmpty = document.getElementById("kz-filter-empty");
    var portalEmptyShown =
      portalEmpty &&
      portalEmpty.style.display !== "none" &&
      portalEmpty.offsetParent !== null;
    if (moduleEl) moduleEl.style.display = visibleIds.length === 0 ? "none" : "";
    if (emptyEl) {
      emptyEl.style.display =
        visibleIds.length === 0 && !portalEmptyShown ? "block" : "none";
    }
  }

  function initGroupChart(chartDiv, groupIndex, group) {
    var rowIds = collectRowIds(group);
    chartRowIdsByGroup[groupIndex] = rowIds.slice();
    chartTypeByGroup[groupIndex] = resolveChartType(group);
    var idxMap = {};
    for (var r = 0; r < rowIds.length; r++) idxMap[rowIds[r]] = r;
    chartRowMap[groupIndex] = idxMap;

    if (!groupHasRenderable(group)) {
      if (!chartDiv.querySelector(".kz-chart-undisclosed")) {
        renderUndisclosedMessage(chartDiv);
      }
      var stubData = [];
      for (var s = 0; s < group.rows.length; s++) {
        stubData.push({
          value: null,
          status: group.rows[s].disclosure_state
        });
      }
      optionCache[groupIndex] = withMeta({ series: [{ data: stubData }] }, rowIds);
      return;
    }

    chartDiv.classList.remove("kz-chart-group__chart--undisclosed");
    chartDiv.style.width = "100%";
    chartDiv.style.height = "340px";
    chartDiv.style.minHeight = "";

    var option = buildOption(group);
    if (!option || !ECHARTS_READY) {
      chartDiv.textContent = "当前组暂无可绘制数值，完整表格仍保留全部记录";
      return;
    }
    var inst = window.echarts.init(chartDiv, null, { renderer: "svg" });
    inst.setOption(option);
    chartInstances[groupIndex] = inst;
    optionCache[groupIndex] = option;
    wireChartClick(groupIndex);
  }

  function init() {
    var moduleEl = document.getElementById("kz-chart-module");
    if (!moduleEl) return;
    moduleEl.innerHTML = "";
    selectedRowId = null;
    chartInstances = {};
    chartRowMap = {};
    chartRowIdsByGroup = {};
    chartTypeByGroup = {};
    rowElementMap = {};
    optionCache = {};

    if (chartGroups.length === 0) {
      var empty = document.createElement("div");
      empty.className = "kz-chart-empty";
      empty.id = "kz-chart-empty";
      empty.innerHTML = '<p class="kz-chart-empty__title">当前选择下暂无可比较数据</p>';
      moduleEl.appendChild(empty);
      return;
    }

    for (var g = 0; g < chartGroups.length; g++) {
      var group = chartGroups[g];
      var wrapper = document.createElement("div");
      wrapper.className = "kz-chart-module__group";
      wrapper.setAttribute("data-group-index", String(g));
      moduleEl.appendChild(wrapper);
      var chartDiv = renderChartContainer(wrapper, g, group);
      renderTable(wrapper, g, group);
      initGroupChart(chartDiv, g, group);
      var rows = wrapper.querySelectorAll(".kz-chart-table__row");
      for (var ri = 0; ri < rows.length; ri++) wireTableRowClick(rows[ri]);
    }

    if (
      window.__PORTAL_FILTER__ &&
      typeof window.__PORTAL_FILTER__.reapply === "function"
    ) {
      window.__PORTAL_FILTER__.reapply();
    } else {
      syncChartWithFilter();
    }

    var filterPanel = document.getElementById("kz-filter-panel");
    if (filterPanel) {
      filterPanel.addEventListener("toggle", function () {
        if (!filterPanel.hasAttribute("open")) clearSelection();
      });
    }
    var filterClose = document.getElementById("kz-filter-close");
    if (filterClose) {
      filterClose.addEventListener("click", function () {
        clearSelection();
      });
    }

    window.addEventListener("resize", function () {
      var keys = Object.keys(chartInstances);
      for (var i = 0; i < keys.length; i++) {
        var inst = chartInstances[keys[i]];
        if (inst && !inst.isDisposed()) inst.resize();
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  window.__CHART_SYNC__ = {
    syncWithFilter: syncChartWithFilter,
    selectByRowId: selectByRowId,
    clearSelection: clearSelection,
    getSelectedRowId: function () {
      return selectedRowId;
    },
    getRowSetDigest: function () {
      return rowSetDigest;
    },
    getSnapshotId: function () {
      return snapshotId;
    },
    getChartRowIds: function () {
      return allChartRowIds();
    },
    getSeriesValues: function (groupIndex) {
      var opt = optionCache[String(groupIndex)] || optionCache[groupIndex];
      if (!opt || !opt.series || !opt.series[0]) return [];
      var series = opt.series[opt.series.length > 1 ? opt.series.length - 1 : 0];
      return (series.data || []).map(function (d) {
        if (d && typeof d === "object") {
          if (d.status) return null;
          if (d.value === null || d.value === undefined) return null;
          if (Array.isArray(d.value)) {
            for (var i = 0; i < d.value.length; i++) {
              if (d.value[i] === null || d.value[i] === undefined) return null;
            }
          }
          return d.value;
        }
        return d === undefined ? null : d;
      });
    },
    supportedChartTypes: function () {
      return Object.keys(CHART_TYPES);
    }
  };
})();
