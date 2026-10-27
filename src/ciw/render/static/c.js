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

  const ep = (list) => list.map((o) => `${esc(o.concept || o.title)}<span class="hint">${o.timeframe ? "（" + esc(o.timeframe.slice(0, 40)) + "）" : ""}</span>`).join("<br>");
  const cols = [
    { label: "试验", key: "acronym", html: (r) => `${r.is_own ? '<span class="own-tag">本品 </span>' : ""}${src(r.url, r.acronym || r.trial_id)}<br><span class="hint">${(r.registration_ids || [r.trial_id]).map(esc).join(" / ")}</span>` },
    { label: "产品", html: (r) => r.products.map((p) => (p.is_own ? `<span class="own-tag">${esc(p.label)}</span>` : esc(p.label))).join("、") },
    { label: "期别", key: "phase_rank", html: (r) => esc(r.phase) },
    { label: "状态", key: "status" },
    { label: "设计", html: (r) => [r.allocation, r.masking, r.model].filter(Boolean).map(esc).join(" · ") },
    { label: "组数", key: "arm_count", num: true },
    { label: "样本量", key: "enrollment", num: true, html: (r) => (r.enrollment == null ? esc(r.enrollment_text || "—") : `${r.enrollment}<span class="hint">${esc(r.enrollment_type)}</span>`) },
    { label: "主要终点（时间）", html: (r) => ep(r.primary) },
    { label: "背景治疗", html: (r) => esc(r.background_therapy.join("；")) },
    { label: "地区", html: (r) => `${r.country_count} 国${r.china ? "，含中国" : ""}` },
    { label: "首例入组", key: "start" },
    { label: "主要完成", key: "primary_completion" },
    { label: "申办方", key: "sponsor" },
  ];
  const tEl = document.getElementById("matrix");
  function redraw() {
    const data = filtered();
    document.getElementById("count").textContent = `${data.length} / ${rows.length} 项试验`;
    table(tEl, cols, data, { rowClass: (r) => (r.is_own ? "own" : ""), onRow: show });
  }
  ["q", "f-phase", "f-mask", "f-concept", "f-china"].forEach((id) => document.getElementById(id).addEventListener("input", redraw));
  redraw();

  function highlight(text) {
    return window.U.highlight(text, document.getElementById("q").value.trim());
  }

  function show(r) {
    drawer(`<h2>${esc(r.acronym || r.trial_id)} · ${esc(r.title)}</h2>
      <p class="hint">${esc(r.official_title)}</p>
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
      <h3>入选与排除标准（原文）</h3><pre>${highlight(r.eligibility || "未公开")}</pre>
      ${(r.registrations || []).map(g => `<details><summary>${esc(g.registry)} · ${esc(g.trial_id)}</summary>
        <p>${src(g.url, g.trial_id)} · ${esc(g.phase)} · ${esc(g.status)} · ${esc(g.sponsor)}</p>
        <p>样本量：${g.enrollment == null ? esc(g.enrollment_text || "—") : esc(g.enrollment)} ${esc(g.enrollment_type)}</p>
        <h3>组别与给药</h3><ul>${g.arms.map(a => `<li>${esc(a.label)} · ${esc(a.role_label)} · ${esc(a.interventions.join("；"))}<p>${esc(a.description)}</p></li>`).join("")}</ul>
        <h3>主要终点</h3><ul>${g.primary.map(o => `<li>${esc(o.title)} · ${esc(o.timeframe)}</li>`).join("")}</ul>
        <h3>次要终点</h3><ul>${g.secondary.map(o => `<li>${esc(o.title)} · ${esc(o.timeframe)}</li>`).join("")}</ul>
        <h3>完整入排</h3><pre>${highlight(g.eligibility)}</pre></details>`).join("")}`);
  }

  // 主要终点构成
  const counts = {};
  rows.forEach((r) => r.primary_concepts.forEach((c) => (counts[c] = (counts[c] || 0) + 1)));
  const ck = Object.keys(counts).sort((a, b) => counts[b] - counts[a]);
  chart("concept-chart", { grid: { left: 200, right: 40, top: 20, bottom: 30 }, tooltip: {},
    xAxis: { type: "value", minInterval: 1 }, yAxis: { type: "category", data: ck, inverse: true },
    series: [{ type: "bar", data: ck.map((k) => counts[k]), itemStyle: { color: "#3282b8" }, label: { show: true, position: "right" } }] });

  // 样本量 × 首例入组
  const phases = [...new Set(rows.map((r) => r.phase))];
  chart("size-chart", { grid: { left: 60, right: 30, top: 40, bottom: 40 }, legend: { top: 0 },
    tooltip: { formatter: (p) => `${esc(p.data.r.acronym || p.data.r.trial_id)}<br>${esc(p.data.r.phase)} · N=${p.data.r.enrollment}<br>${esc(p.data.r.start)}` },
    xAxis: { type: "time" }, yAxis: { type: "value", name: "样本量" },
    series: phases.map((ph, i) => ({ name: ph || "未知", type: "scatter",
      data: rows.filter((r) => r.phase === ph && r.start && r.enrollment != null).map((r) => ({ value: [r.start, r.enrollment], r,
        itemStyle: { color: r.is_own ? OWN : PAL[i % PAL.length] }, symbolSize: r.is_own ? 14 : 9 })) })) });
})();
