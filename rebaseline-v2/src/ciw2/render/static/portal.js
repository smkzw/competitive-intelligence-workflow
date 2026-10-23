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
    var c = echarts.init(node);
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
    c.setOption(option);
    var observer = new ResizeObserver(function () { c.resize(); });
    observer.observe(node); observers.push(observer);
  }
  var dataNode = el("charts");
  var D = dataNode ? JSON.parse(dataNode.textContent || "{}") : {};
  var DESIGN_MAX_HEIGHT = 336, DESIGN_MIN_HEIGHT = 120, DESIGN_VISIBLE_ROWS = 12;
  var DESIGN_ROW_HEIGHT = 24, DESIGN_PANEL_CHROME = 48, PHASE_MIN_HEIGHT = 120;
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
  (D.groups || []).forEach(function (g, i) {
    chart("chart-group-" + i, {
      title: { text: g.title, subtext: g.subtitle, textStyle: { fontSize: readingSize }, subtextStyle: { fontSize: readingSize } },
      tooltip: {}, grid: { left: 260, right: 40, top: 60, bottom: 20 },
      xAxis: { type: "value" }, yAxis: { type: "category", data: g.labels, axisLabel: { width: 240, overflow: "break" } },
      series: [{ type: "bar", data: g.values, barMaxWidth: 18, label: { show: true, position: "right" } }]
    });
  });
  if (D.size) {
    setPanelHeight("chart-size", designPanelHeight(D.size.labels.length));
    chart("chart-size", {
      tooltip: { trigger: "axis" }, grid: { left: 130, right: 70, top: 24, bottom: 30 },
      dataZoom: designZoom(D.size.labels.length),
      yAxis: { type: "category", data: D.size.labels, inverse: true }, xAxis: { type: "value", name: "样本量" },
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
    document.querySelectorAll(".endpoint-entry").forEach(function (entry) {
      var row = entry.closest("tr"); row.hidden = !Array.from(row.querySelectorAll(".endpoint-entry")).some(function (e) { return !e.hidden; });
    });
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
    document.querySelectorAll(".design-evidence > summary").forEach(function (summary) {
      summary.addEventListener("click", function (event) {
        if (dialog.open) return;
        var section = summary.parentElement.querySelector(".design-evidence-content");
        if (!section) return;
        event.preventDefault();
        origin = summary.parentElement; content = section; trigger = summary;
        var row = summary.closest("tr");
        title.textContent = (row ? row.dataset.trial + " · " : "") + "入排与依据";
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
