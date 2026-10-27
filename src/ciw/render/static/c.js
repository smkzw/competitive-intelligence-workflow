/* C 设计先例 */
(function () {
  const { D, esc, src, table, drawer, chart, options, OWN, PAL } = window.U;
  const C = D.c, rows = C.rows;
  options("#f-phase", rows.map((r) => r.phase));
  options("#f-mask", rows.map((r) => r.masking));
  options("#f-concept", rows.flatMap((r) => r.primary_concepts));

  function filtered() {
    const q = document.getElementById("q").value.trim().toLowerCase();
    const fp = document.getElementById("f-phase").value, fm = document.getElementById("f-mask").value;
    const fc = document.getElementById("f-concept").value, china = document.getElementById("f-china").checked;
    return rows.filter((r) => (!fp || r.phase === fp) && (!fm || r.masking === fm) && (!fc || r.primary_concepts.includes(fc))
      && (!china || r.china) && (!q || [r.trial_id, r.acronym, r.title, r.sponsor, ...r.products.map((p) => p.label),
        ...r.primary.map((o) => o.title), r.eligibility,
        ...(r.registrations || []).flatMap(g => [g.trial_id, g.title, g.eligibility, ...g.primary.map(o => o.title)])]
        .join(" ").toLowerCase().includes(q)));
  }

  const ep = (list) => list.map((o) => `${esc(o.concept || o.title)}<span class="hint">${o.timeframe ? "（" + esc(o.timeframe) + "）" : ""}</span>`).join("<br>");
  const excerpts = r => (r.design_excerpts || []).map(t=>`<details><summary>${esc(t.label)} · ${t.snippets.length}处原文</summary>${t.snippets.map(s=>`<p><span class="hint">${esc(s.section)}</span><br>${window.U.annotate(s.text,s.marks,document.getElementById("q").value.trim())}</p>`).join("")}</details>`).join("");
  const cols = [
    { label: "药物 / 研究", key: "acronym", html: (r) => `<strong>${r.products.map(p=>esc(p.label)).join("、")}</strong><br>${r.is_own ? '<span class="own-tag">本品 </span>' : ""}${esc(r.phase)} · ${src(r.url, r.acronym || r.trial_id)}${r.acronym ? `<br><span class="hint">${esc(r.trial_id)}</span>` : ""}` },
    { label: "设计 / 组别", html: (r) => `${[r.allocation,r.masking,r.model].filter(Boolean).map(esc).join(" · ")}<br>${r.arm_count} 组` },
    { label: "样本量", key: "enrollment", num: true, html: (r) => r.enrollment == null ? esc(r.enrollment_text || "—") : `${r.enrollment}<br><span class="hint">${esc(r.enrollment_type)}</span>` },
    { label: "主要终点 / 时间窗", html: r => ep(r.primary) },
    { label: "背景治疗", html: r => esc(r.background_therapy.join("；")) },
    { label: "关键设计条款", html: r => (r.design_excerpts || []).length ? `<details><summary>${r.design_excerpts.length} 个主题</summary>${excerpts(r)}</details>` : "" },
    { label: "研究信息", html: r => `${esc(r.status)}<br><span class="hint">首例 ${esc(r.start || "—")}</span><details><summary>地区 / 申办方</summary><p>${esc(r.country_label || "—")}</p><p>主要完成 ${esc(r.primary_completion || "—")}</p><p>申办方：${esc(r.sponsor)}</p><p>${(r.registration_ids || [r.trial_id]).map(esc).join(" / ")}</p></details>` },
  ];
  const tEl = document.getElementById("matrix");
  function redraw() {
    const data = filtered();
    document.getElementById("count").textContent = `${data.length} / ${rows.length} 项试验`;
    table(tEl, cols, data, { rowClass: (r) => (r.is_own ? "own" : ""), onRow: show });
    drawSummary(data);
  }
  ["q", "f-phase", "f-mask", "f-concept", "f-china"].forEach((id) => document.getElementById(id).addEventListener("input", redraw));
  redraw();

  function show(r) {
    drawer(`<h2>${r.products.map(p => esc(p.label)).join(" / ")}${r.phase ? " · " + esc(r.phase) : ""}</h2>
      <p>${esc(D.indication.name_zh)} · ${esc(r.acronym || r.trial_id)}</p>
      <details><summary>研究题目原文</summary><p>${esc(r.title)}</p><p>${esc(r.official_title)}</p></details>
      <dl><dt>登记号</dt><dd>${src(r.url, r.trial_id)}（${esc(r.registry)}）</dd><dt>申办方</dt><dd>${esc(r.sponsor)}</dd>
      <dt>期别 / 状态</dt><dd>${esc(r.phase)} · ${esc(r.status)}</dd>
      <dt>设计</dt><dd>${[r.allocation, r.masking, r.model].filter(Boolean).map(esc).join(" · ")}</dd>
      <dt>样本量</dt><dd>${r.enrollment == null ? esc(r.enrollment_text || "—") : r.enrollment + "（" + esc(r.enrollment_type) + "）"}</dd>
      <dt>年龄 / 性别</dt><dd>${esc(r.min_age || "—")} 至 ${esc(r.max_age || "—")} · ${esc(r.sex || "—")}</dd>
      <dt>地区</dt><dd>${esc(r.countries.join("、"))}</dd><dt>背景治疗</dt><dd>${esc(r.background_therapy.join("；") || "—")}</dd></dl>
      <h3>组别</h3><table class="grid"><thead><tr><th>组别</th><th>角色</th><th>干预与给药</th></tr></thead><tbody>
      ${r.arms.map((a) => `<tr><td>${esc(a.label)}</td><td>${esc(a.role_label)}</td><td>${esc(a.interventions.join("；"))}<br><span class="hint">${esc(a.description)}</span></td></tr>`).join("")}</tbody></table>
      <h3>主要终点</h3><ul>${r.primary.map((o) => `<li>${esc(o.title)}<br><span class="hint">${esc(o.timeframe)}</span></li>`).join("")}</ul>
      <h3>次要终点（${r.secondary.length}）</h3><ul>${r.secondary.map((o) => `<li>${esc(o.title)}<br><span class="hint">${esc(o.timeframe)}</span></li>`).join("")}</ul>
      ${(r.design_excerpts || []).length ? `<h3>关键设计原文</h3>${excerpts(r)}` : ""}
      <h3>入选与排除标准（原文）</h3><pre>${window.U.annotate(r.eligibility || "—",r.eligibility_marks,document.getElementById("q").value.trim())}</pre>
      ${(r.registrations || []).map(g => `<details><summary>${esc(g.registry)} · ${esc(g.trial_id)}</summary>
        <p>${src(g.url, g.trial_id)} · ${esc(g.phase)} · ${esc(g.status)} · ${esc(g.sponsor)}</p>
        <p>样本量：${g.enrollment == null ? esc(g.enrollment_text || "—") : esc(g.enrollment)} ${esc(g.enrollment_type)}</p>
        <h3>组别与给药</h3><ul>${g.arms.map(a => `<li>${esc(a.label)} · ${esc(a.role_label)} · ${esc(a.interventions.join("；"))}<p>${esc(a.description)}</p></li>`).join("")}</ul>
        <h3>主要终点</h3><ul>${g.primary.map(o => `<li>${esc(o.title)} · ${esc(o.timeframe)}</li>`).join("")}</ul>
        <h3>次要终点</h3><ul>${g.secondary.map(o => `<li>${esc(o.title)} · ${esc(o.timeframe)}</li>`).join("")}</ul>
        <h3>完整入排</h3><pre>${window.U.annotate(g.eligibility,g.eligibility_marks,document.getElementById("q").value.trim())}</pre></details>`).join("")}`);
  }

  function drawSummary(data) {
  const counts = {};
  data.forEach((r) => r.primary_concepts.forEach((c) => (counts[c] = (counts[c] || 0) + 1)));
  const ck = Object.keys(counts).sort((a, b) => counts[b] - counts[a]);
  const conceptEl = document.getElementById("concept-chart");
  conceptEl.parentElement.hidden = !ck.length;
  const plotHeight = Math.min(360, Math.max(160, ck.length * 32 + 60));
  conceptEl.style.height = plotHeight + "px";
  if (ck.length) chart("concept-chart", { grid: { left: 200, right: 40, top: 20, bottom: 30 }, tooltip: {},
    xAxis: { type: "value", minInterval: 1 }, yAxis: { type: "category", data: ck, inverse: true },
    series: [{ type: "bar", data: ck.map((k) => counts[k]), itemStyle: { color: "#008F8A" }, label: { show: true, position: "right" } }] });

  // 样本量 × 首例入组
  const drawable = data.filter(r => r.start && r.enrollment != null);
  const sizeEl = document.getElementById("size-chart");
  sizeEl.parentElement.hidden = !drawable.length;
  sizeEl.style.height = (data.length < 5 ? plotHeight : 360) + "px";
  const phases = [...new Set(drawable.map((r) => r.phase))];
  if (drawable.length) chart("size-chart", { grid: { left: 60, right: 30, top: 40, bottom: 40 }, legend: { top: 0 },
    tooltip: { formatter: (p) => `${esc(p.data.r.acronym || p.data.r.trial_id)}<br>${esc(p.data.r.phase)} · N=${p.data.r.enrollment}<br>${esc(p.data.r.start)}` },
    xAxis: { type: "time", ...(drawable.length === 1 ? { splitNumber: 2, minInterval: 86400000,
      axisLabel: { formatter: "{yyyy}-{MM}-{dd}", hideOverlap: true } } : {}) }, yAxis: { type: "value", name: "样本量" },
    series: phases.map((ph, i) => ({ name: ph || "未知", type: "scatter",
      data: drawable.filter((r) => r.phase === ph).map((r) => ({ value: [r.start, r.enrollment], r,
        itemStyle: { color: r.is_own ? OWN : PAL[i % PAL.length] }, symbolSize: r.is_own ? 14 : 9 })) })) });
  }
})();
