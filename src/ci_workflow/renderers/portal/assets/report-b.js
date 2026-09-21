/* B 类门户联动：只读取服务端嵌入的行维度，不在浏览器计算临床事实。 */
(function () {
  "use strict";

  var started = false;

  function armText(row) {
    var explicit = row && (row.arm || row.group);
    if (explicit) return String(explicit);
    if (row && (row.category === "治疗组" || row.category === "对照组")) {
      return String(row.category);
    }
    var groupId = String((row && row.group_id) || "");
    if (groupId.indexOf("treat") !== -1) return "治疗组";
    if (groupId.indexOf("ctrl") !== -1) return "对照组";
    return "组别未列示";
  }

  function normalizeBChartGroups() {
    var source = window.__CHART_GROUPS__ || [];
    if (!Array.isArray(source)) return;
    var pageId = String(window.__B_PAGE_ID__ || "");
    var prepared = [];
    for (var i = 0; i < source.length; i += 1) {
      var original = source[i] || {};
      var rows = Array.isArray(original.rows) ? original.rows : [];
      var normalizedRows = [];
      for (var j = 0; j < rows.length; j += 1) {
        var row = {};
        var keys = Object.keys(rows[j] || {});
        for (var k = 0; k < keys.length; k += 1) row[keys[k]] = rows[j][keys[k]];
        var arm = armText(row);
        if (!row.arm && arm !== "组别未列示") row.arm = arm;
        if (!row.group_id && (arm === "治疗组" || arm === "对照组")) {
          row.group_id = arm === "治疗组" ? "treatment" : "control";
        }
        if (arm !== "组别未列示") row.category = arm;
        if (pageId === "safety" || row._domain === "safety") {
          var originalEvent = String(row.original_endpoint || row.event || row.display_label_zh || "安全性事件");
          row._b_original_event = originalEvent;
          var identityParts = [];
          var identityValues = [
            row.product_zh || "产品未列示",
            row.trial_zh || "试验未列示"
          ];
          for (var identityIndex = 0; identityIndex < identityValues.length; identityIndex += 1) {
            if (
              identityValues[identityIndex] &&
              identityParts.indexOf(String(identityValues[identityIndex])) === -1
            ) {
              identityParts.push(String(identityValues[identityIndex]));
            }
          }
          row.event = identityParts.join(" · ");
        }
        normalizedRows.push(row);
      }
      var chartType = String(original._chart_type || original.chart_type || "");
      if (chartType !== "line" || original.identity_series || original.cross_trial) {
        var copied = {};
        var groupKeys = Object.keys(original);
        for (var gk = 0; gk < groupKeys.length; gk += 1) {
          copied[groupKeys[gk]] = original[groupKeys[gk]];
        }
        copied.rows = normalizedRows;
        prepared.push(copied);
        continue;
      }
      var armBuckets = {};
      var armOrder = [];
      for (var r = 0; r < normalizedRows.length; r += 1) {
        var armKey = armText(normalizedRows[r]);
        if (!armBuckets[armKey]) {
          armBuckets[armKey] = [];
          armOrder.push(armKey);
        }
        armBuckets[armKey].push(normalizedRows[r]);
      }
      for (var a = 0; a < armOrder.length; a += 1) {
        var bucket = armBuckets[armOrder[a]];
        var timeSet = {};
        for (var t = 0; t < bucket.length; t += 1) {
          if (bucket[t].time) timeSet[String(bucket[t].time)] = true;
        }
        var split = {};
        var splitKeys = Object.keys(original);
        for (var sk = 0; sk < splitKeys.length; sk += 1) {
          split[splitKeys[sk]] = original[splitKeys[sk]];
        }
        split.rows = bucket;
        split._chart_type = Object.keys(timeSet).length > 1 ? "line" : "bar";
        if (armOrder.length > 1 || split.title_zh) {
          split.title_zh =
            String(original.title_zh || "纵向结果") + " · " + armOrder[a];
        }
        prepared.push(split);
      }
    }
    window.__CHART_GROUPS__ = prepared;
  }

  normalizeBChartGroups();

  function filterDimensions() {
    var declared = window.__B_FILTER_DIMENSIONS__ || [];
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
    if (!result.length) return ["product", "trial"];
    return result;
  }

  function valuesFor(params, name) {
    var values = params.getAll(name);
    var seen = {};
    var result = [];
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
      buttons[i].setAttribute("aria-checked", active ? "true" : "false");
    }
  }

  function rowDimensions(rowId) {
    var all = window.__B_ROW_DIMENSIONS__ || {};
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
    var rows = document.querySelectorAll(".kz-chart-table__row[data-row-id]");
    for (var i = 0; i < rows.length; i += 1) {
      var rowId = rows[i].getAttribute("data-row-id");
      var dimensions = rowDimensions(rowId);
      var keys = Object.keys(dimensions);
      for (var j = 0; j < keys.length; j += 1) {
        if (dimensions[keys[j]]) {
          rows[i].setAttribute("data-filter-" + keys[j], dimensions[keys[j]]);
        }
      }
    }
  }

  function disclosureLabel(state) {
    var labels = {
      reported_value: "已报告值",
      reported_zero: "已报告零值",
      not_publicly_disclosed: "未公开",
      not_reported: "未报告",
      not_applicable: "不适用",
      below_reporting_threshold: "低于报告阈值",
      unresolved_due_to_route: "路径未解析",
      conflicting: "来源冲突",
      conflicting_sources: "来源冲突"
    };
    return labels[String(state || "")] || "未报告";
  }

  function rowValueText(row) {
    if (!row || row.renderable === false) {
      return row && row.status ? String(row.status) : disclosureLabel(row && row.disclosure_state);
    }
    if (row.numeric_value !== null && row.numeric_value !== undefined) {
      return String(row.numeric_value);
    }
    if (row.value !== null && row.value !== undefined) return String(row.value);
    if (row.effect !== null && row.effect !== undefined) return String(row.effect);
    if (Array.isArray(row.value_matrix)) {
      return row.value_matrix[0] === null || row.value_matrix[0] === undefined
        ? ""
        : String(row.value_matrix[0]);
    }
    return row.status ? String(row.status) : "";
  }

  function addTableSemantics() {
    var tables = document.querySelectorAll("#kz-chart-module table");
    var title = String(window.__B_PAGE_TITLE__ || "结果");
    for (var i = 0; i < tables.length; i += 1) {
      var table = tables[i];
      if (!table.querySelector("caption")) {
        var caption = document.createElement("caption");
        caption.textContent = title + "数据表";
        table.insertBefore(caption, table.firstChild);
      }
      var headers = table.querySelectorAll("thead th");
      for (var h = 0; h < headers.length; h += 1) {
        headers[h].setAttribute("scope", "col");
      }
    }
  }

  function pageDomain(row) {
    var explicit = row && String(row._domain || "");
    if (explicit) return explicit;
    var pageId = String(window.__B_PAGE_ID__ || "");
    if (pageId === "safety") return "safety";
    if (pageId === "product-trial-profiles") return "profile";
    if (pageId === "trial-exposure-context") return "trial_context";
    if (pageId === "efficacy-safety-matrix") return "matrix";
    if (pageId.indexOf("baseline-") === 0) return "baseline";
    if (
      pageId === "disposition-overview" ||
      pageId === "participant-flow" ||
      pageId === "adherence" ||
      pageId === "loss-exit" ||
      pageId === "screen-failure" ||
      pageId === "rescue-treatment" ||
      pageId === "prohibited-medication" ||
      pageId === "plan-deviation"
    ) {
      return "disposition";
    }
    if (pageId === "subgroups-supporting-evidence") return "supporting";
    return "efficacy";
  }

  function columnsFor(row) {
    var domain = pageDomain(row);
    if (domain === "safety") {
      return [
        ["product_zh", "产品"],
        ["trial_zh", "试验"],
        ["arm_detail", "组别"],
        ["clinical_concept", "安全性事件"],
        ["time_window", "观察时间"],
        ["numeric_value", "数值"],
        ["denominator", "风险人数"],
        ["unit", "单位"],
        ["disclosure_state", "披露状态"]
      ];
    }
    if (domain === "baseline") {
      return [
        ["product_zh", "产品"],
        ["trial_zh", "试验"],
        ["arm_detail", "组别"],
        ["clinical_concept", "基线变量"],
        ["statistical_form_family", "统计形式"],
        ["numeric_value", "数值"],
        ["unit", "单位"],
        ["disclosure_state", "披露状态"]
      ];
    }
    if (domain === "disposition") {
      return [
        ["product_zh", "产品"],
        ["trial_zh", "试验"],
        ["arm_detail", "组别"],
        ["clinical_concept", "完成情况"],
        ["time_window", "观察时间"],
        ["numeric_value", "数值"],
        ["unit", "单位"],
        ["disclosure_state", "披露状态"]
      ];
    }
    if (domain === "matrix") {
      return [
        ["product_zh", "产品"],
        ["trial_zh", "试验"],
        ["display_label_zh", "指标"],
        ["arm", "组别"],
        ["x_value", "疗效位置"],
        ["y_value", "安全性位置"],
        ["size", "比较规模"],
        ["status", "比较状态"],
        ["difference_note", "口径提示"],
        ["disclosure_state", "披露状态"]
      ];
    }
    if (domain === "trial_context") {
      return [
        ["product_zh", "产品"],
        ["trial_zh", "试验"],
        ["role", "研究角色"],
        ["phase", "阶段"],
        ["status", "试验状态"],
        ["sample_size", "总样本量"],
        ["treatment_sample_size", "治疗组样本量"]
      ];
    }
    if (domain === "profile") {
      return [
        ["product_zh", "产品"],
        ["trial_zh", "试验"],
        ["target", "靶点/机制"],
        ["modality", "类型"],
        ["phase", "阶段"],
        ["status", "状态"],
        ["result_status", "结果覆盖"],
        ["regions", "区域"],
        ["developer", "开发方"],
        ["route", "给药途径"],
        ["mechanism", "作用机制"]
      ];
    }
    // 独立复核 B r46（issue-1）：补"统计形式/分析人群"两列，
    // 展开表行可归属到分析集与分析形式（数据已在行字段）
    return [
      ["product_zh", "产品"],
      ["trial_zh", "试验"],
      ["arm_detail", "组别"],
      ["clinical_concept", "疗效指标"],
      ["statistical_form_family_label_zh", "统计形式"],
      ["population_context_label_zh", "分析人群"],
      ["time_window", "评价时间"],
      ["numeric_value", "比较值"],
      ["unit", "单位"],
      ["disclosure_state", "披露状态"]
    ];
  }

  function columnValue(row, key) {
    if (key === "disclosure_state") return disclosureLabel(row.disclosure_state);
    if (key === "statistical_form_family_label_zh") {
      return row.statistical_form_family_label_zh || row.statistic_form || "未列示";
    }
    if (key === "population_context_label_zh") {
      return row.population_context_label_zh || row.population || "分析人群未列示";
    }
    if (key === "product_zh") return row.product_zh || "未列示产品";
    if (key === "trial_zh") return row.trial_zh || "未列示试验";
    if (key === "arm") return armText(row);
    if (key === "arm_role") return row.arm_role_label_zh || row.arm_role || "组别未列示";
    if (key === "arm_detail") {
      // 独立复核 B r35：组别列以中文角色为主，登记明细只作括注，
      // 表格与图例（治疗组/对照组）不再出现两种写法
      var roleLabel = row.arm_role_label_zh || "";
      var detailText = String(row.arm_detail || "");
      if (roleLabel && detailText && detailText !== roleLabel) {
        return roleLabel + "（" + detailText + "）";
      }
      if (roleLabel) return roleLabel;
      return detailText || armText(row);
    }
    if (key === "clinical_concept") {
      var ccLabel = row.clinical_concept_label_zh || row.clinical_concept || "临床概念未列示";
      // 独立复核 B r40：行级携带终点定义序号，展开表内可归属到具体定义
      return row._endpoint_ordinal ? ccLabel + "（" + row._endpoint_ordinal + "）" : ccLabel;
    }
    if (key === "original_endpoint") {
      return row._b_original_event || row.original_endpoint || row.event || "原始终点未列示";
    }
    if (key === "original_variable") {
      return row.original_variable_label_zh || row.original_variable || row.variable || row.display_label_zh || "原始变量未列示";
    }
    if (key === "original_definition") return row.original_definition || "原始定义未列示";
    if (key === "time_window") {
      var twMap = {"Extension Period":"扩展期","LTE Period":"长期扩展期","Long-Term Extension (LTE)":"长期扩展期（LTE）","Long-Term Extension Period (52 Weeks)":"长期扩展期（52周）","Overall Study":"整个研究期","Primary Treatment Period (12 Weeks)":"主要治疗期（12周）","Treatment Period 1 (TP1)":"治疗期1（TP1）","Treatment Period 2 (TP2)":"治疗期2（TP2）","Treatment Period":"治疗期","Baseline":"基线"};
      var twVal = row.time_window || "";
      return twMap[twVal] || twVal;
    }
    if (key === "actual_timepoint") {
      if (row.actual_timepoint === null || row.actual_timepoint === undefined) return "未列示";
      var tp = Number(row.actual_timepoint);
      var unit = row.actual_timepoint_unit || "week";
      // 独立复核第四十二轮：分数周不可读——回到天显示
      if (unit === "week" && tp % 1 !== 0) {
        var d = tp * 7;
        if (Math.abs(d - Math.round(d)) < 0.01) return "第" + Math.round(d) + "天";
        return "约" + (Math.round(tp * 10) / 10) + "周";
      }
      if (unit === "week") return "第" + Math.round(tp) + "周";
      if (unit === "day") return "第" + Math.round(tp) + "天";
      return String(row.actual_timepoint);
    }
    if (key === "actual_timepoint_unit") return row.actual_timepoint_unit || "未列示";
    if (key === "time_window_band") {
      return row.time_window_band_label_zh || row.time_window_band || "时间窗未列示";
    }
    if (key === "population_context") {
      return row.population_context_label_zh || row.population_context || "分析人群未列示";
    }
    if (key === "statistical_form_family") {
      return row.statistical_form_family_label_zh || row.statistical_form_family || "报告未注明统计口径";
    }
    if (key === "event") return row._b_original_event || row.event || "安全性事件未列示";
    if (key === "variable") return row.variable || row.display_label_zh || "基线变量未列示";
    if (key === "field") return row.field || row.display_label_zh || "完成情况字段未列示";
    if (key === "regions") {
      return Array.isArray(row.regions) ? row.regions.join("、") : row.regions || "未列示";
    }
    if (key === "numeric_value") return rowValueText(row) || "未列示";
    if (key === "value") return rowValueText(row) || "未列示";
    if (key === "numerator" || key === "denominator") {
      return row[key] === null || row[key] === undefined ? "未列示" : String(row[key]);
    }
    if (key === "x_value" || key === "y_value" || key === "size") {
      return row[key] === null || row[key] === undefined ? "未列示" : String(row[key]);
    }
    if (key === "sample_size" || key === "treatment_sample_size") {
      return row[key] === null || row[key] === undefined ? "未列示" : String(row[key]);
    }
    if (key === "status") {
      return row.status || disclosureLabel(row.disclosure_state);
    }
    var value = row[key];
    return value === null || value === undefined || value === "" ? "未列示" : String(value);
  }

  function detailPrefix() {
    if (window.__B_SITE_PREFIX__ !== undefined) return String(window.__B_SITE_PREFIX__);
    return /\/(products|trials)\//.test(window.location.pathname) ? "../" : "";
  }

  function markEvidenceCell(td, rowId) {
    td.setAttribute("data-evidence-open", rowId);
    td.setAttribute("tabindex", "0");
    td.setAttribute("role", "button");
    td.addEventListener("keydown", function (event) {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        if (event.stopPropagation) event.stopPropagation();
        // Reuse the charts.js row click path (wired on tr); do not call
        // out-of-scope activateRow from this module.
        if (typeof td.click === "function") td.click();
      }
    });
  }

  function appendTableCell(tr, row, column) {
    var key = column[0];
    var td = document.createElement("td");
    td.className = "kz-chart-table__cell kz-chart-table__cell--" + key;
    td.setAttribute("data-evidence-field", key);
    td.setAttribute("data-label", column[1]);
    var value = columnValue(row, key);
    var linked = false;
    if (key === "product_zh" && row.product_id) {
      var productLink = document.createElement("a");
      productLink.href = detailPrefix() + "products/" + encodeURIComponent(String(row.product_id)) + ".html";
      productLink.textContent = value;
      td.appendChild(productLink);
      linked = true;
    } else if (key === "trial_zh" && row.trial_id) {
      var trialLink = document.createElement("a");
      trialLink.href = detailPrefix() + "trials/" + encodeURIComponent(String(row.trial_id)) + ".html";
      trialLink.textContent = value;
      td.appendChild(trialLink);
      linked = true;
    } else {
      td.textContent = value;
    }
    if (
      key === "disclosure_state" &&
      row.disclosure_state &&
      row.disclosure_state !== "reported_value"
    ) {
      td.classList.add("kz-chart-table__cell--status");
    }
    if (!linked) markEvidenceCell(td, row.row_id);
    tr.appendChild(td);
  }
  function drawerFieldRows(label) {
    var fields = document.querySelectorAll(
      "#kz-evidence-view-fields .kz-evidence-field"
    );
    var result = [];
    for (var i = 0; i < fields.length; i += 1) {
      var dt = fields[i].querySelector("dt");
      if (dt && dt.textContent === label) result.push(fields[i]);
    }
    return result;
  }

  function linkDrawerIdentity(label, id, href, text) {
    if (!id) return;
    var rows = drawerFieldRows(label);
    for (var i = 0; i < rows.length; i += 1) {
      var dd = rows[i].querySelector("dd");
      if (!dd) continue;
      while (dd.firstChild) dd.removeChild(dd.firstChild);
      var link = document.createElement("a");
      link.href = href;
      link.textContent = text;
      dd.appendChild(link);
    }
  }


  function augmentEvidenceDrawer(rowId) {
    var id = rowId;
    if (!id && window.__EVIDENCE_DRAWER__) {
      id = window.__EVIDENCE_DRAWER__.getOpenRowId();
    }
    if (!id) return;
    var row = rowRecord(id);
    if (!row) return;
    linkDrawerIdentity(
      "产品",
      row.product_id,
      detailPrefix() + "products/" + encodeURIComponent(String(row.product_id)) + ".html",
      row.product_zh || "未列示产品"
    );
    linkDrawerIdentity(
      "试验",
      row.trial_id,
      detailPrefix() + "trials/" + encodeURIComponent(String(row.trial_id)) + ".html",
      row.trial_zh || "未列示试验"
    );
  }


  function updateTableContents() {
    var tables = document.querySelectorAll("#kz-chart-module table");
    for (var i = 0; i < tables.length; i += 1) {
      var table = tables[i];
      if (
        table.parentElement &&
        !table.parentElement.classList.contains("kz-b-table-scroll")
      ) {
        var scroll = document.createElement("div");
        scroll.className = "kz-b-table-scroll";
        table.parentNode.insertBefore(scroll, table);
        scroll.appendChild(table);
      }
      var index = Number(table.getAttribute("data-group-index"));
      var group = (window.__CHART_GROUPS__ || [])[index] || {};
      var columns = columnsFor((group.rows || [])[0] || {});
      var header = table.querySelector("thead tr");
      if (header) {
        header.innerHTML = "";
        for (var h = 0; h < columns.length; h += 1) {
          var th = document.createElement("th");
          th.className = "kz-chart-table__th";
          th.textContent = columns[h][1];
          header.appendChild(th);
        }
      }
      var rows = table.querySelectorAll(".kz-chart-table__row[data-row-id]");
      for (var j = 0; j < rows.length; j += 1) {
        var row = rowRecord(rows[j].getAttribute("data-row-id"));
        if (!row) continue;
        rows[j].innerHTML = "";
        for (var c = 0; c < columns.length; c += 1) {
          appendTableCell(rows[j], row, columns[c]);
        }
      }
    }
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
    var visible = [];
    for (var i = 0; i < rows.length; i += 1) {
      var rowId = rows[i].getAttribute("data-row-id");
      var show = matches(rowId, state);
      rows[i].style.display = show ? "" : "none";
      if (show) visible.push(rowId);
    }
    if (
      window.__CHART_SYNC__ &&
      typeof window.__CHART_SYNC__.syncWithFilter === "function"
    ) {
      window.__CHART_SYNC__.syncWithFilter();
    }
    if (
      window.__EVIDENCE_DRAWER__ &&
      typeof window.__EVIDENCE_DRAWER__.pruneToVisible === "function"
    ) {
      window.__EVIDENCE_DRAWER__.pruneToVisible(visible);
    }
    updateStatus(state);
    updateChartStatusMessages();
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

  function collapseFilterForSmallViewport() {
    var panel = document.getElementById("kz-filter-panel");
    if (!panel || window.innerWidth > 1024) return;
    var params = new URLSearchParams(window.location.search || "");
    var dimensions = filterDimensions();
    for (var i = 0; i < dimensions.length; i += 1) {
      if (params.getAll(dimensions[i]).length) return;
    }
    panel.removeAttribute("open");
  }

  function updateChartStatusMessages() {
    var pageId = String(window.__B_PAGE_ID__ || "");
    var message = "";
    if (pageId === "product-trial-profiles") {
      message = "产品与试验属性按完整字段表列示，图形不适用于此页";
    } else if (pageId.indexOf("baseline-") === 0) {
      message = "暂无公开记录（基线）；完整字段表保留披露状态";
    } else if (
      pageId === "disposition-overview" ||
      pageId === "participant-flow" ||
      pageId === "adherence" ||
      pageId === "loss-exit" ||
      pageId === "screen-failure" ||
      pageId === "rescue-treatment" ||
      pageId === "prohibited-medication" ||
      pageId === "plan-deviation"
    ) {
      message = "暂无公开记录（试验完成情况）；完整字段表保留披露状态";
    }
    if (!message) return;
    var titles = document.querySelectorAll(".kz-chart-undisclosed__title");
    for (var i = 0; i < titles.length; i += 1) {
      titles[i].textContent = message;
    }
  }

  function allRowsDomainEmpty() {
    var groups = window.__CHART_GROUPS__ || [];
    var found = false;
    for (var i = 0; i < groups.length; i += 1) {
      var rows = groups[i].rows || [];
      for (var j = 0; j < rows.length; j += 1) {
        found = true;
        if (rows[j]._empty_state !== true) return false;
      }
    }
    return found;
  }


  function updateEmptyState() {
    var groups = window.__CHART_GROUPS__ || [];
    if (groups.length && !allRowsDomainEmpty()) return;
    var emptyTitle = document.querySelector(".kz-chart-empty__title");
    if (emptyTitle && window.__B_EMPTY_STATE__) {
      emptyTitle.textContent = String(window.__B_EMPTY_STATE__);
    }
  }


  function start() {
    if (started) return;
    started = true;
    removeSharedHash();
    updateTableContents();
    addTableSemantics();
    updateEmptyState();
    collapseFilterForSmallViewport();
    var state = sanitizeState(selectedState());
    applyButtonState(state);
    applyState(state);
    bindFilterButtons();
    bindEvidenceTriggers();
    document.addEventListener("kz-evidence-drawer-change", function (event) {
      var detail = (event && event.detail) || {};
      writeFocusUrl(detail.openRowId || "");
      augmentEvidenceDrawer(detail.openRowId || "");
    });
    restoreFocusFromUrl();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      window.setTimeout(start, 0);
    });
  } else {
    window.setTimeout(start, 0);
  }

})();
