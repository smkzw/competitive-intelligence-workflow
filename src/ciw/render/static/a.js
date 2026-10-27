/* A 竞品全景 */
(function () {
  const { D, esc, tag, src, table, drawer, chart, options, OWN } = window.U;
  const A = D.a, T = D.trials;
  const phaseName = (r) => (A.phase_columns.find((c) => c.rank === r) || {}).label || "未知";
  const prods = A.products;

  // KPI
  const n3 = prods.filter((p) => p.global_rank >= 4).length;
  const c3 = prods.filter((p) => p.china_rank >= 4).length;
  const own = prods.find((p) => p.is_own);
  document.getElementById("kpis").innerHTML = [
    [prods.length, "纳入竞品宇宙的产品"],
    [n3, "全球已到 III 期及以上"],
    [c3, "中国已到 III 期及以上"],
    [D.stats.trials_core, `核心试验（其中 ${D.stats.trials_core_with_results} 项已公布登记结果）`],
    [own ? `${esc(own.china_phase)}` : "—", own ? `本品 ${esc(own.label)} 本适应症中国最高阶段${own.other_indications && own.other_indications.length ? `（其他适应症登记 ${own.other_indications.length} 项，点产品表查看）` : ""}` : "未配置本品"],
  ].map(([v, l]) => `<div class="kpi"><b>${v}</b><span>${l}</span></div>`).join("");

  // 阶段矩阵
  const ys = [...prods].reverse();
  const el = document.getElementById("phase-chart");
  el.style.height = Math.max(360, ys.length * 24 + 80) + "px";
  chart("phase-chart", {
    grid: { left: 260, right: 40, top: 40, bottom: 20 },
    tooltip: { trigger: "item", formatter: (p) => {
      const r = ys[p.dataIndex];
      return `<b>${esc(r.label)}</b><br>靶点：${esc(r.target || "待核")}<br>全球：${esc(r.global_phase)}　中国：${esc(r.china_phase)}<br>试验 ${r.trial_count} 项（进行中 ${r.active_trials}）`;
    } },
    xAxis: { type: "value", position: "top", min: 0, max: 5.5, interval: 1, axisLabel: { formatter: (v) => (v >= 1 && v <= 5 ? phaseName(v) : "") }, splitLine: { lineStyle: { type: "dashed" } } },
    yAxis: { type: "category", data: ys.map((r) => r.label + (r.target ? `  ·  ${r.target}` : "")),
      axisLabel: { color: (v, i) => (ys[i] && ys[i].is_own ? OWN : "#0F1115"), fontWeight: 400, width: 240, overflow: "truncate" } },
    series: [
      { name: "全球最高阶段", type: "bar", barWidth: 8, data: ys.map((r) => ({ value: r.global_rank, itemStyle: { color: r.is_own ? OWN : "#008F8A" } })) },
      { name: "中国最高阶段", type: "scatter", symbol: "diamond", symbolSize: 13, data: ys.map((r) => (r.china_rank ? r.china_rank : null)), itemStyle: { color: "#7B5CC7" } },
    ],
  });

  // 产品表
  const tableEl = document.getElementById("products");
  options("#f-target", prods.map((p) => p.target));
  options("#f-phase", prods.map((p) => p.global_phase));
  const trialLinks = (ids) => ids.map((id) => { const t = T[id] || {}; return src(t.url, t.acronym || id); }).join("、");
  const cols = [
    { label: "产品", key: "label", html: (r) => `${r.is_own ? '<span class="own-tag">本品 </span>' : ""}${esc(r.label)}${r.codes.length ? `<br><span class="hint">${esc(r.codes.join(" / "))}</span>` : ""}` },
    { label: "靶点", key: "target", html: (r) => esc(r.target || "") || '<span class="hint">待核</span>' },
    { label: "分子类型", key: "modality" },
    { label: "企业", key: "company" },
    { label: "全球最高阶段", key: "global_rank", html: (r) => esc(r.global_phase) },
    { label: "中国最高阶段", key: "china_rank", html: (r) => esc(r.china_phase) },
    { label: "试验数", key: "trial_count", num: true, html: (r) => `${r.trial_count}${r.active_trials ? `<span class="hint">（进行中 ${r.active_trials}）</span>` : ""}` },
    { label: "上市许可 / 获批", html: (r) => !(r.approvals || []).length ? "" :
      `<details><summary>查看许可记录</summary>${r.approvals.map(x => {
        const s = (D.sources || {})[x.source_id] || {};
        return `<p>${esc(x.region)} ${src(s.url, x.scope_label)} ${esc(x.date || "")} ${tag(x.status)}<br>${esc(x.detail || "")}</p>`;
      }).join("")}</details>` },
    { label: "II 期及以上关键试验", html: (r) => trialLinks(r.key_trials) },
    { label: "属性来源", html: (r) => tag(r.attribute_status) },
  ];
  function filtered() {
    const q = document.getElementById("q").value.trim().toLowerCase();
    const ft = document.getElementById("f-target").value, fp = document.getElementById("f-phase").value;
    const fc = document.getElementById("f-china").checked;
    return prods.filter((p) => (!q || [p.label, p.target, p.company, ...p.codes].join(" ").toLowerCase().includes(q))
      && (!ft || p.target === ft) && (!fp || p.global_phase === fp) && (!fc || p.china_rank > 0));
  }
  const redraw = () => table(tableEl, cols, filtered(), { rowClass: (r) => (r.is_own ? "own" : ""), onRow: showProduct });
  ["q", "f-target", "f-phase", "f-china"].forEach((id) => document.getElementById(id).addEventListener("input", redraw));
  redraw();

  function showProduct(p) {
    const trials = A.timeline.filter((t) => t.product_id === p.product_id);
    drawer(`<h2>${esc(p.label)}</h2><dl>
      <dt>靶点</dt><dd>${esc(p.target || "待核")}</dd><dt>分子类型</dt><dd>${esc(p.modality || "—")}</dd>
      <dt>给药途径</dt><dd>${esc(p.route || "—")}</dd><dt>企业</dt><dd>${esc(p.company || "—")}</dd>
      <dt>全球最高阶段</dt><dd>${esc(p.global_phase)}</dd><dt>中国最高阶段</dt><dd>${esc(p.china_phase)}</dd>
      <dt>试验状态</dt><dd>${Object.entries(p.status_counts).map(([k, v]) => `${esc(k)} ${v}`).join("　") || "本适应症暂无登记"}</dd></dl>
      ${(p.other_indications || []).length ? `<h3>本品其他适应症登记（CDE，${p.other_indications.length} 项）</h3><table class="grid"><thead><tr><th>登记号</th><th>适应症</th><th>状态</th><th>题目</th></tr></thead><tbody>${p.other_indications.map((o) => `<tr><td>${src(o.url, o.trial_id)}</td><td>${esc(o.indication)}</td><td>${esc(o.status)}</td><td>${esc(o.title)}</td></tr>`).join("")}</tbody></table>` : ""}
      <h3>II 期及以上试验</h3><table class="grid"><thead><tr><th>试验</th><th>期别</th><th>状态</th><th>首例入组</th><th>主要完成</th><th>中国</th></tr></thead><tbody>
      ${trials.map((t) => `<tr><td>${src((T[t.trial_id] || {}).url, t.acronym || t.trial_id)}</td><td>${esc(t.phase)}</td><td>${esc(t.status)}</td><td>${esc(t.start || "")}</td><td>${esc(t.primary_completion || "")}</td><td>${t.china ? "是" : ""}</td></tr>`).join("") || '<tr><td colspan="6" class="empty">无</td></tr>'}
      </tbody></table>`);
  }

  // 里程碑事件
  const EV_ZH = { approval: "获批", filing: "上市申请", topline: "顶线结果", phase_start: "关键试验启动", licensing: "授权许可", other: "其他" };
  const evs = D.events || [];
  if (evs.length) {
    document.getElementById("events-card").hidden = false;
    const label = (id) => { const p = prods.find((x) => x.product_id === id); return p ? p.label : ""; };
    table(document.getElementById("events"), [
      { label: "日期", key: "date" },
      { label: "产品", html: (e) => esc(label(e.product_id) || e.product_mention) },
      { label: "事件", html: (e) => esc(EV_ZH[e.event_type] || e.event_type) },
      { label: "地区", key: "region" },
      { label: "内容", key: "detail" },
      { label: "原文", html: (e) => `<details><summary>查看原文</summary><pre>${esc(e.quote)}</pre></details>` },
      { label: "核对", html: (e) => tag(e.status) },
      { label: "来源", html: (e) => { const s = (D.sources || {})[e.source_id] || {}; return src(s.url, s.title || "来源"); } },
    ], [...evs].sort((x, y) => ((y.date || "") > (x.date || "") ? 1 : -1)));
  }

  // 时间线
  const tl = A.timeline.filter((t) => t.start).sort((a, b) => (a.start < b.start ? -1 : 1));
  const label = (t) => { const p = prods.find((x) => x.product_id === t.product_id); return `${p ? p.label : t.product_id} · ${t.acronym || t.trial_id}`; };
  const isOwn = (t) => t.product_id === D.own_product_id;
  const tEl = document.getElementById("timeline-chart");
  tEl.style.height = Math.max(360, tl.length * 18 + 80) + "px";
  const day = (s) => +new Date(s.length === 7 ? s + "-01" : s);
  chart("timeline-chart", {
    grid: { left: 300, right: 40, top: 20, bottom: 40 },
    tooltip: { formatter: (p) => { const t = tl[p.value[0]]; return `${esc(label(t))}<br>${esc(t.phase)} · ${esc(t.status)}<br>${esc(t.start)} → ${esc(t.primary_completion || "未登记")}`; } },
    xAxis: { type: "time" },
    yAxis: { type: "category", data: tl.map(label), inverse: true, axisLabel: { width: 280, overflow: "truncate", color: (v, i) => (tl[i] && isOwn(tl[i]) ? OWN : "#0F1115") } },
    series: [{ type: "custom", renderItem: (params, api) => {
      const i = api.value(0), s = api.coord([api.value(1), i]), e = api.coord([api.value(2), i]);
      const h = api.size([0, 1])[1] * 0.55, t = tl[i];
      return { type: "rect", shape: { x: s[0], y: s[1] - h / 2, width: Math.max(e[0] - s[0], 3), height: h },
        style: { fill: isOwn(t) ? OWN : t.phase.includes("III") ? "#008F8A" : "#6E7B8C", opacity: t.status.includes("终止") || t.status.includes("撤回") ? 0.35 : 1 } };
    }, encode: { x: [1, 2], y: 0 }, data: tl.map((t, i) => [i, day(t.start), day(t.primary_completion || t.start)]) }],
  });

  // 未归类干预
  const u = document.getElementById("unclassified");
  u.querySelector(".count").textContent = `${A.unclassified.length} 项（企业申办的药物干预，尚未纳入产品配置，需补充或排除）`;
  const ut = document.createElement("table"); ut.className = "grid";
  u.querySelector(".table-wrap").appendChild(ut);
  table(ut, [
    { label: "干预名称（原文）", key: "name" },
    { label: "申办方", html: (r) => esc(r.sponsors.join("；")) },
    { label: "期别", html: (r) => esc([...new Set(r.phases)].join("、")) },
    { label: "试验", html: (r) => r.trials.map((id) => src((T[id] || {}).url, id)).join("、") },
  ], A.unclassified);
  if ((A.non_innovative || []).length) {
    const h = document.createElement("h3"); h.textContent = `生物类似药与非创新产品（${A.non_innovative.length}，不计入竞品宇宙）`;
    const nt = document.createElement("table"); nt.className = "grid";
    u.querySelector(".table-wrap").append(h, nt);
    table(nt, [{ label: "产品", key: "label" }, { label: "说明", key: "modality" }, { label: "企业", key: "company" },
      { label: "全球最高阶段", key: "global_phase" }, { label: "中国最高阶段", key: "china_phase" }], A.non_innovative);
  }
})();
