/* 门户交互：ECharts 初始化 + 表格筛选。数据来自 <script id="charts" type="application/json">。 */
(function () {
  var C = { brand: "#FF9900", brand2: "#FFCC00", ops: "#407AAA", stat: "#587B3B", pv: "#A85F34", muted: "#64676B" };
  var palette = [C.brand, C.ops, C.stat, C.pv, C.brand2, "#8E6FB5", "#2E9C9C"];
  var instances = {}, observers = [];
  function el(id) { return document.getElementById(id); }
  function chart(id, option) {
    var node = el(id);
    if (!node) return;
    if (!window.echarts) { node.innerHTML = '<p class="muted">图表库未加载（运行 scripts/fetch_assets.sh）</p>'; return; }
    var c = echarts.init(node);
    instances[id] = c;
    option.color = option.color || palette;
    option.textStyle = { fontFamily: '"Microsoft YaHei","PingFang SC","Noto Sans CJK SC",Arial' };
    c.setOption(option);
    var observer = new ResizeObserver(function () { c.resize(); });
    observer.observe(node); observers.push(observer);
  }
  var dataNode = el("charts");
  var D = dataNode ? JSON.parse(dataNode.textContent || "{}") : {};
  if (D.heat) {
    chart("chart-heat", {
      tooltip: { formatter: function (p) { return D.heat.y[p.value[1]] + " · " + D.heat.x[p.value[0]] + "：" + p.value[2] + " 个药物"; } },
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
      title: { text: g.title, subtext: g.subtitle, textStyle: { fontSize: 13 }, subtextStyle: { fontSize: 11 } },
      tooltip: {}, grid: { left: 260, right: 40, top: 60, bottom: 20 },
      xAxis: { type: "value" }, yAxis: { type: "category", data: g.labels, axisLabel: { width: 240, overflow: "truncate" } },
      series: [{ type: "bar", data: g.values, barMaxWidth: 18, label: { show: true, position: "right" } }]
    });
  });
  if (D.size) {
    var designHeight = Math.max(200, Math.min(540, D.size.labels.length * 24 + 72));
    ["chart-size", "chart-phase-pie"].forEach(function (id) {
      if (el(id)) el(id).style.height = designHeight + "px";
    });
    chart("chart-size", {
      tooltip: { trigger: "axis" }, grid: { left: 130, right: 50, top: 24, bottom: 30 },
      yAxis: { type: "category", data: D.size.labels, inverse: true }, xAxis: { type: "value", name: "样本量" },
      series: [{ type: "bar", data: D.size.values, barMaxWidth: 22,
        label: { show: true, position: "right" } }]
    });
  }
  if (D.phase) {
    chart("chart-phase-pie", { tooltip: {}, series: [{ type: "pie", radius: ["40%", "70%"], data: D.phase }] });
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
    var visible = Array.from(table.querySelectorAll("tbody tr")).filter(function (tr) { return tr.style.display !== "none"; });
    var selected = new Set(visible.map(function (tr) { return tr.dataset.trial; }));
    var indices = D.size.labels.map(function (label, index) { return selected.has(label) ? index : -1; }).filter(function (i) { return i >= 0; });
    if (instances["chart-size"]) {
      var node = el("chart-size");
      node.style.height = Math.max(180, Math.min(540, indices.length * 24 + 72)) + "px";
      node.closest(".card").hidden = !indices.length;
      instances["chart-size"].setOption({ yAxis: { data: indices.map(function (i) { return D.size.labels[i]; }) },
        series: [{ data: indices.map(function (i) { return D.size.values[i]; }) }] });
    }
    var phases = {};
    visible.forEach(function (tr) { phases[tr.dataset.phase] = (phases[tr.dataset.phase] || 0) + 1; });
    if (instances["chart-phase-pie"]) {
      el("chart-phase-pie").closest(".card").hidden = !visible.length;
      instances["chart-phase-pie"].setOption({ series: [{ data: Object.keys(phases).map(function (name) { return { name: name, value: phases[name] }; }) }] });
    }
    if (el("design-count")) el("design-count").textContent = visible.length + " / " + table.querySelectorAll("tbody tr").length + " 项研究";
    document.querySelectorAll(".endpoint-entry").forEach(function (entry) { entry.hidden = !selected.has(entry.dataset.trial); });
    document.querySelectorAll(".endpoint-entry").forEach(function (entry) {
      var row = entry.closest("tr"); row.hidden = !Array.from(row.querySelectorAll(".endpoint-entry")).some(function (e) { return !e.hidden; });
    });
  }
  window.addEventListener("pagehide", function () {
    observers.forEach(function (observer) { observer.disconnect(); });
    Object.keys(instances).forEach(function (id) { instances[id].dispose(); });
  });
})();
