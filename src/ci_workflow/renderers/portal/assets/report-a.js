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
  function efficacyFor(productId, arm, endpointFilter, timepointFilter) {
    for (var i = 0; i < efficacy.length; i += 1) {
      if (efficacy[i].product_id !== productId || efficacy[i].arm !== arm) continue;
      var endpoints = endpointFilter || selected.endpoint;
      var timepoints = timepointFilter || selected.timepoint;
      if (endpoints && endpoints.indexOf(efficacy[i].endpoint) === -1) continue;
      if (timepoints && timepoints.indexOf(efficacy[i].timepoint) === -1) continue;
      return efficacy[i].value;
    }
    return null;
  }
  function safetyFor(productId, term) {
    var chosenArm = selected.arm && selected.arm.length ? selected.arm[0] : "治疗组";
    for (var i = 0; i < safety.length; i += 1) {
      if (safety[i].product_id !== productId || safety[i].term !== term) continue;
      if ((safety[i].arm || "治疗组") !== chosenArm) continue;
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
    if (selected.product && selected.product.length) {
      var chosen = {};
      selected.product.forEach(function (name) { chosen[name] = true; });
      return chosen;
    }
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
    var isHome = host.getAttribute("data-chart-id") === "home-efficacy";
    var endpointFilter = isHome ? ["EASI-75"] : null;
    var timepointFilter = isHome ? ["第16周"] : null;
    var rows = products.filter(function (p) {
      if (productScope) return p.id === productScope;
      return Object.keys(active).length === 0 || active[p.name];
    }).filter(function (p) {
      return efficacyFor(p.id, "治疗组", endpointFilter, timepointFilter) != null &&
        efficacyFor(p.id, "对照组", endpointFilter, timepointFilter) != null;
    });
    if (!rows.length) {
      host.appendChild(el("div", "kz-empty", "当前产品暂无可横向比较的公开关键疗效数值。"));
      return;
    }
    for (var i = 0; i < rows.length; i += 1) {
      var p = rows[i];
      var treat = efficacyFor(p.id, "治疗组", endpointFilter, timepointFilter);
      var ctrl = efficacyFor(p.id, "对照组", endpointFilter, timepointFilter);
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
    var active = visibleProductNames();
    var shownProducts = products.filter(function (item) {
      if (productScope) return item.id === productScope;
      return Object.keys(active).length === 0 || active[item.name];
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
      var min = published.length ? Math.min.apply(null, published) : 0;
      var max = published.length ? Math.max.apply(null, published) : 0;
      grid.appendChild(el("div", "kz-a-heat-label", terms[t]));
      for (var j = 0; j < values.length; j += 1) {
        var cell = el("div", "", values[j] == null ? "未公开" : values[j] + "%");
        var ratio = values[j] == null ? 0 : (max === min ? 0.5 : (values[j] - min) / (max - min));
        cell.style.background = values[j] == null ? "#eeeeec" : color(values[j], min, max);
        cell.style.color = values[j] != null && ratio > 0.55 ? "#fff" : "#17130f";
        grid.appendChild(cell);
      }
    }
    host.appendChild(grid);
    host.setAttribute("data-view-digest", shownProducts.map(function (item) { return item.id; }).join("|"));
    var armLabel = selected.arm && selected.arm.length ? selected.arm[0] : "治疗组";
    host.appendChild(el("p", "kz-a-heat-note", "当前组别：" + armLabel + "。颜色深浅仅在同一事件内比较；灰色表示未公开。"));
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
    }).filter(function (p) {
      return efficacyFor(p.id, "治疗组") != null &&
        efficacyFor(p.id, "对照组") != null &&
        safetyFor(p.id, term) != null && trialFor(p.id) != null &&
        (useTotalSample || trialFor(p.id).treatment_sample_size != null);
    });
    if (!shownProducts.length) {
      host.appendChild(el("div", "kz-empty", "当前筛选下缺少可同时量化疗效、安全性和样本量的公开数据。"));
      return;
    }
    var points = shownProducts.map(function (p) {
      var treatment = efficacyFor(p.id, "治疗组");
      var control = efficacyFor(p.id, "对照组");
      return {
        product: p,
        x: useDifference ? treatment - control : treatment,
        eventRate: safetyFor(p.id, term),
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
      var bubble = el("div", "kz-a-bubble", String(i + 1));
      bubble.style.left = xPosition + "%";
      bubble.style.bottom = yPosition + "%";
      bubble.style.width = size + "px"; bubble.style.height = size + "px";
      bubble.setAttribute("data-efficacy-value", point.x.toFixed(1));
      bubble.setAttribute("data-event-rate", point.eventRate.toFixed(1));
      bubble.title = "疗效 " + point.x.toFixed(1) + "%｜" + term + " " + point.eventRate + "%｜样本量 " + n;
      bubble.setAttribute("aria-label", p.name + "：" + bubble.title);
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
    var key = el("ol", "kz-a-bubble-key");
    points.forEach(function (point, index) {
      var item = el("li", "");
      item.appendChild(el("b", "", String(index + 1)));
      item.appendChild(el("span", "", point.product.name));
      key.appendChild(item);
    });
    host.appendChild(key);
    var missing = products.filter(function (product) {
      if (selected.product && selected.product.length && selected.product.indexOf(product.name) === -1) return false;
      return !shownProducts.some(function (shown) { return shown.id === product.id; });
    });
    if (missing.length) {
      var disclosure = el("details", "kz-a-matrix-missing");
      disclosure.appendChild(el("summary", "", "另有 " + missing.length + " 个产品因当前三维数据未完整公开，未绘入气泡图"));
      disclosure.appendChild(el("p", "", missing.map(function (product) { return product.name; }).join("、")));
      host.appendChild(disclosure);
    }
    host.appendChild(el("p", "kz-a-chart-note", "横轴：越靠右，疗效观察值越高｜纵轴：发生率（越低越靠上）；固定量程避免放大细小差异"));
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
    function stageForProduct(product) {
      if (/终止|暂停|撤回|停止|清算/.test(product.status)) return "历史观察";
      if (/申报|上市|获批|NDA/.test(product.phase + product.status)) return "申报或上市";
      if (/III期/.test(product.phase)) return "III期";
      return "II期及更早";
    }
    var active = visibleProductNames();
    targets.forEach(function (target) {
      wrapper.appendChild(el("strong", "kz-a-landscape-target", target));
      stages.forEach(function (stage) {
        var cell = el("div", "kz-a-landscape-cell");
        products.filter(function (p) {
          return p.target === target && stageForProduct(p) === stage &&
            (Object.keys(active).length === 0 || active[p.name]);
        }).forEach(function (p) {
          var chip = el("span", "kz-a-landscape-product", p.name);
          chip.setAttribute("data-visual-node", "product"); cell.appendChild(chip);
        });
        if (!cell.children.length) cell.appendChild(el("span", "kz-a-landscape-empty", "—"));
        wrapper.appendChild(cell);
      });
    });
    host.appendChild(wrapper);
    host.setAttribute("data-view-digest", Object.keys(active).sort().join("|") || "全部产品");
  }
  function renderPortfolio(host) {
    host.innerHTML = "";
    var wrapper = el("div", "kz-a-portfolio-visual");
    var active = visibleProductNames();
    trials.filter(function (trial) {
      var name = productName(trial.product_id);
      if (Object.keys(active).length && !active[name]) return false;
      if (selected.phase && selected.phase.indexOf(trial.phase) === -1) return false;
      if (selected.region && selected.region.indexOf(trial.region) === -1) return false;
      return true;
    }).forEach(function (trial) {
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
    var active = visibleProductNames();
    rows = rows.filter(function (row) {
      return Object.keys(active).length === 0 || active[productName(row.product_id)];
    });
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
      var track = row.track ? row.track + "｜" : "";
      item.appendChild(el("b", "", track + (row.event || row.display_family || row.observation)));
      item.appendChild(el("small", "", (row.date || (row.jurisdiction + "｜" + row.expiry)) + (row.status ? "｜" + row.status : "")));
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
    var active = visibleProductNames();
    companies.filter(function (row) {
      return Object.keys(active).length === 0 || active[productName(row.product_id)];
    }).forEach(function (row) {
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
    var active = visibleProductNames();
    products.filter(function (p) { return Object.keys(active).length === 0 || active[p.name]; }).forEach(function (p) { var card=el("div","");card.appendChild(el("strong","",p.name));card.appendChild(el("span","",p.target+"｜"+p.phase+"｜"+p.status));wrapper.appendChild(card); });
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
      var group = items[i].closest("[data-filter-dimension]");
      var dim = group ? group.getAttribute("data-filter-dimension") : null;
      if (!dim) continue;
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
    var empties = document.querySelectorAll("[data-filter-empty]");
    for (var e = 0; e < empties.length; e += 1) empties[e].hidden = shown !== 0;
    var counts = document.querySelectorAll("[data-filter-selection-count]");
    for (var s = 0; s < counts.length; s += 1) {
      var countDim = counts[s].getAttribute("data-filter-selection-count");
      var count = countDim && selected[countDim] ? selected[countDim].length : 0;
      var total = counts[s].closest("[data-filter-total]");
      var totalCount = total ? total.getAttribute("data-filter-total") : String(products.length);
      counts[s].textContent = count ? "已选择 " + count + " 项" : "默认显示全部 " + totalCount + " 项";
    }
    var summaries = document.querySelectorAll("[data-filter-summary]");
    for (var u = 0; u < summaries.length; u += 1) summaries[u].textContent = Object.keys(selected).length ? "筛选已生效" : "当前显示全部";
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
    if (target.closest("[data-filter-reset]")) {
      var pressed = document.querySelectorAll("[data-filter-dimension] button[aria-pressed='true']");
      for (var i = 0; i < pressed.length; i += 1) pressed[i].setAttribute("aria-pressed", "false");
      applyFilters();
    }
    var evidence = target.closest("[data-open-evidence]");
    if (evidence) { var panel=document.getElementById("data-basis-panel"); if(panel){panel.hidden=false;var content=panel.querySelector("[data-evidence-content]");if(content)renderEvidencePanel(content,evidence.getAttribute("data-open-evidence"),evidence.getAttribute("data-evidence-product"));} }
    if (target.closest("[data-close-evidence]")) { var p=document.getElementById("data-basis-panel");if(p)p.hidden=true; }
  });
  var controls = document.querySelectorAll("[data-matrix-control]");
  for (var c = 0; c < controls.length; c += 1) controls[c].addEventListener("change", function () {
    var host=document.querySelector('[data-module="matrix"] .kz-chart'); if(host){host.setAttribute("data-view-digest", Array.prototype.map.call(controls,function(x){return x.selectedIndex;}).join("-"));applyFilters();}
  });
  var params = new URLSearchParams(window.location.search);
  var parameterDimensions = {};
  params.forEach(function (_value, key) { parameterDimensions[key] = true; });
  Object.keys(parameterDimensions).forEach(function (key) {
    var defaults = document.querySelectorAll('[data-filter-dimension="'+CSS.escape(key)+'"] button[aria-pressed="true"]');
    for (var d = 0; d < defaults.length; d += 1) defaults[d].setAttribute("aria-pressed", "false");
  });
  params.forEach(function (value, key) { var button=document.querySelector('[data-filter-dimension="'+CSS.escape(key)+'"] [data-filter-value="'+CSS.escape(value)+'"]');if(button)button.setAttribute("aria-pressed","true"); });
  if (controls.length) {
    controls[0].selectedIndex = params.get("matrix_x") === "difference" ? 1 : 0;
    controls[1].selectedIndex = params.get("matrix_y") === "sae" ? 1 : 0;
    controls[2].selectedIndex = params.get("matrix_size") === "total" ? 1 : 0;
  }
  var filterRoots = document.querySelectorAll("[data-module]");
  for (var f = 0; f < filterRoots.length; f += 1) {
    if (!filterRoots[f].querySelector("[data-filter-dimension]")) continue;
    var tools = el("div", "kz-a-filter-tools");
    var reset = el("button", "", "清除筛选");
    reset.type = "button"; reset.setAttribute("data-filter-reset", "");
    tools.appendChild(reset); tools.appendChild(el("span", "", "当前显示全部"));
    tools.lastChild.setAttribute("data-filter-summary", "");
    var grid = filterRoots[f].querySelector(".kz-a-filter-grid") || filterRoots[f].querySelector("[data-filter-dimension]");
    if (grid) grid.insertAdjacentElement("afterend", tools);
  }
  applyFilters();
})();
