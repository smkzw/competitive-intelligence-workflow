/* B 临床结果 */
(function () {
  const { D, esc, num, nN, tag, src, table, chart, OWN, PAL } = window.U;
  const B = D.b;
  const observationById = new Map((B.observations || []).map(row => [row.result_id, row]));
  const qs = B.questions;
  let current = null;
  const selectedFrames = new Map();

  function listQuestions() {
    const q = document.getElementById("qsearch").value.trim().toLowerCase();
    const prim = document.getElementById("only-primary").checked;
    const items = qs.filter((x) => (!prim || x.has_primary) && (!q || window.U.matchesQuestion(x,q)));
    const ul = document.getElementById("qlist");
    ul.innerHTML = items.map((x) => `<li data-id="${esc(x.question_id)}" class="${current && current.question_id === x.question_id ? "on" : ""}">
      <div class="q">${esc(x.label)}${x.time_label ? " · " + esc(x.time_label) : ""}${!x.is_family && x.category ? ` · ${esc(x.category)}` : ""}</div>${!x.is_family && x.subgroup ? `<div class="s">亚组：${esc(x.subgroup)}</div>` : ""}
      <div class="s">${x.is_family ? "" : esc(x.measure_label) + " · "}${x.trial_ids.length} 项研究${x.frames?.length > 1 ? ` · ${x.frames.length} 个分析分面` : ""}${x.has_primary ? " · 含主要终点" : ""}</div></li>`).join("") || '<li class="empty">无匹配问题</li>';
    ul.querySelectorAll("li[data-id]").forEach((li) => {
      li.tabIndex=0;li.setAttribute("role","button");
      const activate=()=>{const id=li.dataset.id;select(id);
        [...ul.querySelectorAll("li[data-id]")].find(node=>node.dataset.id===id)?.focus();};
      li.onclick=activate;
      li.onkeydown=event=>{if(event.target===li && ["Enter"," "].includes(event.key)){
        event.preventDefault();activate();}};
    });
  }

  // 组标题与产品名相同（只差大小写）时不重复显示
  const sameName = (a, b) => (a || "").toLowerCase().replace(/[^a-z0-9一-鿿]/g, "") === (b || "").toLowerCase().replace(/[^a-z0-9一-鿿]/g, "");
  const groupSuffix = (label, group) => (label && group && !sameName(label, group) && !label.toLowerCase().includes(group.toLowerCase()) ? `（${group}）` : "");
  const rowLabel = (r) => `${r.role === "placebo" ? "安慰剂" : (r.product_label || r.group_title)}${r.role !== "placebo" ? groupSuffix(r.product_label, r.group_title) : ""}${r.phase ? " · " + r.phase + "期" : ""} · ${r.acronym}${r.stratum_label ? " · " + r.stratum_label : ""}`;
  const compactRowLabel = r => [r.acronym, r.group_title || r.product_label].filter(Boolean).join(" · ");
  const pointUnit = (point, chart) => observationById.get(point.result_id)?.unit ?? point.unit ?? chart.unit;


  const studyLink = row => row.source_records?.length > 1
    ? row.source_records.map(s => src(s.url, s.acronym)).join(" · ") : src(row.url, row.acronym);
  const studyMeta = row => `${row.phase ? esc(row.phase) + "期 · " : ""}${studyLink(row)}`;
  function showResult(row) {
    const observation = observationById.get(row.result_id);
    if(observation) showObservation(observation);
  }

  function drawFamilyOverview() {
    document.getElementById("family-overview").hidden = !current.is_family;
    if(!current.is_family) return;
    const all = [];
    for(const frame of current.frames) {
      const common = {frame_id:frame.frame_id,time_label:frame.time_label,population:frame.population};
      for(const r of frame.rows) all.push({...common,...r,title:r.group_title,metric:frame.measure_label});
      for(const c of frame.comparisons) all.push({...common,...c,title:`${c.exp_group} / ${c.ctrl_group}`,
        metric:c.param_type,n_label:`${num(c.n_exp)} / ${num(c.n_ctrl)}`,lower:c.ci_lower,upper:c.ci_upper});
      for(const s of frame.source_statistics || []) all.push({...common,...s,title:s.group_labels.join(" / "),
        metric:s.param_type,lower:s.ci_lower,upper:s.ci_upper});
    }
    document.getElementById("family-count").textContent = `全研究对照表 · ${current.trial_ids.length} 项研究 · ${all.length} 条记录`;
    table(document.getElementById("family-table"), [
      {label:"药物 / 研究",html:r=>`<strong>${esc(r.product_label || r.title)}</strong>${r.product_label && !sameName(r.product_label,r.title) ? "<br>" + esc(r.title) : ""}<br>${r.phase ? esc(r.phase) + "期 · " : ""}${studyLink(r)}`},
      {label:"时间",key:"time_label"},{label:"统计量",key:"metric"},
      {label:"N（组 / 对照）",key:"n",num:true,html:r=>r.n_label || num(r.n)},
      {label:"原值",num:true,html:r=>esc(r.value_raw || num(r.value))},
      {label:"离散度 / 区间",html:r=>r.spread != null ? num(r.spread) : r.lower != null ? `${num(r.lower)}, ${num(r.upper)}` : "—"},
      {label:"单位",key:"unit"},
      {label:"依据",html:r=>tag(r.kind === "computed" ? "computed" : r.status || "registry")},
      {label:"分析人群",html:r=>r.population ? `<details><summary>${esc(r.stratum_label || "查看人群")}</summary>${esc(r.population)}</details>` : "—"},
      {label:"图表",html:r=>`<button type="button" class="detail-button" data-frame-id="${esc(r.frame_id)}">看图</button>`}
    ], all, {onRow:showResult});
  }
  document.getElementById("family-table").addEventListener("click",event=>{
    const button=event.target.closest("button[data-frame-id]");
    if(button) select(current.question_id,button.dataset.frameId);
  });

  function drawForest(id, list, ref, log, sourceOnly = false) {
    const cl = list.map((c) => sourceOnly ? `${c.group_labels.join("、")} · ${c.acronym}` : `${c.product_label}${groupSuffix(c.product_label, c.exp_group)}${c.h2h ? " vs " + c.ctrl_group : ""} · ${c.acronym}`);
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
    const frames = current.frames?.length ? current.frames : [current];
    const query = document.getElementById("qsearch").value.trim();
    const matching = current.is_family && query ? frames.filter(f=>window.U.matchesQuestion({
      ...f,label:current.label,frames:f.source_contexts || [f]},query)) : frames;
    const frame = (frameId && frames.find(f=>f.frame_id === frameId)) ||
      matching.find(f => f.frame_id === selectedFrames.get(id)) || matching[0] || frames[0];
    selectedFrames.set(id, frame.frame_id);
    const picker = document.getElementById("frame-select");
    document.getElementById("frame-label").hidden = frames.length < 2;
    picker.innerHTML = frames.map((f, i) => `<option value="${esc(f.frame_id || "")}">${i + 1}${f.time_label ? " · " + esc(f.time_label) : ""}${f.category ? " · " + esc(f.category) : ""}${f.subgroup ? " · " + esc(f.subgroup) : ""}${f.measure_label ? " · " + esc(f.measure_label) : ""} · ${f.trial_ids.length} 项研究${f.context_label ? " · " + esc(f.context_label) : ""}${f.rows?.length ? " · " + [...new Set(f.rows.map(r => r.product_label).filter(Boolean))].slice(0, 2).map(esc).join("、") : ""}</option>`).join("");
    picker.value = frame.frame_id || "";
    picker.onchange = () => select(id, picker.value);
    const point = frame.time_label || current.time_label, units = frame.units || current.units;
    const category = current.is_family ? frame.category : current.category;
    document.getElementById("q-title").textContent = `${current.label}${point ? " · " + point : ""}${category ? " · " + category : ""}`;
    document.getElementById("q-sub").textContent = `${frame.measure_label || current.measure_label}${units.length ? " · 单位：" + units.join(" / ") : ""}`;
    document.getElementById("frame-context-text").textContent = (frame.source_contexts || [frame])
      .map(f=>[f.title,f.description,f.population].filter(Boolean).join("\n\n")).join("\n\n");
    document.getElementById("frame-context").open = false;
    drawFamilyOverview();
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
    const questionConcepts = new Set(current.member_concept_ids || [current.concept_id]);
    const pairedTrend = B.longitudinal.some(c => questionConcepts.has(c.concept_id));
    document.getElementById("arm-values").hidden = !rows.length;
    document.getElementById("arm-details").hidden = !rows.length;
    chart("value-chart", {
      grid: { left: pairedTrend ? 200 : 300, right: 60, top: 20, bottom: 40 },
      tooltip: { formatter: (p) => { const r = rows[p.dataIndex]; return `<b>${esc(rowLabel(r))}</b><br>${num(r.value)} ${esc(r.unit)}${r.n != null ? `<br>N=${r.n}` : ""}${r.spread != null ? `<br>${esc(r.dispersion_type)} ${num(r.spread)}` : ""}${r.lower != null ? `<br>${esc(r.dispersion_type)} ${num(r.lower)}, ${num(r.upper)}` : ""}`; } },
      xAxis: { type: "value", scale: false },
      yAxis: { type: "category", data: rows.map(rowLabel), inverse: true, axisLabel: { width: pairedTrend ? 180 : 280, lineHeight:20, overflow: "break", formatter: (v, i) => pairedTrend ? compactRowLabel(rows[i]).replace(" · ", "\n") : compactRowLabel(rows[i]), color: (v, i) => (rows[i] && rows[i].is_own ? OWN : "#0F1115") } },
      series: [{ type: "bar", barWidth: 12, data: rows.map((r) => ({ value: r.value, itemStyle: { color: r.is_own ? OWN : r.role === "placebo" ? "#6E7B8C" : "#008F8A" } })),
        label: { show: true, position: "right", formatter: (p) => num(p.value) } }],
    });

    table(document.getElementById("comp-table"), [
      { label: "药物 / 研究", key: "acronym", html: (c) => `<strong>${esc(c.product_label || c.exp_group)}</strong><br>${studyMeta(c)}` },
      { label: "产品（试验组）", key: "product_label", html: (c) => `${c.is_own ? '<span class="own-tag">本品 </span>' : ""}${esc(c.product_label)}<br><span class="hint">${esc(c.exp_group)}${c.n_exp != null ? `，N=${c.n_exp}` : ""}</span>` },
      { label: "对照", html: (c) => `${esc(c.ctrl_role_label)}<br><span class="hint">${esc(c.ctrl_group)}${c.n_ctrl != null ? `，N=${c.n_ctrl}` : ""}</span>` },
      { label: "统计量", key: "param_type" },
      { label: "差值", key: "value", num: true, html: (c) => num(c.value) },
      { label: "置信区间", num: true, html: (c) => (c.ci_lower != null ? `${c.ci_pct ? c.ci_pct + "% " : ""}${num(c.ci_lower)}, ${num(c.ci_upper)}` : "—") },
      { label: "P 值", key: "p_value" },
      { label: "方法", key: "method" },
      { label: "依据", html: (c) => `${c.source_kind === "publication" ? src(c.url, "论文") + (c.group_basis === "论文分组" ? " · 论文分组 " : " ") : ""}` + tag(c.kind === "computed" ? "computed" : c.status || "registry") + (c.note ? `<br><span class="hint">${esc(c.note)}</span>` : "") },
    ], comps, { rowClass: (c) => (c.is_own ? "own" : ""), onRow:showResult });

    table(document.getElementById("row-table"), [
      { label: "药物 / 研究", key: "acronym", html: (r) => `<strong>${esc(r.product_label || r.group_title)}</strong><br>${studyMeta(r)}<br><span class="hint">${esc(r.outcome_type)}</span>` },
      { label: "组别", key: "group_title", html: (r) => `${esc(r.group_title)}<br><span class="hint">${esc(r.role_label)}</span>` },
      { label: "N", key: "n", num: true, html: (r) => num(r.n) },
      { label: "数值", key: "value", num: true, html: (r) => num(r.value) },
      { label: "离散度", num: true, html: (r) => (r.spread != null ? `${esc(r.dispersion_type)} ${num(r.spread)}` : r.lower != null ? `${esc(r.dispersion_type)} ${num(r.lower)}, ${num(r.upper)}` : "—") },
      { label: "单位", key: "unit" },
      { label: "终点原文", html: (r) => `<details><summary>查看原文</summary>${esc(r.title)}${r.class_title ? `<br>${esc(r.class_title)}` : ""}<br>${esc(r.timeframe)}</details>` },
      { label: "分析人群", html: (r) => r.population ? `<details><summary>${esc(r.stratum_label || "查看人群")}</summary>${esc(r.population)}</details>` : "—" },
      { label: "依据", html: (r) => `${r.source_kind === "publication" ? src(r.url, "论文") + " " : ""}${tag(r.status || "registry")}` },
    ], rows, { rowClass: (r) => (r.is_own ? "own" : ""), onRow:showResult });
    selectLongitudinal();
  }

  // 历时
  let L = [];
  const selectedLong = new Map();
  const ls = document.getElementById("long-select");
  function selectLongitudinal() {
    const ids = new Set(current.member_concept_ids || [current.concept_id]);
    L = B.longitudinal.filter(c => ids.has(c.concept_id));
    document.getElementById("longitudinal-card").hidden = !L.length;
    document.getElementById("long-point-details").hidden = !L.length;
    ls.innerHTML = L.map((c, i) => `<option value="${i}">${esc(current.is_family && !c.axis_id ? current.label : c.label)} · ${esc(c.measure_label)} · ${esc(c.unit)}（${c.lines.length} 条曲线）</option>`).join("");
    ls.value = String(Math.max(0,L.findIndex(c=>c.chart_id === selectedLong.get(current.question_id))));
    drawLong();
  }
  function drawLong() {
    const c = L[+ls.value || 0];
    if (!c) return;
    selectedLong.set(current.question_id,c.chart_id);
    chart("long-chart", {
      tooltip: { trigger: "item", formatter: (p) => { const pt = p.data.pt; return `<b>${esc(p.seriesName)}</b><br>${esc(pt.label)}：${num(pt.value)} ${esc(pointUnit(pt, c))}${pt.n != null ? `（N=${pt.n}）` : ""}`; } },
      legend: { type: c.lines.length <= 4 ? "plain" : "scroll", top: 0, left:0, right:0, formatter: name => {
        const line = c.lines.find(line => rowLabel(line) === name);
        return line ? compactRowLabel(line).replace(" · ", "\n") : name;
      } },
      grid: { left: 60, right: 30, top: 70, bottom: 50 },
      xAxis: { type: "value", name: "周", nameLocation: "end", min: 0 },
      yAxis: { type: "value", scale: true },
      series: c.lines.map((l, i) => ({ name: rowLabel(l), type: "line", connectNulls: false,
        symbolSize: 6, lineStyle: { width: l.is_own ? 3 : 1.6, type: l.role === "placebo" ? "dashed" : "solid" },
        itemStyle: { color: l.is_own ? OWN : l.role === "placebo" ? "#6E7B8C" : PAL[i % PAL.length] },
        data: l.points.map((pt) => ({ value: [pt.weeks, pt.value], pt })),
        endLabel: { show: c.lines.length <= 8, formatter: (p) => num(p.value[1]) } })),
    });
    table(document.getElementById("long-table"), [
      {label:"药物 / 研究",html:r=>`<strong>${esc(r.product_label || r.group_title)}</strong><br>${studyMeta(r)}`},
      {label:"组别",key:"group_title"},
      {label:"时间",key:"label"}, {label:"N",key:"n",num:true,html:r=>num(r.n)},
      {label:"数值",num:true,html:r=>num(r.value)}, {label:"单位",key:"unit"},
      {label:"离散度 / 区间",html:r=>r.lower == null ? "—" : `${num(r.lower)}, ${num(r.upper)}`}
    ], c.lines.flatMap(line=>line.points.map(pt=>({...line,...pt,unit:pointUnit(pt,c)}))), {onRow:showResult});
  }
  ls.onchange = drawLong;

  // 安全
  const S = B.safety;
  const sEl = document.getElementById("sae-chart");
  const sRows = S.filter((r) => r.sae_pct != null && (!r.condition_scope || r.condition_scope.status === "target"));
  sEl.hidden = !sRows.length;
  const sl = (r) => `${r.role === "placebo" ? "安慰剂" : (r.product_label || r.group_title)}${groupSuffix(r.product_label,r.group_title)} · ${r.acronym}`;
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
    { label: "药物 / 研究", key: "acronym", html: (r) => `<strong>${esc(r.product_label || r.group_title)}</strong><br>${studyMeta(r)}` },
    { label: "组别", key: "group_title", html: (r) => `${esc(r.group_title)}<br><span class="hint">${esc(r.role_label)}</span>${r.condition_scope?.multiple_conditions ? '<br>多疾病登记' : ""}` },
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
      window.U.matchesSearch([r.trial_id,r.acronym,...r.products,...r.groups.map(g=>g.title),r.title,
        r.timeframe,r.population,r.class_title,r.category_title].join(" "),q)));
    const pageSize = 100, start = observationPage * pageSize;
    const rows = all.slice(start,start+pageSize);
    document.getElementById("observation-count").textContent = `${all.length ? start+1 : 0}–${Math.min(start+pageSize,all.length)} / ${all.length} 条观测`;
    document.getElementById("observation-prev").disabled = observationPage === 0;
    document.getElementById("observation-next").disabled = start+pageSize >= all.length;
    table(document.getElementById("observation-table"),[
      {label:"药物 / 研究",html:r=>`<strong>${r.products.map(esc).join("、")}</strong><br>${esc(r.phase)} · ${esc(r.acronym)}`},
      {label:"类别",html:r=>esc(r.domain_label)},
      {label:"终点原文",html:r=>`${esc(r.title)}<br><span class="hint">${esc(r.class_title)} ${esc(r.category_title)}</span>`},
      {label:"时间 / 人群",html:r=>`${esc(r.time_label || r.timeframe)}<br>${esc(r.population)}${r.condition_scope?.multiple_conditions ? '<br>多疾病登记' : ""}`},
      {label:"数值明细",html:r=>`${r.groups.length} 组 · ${r.analyses.length} 项统计比较`},
      {label:"来源",html:r=>src(r.url,"查看原文")+" "+tag(r.status)},
    ],rows,{onRow:showObservation});
  }
  function showObservation(r) {
    const value = v=>esc(v.value_raw || num(v.value));
    window.U.drawer(`<h2>${r.products.map(esc).join("、")} · ${esc(r.acronym)}</h2>
      <p>${esc(r.domain_label)} · ${esc(r.phase)} · ${src(r.url,"来源原文")}</p><h3>${esc(r.title)}</h3>
      <p>${esc(r.time_label || r.timeframe)} · ${esc(r.population)} ${esc(r.class_title)} ${esc(r.category_title)}</p>
      ${r.time_label ? `<details><summary>来源时间范围</summary>${esc(r.timeframe)}</details>` : ""}
      <p>${esc(r.param_type)} · ${esc(r.unit)} · ${esc(r.dispersion_type)}</p>
      <table class="grid"><thead><tr><th>组别</th><th>角色</th><th>N</th><th>原值</th><th>离散度</th></tr></thead><tbody>
      ${r.groups.map(g=>`<tr><td>${esc(g.title)}</td><td>${esc(g.role_label)}</td><td>${num(g.n)}</td><td>${value(g)}</td><td>${g.spread != null ? num(g.spread) : g.lower != null ? num(g.lower)+", "+num(g.upper) : "—"}</td></tr>`).join("")}</tbody></table>
      ${r.analyses.length ? `<h3>来源统计比较</h3><table class="grid"><thead><tr><th>原文组别</th><th>统计量</th><th>值</th><th>CI</th><th>P</th><th>方法</th></tr></thead><tbody>${r.analyses.map(a=>`<tr><td>${a.group_ids.map(id=>esc(r.groups.find(g=>g.group_id===id)?.title || id)).join(" / ")}</td><td>${esc(a.param_type)}</td><td>${value(a)}</td><td>${a.ci_lower != null ? `${num(a.ci_pct)}% ${num(a.ci_lower)}, ${num(a.ci_upper)}` : "—"}</td><td>${esc(a.p_value)}</td><td>${esc(a.method)}</td></tr>`).join("")}</tbody></table>` : ""}`);
  }
  document.getElementById("observation-detail").addEventListener("toggle",event=>{if(event.target.open)drawObservations();});
  ["observation-search","observation-domain"].forEach(id=>document.getElementById(id).addEventListener("input",()=>{observationPage=0;drawObservations();}));
  document.getElementById("observation-prev").onclick=()=>{observationPage=Math.max(0,observationPage-1);drawObservations();};
  document.getElementById("observation-next").onclick=()=>{observationPage++;drawObservations();};

  document.getElementById("qsearch").oninput = () => {
    const query=document.getElementById("qsearch").value;
    if(current?.is_family && window.U.matchesQuestion(current,query)) select(current.question_id);
    else listQuestions();
  };
  document.getElementById("only-primary").onchange = listQuestions;
  select(qs[0] && qs[0].question_id);
})();
