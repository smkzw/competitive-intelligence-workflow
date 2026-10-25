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
    option.animation = option.animation !== false && !reducedMotion;
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
    var grid = phaseNode && phaseNode.closest('.card').parentElement;
    if (grid && grid.style) grid.style.gridTemplateColumns = '';
    var heatCard = heatNode && heatNode.closest('.card'), phaseCard = phaseNode && phaseNode.closest('.card');
    if (heatCard && heatCard.style) heatCard.style.gridColumn = heat.y.length > 4 ? 'span 12' : 'span 6';
    if (phaseCard && phaseCard.style) phaseCard.style.gridColumn =
      phases.x.length > 4 || phases.series.length > 2 ? 'span 12' : 'span 6';
    if (heat.data.length) {
    var pageSize = heat.scoped ? 4 : 6, rowHeight = heat.scoped ? 88 : 40;
    setPanelHeight('chart-heat', Math.min(440, 88 + Math.min(pageSize, heat.y.length) * rowHeight));
    chart("chart-heat", {
      tooltip: { formatter: function (p) { return safeText(heat.y[p.value[1]]) + " · " + safeText(heat.x[p.value[0]]) + "：" + safeText(p.value[2]) + " 个药物"; } },
      grid: { left: 180, right: 32, top: 12, bottom: 64 },
      xAxis: { type: "category", data: heat.x },
      yAxis: { type: "category", data: heat.y, axisLabel: { width: 160, overflow: 'break' } },
      dataZoom: [{ type: 'slider', yAxisIndex: 0, right: 0, width: 16, show: heat.y.length > pageSize,
        startValue: 0, endValue: Math.min(pageSize - 1, heat.y.length - 1), filterMode: 'filter' }],
      visualMap: { min: 0, max: Math.max.apply(null, heat.data.map(function (d) { return d.value[2]; }).concat([1])),
        orient: "horizontal", left: "center", bottom: 0, inRange: { color: ["#FFF3E0", C.brand] } },
      series: [{ type: "heatmap", data: heat.data, label: { show: true, formatter: function (p) { return p.value[2]; } } }]
    });
    }
    if (phases.x.length) {
    var compact = phases.x.length <= 2 && phases.series.length <= 2;
    setPanelHeight('chart-phase', compact ? 160 : 208);
    chart("chart-phase", {
      tooltip: { trigger: "axis", formatter: function (items) { return items.map(function (p) {
        return safeText(p.seriesName) + '：' + safeText(p.value) + ' 个药物';
      }).join('<br>'); } }, legend: { type: 'scroll', top: 0 }, grid: { left: 48, right: 16, top: 48, bottom: compact ? 48 : 64 },
      xAxis: { type: "category", data: phases.x, axisLabel: { interval: 0, rotate: phases.x.length > 5 ? 30 : 0 } },
      yAxis: { type: "value", minInterval: 1 },
      series: phases.series.map(function (s) { return { name: s.name, type: "bar", data: s.data,
        itemStyle: {color: s.color}, barMaxWidth: 28, label: {show: true, position: 'top'} }; })
    });
    }
  }
  function landscapeObservations(rows) {
    return rows.flatMap(function (r) {
      var observations = r.phase_observations;
      if (!Array.isArray(observations)) observations = ['global', 'china'].filter(function (region) {
        return r['phase_' + region] && r['phase_' + region] !== 'unknown';
      }).map(function (region) { return {region: region, phase: r['phase_' + region]}; });
      return observations.map(function (o) {
        return Object.assign({}, o, {entity_id: r.id, targets: r.targets, frame: [
          o.region === 'china' ? '中国' : '全球', o.indication,
          o.as_of ? '截至 ' + o.as_of : '', o.source_label || o.source_kind
        ].filter(Boolean).join(' · ')});
      });
    });
  }
  function landscapePoint(points, value) {
    return {value: value, fact_ids: Array.from(new Set(points.map(function (p) { return p.fact_id; }).filter(Boolean))),
      source_ids: Array.from(new Set(points.map(function (p) { return p.source_id; }).filter(Boolean)))};
  }
  function updateLandscapeQuery(table) {
    if (!D.landscape) return;
    var all = D.landscape.rows, labels = D.landscape.phase_labels;
    var visible = table ? new Set(Array.from(table.querySelectorAll('tbody tr')).filter(function (r) {
      return r.style.display !== 'none';
    }).map(function (r) { return r.dataset.entityId; })) : new Set(all.map(function (r) { return r.id; }));
    var rows = all.filter(function (r) { return visible.has(r.id); });
    var observations = landscapeObservations(rows), plotted = observations.filter(function (o) { return labels[o.phase]; });
    var phases = Object.keys(labels).filter(function (p) { return plotted.some(function (o) { return o.phase === p; }); });
    var frames = Array.from(new Set(landscapeObservations(all).map(function (o) { return o.frame; }))).sort();
    var activeFrames = frames.filter(function (f) { return plotted.some(function (o) { return o.frame === f; }); });
    var eligible = plotted.filter(function (o) { return o.region === 'global' && o.targets.length; });
    function targetLabel(target, o) { return target + (o.indication || o.as_of ? '\n' + o.frame : ''); }
    var targets = Array.from(new Set(eligible.flatMap(function (o) {
      return o.targets.map(function (t) { return targetLabel(t, o); });
    }))).sort(), cells = new Map();
    var heatPhases = phases.filter(function (p) { return eligible.some(function (o) { return o.phase === p; }); });
    eligible.forEach(function (o) { new Set(o.targets).forEach(function (t) {
      var key = JSON.stringify([heatPhases.indexOf(o.phase), targets.indexOf(targetLabel(t, o))]);
      if (!cells.has(key)) cells.set(key, []);
      cells.get(key).push(o);
    }); });
    function count(points) { return new Set(points.map(function (o) { return o.entity_id; })).size; }
    drawLandscape({x: heatPhases.map(function (p) { return labels[p]; }), y: targets,
      scoped: eligible.some(function (o) { return o.indication || o.as_of; }),
      data: Array.from(cells, function (pair) { return landscapePoint(pair[1], JSON.parse(pair[0]).concat(count(pair[1]))); })},
      {x: phases.map(function (p) { return labels[p]; }), series: activeFrames.map(function (f) {
        return {name: f, color: palette[frames.indexOf(f) % palette.length], data: phases.map(function (p) {
          var points = plotted.filter(function (o) { return o.frame === f && o.phase === p; });
          return landscapePoint(points, count(points));
        })};
      })});
    if (el('landscape-count')) el('landscape-count').textContent = rows.length + ' / ' + all.length + ' 个药物 · 全球阶段 ' +
      count(observations.filter(function (o) { return o.region === 'global'; })) + ' · 中国阶段 ' +
      count(observations.filter(function (o) { return o.region === 'china'; })) + ' · 靶点与阶段 ' + count(eligible);
  }
  if (D.landscape) updateLandscapeQuery(null);
  function resultTooltip(p) {
    var point = p.data || {};
    return safeText(point.series_name || point.label || "") + "<br>" + safeText(point.visit || "") +
      "：" + safeText(Array.isArray(point.value) ? point.value[1] : point.value) +
      (point.dispersion_text ? "<br>" + safeText(point.dispersion_text) : "");
  }
  function resultBars(points) {
    var labels = points.map(function (p, i) {
      return String(i + 1) + " · " + (p.axis_label || p.drug_label || p.arm || "研究观察") +
        (p.visit ? " · " + p.visit : "");
    });
    // Same decision drives row spacing, visible count and figure height.
    var units = Math.max.apply(null, labels.map(function (text) {
      return Array.from(text).reduce(function (sum, ch) { return sum + (ch.charCodeAt(0) > 255 ? 1 : 0.6); }, 0);
    }).concat([1]));
    var rowHeight = Math.max(44, Math.ceil(units * readingSize / 280) * 22 + 12);
    var visible = Math.max(1, Math.min(6, points.length, Math.floor(276 / rowHeight)));
    return { labels: labels, visible: visible, height: Math.max(120, visible * rowHeight + 60) };
  }
  function resultOption(group, points) {
    // Clinical observations appear immediately, including their true final values.
    var option = { animation: false, tooltip: { formatter: resultTooltip },
      grid: { left: 72, right: 48, top: 24, bottom: 72 } };
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
          (point && point.phase_label ? point.phase_label + " · " : "") + "组" + name +
          (point && point.arm_label ? " · " + point.arm_label : "");
      } };
      option.xAxis = { type: "value", scale: true, name: group.display_axis === "weeks" ? "周" : group.axis_unit === "months" ? "月" : "天" };
      option.yAxis = { type: "value", scale: true };
      var labelCharacters = Math.max.apply(null, points.map(function (p) {
        return String(p.value).length + String(order.indexOf(p.series_key) + 1).length + 2;
      }));
      option.grid.right = Math.max(112, Math.ceil(labelCharacters * readingSize * 0.7 + 16));
      option.series = Array.from(series.values()).map(function (items) {
        items.sort(function (a, b) { return a.x - b.x; });
        var index = order.indexOf(items[0].series_key), at = new Map(items.map(function (p) { return [p.x, p]; }));
        return { name: String(index + 1), type: "line", smooth: false, connectNulls: false, symbolSize: 7,
          labelLayout: { moveOverlap: "shiftY" },
          endLabel: { show: true, formatter: "组" + (index + 1) + "：" + String(items[items.length - 1].value) },
          lineStyle: { color: palette[index % palette.length] }, itemStyle: { color: palette[index % palette.length] },
          data: (group.positions || items.map(function (p) { return p.x; })).map(function (x) {
            var p = at.get(x);
            var plottedX = group.display_axis === "weeks" ? x / 7 : x;
            return p ? Object.assign({}, p, { value: [plottedX, p.value],
              label: { show: items.length <= 8 && p !== items[items.length - 1],
                position: index % 2 ? 'bottom' : 'top', distance: 8 } }) : { value: [plottedX, null] };
          }),
          label: { formatter: function (p) { return p.value[1]; } } };
      });
    } else {
      var bars = resultBars(points);
      option.grid.left = 310; option.grid.bottom = 32;
      option.xAxis = { type: "value", scale: false };
      option.yAxis = { type: "category", inverse: true, data: bars.labels,
        axisLabel: { width: 280, overflow: "break", lineHeight: 22 } };
      option.dataZoom = [{ type: "slider", yAxisIndex: 0, right: 0, width: 16, show: points.length > bars.visible,
        startValue: 0, endValue: bars.visible - 1, filterMode: "filter" }];
      option.series = [{ type: "bar", barMaxWidth: 22, data: points.map(function (p) {
        return Object.assign({}, p, { itemStyle: { color: palette[order.indexOf(p.series_key) % palette.length] } });
      }),
        label: { show: true, position: "right" } }];
    }
    return option;
  }
  var resultPreferred, resultClickBound = false;
  function resultStudyContext(points) {
    var caption = el('result-study-reference'), list = el('result-study-list'), container = el('result-study-context');
    if (!caption || !list) return;
    var studies = new Map();
    points.forEach(function (p) {
      if (p.trial && !studies.has(p.trial)) studies.set(p.trial,
        (p.trial_label && p.trial_label !== p.trial ? p.trial_label + ' · ' : '') + p.trial);
    });
    caption.textContent = studies.size === 1 ? Array.from(studies.values())[0] : '研究来源 ' + studies.size + ' 项';
    if (container) container.hidden = !studies.size;
    list.replaceChildren();
    studies.forEach(function (label) {
      var node = document.createElement('p'); node.textContent = label; list.appendChild(node);
    });
  }
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
    resultStudyContext(points);
    var viewGroup = Object.assign({}, group, { kind: group.kind === "line" && new Set(points.map(function (p) { return p.x; })).size > 1 ? "line" : "bar" });
    var height = viewGroup.kind === "line" ? 320 : resultBars(points).height;
    setPanelHeight("chart-result", height);
    el("result-definition").textContent = [group.title].concat(group.facets || [],
      [group.population, group.unit, group.stat_type]).filter(Boolean).join(" · ");
    if (el("result-unit")) el("result-unit").textContent = [group.unit_label || group.unit,
      group.stat_label || group.stat_type].concat(group.facets || []).filter(Boolean).join(" · ");
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
        var identity = summary.closest('.trial-identity'), study = el('design-evidence-study');
        if (study) {
          study.textContent = row && row.dataset.trial || identity && identity.dataset.clinicalTrial || '';
          study.hidden = !study.textContent;
        }
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
