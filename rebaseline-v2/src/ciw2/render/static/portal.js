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
  var DESIGN_ROW_HEIGHT = 24, DESIGN_PANEL_CHROME = 48, PHASE_MIN_HEIGHT = 72;
  var designIdentities = new Map((D.size && D.size.identities || []).map(function (identity) { return [identity.registry_id, identity]; }));
  var designLabelCounts = new Map();
  designIdentities.forEach(function (identity) {
    designLabelCounts.set(identity.axis_label, (designLabelCounts.get(identity.axis_label) || 0) + 1);
  });
  if (designIdentities.size) { DESIGN_VISIBLE_ROWS = 6; DESIGN_ROW_HEIGHT = 44; }
  function designLabel(registryId) {
    var identity = designIdentities.get(registryId);
    return identity ? identity.axis_label + (designLabelCounts.get(identity.axis_label) > 1 ? "\n" + registryId : "") : registryId;
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
  function phaseOption(items) {
    return {
      tooltip: { formatter: function (p) { return safeText(p.name) + "：" + safeText(p.value) + " 项研究"; } },
      grid: { left: 96, right: 64, top: 8, bottom: 24 },
      xAxis: { type: "value", min: 0, minInterval: 1 },
      yAxis: { type: "category", inverse: true, data: items.map(function (item) { return item.name; }) },
      series: [{ type: "bar", barMaxWidth: 18,
        label: { show: true, position: "right", formatter: "{c} 项" },
        data: items.map(function (item) { return item.value; }) }]
    };
  }
  function drawLandscape(heat, phases) {
    var heatNode = el('chart-heat'), phaseNode = el('chart-phase');
    if (heatNode) heatNode.closest('.card').hidden = !heat.data.length;
    if (phaseNode) phaseNode.closest('.card').hidden = !phases.x.length;
    if (heat.data.length) {
    setPanelHeight('chart-heat', Math.min(336, 88 + Math.min(6, heat.y.length) * 40));
    chart("chart-heat", {
      tooltip: { formatter: function (p) { return safeText(heat.y[p.value[1]]) + " · " + safeText(heat.x[p.value[0]]) + "：" + safeText(p.value[2]) + " 个药物"; } },
      grid: { left: 180, right: 32, top: 12, bottom: 64 },
      xAxis: { type: "category", data: heat.x },
      yAxis: { type: "category", data: heat.y, axisLabel: { width: 160, overflow: 'break' } },
      dataZoom: [{ type: 'slider', yAxisIndex: 0, right: 0, width: 16, show: heat.y.length > 6,
        startValue: 0, endValue: Math.min(5, heat.y.length - 1), filterMode: 'filter' }],
      visualMap: { min: 0, max: Math.max.apply(null, heat.data.map(function (d) { return d[2]; }).concat([1])),
        orient: "horizontal", left: "center", bottom: 0, inRange: { color: ["#FFF3E0", C.brand] } },
      series: [{ type: "heatmap", data: heat.data, label: { show: true } }]
    });
    }
    if (phases.x.length) {
    setPanelHeight('chart-phase', 208);
    chart("chart-phase", {
      tooltip: { trigger: "axis" }, legend: { top: 0 }, grid: { left: 48, right: 16, top: 48, bottom: 64 },
      xAxis: { type: "category", data: phases.x, axisLabel: { interval: 0, rotate: phases.x.length > 5 ? 30 : 0 } },
      yAxis: { type: "value", minInterval: 1 },
      series: phases.series.map(function (s) { return { name: s.name, type: "bar", data: s.data, barMaxWidth: 28 }; })
    });
    }
  }
  function updateLandscapeQuery(table) {
    if (!D.landscape) return;
    var all = D.landscape.rows, labels = D.landscape.phase_labels;
    var visible = table ? new Set(Array.from(table.querySelectorAll('tbody tr')).filter(function (r) {
      return r.style.display !== 'none';
    }).map(function (r) { return r.dataset.entityId; })) : new Set(all.map(function (r) { return r.id; }));
    var rows = all.filter(function (r) { return visible.has(r.id); });
    var phases = Object.keys(labels).filter(function (p) {
      return rows.some(function (r) { return r.phase_global === p || r.phase_china === p; });
    });
    var eligible = rows.filter(function (r) { return labels[r.phase_global] && r.targets.length; });
    var heatPhases = phases.filter(function (p) { return eligible.some(function (r) { return r.phase_global === p; }); });
    var targets = Array.from(new Set(eligible.flatMap(function (r) { return r.targets; }))).sort(), cells = new Map();
    eligible.forEach(function (r) { new Set(r.targets).forEach(function (t) {
      var key = JSON.stringify([heatPhases.indexOf(r.phase_global), targets.indexOf(t)]);
      cells.set(key, (cells.get(key) || 0) + 1);
    }); });
    drawLandscape({x: heatPhases.map(function (p) { return labels[p]; }), y: targets,
      data: Array.from(cells, function (pair) { return JSON.parse(pair[0]).concat(pair[1]); })},
      {x: phases.map(function (p) { return labels[p]; }), series: [
        {name: '全球最高阶段', data: phases.map(function (p) { return rows.filter(function (r) { return r.phase_global === p; }).length; })},
        {name: '中国最高阶段', data: phases.map(function (p) { return rows.filter(function (r) { return r.phase_china === p; }).length; })}]});
    if (el('landscape-count')) el('landscape-count').textContent = rows.length + ' / ' + all.length + ' 个药物 · 全球阶段 ' +
      rows.filter(function (r) { return labels[r.phase_global]; }).length + ' · 中国阶段 ' +
      rows.filter(function (r) { return labels[r.phase_china]; }).length + ' · 靶点与阶段 ' + eligible.length;
  }
  if (D.landscape) updateLandscapeQuery(null);
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
        return (point && point.drug_label ? point.drug_label + " · " : "") +
          (point && point.phase_label ? point.phase_label + " · " : "") + "组" + name;
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
              label: { show: items.length <= 8 || p === items[items.length - 1],
                position: index % 2 ? 'bottom' : 'top', distance: 8 } }) : { value: [plottedX, null] };
          }),
          label: { formatter: function (p) { return p.value[1]; } } };
      });
    } else {
      option.grid.left = 310; option.grid.bottom = 32;
      option.xAxis = { type: "value", scale: false };
      option.yAxis = { type: "category", inverse: true, data: points.map(function (p, i) {
        return String(i + 1) + " · " + (p.axis_label || p.drug_label || p.arm || "研究观察") +
          (p.visit && p.visit.length <= 16 ? " · " + p.visit : "");
      }), axisLabel: { width: 280, overflow: "break", lineHeight: 22 } };
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
    var domain = el('result-domain'), query = el('result-query');
    if (domain) rows.forEach(function (row) {
      var matchesDomain = domain.value === 'all' || row.dataset.domain === domain.value;
      var q = query ? query.value.trim().toLowerCase() : '';
      row.style.display = matchesDomain && (!q || row.textContent.toLowerCase().indexOf(q) >= 0) ? '' : 'none';
    });
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
    if (el("result-unit")) el("result-unit").textContent = [group.unit_label || group.unit,
      group.stat_label || group.stat_type].filter(Boolean).join(" · ");
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
    if (el('result-domain')) el('result-domain').addEventListener('change', function () {
      updateResultQuery(el('tbl-b'));
    });
    updateResultQuery(el("tbl-b"));
  }
  if (D.size) {
    setPanelHeight("chart-size", designPanelHeight(D.size.labels.length));
    chart("chart-size", {
      tooltip: { trigger: "axis", formatter: designTooltip }, grid: { left: designIdentities.size ? 320 : 130, right: 70, top: 24, bottom: 30 },
      dataZoom: designZoom(D.size.labels.length),
      yAxis: { type: "category", data: D.size.labels, inverse: true,
        axisLabel: { formatter: designLabel, interval: 0, width: 290, overflow: "break", lineHeight: 22 } }, xAxis: { type: "value", name: "样本量" },
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
      var extra = el(inp.getAttribute("data-filter-extra"));
      if (extra && extra !== table) {
        var extraRows = Array.from(extra.querySelectorAll("tbody tr"));
        extraRows.forEach(function (tr) {
          tr.style.display = !q || tr.textContent.toLowerCase().indexOf(q) >= 0 ? "" : "none";
        });
        if (el("safety-count")) el("safety-count").textContent =
          extraRows.filter(function (tr) { return tr.style.display !== "none"; }).length + " / " + extraRows.length;
      }
      if (table.id === "tbl-c") updateDesignQuery(table);
      if (table.id === "tbl-a") updateLandscapeQuery(table);
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
        setPanelHeight("chart-phase-pie", phasePanelHeight(items.length));
        chart("chart-phase-pie", phaseOption(items));
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
    document.querySelectorAll(".design-evidence > summary, #tbl-c .evidence > summary, .shared-evidence > summary").forEach(function (summary) {
      summary.addEventListener("click", function (event) {
        if (dialog.open) return;
        var section = summary.parentElement.querySelector(".design-evidence-content, .source-evidence-content");
        if (!section) return;
        event.preventDefault();
        origin = summary.parentElement; content = section; trigger = summary;
        var row = summary.closest("tr");
        var readingTitle = summary.getAttribute && summary.getAttribute("data-reading-title") || "入排与依据";
        title.textContent = (row ? (row.dataset.readingLabel || row.dataset.trialLabel || row.dataset.trial) + " · " : "") + readingTitle;
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
