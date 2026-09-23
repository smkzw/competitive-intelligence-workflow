/**
 * Task 4.4 — 离线八类图形、小多图与图表-表格双向联动。
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
  var allRowIdsByGroup = {};
  var chartTypeByGroup = {};
  var rowElementMap = {};
  var optionCache = {};
  var resizeObserver = null;
  var windowResizeBound = false;

  var CHART_TYPES = {
    bar: true,
    line: true,
    forest: true,
    heatmap: true,
    bubble: true,
    scatter_interval: true,
    timeline: true,
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
        fontSize: 16
      }
    };
  }

  function collectRowIds(group) {
    var ids = [];
    for (var i = 0; i < group.rows.length; i++) ids.push(group.rows[i].row_id);
    return ids;
  }

  function collectRenderableRowIds(group) {
    var ids = [];
    for (var i = 0; i < group.rows.length; i++) {
      if (isRenderable(group.rows[i])) ids.push(group.rows[i].row_id);
    }
    return ids;
  }

  function withMeta(option, rowIds) {
    option.animation = false;
    option._rowIds = rowIds;
    option._snapshotId = snapshotId;
    option._rowSetDigest = rowSetDigest;
    return option;
  }

  function usesIdentitySeries(group) {
    return !!(group && (group.identity_series || group.cross_trial));
  }

  function groupedIdentity(row) {
    if (row && row._chart_identity_key) return String(row._chart_identity_key);
    return String(
      (row && row.identity_label_zh) ||
        ((row && row.product_zh) || "未列示产品") +
          "｜" +
          ((row && row.trial_zh) || "未列示试验")
    );
  }

  function groupedIdentityLabel(row) {
    if (row && row._chart_identity_label) {
      var label = String(row._chart_identity_label);
      // 独立复核修复：超长身份标签（全试验名）压缩为登记编号，
      // 完整名称保留在同源数据表中，轴标签不再旋转穿插。
      if (label.length > 26 && row._chart_identity_key) {
        var trialId = String(row._chart_identity_key).split("::")[1] || "";
        if (/^nct[0-9]+$/.test(trialId)) return trialId.toUpperCase();
      }
      return label;
    }
    return groupedIdentity(row);
  }

  function groupedSeriesKey(row) {
    if (row && row._chart_series_key) return String(row._chart_series_key);
    // 第十五轮复核修复：类别级行（如性别女/男）按类别分系列，避免同系列柱体重叠
    if (row && row.category_level) {
      var role = row.arm_role || "";
      return String(role) + "·" + String(row.category_level);
    }
    if (row && row.arm_role) return String(row.arm_role);
    return String(row && (row.arm || row.group) ? row.arm || row.group : "unknown");
  }

  function groupedSeriesLabel(row, key) {
    if (row && row._chart_series_label) return String(row._chart_series_label);
    if (key === "treatment" || key === "治疗组") return "治疗组";
    if (key === "control" || key === "对照组" || key === "placebo") return "对照组";
    return String((row && (row.arm || row.group)) || "组别未列示");
  }

  function groupedSeriesOrder(rows) {
    var seen = {};
    var keys = [];
    for (var i = 0; i < rows.length; i++) {
      var key = groupedSeriesKey(rows[i]);
      if (!seen[key]) {
        seen[key] = true;
        keys.push(key);
      }
    }
    keys.sort(function (left, right) {
      var priority = { treatment: 0, control: 1, single_arm: 2, unknown: 3 };
      var leftRoot = String(left).split(":")[0];
      var rightRoot = String(right).split(":")[0];
      var lp = priority[leftRoot] === undefined ? 4 : priority[leftRoot];
      var rp = priority[rightRoot] === undefined ? 4 : priority[rightRoot];
      return lp - rp || String(left).localeCompare(String(right));
    });
    return keys;
  }

  function valueAxisMaximum(group, extent) {
    var observed = Math.max(0, Number(extent.max) || 0);
    if (typeof group.y_axis_max === "number") return Math.max(group.y_axis_max, observed);
    var plotted = (group.rows || []).filter(isRenderable);
    var proportions = plotted.length > 0 && plotted.every(function (row) {
      var projection = row.numeric_projection || {};
      return projection.kind === "participant_proportion" && projection.plot_unit === "%"
        && Number(projection.plot_value) >= 0 && Number(projection.plot_value) <= 100;
    });
    if (proportions) return 100;
    if (observed === 0) return 1;
    var padded = observed * 1.12;
    var step = Math.pow(10, Math.floor(Math.log10(padded)) - 1);
    return Math.ceil(padded / step) * step;
  }

  function groupedCategoryAssignments(rows) {
    var occurrences = {};
    var assignments = [];
    for (var i = 0; i < rows.length; i++) {
      var base = groupedIdentity(rows[i]);
      var series = groupedSeriesKey(rows[i]);
      var cell = base + "\u0001" + series;
      var occurrence = occurrences[cell] || 0;
      occurrences[cell] = occurrence + 1;
      assignments.push({
        key: occurrence ? base + "\u0001repeat:" + occurrence : base,
        label: groupedIdentityLabel(rows[i]) + (occurrence ? "｜第" + (occurrence + 1) + "项同身份观察" : ""),
        repeated: occurrence > 0
      });
    }
    return assignments;
  }

  function groupedBarOption(group) {
    var categories = [];
    var categoryIndex = {};
    var categoryKeys = [];
    var rowsByCategory = {};
    var seriesRows = {};
    var seriesOrder = [];
    var seriesLabels = {};
    var rowIds = collectRowIds(group);
    var unitLabel = "";
    var assignments = groupedCategoryAssignments(group.rows);
    for (var i = 0; i < group.rows.length; i++) {
      var row = group.rows[i];
      var categoryKey = assignments[i].key;
      if (!categoryIndex.hasOwnProperty(categoryKey)) {
        categoryIndex[categoryKey] = categories.length;
        categories.push(assignments[i].label);
        categoryKeys.push(categoryKey);
        rowsByCategory[categoryKey] = {};
      }
      var seriesKey = groupedSeriesKey(row);
      if (!seriesRows.hasOwnProperty(seriesKey)) {
        seriesRows[seriesKey] = {};
        seriesOrder.push(seriesKey);
      }
      if (rowsByCategory[categoryKey].hasOwnProperty(seriesKey)) {
        throw new Error("同身份观察分列后仍有图形坐标冲突：" + categoryKey + " / " + seriesKey);
      }
      rowsByCategory[categoryKey][seriesKey] = row;
      seriesRows[seriesKey][categoryKey] = rowsByCategory[categoryKey][seriesKey];
      if (!seriesLabels[seriesKey]) {
        seriesLabels[seriesKey] = groupedSeriesLabel(row, seriesKey);
      }
      if (!unitLabel && row.unit) unitLabel = String(row.unit);
    }
    seriesOrder = groupedSeriesOrder(group.rows);
    var series = [];
    for (var s = 0; s < seriesOrder.length; s++) {
      var key = seriesOrder[s];
      var seriesColor = String(key).split(":")[0] === "control" || key === "对照组"
        ? "#407AAA"
        : "#FF9900";
      var data = [];
      for (var c = 0; c < categories.length; c++) {
        var category = categoryKeys[c];
        var rowForCell = category ? seriesRows[key][category] : null;
        if (!rowForCell || !isRenderable(rowForCell)) {
          var missing = nullPoint(rowForCell || { disclosure_state: "not_reported" });
          if (rowForCell && rowForCell.row_id) missing._row_id = String(rowForCell.row_id);
          data.push(missing);
          continue;
        }
        var value = rowForCell.numeric_value != null ? rowForCell.numeric_value : rowForCell.value;
        data.push({
          value: value,
          _row_id: String(rowForCell.row_id),
          status: null,
          itemStyle: {
            color: seriesColor
          },
          label: {
            // 独立审阅 R08（UI01）：标签策略按当前显示类别数判定；
            // 原 series[0] 自引用在首系列构建时恒为 undefined，首系列标签被吞
            show: categories.length <= 12,
            position: value < 0 ? "insideBottom" : "top",
            formatter: String(value),
            color: value < 0 ? "#FFFFFF" : "#0F1115",
            fontSize: 13,
            fontWeight: 600,
            padding: 2
          }
        });
      }
      series.push({
        name: seriesLabels[key] || key,
        type: "bar",
        data: data,
        itemStyle: { color: seriesColor },
        barMaxWidth: 54,
        labelLayout: { hideOverlap: true },
        emphasis: {
          focus: "series",
          itemStyle: { borderColor: "#0F1115", borderWidth: 2 }
        }
      });
    }
    return withMeta(
      {
        tooltip: {
          trigger: "axis",
          formatter: function (params) {
            var items = Array.isArray(params) ? params : [params];
            var title = items.length && items[0].axisValue ? String(items[0].axisValue) : "";
            var lines = [title];
            for (var p = 0; p < items.length; p++) {
              var item = items[p];
              if (!item || !item.data || item.data.status) continue;
              lines.push(String(item.seriesName) + "：" + String(item.data.value));
            }
            return lines.join("<br>");
          }
        },
        legend: {
          show: series.length > 1,
          data: series.map(function (item) { return item.name; }),
          bottom: 0,
          textStyle: { fontSize: 13 }
        },
        grid: { left: 56, right: 40, top: series.length > 1 ? 66 : 44, bottom: categories.length > 8 ? 100 : 78, containLabel: true },
        dataZoom: categories.length > 8 ? [
          { type: "slider", height: 20, bottom: 4, start: 0, end: Math.min(100, 800 / categories.length) },
          { type: "inside" }
        ] : [],
        xAxis: {
          type: "category",
          data: categories,
          name: group.x_axis_label_zh || "产品｜试验",
          nameLocation: "middle",
          nameGap: 40,
          axisLabel: { interval: "auto", hideOverlap: true, fontSize: 14, rotate: 30, width: 110, overflow: "break" }
        },
        yAxis: {
          type: "value",
          name: unitLabel,
          axisLabel: { fontSize: 14, rotate: 25, hideOverlap: true, width: 100, overflow: "break" },
          scale: false,
          min: function (extent) {
            if (typeof group.y_axis_min === "number") return group.y_axis_min;
            return Math.min(0, extent.min);
          },
          max: function (extent) {
            return valueAxisMaximum(group, extent);
          },
          axisLine: { show: true, onZero: true },
          splitLine: { show: true }
        },
        series: series
      },
      rowIds
    );
  }

  function buildBarOption(group) {
    if (usesIdentitySeries(group)) return groupedBarOption(group);
    var categories = [];
    var seriesData = [];
    var rowIds = collectRowIds(group);
    var unitLabel = "";
    var treatColor = "#FF9900";
    var ctrlColor = "#407AAA";
    for (var i = 0; i < group.rows.length; i++) {
      var row = group.rows[i];
      if (!isRenderable(row)) continue;
      var arm = armLabel(row);
      var domain = String(row._domain || "");
      var category = arm || row.display_label_zh || "";
      if (domain === "baseline" || domain === "disposition") {
        category = String(row.display_label_zh || "");
        if (arm && arm !== "组别未列示") category += "\n" + arm;
      }
      categories.push(category);
      if (!unitLabel && row.unit) unitLabel = row.unit;
      var v = row.numeric_value != null ? row.numeric_value : row.value;
      seriesData.push({
          value: v,
          status: null,
          itemStyle: { color: arm === "对照组" ? ctrlColor : treatColor },
          label: {
            show: categories.length <= 12,
            position: v < 0 ? "insideBottom" : "top",
            formatter: String(v),
            color: v < 0 ? "#FFFFFF" : "#0F1115",
            fontSize: 14,
            fontWeight: 600,
            padding: 3
          }
      });
    }
    return withMeta(
      {
        tooltip: { trigger: "item", show: false },
        grid: { left: 56, right: 40, top: 36, bottom: 48, containLabel: true },
        xAxis: {
          type: "category",
          data: categories,
          axisLabel: { interval: "auto", hideOverlap: true, fontSize: 16, rotate: 30, width: 120, overflow: "break" }
        },
        yAxis: {
          type: "value",
          name: unitLabel,
          axisLabel: { fontSize: 14, rotate: 25, hideOverlap: true, width: 100, overflow: "break" },
          scale: false,
          min: function (extent) {
            if (typeof group.y_axis_min === "number") return group.y_axis_min;
            return Math.min(0, extent.min);
          },
          max: function (extent) {
            return valueAxisMaximum(group, extent);
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
            labelLayout: { hideOverlap: true },
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
      collectRenderableRowIds(group)
    );
  }

  function groupedLineOption(group) {
    var timeLabels = {};
    var timeOrder = {};
    var seriesRows = {};
    var seriesOrder = [];
    var rowIds = collectRowIds(group);
    for (var i = 0; i < group.rows.length; i++) {
      var row = group.rows[i];
      var timeKey = String(row._chart_time_key || row.time || row.display_label_zh || "");
      if (!timeLabels.hasOwnProperty(timeKey)) {
        timeLabels[timeKey] = String(
          row.time_window_band_label_zh || row.time || row.display_label_zh || timeKey
        );
        var numericTime = Number(row.actual_timepoint);
        timeOrder[timeKey] = isFinite(numericTime) ? numericTime : Object.keys(timeOrder).length;
      }
      var seriesKey =
        groupedIdentity(row) + " · " + groupedSeriesKey(row);
      if (!seriesRows.hasOwnProperty(seriesKey)) {
        seriesRows[seriesKey] = {
          label: groupedIdentityLabel(row) + " · " + groupedSeriesLabel(row, groupedSeriesKey(row)),
          rows: {}
        };
        seriesOrder.push(seriesKey);
      }
      seriesRows[seriesKey].rows[timeKey] = row;
    }
    var times = Object.keys(timeLabels);
    times.sort(function (left, right) {
      return timeOrder[left] - timeOrder[right] || left.localeCompare(right);
    });
    seriesOrder.sort(function (left, right) { return left.localeCompare(right); });
    var series = [];
    for (var s = 0; s < seriesOrder.length; s++) {
      var descriptor = seriesRows[seriesOrder[s]];
      var data = [];
      for (var t = 0; t < times.length; t++) {
        var rowForPoint = descriptor.rows[times[t]];
        if (!rowForPoint || !isRenderable(rowForPoint)) {
          var missing = nullPoint(rowForPoint || { disclosure_state: "not_reported" });
          if (rowForPoint && rowForPoint.row_id) missing._row_id = String(rowForPoint.row_id);
          data.push(missing);
          continue;
        }
        data.push({
          value: rowForPoint.numeric_value != null ? rowForPoint.numeric_value : rowForPoint.value,
          _row_id: String(rowForPoint.row_id),
          status: null
        });
      }
      series.push({
        name: descriptor.label,
        type: "line",
        data: data,
        connectNulls: false,
        symbol: "circle",
        symbolSize: 9,
        emphasis: { focus: "series" }
      });
    }
    return withMeta(
      {
        tooltip: { trigger: "axis" },
        legend: {
          show: series.length > 1,
          data: series.map(function (item) { return item.name; }),
          top: 0,
          textStyle: { fontSize: 13 }
        },
        grid: { left: 56, right: 40, top: series.length > 1 ? 58 : 40, bottom: 54, containLabel: true },
        xAxis: {
          type: "category",
          data: times.map(function (key) { return timeLabels[key]; }),
          name: group.x_axis_label_zh || "时间窗",
          nameLocation: "middle",
          nameGap: 36,
          boundaryGap: false,
          axisLabel: { fontSize: 14, rotate: 25, hideOverlap: true, width: 100, overflow: "break" }
        },
        yAxis: {
          type: "value",
          scale: true,
          axisLabel: { fontSize: 14, rotate: 25, hideOverlap: true, width: 100, overflow: "break" },
          min: typeof group.y_axis_min === "number" ? group.y_axis_min : null,
          max: typeof group.y_axis_max === "number" ? group.y_axis_max : null
        },
        series: series
      },
      rowIds
    );
  }

  function buildLineOption(group) {
    if (usesIdentitySeries(group)) return groupedLineOption(group);
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
        grid: { left: 56, right: 40, top: 40, bottom: 40, containLabel: true },
        xAxis: {
          type: "category",
          data: times,
          boundaryGap: false,
          axisLabel: { fontSize: 14, rotate: 25, hideOverlap: true, width: 100, overflow: "break" }
        },
        yAxis: {
          type: "value",
          scale: true,
          axisLabel: { fontSize: 14, rotate: 25, hideOverlap: true, width: 100, overflow: "break" },
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
        xAxis: { type: "value", name: "效应值", axisLabel: { fontSize: 14, rotate: 25, hideOverlap: true, width: 100, overflow: "break" } },
        yAxis: {
          type: "category",
          data: categories,
          inverse: true,
          axisLabel: { fontSize: 14, rotate: 25, hideOverlap: true, width: 100, overflow: "break" }
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

  function legendText(maxAbs, rowUnit, allInteger) {
    // 图例单位随数据口径：计数（例/人）不带百分号，仅比率用 %
    var suffix = "%";
    if (rowUnit === "例" || rowUnit === "人" || rowUnit === "Participants") {
      suffix = rowUnit === "Participants" ? "人" : rowUnit;
    } else if (allInteger && rowUnit && !/%/.test(rowUnit) && !/percent/i.test(rowUnit)) {
      suffix = rowUnit;
    }
    return [String(maxAbs) + suffix, "0" + (suffix === "%" ? "%" : "")];
  }

  function buildHeatmapOption(group) {
    var events = [];
    var arms = [];
    var seriesData = [];
    var rowIds = collectRowIds(group);
    var maxAbs = 1;
    var allInteger = true;
    var rowUnit = "";
    for (var i = 0; i < group.rows.length; i++) {
      var row = group.rows[i];
      if (!rowUnit && row.unit) rowUnit = String(row.unit);
      if (rowUnit && row.unit && String(row.unit) !== rowUnit) rowUnit = "例";
      var eventName = row.event || row.display_label_zh || "";
      var armName = armLabel(row) || String(row.arm_detail || row.arm || "组别未列示");
      var eventIndex = events.indexOf(eventName);
      var armIndex = arms.indexOf(armName);
      if (eventIndex === -1) {
        events.push(eventName);
        eventIndex = events.length - 1;
      }
      if (armIndex === -1) {
        arms.push(armName);
        armIndex = arms.length - 1;
      }
      if (!isRenderable(row)) {
        seriesData.push({
          value: [armIndex, eventIndex, 0],
          rowIndex: i,
          _row_id: String(row.row_id),
          status: row.disclosure_state,
          itemStyle: {
            color: "#F4F1EC",
            borderColor: "#8A8178",
            borderWidth: 1,
            decal: { symbol: "rect", dashArrayX: [1, 0], dashArrayY: [3, 3], color: "#D4CDC4" }
          }
        });
      } else {
        var matrix = row.value_matrix;
        var cell = Array.isArray(matrix) ? matrix[0] : matrix;
        var num = typeof cell === "number" ? cell : Number(cell);
        if (!isFinite(num)) num = null;
        if (num != null) {
          if (Math.abs(num) > maxAbs) maxAbs = Math.abs(num);
          if (!Number.isInteger(num)) allInteger = false;
        }
        seriesData.push({
          value: [armIndex, eventIndex, num],
          rowIndex: i,
          _row_id: String(row.row_id),
          status: null
        });
      }
    }
    return withMeta(
      {
        tooltip: { position: "top" },
        grid: { left: 100, right: 40, top: 24, bottom: 40, containLabel: true },
        xAxis: {
          type: "category",
          data: arms,
          axisLabel: { fontSize: 14, rotate: 25, hideOverlap: true, width: 100, overflow: "break" }
        },
        yAxis: {
          type: "category",
          data: events,
          inverse: true,
          axisLabel: { fontSize: 14, rotate: 25, hideOverlap: true, width: 100, overflow: "break" }
        },
        visualMap: {
          min: 0,
          max: maxAbs,
          calculable: false,
          orient: "horizontal",
          left: "center",
          bottom: 0,
          inRange: { color: ["#FFF6E8", "#F5A623", "#A61B1B"] },
          text: legendText(maxAbs, rowUnit, allInteger),
          textGap: 8,
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
                var rowIndex = p.data && p.data.rowIndex;
                if (p.data && p.data.status) {
                  return disclosureLabelZh(
                    (group.rows[rowIndex] && group.rows[rowIndex].disclosure_state) ||
                      "not_publicly_disclosed"
                  );
                }
                var sourceRow = group.rows[rowIndex] || {};
                if (sourceRow._user_edit && typeof p.value[2] === "number") {
                  var rounded = Number(p.value[2].toPrecision(3));
                  return (rounded === p.value[2] ? "" : "约") + rounded + String(sourceRow.unit || "");
                }
                return String(p.value[2]);
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
    var xUnit = String(group.x_unit || "");
    var yUnit = String(group.y_unit || "");
    var sizeTerm = String(group.size_label_zh || "治疗组样本量")
      .replace(/^气泡大小[：:]/, "")
      .trim();
    var projectedX = [];
    var projectedY = [];
    for (var i = 0; i < group.rows.length; i++) {
      var row = group.rows[i];
      if (!isRenderable(row)) {
        seriesData.push({
          value: null,
          status: row.disclosure_state,
          statusLabel: disclosureLabelZh(row.disclosure_state)
        });
      } else {
        var sampleSize = Number(row.size) || 0;
        projectedX.push(Number(row.x_value));
        projectedY.push(Number(row.y_value));
        seriesData.push({
          value: [row.x_value, row.y_value, row.size],
          name: groupedIdentityLabel(row),
          _row_id: String(row.row_id),
          _status: row.status || "",
          _size_basis: row.size_basis || sizeTerm,
          status: null,
          symbolSize: Math.max(18, Math.min(56, 4 * Math.sqrt(sampleSize / Math.PI))),
          label: {
            position: seriesData.length % 2 ? "bottom" : "top",
            distance: 6,
            offset: [0, (seriesData.length % 3 - 1) * 12],
            backgroundColor: "rgba(255,255,255,.82)",
            borderRadius: 3,
            padding: [2, 4]
          }
        });
      }
    }
    return withMeta(
      {
        tooltip: {
          trigger: "item",
          formatter: function (p) {
            return p.name + "<br>疗效：" + p.value[0] + (xUnit ? " " + xUnit : "") + "<br>安全性：" + p.value[1] + (yUnit ? " " + yUnit : "") + "<br>" + (p.data._size_basis || sizeTerm) + "：" + p.value[2];
          }
        },
        grid: { left: 64, right: 40, top: 44, bottom: 68, containLabel: true },
        xAxis: {
          type: "value",
          name: group.x_axis_label_zh || "疗效",
          nameLocation: "middle",
          nameGap: 42,
          axisLabel: { fontSize: 14, rotate: 25, hideOverlap: true, width: 100, overflow: "break" }
        },
        yAxis: {
          type: "value",
          name: group.y_axis_label_zh || "安全性",
          nameLocation: "middle",
          nameGap: 48,
          min: projectedY.length ? Math.min.apply(null, projectedY.concat([0])) : 0,
          max: projectedY.length ? Math.max.apply(null, projectedY) * 1.1 || 1 : 1,
          inverse: true,
          axisLabel: { fontSize: 14, rotate: 25, hideOverlap: true, width: 100, overflow: "break" }
        },
        series: [
          {
            name: "气泡",
            type: "scatter",
            data: seriesData,
            label: {
              show: true,
              position: "top",
              formatter: function (p) {
                var v = p.value;
                if (!Array.isArray(v) || v[0] == null) {
                  return (p.data && p.data.statusLabel) || "";
                }
                var lines = [p.name];
                if (p.data && p.data._status) lines.push("比较状态 " + p.data._status);
                lines.push("疗效差 " + v[0] + (xUnit ? " " + xUnit : ""));
                lines.push("不良事件 " + v[1] + (yUnit ? " " + yUnit : ""));
                lines.push(((p.data && p.data._size_basis) || sizeTerm) + " " + v[2]);
                return lines.join("\n");
              },
              fontSize: 16,
              lineHeight: 22,
              color: "#0F1115",
              overflow: "break"
            },
            labelLayout: {hideOverlap: true},
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
        xAxis: { type: "value", name: "估计值", axisLabel: { fontSize: 14, rotate: 25, hideOverlap: true, width: 100, overflow: "break" } },
        yAxis: {
          type: "category",
          data: categories,
          inverse: true,
          axisLabel: { fontSize: 14, rotate: 25, hideOverlap: true, width: 100, overflow: "break" }
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
          label: { show: true, formatter: statusText, position: "top", fontSize: 16 }
        });
      }
    }
    return withMeta(
      {
        tooltip: { trigger: "axis" },
        grid: { left: 40, right: 24, top: 48, bottom: 40, containLabel: true },
        xAxis: { type: "category", data: times, axisLabel: { fontSize: 14, rotate: 25, hideOverlap: true, width: 100, overflow: "break" } },
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


  function buildStatusMatrixOption(group) {
    var labels = [];
    var seriesData = [];
    var rowIds = collectRowIds(group);
    for (var i = 0; i < group.rows.length; i++) {
      var row = group.rows[i];
      labels.push(row.trial_zh || row.display_label_zh || "");
      if (!isRenderable(row)) {
        seriesData.push({
          value: [0, i, null],
          _row_id: String(row.row_id),
          status: row.disclosure_state
        });
      } else {
        var cov = row.coverage;
        var num = typeof cov === "number" ? cov : Number(cov);
        seriesData.push({
          value: [0, i, isFinite(num) ? num : null],
          _row_id: String(row.row_id),
          status: null
        });
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
          axisLabel: { fontSize: 14, rotate: 25, hideOverlap: true, width: 100, overflow: "break" }
        },
        yAxis: {
          type: "category",
          data: labels,
          inverse: true,
          axisLabel: { fontSize: 14, rotate: 25, hideOverlap: true, width: 100, overflow: "break" }
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
      if (arm && arm !== "组别未列示" && !seen[arm]) {
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

  function undisclosedTitle(group) {
    var rows = (group && group.rows) || [];
    var total = 0;
    var notApplicable = 0;
    var publishedButUnplotted = 0;
    for (var i = 0; i < rows.length; i++) {
      total += 1;
      if (rows[i].disclosure_state === "not_applicable") notApplicable += 1;
      if (rows[i].disclosure_state === "reported_value" ||
          rows[i].disclosure_state === "reported_zero") publishedButUnplotted += 1;
    }
    if (publishedButUnplotted) return "有公开记录，但当前口径不适合绘图";
    return total > 0 && notApplicable === total ? "不适用" : "该指标结果尚未公开";
  }

  function hasPublishedDisclosure(row) {
    return row.disclosure_state === "reported_value" || row.disclosure_state === "reported_zero";
  }

  function unplottedReason(row) {
    return String(row.difference_note || row.reason || "当前图形口径不适合该记录");
  }

  function renderUndisclosedMessage(chartDiv, group) {
    chartDiv.classList.add("kz-chart-group__chart--undisclosed");
    chartDiv.style.height = "auto";
    chartDiv.style.minHeight = "0";
    var status = document.createElement("div");
    status.className = "kz-chart-undisclosed";
    status.setAttribute("role", "status");
    var p1 = document.createElement("p");
    p1.className = "kz-chart-undisclosed__title";
    p1.textContent = undisclosedTitle(group);
    var p2 = document.createElement("p");
    p2.className = "kz-chart-undisclosed__hint";
    var reasons = (group.rows || []).filter(function (row) {
      return !isRenderable(row) && (row.difference_note || row.reason);
    }).map(function (row) { return String(row.difference_note || row.reason); });
    p2.textContent = (reasons.length ? Array.from(new Set(reasons)).join("；") + "。" : "") +
      "完整记录仍列于下方表格，便于核对来源与口径。";
    status.appendChild(p1);
    status.appendChild(p2);
    chartDiv.appendChild(status);
  }

  function presentationPlan(group) {
    var rows = group.rows || [];
    var plotted = rows.filter(isRenderable);
    var kind = resolveChartType(group);
    var compactMatrix = (kind === "heatmap" || kind === "status_matrix")
      && rows.length <= 4;
    var compact = ((kind === "bar" || kind === "line") && plotted.length <= 4)
      || compactMatrix;
    var height = kind === "heatmap" || kind === "status_matrix"
      ? compactMatrix ? (rows.length <= 1 ? 160 : 184)
        : Math.min(420, Math.max(260, 140 + rows.length * 28))
      : plotted.length <= 1 ? 168
        : plotted.length <= 2 ? 220
          : plotted.length <= 8 ? 300 : 380;
    return {
      query_digest: group.query_digest || rowSetDigest,
      revision: group.revision || window.__FACT_REVISION__ || 0,
      facet: group.facet_key || null,
      numeric_frame: group.numeric_frame || null,
      observation_ids: rows.map(function (row) { return String(row.row_id || ""); }),
      plotted_ids: plotted.map(function (row) { return String(row.row_id || ""); }),
      unplotted: rows.filter(function (row) { return !isRenderable(row); }).map(function (row) {
        return { row_id: String(row.row_id || ""), reason: String(row.difference_note || row.reason || row.disclosure_state || "未形成可绘图形") };
      }),
      observation_count: rows.length,
      glyph_count: plotted.length,
      series_count: usesIdentitySeries(group) ? groupedSeriesOrder(rows).length : 1,
      kind: kind,
      grid_span: compact ? 6 : 12,
      target_height: height,
      max_height: 420,
      axis_plan: { explicit_min: group.y_axis_min, explicit_max: group.y_axis_max, unit: group.unit || null },
      reason: compact ? "少量同框观察，紧凑显示" : "多项观察或复杂图形，需要完整绘图区"
    };
  }

  function renderChartContainer(container, groupIndex, group) {
    container.setAttribute("data-group-index", String(groupIndex));
    var plan = presentationPlan(group);
    container.setAttribute("data-grid-span", String(plan.grid_span));
    container.setAttribute("data-observation-count", String(plan.observation_count));

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
    var completeTitle = group.title_complete === true;
    title.textContent = completeTitle
      ? dimensionTitle || indicatorTitle
      : dimensionTitle && dimensionTitle !== "全部指标"
        ? indicatorTitle + "｜" + dimensionTitle
        : indicatorTitle;
    container.appendChild(title);
    var resolvedType = resolveChartType(group);
    if (
      groupHasRenderable(group) &&
      resolvedType !== "status_matrix" &&
      resolvedType !== "heatmap" &&
      resolvedType !== "bubble" &&
      !usesIdentitySeries(group)
    ) {
      renderArmLegend(container, group);
    }
    if (resolvedType === "bubble" && group.size_label_zh) {
      var encodingNote = document.createElement("p");
      encodingNote.className = "kz-chart-group__encoding-note";
      encodingNote.textContent = String(group.size_label_zh);
      container.appendChild(encodingNote);
    }
    var statusNotes = [];
    var seenNotes = {};
    for (var n = 0; n < group.rows.length; n++) {
      var noteRow = group.rows[n];
      if (isRenderable(noteRow)) continue;
      var reason = String(noteRow.difference_note || noteRow.reason || "").trim();
      if (!reason) continue;
      var trial = String(noteRow.trial_zh || noteRow.product_zh || "相关记录");
      var noteText = trial + "：" + reason;
      if (!seenNotes[noteText]) {
        seenNotes[noteText] = true;
        statusNotes.push(noteText);
      }
    }
    if (statusNotes.length) {
      var statusNote = document.createElement("div");
      statusNote.className = "kz-chart-group__status-note";
      statusNote.setAttribute("role", "note");
      statusNote.textContent = statusNotes.join("；");
      container.appendChild(statusNote);
    }

    var chartDiv = document.createElement("div");
    chartDiv.className = "kz-chart-group__chart";
    chartDiv.id = "kz-chart-" + groupIndex;
    var chartType = resolveChartType(group);
    if (chartType) chartDiv.setAttribute("data-chart-type", chartType);
    chartDiv.setAttribute("role", "img");
    chartDiv.setAttribute("aria-label", title.textContent + " 图形");
    if (!groupHasRenderable(group)) {
      if (chartType === "heatmap") {
        chartDiv.style.width = "100%";
        chartDiv.style.height = plan.target_height + "px";
      } else {
        renderUndisclosedMessage(chartDiv, group);
      }
    } else {
      chartDiv.style.width = "100%";
      chartDiv.style.height = plan.target_height + "px";
    }
    var viewport = document.createElement("div");
    viewport.style.maxWidth = "100%";
    viewport.style.overflowX = "auto";
    viewport.addEventListener("keydown", function (event) {
      if (event.target !== viewport || viewport.scrollWidth <= viewport.clientWidth) return;
      if (event.altKey || event.ctrlKey || event.metaKey) return;
      if (event.key !== "ArrowRight" && event.key !== "ArrowLeft") return;
      event.preventDefault();
      viewport.scrollLeft += event.key === "ArrowRight" ? 80 : -80;
    });
    viewport.appendChild(chartDiv);
    container.appendChild(viewport);
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
        tdValue.textContent = hasPublishedDisclosure(row)
          ? String(row.display_value != null ? row.display_value
            : row.numeric_value != null ? row.numeric_value
              : row.value != null ? row.value : "已公开；核对原始来源")
          : disclosureLabelZh(row.disclosure_state);
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
      tdStatus.textContent = isRenderable(row) ? "已披露"
        : hasPublishedDisclosure(row) ? "已披露；未绘制：" + unplottedReason(row)
          : disclosureLabelZh(row.disclosure_state);
      if (!isRenderable(row)) tdStatus.classList.add("kz-chart-table__cell--unrenderable");
      tdStatus.setAttribute("data-evidence-field", "disclosure");
      markEvidenceCell(tdStatus, row.row_id);
      tr.appendChild(tdStatus);

      tbody.appendChild(tr);
      if (!rowElementMap[row.row_id]) rowElementMap[row.row_id] = [];
      rowElementMap[row.row_id].push(tr);
    }
    table.appendChild(tbody);
    var disclosure = document.createElement("details");
    disclosure.className = "kz-complete-table";
    var summary = document.createElement("summary");
    summary.className = "kz-complete-table__summary";
    summary.textContent = "展开完整数据表";
    disclosure.appendChild(summary);
    disclosure.appendChild(table);
    container.appendChild(disclosure);
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
    var previousRows = rowElementMap[selectedRowId] || [];
    for (var p = 0; p < previousRows.length; p++) {
      previousRows[p].classList.remove("kz-chart-table__row--selected");
    }
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
    var targetRows = rowElementMap[rowId] || [];
    for (var r = 0; r < targetRows.length; r++) {
      targetRows[r].classList.add("kz-chart-table__row--selected");
    }
    if (targetRows.length && typeof targetRows[0].scrollIntoView === "function") {
      targetRows[0].scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
    var keys = Object.keys(chartRowMap);
    for (var i = 0; i < keys.length; i++) {
      var gIdx = keys[i];
      var idxMap = chartRowMap[gIdx];
      if (idxMap[rowId] !== undefined) {
        var inst = chartInstances[gIdx];
        if (inst && !inst.isDisposed()) {
          var target = idxMap[rowId];
          var seriesIndex = 0;
          var dataIndex = target;
          if (target && typeof target === "object") {
            seriesIndex = target.seriesIndex || 0;
            dataIndex = target.dataIndex;
          } else if (inst.getOption().series.length > 1) {
            seriesIndex = 1;
          }
          inst.dispatchAction({
            type: "highlight",
            seriesIndex: seriesIndex,
            dataIndex: dataIndex
          });
        }
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
      var directRowId =
        params &&
        params.data &&
        (params.data._row_id || params.data.row_id || params.data.rowId);
      var idx = rowIndexFromClick(groupIndex, params);
      if (directRowId) idx = -1;
      if (
        !directRowId &&
        (typeof idx !== "number" || idx < 0 || idx >= rowIds.length)
      ) {
        return;
      }
      var trigger = null;
      if (params.event && params.event.event && params.event.event.target) {
        trigger = params.event.event.target;
      }
      activateRow(String(directRowId || rowIds[idx]), trigger);
    });
  }

  function positionBarEvidenceTargets(chartDiv, inst) {
    var targets = chartDiv.querySelectorAll(".kz-chart-evidence-hit");
    for (var i = 0; i < targets.length; i++) {
      var seriesIndex = Number(targets[i].getAttribute("data-chart-series-index") || 0);
      var dataIndex = Number(targets[i].getAttribute("data-chart-data-index"));
      var series = inst.getModel().getSeriesByIndex(seriesIndex);
      var glyph = series && series.getData().getItemGraphicEl(dataIndex);
      if (!glyph || typeof glyph.getBoundingRect !== "function") {
        targets[i].hidden = true;
        continue;
      }
      var bounds = glyph.getBoundingRect();
      var centerX = bounds.x + bounds.width / 2;
      var centerY = bounds.y + bounds.height / 2;
      var transform = glyph.getComputedTransform();
      if (transform) {
        var transformedX = transform[0] * centerX + transform[2] * centerY + transform[4];
        centerY = transform[1] * centerX + transform[3] * centerY + transform[5];
        centerX = transformedX;
      }
      if (!isFinite(centerX) || !isFinite(centerY)) {
        targets[i].hidden = true;
        continue;
      }
      targets[i].hidden = false;
      targets[i].style.left = String(centerX - targets[i].offsetWidth / 2) + "px";
      targets[i].style.top = String(centerY - targets[i].offsetHeight / 2) + "px";
    }
  }

  function renderBarEvidenceTargets(chartDiv, inst, groupIndex, group) {
    if (chartTypeByGroup[groupIndex] !== "bar") return;
    var old = chartDiv.querySelectorAll(".kz-chart-evidence-hit");
    for (var o = 0; o < old.length; o++) old[o].remove();
    var rowTargets = chartRowMap[groupIndex] || {};
    for (var i = 0; i < group.rows.length; i++) {
      var row = group.rows[i];
      if (!isRenderable(row)) continue;
      var value = row.numeric_value != null ? row.numeric_value : row.value;
      var mapped = rowTargets[String(row.row_id)];
      if (mapped === undefined) continue;
      var seriesIndex = typeof mapped === "object" ? mapped.seriesIndex : 0;
      var dataIndex = typeof mapped === "object" ? mapped.dataIndex : mapped;
      var button = document.createElement("button");
      button.type = "button";
      button.className = "kz-chart-evidence-hit";
      button.setAttribute("data-chart-value", String(value));
      button.setAttribute("data-chart-series-index", String(seriesIndex));
      button.setAttribute("data-chart-data-index", String(dataIndex));
      button.style.width = "32px";
      button.style.height = "32px";
      button.setAttribute("data-chart-evidence-open", String(row.row_id));
      button.setAttribute("aria-label", "查看数值 " + String(value) + " 的数据依据");
      (function (rowId, target) {
        target.addEventListener("click", function (event) {
          event.preventDefault();
          event.stopPropagation();
          activateRow(rowId, target);
        });
      })(String(row.row_id), button);
      chartDiv.appendChild(button);
    }
    positionBarEvidenceTargets(chartDiv, inst);
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
    var keys = Object.keys(allRowIdsByGroup).sort(function (a, b) {
      return Number(a) - Number(b);
    });
    for (var i = 0; i < keys.length; i++) {
      var list = allRowIdsByGroup[keys[i]] || [];
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
      var rowsForFact = rowElementMap[rid] || [];
      for (var rt = 0; rt < rowsForFact.length; rt++) {
        rowsForFact[rt].style.display = visibleSet[rid] ? "" : "none";
      }
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
          var filteredPlan = presentationPlan(filteredGroup);
          if (wrapper) {
            wrapper.setAttribute("data-grid-span", String(filteredPlan.grid_span));
            wrapper.setAttribute("data-observation-count", String(filteredPlan.observation_count));
          }
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

  function fitHeatmapLabels(inst, chartDiv) {
    if (chartDiv.getAttribute("data-chart-type") !== "heatmap") return;
    var narrow = chartDiv.clientWidth <= 480;
    inst.setOption({
      grid: { left: narrow ? 120 : 100, right: narrow ? 0 : 40,
        top: 24, bottom: narrow ? 90 : 40, containLabel: !narrow },
      xAxis: { axisLabel: { interval: 0 } },
      yAxis: { axisLabel: { width: narrow ? 104 : null,
        overflow: narrow ? "break" : null, lineHeight: 20, margin: 8 } },
      visualMap: { itemWidth: 12, itemHeight: narrow ? 110 : 140 }
    });
  }

  function fitBarLabels(inst, chartDiv) {
    if (chartDiv.getAttribute("data-chart-type") !== "bar") return;
    var axis = inst.getOption().xAxis[0];
    if (!axis || axis.type !== "category" || !axis.data.length) return;
    var count = axis.data.length;
    var viewport = chartDiv.parentElement;
    var width = Math.max(viewport.clientWidth, count > 3 ? count * 120 + 100 : 0);
    chartDiv.style.width = width + "px";
    chartDiv.style.maxWidth = "none";
    viewport.tabIndex = width > viewport.clientWidth ? 0 : -1;
    viewport.setAttribute("aria-label", "完整图形，较宽时可左右滚动");
    inst.resize();
    inst.setOption({
      grid: { left: 64, right: 24, top: 32, bottom: count <= 3 ? 66 : 88,
        containLabel: false },
      xAxis: { nameGap: 64, axisLabel: {
        interval: 0, hideOverlap: false, fontSize: 14, lineHeight: 18,
        rotate: count <= 3 ? 0 : 30,
        width: Math.max(40, Math.min(180, (width - 64) / count - 8)),
        overflow: "break",
        formatter: function (value) { return String(value).replace(/｜/g, "\n"); }
      } }
    });
  }

  function initGroupChart(chartDiv, groupIndex, group) {
    chartTypeByGroup[groupIndex] = resolveChartType(group);
    allRowIdsByGroup[groupIndex] = collectRowIds(group);
    var rowIds = chartTypeByGroup[groupIndex] === "bar"
      ? collectRenderableRowIds(group)
      : collectRowIds(group);
    chartRowIdsByGroup[groupIndex] = rowIds.slice();
    var idxMap = {};
    for (var r = 0; r < rowIds.length; r++) idxMap[rowIds[r]] = r;
    chartRowMap[groupIndex] = idxMap;

    if (!groupHasRenderable(group)) {
      if (chartTypeByGroup[groupIndex] !== "heatmap") {
        if (!chartDiv.querySelector(".kz-chart-undisclosed")) {
          renderUndisclosedMessage(chartDiv, group);
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
    }

    chartDiv.classList.remove("kz-chart-group__chart--undisclosed");
    chartDiv.style.width = "100%";
    chartDiv.style.height = presentationPlan(group).target_height + "px";
    chartDiv.style.minHeight = "";

    var option = buildOption(group);
    if (!option || !ECHARTS_READY) {
      chartDiv.textContent = "当前组暂无可绘制数值，完整表格仍保留全部记录";
      return;
    }
    if (usesIdentitySeries(group) && option.series) {
      var groupedMap = {};
      for (var gs = 0; gs < option.series.length; gs++) {
        var points = option.series[gs].data || [];
        for (var gp = 0; gp < points.length; gp++) {
          var pointRowId =
            points[gp] &&
            (points[gp]._row_id || points[gp].row_id || points[gp].rowId);
          if (pointRowId) {
            groupedMap[String(pointRowId)] = { seriesIndex: gs, dataIndex: gp };
          }
        }
      }
      chartRowMap[groupIndex] = groupedMap;
    }
    var inst = window.echarts.init(chartDiv, null, { renderer: "svg" });
    inst.setOption(option);
    fitHeatmapLabels(inst, chartDiv);
    fitBarLabels(inst, chartDiv);
    chartInstances[groupIndex] = inst;
    optionCache[groupIndex] = option;
    wireChartClick(groupIndex);
    renderBarEvidenceTargets(chartDiv, inst, groupIndex, group);
  }

  function resizeCharts() {
    var keys = Object.keys(chartInstances);
    for (var i = 0; i < keys.length; i++) {
      var inst = chartInstances[keys[i]];
      if (!inst || inst.isDisposed()) continue;
      inst.resize();
      var chartDiv = document.getElementById("kz-chart-" + keys[i]);
      if (!chartDiv) continue;
      fitHeatmapLabels(inst, chartDiv);
      fitBarLabels(inst, chartDiv);
      positionBarEvidenceTargets(chartDiv, inst);
    }
  }

  function init() {
    var moduleEl = document.getElementById("kz-chart-module");
    if (!moduleEl) return;
    if (resizeObserver) resizeObserver.disconnect();
    Object.keys(chartInstances).forEach(function (key) {
      var previous = chartInstances[key];
      if (previous && !previous.isDisposed()) previous.dispose();
    });
    moduleEl.innerHTML = "";
    moduleEl.setAttribute("data-group-count", String(chartGroups.length));
    selectedRowId = null;
    chartInstances = {};
    chartRowMap = {};
    chartRowIdsByGroup = {};
    allRowIdsByGroup = {};
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
      if (typeof window.ResizeObserver === "function") {
        if (!resizeObserver) resizeObserver = new ResizeObserver(resizeCharts);
        resizeObserver.observe(chartDiv.parentElement);
      }
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

    if (!windowResizeBound) {
      window.addEventListener("resize", resizeCharts);
      windowResizeBound = true;
    }
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
