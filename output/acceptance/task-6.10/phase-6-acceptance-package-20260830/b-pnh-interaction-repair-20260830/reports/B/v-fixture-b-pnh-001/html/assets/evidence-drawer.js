/**
 * Task 4.5 数据依据面板 — 同页右侧面板与固定对照。
 *
 * - 同页打开：不导航、不改变滚动与筛选；关闭同样如此。
 * - 数据全部来自 window.__EVIDENCE_VIEWS__（服务端已验证的只读嵌入），
 *   本模块只渲染，绝不从展示层拼出临床事实。
 * - 空字段以互斥中文状态呈现（不适用/尚未公开/来源未列示/技术暂不可用），
 *   不留白；已报告零值渲染为 0 而不是缺失。
 * - 原文定位仅在存在有效 http(s) 链接时渲染链接，非法协议不生成伪链接。
 * - 固定多条后以并列对照表核对定义、时间点、分母与冲突；重复固定去重。
 * - 未知/过期行失败关闭并给出中文提示。
 *
 * 公开 API（window.__EVIDENCE_DRAWER__）：
 *   openByRowId(rowId, triggerEl) -> boolean  打开一条数据依据（同页）
 *   close()                                   关闭并把焦点返回触发点
 *   pin(rowId) / unpin(rowId) / togglePin(rowId)
 *   pruneToVisible(visibleRowIds)             移除不在当前事实行集内的打开/固定项
 *   isOpen() / getOpenRowId() / getPinnedRowIds() / isPinned(rowId) / hasView(rowId) / listRowIds()
 * 变更事件：宿主元素上派发 CustomEvent("kz-evidence-drawer-change")，
 * detail = { openRowId, pinnedRowIds }，供网址状态层订阅。
 *
 * Zero remote dependencies; works from file://.
 */
(function () {
  "use strict";

  var host = document.getElementById("kz-evidence-drawer");
  if (!host) return; // 页面未安装数据依据面板

  var panel = document.getElementById("kz-evidence-drawer-panel");
  var closeBtn = document.getElementById("kz-evidence-drawer-close");
  var statusEl = document.getElementById("kz-evidence-drawer-status");
  var viewSection = document.getElementById("kz-evidence-view");
  var viewSubject = document.getElementById("kz-evidence-view-subject");
  var viewFields = document.getElementById("kz-evidence-view-fields");
  var viewConflicts = document.getElementById("kz-evidence-view-conflicts");
  var viewConflictList = document.getElementById("kz-evidence-view-conflict-list");
  var viewHistory = document.getElementById("kz-evidence-view-history");
  var viewHistoryList = document.getElementById("kz-evidence-view-history-list");
  var pinBtn = document.getElementById("kz-evidence-pin-btn");
  var pinnedSection = document.getElementById("kz-evidence-pinned");
  var pinnedHint = document.getElementById("kz-evidence-pinned-hint");
  var compareHost = document.getElementById("kz-evidence-compare");

  var views = window.__EVIDENCE_VIEWS__ || [];
  var labels = window.__EVIDENCE_DRAWER_LABELS__ || {};
  var fieldStateLabels = labels.field_states || {};
  var disclosureLabels = labels.disclosure_states || {};
  var roleLabels = labels.document_roles || {};
  var originalTextLabels = labels.original_text_states || {};

  var UNKNOWN_FIELD_STATE = "技术暂不可用";
  var UNKNOWN_DISCLOSURE = "来源未列示";
  var NOT_LISTED = "来源未列示";

  var byRowId = {};
  for (var i = 0; i < views.length; i++) {
    var view = views[i];
    if (view && view.row && view.row.row_id) byRowId[view.row.row_id] = view;
  }

  var openRowId = null;
  var pinnedOrder = [];
  var pinnedSet = {};
  var lastTrigger = null;
  var filterNotice = document.getElementById("kz-evidence-filter-notice");
  if (!filterNotice) {
    filterNotice = document.createElement("p");
    filterNotice.id = "kz-evidence-filter-notice";
    filterNotice.className = "kz-evidence-filter-notice";
    filterNotice.setAttribute("role", "status");
    filterNotice.setAttribute("aria-live", "polite");
    filterNotice.hidden = true;
    var filterBar = document.querySelector(".kz-filter-bar");
    if (filterBar) filterBar.appendChild(filterNotice);
  }

  // 字段渲染清单：[数据键, 中文标签]
  var GENERAL_FIELDS = [
    ["product_zh", "产品"],
    ["trial_zh", "试验"],
    ["group_zh", "组别"],
    ["element_zh", "终点/事件/设计要素"],
    ["scale", "量表"],
    ["timepoint", "时间点"],
    ["value", "值"],
    ["threshold", "阈值"],
    ["unit", "单位"],
    ["numerator", "分子"],
    ["denominator", "分母"],
    ["_disclosure", "披露状态"],
    ["explanation", "数据说明"],
    ["source_version_label_zh", "来源版本"],
    ["_locator", "原文定位"],
    ["_original_text", "简短原文"]
  ];

  var EXTENSION_FIELDS = [
    ["canonical_variable_family", "变量类别"],
    ["source_field_name", "来源字段原名"],
    ["source_field_definition", "来源字段定义"],
    ["statistical_form_or_measurement_object", "统计形式/计量对象"],
    ["scale_version_direction", "量表版本与方向"],
    ["denominator_role", "分母角色"],
    ["time_window_or_baseline_definition", "时间窗/基线定义"],
    ["_reason_original", "原因原文"],
    ["canonical_reason", "原因分类"],
    ["mutual_exclusion_exhaustiveness", "互斥与穷尽"],
    ["compatibility_rule", "可比性口径"],
    ["difference_label", "主要差异"]
  ];

  var COMPARE_FIELDS = [
    ["element_zh", "定义"],
    ["product_zh", "产品"],
    ["trial_zh", "试验"],
    ["group_zh", "组别"],
    ["timepoint", "时间点"],
    ["value", "值"],
    ["unit", "单位"],
    ["numerator", "分子"],
    ["denominator", "分母"],
    ["_disclosure", "披露状态"],
    ["source_version_label_zh", "来源版本"],
    ["_conflicts", "冲突"],
    ["_locator", "原文定位"]
  ];

  function showStatus(message) {
    if (!statusEl) return;
    statusEl.textContent = message || "";
    statusEl.hidden = !message;
  }

  function showFilterNotice(message) {
    if (!filterNotice) return;
    filterNotice.textContent = message || "";
    filterNotice.hidden = !message;
  }

  function fieldValue(field) {
    if (!field) return { text: NOT_LISTED, isState: true };
    if (field.value !== null && field.value !== undefined) {
      return { text: String(field.value), isState: false };
    }
    var label = fieldStateLabels[field.state];
    return { text: label || UNKNOWN_FIELD_STATE, isState: true };
  }

  function disclosureText(view) {
    var state = view && view.row ? view.row.disclosure_state : "";
    return disclosureLabels[state] || UNKNOWN_DISCLOSURE;
  }

  function locatorUrlIsSafe(url) {
    return /^https?:\/\//i.test(String(url || ""));
  }

  function locatorLines(locator) {
    var lines = [];
    if (!locator) return lines;
    var role = roleLabels[locator.document_role];
    if (role) lines.push("来源类型：" + role);
    if (locator.field_path) lines.push("字段：" + locator.field_path);
    if (locator.heading) lines.push("章节：" + locator.heading);
    if (locator.table) {
      var tableText = String(locator.table);
      lines.push(tableText.indexOf("表") !== -1 ? tableText : "表 " + tableText);
    }
    if (locator.row) lines.push("行：" + locator.row);
    if (locator.column) lines.push("列：" + locator.column);
    if (locator.paragraph) lines.push("段落：" + locator.paragraph);
    if (locator.page) lines.push("第 " + locator.page + " 页");
    return lines;
  }

  function locatorLink(locator) {
    return locatorUrlIsSafe(locator && locator.url) ? locator.url : null;
  }

  // 定位渲染：文字定位行 + 有效链接；全部无效时呈现「来源未列示」。
  function renderLocatorInto(container, locator) {
    var lines = locatorLines(locator);
    if (lines.length) {
      var span = document.createElement("span");
      span.className = "kz-evidence-locator__lines";
      span.textContent = lines.join("；");
      container.appendChild(span);
    }
    var url = locatorLink(locator);
    if (url) {
      var link = document.createElement("a");
      link.className = "kz-evidence-locator__link";
      link.href = url;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.textContent = "打开原文";
      if (lines.length) container.appendChild(document.createTextNode("；"));
      container.appendChild(link);
    }
    if (!lines.length && !url) {
      container.textContent = NOT_LISTED;
      container.classList.add("kz-evidence-field__state");
    }
  }

  function appendFieldRow(dl, label, text, isState) {
    var row = document.createElement("div");
    row.className = "kz-evidence-field";
    var dt = document.createElement("dt");
    dt.textContent = label;
    var dd = document.createElement("dd");
    if (isState) dd.classList.add("kz-evidence-field__state");
    dd.textContent = text;
    row.appendChild(dt);
    row.appendChild(dd);
    dl.appendChild(row);
  }

  function appendLocatorRow(dl, label, locator) {
    var row = document.createElement("div");
    row.className = "kz-evidence-field";
    var dt = document.createElement("dt");
    dt.textContent = label;
    var dd = document.createElement("dd");
    dd.className = "kz-evidence-locator";
    renderLocatorInto(dd, locator);
    row.appendChild(dt);
    row.appendChild(dd);
    dl.appendChild(row);
  }

  function appendQuoteRow(dl, label, quote) {
    var row = document.createElement("div");
    row.className = "kz-evidence-field";
    var dt = document.createElement("dt");
    dt.textContent = label;
    var dd = document.createElement("dd");
    dd.className = "kz-evidence-quote";
    dd.textContent = quote;
    row.appendChild(dt);
    row.appendChild(dd);
    dl.appendChild(row);
  }

  function clearChildren(el) {
    while (el.firstChild) el.removeChild(el.firstChild);
  }

  function renderConflictList(container, conflicts) {
    clearChildren(container);
    for (var i = 0; i < conflicts.length; i++) {
      var conflict = conflicts[i];
      var li = document.createElement("li");
      li.className = "kz-evidence-conflict";

      var value = document.createElement("p");
      value.className = "kz-evidence-conflict__value";
      var valueKey = document.createElement("span");
      valueKey.className = "kz-evidence-conflict__key";
      valueKey.textContent = "冲突取值";
      value.appendChild(valueKey);
      value.appendChild(document.createTextNode("：" + conflict.conflicting_value_zh));
      li.appendChild(value);

      var note = document.createElement("p");
      note.className = "kz-evidence-conflict__note";
      var noteKey = document.createElement("span");
      noteKey.className = "kz-evidence-conflict__key";
      noteKey.textContent = "冲突说明";
      note.appendChild(noteKey);
      note.appendChild(document.createTextNode("：" + conflict.conflict_note_zh));
      li.appendChild(note);

      var source = document.createElement("p");
      source.className = "kz-evidence-conflict__source";
      var sourceKey = document.createElement("span");
      sourceKey.className = "kz-evidence-conflict__key";
      sourceKey.textContent = "冲突方来源版本";
      source.appendChild(sourceKey);
      source.appendChild(
        document.createTextNode("：" + conflict.conflicting_source_version_id)
      );
      li.appendChild(source);

      var loc = document.createElement("p");
      loc.className = "kz-evidence-conflict__locator";
      var locKey = document.createElement("span");
      locKey.className = "kz-evidence-conflict__key";
      locKey.textContent = "冲突方定位";
      loc.appendChild(locKey);
      loc.appendChild(document.createTextNode("："));
      renderLocatorInto(loc, conflict.locator);
      li.appendChild(loc);

      container.appendChild(li);
    }
  }

  function renderHistoryList(container, versions) {
    clearChildren(container);
    for (var i = 0; i < versions.length; i++) {
      var version = versions[i];
      var li = document.createElement("li");
      li.className = "kz-evidence-history";

      var source = document.createElement("p");
      source.className = "kz-evidence-history__source";
      var sourceKey = document.createElement("span");
      sourceKey.className = "kz-evidence-conflict__key";
      sourceKey.textContent = "此前来源版本";
      source.appendChild(sourceKey);
      source.appendChild(document.createTextNode("：" + version.source_version_id));
      li.appendChild(source);

      var previous = fieldValue(version.previous_value);
      var prev = document.createElement("p");
      prev.className = "kz-evidence-history__previous";
      var prevKey = document.createElement("span");
      prevKey.className = "kz-evidence-conflict__key";
      prevKey.textContent = "此前取值";
      prev.appendChild(prevKey);
      prev.appendChild(document.createTextNode("：" + previous.text));
      li.appendChild(prev);

      var note = document.createElement("p");
      note.className = "kz-evidence-history__note";
      var noteKey = document.createElement("span");
      noteKey.className = "kz-evidence-conflict__key";
      noteKey.textContent = "取代说明";
      note.appendChild(noteKey);
      note.appendChild(document.createTextNode("：" + version.supersession_note_zh));
      li.appendChild(note);

      var loc = document.createElement("p");
      loc.className = "kz-evidence-history__locator";
      var locKey = document.createElement("span");
      locKey.className = "kz-evidence-conflict__key";
      locKey.textContent = "定位";
      loc.appendChild(locKey);
      loc.appendChild(document.createTextNode("："));
      renderLocatorInto(loc, version.locator);
      li.appendChild(loc);

      container.appendChild(li);
    }
  }

  function renderView(view) {
    viewSubject.textContent = view.product_zh + " · " + view.element_zh;
    clearChildren(viewFields);

    var i;
    for (i = 0; i < GENERAL_FIELDS.length; i++) {
      var spec = GENERAL_FIELDS[i];
      var key = spec[0];
      if (key === "_disclosure") {
        appendFieldRow(viewFields, spec[1], disclosureText(view), true);
      } else if (key === "_locator") {
        appendLocatorRow(viewFields, spec[1], view.locator);
      } else if (key === "_original_text") {
        if (
          view.original_text_status === "provided" &&
          view.original_text !== null &&
          view.original_text !== undefined
        ) {
          appendQuoteRow(viewFields, spec[1], String(view.original_text));
        } else {
          var originalState =
            originalTextLabels[view.original_text_status] || "原文未提供";
          appendFieldRow(viewFields, spec[1], originalState, true);
        }
      } else if (
        key === "product_zh" ||
        key === "trial_zh" ||
        key === "element_zh" ||
        key === "source_version_label_zh"
      ) {
        appendFieldRow(viewFields, spec[1], String(view[key]), false);
      } else {
        var resolved = fieldValue(view[key]);
        appendFieldRow(viewFields, spec[1], resolved.text, resolved.isState);
      }
    }

    var isExtension =
      view.observation_kind === "baseline_observation" ||
      view.observation_kind === "trial_disposition_observation";
    if (isExtension) {
      for (var e = 0; e < EXTENSION_FIELDS.length; e++) {
        var ext = EXTENSION_FIELDS[e];
        if (ext[0] === "_reason_original") {
          if (view.reason_original_text) {
            appendQuoteRow(viewFields, ext[1], String(view.reason_original_text));
          } else {
            appendFieldRow(viewFields, ext[1], "原文未提供", true);
          }
        } else {
          var extValue = fieldValue(view[ext[0]]);
          appendFieldRow(viewFields, ext[1], extValue.text, extValue.isState);
        }
      }
    }

    var conflicts = view.conflicts || [];
    viewConflicts.hidden = conflicts.length === 0;
    if (conflicts.length) renderConflictList(viewConflictList, conflicts);

    var history = view.historical_versions || [];
    viewHistory.hidden = history.length === 0;
    if (history.length) renderHistoryList(viewHistoryList, history);

    updatePinButton();
  }

  function updatePinButton() {
    if (!pinBtn) return;
    var pinned = openRowId !== null && pinnedSet[openRowId] === true;
    pinBtn.setAttribute("aria-pressed", pinned ? "true" : "false");
    pinBtn.textContent = pinned ? "移出对照" : "加入对照";
  }

  function updatePinnedSection() {
    if (!pinnedSection || !compareHost || !pinnedHint) return;
    var count = pinnedOrder.length;
    pinnedSection.hidden = count === 0;
    if (count === 0) {
      compareHost.hidden = true;
      pinnedHint.textContent = "";
      return;
    }
    pinnedHint.textContent = "以下为已固定条目，可并列核对定义、时间点、分母与冲突。";
    renderCompare();
    compareHost.hidden = false;
  }

  function compareConflictCell(view) {
    var conflicts = view.conflicts || [];
    if (!conflicts.length) return "无冲突";
    var text = conflicts.length + " 条冲突";
    if (conflicts[0].conflicting_value_zh) {
      text += "：" + conflicts[0].conflicting_value_zh;
    }
    return text;
  }

  function compareLocatorCell(view) {
    var lines = locatorLines(view.locator);
    if (!lines.length) return NOT_LISTED;
    var text = lines[0];
    if (locatorLink(view.locator)) text += "（可打开原文）";
    return text;
  }

  function compareDifferenceLabels() {
    var compareIds = pinnedOrder.slice();
    if (openRowId !== null && compareIds.indexOf(openRowId) === -1) {
      compareIds.push(openRowId);
    }
    if (compareIds.length < 2) return [];
    var specs = [
      ["element_zh", "指标定义", true],
      ["group_zh", "组别", false],
      ["timepoint", "时间点", false],
      ["unit", "单位", false],
      ["denominator", "分母", false]
    ];
    var different = [];
    for (var s = 0; s < specs.length; s++) {
      var spec = specs[s];
      var values = {};
      for (var p = 0; p < compareIds.length; p++) {
        var view = byRowId[compareIds[p]];
        if (!view) continue;
        var text = spec[2] ? String(view[spec[0]] || "") : fieldValue(view[spec[0]]).text;
        values[text] = true;
      }
      if (Object.keys(values).length > 1) different.push(spec[1]);
    }
    return different;
  }

  function renderCompare() {
    clearChildren(compareHost);
    var differenceLabels = compareDifferenceLabels();
    if (differenceLabels.length) {
      var warning = document.createElement("p");
      warning.className = "kz-evidence-compare__warning";
      warning.textContent =
        differenceLabels.join("、") +
        "存在差异；并列用于核对口径，不代表可以直接比较数值。";
      compareHost.appendChild(warning);
    }
    var table = document.createElement("table");
    table.className = "kz-evidence-compare__table";

    var thead = document.createElement("thead");
    var headRow = document.createElement("tr");
    var corner = document.createElement("th");
    corner.scope = "col";
    corner.className = "kz-evidence-compare__corner";
    corner.textContent = "核对字段";
    headRow.appendChild(corner);

    for (var c = 0; c < pinnedOrder.length; c++) {
      var rowId = pinnedOrder[c];
      var view = byRowId[rowId];
      if (!view) continue;
      var th = document.createElement("th");
      th.scope = "col";
      th.className = "kz-evidence-compare__col";
      th.setAttribute("data-compare-row-id", rowId);

      var subject = document.createElement("span");
      subject.className = "kz-evidence-compare__col-subject";
      subject.textContent = view.product_zh + " · " + view.element_zh;
      th.appendChild(subject);

      var actions = document.createElement("span");
      actions.className = "kz-evidence-compare__col-actions";

      var openBtn = document.createElement("button");
      openBtn.type = "button";
      openBtn.className = "kz-evidence-compare__col-open";
      openBtn.textContent = "查看完整依据";
      (function (targetRowId) {
        openBtn.addEventListener("click", function () {
          openByRowId(targetRowId, openBtn);
        });
      })(rowId);
      actions.appendChild(openBtn);

      var removeBtn = document.createElement("button");
      removeBtn.type = "button";
      removeBtn.className = "kz-evidence-compare__col-remove";
      removeBtn.textContent = "取消固定";
      (function (targetRowId) {
        removeBtn.addEventListener("click", function () {
          unpin(targetRowId);
        });
      })(rowId);
      actions.appendChild(removeBtn);

      th.appendChild(actions);
      headRow.appendChild(th);
    }
    thead.appendChild(headRow);
    table.appendChild(thead);

    var tbody = document.createElement("tbody");
    for (var r = 0; r < COMPARE_FIELDS.length; r++) {
      var spec = COMPARE_FIELDS[r];
      var tr = document.createElement("tr");
      var label = document.createElement("th");
      label.scope = "row";
      label.textContent = spec[1];
      tr.appendChild(label);

      for (var p = 0; p < pinnedOrder.length; p++) {
        var pinnedId = pinnedOrder[p];
        var pinnedView = byRowId[pinnedId];
        var td = document.createElement("td");
        if (!pinnedView) {
          td.textContent = NOT_LISTED;
          tr.appendChild(td);
          continue;
        }
        var key = spec[0];
        if (key === "_disclosure") {
          td.textContent = disclosureText(pinnedView);
          td.classList.add("kz-evidence-field__state");
        } else if (key === "_conflicts") {
          td.textContent = compareConflictCell(pinnedView);
        } else if (key === "_locator") {
          td.textContent = compareLocatorCell(pinnedView);
        } else if (
          key === "product_zh" ||
          key === "trial_zh" ||
          key === "element_zh" ||
          key === "source_version_label_zh"
        ) {
          td.textContent = String(pinnedView[key]);
        } else {
          var value = fieldValue(pinnedView[key]);
          td.textContent = value.text;
          if (value.isState) td.classList.add("kz-evidence-field__state");
        }
        tr.appendChild(td);
      }
      tbody.appendChild(tr);
    }
    table.appendChild(tbody);
    compareHost.appendChild(table);
  }

  function emitChange() {
    var event;
    try {
      event = new CustomEvent("kz-evidence-drawer-change", {
        bubbles: true,
        detail: { openRowId: openRowId, pinnedRowIds: pinnedOrder.slice() }
      });
    } catch (err) {
      event = document.createEvent("CustomEvent");
      event.initCustomEvent("kz-evidence-drawer-change", true, false, {
        openRowId: openRowId,
        pinnedRowIds: pinnedOrder.slice()
      });
    }
    host.dispatchEvent(event);
  }

  function closeResponsiveNavigation() {
    var nav = document.querySelector(".site-header__nav");
    var search = document.querySelector(".site-header__search");
    var toggle = document.getElementById("menu-toggle");
    if (nav) nav.classList.remove("is-open");
    if (search) search.classList.remove("is-open");
    if (toggle) {
      toggle.setAttribute("aria-expanded", "false");
      toggle.setAttribute("aria-label", "打开导航菜单");
    }
  }

  function openByRowId(rowId, triggerEl) {
    closeResponsiveNavigation();
    showFilterNotice("");
    var view = byRowId[String(rowId)];
    if (!view) {
      if (triggerEl) lastTrigger = triggerEl;
      else if (arguments.length < 2) lastTrigger = document.activeElement || null;
      openRowId = null;
      viewSection.hidden = true;
      host.hidden = false;
      panel.classList.add("kz-evidence-drawer__panel--in");
      showStatus("此条数据依据在当前页面数据中不存在或已失效，无法展示。");
      emitChange();
      return false;
    }
    if (triggerEl) {
      if (
        triggerEl.setAttribute &&
        (triggerEl.tabIndex === undefined || triggerEl.tabIndex < 0)
      ) {
        triggerEl.setAttribute("tabindex", "-1");
      }
      lastTrigger = triggerEl;
    } else if (arguments.length < 2) {
      lastTrigger = document.activeElement || null;
    }
    openRowId = String(rowId);
    renderView(view);
    viewSection.hidden = false;
    host.hidden = false;
    panel.classList.add("kz-evidence-drawer__panel--in");
    showStatus("");
    updatePinnedSection();
    emitChange();
    return true;
  }

  function closeInternal(restoreFocus) {
    if (host.hidden) return;
    host.hidden = true;
    panel.classList.remove("kz-evidence-drawer__panel--in");
    openRowId = null;
    showStatus("");
    var target = lastTrigger;
    lastTrigger = null;
    if (
      restoreFocus &&
      target &&
      target.isConnected &&
      typeof target.focus === "function"
    ) {
      target.focus();
    }
    emitChange();
  }

  function close(restoreFocus) {
    closeInternal(restoreFocus !== false);
  }

  function pin(rowId) {
    var key = String(rowId);
    if (!byRowId[key]) {
      showStatus("此条数据依据无法固定：不在当前页面数据中。");
      return false;
    }
    if (pinnedSet[key]) return true;
    pinnedSet[key] = true;
    pinnedOrder.push(key);
    updatePinnedSection();
    updatePinButton();
    emitChange();
    return true;
  }

  function unpin(rowId) {
    var key = String(rowId);
    if (!pinnedSet[key]) return false;
    delete pinnedSet[key];
    var index = pinnedOrder.indexOf(key);
    if (index !== -1) pinnedOrder.splice(index, 1);
    updatePinnedSection();
    updatePinButton();
    emitChange();
    return true;
  }

  function togglePin(rowId) {
    var key = String(rowId);
    if (pinnedSet[key]) {
      unpin(key);
      return false;
    }
    return pin(key);
  }

  function pruneToVisible(visibleRowIds) {
    var visible = {};
    var removedCount = 0;
    for (var i = 0; i < visibleRowIds.length; i++) {
      visible[String(visibleRowIds[i])] = true;
    }
    for (var p = pinnedOrder.length - 1; p >= 0; p--) {
      if (!visible[pinnedOrder[p]]) {
        unpin(pinnedOrder[p]);
        removedCount += 1;
      }
    }
    if (openRowId !== null && !visible[openRowId]) {
      // 打开项已不在当前事实行集：静默关闭，不把焦点还给已隐藏的触发点。
      closeInternal(false);
      showStatus("");
    }
    if (removedCount > 0) {
      var removalMessage =
        "筛选范围已更新：已移除 " +
        String(removedCount) +
        " 条不在当前筛选范围内的固定数据。";
      showFilterNotice(removalMessage);
      if (!host.hidden) showStatus(removalMessage);
    }
  }

  if (closeBtn) {
    closeBtn.addEventListener("click", close);
  }
  if (pinBtn) {
    pinBtn.addEventListener("click", function () {
      if (openRowId !== null) togglePin(openRowId);
    });
  }

  document.addEventListener(
    "keydown",
    function (e) {
      if (e.key !== "Escape" && e.key !== "Esc") return;
      if (host.hidden) return;
      e.preventDefault();
      if (e.stopPropagation) e.stopPropagation();
      close();
    },
    true
  );

  window.__EVIDENCE_DRAWER__ = {
    openByRowId: openByRowId,
    close: close,
    pin: pin,
    unpin: unpin,
    togglePin: togglePin,
    pruneToVisible: pruneToVisible,
    isOpen: function () {
      return !host.hidden;
    },
    getOpenRowId: function () {
      return openRowId;
    },
    getPinnedRowIds: function () {
      return pinnedOrder.slice();
    },
    isPinned: function (rowId) {
      return pinnedSet[String(rowId)] === true;
    },
    hasView: function (rowId) {
      return byRowId[String(rowId)] !== undefined;
    },
    listRowIds: function () {
      return Object.keys(byRowId);
    }
  };

  if (
    window.__PORTAL_FILTER__ &&
    typeof window.__PORTAL_FILTER__.restoreEvidence === "function"
  ) {
    window.__PORTAL_FILTER__.restoreEvidence();
  }
})();
