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
          var originalEvent = String(row.event || row.display_label_zh || "安全性事件");
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
      var safetyGroup = pageId === "safety";
      for (var safetyRowIndex = 0; safetyRowIndex < normalizedRows.length; safetyRowIndex += 1) {
        if (normalizedRows[safetyRowIndex]._domain === "safety") {
          safetyGroup = true;
          break;
        }
      }
      var safetyTitleSuffix = "";
      if (safetyGroup) {
        var safetyEvents = [];
        var safetyArms = [];
        var safetyTimes = [];
        for (var safetyIndex = 0; safetyIndex < normalizedRows.length; safetyIndex += 1) {
          var safetyRow = normalizedRows[safetyIndex];
          var eventText = String(
            safetyRow._b_original_event || safetyRow.display_label_zh || "安全性事件"
          );
          var armTextValue = armText(safetyRow);
          var timeText = String(safetyRow.time_window || "");
          if (safetyEvents.indexOf(eventText) === -1) safetyEvents.push(eventText);
          if (armTextValue && safetyArms.indexOf(armTextValue) === -1) {
            safetyArms.push(armTextValue);
          }
          if (timeText && safetyTimes.indexOf(timeText) === -1) safetyTimes.push(timeText);
        }
        var safetyTitleParts = [];
        if (safetyEvents.length) safetyTitleParts.push("事件：" + safetyEvents.join("、"));
        if (safetyArms.length) safetyTitleParts.push("组别：" + safetyArms.join("、"));
        if (safetyTimes.length) safetyTitleParts.push("时间窗：" + safetyTimes.join("、"));
        safetyTitleSuffix = safetyTitleParts.join(" · ");
      }
      var chartType = String(original._chart_type || original.chart_type || "");
      if (chartType !== "line") {
        var copied = {};
        var groupKeys = Object.keys(original);
        for (var gk = 0; gk < groupKeys.length; gk += 1) {
          copied[groupKeys[gk]] = original[groupKeys[gk]];
        }
        copied.rows = normalizedRows;
        if (safetyTitleSuffix) {
          copied.title_zh =
            String(original.title_zh || "安全性") + " · " + safetyTitleSuffix;
        }
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
        if (safetyTitleSuffix) {
          split.title_zh =
            String(split.title_zh || original.title_zh || "安全性") +
            " · " +
            safetyTitleSuffix;
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
        caption.textContent = title + "完整数据表";
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
    if (pageId === "evidence-limitations") return "source";
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
        ["event", "安全性事件"],
        ["arm", "组别"],
        ["time_window", "时间窗"],
        ["population", "分析人群"],
        ["numerator", "分子"],
        ["denominator", "分母"],
        ["numeric_value", "发生率/数值"],
        ["unit", "单位"],
        ["disclosure_state", "披露状态"]
      ];
    }
    if (domain === "baseline") {
      return [
        ["product_zh", "产品"],
        ["trial_zh", "试验"],
        ["variable", "基线变量"],
        ["arm", "组别"],
        ["time", "时间点"],
        ["population", "分析人群"],
        ["statistic", "统计形式"],
        ["numerator", "分子"],
        ["denominator", "分母"],
        ["numeric_value", "数值"],
        ["unit", "单位"],
        ["disclosure_state", "披露状态"]
      ];
    }
    if (domain === "disposition") {
      return [
        ["product_zh", "产品"],
        ["trial_zh", "试验"],
        ["field", "完成情况字段"],
        ["arm", "组别"],
        ["time", "时间点/期间"],
        ["population", "分析人群"],
        ["status", "状态"],
        ["numerator", "分子"],
        ["denominator", "分母"],
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
    if (domain === "source") {
      return [
        ["source_name", "来源"],
        ["scope", "覆盖范围"],
        ["maturity", "来源成熟度"],
        ["limitation", "局限"],
        ["status", "记录状态"]
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
    return [
      ["product_zh", "产品"],
      ["trial_zh", "试验"],
      ["display_label_zh", "终点/事件"],
      ["arm", "组别"],
      ["time", "时间点"],
      ["population", "分析人群"],
      ["numerator", "分子"],
      ["denominator", "分母"],
      ["numeric_value", "比较值"],
      ["unit", "单位"],
      ["disclosure_state", "披露状态"]
    ];
  }

  function columnValue(row, key) {
    if (key === "disclosure_state") return disclosureLabel(row.disclosure_state);
    if (key === "product_zh") return row.product_zh || "未列示产品";
    if (key === "trial_zh") return row.trial_zh || "未列示试验";
    if (key === "arm") return armText(row);
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
        activateRow(rowId, td);
      }
    });
  }

  function appendTableCell(tr, row, column) {
    var key = column[0];
    var td = document.createElement("td");
    td.className = "kz-chart-table__cell kz-chart-table__cell--" + key;
    td.setAttribute("data-evidence-field", key);
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

  function appendDrawerContext(row) {
    var fields = document.getElementById("kz-evidence-view-fields");
    if (!fields) return;
    var previous = document.getElementById("kz-b-evidence-context");
    if (previous && previous.parentNode) previous.parentNode.removeChild(previous);
    if (pageDomain(row) !== "source") return;

    var section = document.createElement("section");
    section.id = "kz-b-evidence-context";
    section.className = "kz-b-evidence-context";
    var heading = document.createElement("h3");
    heading.textContent = "来源范围与限制";
    section.appendChild(heading);
    var list = document.createElement("dl");
    var items = [
      ["来源", row.source_name || "来源未列示"],
      ["覆盖范围", row.scope || "范围未列示"],
      ["来源成熟度", row.maturity || "成熟度未列示"],
      ["局限", row.limitation || "局限未列示"]
    ];
    for (var i = 0; i < items.length; i += 1) {
      var item = document.createElement("div");
      item.className = "kz-b-evidence-context__item";
      var dt = document.createElement("dt");
      dt.textContent = items[i][0];
      var dd = document.createElement("dd");
      dd.textContent = String(items[i][1]);
      item.appendChild(dt);
      item.appendChild(dd);
      list.appendChild(item);
    }
    section.appendChild(list);
    fields.parentNode.insertBefore(section, fields.nextSibling);
  }

  function augmentEvidenceDrawer(rowId) {
    var id = rowId;
    if (!id && window.__EVIDENCE_DRAWER__) {
      id = window.__EVIDENCE_DRAWER__.getOpenRowId();
    }
    if (!id) return;
    var row = rowRecord(id);
    if (!row) return;
    var subject = document.getElementById("kz-evidence-view-subject");
    if (pageDomain(row) === "source") {
      var sourceName = row.source_name || row.display_label_zh || "来源记录";
      if (subject) subject.textContent = sourceName + " · 来源成熟度";
      var productRows = drawerFieldRows("产品");
      var trialRows = drawerFieldRows("试验");
      for (var p = 0; p < productRows.length; p += 1) {
        productRows[p].parentNode.removeChild(productRows[p]);
      }
      for (var t = 0; t < trialRows.length; t += 1) {
        trialRows[t].parentNode.removeChild(trialRows[t]);
      }
    } else {
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
    appendDrawerContext(row);
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
    } else if (pageId === "evidence-limitations") {
      message = "来源成熟度按范围、成熟度与局限列示，图形不适用于此页";
    } else if (pageId === "efficacy-safety-matrix") {
      message = "矩阵暂无可绘制覆盖值，完整比较状态见下表";
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
