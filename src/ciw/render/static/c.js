/* C 设计先例 */
(function () {
  const { D, esc, src, table, drawer, chart, options, OWN, PAL } = window.U;
  const C = D.c, rows = C.rows;
  options("#f-phase", rows.map((r) => r.phase));
  options("#f-mask", rows.map((r) => r.masking));
  const primaryCategories = r => r.primary_concepts.length ? r.primary_concepts :
    [r.primary.length ? "其他原文终点" : "未登记主要终点"];
  options("#f-concept", rows.flatMap(primaryCategories));

  function filtered() {
    const q = document.getElementById("q").value.trim().toLowerCase();
    const fp = document.getElementById("f-phase").value, fm = document.getElementById("f-mask").value;
    const fc = document.getElementById("f-concept").value, china = document.getElementById("f-china").checked;
    return rows.filter((r) => (!fp || r.phase === fp) && (!fm || r.masking === fm) && (!fc || primaryCategories(r).includes(fc))
      && (!china || r.china) && (!q || [r.trial_id, r.acronym, r.title, r.sponsor, ...r.products.map((p) => p.label),
        ...r.primary.flatMap((o) => [o.title,o.description]), r.eligibility, r.search_text || "", ...(r.conditions || []),
        ...(r.registrations || []).flatMap(g => [g.trial_id, g.title, g.eligibility, ...g.primary.map(o => o.title)])]
        .join(" ").toLowerCase().includes(q)));
  }

  const endpointDetails = o => `${o.description ? `<details><summary>完整终点定义</summary><p>${window.U.annotate(o.description,o.description_marks,document.getElementById("q").value.trim())}</p></details>` : ""}`;
  const ep = list => list.map(o => `${esc(o.summary || o.concept || o.title)}<span class="hint">${o.timeframe ? (o.timeframe.length > 48 ? `<details><summary>时间窗原文</summary><p>${esc(o.timeframe)}</p></details>` : "（" + esc(o.timeframe) + "）") : ""}</span>${endpointDetails(o)}`).join("<br>");
  const regimens = r => `<details><summary>${r.arms.length}组给药方案</summary>${r.arms.map(a=>`<p><strong>${esc(a.label)}</strong><br>${esc(a.interventions.join("；"))}<br>${esc(a.description)}</p>`).join("")}${(r.study_narrative || []).map(n=>`<details><summary>${esc(n.label)}</summary><p>${esc(n.text)}</p></details>`).join("")}</details>`;
  const annotation = (text, marks) => window.U.annotate(text, marks, document.getElementById("q").value.trim());
  const originalParagraphs = s => {
    const parts = [[s.cohort_quote,[]],[s.condition,s.condition_marks],[s.text,s.marks],
      [s.timeframe,[]],[s.context,s.context_marks]].filter(([text])=>text);
    return parts.filter(([text],i)=>!parts.some(([other],j)=>i!==j&&other.includes(text)&&
      (other.length>text.length||j<i))).map(([text,marks])=>`<p>${annotation(text,marks)}</p>`).join("");
  };
  const clause = s => {
    const reading = s.reading;
    const role = s.criterion_role === "inclusion" ? "入选" : s.criterion_role === "exclusion" ? "排除" : "";
    const cohort = reading ? reading.cohort_zh : s.cohort_quote;
    const condition = reading ? reading.condition_zh : s.condition;
    const timeframe = reading ? reading.timeframe_zh : s.timeframe;
    const original = reading ? `<details class="clause-original"><summary>原文与上下文</summary>
      ${originalParagraphs(s)}</details>` :
      (s.context && s.context !== s.text ? `<details><summary>上下文原文</summary><p>${annotation(s.context,s.context_marks)}</p></details>` : "");
    return `<div class="design-clause">${cohort ? `<p class="clause-condition">${esc(cohort)}</p>` : ""}
      ${condition ? `<p class="clause-condition">${annotation(condition,reading ? reading.condition_marks : s.condition_marks)}</p>` : ""}
      <p class="clause-point">${role ? `<span class="clause-role">${role}</span>` : ""}${annotation(reading ? reading.text_zh : s.text,reading ? reading.marks : s.marks)}</p>
      ${timeframe ? `<p class="hint">${esc(timeframe)}</p>` : ""}${original}</div>`;
  };
  const excerpts = r => (r.design_excerpts || []).map(t=>`<details><summary>${esc(t.label)} · ${t.snippets.length}处原文</summary>${t.snippets.map(clause).join("")}</details>`).join("");
  const cols = [
    { label: "药物 / 研究", key: "acronym", html: (r) => `<strong>${r.products.map(p=>esc(p.label)).join("、")}</strong><br>${r.is_own ? '<span class="own-tag">本品 </span>' : ""}${esc(r.phase)} · ${src(r.url, r.acronym || r.trial_id)}${r.population_extent ? '<br><span class="hint">多疾病登记</span>' : ""} <button class="detail-button" data-design-id="${esc(r.trial_id)}" type="button">查看设计</button>` },
    { label: "设计 / 组别", html: (r) => `${[r.allocation,r.masking,r.model].filter(Boolean).map(esc).join(" · ")}<br>${r.arm_count} 组` },
    { label: "样本量", key: "enrollment", num: true, html: (r) => r.enrollment == null ? esc(r.enrollment_text || "—") : `${r.enrollment}<br><span class="hint">${esc(r.population_extent || "")} ${esc(r.enrollment_type)}</span>` },
    { label: "主要终点 / 时间窗", html: r => ep(r.primary) },
    { label: "给药与背景方案", html: r => `${esc(r.background_therapy.join("；"))}${regimens(r)}` },
    { label: "关键设计条款", html: r => (r.design_excerpts || []).length ? `<details><summary>${r.design_excerpts.length} 个主题</summary>${excerpts(r)}</details>` : "" },
    { label: "研究信息", html: r => `${esc(r.status)}<br><span class="hint">首例 ${esc(r.start || "—")}</span><details><summary>地区 / 申办方</summary><p>${esc(r.country_label || "—")}</p><p>主要完成 ${esc(r.primary_completion || "—")}</p><p>申办方：${esc(r.sponsor)}</p><p>${(r.registration_ids || [r.trial_id]).map(esc).join(" / ")}</p><p>登记疾病/人群：${(r.conditions || []).map(esc).join("；")}</p></details>` },
  ];
  const tEl = document.getElementById("matrix");
  const catalog = C.topic_catalog || [];
  let topicView = catalog.length > 0;
  const initial = catalog.filter(t => t.kind === "eligibility_threshold");
  const selectedTopics = new Set((initial.length ? initial : catalog).slice(0,4).map(t => t.topic_id));
  const topicCols = () => [{...cols[0],html:r=>`${cols[0].html(r)}<p class="hint">${r.population_extent ? "全研究 · " : ""}N=${r.enrollment == null ? esc(r.enrollment_text || "—") : esc(r.enrollment)} ${esc(r.enrollment_type)}</p>`},
    ...catalog.filter(t=>selectedTopics.has(t.topic_id)).map(t=>({label:t.label,html:r=>
      (r.design_excerpts || []).filter(e=>e.topic_id === t.topic_id).flatMap(e=>e.snippets).map(clause).join("") || "—"}))];
  if (catalog.length && document.getElementById("design-view-controls")) {
    document.getElementById("design-view-controls").hidden = false;
    const picker = document.getElementById("topic-picker");
    picker.innerHTML = `<legend>比较主题</legend>${catalog.map(t=>`<label><input type="checkbox" data-topic-id="${esc(t.topic_id)}" ${selectedTopics.has(t.topic_id) ? "checked" : ""}>${esc(t.label)}</label>`).join("")}`;
    picker.addEventListener("change", event => {
      const id = event.target.dataset.topicId;
      if (!catalog.some(t=>t.topic_id === id)) return;
      if (event.target.checked) selectedTopics.add(id); else selectedTopics.delete(id);
      redraw();
    });
    ["topics-all","topics-clear"].forEach(id => document.getElementById(id).addEventListener("click",()=>{
      selectedTopics.clear();
      if (id === "topics-all") catalog.forEach(t=>selectedTopics.add(t.topic_id));
      picker.querySelectorAll("input").forEach(input=>input.checked=selectedTopics.has(input.dataset.topicId));
      redraw();
    }));
    ["view-topics","view-comprehensive"].forEach(id => document.getElementById(id).addEventListener("click",()=>{
      topicView = id === "view-topics";
      redraw();
    }));
  }
  tEl.addEventListener("click", event => {
    const button = event.target.closest("button[data-design-id]");
    if (button) show(rows.find(r => r.trial_id === button.dataset.designId));
  });
  function redraw() {
    const data = filtered();
    document.getElementById("count").textContent = `${data.length} / ${rows.length} 项试验`;
    tEl.classList?.toggle("topic-matrix",topicView);
    tEl.style?.setProperty?.("--topic-columns",selectedTopics.size);
    if (catalog.length) {
      document.getElementById("view-topics").setAttribute("aria-pressed",String(topicView));
      document.getElementById("view-comprehensive").setAttribute("aria-pressed",String(!topicView));
      document.getElementById("topic-controls").hidden = !topicView;
      document.getElementById("topic-selection-label").textContent = `比较主题 · ${selectedTopics.size} / ${catalog.length}`;
    }
    table(tEl, topicView ? topicCols() : cols, data, { rowClass: (r) => (r.is_own ? "own" : ""), onRow: show });
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
      <dt>${r.population_extent ? "全研究样本量" : "样本量"}</dt><dd>${r.enrollment == null ? esc(r.enrollment_text || "—") : r.enrollment + "（" + esc(r.enrollment_type) + "）"}</dd>
      <dt>登记年龄 / 性别</dt><dd>${esc(r.min_age || "—")} 至 ${esc(r.max_age || "—")} · ${esc(r.sex || "—")}</dd>
      <dt>地区</dt><dd>${esc(r.countries.join("、"))}</dd>${r.background_therapy.length ? `<dt>背景治疗</dt><dd>${esc(r.background_therapy.join("；"))}</dd>` : ""}</dl>
      ${(r.conditions || []).length ? `<p><strong>登记疾病/人群：</strong>${r.conditions.map(esc).join("；")}</p>` : ""}
      <h3>组别</h3><table class="grid"><thead><tr><th>组别</th><th>角色</th><th>干预与给药</th></tr></thead><tbody>
      ${r.arms.map((a) => `<tr><td>${esc(a.label)}</td><td>${esc(a.role_label)}</td><td>${esc(a.interventions.join("；"))}<br><span class="hint">${esc(a.description)}</span></td></tr>`).join("")}</tbody></table>
      <h3>主要终点</h3><ul>${r.primary.map((o) => `<li>${esc(o.title)}<br><span class="hint">${esc(o.timeframe)}</span>${endpointDetails(o)}</li>`).join("")}</ul>
      <h3>次要终点（${r.secondary.length}）</h3><ul>${r.secondary.map((o) => `<li>${esc(o.title)}<br><span class="hint">${esc(o.timeframe)}</span>${endpointDetails(o)}</li>`).join("")}</ul>
      ${(r.study_narrative || []).map(n=>`<details><summary>${esc(n.label)}</summary><p>${esc(n.text)}</p></details>`).join("")}
      ${(r.design_excerpts || []).length ? `<h3>关键设计原文</h3>${excerpts(r)}` : ""}
      <h3>入选与排除标准（原文）</h3><pre>${window.U.annotate(r.eligibility || "—",r.eligibility_marks,document.getElementById("q").value.trim())}</pre>
      ${(r.registrations || []).map(g => `<details><summary>${esc(g.registry)} · ${esc(g.trial_id)}</summary>
        <p>${src(g.url, g.trial_id)} · ${esc(g.phase)} · ${esc(g.status)} · ${esc(g.sponsor)}</p>
        <p>样本量：${g.enrollment == null ? esc(g.enrollment_text || "—") : esc(g.enrollment)} ${esc(g.enrollment_type)}</p>
        <h3>组别与给药</h3><ul>${g.arms.map(a => `<li>${esc(a.label)} · ${esc(a.role_label)} · ${esc(a.interventions.join("；"))}<p>${esc(a.description)}</p></li>`).join("")}</ul>
        <h3>主要终点</h3><ul>${g.primary.map(o => `<li>${esc(o.title)} · ${esc(o.timeframe)}${endpointDetails(o)}</li>`).join("")}</ul>
        <h3>次要终点</h3><ul>${g.secondary.map(o => `<li>${esc(o.title)} · ${esc(o.timeframe)}${endpointDetails(o)}</li>`).join("")}</ul>
        <h3>完整入排</h3><pre>${window.U.annotate(g.eligibility,g.eligibility_marks,document.getElementById("q").value.trim())}</pre></details>`).join("")}`);
  }

  function drawSummary(data) {
  const counts = {};
  data.forEach((r) => primaryCategories(r).forEach((c) => (counts[c] = (counts[c] || 0) + 1)));
  const ck = Object.keys(counts).sort((a, b) => counts[b] - counts[a]);
  const conceptEl = document.getElementById("concept-chart");
  conceptEl.parentElement.hidden = !ck.length;
  if (ck.length) chart("concept-chart", { grid: { left: 200, right: 40, top: 20, bottom: 30 }, tooltip: {},
    xAxis: { type: "value", minInterval: 1 }, yAxis: { type: "category", data: ck, inverse: true },
    series: [{ type: "bar", data: ck.map((k) => counts[k]), itemStyle: { color: "#008F8A" }, label: { show: true, position: "right" } }] });

  table(document.getElementById("concept-data"), [{label:"主要终点",key:"label"},
    {label:"研究数",key:"count",num:true}], ck.map(k=>({label:k,count:counts[k]})));

  // 样本量 × 首例入组
  const drawable = data.filter(r => r.start && r.enrollment != null);
  const sizeEl = document.getElementById("size-chart");
  sizeEl.parentElement.hidden = !data.length;
  sizeEl.hidden = !drawable.length;
  document.getElementById("size-data-label").textContent = `完整数据表 · ${drawable.length}/${data.length}项已绘制`;
  table(document.getElementById("size-data"), [
    {label:"药物 / 研究",html:r=>`${(r.products || []).map(p=>esc(p.label)).join("、")} · ${src(r.url,r.acronym || r.trial_id)}`},
    {label:"期别",key:"phase"},{label:"首例入组",key:"start"},{label:"样本量",key:"enrollment",num:true},
    {label:"样本量类型",key:"enrollment_type"},
    {label:"绘图状态",html:r=>[!r.start ? "未记录首例日期" : "",r.enrollment == null ? "未记录样本量" : ""].filter(Boolean).join("；") || "已绘制"}
  ],data);
  sizeEl.style.height = (drawable.length < 5 ? 240 : 300) + "px";
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
