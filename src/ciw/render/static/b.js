/* B 临床结果 */
(function () {
  const { D, esc, num, nN, tag, src, table, chart, OWN, PAL } = window.U;
  const B = D.b;
  const qs = B.questions;
  let current = null;
  const selectedFrames = new Map();

  function listQuestions() {
    const q = document.getElementById("qsearch").value.trim().toLowerCase();
    const prim = document.getElementById("only-primary").checked;
    const items = qs.filter((x) => (!prim || x.has_primary) && (!q || `${x.label} ${x.time_label} ${x.measure_label} ${(x.frames || []).map(f => f.title + " " + f.population).join(" ")}`.toLowerCase().includes(q)));
    const ul = document.getElementById("qlist");
    ul.innerHTML = items.map((x) => `<li data-id="${esc(x.question_id)}" class="${current && current.question_id === x.question_id ? "on" : ""}">
      <div class="q">${esc(x.label)} · ${esc(x.time_label)}${x.category ? ` · ${esc(x.category)}` : ""}</div>${x.subgroup ? `<div class="s">亚组：${esc(x.subgroup)}</div>` : ""}
      <div class="s">${esc(x.measure_label)} · ${x.trial_ids.length} 项登记研究${x.frames?.length > 1 ? ` · ${x.frames.length} 个口径` : ""}${x.has_primary ? " · 含主要终点" : ""}</div></li>`).join("") || '<li class="empty">无匹配问题</li>';
    ul.querySelectorAll("li[data-id]").forEach((li) => li.onclick = () => select(li.dataset.id));
  }

  // 组标题与产品名相同（只差大小写）时不重复显示
  const sameName = (a, b) => (a || "").toLowerCase().replace(/[^a-z0-9一-鿿]/g, "") === (b || "").toLowerCase().replace(/[^a-z0-9一-鿿]/g, "");
  const groupSuffix = (label, group) => (label && group && !sameName(label, group) && !label.toLowerCase().includes(group.toLowerCase()) ? `（${group}）` : "");
  const rowLabel = (r) => `${r.acronym} · ${r.role === "placebo" ? "安慰剂" : (r.product_label || r.group_title)}${r.role !== "placebo" ? groupSuffix(r.product_label, r.group_title) : ""}`;


  const studyLink = row => row.source_records?.length > 1
    ? row.source_records.map(s => src(s.url, s.acronym)).join(" · ") : src(row.url, row.acronym);

  function drawForest(id, list, ref, log, sourceOnly = false) {
    const cl = list.map((c) => sourceOnly ? `${c.acronym} · ${c.group_labels.join("、")}` : `${c.acronym} · ${c.product_label}${groupSuffix(c.product_label, c.exp_group)}${c.h2h ? " vs " + c.ctrl_group : ""}`);
    if (!list.length) {
      chart(id, { title: { text: "该问题没有可入图的组间比较（见下表）", left: "center", top: "middle", textStyle: { color: "#64676B", fontSize: 16, fontWeight: 400 } } });
      return;
    }
    chart(id, {
      grid: { left: 300, right: 60, top: 20, bottom: 40 },
      tooltip: { formatter: (p) => { const c = list[p.dataIndex]; return `<b>${esc(cl[p.dataIndex])}</b><br>${sourceOnly ? "比较组：" + esc(c.group_labels.join("、")) : "对照：" + esc(c.ctrl_group)}<br>${esc(c.param_type)}：${num(c.value)}${c.ci_lower != null ? `（${c.ci_pct != null ? c.ci_pct + "% " : ""}CI ${num(c.ci_lower)}, ${num(c.ci_upper)}）` : ""}${c.p_value ? `<br>P ${esc(c.p_value)}` : ""}<br>${esc(c.kind_label || "来源报告")}${c.note ? "<br>" + esc(c.note) : ""}`; } },
      xAxis: log ? { type: "log", splitLine: { lineStyle: { type: "dashed" } } } : { type: "value", scale: true, splitLine: { lineStyle: { type: "dashed" } } },
      yAxis: { type: "category", data: cl, inverse: true, axisLabel: { width: 280, overflow: "truncate", color: (v, i) => (list[i] && list[i].is_own ? OWN : "#0F1115") } },
      series: [
        { type: "custom", renderItem: (params, api) => {
          const lo = api.value(1), hi = api.value(2); if (lo == null || hi == null || Number.isNaN(lo) || (log && lo <= 0)) return null;
          const a = api.coord([lo, api.value(0)]), b = api.coord([hi, api.value(0)]);
          return { type: "group", children: [
            { type: "line", shape: { x1: a[0], y1: a[1], x2: b[0], y2: b[1] }, style: { stroke: "#64676B", lineWidth: 1.5 } },
            { type: "line", shape: { x1: a[0], y1: a[1] - 5, x2: a[0], y2: a[1] + 5 }, style: { stroke: "#64676B" } },
            { type: "line", shape: { x1: b[0], y1: b[1] - 5, x2: b[0], y2: b[1] + 5 }, style: { stroke: "#64676B" } }] };
        }, encode: { x: [1, 2], y: 0 }, data: list.map((c, i) => [i, c.plot_lower, c.plot_upper]), z: 1 },
        { type: "scatter", symbolSize: 11, data: list.map((c) => ({ value: c.plot_value, symbol: c.h2h ? "diamond" : c.kind === "computed" ? "emptyCircle" : "circle", itemStyle: { color: c.is_own ? OWN : "#008F8A" } })),
          markLine: { silent: true, symbol: "none", lineStyle: { color: "#999" }, data: ref == null ? [] : [{ xAxis: ref }] }, z: 2 },
      ],
    });
  }

  function drawSourceStatistics(rows) {
    document.getElementById("source-statistics").hidden = !rows.length;
    const selector = document.getElementById("source-stat-kind");
    const types = [...new Set(rows.map(r => r.param_type || "原文统计量"))].sort();
    selector.innerHTML = types.map(t => `<option value="${esc(t)}">${esc(t)}</option>`).join("");
    selector.value = types[0] || "";
    const draw = () => {
      const selected = rows.filter(r => (r.param_type || "原文统计量") === selector.value);
      const plotted = selected.filter(r => r.value != null).map(r => ({ ...r,
        plot_value:r.value, plot_lower:r.ci_lower, plot_upper:r.ci_upper }));
      document.getElementById("source-stat-chart").hidden = !plotted.length;
      if(plotted.length) drawForest("source-stat-chart", plotted, null, false, true);
      table(document.getElementById("source-stat-table"), [
        {label:"研究",html:studyLink}, {label:"比较组",html:r=>r.group_labels.map(esc).join("、")},
        {label:"统计量",key:"param_type"}, {label:"原值",num:true,html:r=>esc(r.value_raw || num(r.value))},
        {label:"置信区间",num:true,html:r=>r.ci_lower == null ? "—" :
          `${r.ci_pct == null ? "" : esc(r.ci_pct) + "% "}${num(r.ci_lower)}, ${num(r.ci_upper)}`},
        {label:"P值",key:"p_value"}, {label:"方法",key:"method"}, {label:"来源",html:r=>src(r.url,"查看原文")}
      ], selected);
    };
    selector.onchange = draw;
    draw();
  }

  function select(id, frameId) {
    current = qs.find((x) => x.question_id === id) || qs[0];
    if (!current) { document.getElementById("q-title").textContent = "暂无可比较的临床问题"; return; }
    listQuestions();
    document.getElementById("q-title").textContent = `${current.label} · ${current.time_label}${current.category ? " · " + current.category : ""}${current.subgroup ? "（亚组：" + current.subgroup + "）" : ""}`;
    document.getElementById("q-sub").textContent = `${current.measure_label}${current.units.length ? " · 单位：" + current.units.join(" / ") : ""}${current.direction === "lower_better" ? " · 数值越低越好" : current.direction === "higher_better" ? " · 数值越高越好" : ""}`;

    const frames = current.frames?.length ? current.frames : [current];
    const frame = frames.find(f => f.frame_id === (frameId || selectedFrames.get(id))) || frames[0];
    selectedFrames.set(id, frame.frame_id);
    const picker = document.getElementById("frame-select");
    document.getElementById("frame-label").hidden = frames.length < 2;
    picker.innerHTML = frames.map((f, i) => `<option value="${esc(f.frame_id || "")}">${i + 1} · ${f.trial_ids.length} 项研究${f.context_label ? " · " + esc(f.context_label) : ""}${f.rows?.length ? " · " + [...new Set(f.rows.map(r => r.product_label).filter(Boolean))].slice(0, 2).map(esc).join("、") : ""}</option>`).join("");
    picker.value = frame.frame_id || "";
    picker.onchange = () => select(id, picker.value);
    document.getElementById("frame-context-text").textContent = [frame.title, frame.description, frame.population].filter(Boolean).join("\n\n");
    document.getElementById("frame-context").open = false;
    drawSourceStatistics(frame.source_statistics || []);
    const comps = frame.comparisons;
    document.getElementById("comparison-details").hidden = !comps.length;
    const differences = comps.filter(c => c.family === "difference" && c.plot_value != null);
    const ratios = comps.filter(c => c.family === "ratio" && c.plot_value > 0);
    document.getElementById("comparison-plots").hidden = !differences.length && !ratios.length;
    document.getElementById("diff-wrap").hidden = !differences.length;
    if(differences.length) drawForest("diff-chart", differences, 0, false);
    document.getElementById("ratio-wrap").hidden = !ratios.length;
    if (ratios.length) drawForest("ratio-chart", ratios, 1, true);

    const rows = frame.rows;
    document.getElementById("arm-values").hidden = !rows.length;
    document.getElementById("arm-details").hidden = !rows.length;
    chart("value-chart", {
      grid: { left: 300, right: 60, top: 20, bottom: 40 },
      tooltip: { formatter: (p) => { const r = rows[p.dataIndex]; return `<b>${esc(rowLabel(r))}</b><br>${num(r.value)} ${esc(r.unit)}${r.n != null ? `<br>N=${r.n}` : ""}${r.spread != null ? `<br>${esc(r.dispersion_type)} ${num(r.spread)}` : ""}${r.lower != null ? `<br>${esc(r.dispersion_type)} ${num(r.lower)}, ${num(r.upper)}` : ""}`; } },
      xAxis: { type: "value", scale: false },
      yAxis: { type: "category", data: rows.map(rowLabel), inverse: true, axisLabel: { width: 280, overflow: "truncate", color: (v, i) => (rows[i] && rows[i].is_own ? OWN : "#0F1115") } },
      series: [{ type: "bar", barWidth: 12, data: rows.map((r) => ({ value: r.value, itemStyle: { color: r.is_own ? OWN : r.role === "placebo" ? "#6E7B8C" : "#008F8A" } })),
        label: { show: true, position: "right", formatter: (p) => num(p.value) } }],
    });

    table(document.getElementById("comp-table"), [
      { label: "试验", key: "acronym", html: (c) => studyLink(c) + `<br><span class="hint">${esc(c.phase)} 期</span>` },
      { label: "产品（试验组）", key: "product_label", html: (c) => `${c.is_own ? '<span class="own-tag">本品 </span>' : ""}${esc(c.product_label)}<br><span class="hint">${esc(c.exp_group)}${c.n_exp != null ? `，N=${c.n_exp}` : ""}</span>` },
      { label: "对照", html: (c) => `${esc(c.ctrl_role_label)}<br><span class="hint">${esc(c.ctrl_group)}${c.n_ctrl != null ? `，N=${c.n_ctrl}` : ""}</span>` },
      { label: "统计量", key: "param_type" },
      { label: "差值", key: "value", num: true, html: (c) => num(c.value) },
      { label: "置信区间", num: true, html: (c) => (c.ci_lower != null ? `${c.ci_pct ? c.ci_pct + "% " : ""}${num(c.ci_lower)}, ${num(c.ci_upper)}` : "—") },
      { label: "P 值", key: "p_value" },
      { label: "方法", key: "method" },
      { label: "依据", html: (c) => `${c.source_kind === "publication" ? src(c.url, "论文") + (c.group_basis === "论文分组" ? " · 论文分组 " : " ") : ""}` + tag(c.kind === "computed" ? "computed" : c.status || "registry") + (c.note ? `<br><span class="hint">${esc(c.note)}</span>` : "") },
    ], comps, { rowClass: (c) => (c.is_own ? "own" : "") });

    table(document.getElementById("row-table"), [
      { label: "试验", key: "acronym", html: (r) => studyLink(r) + `<br><span class="hint">${esc(r.outcome_type)}</span>` },
      { label: "组别", key: "group_title", html: (r) => `${esc(r.group_title)}<br><span class="hint">${esc(r.role_label)}</span>` },
      { label: "N", key: "n", num: true, html: (r) => num(r.n) },
      { label: "数值", key: "value", num: true, html: (r) => num(r.value) },
      { label: "离散度", num: true, html: (r) => (r.spread != null ? `${esc(r.dispersion_type)} ${num(r.spread)}` : r.lower != null ? `${esc(r.dispersion_type)} ${num(r.lower)}, ${num(r.upper)}` : "—") },
      { label: "单位", key: "unit" },
      { label: "终点原文", html: (r) => `${esc(r.title)}${r.class_title ? `<br><span class="hint">${esc(r.class_title)}</span>` : ""}<br><span class="hint">${esc(r.timeframe)}</span>` },
      { label: "分析人群", html: (r) => `<span class="hint">${esc(r.population)}</span>` },
      { label: "依据", html: (r) => `${r.source_kind === "publication" ? src(r.url, "论文") + " " : ""}${tag(r.status || "registry")}` },
    ], rows, { rowClass: (r) => (r.is_own ? "own" : "") });
  }

  // 历时
  const L = B.longitudinal;
  document.getElementById("longitudinal-card").hidden = !L.length;
  const ls = document.getElementById("long-select");
  ls.innerHTML = L.map((c, i) => `<option value="${i}">${esc(c.label)} · ${esc(c.measure_label)}（${c.lines.length} 条曲线）</option>`).join("");
  function drawLong() {
    const c = L[+ls.value || 0];
    if (!c) { chart("long-chart", { title: { text: "暂无多时间点数据", left: "center", top: "middle", textStyle: { color: "#64676B", fontSize: 16, fontWeight: 400 } } }); return; }
    chart("long-chart", {
      tooltip: { trigger: "item", formatter: (p) => { const pt = p.data.pt; return `<b>${esc(p.seriesName)}</b><br>${esc(pt.label)}：${num(pt.value)}${pt.n != null ? `（N=${pt.n}）` : ""}`; } },
      legend: { type: "scroll", top: 0 },
      grid: { left: 60, right: 30, top: 50, bottom: 50 },
      xAxis: { type: "value", name: "周", nameLocation: "end", min: 0 },
      yAxis: { type: "value", scale: true },
      series: c.lines.map((l, i) => ({ name: `${l.acronym} · ${l.role === "placebo" ? "安慰剂" : l.group_title}`, type: "line", connectNulls: false,
        symbolSize: 6, lineStyle: { width: l.is_own ? 3 : 1.6, type: l.role === "placebo" ? "dashed" : "solid" },
        itemStyle: { color: l.is_own ? OWN : l.role === "placebo" ? "#6E7B8C" : PAL[i % PAL.length] },
        data: l.points.map((pt) => ({ value: [pt.weeks, pt.value], pt })),
        endLabel: { show: c.lines.length <= 8, formatter: (p) => num(p.value[1]) } })),
    });
  }
  ls.onchange = drawLong;
  drawLong();

  // 安全
  const S = B.safety;
  const sEl = document.getElementById("sae-chart");
  const sRows = S.filter((r) => r.sae_pct != null);
  sEl.hidden = !sRows.length;
  const sl = (r) => `${r.acronym} · ${r.role === "placebo" ? "安慰剂" : (r.product_label || r.group_title)}（${r.group_title}）`;
  chart("sae-chart", {
    grid: { left: 320, right: 60, top: 30, bottom: 40 }, legend: { top: 0 },
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    xAxis: { type: "value", name: "%" },
    yAxis: { type: "category", data: sRows.map(sl), inverse: true, axisLabel: { width: 300, overflow: "truncate", color: (v, i) => (sRows[i] && sRows[i].is_own ? OWN : "#0F1115") } },
    series: [
      { name: "严重不良事件", type: "bar", data: sRows.map((r) => r.sae_pct), itemStyle: { color: "#C00000" } },
      { name: "因 AE 停药", type: "bar", data: sRows.map((r) => r.disc_pct), itemStyle: { color: "#B38A00" } },
    ],
  });
  table(document.getElementById("safety-table"), [
    { label: "试验", key: "acronym", html: (r) => src(r.url, r.acronym) },
    { label: "组别", key: "group_title", html: (r) => `${esc(r.group_title)}<br><span class="hint">${esc(r.role_label)}</span>` },
    { label: "N", key: "N", num: true, html: (r) => (r.N == null ? "未报告" : r.N) },
    { label: "严重不良事件", key: "sae_pct", num: true, html: (r) => nN(r.sae_n, null, r.sae_pct) },
    { label: "非严重 AE（≥阈值）", key: "other_pct", num: true, html: (r) => nN(r.other_n, null, r.other_pct) + (r.other_threshold != null ? `<br><span class="hint">阈值 ${num(r.other_threshold)}%</span>` : "") },
    { label: "因 AE 停药", key: "disc_pct", num: true, html: (r) => nN(r.disc_n, r.disc_N, r.disc_pct) },
    { label: "死亡", key: "death_n", num: true, html: (r) => nN(r.death_n, r.death_N, null) },
    { label: "高频事件", html: (r) => r.top_terms.map((t) => `${esc(t.term)} ${t.pct}%${t.serious ? "（严重）" : ""}`).join("；") },
  ], S, { rowClass: (r) => (r.is_own ? "own" : "") });

  // All source domains stay searchable; pagination changes the DOM, not the data set.
  const observations = B.observations || [];
  let observationPage = 0;
  optionsForObservations();
  function optionsForObservations() {
    window.U.options("#observation-domain", observations.map(r=>r.domain_label));
  }
  function drawObservations() {
    const q = document.getElementById("observation-search").value.trim().toLowerCase();
    const domain = document.getElementById("observation-domain").value;
    const all = observations.filter(r=>(!domain || r.domain_label === domain) && (!q ||
      [r.trial_id,r.acronym,...r.products,r.title,r.population,r.class_title,r.category_title].join(" ").toLowerCase().includes(q)));
    const pageSize = 100, start = observationPage * pageSize;
    const rows = all.slice(start,start+pageSize);
    document.getElementById("observation-count").textContent = `${all.length ? start+1 : 0}–${Math.min(start+pageSize,all.length)} / ${all.length} 条观测`;
    document.getElementById("observation-prev").disabled = observationPage === 0;
    document.getElementById("observation-next").disabled = start+pageSize >= all.length;
    table(document.getElementById("observation-table"),[
      {label:"药物 / 研究",html:r=>`<strong>${r.products.map(esc).join("、")}</strong><br>${esc(r.phase)} · ${esc(r.acronym)}`},
      {label:"类别",html:r=>esc(r.domain_label)},
      {label:"终点原文",html:r=>`${esc(r.title)}<br><span class="hint">${esc(r.class_title)} ${esc(r.category_title)}</span>`},
      {label:"时间 / 人群",html:r=>`${esc(r.timeframe)}<br>${esc(r.population)}`},
      {label:"数值明细",html:r=>`${r.groups.length} 组 · ${r.analyses.length} 项统计比较`},
      {label:"来源",html:r=>src(r.url,"查看原文")+" "+tag(r.status)},
    ],rows,{onRow:showObservation});
  }
  function showObservation(r) {
    const value = v=>esc(v.value_raw || num(v.value));
    window.U.drawer(`<h2>${r.products.map(esc).join("、")} · ${esc(r.acronym)}</h2>
      <p>${esc(r.domain_label)} · ${esc(r.phase)} · ${src(r.url,"来源原文")}</p><h3>${esc(r.title)}</h3>
      <p>${esc(r.timeframe)} · ${esc(r.population)} ${esc(r.class_title)} ${esc(r.category_title)}</p>
      <p>${esc(r.param_type)} · ${esc(r.unit)} · ${esc(r.dispersion_type)}</p>
      <table class="grid"><thead><tr><th>组别</th><th>角色</th><th>N</th><th>原值</th><th>离散度</th></tr></thead><tbody>
      ${r.groups.map(g=>`<tr><td>${esc(g.title)}</td><td>${esc(g.role_label)}</td><td>${num(g.n)}</td><td>${value(g)}</td><td>${g.spread != null ? num(g.spread) : g.lower != null ? num(g.lower)+", "+num(g.upper) : "—"}</td></tr>`).join("")}</tbody></table>
      ${r.analyses.length ? `<h3>来源统计比较</h3><table class="grid"><thead><tr><th>原文组别</th><th>统计量</th><th>值</th><th>CI</th><th>P</th><th>方法</th></tr></thead><tbody>${r.analyses.map(a=>`<tr><td>${a.group_ids.map(id=>esc(r.groups.find(g=>g.group_id===id)?.title || id)).join(" / ")}</td><td>${esc(a.param_type)}</td><td>${value(a)}</td><td>${a.ci_lower != null ? `${num(a.ci_pct)}% ${num(a.ci_lower)}, ${num(a.ci_upper)}` : "—"}</td><td>${esc(a.p_value)}</td><td>${esc(a.method)}</td></tr>`).join("")}</tbody></table>` : ""}`);
  }
  document.getElementById("observation-detail").addEventListener("toggle",event=>{if(event.target.open)drawObservations();});
  ["observation-search","observation-domain"].forEach(id=>document.getElementById(id).addEventListener("input",()=>{observationPage=0;drawObservations();}));
  document.getElementById("observation-prev").onclick=()=>{observationPage=Math.max(0,observationPage-1);drawObservations();};
  document.getElementById("observation-next").onclick=()=>{observationPage++;drawObservations();};

  document.getElementById("qsearch").oninput = listQuestions;
  document.getElementById("only-primary").onchange = listQuestions;
  select(qs[0] && qs[0].question_id);
})();
