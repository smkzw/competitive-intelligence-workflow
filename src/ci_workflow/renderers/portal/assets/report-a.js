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
  var safetyTermLabels = {};
  var efficacyContextArms = {};
  var safetyContextArms = {};
  var trialEfficacyPair = {};
  var trialSafetyPair = {};
  var productInsightDrawer = document.getElementById("a-product-insight-drawer");
  var productInsightClose = document.getElementById("a-product-insight-close");
  var productInsightId = null;
  var productInsightTrigger = null;
  var fallbackSafetyTermKeys = {
    "任何teae": "any_teae", "any teae": "any_teae", "teae": "any_teae",
    "任何sae": "any_sae", "any sae": "any_sae", "sae": "any_sae",
    "nasopharyngitis": "nasopharyngitis", "鼻咽炎": "nasopharyngitis",
    "headache": "headache", "头痛": "headache",
    "upper respiratory tract infection": "upper_respiratory_tract_infection",
    "上呼吸道感染": "upper_respiratory_tract_infection",
    "injection site reaction": "injection_site_reaction", "注射部位反应": "injection_site_reaction"
  };

  function normalizedSafetyTerm(value) {
    return String(value || "").trim().replace(/\s+/g, " ").toLowerCase();
  }
  function safetyTermKey(rowOrTerm) {
    if (rowOrTerm && typeof rowOrTerm === "object" && rowOrTerm.term_key) {
      return rowOrTerm.term_key;
    }
    var raw = rowOrTerm && typeof rowOrTerm === "object" ? rowOrTerm.term : rowOrTerm;
    var normalized = normalizedSafetyTerm(raw);
    return fallbackSafetyTermKeys[normalized] || "raw:" + normalized;
  }
  function safetyTermLabel(termKey) {
    return safetyTermLabels[termKey] || ({
      any_teae: "任何TEAE",
      any_sae: "任何SAE",
      nasopharyngitis: "鼻咽炎",
      headache: "头痛",
      upper_respiratory_tract_infection: "上呼吸道感染",
      injection_site_reaction: "注射部位反应"
    }[termKey] || termKey);
  }

  safety.forEach(function (row) {
    var key = safetyTermKey(row);
    if (!safetyTermLabels[key]) safetyTermLabels[key] = row.term_label || row.term || key;
  });

  efficacy.forEach(function (row) {
    if (!numericValue(row.value)) return;
    var key = [row.product_id, row.trial_id, row.endpoint, row.timepoint, row.unit, row.population].join("\u0001");
    if (!efficacyContextArms[key]) efficacyContextArms[key] = {};
    efficacyContextArms[key][row.arm] = true;
  });
  Object.keys(efficacyContextArms).forEach(function (key) {
    var parts = key.split("\u0001");
    if (efficacyContextArms[key]["治疗组"] && efficacyContextArms[key]["对照组"]) {
      trialEfficacyPair[parts[1]] = true;
    }
  });
  safety.forEach(function (row) {
    var termKey = safetyTermKey(row);
    if (!numericValue(row.value) || (termKey !== "any_teae" && termKey !== "any_sae")) return;
    var key = [row.product_id, row.trial_id, row.category, termKey, row.time_window, row.unit].join("\u0001");
    if (!safetyContextArms[key]) safetyContextArms[key] = {};
    safetyContextArms[key][row.arm || "治疗组"] = true;
  });
  Object.keys(safetyContextArms).forEach(function (key) {
    var parts = key.split("\u0001");
    if (safetyContextArms[key]["治疗组"] && safetyContextArms[key]["对照组"]) {
      trialSafetyPair[parts[1]] = true;
    }
  });

  function productName(id) {
    for (var i = 0; i < products.length; i += 1) if (products[i].id === id) return products[i].name;
    return id;
  }
  function numericValue(value) {
    return typeof value === "number" && Number.isFinite(value);
  }
  // 独立测试第二轮（UC）：百分率单位同义归一——登记口径写法多样
  // （%、percent、Percentage of Participants 等），不得硬编码单一 "%"
  function isPercentUnit(unit) {
    var u = String(unit || "").trim().toLowerCase().replace("％", "%");
    return u === "%" || u.indexOf("percent") !== -1 || u.indexOf("%") !== -1;
  }
  // 独立视觉复核（copy_zh）：数值与单位直接拼接（"92.2Percentage of
  // responders"）不可读；百分率单位显示 %，其余单位前加空格
  function unitSuffix(unit) {
    return isPercentUnit(unit) ? "%" : " " + String(unit || "").trim();
  }
  function isEasi75(value) {
    var text = String(value || "").toLowerCase();
    return /easi\s*[- ]?\s*75/.test(text)
      || /75\s*%[^]{0,100}eczema area and severity index/.test(text);
  }
  function isWeek16(value) {
    return /(?:week\s*16|16\s*weeks|第\s*16\s*周)/i.test(String(value || ""));
  }
  function isIgaResponse(value) {
    var text = String(value || "").toLowerCase();
    return /(viga|isga|iga)/.test(text)
      && /(0\s*(?:or|and|\/|或)\s*1|clear|almost clear|success|成功|清除|几乎清除)/.test(text);
  }
  function dimensionMatches(dimension, actual, wanted, companion) {
    if (actual === wanted) return true;
    if (dimension === "endpoint" && wanted === "EASI-75") return isEasi75(actual);
    if (dimension === "endpoint" && wanted === "IGA 0/1") return isIgaResponse(actual);
    if (dimension === "timepoint" && wanted === "第16周") {
      return isWeek16(actual);
    }
    return false;
  }
  function rowMatchesFilters(row, endpointFilter, timepointFilter) {
    var endpoints = endpointFilter || selected.endpoint;
    var timepoints = timepointFilter || selected.timepoint;
    if (endpoints && endpoints.length && !endpoints.some(function (value) {
      return dimensionMatches("endpoint", row.endpoint, value, row.timepoint);
    })) return false;
    if (timepoints && timepoints.length && !timepoints.some(function (value) {
      return dimensionMatches("timepoint", row.timepoint, value, row.endpoint);
    })) return false;
    return true;
  }
  function trialById(id) {
    for (var i = 0; i < trials.length; i += 1) if (trials[i].id === id) return trials[i];
    return null;
  }
  function hasEfficacyPair(trialId) {
    return Boolean(trialEfficacyPair[trialId]);
  }
  function hasSafetyPair(trialId) {
    return Boolean(trialSafetyPair[trialId]);
  }
  function trialRank(trial) {
    if (!trial) return -1;
    var score = 0;
    if (hasEfficacyPair(trial.id) && hasSafetyPair(trial.id)) score += 1000000;
    else if (hasEfficacyPair(trial.id)) score += 10000;
    else if (hasSafetyPair(trial.id)) score += 1000;
    if (trial.role === "核心") score += 100;
    if (trial.treatment_sample_size != null) score += 10;
    if (trial.status === "COMPLETED") score += 1;
    return score;
  }
  function endpointRank(endpoint) {
    var value = String(endpoint || "").toLowerCase();
    if (/easi[\s-]*75/.test(value)) return 100;
    if (isIgaResponse(value)) return 90;
    if (value.indexOf("easi") >= 0) return 80;
    if (value.indexOf("iga") >= 0 || value.indexOf("viga") >= 0 || value.indexOf("isga") >= 0) return 70;
    return 0;
  }
  function timepointWeeks(value) {
    var raw = String(value || "");
    var weeks = [];
    var patterns = [/(?:week\s*|第\s*)(\d+)\s*(?:周)?/ig, /(\d+)\s*weeks?/ig];
    patterns.forEach(function (pattern) {
      var match;
      while ((match = pattern.exec(raw)) !== null) {
        var week = Number(match[1]);
        if (weeks.indexOf(week) === -1) weeks.push(week);
      }
    });
    return weeks;
  }
  function timepointRank(timepoint) {
    var weeks = timepointWeeks(timepoint);
    if (weeks.length) {
      var nearest = Math.min.apply(null, weeks.map(function (week) { return Math.abs(week - 16); }));
      return 100 - Math.min(80, nearest) - (weeks.length > 1 ? 10 : 0);
    }
    return 0;
  }
  function trialFor(productId) {
    var candidates = trials.filter(function (trial) { return trial.product_id === productId; });
    candidates.sort(function (left, right) {
      return trialRank(right) - trialRank(left)
        || (right.sample_size || 0) - (left.sample_size || 0)
        || left.id.localeCompare(right.id, "zh-CN");
    });
    return candidates.length ? candidates[0] : null;
  }
  function efficacyRank(row) {
    var score = trialRank(trialById(row.trial_id)) * 10
      + endpointRank(row.endpoint) + timepointRank(row.timepoint);
    var key = [row.product_id, row.trial_id, row.endpoint, row.timepoint, row.unit, row.population].join("\u0001");
    return score + (efficacyContextArms[key]
      && efficacyContextArms[key]["治疗组"]
      && efficacyContextArms[key]["对照组"] ? 1 : 0);
  }
  function efficacyPairFor(productId, endpointFilter, timepointFilter) {
    var contexts = {};
    for (var i = 0; i < efficacy.length; i += 1) {
      var row = efficacy[i];
      if (row.product_id !== productId || !numericValue(row.value)) continue;
      if (!rowMatchesFilters(row, endpointFilter, timepointFilter)) continue;
      var key = [row.trial_id, row.endpoint, row.timepoint, row.unit, row.population].join("\u0001");
      if (!contexts[key]) contexts[key] = {
        trial_id: row.trial_id,
        endpoint: row.endpoint,
        timepoint: row.timepoint,
        unit: row.unit,
        rows: {}
      };
      var current = contexts[key].rows[row.arm];
      if (!current || (row.denominator || 0) > (current.denominator || 0)
        || ((row.denominator || 0) === (current.denominator || 0) && row.row_id < current.row_id)) {
        contexts[key].rows[row.arm] = row;
      }
    }
    var pairs = Object.keys(contexts).map(function (key) { return contexts[key]; }).filter(function (context) {
      // S1 修复：治疗+对照 对 或 单臂 均可形成矩阵点
      return (context.rows["治疗组"] && context.rows["对照组"])
        || (context.rows["治疗组"] && !context.rows["对照组"])
        || (!context.rows["治疗组"] && Object.keys(context.rows).length > 0);
    });
    // 独立测试第二轮（UC/IgAN）：登记臂名不一定是"治疗组"，排序锚行
    // 必须兜底到该上下文的任一臂行，不得硬读 rows["治疗组"]
    function pairAnchorRow(context) {
      return context.rows["治疗组"]
        || context.rows["对照组"]
        || context.rows[Object.keys(context.rows)[0]];
    }
    pairs.sort(function (left, right) {
      var leftRow = pairAnchorRow(left);
      var rightRow = pairAnchorRow(right);
      if (!leftRow || !rightRow) return leftRow ? -1 : 1;
      return efficacyRank(rightRow) - efficacyRank(leftRow)
        || String(leftRow.row_id).localeCompare(String(rightRow.row_id), "zh-CN");
    });
    return pairs.length ? pairs[0] : null;
  }
  function efficacyFor(productId, arm, endpointFilter, timepointFilter) {
    var pair = efficacyPairFor(productId, endpointFilter, timepointFilter);
    return pair ? pair.rows[arm].value : null;
  }
  function safetyRowsForView(productScope) {
    var active = visibleProductNames();
    var chosenArm = selected.arm && selected.arm.length ? selected.arm[0] : null;
    return safety.filter(function (row) {
      if (productScope && row.product_id !== productScope) return false;
      if (!productScope && Object.keys(active).length && !active[productName(row.product_id)]) return false;
      if (chosenArm && (row.arm || "治疗组") !== chosenArm) return false;
      if (selected.category && selected.category.indexOf(row.category) === -1) return false;
      if (selected.event && selected.event.indexOf(safetyTermKey(row)) === -1) return false;
      return true;
    });
  }
  function safetyRecordFor(productId, termView, trialId, armDetail, sourceRows) {
    var termKey = typeof termView === "string" ? termView : termView.key;
    var categoryName = typeof termView === "string" ? null : termView.category;
    var timeWindow = typeof termView === "string" ? null : termView.time_window;
    if (!categoryName && termKey === "any_teae") categoryName = "治疗期间不良事件";
    if (!categoryName && termKey === "any_sae") categoryName = "严重不良事件";
    var rows = sourceRows || safetyRowsForView();
    var matches = rows.filter(function (row) {
      if (row.product_id !== productId || safetyTermKey(row) !== termKey) return false;
      if (trialId && row.trial_id !== trialId) return false;
      if (selected.arm && selected.arm.length && (row.arm || "治疗组") !== selected.arm[0]) return false;
      if (armDetail && (row.arm_detail || "").trim() !== armDetail.trim()) return false;
      // 独立复核会商 P0 #3：payload 类目带（登记）后缀，包含式匹配
      if (categoryName && row.category !== categoryName && String(row.category || "").indexOf(categoryName) === -1) return false;
      if (timeWindow && row.time_window !== timeWindow) return false;
      return numericValue(row.value) || row.value == null;
    });
    matches.sort(function (left, right) {
      var leftPublished = numericValue(left.value) ? 1 : 0;
      var rightPublished = numericValue(right.value) ? 1 : 0;
      return rightPublished - leftPublished
        || trialRank(trialById(right.trial_id)) - trialRank(trialById(left.trial_id))
        || (numericValue(right.value) ? right.value : -Infinity) - (numericValue(left.value) ? left.value : -Infinity)
        || left.row_id.localeCompare(right.row_id, "zh-CN");
    });
    return matches.length ? matches[0] : null;
  }
  function safetyFor(productId, termView, trialId, armDetail, sourceRows) {
    var row = safetyRecordFor(productId, termView, trialId, armDetail, sourceRows);
    return row ? row.value : null;
  }
  function safetyDisplayValue(row) {
    if (!row) return "未公开";
    if (numericValue(row.value)) return row.value + (row.unit || "");
    return row.disclosure_state || "未公开";
  }
  function safetyTimeWindowLabel(value) {
    var raw = String(value || "").trim();
    var exact = {
      "AEs: Baseline (Day 1) up to Day 29, SAEs: Baseline (Day 1) up to Day 36": "AE：第1至29天；SAE：第1至36天",
      "Week 24 through week 68": "第24至68周",
      "Baseline through week 24": "基线至第24周",
      "From first dose to Week 24": "首次给药至第24周",
      "From first dose date in LTS Period (Week 8) until last follow-up visit (up to 52 weeks)": "长期扩展期第8周至末次随访（最长52周）",
      "登记结果报告期（来源未单列时间窗）": "登记报告期"
    };
    if (exact[raw]) return exact[raw];
    var weekRange = raw.match(/^Week\s*(\d+)\s*(?:through|to|-)\s*week\s*(\d+)$/i);
    if (weekRange) return "第" + weekRange[1] + "至" + weekRange[2] + "周";
    var upToWeek = raw.match(/^(?:up to|through)\s*week\s*(\d+)$/i);
    if (upToWeek) return "至第" + upToWeek[1] + "周";
    if (/[A-Za-z]/.test(raw)) return "观察期见明细";
    return raw;
  }
  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }
  function productById(productId) {
    for (var i = 0; i < products.length; i += 1) {
      if (products[i].id === productId) return products[i];
    }
    return null;
  }
  function textOr(value, fallback) {
    return value === null || value === undefined || value === "" ? fallback : String(value);
  }
  function clearNode(node) {
    while (node && node.firstChild) node.removeChild(node.firstChild);
  }
  function appendInsightField(container, label, value) {
    var row = el("div", "kz-a-insight-field");
    row.appendChild(el("dt", "", label));
    row.appendChild(el("dd", "", textOr(value, "未公开")));
    container.appendChild(row);
  }
  function appendInsightHeading(container, title) {
    container.appendChild(el("h3", "", title));
    var fields = el("dl", "kz-a-insight-fields");
    container.appendChild(fields);
    return fields;
  }
  function appendInsightList(container, values) {
    var list = el("ul", "kz-a-insight-list");
    values.forEach(function (value) {
      list.appendChild(el("li", "", value));
    });
    container.appendChild(list);
  }
  function insightRowValue(row) {
    return row && numericValue(row.value) ? String(row.value) + (row.unit || "") : "未公开";
  }
  function insightCountValue(row) {
    if (!row || row.numerator === null || row.numerator === undefined
      || row.denominator === null || row.denominator === undefined) return "未公开";
    return String(row.numerator) + "/" + String(row.denominator);
  }
  function productDossierHref(productId) {
    var path = window.location.pathname || "";
    var prefix = /\/products\/[^/]+\.html$/i.test(path) ? "../" : "";
    return prefix + "products/" + encodeURIComponent(String(productId)) + ".html";
  }
  function insightTrial(productId, preferredTrialId) {
    if (preferredTrialId) {
      var preferred = trialById(preferredTrialId);
      if (preferred && preferred.product_id === productId) return preferred;
    }
    return trialFor(productId);
  }
  function efficacyPairForInsight(productId, preferredTrialId) {
    var contexts = {};
    for (var i = 0; i < efficacy.length; i += 1) {
      var row = efficacy[i];
      if (row.product_id !== productId || !numericValue(row.value) || !isPercentUnit(row.unit)) continue;
      var key = [row.trial_id, row.endpoint, row.timepoint, row.unit, row.population].join("\u0001");
      if (!contexts[key]) {
        contexts[key] = {
          trial_id: row.trial_id,
          endpoint: row.endpoint,
          timepoint: row.timepoint,
          rows: {}
        };
      }
      var current = contexts[key].rows[row.arm];
      if (!current || (row.denominator || 0) > (current.denominator || 0)
        || ((row.denominator || 0) === (current.denominator || 0) && row.row_id < current.row_id)) {
        contexts[key].rows[row.arm] = row;
      }
    }
    var pairs = Object.keys(contexts).map(function (key) { return contexts[key]; }).filter(function (context) {
      return context.rows["治疗组"] && context.rows["对照组"];
    });
    pairs.sort(function (left, right) {
      var leftPreferred = left.trial_id === preferredTrialId ? 1 : 0;
      var rightPreferred = right.trial_id === preferredTrialId ? 1 : 0;
      return rightPreferred - leftPreferred
        || efficacyRank(right.rows["治疗组"]) - efficacyRank(left.rows["治疗组"])
        || left.rows["治疗组"].row_id.localeCompare(right.rows["治疗组"].row_id, "zh-CN");
    });
    return pairs.length ? pairs[0] : null;
  }
  function insightSafetyRow(productId, termKey, preferredTrialId, armDetail) {
    var matches = safety.filter(function (row) {
      if (row.product_id !== productId || safetyTermKey(row) !== termKey) return false;
      if (preferredTrialId && row.trial_id !== preferredTrialId) return false;
      if ((row.arm || "治疗组") !== "治疗组") return false;
      if (armDetail && (row.arm_detail || "").trim() !== armDetail.trim()) return false;
      return numericValue(row.value) || row.value == null;
    });
    matches.sort(function (left, right) {
      return (numericValue(right.value) ? 1 : 0) - (numericValue(left.value) ? 1 : 0)
        || trialRank(trialById(right.trial_id)) - trialRank(trialById(left.trial_id))
        || (numericValue(right.value) ? right.value : -Infinity)
          - (numericValue(left.value) ? left.value : -Infinity)
        || left.row_id.localeCompare(right.row_id, "zh-CN");
    });
    return matches.length ? matches[0] : null;
  }
  function buildProductInsightContext(productId, trigger) {
    var preferredTrialId = trigger && trigger.getAttribute("data-trial-id");
    var efficacyRowId = trigger && trigger.getAttribute("data-efficacy-row-id");
    var selectedEfficacy = efficacyRowId ? efficacy.find(function (row) {
      return row.product_id === productId && row.row_id === efficacyRowId;
    }) : null;
    if (selectedEfficacy) preferredTrialId = selectedEfficacy.trial_id;
    var pair = efficacyPairForInsight(productId, preferredTrialId);
    if (selectedEfficacy) pair = null; // Never replace the clicked dose/endpoint by a ranked pair.
    var trial = insightTrial(productId, preferredTrialId || (pair && pair.trial_id));
    if (pair && trial && pair.trial_id !== trial.id) {
      trial = trialById(pair.trial_id) || trial;
    }
    var armDetail = pair && pair.rows["治疗组"] ? pair.rows["治疗组"].arm_detail : null;
    var eventKey = trigger && trigger.getAttribute("data-event-key");
    var eventRow = eventKey ? insightSafetyRow(productId, eventKey, trial && trial.id, armDetail) : null;
    var selectedRowId = trigger && trigger.getAttribute("data-row-id");
    if (selectedRowId) {
      var exactRows = safety.filter(function (row) {
        return row.product_id === productId && row.row_id === selectedRowId;
      });
      if (exactRows.length === 1) eventRow = exactRows[0];
    }
    var teaeRow = insightSafetyRow(productId, "any_teae", trial && trial.id, armDetail);
    var saeRow = insightSafetyRow(productId, "any_sae", trial && trial.id, armDetail);
    var primarySafety = eventRow || teaeRow || saeRow;
    return {
      trial: trial,
      selectedEfficacy: selectedEfficacy,
      pair: pair,
      eventRow: eventRow,
      teaeRow: teaeRow,
      saeRow: saeRow,
      primarySafety: primarySafety,
      eventKey: eventKey || (primarySafety && safetyTermKey(primarySafety)) || "",
      triggerEfficacyValue: trigger && trigger.getAttribute("data-efficacy-value"),
      triggerEventRate: trigger && trigger.getAttribute("data-event-rate")
    };
  }
  function renderInsightSummary(product, context) {
    var summary = document.getElementById("a-product-insight-summary");
    if (!summary) return;
    clearNode(summary);
    var trial = context.trial;
    var pair = context.pair;
    var safetyRow = context.primarySafety;
    var efficacyText = context.selectedEfficacy
      ? (context.selectedEfficacy.arm_detail || context.selectedEfficacy.arm) + " " + insightRowValue(context.selectedEfficacy)
      : pair
      ? "治疗组 " + insightRowValue(pair.rows["治疗组"]) + "；对照组 " + insightRowValue(pair.rows["对照组"])
      : "未公开";
    var safetyText = safetyRow
      ? (safetyRow.term_label || safetyRow.term || safetyTermLabel(safetyTermKey(safetyRow)))
        + " " + insightRowValue(safetyRow)
      : "未公开";
    var fields = [
      ["项目最高阶段", product.phase],
      ["当前证据试验", trial ? trial.name + "（" + trial.display_id + "）" : "未公开"],
      ["证据试验分期", trial ? trial.phase : "未公开"],
      ["疗效治疗组/对照组", efficacyText],
      ["疗效数据时间点", context.selectedEfficacy ? context.selectedEfficacy.timepoint : pair ? efficacyObservationTimepoint(pair) : "未公开"],
      ["安全性事件", safetyText],
      ["安全性观察窗", safetyRow ? safetyTimeWindowLabel(safetyRow.time_window) : "未公开"],
      ["治疗组样本量", trial ? textOr(trial.treatment_sample_size, "未公开") : "未公开"],
      ["总样本量", trial ? textOr(trial.sample_size, "未公开") : "未公开"]
    ];
    fields.forEach(function (field) {
      var item = el("dl", "kz-a-insight-summary-field");
      item.appendChild(el("dt", "", field[0]));
      item.appendChild(el("dd", "", field[1]));
      summary.appendChild(item);
    });
  }
  function renderInsightEfficacy(product, context) {
    var panel = document.querySelector('[data-product-panel="efficacy"]');
    if (!panel) return;
    clearNode(panel);
    var fields = appendInsightHeading(panel, "关键疗效");
    var selectedObservation = context.selectedEfficacy;
    if (selectedObservation) {
      appendInsightField(fields, "终点", selectedObservation.endpoint);
      appendInsightField(fields, "数据时间点", selectedObservation.timepoint);
      appendInsightField(fields, "分析人群", selectedObservation.population);
      appendInsightField(fields, "组别", selectedObservation.arm_detail || selectedObservation.arm);
      appendInsightField(fields, "观察值", insightRowValue(selectedObservation));
      appendInsightField(fields, "人数", insightCountValue(selectedObservation));
      panel.appendChild(el("p", "kz-a-insight-note", "此处对应刚才选择的原始观察，不替换为其他剂量或默认终点，也不自动配对对照。"));
      return;
    }
    var pair = context.pair;
    if (!pair) {
      panel.appendChild(el("p", "kz-a-insight-note", "当前产品暂无可同时核对治疗组与对照组的公开疗效数值。"));
      return;
    }
    appendInsightField(fields, "终点", pair.endpoint);
    appendInsightField(fields, "数据时间点", efficacyObservationTimepoint(pair));
    appendInsightField(fields, "分析人群", pair.rows["治疗组"].population);
    appendInsightField(fields, "治疗组", insightRowValue(pair.rows["治疗组"]));
    appendInsightField(fields, "对照组", insightRowValue(pair.rows["对照组"]));
    appendInsightField(fields, "治疗组人数", insightCountValue(pair.rows["治疗组"]));
    appendInsightField(fields, "对照组人数", insightCountValue(pair.rows["对照组"]));
    panel.appendChild(el("p", "kz-a-insight-note", "疗效数值保留产品、试验、组别、时间点与分析人群身份；具体来源定位请进入数据依据页签。"));
  }
  function renderInsightSafety(product, context) {
    var panel = document.querySelector('[data-product-panel="safety"]');
    if (!panel) return;
    clearNode(panel);
    var fields = appendInsightHeading(panel, "关键安全性");
    var rows = [context.eventRow, context.teaeRow, context.saeRow];
    var seen = {};
    rows = rows.filter(function (row) {
      if (!row || seen[row.row_id]) return false;
      seen[row.row_id] = true;
      return true;
    });
    if (!rows.length) {
      panel.appendChild(el("p", "kz-a-insight-note", "当前产品暂无可在本页核对的公开关键安全性数值。"));
      return;
    }
    rows.forEach(function (row, index) {
      if (index > 0) panel.appendChild(el("hr", "", null));
      appendInsightField(fields, "事件", row.term_label || row.term);
      appendInsightField(fields, "安全性维度", row.category);
      appendInsightField(fields, "组别", row.arm_detail || row.arm || "治疗组");
      appendInsightField(fields, "发生率", insightRowValue(row));
      appendInsightField(fields, "人数", insightCountValue(row));
      appendInsightField(fields, "观察窗", safetyTimeWindowLabel(row.time_window));
    });
  }
  function renderInsightProfile(product) {
    var panel = document.querySelector('[data-product-panel="profile"]');
    if (!panel) return;
    clearNode(panel);
    var fields = appendInsightHeading(panel, "完整产品档案");
    appendInsightField(fields, "研发企业", product.developer);
    appendInsightField(fields, "靶点", product.target);
    appendInsightField(fields, "技术类型", product.modality);
    appendInsightField(fields, "最高阶段", product.phase);
    appendInsightField(fields, "当前状态", product.status);
    appendInsightField(fields, "开发地域", (product.regions || []).join("、"));
    appendInsightField(fields, "给药方式", product.route);
    appendInsightField(fields, "作用机制", product.mechanism);
    var link = el("a", "kz-a-insight-dossier-link", "查看完整产品档案");
    link.href = productDossierHref(product.id);
    panel.appendChild(link);
  }
  function renderInsightEvidence(product, context) {
    var panel = document.querySelector('[data-product-panel="evidence"]');
    if (!panel) return;
    clearNode(panel);
    var fields = appendInsightHeading(panel, "数据依据");
    appendInsightField(fields, "报告适用范围", product.name + "及其公开临床结果");
    appendInsightField(fields, "数据截至", formatCutoff(data.data_cutoff));
    appendInsightField(fields, "当前试验", context.trial ? context.trial.display_id : "未公开");
    var publicSources = data.public_sources || [];
    if (!publicSources.length) {
      panel.appendChild(el("p", "kz-a-insight-note", "此报告没有绑定可核验的具体公共来源；来源类别不能替代出处。"));
      return;
    }
    appendInsightField(fields, "报告级来源数量", publicSources.length);
    panel.appendChild(el("h4", "", "报告级资料来源"));
    var list = el("ol", "kz-a-public-source-list");
    publicSources.forEach(function (source) {
      var item = el("li", "");
      var label = el(source.url ? "a" : "span", "", source.label);
      if (source.url) {
        label.href = source.url;
        label.target = "_blank";
        label.rel = "noopener noreferrer";
      }
      item.appendChild(label);
      item.appendChild(el("p", "", source.source_type + "｜发布日期：" + source.published_at
        + "｜数据截止：" + source.data_cutoff));
      list.appendChild(item);
    });
    panel.appendChild(list);
    panel.appendChild(el("p", "kz-a-insight-note", "以上是报告级来源集合，不代表每份来源都支持当前产品；行级支持关系尚未在此展开。"));
  }
  function setProductInsightTab(tabId, moveFocus) {
    if (!productInsightDrawer) return;
    var tabs = productInsightDrawer.querySelectorAll("[data-product-tab]");
    var panels = productInsightDrawer.querySelectorAll("[data-product-panel]");
    var active = false;
    for (var i = 0; i < tabs.length; i += 1) {
      var selectedTab = tabs[i].getAttribute("data-product-tab") === tabId;
      tabs[i].setAttribute("aria-selected", selectedTab ? "true" : "false");
      tabs[i].tabIndex = selectedTab ? 0 : -1;
      if (selectedTab) active = true;
    }
    if (!active) tabId = "efficacy";
    for (var j = 0; j < panels.length; j += 1) {
      panels[j].hidden = panels[j].getAttribute("data-product-panel") !== tabId;
    }
    if (moveFocus) {
      var target = productInsightDrawer.querySelector('[data-product-tab="' + tabId + '"]');
      if (target) target.focus();
    }
  }
  function renderProductInsight(productId, trigger) {
    var product = productById(productId);
    if (!product || !productInsightDrawer) return false;
    var context = buildProductInsightContext(productId, trigger);
    productInsightId = product.id;
    var title = document.getElementById("a-product-insight-title");
    var subtitle = document.getElementById("a-product-insight-subtitle");
    if (title) title.textContent = product.name;
    if (subtitle) subtitle.textContent = product.target + "｜" + product.modality + "｜项目最高阶段：" + product.phase;
    productInsightDrawer.setAttribute("data-product-id", product.id);
    productInsightDrawer.setAttribute("data-trial-id", context.trial ? context.trial.id : "");
    renderInsightSummary(product, context);
    renderInsightEfficacy(product, context);
    renderInsightSafety(product, context);
    renderInsightProfile(product);
    renderInsightEvidence(product, context);
    setProductInsightTab("efficacy", false);
    return true;
  }
  function writeProductFocusUrl() {
    var query = new URLSearchParams(window.location.search || "");
    if (productInsightId) query.set("focus", productInsightId);
    else query.delete("focus");
    var next = window.location.pathname + (query.toString() ? "?" + query.toString() : "");
    window.history.replaceState(null, "", next);
  }
  function openProductInsight(productId, trigger, syncUrl) {
    if (!renderProductInsight(productId, trigger)) return false;
    productInsightTrigger = trigger || document.activeElement;
    productInsightDrawer.hidden = false;
    document.body.classList.add("kz-a-insight-drawer-open");
    if (productInsightClose) productInsightClose.focus();
    if (syncUrl !== false) writeProductFocusUrl();
    return true;
  }
  function closeProductInsight(restoreFocus, syncUrl) {
    var wasOpen = productInsightDrawer && !productInsightDrawer.hidden;
    if (productInsightDrawer) productInsightDrawer.hidden = true;
    document.body.classList.remove("kz-a-insight-drawer-open");
    var trigger = productInsightTrigger;
    productInsightTrigger = null;
    productInsightId = null;
    if (restoreFocus !== false && wasOpen && trigger && trigger.isConnected
      && typeof trigger.focus === "function") trigger.focus();
    if (syncUrl !== false && wasOpen) writeProductFocusUrl();
  }
  function insightFocusableNodes() {
    if (!productInsightDrawer) return [];
    return Array.prototype.slice.call(productInsightDrawer.querySelectorAll(
      'button:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])'
    )).filter(function (node) {
      return !node.hidden && !node.closest("[hidden]") && node.getClientRects().length > 0;
    });
  }
  document.addEventListener("keydown", function (event) {
    if (!productInsightDrawer || productInsightDrawer.hidden) return;
    if (event.key === "Escape" || event.key === "Esc") {
      event.preventDefault();
      event.stopPropagation();
      closeProductInsight(true);
      return;
    }
    var tab = event.target && event.target.closest
      ? event.target.closest("[data-product-tab]") : null;
    if (tab && (event.key === "ArrowRight" || event.key === "ArrowDown"
      || event.key === "ArrowLeft" || event.key === "ArrowUp")) {
      var tabs = Array.prototype.slice.call(productInsightDrawer.querySelectorAll("[data-product-tab]"));
      var current = tabs.indexOf(tab);
      var delta = event.key === "ArrowRight" || event.key === "ArrowDown" ? 1 : -1;
      var next = tabs[(current + delta + tabs.length) % tabs.length];
      event.preventDefault();
      setProductInsightTab(next.getAttribute("data-product-tab"), true);
      return;
    }
    if (event.key !== "Tab") return;
    var focusable = insightFocusableNodes();
    if (!focusable.length) return;
    var first = focusable[0], last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  });
  function visibleProductNames() {
    if (selected.product && selected.product.length) {
      var chosen = {};
      selected.product.forEach(function (name) { chosen[name] = true; });
      return chosen;
    }
    return {};
  }
  function efficacyTimepointLabel(value) {
    var raw = String(value || "").trim();
    var weeks = timepointWeeks(raw);
    if (weeks.length === 1) return "第" + weeks[0] + "周";
    if (weeks.length > 1) {
      var nearest = weeks.slice().sort(function (left, right) {
        return Math.abs(left - 16) - Math.abs(right - 16) || left - right;
      })[0];
      return "多时间点（含第" + nearest + "周）";
    }
    return /[A-Za-z]/.test(raw) ? "时间点见明细" : raw;
  }
  function efficacyObservationTimepoint(pair) {
    var endpoint = String(pair && pair.endpoint || "");
    var match = endpoint.match(/第\s*(\d+(?:\.\d+)?)\s*周/)
      || endpoint.match(/[（(]\s*Week\s*(\d+(?:\.\d+)?)\s*[）)]/i);
    if (match) return "第" + match[1] + "周";
    return efficacyTimepointLabel(pair && pair.timepoint);
  }
  function efficacyEndpointLabel(value) {
    if (isEasi75(value)) return "EASI-75";
    if (isIgaResponse(value)) return "IGA 0/1";
    return "其他主要疗效指标";
  }
  function paginateObservations(host, groupSelector, label) {
    var observations = Array.prototype.slice.call(host.querySelectorAll("[data-row-id]"));
    var pageSize = 60, currentPage = 0;
    if (observations.length > pageSize) {
      var navigation = el("nav", "kz-a-observation-pagination");
      navigation.setAttribute("aria-label", label + "图表翻页");
      var previous = el("button", "", "上一页"), next = el("button", "", "下一页");
      previous.type = "button"; next.type = "button";
      var status = el("span", ""); status.setAttribute("aria-live", "polite");
      function showPage(index) {
        currentPage = index;
        observations.forEach(function (node, position) {
          node.hidden = position < index * pageSize || position >= (index + 1) * pageSize;
        });
        Array.prototype.forEach.call(host.querySelectorAll(groupSelector), function (group) {
          group.hidden = !group.querySelector("[data-row-id]:not([hidden])");
        });
        previous.disabled = index === 0;
        next.disabled = (index + 1) * pageSize >= observations.length;
        status.textContent = "第" + (index + 1) + "/" + Math.ceil(observations.length / pageSize)
          + "页，共" + observations.length + "条观察（全部可翻页）";
      }
      previous.addEventListener("click", function () { showPage(currentPage - 1); });
      next.addEventListener("click", function () { showPage(currentPage + 1); });
      navigation.appendChild(previous); navigation.appendChild(status); navigation.appendChild(next);
      host.insertBefore(navigation, host.firstChild); showPage(0);
    }
  }
  function renderEfficacy(host) {
    host.innerHTML = "";
    var active = visibleProductNames();
    var productScope = host.getAttribute("data-product-scope");
    var groups = {};
    var title = ((selected.timepoint || []).join("、") + (selected.endpoint || []).join("、"))
      || "公开疗效观察";
    var heading = document.querySelector("[data-efficacy-heading] h2");
    if (heading) heading.textContent = title;
    host.setAttribute("aria-label", title + "：按试验及完整观察条件分组");
    efficacy.forEach(function (item) {
      if (!numericValue(item.value) || !rowMatchesFilters(item)) return;
      if (productScope && item.product_id !== productScope) return;
      if (!productScope && Object.keys(active).length && !active[productName(item.product_id)]) return;
      var key = [item.product_id, item.trial_id, item.endpoint, item.timepoint, item.unit, item.population].join("\u0001");
      if (!groups[key]) groups[key] = [];
      groups[key].push(item);
    });
    var keys = Object.keys(groups);
    if (!keys.length) {
      host.appendChild(el("div", "kz-empty", "当前筛选没有可绘制的公开疗效数值。"));
      return;
    }
    keys.forEach(function (key) {
      var observations = groups[key];
      var first = observations[0];
      var trial = trialById(first.trial_id);
      var minimum = Math.min.apply(null, [0].concat(observations.map(function (item) { return item.value; })));
      var maximum = Math.max.apply(null, [isPercentUnit(first.unit) ? 100 : 0].concat(observations.map(function (item) { return item.value; })));
      var span = maximum - minimum || 1;
      var row = el("div", "kz-a-bar-row kz-a-observation-group");
      row.setAttribute("data-product-id", first.product_id);
      row.setAttribute("data-trial-id", first.trial_id);
      var label = el("div", "kz-a-bar-label");
      var product = el("button", "kz-a-product-trigger", productName(first.product_id));
      product.setAttribute("data-a-product-focus", first.product_id);
      product.setAttribute("data-trial-id", first.trial_id);
      product.setAttribute("aria-label", productName(first.product_id) + "：打开产品档案");
      label.appendChild(product);
      label.appendChild(el("small", "", first.endpoint + "｜" + first.timepoint));
      label.appendChild(el("small", "", (trial ? trial.display_id : first.trial_id) + "｜" + first.population));
      row.appendChild(label);
      var bars = el("div", "kz-a-bar-row__bars");
      observations.forEach(function (item) {
        var lane = el("div", "kz-a-bar-lane");
        lane.setAttribute("data-row-id", item.row_id);
        var observationButton = el("button", "kz-a-product-trigger", item.arm_detail || item.arm);
        observationButton.type = "button";
        observationButton.setAttribute("data-a-product-focus", item.product_id);
        observationButton.setAttribute("data-trial-id", item.trial_id);
        observationButton.setAttribute("data-efficacy-row-id", item.row_id);
        observationButton.setAttribute("aria-label", (item.arm_detail || item.arm) + "：查看此项疗效观察");
        lane.appendChild(observationButton);
        var track = el("div", "kz-a-bar-track");
        var zero = el("i", "kz-a-zero-line");
        zero.style.left = ((0 - minimum) / span * 100) + "%";
        track.appendChild(zero);
        var bar = el("div", "kz-a-bar" + (item.arm === "对照组" ? " kz-a-bar--control" : ""));
        bar.style.left = ((Math.min(0, item.value) - minimum) / span * 100) + "%";
        bar.style.width = (Math.abs(item.value) / span * 100) + "%";
        bar.title = (item.arm_detail || item.arm) + " " + item.value + unitSuffix(item.unit);
        track.appendChild(bar);
        lane.appendChild(track);
        lane.appendChild(el("strong", "kz-a-observation-value", item.value + unitSuffix(item.unit)));
        bars.appendChild(lane);
      });
      bars.appendChild(el("small", "kz-a-local-scale", "本组刻度：" + minimum + " 至 " + maximum + unitSuffix(first.unit)));
      row.appendChild(bars); host.appendChild(row);
    });
    paginateObservations(host, ".kz-a-observation-group", "疗效");
    host.appendChild(el("p", "kz-a-chart-note", "保留全部组别和观察；每组独立刻度，不代表跨试验可比或优劣排名。"));
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
    var rows = safetyRowsForView(host.getAttribute("data-product-scope"));
    if (!rows.length) {
      host.appendChild(el("div", "kz-empty", "当前筛选没有公开安全性观察。"));
      return;
    }
    var groups = {};
    rows.forEach(function (item) {
      var key = [item.product_id, item.trial_id, item.arm, item.arm_detail, item.time_window].join("\u0001");
      if (!groups[key]) groups[key] = [];
      groups[key].push(item);
    });
    Object.keys(groups).forEach(function (key) {
      var observations = groups[key], first = observations[0];
      var group = el("section", "kz-a-safety-observation-group");
      var trial = trialById(first.trial_id);
      var productLabel = el("h3", "", productName(first.product_id));
      productLabel.setAttribute("data-heat-label", "product");
      group.appendChild(productLabel);
      group.appendChild(el("p", "kz-a-safety-context",
        (trial ? trial.display_id : "未公开试验") + "｜" + (first.arm_detail || first.arm)
        + "｜" + first.time_window));
      var cells = el("div", "kz-a-safety-observations");
      observations.forEach(function (record) {
        var cell = el("button", "kz-a-safety-observation kz-a-product-trigger");
        cell.type = "button";
        cell.setAttribute("data-row-id", record.row_id);
        cell.setAttribute("data-a-product-focus", record.product_id);
        cell.setAttribute("data-trial-id", record.trial_id || "");
        cell.setAttribute("data-event-key", safetyTermKey(record));
        cell.setAttribute("data-time-window", record.time_window);
        cell.setAttribute("data-heat-key", safetyTermKey(record));
        cell.setAttribute("data-heat-product", productName(record.product_id));
        cell.setAttribute("data-heat-event", safetyTermLabel(safetyTermKey(record)));
        var eventLabel = el("span", "", record.category + "｜" + safetyTermLabel(safetyTermKey(record)));
        eventLabel.setAttribute("data-heat-label", "event");
        cell.appendChild(eventLabel);
        var value = el("strong", "kz-a-heat-value", safetyDisplayValue(record));
        if (numericValue(record.value) && isPercentUnit(record.unit) && record.value >= 0 && record.value <= 100) {
          value.style.background = color(record.value, 0, 100);
          value.style.color = record.value > 55 ? "#fff" : "#17130f";
        }
        cell.appendChild(value);
        if (record.numerator != null) {
          cell.appendChild(el("small", "", record.numerator + "/" + record.denominator + "人"));
        }
        cell.setAttribute("aria-label", productName(record.product_id) + "："
          + safetyTermLabel(safetyTermKey(record)) + " " + safetyDisplayValue(record)
          + "，" + record.time_window + "，打开产品档案");
        cells.appendChild(cell);
      });
      group.appendChild(cells); host.appendChild(group);
    });
    paginateObservations(host, ".kz-a-safety-observation-group", "安全性");
    host.setAttribute("data-view-digest", rows.map(function (item) { return item.row_id; }).join("|"));
    host.appendChild(el("p", "kz-a-heat-note",
      "保留全部组别、事件和观察窗。百分比颜色使用固定0至100%刻度；其他单位不着色。不同试验、观察窗及分母不默认可比。"));
  }
  function updateMatrixTable(points) {
    var byProduct = {};
    points.forEach(function (point) { byProduct[point.product.id] = point; });
    var rows = document.querySelectorAll("[data-matrix-product]");
    for (var i = 0; i < rows.length; i += 1) {
      var productId = rows[i].getAttribute("data-matrix-product");
      var point = byProduct[productId];
      var values = point ? {
        treatment: point.treatment.toFixed(1) + "%",
        control: point.control.toFixed(1) + "%",
        teae: safetyDisplayValue(point.teaeRecord),
        sae: safetyDisplayValue(point.saeRecord),
        sample: String(point.trial.sample_size)
      } : { treatment: "未纳入当前矩阵", control: "—", teae: "—", sae: "—", sample: "—" };
      Object.keys(values).forEach(function (key) {
        var cell = rows[i].querySelector('[data-matrix-value="' + key + '"]');
        if (cell) cell.textContent = values[key];
      });
    }
  }
  function renderMatrix(host) {
    host.innerHTML = "";
    var coverage = document.querySelector("[data-matrix-coverage]");
    var plot = el("div", "kz-a-bubble-plot");
    var efficacySelect = document.querySelector('[data-matrix-control="efficacy-axis"]');
    var safetySelect = document.querySelector('[data-matrix-control="safety-axis"]');
    var sizeSelect = document.querySelector('[data-matrix-control="bubble-size"]');
    var useDifference = efficacySelect && efficacySelect.selectedIndex === 1;
    var termKey = safetySelect && safetySelect.selectedIndex === 1 ? "any_sae" : "any_teae";
    var termLabel = safetyTermLabel(termKey);
    var sourceRows = safetyRowsForView();
    var useTotalSample = sizeSelect && sizeSelect.selectedIndex === 1;
    var active = visibleProductNames();
    var candidateProducts = products.filter(function (p) {
      return Object.keys(active).length === 0 || active[p.name];
    });
    var points = [];
    function preferredEndpoints(productId) {
      // 独立复核修复：矩阵终点按当前产品疗效行的真实频次数据驱动，
      // 不再硬编码特应性皮炎的 EASI-75（跨适应症错位）。
      var counts = {};
      (productId && efficacyByProduct[productId] ? efficacyByProduct[productId] : efficacyRows)
        .forEach(function (r) {
          var key = r && r.endpoint;
          if (!key) return;
          counts[key] = (counts[key] || 0) + 1;
        });
      return Object.keys(counts).sort(function (a, b) {
        return counts[b] - counts[a];
      });
    }
    var efficacyRows = efficacy;
    var efficacyByProduct = {};
    efficacy.forEach(function (r) {
      var pid = r.product_id;
      efficacyByProduct[pid] = efficacyByProduct[pid] || [];
      efficacyByProduct[pid].push(r);
    });
    candidateProducts.forEach(function (p) {
      var pair = efficacyPairFor(p.id, preferredEndpoints(p.id), []);
      if (!pair) return;
      var trial = trialById(pair.trial_id);
      var safetyArm = selected.arm && selected.arm.length ? selected.arm[0] : "治疗组";
      var safetyArmDetail = pair.rows[safetyArm] ? pair.rows[safetyArm].arm_detail : null;
      // 矩阵沿用当前产品的锚定试验；不同观察窗不跨产品合并，具体窗口随记录保留。
      var eventRecord = safetyRecordFor(p.id, termKey, pair.trial_id, safetyArmDetail, sourceRows);
      var teaeRecord = safetyRecordFor(p.id, "any_teae", pair.trial_id, safetyArmDetail, sourceRows);
      var saeRecord = safetyRecordFor(p.id, "any_sae", pair.trial_id, safetyArmDetail, sourceRows);
      var eventRate = eventRecord && numericValue(eventRecord.value) ? eventRecord.value : null;
      // 会商 P0 #3：登记只给组别计数（例）+风险人数时，纵轴使用派生发生率（%）
      if (eventRate != null && eventRecord.denominator && numericValue(eventRecord.denominator)
          && String(eventRecord.unit || "").indexOf("例") !== -1) {
        eventRate = Math.round(eventRate / numericValue(eventRecord.denominator) * 1000) / 10;
      }
      // 会商 P0 #3：治疗臂样本量缺失时降级用试验总样本量（登记已披露），
      // 不再因此丢点；尺寸标注在气泡说明中体现口径
      if (!trial || eventRate == null) return;
      if (!useTotalSample && trial.treatment_sample_size == null) {
        if (!(trial.sample_size > 0)) return;
      }
      var treatmentRow = pair.rows["治疗组"] || pair.rows[Object.keys(pair.rows)[0]];
      var controlRow = pair.rows["对照组"] || null;
      var treatment = treatmentRow.value;
      var control = controlRow ? controlRow.value : null;
      points.push({
        product: p,
        treatment: treatment,
        control: control,
        x: (useDifference && control != null) ? treatment - control : treatment,
        eventRate: eventRate,
        eventRecord: eventRecord,
        teaeRecord: teaeRecord,
        saeRecord: saeRecord,
        safetyTimeWindow: eventRecord.time_window || "",
        safetyArmDetail: safetyArmDetail,
        efficacyTimepoint: pair.timepoint,
        trial: trial
      });
    });
    updateMatrixTable(points);
    if (!points.length) {
      // 会商 P0 #3：空态必须告知缺哪一轴，而非笼统一句话。
      var missingAxes = [];
      var haveEfficacy = 0, haveSafety = 0, haveSize = 0;
      candidateProducts.forEach(function (p) {
        var pair = efficacyPairFor(p.id, preferredEndpoints(p.id), []);
        if (!pair) return;
        haveEfficacy += 1;
        var trial = trialById(pair.trial_id);
        var safetyArm = selected.arm && selected.arm.length ? selected.arm[0] : "治疗组";
        var safetyArmDetail = pair.rows[safetyArm] ? pair.rows[safetyArm].arm_detail : null;
        var rec = safetyRecordFor(p.id, termKey, pair.trial_id, safetyArmDetail, sourceRows);
        if (rec && numericValue(rec.value) != null) haveSafety += 1;
        if (trial && ((useTotalSample || trial.treatment_sample_size != null) || (trial.sample_size > 0))) haveSize += 1;
      });
      if (!haveEfficacy) missingAxes.push("疗效轴：当前筛选下没有可量化为主要观察的疗效终点");
      if (!haveSafety) missingAxes.push("安全性轴：登记只有组别计数、没有可比较的发生率（%）");
      if (!haveSize) missingAxes.push("样本量轴：登记未按治疗组披露样本量");
      var diag = missingAxes.length
        ? "矩阵需要同时具备三轴数据；本次缺失——" + missingAxes.join("；") + "。"
        : "当前筛选范围内没有产品具备可同时量化的疗效、安全性和样本量数据。";
      if (coverage) coverage.innerHTML = diag;
      host.appendChild(el("div", "kz-empty", diag));
      return;
    }
    var shownProducts = points.map(function (point) { return point.product; });
    var xMin = useDifference ? -100 : 0, xMax = 100;
    var allEventRates = safety.filter(function (record) {
      return safetyTermKey(record) === termKey && isPercentUnit(record.unit) && numericValue(record.value);
    }).map(function (record) { return record.value; });
    var yMin = 0, yMax = termKey === "any_sae"
      ? Math.max(10, Math.ceil(Math.max.apply(null, [0].concat(allEventRates)) / 10) * 10) : 100;
    var maxN = Math.max.apply(null, points.map(function (point) {
      if (!point.trial) return 1;
      var n = useTotalSample
        ? point.trial.sample_size
        : (point.trial.treatment_sample_size != null ? point.trial.treatment_sample_size : point.trial.sample_size);
      return n;
    }));
    for (var i = 0; i < points.length; i += 1) {
      var point = points[i], p = point.product;
      var xPosition = 14 + 72 * (point.x - xMin) / (xMax - xMin);
      var yPosition = 14 + 72 * (yMax - point.eventRate) / (yMax - yMin);
      var trial = point.trial;
      var n = trial ? (useTotalSample ? trial.sample_size : (trial.treatment_sample_size != null ? trial.treatment_sample_size : trial.sample_size)) : 1;
      var size = 80 * Math.sqrt(n / maxN);
      var bubble = el("button", "kz-a-bubble", String(i + 1));
      bubble.type = "button";
      bubble.style.left = xPosition + "%";
      bubble.style.bottom = yPosition + "%";
      bubble.style.width = size + "px"; bubble.style.height = size + "px";
      bubble.setAttribute("data-a-product-focus", p.id);
      bubble.setAttribute("data-product-id", p.id);
      bubble.setAttribute("data-product", p.name);
      bubble.setAttribute("data-efficacy-value", point.x.toFixed(1));
      bubble.setAttribute("data-event-rate", point.eventRate.toFixed(1));
      bubble.setAttribute("data-trial-id", trial.id);
      bubble.setAttribute("data-arm-detail", point.safetyArmDetail || "");
      bubble.setAttribute("data-event-key", termKey);
      bubble.setAttribute("data-disclosure-state", point.eventRecord.disclosure_state || "已公开");
      bubble.setAttribute("data-original-term", point.eventRecord.original_term || point.eventRecord.term || "");
      bubble.setAttribute("data-safety-time-window", point.safetyTimeWindow);
      bubble.title = trial.display_id + "｜" + efficacyTimepointLabel(point.efficacyTimepoint) + "疗效 " + point.x.toFixed(1) + "%｜" + termLabel + " " + point.eventRate + "%｜样本量 " + n
        + (point.safetyTimeWindow ? "｜观察窗 " + point.safetyTimeWindow : "");
      bubble.setAttribute("aria-label", p.name + "：" + bubble.title + "；点击查看产品洞察");
      plot.appendChild(bubble);
    }
    [0, 0.25, 0.5, 0.75, 1].forEach(function (ratio) {
      var xTick = el("span", "kz-a-axis-tick kz-a-axis-tick--x", (xMin + ratio * (xMax - xMin)).toFixed(1) + "%");
      xTick.style.left = (14 + ratio * 72) + "%"; plot.appendChild(xTick);
      var yTick = el("span", "kz-a-axis-tick kz-a-axis-tick--y", (yMax - ratio * (yMax - yMin)).toFixed(1) + "%");
      yTick.style.bottom = (14 + ratio * 72) + "%"; plot.appendChild(yTick);
    });
    plot.appendChild(el("span", "kz-a-axis-title kz-a-axis-title--x", useDifference ? "治疗组－对照组差值" : "治疗组疗效观察值"));
    plot.appendChild(el("span", "kz-a-axis-title kz-a-axis-title--y", termLabel + "发生率"));
    host.appendChild(plot);
    var key = el("ol", "kz-a-bubble-key");
    points.forEach(function (point, index) {
      var item = el("li", "");
      item.appendChild(el("b", "", String(index + 1)));
      var legendButton = el("button", "", point.product.name);
      legendButton.type = "button";
      legendButton.setAttribute("data-a-product-focus", point.product.id);
      legendButton.setAttribute("data-product-id", point.product.id);
      legendButton.setAttribute("data-product", point.product.name);
      legendButton.setAttribute("data-trial-id", point.trial.id);
      legendButton.setAttribute("data-event-key", termKey);
      legendButton.setAttribute("aria-label", point.product.name + "：打开疗效与安全性产品档案");
      item.appendChild(legendButton);
      key.appendChild(item);
    });
    host.appendChild(key);
    var missing = products.filter(function (product) {
      if (selected.product && selected.product.length && selected.product.indexOf(product.name) === -1) return false;
      return !shownProducts.some(function (shown) { return shown.id === product.id; });
    });
    if (missing.length) {
      var disclosure = el("details", "kz-a-matrix-coverage__details");
      disclosure.appendChild(el("summary", "", "本图绘入 " + shownProducts.length + " 个产品；另有 " + missing.length + " 个因当前三维数据未完整公开而未绘入"));
      disclosure.appendChild(el("p", "", missing.map(function (product) { return product.name; }).join("、")));
      if (coverage) { coverage.innerHTML = ""; coverage.appendChild(disclosure); }
    } else if (coverage) {
      coverage.textContent = "本图已绘入当前筛选范围内全部 " + shownProducts.length + " 个产品。";
    }
    host.appendChild(el("p", "kz-a-chart-note", "横轴：越靠右，疗效观察值越高｜纵轴：发生率（越低越靠上）；0起点且量程覆盖全部公开值，产品筛选不改变刻度"));
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
          var chip = el("button", "kz-a-landscape-product", p.name);
          chip.type = "button";
          chip.setAttribute("data-visual-node", "product");
          chip.setAttribute("data-a-product-focus", p.id);
          chip.setAttribute("data-product-id", p.id);
          chip.setAttribute("data-product", p.name);
          chip.setAttribute("aria-label", p.name + "：打开疗效与安全性产品档案");
          cell.appendChild(chip);
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
      var item = el("article", "kz-a-portfolio-item kz-a-product-trigger");
      item.setAttribute("data-visual-node", "trial");
      item.setAttribute("data-a-product-focus", trial.product_id);
      item.setAttribute("data-product-id", trial.product_id);
      item.setAttribute("data-product", productName(trial.product_id));
      item.setAttribute("data-trial-id", trial.id);
      item.setAttribute("role", "button");
      item.setAttribute("tabindex", "0");
      item.setAttribute("aria-label", productName(trial.product_id) + "：" + trial.display_id + "，打开疗效与安全性产品档案");
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
      var item = el("article", "kz-a-timeline-event kz-a-product-trigger");
      item.setAttribute("data-visual-node", "event");
      item.setAttribute("data-a-product-focus", row.product_id);
      item.setAttribute("data-product-id", row.product_id);
      item.setAttribute("data-product", productName(row.product_id));
      item.setAttribute("role", "button");
      item.setAttribute("tabindex", "0");
      item.setAttribute("aria-label", productName(row.product_id) + "：" + (row.event || row.display_family || row.observation) + "，打开疗效与安全性产品档案");
      item.appendChild(el("span", "kz-a-timeline-dot"));
      item.appendChild(el("strong", "", productName(row.product_id)));
      var track = row.track ? row.track + "｜" : "";
      item.appendChild(el("b", "", track + (row.event || row.display_family || row.observation)));
      item.appendChild(el("small", "", (row.date || (row.jurisdiction + "｜" + row.expiry)) + (row.status ? "｜" + row.status : "")));
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
      trialList.appendChild(el("li", "", trial.name + "（" + trial.display_id + "）｜" + trial.phase + "｜总样本量：" + textOr(trial.sample_size, "未公开") + "｜治疗组样本量：" + textOr(trial.treatment_sample_size, "未公开")));
    });
    content.appendChild(trialList);
    content.appendChild(el("h3", "", "资料来源"));
    var sourceList = el("ul", "kz-a-evidence-list");
    sources.forEach(function (row) {
      sourceList.appendChild(el("li", "", row.source + "｜" + row.scope));
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
      var flow = el("article", "kz-a-network-flow kz-a-product-trigger");
      flow.setAttribute("data-visual-node", "relationship");
      flow.setAttribute("data-a-product-focus", row.product_id);
      flow.setAttribute("data-product-id", row.product_id);
      flow.setAttribute("data-product", productName(row.product_id));
      flow.setAttribute("role", "button");
      flow.setAttribute("tabindex", "0");
      flow.setAttribute("aria-label", productName(row.product_id) + "：打开疗效与安全性产品档案");
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
    products.filter(function (p) {
      return Object.keys(active).length === 0 || active[p.name];
    }).forEach(function (p) {
      var card = el("div", "kz-a-product-trigger");
      card.setAttribute("data-a-product-focus", p.id);
      card.setAttribute("data-product-id", p.id);
      card.setAttribute("data-product", p.name);
      card.setAttribute("role", "button");
      card.setAttribute("tabindex", "0");
      card.setAttribute("aria-label", p.name + "：打开疗效与安全性产品档案");
      card.appendChild(el("strong", "", p.name));
      card.appendChild(el("span", "", p.target + "｜" + p.phase + "｜" + p.status));
      wrapper.appendChild(card);
    });
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
      else renderGeneric(hosts[i]);
    }
  }
  function applyPagedTables(resetPage) {
    var tables = document.querySelectorAll("[data-paged-table]");
    for (var t = 0; t < tables.length; t += 1) {
      var table = tables[t];
      var pagination = table.nextElementSibling;
      if (!pagination || !pagination.hasAttribute("data-table-pagination")) continue;
      var rows = table.querySelectorAll("tbody tr");
      var matches = [];
      for (var r = 0; r < rows.length; r += 1) {
        if (rows[r].getAttribute("data-filter-match") !== "false") matches.push(rows[r]);
      }
      var pageSize = Number(table.getAttribute("data-page-size")) || 50;
      var pageCount = Math.max(1, Math.ceil(matches.length / pageSize));
      var page = resetPage ? 1 : Number(table.getAttribute("data-current-page")) || 1;
      page = Math.min(Math.max(page, 1), pageCount);
      table.setAttribute("data-current-page", String(page));
      for (var h = 0; h < rows.length; h += 1) rows[h].hidden = true;
      var start = (page - 1) * pageSize;
      for (var v = start; v < Math.min(start + pageSize, matches.length); v += 1) matches[v].hidden = false;
      var status = pagination.querySelector("[data-page-status]");
      if (status) status.textContent = matches.length ? "第 " + page + "/" + pageCount + " 页｜当前筛选 " + matches.length + " 条｜每页 " + pageSize + " 条" : "当前筛选无数据";
      var previous = pagination.querySelector('[data-page-action="prev"]');
      var next = pagination.querySelector('[data-page-action="next"]');
      if (previous) previous.disabled = page <= 1 || !matches.length;
      if (next) next.disabled = page >= pageCount || !matches.length;
    }
  }
  function applyFilters(resetPage) {
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
        var actual = dim === "event"
          ? (candidates[r].getAttribute("data-event-key") || candidates[r].getAttribute("data-event"))
          : candidates[r].getAttribute("data-" + dim);
        var companion = dim === "endpoint"
          ? candidates[r].getAttribute("data-timepoint")
          : candidates[r].getAttribute("data-endpoint");
        if (actual && !selected[dim].some(function (value) {
          return dimensionMatches(dim, actual, value, companion);
        })) ok = false;
      });
      candidates[r].setAttribute("data-filter-match", ok ? "true" : "false");
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
    for (var u = 0; u < summaries.length; u += 1) summaries[u].textContent = Object.keys(selected).length ? "筛选范围：已选择" : "筛选范围：全部";
    var query = new URLSearchParams();
    Object.keys(selected).forEach(function (dim) { selected[dim].forEach(function (value) { query.append(dim, value); }); });
    var matrixControls = document.querySelectorAll("[data-matrix-control]");
    if (matrixControls.length) {
      if (matrixControls[0].selectedIndex === 1) query.set("matrix_x", "difference");
      if (matrixControls[1].selectedIndex === 1) query.set("matrix_y", "sae");
      if (matrixControls[2].selectedIndex === 1) query.set("matrix_size", "total");
    }
    if (productInsightId) query.set("focus", productInsightId);
    var next = window.location.pathname + (query.toString() ? "?" + query.toString() : "");
    window.history.replaceState(null, "", next);
    applyPagedTables(resetPage !== false);
    renderCharts();
  }
  document.addEventListener("click", function (event) {
    var target = event.target;
    if (!(target instanceof Element)) return;
    var productTrigger = target.closest("[data-a-product-focus]");
    if (productTrigger) {
      event.preventDefault();
      openProductInsight(productTrigger.getAttribute("data-a-product-focus"), productTrigger);
      return;
    }
    var productTab = target.closest("[data-product-tab]");
    if (productTab) {
      event.preventDefault();
      setProductInsightTab(productTab.getAttribute("data-product-tab"), true);
      return;
    }
    if (target.closest("#a-product-insight-close")) {
      event.preventDefault();
      closeProductInsight(true);
      return;
    }
    var filter = target.closest("[data-filter-dimension] button");
    if (filter) {
      var group = filter.closest("[data-filter-dimension]");
      var dimension = group ? group.getAttribute("data-filter-dimension") : "";
      if (dimension === "endpoint" || dimension === "timepoint") {
        var peers = group.querySelectorAll("button[aria-pressed='true']");
        for (var p = 0; p < peers.length; p += 1) peers[p].setAttribute("aria-pressed", "false");
        filter.setAttribute("aria-pressed", "true");
      } else {
        filter.setAttribute("aria-pressed", filter.getAttribute("aria-pressed") === "true" ? "false" : "true");
      }
      applyFilters();
    }
    if (target.closest("[data-filter-reset]")) {
      var pressed = document.querySelectorAll("[data-filter-dimension] button[aria-pressed='true']");
      for (var i = 0; i < pressed.length; i += 1) pressed[i].setAttribute("aria-pressed", "false");
      var defaults = document.querySelectorAll("[data-filter-default]");
      for (var j = 0; j < defaults.length; j += 1) defaults[j].setAttribute("aria-pressed", "true");
      applyFilters();
    }
    var pageAction = target.closest("[data-page-action]");
    if (pageAction) {
      var pagination = pageAction.closest("[data-table-pagination]");
      var table = pagination ? pagination.previousElementSibling : null;
      if (table && table.hasAttribute("data-paged-table")) {
        var direction = pageAction.getAttribute("data-page-action") === "next" ? 1 : -1;
        table.setAttribute("data-current-page", String((Number(table.getAttribute("data-current-page")) || 1) + direction));
        applyPagedTables(false);
        table.scrollIntoView({behavior: "smooth", block: "start"});
      }
    }
    var evidence = target.closest("[data-open-evidence]");
    if (evidence) { var panel=document.getElementById("data-basis-panel"); if(panel){panel.hidden=false;var content=panel.querySelector("[data-evidence-content]");if(content)renderEvidencePanel(content,evidence.getAttribute("data-open-evidence"),evidence.getAttribute("data-evidence-product"));} }
    if (target.closest("[data-close-evidence]")) { var p=document.getElementById("data-basis-panel");if(p)p.hidden=true; }
  });
  document.addEventListener("keydown", function (event) {
    var trigger = event.target && event.target.closest
      ? event.target.closest("[data-a-product-focus]") : null;
    if (!trigger || String(trigger.tagName || "").toLowerCase() === "button") return;
    if (event.key !== "Enter" && event.key !== " ") return;
    event.preventDefault();
    openProductInsight(trigger.getAttribute("data-a-product-focus"), trigger);
  });
  var controls = document.querySelectorAll("[data-matrix-control]");
  for (var c = 0; c < controls.length; c += 1) controls[c].addEventListener("change", function () {
    var host=document.querySelector('[data-module="matrix"] .kz-chart'); if(host){host.setAttribute("data-view-digest", Array.prototype.map.call(controls,function(x){return x.selectedIndex;}).join("-"));applyFilters();}
  });
  var params = new URLSearchParams(window.location.search);
  var initialProductFocus = params.get("focus");
  if (initialProductFocus && productById(initialProductFocus)) productInsightId = initialProductFocus;
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
  var resizeTimer = null;
  window.addEventListener("resize", function () {
    window.clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(renderCharts, 120);
  });
  var filterRoots = document.querySelectorAll("[data-module]");
  for (var f = 0; f < filterRoots.length; f += 1) {
    if (!filterRoots[f].querySelector("[data-filter-dimension]")) continue;
    var tools = el("div", "kz-a-filter-tools");
    var reset = el("button", "", "清除筛选");
    reset.type = "button"; reset.setAttribute("data-filter-reset", "");
    tools.appendChild(reset); tools.appendChild(el("span", "", "筛选范围：全部"));
    tools.lastChild.setAttribute("data-filter-summary", "");
    var grid = filterRoots[f].querySelector(".kz-a-filter-grid") || filterRoots[f].querySelector("[data-filter-dimension]");
    if (grid) grid.insertAdjacentElement("afterend", tools);
  }
  window.addEventListener("popstate", function () {
    var focus = new URLSearchParams(window.location.search || "").get("focus");
    if (focus && productById(focus)) {
      openProductInsight(focus, null, false);
    } else if (productInsightDrawer && !productInsightDrawer.hidden) {
      closeProductInsight(false, false);
    }
  });
  window.setTimeout(function () {
    if (productInsightId) openProductInsight(productInsightId, null, false);
  }, 0);
  applyFilters();
})();
