/* 公共工具：只做显示与交互，不做任何科学判断。 */
(function () {
  const D = window.CIW;
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const num = (v, d) => (v == null || Number.isNaN(v) ? "—" : (d == null ? String(+(+v).toFixed(3)) : (+v).toFixed(d)));
  const nN = (n, N, p) => (n == null ? "未报告" : `${n}${N != null ? "/" + N : ""}${p != null ? `（${p}%）` : ""}`);
  const STATUS = { registry: "登记结构化", verified: "模型核对", dual_agreed: "双模型一致", arbitrated: "仲裁", needs_review: "待核", config: "配置", computed: "计算值" };
  const tag = (k) => `<span class="tag ${esc(k)}">${esc(STATUS[k] || k)}</span>`;
  const src = (url, label) => {
    if (!url) return "";
    try {
      const parsed = new URL(String(url));
      if (["http:", "https:"].includes(parsed.protocol)) return `<a href="${esc(parsed.href)}" target="_blank" rel="noopener">${esc(label || "来源")}</a>`;
    } catch {}
    return esc(label || "来源");
  };
  const highlight = (text, query) => {
    const original = String(text == null ? "" : text);
    if (!query) return esc(original);
    const re = new RegExp("(" + String(query).replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")", "gi");
    return original.split(re).map((part, i) => i % 2 ? `<mark>${esc(part)}</mark>` : esc(part)).join("");
  };
  const annotate = (text, spans, query) => {
    const original = String(text == null ? "" : text), chars = Array.from(original);
    const marks = (spans || []).filter(s => Number.isInteger(s.start) && Number.isInteger(s.end) && s.start >= 0 && s.end > s.start && s.end <= chars.length);
    const hits = [];
    if (query) {
      const re = new RegExp(String(query).replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "gi");
      for (const m of original.matchAll(re)) hits.push({start:Array.from(original.slice(0,m.index)).length,end:Array.from(original.slice(0,m.index+m[0].length)).length});
    }
    const edges = [...new Set([0,chars.length,...marks.flatMap(s=>[s.start,s.end]),...hits.flatMap(s=>[s.start,s.end])])].sort((a,b)=>a-b);
    return edges.slice(0,-1).map((a,i)=>{
      const b=edges[i+1];let part=esc(chars.slice(a,b).join(""));
      if(hits.some(s=>s.start<=a&&s.end>=b))part=`<mark>${part}</mark>`;
      if(marks.some(s=>s.start<=a&&s.end>=b))part=`<strong class="criterion-value">${part}</strong>`;
      return part;
    }).join("");
  };
  const OWN = "#A65000", PAL = ["#D46B08", "#008F8A", "#7B5CC7", "#B38A00", "#C4457C"];

  function coverage() {
    const el = document.getElementById("coverage");
    if (!el) return;
    el.innerHTML = D.coverage.map((c) => `<span class="chip ${esc(c.status)}" title="${esc(c.detail || "")}">${esc(c.label)}：${esc(c.status_label)}</span>`).join("");
  }

  function table(el, cols, rows, opts) {
    opts = opts || {};
    let sortKey = null, asc = true;
    function draw() {
      const data = sortKey == null ? rows : [...rows].sort((a, b) => {
        const x = a[sortKey], y = b[sortKey];
        if (x == null) return 1; if (y == null) return -1;
        return (x > y ? 1 : x < y ? -1 : 0) * (asc ? 1 : -1);
      });
      if (!data.length) { el.innerHTML = `<tbody><tr><td class="empty">没有符合条件的记录</td></tr></tbody>`; return; }
      el.innerHTML = `<thead><tr>${cols.map((c, i) => `<th data-i="${i}">${esc(c.label)}</th>`).join("")}</tr></thead>` +
        `<tbody>${data.map((r, ri) => `<tr data-ri="${rows.indexOf(r)}" class="${opts.rowClass ? opts.rowClass(r) : ""}">` +
          cols.map((c) => `<td class="${c.num ? "num" : ""}">${c.html ? c.html(r) : esc(r[c.key])}</td>`).join("") + `</tr>`).join("")}</tbody>`;
      el.querySelectorAll("th").forEach((th) => th.onclick = () => {
        const c = cols[+th.dataset.i]; if (!c.key) return;
        if (sortKey === c.key) asc = !asc; else { sortKey = c.key; asc = true; }
        draw();
      });
      if (opts.onRow) el.querySelectorAll("tbody tr[data-ri]").forEach((tr) => {
        tr.tabIndex = 0;
        const open = () => { tr.focus?.(); opts.onRow(rows[+tr.dataset.ri]); };
        tr.onclick = event => {
          if (event.target.closest?.("a,button,input,select,textarea,summary,details")) return;
          open();
        };
        tr.onkeydown = event => {
          if(event.target === tr && ["Enter", " "].includes(event.key)) { event.preventDefault(); open(); }
        };
      });
    }
    draw();
  }

  let drawerTrigger, drawerFallback;
  function drawer(html) {
    drawerTrigger = document.activeElement;
    drawerFallback = drawerTrigger?.closest?.("table");
    const d = document.getElementById("drawer");
    d.querySelector(".drawer-body").innerHTML = html;
    d.setAttribute("role", "dialog");
    d.setAttribute("aria-label", d.querySelector("h2")?.textContent || "研究详情");
    d.hidden = false;
    if(!d.open) d.showModal();
    d.querySelector(".drawer-body").scrollTop = 0;
    d.querySelector(".close").focus();
  }
  function closeDrawer() {
    const d = document.getElementById("drawer");
    if(!d || d.hidden) return;
    d.close();
    d.hidden = true;
    if(drawerTrigger?.isConnected) drawerTrigger.focus();
    else if(drawerFallback?.isConnected) { drawerFallback.tabIndex = -1; drawerFallback.focus(); }
  }
  document.addEventListener("click", (e) => { if (e.target.closest(".drawer .close")) closeDrawer(); });
  const dialog = document.getElementById("drawer");
  if(dialog?.addEventListener) {
    dialog.addEventListener("cancel", event => { event.preventDefault(); closeDrawer(); });
    dialog.addEventListener("keydown", event => {
      event.stopPropagation();
      if(event.key !== "Tab") return;
      const nodes = [...dialog.querySelectorAll('a[href],button,input,select,textarea,summary,[tabindex]')]
        .filter(el => !el.disabled && el.tabIndex >= 0 && (el.checkVisibility ? el.checkVisibility() : el.getClientRects().length));
      const first = nodes[0], last = nodes[nodes.length-1];
      if(event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
      else if(!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
    });
  }

  function present(option, el) {
    const label = {fontSize:16,color:"#404040"};
    for(const key of ["xAxis","yAxis"]) {
      if(!option[key]) continue;
      const axes = Array.isArray(option[key]) ? option[key] : [option[key]];
      for(const axis of axes) {
        axis.axisLabel = {...label,...axis.axisLabel,fontSize:Math.max(16,axis.axisLabel?.fontSize || 16)};
        axis.nameTextStyle = {...label,...axis.nameTextStyle};
        axis.axisLine = {lineStyle:{color:"#CED3D8"},...axis.axisLine};
        axis.splitLine = {lineStyle:{color:"#E7EBEE"},...axis.splitLine};
      }
    }
    if(option.legend) option.legend.textStyle = label;
    option.textStyle = {fontSize:16,color:"#404040",...option.textStyle};
    option.tooltip = {confine:true,textStyle:label,...option.tooltip};
    option.color = PAL;
    const axis = option.yAxis;
    if(axis?.type === "category" && axis.data.length) {
      const grid = Array.isArray(option.grid) ? option.grid[0] : option.grid;
      const inset = key => typeof grid?.[key] === "number" ? grid[key] : 40;
      el.style.height = Math.max(144, Math.min(axis.data.length,10) * 28 + inset("top") + inset("bottom")) + "px";
    }
    if(axis?.type === "category" && axis.data.length > 10) {
      const last = axis.data.length - 1;
      option.dataZoom = [{type:"slider",yAxisIndex:0,filterMode:"none",width:16,right:0,
        startValue:axis.inverse ? 0 : last-9,endValue:axis.inverse ? 9 : last,
        fillerColor:"rgba(255,153,0,.10)",borderColor:"#E7EBEE",handleStyle:{color:"#B85C00"},
        dataBackground:{lineStyle:{color:"#CED3D8"},areaStyle:{color:"#E7EBEE"}}}];
    }
    option.series = (option.series || []).map(s=>({...s,clip:true,label:{fontSize:16,...s.label}}));
    return option;
  }

  function chart(id, option) {
    const el = document.getElementById(id);
    if (!el || !el.getClientRects().length) return null;
    const prepared = present(option, el);
    const existing = echarts.getInstanceByDom(el);
    const c = existing || echarts.init(el);
    if (existing) c.resize();
    c.setOption(prepared, true);
    if(typeof ResizeObserver !== "undefined" && !el._ciwObserver) {
      el._ciwObserver = new ResizeObserver(() => c.resize());
      el._ciwObserver.observe(el);
    }
    return c;
  }
  window.addEventListener("resize", () => document.querySelectorAll(".chart").forEach((el) => { const c = echarts.getInstanceByDom(el); if (c) c.resize(); }));

  function options(sel, values, keep) {
    const el = document.querySelector(sel);
    const first = el.querySelector("option");
    el.innerHTML = ""; el.appendChild(first);
    [...new Set(values.filter(Boolean))].sort().forEach((v) => { const o = document.createElement("option"); o.value = v; o.textContent = v; el.appendChild(o); });
    if (keep) el.value = keep;
  }

  coverage();
  window.U = { D, esc, num, nN, tag, src, highlight, annotate, table, drawer, chart, present, options, OWN, PAL };
})();
