/* 门户交互：ECharts 初始化 + 表格筛选。数据来自 <script id="charts" type="application/json">。 */
(function () {
  var C = { brand: "#FF9900", brand2: "#FFCC00", ops: "#407AAA", stat: "#587B3B", pv: "#A85F34", muted: "#64676B" };
  var palette = [C.brand, C.ops, C.stat, C.pv, C.brand2, "#8E6FB5", "#2E9C9C"];
  var readingSize = 16; // Kangzhe body_compact/chart_label; never shrink individual charts.
  var readingFont = '"Microsoft YaHei","PingFang SC","Noto Sans CJK SC",Arial';
  if (window.getComputedStyle && document.documentElement) {
    var readingStyle = window.getComputedStyle(document.documentElement);
    var cssSize = parseFloat(readingStyle.getPropertyValue("--report-font-body"));
    if (Number.isFinite(cssSize) && cssSize >= 16) readingSize = cssSize;
    readingFont = readingStyle.getPropertyValue("--font").trim() || readingFont;
  }
  var reducedMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var instances = {}, observers = [];
  function el(id) { return document.getElementById(id); }
  function safeText(value) {
    var entities = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
    return String(value).replace(/[&<>"']/g, function (ch) { return entities[ch]; });
  }
  function chart(id, option) {
    var node = el(id);
    if (!node) return;
    if (!window.echarts) { node.innerHTML = '<p class="muted">图表暂不可用，完整数据请见数据表。</p>'; return; }
    var fresh = !instances[id];
    var c = instances[id] || echarts.init(node);
    instances[id] = c;
    option.color = option.color || palette;
    option.textStyle = { fontFamily: readingFont, fontSize: readingSize };
    option.animation = !reducedMotion;
    ["xAxis", "yAxis"].forEach(function (key) {
      var axes = Array.isArray(option[key]) ? option[key] : option[key] ? [option[key]] : [];
      axes.forEach(function (axis) {
        axis.axisLabel = Object.assign({}, axis.axisLabel, { fontSize: readingSize, lineHeight: 22 });
        axis.nameTextStyle = Object.assign({}, axis.nameTextStyle, { fontSize: readingSize });
      });
    });
    (option.series || []).forEach(function (series) {
      series.label = Object.assign({}, series.label, { fontSize: readingSize });
    });
    if (option.legend) option.legend.textStyle = Object.assign({}, option.legend.textStyle, { fontSize: readingSize });
    option.tooltip = Object.assign({}, option.tooltip, { textStyle: { fontSize: readingSize } });
    c.setOption(option, true);
    if (fresh) {
      var observer = new ResizeObserver(function () { c.resize(); });
      observer.observe(node); observers.push(observer);
    }
  }
  var dataNode = el("charts");
  var D = dataNode ? JSON.parse(dataNode.textContent || "{}") : {};
  var DESIGN_MAX_HEIGHT = 336, DESIGN_MIN_HEIGHT = 120, DESIGN_VISIBLE_ROWS = 12;
  var DESIGN_ROW_HEIGHT = 24, DESIGN_PANEL_CHROME = 48, PHASE_MIN_HEIGHT = 120;
  var designIdentities = new Map((D.size && D.size.identities || []).map(function (identity) { return [identity.registry_id, identity]; }));
  if (designIdentities.size) { DESIGN_VISIBLE_ROWS = 6; DESIGN_ROW_HEIGHT = 44; }
  function designLabel(registryId) {
    var identity = designIdentities.get(registryId);
    return identity ? identity.axis_label : registryId;
  }
  function designTooltip(items) {
    var point = Array.isArray(items) ? items[0] : items;
    var id = point.axisValue || point.name, identity = designIdentities.get(id);
    return safeText(identity ? identity.label : id) + "<br>样本量 " + safeText(point.value) +
      (identity ? "<br>" + safeText(identity.registry_id) : "");
  }
  function designZoom(count) {
    var shown = Math.max(1, Math.min(DESIGN_VISIBLE_ROWS, count || 0));
    var end = Math.max(0, Math.min(count - 1, shown - 1));
    return [{ type: "slider", yAxisIndex: 0, right: 0, width: 16,
      show: count > DESIGN_VISIBLE_ROWS, startValue: 0, endValue: end, filterMode: "filter" },
      { type: "inside", yAxisIndex: 0, startValue: 0, endValue: end,
        filterMode: "filter", zoomOnMouseWheel: false, moveOnMouseWheel: true }];
  }
  function designPanelHeight(count) {
    var rows = Math.max(1, Math.min(DESIGN_VISIBLE_ROWS, count || 0));
    return Math.min(DESIGN_MAX_HEIGHT, Math.max(DESIGN_MIN_HEIGHT, rows * DESIGN_ROW_HEIGHT + DESIGN_PANEL_CHROME));
  }
  function phasePanelHeight(count) {
    return Math.min(DESIGN_MAX_HEIGHT, Math.max(PHASE_MIN_HEIGHT, 32 + Math.max(1, count || 0) * 32));
  }
  function setPanelHeight(id, height) {
    var node = el(id);
    if (!node) return;
    node.style.height = height + "px";
    if (instances[id]) instances[id].resize();
  }
  function phaseLegend(counts) {
    return { type: "plain", orient: "vertical", right: 0, top: "middle",
      itemWidth: 14, itemHeight: 14, itemGap: 10, textStyle: { lineHeight: 22 },
      formatter: function (name) { return String(name) + " " + (counts[name] || 0) + " 项"; } };
  }
  function phaseOption(items) {
    var counts = {};
    items.forEach(function (item) { counts[String(item.name)] = item.value; });
    return {
      tooltip: { formatter: function (p) { return safeText(p.name) + "：" + safeText(p.value) + " 项研究"; } },
      legend: phaseLegend(counts),
      series: [{ type: "pie", center: ["32%", "50%"], radius: ["30%", "58%"],
        label: { show: false }, labelLine: { show: false },
        emphasis: { label: { show: false }, labelLine: { show: false } }, data: items }]
    };
  }
  if (D.heat) {
    chart("chart-heat", {
      tooltip: { formatter: function (p) { return safeText(D.heat.y[p.value[1]]) + " · " + safeText(D.heat.x[p.value[0]]) + "：" + safeText(p.value[2]) + " 个药物"; } },
      grid: { left: 140, right: 20, top: 20, bottom: 60 },
      xAxis: { type: "category", data: D.heat.x }, yAxis: { type: "category", data: D.heat.y },
      visualMap: { min: 0, max: Math.max.apply(null, D.heat.data.map(function (d) { return d[2]; }).concat([1])),
        orient: "horizontal", left: "center", bottom: 0, inRange: { color: ["#FFF3E0", C.brand] } },
      series: [{ type: "heatmap", data: D.heat.data, label: { show: true } }]
    });
  }
  if (D.phase_bar) {
    chart("chart-phase", {
      tooltip: { trigger: "axis" }, legend: {}, grid: { left: 40, right: 20, top: 40, bottom: 30 },
      xAxis: { type: "category", data: D.phase_bar.x }, yAxis: { type: "value", minInterval: 1 },
      series: D.phase_bar.series.map(function (s) { return { name: s.name, type: "bar", data: s.data, barMaxWidth: 28 }; })
    });
  }
  function resultTooltip(p) {
    var point = p.data || {};
    return safeText(point.series_name || point.label || "") + "<br>" + safeText(point.visit || "") +
      "：" + safeText(Array.isArray(point.value) ? point.value[1] : point.value);
  }
  function resultOption(group, points) {
    var option = { tooltip: { formatter: resultTooltip }, grid: { left: 72, right: 48, top: 24, bottom: 72 } };
    var order = Array.from(new Set(group.points.map(function (p) { return p.series_key; })));
    if (group.kind === "line") {
      var series = new Map();
      points.forEach(function (p) {
        if (!series.has(p.series_key)) series.set(p.series_key, []);
        series.get(p.series_key).push(p);
      });
      option.legend = { type: "scroll", bottom: 0, formatter: function (name) {
        var point = group.points.find(function (p) { return p.series_key === order[Number(name) - 1]; });
        return (point && point.drug_label ? point.drug_label + " · " : "") + "组" + name;
      } };
      option.xAxis = { type: "value", scale: true, name: group.display_axis === "weeks" ? "周" : group.axis_unit === "months" ? "月" : "天" };
      option.yAxis = { type: "value", scale: true };
      option.series = Array.from(series.values()).map(function (items) {
        items.sort(function (a, b) { return a.x - b.x; });
        var index = order.indexOf(items[0].series_key), at = new Map(items.map(function (p) { return [p.x, p]; }));
        return { name: String(index + 1), type: "line", smooth: false, connectNulls: false, symbolSize: 7,
          labelLayout: { hideOverlap: true },
          lineStyle: { color: palette[index % palette.length] }, itemStyle: { color: palette[index % palette.length] },
          data: (group.positions || items.map(function (p) { return p.x; })).map(function (x) {
            var p = at.get(x);
            var plottedX = group.display_axis === "weeks" ? x / 7 : x;
            return p ? Object.assign({}, p, { value: [plottedX, p.value],
              label: { show: items.length <= 8 || p === items[items.length - 1], position: "top" } }) : { value: [plottedX, null] };
          }),
          label: { formatter: function (p) { return p.value[1]; } } };
      });
    } else {
      option.grid.left = 210; option.grid.bottom = 32;
      option.xAxis = { type: "value", scale: false };
      option.yAxis = { type: "category", inverse: true, data: points.map(function (p, i) {
        return String(i + 1) + " · " + (p.visit && p.visit.length <= 16 ? p.visit : p.trial);
      }) };
      option.dataZoom = [{ type: "slider", yAxisIndex: 0, right: 0, width: 16, show: points.length > 6,
        startValue: 0, endValue: Math.min(5, points.length - 1), filterMode: "filter" }];
      option.series = [{ type: "bar", barMaxWidth: 22, data: points.map(function (p) {
        return Object.assign({}, p, { itemStyle: { color: palette[order.indexOf(p.series_key) % palette.length] } });
      }),
        label: { show: true, position: "right" } }];
    }
    return option;
  }
  var resultPreferred, resultClickBound = false;
  function updateResultQuery(table) {
    var rows = Array.from(table.querySelectorAll("tbody tr"));
    var visible = rows.filter(function (row) { return row.style.display !== "none"; });
    var selected = new Set(visible.map(function (row) { return row.dataset.factId; }));
    var available = (D.groups || []).filter(function (g) { return g.points.some(function (p) { return selected.has(p.fact_id); }); });
    var selector = el("result-group"), availableIds = new Set(available.map(function (g) { return g.id; }));
    Array.from(selector.querySelectorAll("option")).forEach(function (o) { o.hidden = o.disabled = !availableIds.has(o.value); });
    var group = available.find(function (g) { return g.id === resultPreferred; }) || available[0];
    selector.disabled = !group;
    if (el("result-count")) el("result-count").textContent = visible.length + " / " + rows.length + " 条结果 · " + available.length + " 组";
    if (el("result-panel")) el("result-panel").hidden = !group;
    if (el("result-empty")) el("result-empty").hidden = !!group;
    if (!group) return;
    selector.value = group.id;
    var points = group.points.filter(function (p) { return selected.has(p.fact_id); });
    var viewGroup = Object.assign({}, group, { kind: group.kind === "line" && new Set(points.map(function (p) { return p.x; })).size > 1 ? "line" : "bar" });
    var height = viewGroup.kind === "line" ? 320 : Math.max(120, Math.min(336, Math.min(points.length, 6) * 44 + 60));
    setPanelHeight("chart-result", height);
    el("result-definition").textContent = [group.title, group.population, group.unit, group.stat_type].filter(Boolean).join(" · ");
    var statistics = { mean: "均值", median: "中位数", ls_mean: "最小二乘均值", ls_mean_change: "最小二乘均值变化",
      mean_change: "均值变化", percent_change: "百分比变化", proportion: "受试者比例", count_participants: "受试者人数",
      count_events: "事件次数", hazard_ratio: "风险比", odds_ratio: "优势比", risk_difference: "风险差" };
    if (el("result-unit")) el("result-unit").textContent = [group.unit, statistics[group.stat_type] || group.stat_type].filter(Boolean).join(" · ");
    var series = new Map();
    points.forEach(function (p) { if (!series.has(p.series_key)) series.set(p.series_key, p.series_name); });
    el("result-series").replaceChildren();
    var order = Array.from(new Set(group.points.map(function (p) { return p.series_key; })));
    Array.from(series.entries()).forEach(function (item) {
      var node = document.createElement("p"); node.className = "result-series-row";
      node.textContent = "组" + (order.indexOf(item[0]) + 1) + "：" + item[1]; el("result-series").appendChild(node);
    });
    chart("chart-result", resultOption(viewGroup, points));
    if (!resultClickBound && instances["chart-result"]) {
      instances["chart-result"].on("click", function (p) {
        var row = rows.find(function (r) { return p.data && r.dataset.factId === p.data.fact_id; });
        if (!row || row.style.display === "none") return;
        row.closest(".result-table").open = true; row.tabIndex = -1; row.focus(); row.scrollIntoView({ block: "center" });
      });
      resultClickBound = true;
    }
  }
  if (D.groups && el("result-group")) {
    resultPreferred = el("result-group").value;
    el("result-group").addEventListener("change", function () {
      resultPreferred = this.value; updateResultQuery(el("tbl-b"));
    });
    updateResultQuery(el("tbl-b"));
  }
  if (D.size) {
    setPanelHeight("chart-size", designPanelHeight(D.size.labels.length));
    chart("chart-size", {
      tooltip: { trigger: "axis", formatter: designTooltip }, grid: { left: designIdentities.size ? 320 : 130, right: 70, top: 24, bottom: 30 },
      dataZoom: designZoom(D.size.labels.length),
      yAxis: { type: "category", data: D.size.labels, inverse: true,
        axisLabel: { formatter: designLabel, width: 290, overflow: "break", lineHeight: 22 } }, xAxis: { type: "value", name: "样本量" },
      series: [{ type: "bar", data: D.size.values, barMaxWidth: 22,
        label: { show: true, position: "right" } }]
    });
  }
  if (D.phase) {
    setPanelHeight("chart-phase-pie", phasePanelHeight(D.phase.length));
    chart("chart-phase-pie", phaseOption(D.phase));
  }
  document.querySelectorAll("input[data-filter]").forEach(function (inp) {
    var table = el(inp.getAttribute("data-filter"));
    inp.addEventListener("input", function () {
      var q = inp.value.trim().toLowerCase();
      table.querySelectorAll("tbody tr").forEach(function (tr) {
        tr.style.display = !q || tr.textContent.toLowerCase().indexOf(q) >= 0 ? "" : "none";
      });
      if (table.id === "tbl-c") updateDesignQuery(table);
      if (table.id === "tbl-b" && el("result-group")) updateResultQuery(table);
    });
  });
  function updateDesignQuery(table) {
    var rows = Array.from(table.querySelectorAll("tbody tr"));
    var visible = rows.filter(function (tr) { return tr.style.display !== "none"; });
    var selected = new Set(visible.map(function (tr) { return tr.dataset.trial; }));
    var labels = D.size ? D.size.labels : [];
    var values = D.size ? D.size.values : [];
    var indices = labels.map(function (label, index) { return selected.has(label) ? index : -1; }).filter(function (i) { return i >= 0; });
    if (instances["chart-size"]) {
      var node = el("chart-size");
      if (node.closest(".card")) node.closest(".card").hidden = !indices.length;
      if (indices.length) {
        setPanelHeight("chart-size", designPanelHeight(indices.length));
        instances["chart-size"].setOption({ yAxis: { data: indices.map(function (i) { return labels[i]; }) },
          dataZoom: designZoom(indices.length),
          series: [{ data: indices.map(function (i) { return values[i]; }) }] });
      }
    }
    var phases = {};
    visible.forEach(function (tr) {
      if (tr.dataset.phaseStatus === "verified" && tr.dataset.phase) phases[tr.dataset.phase] = (phases[tr.dataset.phase] || 0) + 1;
    });
    var order = (D.phase || []).map(function (item) { return String(item.name); });
    var items = Object.keys(phases).sort(function (a, b) {
      var ia = order.indexOf(a), ib = order.indexOf(b);
      return (ia < 0 ? order.length : ia) - (ib < 0 ? order.length : ib);
    }).map(function (name) { return { name: name, value: phases[name] }; });
    if (instances["chart-phase-pie"]) {
      var pie = el("chart-phase-pie");
      if (pie.closest(".card")) pie.closest(".card").hidden = !items.length;
      if (items.length) {
        var counts = {};
        items.forEach(function (item) { counts[item.name] = item.value; });
        setPanelHeight("chart-phase-pie", phasePanelHeight(items.length));
        instances["chart-phase-pie"].setOption({ legend: phaseLegend(counts), series: [{ data: items }] });
      }
    }
    if (el("design-count")) el("design-count").textContent = visible.length + " / " + rows.length + " 项研究";
    document.querySelectorAll(".endpoint-entry").forEach(function (entry) { entry.hidden = !selected.has(entry.dataset.trial); });
    var endpointRows = Array.from(document.querySelectorAll(".endpoint-index tbody tr"));
    endpointRows.forEach(function (row) {
      row.hidden = !Array.from(row.querySelectorAll(".endpoint-entry")).some(function (e) { return !e.hidden; });
    });
    if (el("endpoint-group-count")) el("endpoint-group-count").textContent =
      endpointRows.filter(function (row) { return !row.hidden; }).length + " / " + endpointRows.length;
  }
  function designEvidenceReader() {
    var dialog = el("design-evidence-dialog"), body = el("design-evidence-body");
    var title = el("design-evidence-title"), close = el("design-evidence-close");
    if (!dialog || !body || !title || !close || typeof dialog.showModal !== "function") return function () {};
    var origin, content, trigger;
    dialog.addEventListener("close", function () {
      if (content && origin) { origin.appendChild(content); origin.open = false; }
      if (trigger) trigger.focus();
      origin = content = trigger = null;
    });
    close.addEventListener("click", function () { dialog.close(); });
    document.querySelectorAll(".design-evidence > summary, #tbl-c .evidence > summary").forEach(function (summary) {
      summary.addEventListener("click", function (event) {
        if (dialog.open) return;
        var section = summary.parentElement.querySelector(".design-evidence-content, .source-evidence-content");
        if (!section) return;
        event.preventDefault();
        origin = summary.parentElement; content = section; trigger = summary;
        var row = summary.closest("tr");
        var readingTitle = summary.getAttribute && summary.getAttribute("data-reading-title") || "入排与依据";
        title.textContent = (row ? (row.dataset.trialLabel || row.dataset.trial) + " · " : "") + readingTitle;
        body.appendChild(content);
        dialog.showModal();
      });
    });
    return function () { if (dialog.open) dialog.close(); };
  }
  var closeEvidenceReader = designEvidenceReader();
  window.addEventListener("pagehide", function () {
    closeEvidenceReader();
    observers.forEach(function (observer) { observer.disconnect(); });
    Object.keys(instances).forEach(function (id) { instances[id].dispose(); });
  });
})();
