/* 公共工具：只做显示与交互，不做任何科学判断。 */
(function () {
  const D = window.CIW;
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const num = (v, d) => (v == null || Number.isNaN(v) ? "—" : (d == null ? String(+(+v).toFixed(3)) : (+v).toFixed(d)));
  const nN = (n, N, p) => (n == null ? "未报告" : `${n}${N != null ? "/" + N : ""}${p != null ? `（${p}%）` : ""}`);
  const STATUS = { registry: "登记结构化", dual_agreed: "双模型一致", arbitrated: "仲裁", needs_review: "待核", config: "配置", computed: "计算值" };
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
  const OWN = "#c2410c", PAL = ["#0f4c75", "#3282b8", "#2a9d8f", "#6a4c93", "#e76f51", "#8d99ae", "#bc6c25", "#457b9d", "#588157", "#9d4edd"];

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
      if (opts.onRow) el.querySelectorAll("tbody tr[data-ri]").forEach((tr) => tr.onclick = () => opts.onRow(rows[+tr.dataset.ri]));
    }
    draw();
  }

  function drawer(html) {
    const d = document.getElementById("drawer");
    d.querySelector(".drawer-body").innerHTML = html;
    d.hidden = false;
    d.querySelector(".close").focus();
  }
  document.addEventListener("click", (e) => { if (e.target.closest(".drawer .close")) document.getElementById("drawer").hidden = true; });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") document.getElementById("drawer").hidden = true; });

  function chart(id, option) {
    const el = document.getElementById(id);
    if (!el) return null;
    const c = echarts.getInstanceByDom(el) || echarts.init(el);
    c.setOption(option, true);
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
  window.U = { D, esc, num, nN, tag, src, highlight, table, drawer, chart, options, OWN, PAL };
})();
