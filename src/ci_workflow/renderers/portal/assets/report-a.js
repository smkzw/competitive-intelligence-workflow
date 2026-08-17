/** Task 5.4：A 类门户图形、筛选、网址状态、矩阵设置与数据依据交互。 */
(function () {
  "use strict";
  var data = window.REPORT_A || {};
  var products = data.products || [];
  var trials = data.trials || [];
  var efficacy = data.efficacy || [];
  var safety = data.safety || [];
  var regulatory = data.regulatory || [];
  var companies = data.companies || [];
  var patents = data.patents || [];
  var historyRows = data.history || [];
  var sources = data.sources || [];
  var selected = {};

  function productName(id) {
    for (var i = 0; i < products.length; i += 1) if (products[i].id === id) return products[i].name;
    return id;
  }
  function trialFor(productId) {
    for (var i = 0; i < trials.length; i += 1) if (trials[i].product_id === productId) return trials[i];
    return null;
  }
  function efficacyFor(productId, arm) {
    for (var i = 0; i < efficacy.length; i += 1) {
      if (efficacy[i].product_id !== productId || efficacy[i].arm !== arm) continue;
      if (selected.endpoint && selected.endpoint.indexOf(efficacy[i].endpoint) === -1) continue;
      if (selected.timepoint && selected.timepoint.indexOf(efficacy[i].timepoint) === -1) continue;
      return efficacy[i].value;
    }
    return null;
  }
  function safetyFor(productId, term) {
    for (var i = 0; i < safety.length; i += 1) {
      if (safety[i].product_id !== productId || safety[i].term !== term) continue;
      if (selected.category && selected.category.indexOf(safety[i].category) === -1) continue;
      if (selected.event && selected.event.indexOf(safety[i].term) === -1) continue;
      return safety[i].value;
    }
    return null;
  }
  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }
  function visibleProductNames() {
    var active = {};
    var rows = document.querySelectorAll("tbody tr:not([hidden]), [data-product-id]:not([hidden])");
    for (var i = 0; i < rows.length; i += 1) {
      var id = rows[i].getAttribute("data-product-id");
      var name = rows[i].getAttribute("data-product");
      if (id) active[productName(id)] = true;
      if (name) active[name] = true;
    }
    return active;
  }
  function renderEfficacy(host) {
    host.innerHTML = "";
    var active = visibleProductNames();
    var productScope = host.getAttribute("data-product-scope");
    var rows = products.filter(function (p) {
      if (productScope) return p.id === productScope;
      return Object.keys(active).length === 0 || active[p.name];
    });
    for (var i = 0; i < rows.length; i += 1) {
      var p = rows[i];
      var treat = efficacyFor(p.id, "治疗组") || 0;
      var ctrl = efficacyFor(p.id, "对照组") || 0;
      var row = el("div", "kz-a-bar-row");
      row.appendChild(el("strong", "", p.name));
      var bars = el("div", "kz-a-bar-row__bars");
      [["治疗组", treat, "kz-a-bar"], ["对照组", ctrl, "kz-a-bar kz-a-bar--control"]]
        .forEach(function (item) {
          var lane = el("div", "kz-a-bar-lane");
          lane.appendChild(el("span", "", item[0]));
          var track = el("div", "kz-a-bar-track");
          var bar = el("div", item[2], item[1] + "%");
          bar.style.width = Math.max(6, item[1]) + "%";
          bar.title = item[0] + " " + item[1] + "%";
          track.appendChild(bar); lane.appendChild(track); bars.appendChild(lane);
        });
      row.appendChild(bars); host.appendChild(row);
    }
    host.appendChild(el("p", "kz-a-chart-note", "橙色：治疗组｜蓝色：对照组"));
  }
  function color(value, min, max) {
    var ratio = max === min ? 0.5 : (value - min) / (max - min);
    var from = [255, 244, 222], to = [192, 0, 0];
    return "rgb(" + from.map(function (channel, index) {
      return Math.round(channel + ratio * (to[index] - channel));
    }).join(",") + ")";
  }
  function renderSafety(host) {
    host.innerHTML = "";
    var productScope = host.getAttribute("data-product-scope");
    var shownProducts = products.filter(function (item) {
      return !productScope || item.id === productScope;
    });
    var grid = el("div", "kz-a-heatmap");
    grid.style.setProperty("--product-count", shownProducts.length);
    grid.appendChild(el("div", "kz-a-heat-label", "安全性维度"));
    for (var p = 0; p < shownProducts.length; p += 1) grid.appendChild(el("div", "kz-a-heat-label", shownProducts[p].name));
    var terms = ["任何TEAE", "任何SAE", "超敏反应", "鼻咽炎"].filter(function (term) {
      if (selected.event && selected.event.indexOf(term) === -1) return false;
      if (!selected.category) return true;
      return safety.some(function (row) {
        return row.term === term && selected.category.indexOf(row.category) !== -1;
      });
    });
    for (var t = 0; t < terms.length; t += 1) {
      var values = shownProducts.map(function (item) { return safetyFor(item.id, terms[t]); });
      var published = values.filter(function (value) { return value != null; });
      var min = Math.min.apply(null, published);
      var max = Math.max.apply(null, values.map(function (v) { return v == null ? 0 : v; }));
      grid.appendChild(el("div", "kz-a-heat-label", terms[t]));
      for (var j = 0; j < values.length; j += 1) {
        var cell = el("div", "", values[j] == null ? "未公开" : values[j] + "%");
        var ratio = max === min ? 0.5 : (values[j] - min) / (max - min);
        cell.style.background = values[j] == null ? "#eeeeec" : color(values[j], min, max);
        cell.style.color = values[j] != null && ratio > 0.55 ? "#fff" : "#17130f";
        grid.appendChild(cell);
      }
    }
    host.appendChild(grid);
    host.appendChild(el("p", "kz-a-heat-note", "颜色深浅仅在同一事件内比较；灰色表示未公开。"));
  }
  function renderMatrix(host) {
    host.innerHTML = "";
    var plot = el("div", "kz-a-bubble-plot");
    var efficacySelect = document.querySelector('[data-matrix-control="efficacy-axis"]');
    var safetySelect = document.querySelector('[data-matrix-control="safety-axis"]');
    var sizeSelect = document.querySelector('[data-matrix-control="bubble-size"]');
    var useDifference = efficacySelect && efficacySelect.selectedIndex === 1;
    var term = safetySelect && safetySelect.selectedIndex === 1 ? "任何SAE" : "任何TEAE";
    var useTotalSample = sizeSelect && sizeSelect.selectedIndex === 1;
    var active = visibleProductNames();
    var shownProducts = products.filter(function (p) {
      return Object.keys(active).length === 0 || active[p.name];
    });
    var points = shownProducts.map(function (p) {
      var treatment = efficacyFor(p.id, "治疗组") || 0;
      var control = efficacyFor(p.id, "对照组") || 0;
      return {
        product: p,
        x: useDifference ? treatment - control : treatment,
        eventRate: safetyFor(p.id, term) || 0,
        trial: trialFor(p.id)
      };
    });
    var xMin = useDifference ? -100 : 0, xMax = 100;
    var yMin = 0, yMax = term === "任何SAE" ? 10 : 100;
    var maxN = Math.max.apply(null, points.map(function (point) {
      if (!point.trial) return 1;
      return useTotalSample ? point.trial.sample_size : point.trial.treatment_sample_size;
    }));
    var placed = [];
    for (var i = 0; i < points.length; i += 1) {
      var point = points[i], p = point.product;
      var xPosition = 14 + 72 * (point.x - xMin) / (xMax - xMin);
      var yPosition = 14 + 72 * (yMax - point.eventRate) / (yMax - yMin);
      for (var j = 0; j < placed.length; j += 1) {
        if (Math.abs(xPosition - placed[j][0]) < 9 && Math.abs(yPosition - placed[j][1]) < 12) {
          yPosition = Math.max(12, Math.min(88, yPosition + (i % 2 ? 12 : -12)));
        }
      }
      placed.push([xPosition, yPosition]);
      var trial = point.trial;
      var n = trial ? (useTotalSample ? trial.sample_size : trial.treatment_sample_size) : 1;
      var size = 34 + 46 * Math.sqrt(n / maxN);
      var bubble = el("div", "kz-a-bubble", p.name);
      bubble.style.left = xPosition + "%";
      bubble.style.bottom = yPosition + "%";
      bubble.style.width = size + "px"; bubble.style.height = size + "px";
      bubble.setAttribute("data-efficacy-value", point.x.toFixed(1));
      bubble.setAttribute("data-event-rate", point.eventRate.toFixed(1));
      bubble.title = "疗效 " + point.x.toFixed(1) + "%｜" + term + " " + point.eventRate + "%｜样本量 " + n;
      plot.appendChild(bubble);
    }
    [0, 0.25, 0.5, 0.75, 1].forEach(function (ratio) {
      var xTick = el("span", "kz-a-axis-tick kz-a-axis-tick--x", (xMin + ratio * (xMax - xMin)).toFixed(1) + "%");
      xTick.style.left = (14 + ratio * 72) + "%"; plot.appendChild(xTick);
      var yTick = el("span", "kz-a-axis-tick kz-a-axis-tick--y", (yMax - ratio * (yMax - yMin)).toFixed(1) + "%");
      yTick.style.bottom = (14 + ratio * 72) + "%"; plot.appendChild(yTick);
    });
    plot.appendChild(el("span", "kz-a-axis-title kz-a-axis-title--x", useDifference ? "治疗组－对照组差值" : "治疗组疗效观察值"));
    plot.appendChild(el("span", "kz-a-axis-title kz-a-axis-title--y", term + "发生率"));
    host.appendChild(plot);
    host.appendChild(el("p", "kz-a-chart-note", "横轴：越靠右，疗效观察值越高｜纵轴：发生率（越低越靠上）｜固定范围避免放大细小差异"));
    var sizeNote = document.querySelector(".kz-a-bubble-size");
    if (sizeNote) sizeNote.textContent = "气泡大小：" + (useTotalSample ? "全部随机样本量" : "治疗组样本量");
  }
  function renderLandscape(host) {
    host.innerHTML = "";
    var stages = ["II期及更早", "III期", "申报或上市", "历史观察"];
    var targets = products.map(function (p) { return p.target; }).filter(function (value, index, all) { return all.indexOf(value) === index; });
    var wrapper = el("div", "kz-a-landscape-grid");
    wrapper.style.setProperty("--stage-count", stages.length);
    wrapper.appendChild(el("div", "kz-a-landscape-head", "靶点"));
    stages.forEach(function (stage) { wrapper.appendChild(el("div", "kz-a-landscape-head", stage)); });
    targets.forEach(function (target) {
      wrapper.appendChild(el("strong", "kz-a-landscape-target", target));
      stages.forEach(function (stage) {
        var cell = el("div", "kz-a-landscape-cell");
        products.filter(function (p) {
          if (p.target !== target) return false;
          if (stage === "历史观察") return /终止|暂停|撤回/.test(p.status);
          if (/终止|暂停|撤回/.test(p.status)) return false;
          if (stage === "II期及更早") return /I期|II期/.test(p.phase);
          if (stage === "III期") return /III期/.test(p.phase);
          return /申报|上市/.test(p.phase + p.status);
        }).forEach(function (p) {
          var chip = el("span", "kz-a-landscape-product", p.name);
          chip.setAttribute("data-visual-node", "product"); cell.appendChild(chip);
        });
        if (!cell.children.length) cell.appendChild(el("span", "kz-a-landscape-empty", "—"));
        wrapper.appendChild(cell);
      });
    });
    host.appendChild(wrapper);
  }
  function renderPortfolio(host) {
    host.innerHTML = "";
    var wrapper = el("div", "kz-a-portfolio-visual");
    trials.forEach(function (trial) {
      var item = el("article", "kz-a-portfolio-item");
      item.setAttribute("data-visual-node", "trial");
      item.appendChild(el("span", "", trial.region + "｜" + trial.phase));
      item.appendChild(el("strong", "", productName(trial.product_id)));
      item.appendChild(el("b", "", trial.name));
      item.appendChild(el("small", "", trial.role + "｜" + trial.status + "｜n=" + trial.sample_size));
      wrapper.appendChild(item);
    });
    host.appendChild(wrapper);
  }
  function renderTimeline(host) {
    host.innerHTML = "";
    var chartId = host.getAttribute("data-chart-id") || "";
    var rows = (chartId.indexOf("patent") >= 0 ? patents : chartId.indexOf("history") >= 0 ? historyRows : regulatory).slice();
    rows.sort(function (left, right) {
      var leftDate = left.date || left.expiry || "";
      var rightDate = right.date || right.expiry || "";
      return leftDate.localeCompare(rightDate, "zh-CN");
    });
    var wrapper = el("div", "kz-a-timeline-visual");
    rows.forEach(function (row) {
      var item = el("article", "kz-a-timeline-event");
      item.setAttribute("data-visual-node", "event");
      item.appendChild(el("span", "kz-a-timeline-dot"));
      item.appendChild(el("strong", "", productName(row.product_id)));
      item.appendChild(el("b", "", row.event || row.display_family || row.observation));
      item.appendChild(el("small", "", row.date || (row.jurisdiction + "｜" + row.expiry)));
      wrapper.appendChild(item);
    });
    host.appendChild(wrapper);
  }
  function renderEvidence(host) {
    host.innerHTML = "";
    var wrapper = el("div", "kz-a-evidence-visual");
    sources.forEach(function (row) {
      var item = el("article", "kz-a-evidence-source");
      item.setAttribute("data-visual-node", "source");
      item.appendChild(el("span", "", row.maturity));
      item.appendChild(el("strong", "", row.source));
      item.appendChild(el("p", "", row.scope));
      wrapper.appendChild(item);
    });
    host.appendChild(wrapper);
  }
  function formatCutoff(value) {
    var date = new Date(value);
    if (Number.isNaN(date.getTime())) return value || "未注明";
    return date.getFullYear() + "年" + String(date.getMonth() + 1).padStart(2, "0") + "月" + String(date.getDate()).padStart(2, "0") + "日";
  }
  function renderEvidencePanel(content, title, productScope) {
    content.innerHTML = "";
    content.appendChild(el("h3", "", title));
    content.appendChild(el("p", "", "数据截至 " + formatCutoff(data.data_cutoff)));
    content.appendChild(el("h3", "", "涉及试验"));
    var trialList = el("ul", "kz-a-evidence-list");
    trials.filter(function (trial) { return !productScope || trial.product_id === productScope; }).forEach(function (trial) {
      trialList.appendChild(el("li", "", trial.name + "（" + trial.display_id + "）｜" + trial.phase + "｜总样本量：" + trial.sample_size + "｜治疗组样本量：" + trial.treatment_sample_size));
    });
    content.appendChild(trialList);
    content.appendChild(el("h3", "", "资料来源"));
    var sourceList = el("ul", "kz-a-evidence-list");
    sources.forEach(function (row) {
      sourceList.appendChild(el("li", "", row.source + "｜" + row.scope + "｜" + row.maturity));
    });
    content.appendChild(sourceList);
  }
  function renderNetwork(host) {
    host.innerHTML = "";
    var wrapper = el("div", "kz-a-network-visual");
    companies.forEach(function (row) {
      var flow = el("article", "kz-a-network-flow");
      flow.setAttribute("data-visual-node", "relationship");
      flow.appendChild(el("strong", "", productName(row.product_id)));
      flow.appendChild(el("span", "kz-a-network-arrow", "→"));
      flow.appendChild(el("b", "", row.relationship));
      flow.appendChild(el("span", "kz-a-network-arrow", "→"));
      flow.appendChild(el("em", "", row.territory));
      flow.appendChild(el("small", "", row.licensor + " / " + row.licensee));
      wrapper.appendChild(flow);
    });
    host.appendChild(wrapper);
  }
  function renderGeneric(host) {
    host.innerHTML = "";
    var wrapper = el("div", "kz-a-target-groups");
    products.forEach(function (p) { var card=el("div","");card.appendChild(el("strong","",p.name));card.appendChild(el("span","",p.target+"｜"+p.phase+"｜"+p.status));wrapper.appendChild(card); });
    host.appendChild(wrapper);
  }
  function renderCharts() {
    var hosts = document.querySelectorAll("[data-a-chart]");
    for (var i = 0; i < hosts.length; i += 1) {
      var type = hosts[i].getAttribute("data-a-chart");
      if (type === "efficacy") renderEfficacy(hosts[i]);
      else if (type === "safety") renderSafety(hosts[i]);
      else if (type === "matrix") renderMatrix(hosts[i]);
      else if (type === "landscape" || type === "product-map") renderLandscape(hosts[i]);
      else if (type === "portfolio") renderPortfolio(hosts[i]);
      else if (type === "timeline") renderTimeline(hosts[i]);
      else if (type === "network") renderNetwork(hosts[i]);
      else if (type === "evidence") renderEvidence(hosts[i]);
      else renderGeneric(hosts[i]);
    }
  }
  function applyFilters() {
    var items = document.querySelectorAll("[data-filter-dimension] button[aria-pressed='true']");
    selected = {};
    for (var i = 0; i < items.length; i += 1) {
      var dim = items[i].parentElement.getAttribute("data-filter-dimension");
      if (!selected[dim]) selected[dim] = [];
      selected[dim].push(items[i].getAttribute("data-filter-value"));
    }
    var candidates = document.querySelectorAll("tbody tr, [data-product-id], .kz-a-history-list article");
    var shown = 0;
    for (var r = 0; r < candidates.length; r += 1) {
      var ok = true;
      Object.keys(selected).forEach(function (dim) {
        var actual = candidates[r].getAttribute("data-" + dim);
        if (actual && selected[dim].indexOf(actual) === -1) ok = false;
      });
      candidates[r].hidden = !ok;
      if (ok) shown += 1;
    }
    var empty = document.querySelector(".kz-a-empty");
    if (empty) empty.hidden = shown !== 0;
    var query = new URLSearchParams();
    Object.keys(selected).forEach(function (dim) { selected[dim].forEach(function (value) { query.append(dim, value); }); });
    var matrixControls = document.querySelectorAll("[data-matrix-control]");
    if (matrixControls.length) {
      if (matrixControls[0].selectedIndex === 1) query.set("matrix_x", "difference");
      if (matrixControls[1].selectedIndex === 1) query.set("matrix_y", "sae");
      if (matrixControls[2].selectedIndex === 1) query.set("matrix_size", "total");
    }
    var next = window.location.pathname + (query.toString() ? "?" + query.toString() : "");
    window.history.replaceState(null, "", next);
    renderCharts();
  }
  document.addEventListener("click", function (event) {
    var target = event.target;
    if (!(target instanceof Element)) return;
    var filter = target.closest("[data-filter-dimension] button");
    if (filter) { filter.setAttribute("aria-pressed", filter.getAttribute("aria-pressed") === "true" ? "false" : "true"); applyFilters(); }
    var evidence = target.closest("[data-open-evidence]");
    if (evidence) { var panel=document.getElementById("data-basis-panel"); if(panel){panel.hidden=false;var content=panel.querySelector("[data-evidence-content]");if(content)renderEvidencePanel(content,evidence.getAttribute("data-open-evidence"),evidence.getAttribute("data-evidence-product"));} }
    if (target.closest("[data-close-evidence]")) { var p=document.getElementById("data-basis-panel");if(p)p.hidden=true; }
  });
  var controls = document.querySelectorAll("[data-matrix-control]");
  for (var c = 0; c < controls.length; c += 1) controls[c].addEventListener("change", function () {
    var host=document.querySelector('[data-module="matrix"] .kz-chart'); if(host){host.setAttribute("data-view-digest", Array.prototype.map.call(controls,function(x){return x.selectedIndex;}).join("-"));applyFilters();}
  });
  var params = new URLSearchParams(window.location.search);
  params.forEach(function (value, key) { var button=document.querySelector('[data-filter-dimension="'+CSS.escape(key)+'"] [data-filter-value="'+CSS.escape(value)+'"]');if(button)button.setAttribute("aria-pressed","true"); });
  if (controls.length) {
    controls[0].selectedIndex = params.get("matrix_x") === "difference" ? 1 : 0;
    controls[1].selectedIndex = params.get("matrix_y") === "sae" ? 1 : 0;
    controls[2].selectedIndex = params.get("matrix_size") === "total" ? 1 : 0;
  }
  applyFilters();
})();
