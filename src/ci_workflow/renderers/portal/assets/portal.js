/**
 * Portal JS — global search, grouped nav, mobile toggle, keyboard support.
 *
 * Zero remote dependencies; works from file://.
 * Consumes window.__SEARCH_INDEX__ (inline and/or search-index.js).
 */
(function () {
  "use strict";

  var searchInput = document.getElementById("global-search-input");
  var searchResults = document.getElementById("global-search-results");
  var searchIndex = window.__SEARCH_INDEX__ || [];
  var focusedIdx = -1;

  function getQuery() {
    return ((searchInput && searchInput.value) || "").trim().toLowerCase();
  }

  function scoreEntry(query, entry) {
    var score = 0;
    var titleLower = String(entry.title || "").toLowerCase();
    if (titleLower.indexOf(query) !== -1) {
      score += 100;
    }
    var keywords = entry.keywords || [];
    for (var i = 0; i < keywords.length; i += 1) {
      var kw = String(keywords[i] || "").toLowerCase();
      if (kw.indexOf(query) !== -1 || query.indexOf(kw) !== -1) {
        score += 10;
      }
    }
    return score;
  }

  function search(query) {
    if (!query) {
      return searchIndex.slice();
    }
    var results = [];
    for (var i = 0; i < searchIndex.length; i += 1) {
      var score = scoreEntry(query, searchIndex[i]);
      if (score > 0) {
        results.push({ entry: searchIndex[i], score: score });
      }
    }
    results.sort(function (a, b) {
      return b.score - a.score;
    });
    return results.map(function (item) {
      return item.entry;
    });
  }

  function escapeHtml(text) {
    return String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function highlightMatch(text, query) {
    var safe = escapeHtml(text);
    if (!query) {
      return safe;
    }
    var lower = text.toLowerCase();
    var idx = lower.indexOf(query.toLowerCase());
    if (idx === -1) {
      return safe;
    }
    var before = escapeHtml(text.substring(0, idx));
    var match = escapeHtml(text.substring(idx, idx + query.length));
    var after = escapeHtml(text.substring(idx + query.length));
    return (
      before +
      '<span class="site-header__search-result-mark">' +
      match +
      "</span>" +
      after
    );
  }

  function showResults(results, query) {
    if (!searchResults) {
      return;
    }
    searchResults.innerHTML = "";
    focusedIdx = -1;
    if (results.length === 0) {
      var empty = document.createElement("div");
      empty.className = "site-header__search-empty";
      empty.setAttribute("role", "status");
      empty.textContent = "未找到匹配页面或数据";
      searchResults.appendChild(empty);
      searchResults.hidden = false;
      return;
    }
    for (var i = 0; i < results.length; i += 1) {
      var entry = results[i];
      var anchor = document.createElement("a");
      anchor.className = "site-header__search-result";
      anchor.href = entry.slug + ".html";
      anchor.setAttribute("role", "option");
      anchor.setAttribute("data-index", String(i));
      anchor.innerHTML = highlightMatch(entry.title, query);
      searchResults.appendChild(anchor);
    }
    searchResults.hidden = false;
  }

  function updateFocused(delta) {
    var items = searchResults
      ? searchResults.querySelectorAll(".site-header__search-result")
      : [];
    if (items.length === 0) {
      return;
    }
    if (focusedIdx >= 0 && focusedIdx < items.length) {
      items[focusedIdx].classList.remove("site-header__search-result--focused");
    }
    focusedIdx += delta;
    if (focusedIdx < 0) {
      focusedIdx = items.length - 1;
    }
    if (focusedIdx >= items.length) {
      focusedIdx = 0;
    }
    items[focusedIdx].classList.add("site-header__search-result--focused");
    items[focusedIdx].scrollIntoView({ block: "nearest" });
  }

  function activateFocused() {
    var items = searchResults
      ? searchResults.querySelectorAll(".site-header__search-result")
      : [];
    if (focusedIdx >= 0 && focusedIdx < items.length) {
      window.location.href = items[focusedIdx].href;
    } else if (items.length > 0) {
      window.location.href = items[0].href;
    }
  }

  if (searchInput) {
    searchInput.addEventListener("input", function () {
      var query = getQuery();
      showResults(search(query), query);
    });

    searchInput.addEventListener("keydown", function (event) {
      if (!searchResults || searchResults.hidden) {
        if (event.key === "Enter") {
          var query = getQuery();
          var results = search(query);
          if (results.length > 0) {
            event.preventDefault();
            window.location.href = results[0].slug + ".html";
          }
        }
        return;
      }
      if (event.key === "ArrowDown") {
        event.preventDefault();
        updateFocused(1);
      } else if (event.key === "ArrowUp") {
        event.preventDefault();
        updateFocused(-1);
      } else if (event.key === "Enter") {
        event.preventDefault();
        activateFocused();
      } else if (event.key === "Escape") {
        searchResults.hidden = true;
        focusedIdx = -1;
      }
    });
  }

  function closeAllNavGroups(except) {
    var groups = document.querySelectorAll(".site-nav-group");
    for (var i = 0; i < groups.length; i += 1) {
      if (except && groups[i] === except) {
        continue;
      }
      var trigger = groups[i].querySelector(".site-nav-group__trigger");
      var panel = groups[i].querySelector(".site-nav-group__panel");
      if (trigger) {
        trigger.setAttribute("aria-expanded", "false");
      }
      if (panel) {
        panel.hidden = true;
      }
    }
  }

  var navGroups = document.querySelectorAll(".site-nav-group");
  for (var g = 0; g < navGroups.length; g += 1) {
    (function (group) {
      var trigger = group.querySelector(".site-nav-group__trigger");
      var panel = group.querySelector(".site-nav-group__panel");
      if (!trigger || !panel) {
        return;
      }
      trigger.addEventListener("click", function () {
        var open = trigger.getAttribute("aria-expanded") === "true";
        closeAllNavGroups(group);
        trigger.setAttribute("aria-expanded", String(!open));
        panel.hidden = open;
        if (!open) {
          var first = panel.querySelector(".site-nav-group__link");
          if (first) {
            first.focus();
          }
        }
      });
      trigger.addEventListener("keydown", function (event) {
        if (event.key === "ArrowDown" || event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          closeAllNavGroups(group);
          trigger.setAttribute("aria-expanded", "true");
          panel.hidden = false;
          var first = panel.querySelector(".site-nav-group__link");
          if (first) {
            first.focus();
          }
        } else if (event.key === "Escape") {
          closeAllNavGroups();
          trigger.focus();
        }
      });
      panel.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
          event.preventDefault();
          closeAllNavGroups();
          trigger.focus();
        }
      });
    })(navGroups[g]);
  }

  document.addEventListener("click", function (event) {
    var target = event.target;
    if (
      searchResults &&
      !searchResults.contains(target) &&
      target !== searchInput
    ) {
      searchResults.hidden = true;
      focusedIdx = -1;
    }
    if (!(target instanceof Element) || !target.closest(".site-nav-group")) {
      closeAllNavGroups();
    }
  });

  var menuToggle = document.getElementById("menu-toggle");
  var navEl = document.querySelector(".site-header__nav");
  var searchWrap = document.querySelector(".site-header__search");

  if (menuToggle && navEl) {
    menuToggle.addEventListener("click", function () {
      var isOpen = navEl.classList.toggle("is-open");
      menuToggle.setAttribute("aria-expanded", String(isOpen));
      menuToggle.setAttribute(
        "aria-label",
        isOpen ? "关闭导航菜单" : "打开导航菜单"
      );
      if (searchWrap) {
        searchWrap.classList.toggle("is-open", isOpen);
      }
    });
  }

  var prefersReducedMotion = window.matchMedia(
    "(prefers-reduced-motion: reduce)"
  );
  if (prefersReducedMotion && prefersReducedMotion.matches) {
    var countEls = document.querySelectorAll("[data-countup]");
    for (var i = 0; i < countEls.length; i += 1) {
      var target = countEls[i].getAttribute("data-countup");
      if (target) {
        countEls[i].textContent = target;
      }
    }
  }

  /* ── Filter Panel ── */
  var FILTER_SEP = "~";
  var URL_SIZE_LIMIT = 2048;
  var filterPanel = document.getElementById("kz-filter-panel");
  var filterEntry = document.getElementById("kz-filter-entry");
  var filterChips = document.getElementById("kz-filter-chips");
  var filterSummary = document.getElementById("kz-filter-summary");
  var filterRowCount = document.getElementById("kz-filter-row-count");
  var filterEmpty = document.getElementById("kz-filter-empty");
  var filterEmptyRestrictions = document.getElementById(
    "kz-filter-empty-restrictions"
  );
  var filterLocalHint = document.getElementById("kz-filter-local-hint");
  var filterRestoreError = document.getElementById("kz-filter-restore-error");
  var filterClose = document.getElementById("kz-filter-close");
  var filterResetPage = document.getElementById("kz-filter-reset-page");
  var filterResetModules = document.querySelectorAll(".kz-filter-reset-module");
  var filterItems = document.querySelectorAll(".kz-filter-item[data-dim][data-val]");
  var syntheticRows = window.__FILTER_ROWS__ || [];
  var pageFilters = {};
  var moduleFilters = {};
  var filterVersion = "v1";
  var currentPageId =
    (filterPanel && filterPanel.getAttribute("data-page-id")) || "";
  var currentModuleId =
    (filterPanel && filterPanel.getAttribute("data-module-id")) || "";
  var lastFocusEl = null;
  var pageAllow = {};
  var moduleAllow = {};
  var moduleLabels = {};
  var sortField = null;
  var sortDirection = "asc";
  var anchorTrialId = null;
  var evidenceIds = [];
  var evidenceOpenId = null;
  var paginationPage = 1;
  var applyingFromUrl = false;
  var syncingFilter = false;

  function enc(value) {
    return encodeURIComponent(String(value)).replace(/[!'()*]/g, function (c) {
      return "%" + c.charCodeAt(0).toString(16).toUpperCase();
    }).replace(/~/g, "%7E");
  }

  function dec(value) {
    try {
      return decodeURIComponent(String(value));
    } catch (err) {
      throw new Error("decode");
    }
  }

  function utf8ByteLength(str) {
    if (typeof TextEncoder !== "undefined") {
      return new TextEncoder().encode(str).length;
    }
    return unescape(encodeURIComponent(str)).length;
  }

  function buildAllowlists() {
    pageAllow = {};
    moduleAllow = {};
    moduleLabels = {};
    var moduleSections = document.querySelectorAll(
      '.kz-filter-scope[data-scope="module"][data-module-id]'
    );
    for (var si = 0; si < moduleSections.length; si++) {
      var sectionId = moduleSections[si].getAttribute("data-module-id") || "";
      var sectionLabel = moduleSections[si].getAttribute("data-module-label") || "";
      if (sectionId && sectionLabel) moduleLabels[sectionId] = sectionLabel;
    }
    for (var i = 0; i < filterItems.length; i++) {
      var item = filterItems[i];
      if (item.getAttribute("aria-disabled") === "true") continue;
      var dim = item.getAttribute("data-dim");
      var val = item.getAttribute("data-val");
      var scope = item.getAttribute("data-scope") || "page";
      var mid = item.getAttribute("data-module-id") || "";
      if (!dim || !val) continue;
      if (scope === "module") {
        if (!moduleAllow[mid]) moduleAllow[mid] = {};
        if (!moduleAllow[mid][dim]) moduleAllow[mid][dim] = {};
        moduleAllow[mid][dim][val] = true;
      } else {
        if (!pageAllow[dim]) pageAllow[dim] = {};
        pageAllow[dim][val] = true;
      }
    }
  }

  function getActiveBucket(scope, moduleId) {
    if (scope === "module") {
      var mid = moduleId || currentModuleId || "default";
      if (!moduleFilters[mid]) moduleFilters[mid] = {};
      return moduleFilters[mid];
    }
    return pageFilters;
  }

  function encodeSelected(map) {
    var keys = Object.keys(map).sort();
    var parts = [];
    for (var k = 0; k < keys.length; k++) {
      var key = keys[k];
      var vals = map[key];
      if (!vals || vals.length === 0) continue;
      var encodedVals = vals.slice().sort().map(enc).join(",");
      parts.push(enc(key) + ":" + encodedVals);
    }
    return parts.join("|");
  }

  function decodeSelectedStrict(data, allowMap, scopeLabel) {
    var result = {};
    if (!data) return result;
    var groups = data.split("|");
    for (var g = 0; g < groups.length; g++) {
      var colonIdx = groups[g].indexOf(":");
      if (colonIdx === -1) throw new Error("format");
      var dim = dec(groups[g].substring(0, colonIdx));
      if (!dim) throw new Error("empty-dim");
      if (Object.prototype.hasOwnProperty.call(result, dim)) {
        throw new Error("dup-dim");
      }
      if (!allowMap || !allowMap[dim]) throw new Error("unknown-dim");
      var rawVals = groups[g].substring(colonIdx + 1).split(",");
      var cleaned = [];
      var seen = {};
      for (var v = 0; v < rawVals.length; v++) {
        if (!rawVals[v]) continue;
        var val = dec(rawVals[v]);
        if (seen[val]) throw new Error("dup-val");
        seen[val] = true;
        if (!allowMap[dim][val]) throw new Error("unknown-val");
        cleaned.push(val);
      }
      if (cleaned.length) result[dim] = cleaned;
    }
    return result;
  }

  function countFilters(map) {
    var total = 0;
    var keys = Object.keys(map);
    for (var i = 0; i < keys.length; i++) {
      var vals = map[keys[i]];
      if (vals) total += vals.length;
    }
    return total;
  }

  function buildHash() {
    var hash = "v1";
    if (currentPageId) hash += FILTER_SEP + "pid=" + enc(currentPageId);
    var pageSel = encodeSelected(pageFilters);
    if (pageSel) hash += FILTER_SEP + "ps=" + pageSel;
    var mods = Object.keys(moduleFilters).sort();
    for (var i = 0; i < mods.length; i++) {
      var mid = mods[i];
      var modSel = encodeSelected(moduleFilters[mid] || {});
      if (!modSel && countFilters(moduleFilters[mid] || {}) === 0) continue;
      hash += FILTER_SEP + "m=" + enc(mid);
      if (modSel) hash += FILTER_SEP + "ms=" + modSel;
    }
    if (sortField) {
      hash += FILTER_SEP + "s=" + enc(sortField) + ":" + enc(sortDirection || "asc");
    }
    if (anchorTrialId) {
      hash += FILTER_SEP + "a=" + enc(anchorTrialId);
    }
    if (evidenceOpenId) {
      hash += FILTER_SEP + "eo=" + enc(evidenceOpenId);
    }
    if (evidenceIds && evidenceIds.length) {
      hash +=
        FILTER_SEP +
        "e=" +
        evidenceIds
          .slice()
          .sort()
          .map(enc)
          .join(",");
    }
    if (paginationPage && paginationPage !== 1) {
      hash += FILTER_SEP + "pg=" + String(paginationPage);
    }
    return hash;
  }

  function showRestoreError() {
    if (filterRestoreError) {
      filterRestoreError.hidden = false;
      filterRestoreError.textContent = "无法恢复此筛选网址";
    }
  }

  function hideRestoreError() {
    if (filterRestoreError) filterRestoreError.hidden = true;
  }

  function writeFilterToHash(options) {
    options = options || {};
    if (applyingFromUrl && !options.replace) return false;
    var hash = buildHash();
    if (utf8ByteLength(hash) > URL_SIZE_LIMIT) {
      if (filterLocalHint) {
        filterLocalHint.hidden = false;
        filterLocalHint.textContent = "当前选择过多，请保存为本地视图";
      }
      return false;
    }
    if (filterLocalHint) filterLocalHint.hidden = true;
    var next = "#" + hash;
    if (options.replace) {
      history.replaceState({ filterHash: hash }, "", next);
    } else {
      history.pushState({ filterHash: hash }, "", next);
    }
    return true;
  }

  function parseHash(hash) {
    var parts = hash.split(FILTER_SEP);
    if (!parts.length || parts[0] !== "v1") throw new Error("version");
    var pageId = null;
    var pageMap = {};
    var modMaps = {};
    var seenMods = {};
    var lastModule = null;
    var sawPs = false;
    var nextSortField = null;
    var nextSortDir = "asc";
    var nextAnchor = null;
    var nextEvidence = [];
    var nextEvidenceOpen = null;
    var nextPage = 1;
    var sawSort = false;
    var sawAnchor = false;
    var sawEvidence = false;
    var sawEvidenceOpen = false;
    var sawPg = false;
    for (var i = 1; i < parts.length; i++) {
      var seg = parts[i];
      if (seg.indexOf("pid=") === 0) {
        if (pageId !== null) throw new Error("dup-pid");
        pageId = dec(seg.substring(4));
      } else if (seg.indexOf("ps=") === 0) {
        if (sawPs) throw new Error("dup-ps");
        sawPs = true;
        pageMap = decodeSelectedStrict(seg.substring(3), pageAllow, "page");
      } else if (seg.indexOf("m=") === 0) {
        lastModule = dec(seg.substring(2));
        if (!lastModule) throw new Error("empty-module");
        if (seenMods[lastModule]) throw new Error("dup-module");
        seenMods[lastModule] = true;
        if (Object.keys(moduleAllow).length && !moduleAllow[lastModule]) {
          throw new Error("unknown-module");
        }
        if (!modMaps[lastModule]) modMaps[lastModule] = {};
      } else if (seg.indexOf("ms=") === 0) {
        if (!lastModule) throw new Error("ms-without-m");
        if (countFilters(modMaps[lastModule] || {})) throw new Error("dup-ms");
        var allow = moduleAllow[lastModule] || {};
        modMaps[lastModule] = decodeSelectedStrict(seg.substring(3), allow, "module");
      } else if (seg.indexOf("s=") === 0) {
        if (sawSort) throw new Error("dup-sort");
        sawSort = true;
        var sortPart = seg.substring(2);
        var colon = sortPart.indexOf(":");
        if (colon === -1) throw new Error("bad-sort");
        nextSortField = dec(sortPart.substring(0, colon));
        nextSortDir = dec(sortPart.substring(colon + 1));
        if (!nextSortField) throw new Error("bad-sort");
        if (nextSortDir !== "asc" && nextSortDir !== "desc") {
          throw new Error("bad-sort-dir");
        }
      } else if (seg.indexOf("a=") === 0) {
        if (sawAnchor) throw new Error("dup-anchor");
        sawAnchor = true;
        nextAnchor = dec(seg.substring(2));
        if (!nextAnchor) throw new Error("bad-anchor");
      } else if (seg.indexOf("eo=") === 0) {
        if (sawEvidenceOpen) throw new Error("dup-evidence-open");
        sawEvidenceOpen = true;
        nextEvidenceOpen = dec(seg.substring(3));
        if (!nextEvidenceOpen) throw new Error("bad-evidence-open");
      } else if (seg.indexOf("e=") === 0) {
        if (sawEvidence) throw new Error("dup-evidence");
        sawEvidence = true;
        var rawE = seg.substring(2).split(",");
        var seenE = {};
        nextEvidence = [];
        for (var ei = 0; ei < rawE.length; ei++) {
          if (!rawE[ei]) continue;
          var eid = dec(rawE[ei]);
          if (seenE[eid]) throw new Error("dup-evidence-id");
          seenE[eid] = true;
          nextEvidence.push(eid);
        }
        nextEvidence.sort();
      } else if (seg.indexOf("pg=") === 0) {
        if (sawPg) throw new Error("dup-pg");
        sawPg = true;
        nextPage = parseInt(seg.substring(3), 10);
        if (!nextPage || nextPage < 1 || String(nextPage) !== seg.substring(3)) {
          throw new Error("bad-pg");
        }
      } else if (seg) {
        throw new Error("unknown-seg");
      }
    }
    if (!pageId) throw new Error("missing-pid");
    if (pageId !== currentPageId) throw new Error("pid-mismatch");
    return {
      version: "v1",
      pageId: pageId,
      pageFilters: pageMap,
      moduleFilters: modMaps,
      sortField: nextSortField,
      sortDirection: nextSortDir,
      anchorTrialId: nextAnchor,
      evidenceIds: nextEvidence,
      evidenceOpenId: nextEvidenceOpen,
      paginationPage: nextPage
    };
  }

  function collectVisibleRowIds() {
    var ids = [];
    var seen = {};
    var nodes = document.querySelectorAll("[data-filter-row-id]");
    for (var i = 0; i < nodes.length; i++) {
      if (nodes[i].style.display === "none") continue;
      var id = nodes[i].getAttribute("data-filter-row-id");
      if (!id || seen[id]) continue;
      seen[id] = true;
      ids.push(id);
    }
    return ids;
  }

  function syncEvidenceVarsFromDrawer() {
    var api = window.__EVIDENCE_DRAWER__;
    if (!api) return;
    evidenceOpenId = api.getOpenRowId();
    evidenceIds = api.getPinnedRowIds() || [];
  }

  function knownEvidenceIdSet() {
    var set = {};
    var api = window.__EVIDENCE_DRAWER__;
    if (api && typeof api.listRowIds === "function") {
      var listed = api.listRowIds() || [];
      for (var i = 0; i < listed.length; i++) set[String(listed[i])] = true;
      return set;
    }
    var views = window.__EVIDENCE_VIEWS__ || [];
    for (var j = 0; j < views.length; j++) {
      if (views[j] && views[j].row && views[j].row.row_id) {
        set[String(views[j].row.row_id)] = true;
      }
    }
    return set;
  }

  function applyEvidenceFromHash() {
    var api = window.__EVIDENCE_DRAWER__;
    var known = knownEvidenceIdSet();
    var hasCatalog = Object.keys(known).length > 0;
    var visibleNodes = document.querySelectorAll("[data-filter-row-id]");
    var visible = {};
    var restrictVisible = visibleNodes.length > 0;
    if (restrictVisible) {
      var visList = collectVisibleRowIds();
      for (var v = 0; v < visList.length; v++) visible[visList[v]] = true;
    }
    function acceptEvidenceId(id) {
      if (!id) return false;
      if (hasCatalog && !known[id]) return false;
      if (api && typeof api.hasView === "function" && !api.hasView(id)) return false;
      // 无数据依据目录时，e= 是既有全局片段选择，不得按表格行可见性丢弃。
      if (hasCatalog && restrictVisible && !visible[id]) return false;
      return true;
    }
    var dropped = false;
    var nextPins = [];
    for (var i = 0; i < evidenceIds.length; i++) {
      var pid = evidenceIds[i];
      if (!acceptEvidenceId(pid)) {
        dropped = true;
        continue;
      }
      nextPins.push(pid);
    }
    var nextOpen = evidenceOpenId;
    if (nextOpen && !acceptEvidenceId(nextOpen)) {
      nextOpen = null;
      dropped = true;
    }
    if (api) {
      var currentPins = api.getPinnedRowIds() || [];
      var p;
      for (p = 0; p < currentPins.length; p++) {
        if (nextPins.indexOf(currentPins[p]) === -1) api.unpin(currentPins[p]);
      }
      for (p = 0; p < nextPins.length; p++) {
        if (!api.isPinned(nextPins[p])) api.pin(nextPins[p]);
      }
      if (nextOpen) {
        api.openByRowId(nextOpen, null);
      } else if (api.isOpen()) {
        api.close(false);
      }
    }
    evidenceIds = nextPins;
    evidenceOpenId = nextOpen;
    return dropped;
  }

  function restoreEvidenceFromUrl() {
    applyingFromUrl = true;
    var dropped = false;
    try {
      dropped = applyEvidenceFromHash();
      if (dropped) writeFilterToHash({ replace: true });
    } finally {
      applyingFromUrl = false;
    }
    return dropped;
  }

  function readFilterFromHash() {
    var hash = window.location.hash.replace(/^#\/?/, "");
    applyingFromUrl = true;
    try {
      if (!hash) {
        pageFilters = {};
        moduleFilters = {};
        sortField = null;
        sortDirection = "asc";
        anchorTrialId = null;
        evidenceIds = [];
        evidenceOpenId = null;
        paginationPage = 1;
        hideRestoreError();
        renderChips();
        filterVisibleRows();
        applyEvidenceFromHash();
        return;
      }
      try {
        var parsed = parseHash(hash);
        hideRestoreError();
        filterVersion = "v1";
        currentPageId = parsed.pageId;
        pageFilters = parsed.pageFilters;
        moduleFilters = parsed.moduleFilters;
        sortField = parsed.sortField;
        sortDirection = parsed.sortDirection || "asc";
        anchorTrialId = parsed.anchorTrialId;
        evidenceIds = parsed.evidenceIds || [];
        evidenceOpenId = parsed.evidenceOpenId || null;
        paginationPage = parsed.paginationPage || 1;
        renderChips();
        filterVisibleRows();
        var dropped = applyEvidenceFromHash();
        applyingFromUrl = false;
        if (dropped) writeFilterToHash({ replace: true });
      } catch (err) {
        showRestoreError();
        // keep prior UI state; do not rewrite hash
      }
    } finally {
      applyingFromUrl = false;
    }
  }

  function getDimLabel(dimId) {
    var el = document.querySelector('.kz-filter-item[data-dim="' + dimId + '"]');
    if (el) {
      var group = el.closest(".kz-filter-group");
      if (group) {
        var titleEl = group.querySelector(".kz-filter-group__title");
        if (titleEl) return titleEl.textContent.replace(/\s+/g, " ").trim();
      }
    }
    return dimId;
  }

  function getValLabel(dimId, valId) {
    var el = document.querySelector(
      '.kz-filter-item[data-dim="' + dimId + '"][data-val="' + valId + '"]'
    );
    if (el) return el.textContent.replace(/^[✓\s]+/, "").trim();
    return valId;
  }

  function appendChipsForMap(map, scopeLabel, moduleId) {
    var keys = Object.keys(map).sort();
    for (var k = 0; k < keys.length; k++) {
      var dim = keys[k];
      var vals = map[dim];
      if (!vals) continue;
      for (var v = 0; v < vals.length; v++) {
        var chip = document.createElement("span");
        chip.className = "kz-filter-chip";
        var scope = moduleId ? "module" : "page";
        chip.setAttribute("data-scope", scope);
        var dimEl = document.createElement("span");
        dimEl.className = "kz-filter-chip__label";
        dimEl.textContent = scopeLabel + " · " + getDimLabel(dim) + "：";
        var valEl = document.createElement("span");
        valEl.className = "kz-filter-chip__value";
        valEl.textContent = getValLabel(dim, vals[v]);
        var removeBtn = document.createElement("button");
        removeBtn.className = "kz-filter-chip__remove";
        removeBtn.textContent = "×";
        removeBtn.setAttribute(
          "aria-label",
          "移除筛选：" + getValLabel(dim, vals[v])
        );
        removeBtn.setAttribute("data-dim", dim);
        removeBtn.setAttribute("data-val", vals[v]);
        removeBtn.setAttribute("data-scope", scope);
        removeBtn.setAttribute("data-module-id", moduleId || "");
        removeBtn.addEventListener("click", function () {
          removeFilter(
            this.getAttribute("data-scope"),
            this.getAttribute("data-module-id"),
            this.getAttribute("data-dim"),
            this.getAttribute("data-val")
          );
        });
        chip.appendChild(dimEl);
        chip.appendChild(valEl);
        chip.appendChild(removeBtn);
        filterChips.appendChild(chip);
      }
    }
  }

  function renderChips() {
    if (!filterChips) return;
    filterChips.innerHTML = "";
    appendChipsForMap(pageFilters, "整份报告", "");
    var mods = Object.keys(moduleFilters).sort();
    for (var i = 0; i < mods.length; i++) {
      appendChipsForMap(
        moduleFilters[mods[i]],
        moduleLabels[mods[i]] || "当前数据",
        mods[i]
      );
    }
    var total = countFilters(pageFilters);
    for (var j = 0; j < mods.length; j++) {
      total += countFilters(moduleFilters[mods[j]] || {});
    }
    if (filterSummary) {
      filterSummary.textContent =
        total > 0 ? "已选 " + total + " 项" : "无筛选条件";
    }
    if (filterEntry) {
      var countEl = filterEntry.querySelector(".kz-filter-entry__count");
      if (countEl) {
        countEl.textContent = String(total);
        countEl.style.display = total > 0 ? "" : "none";
      }
      filterEntry.setAttribute(
        "aria-expanded",
        filterPanel && filterPanel.hasAttribute("open") ? "true" : "false"
      );
    }
  }

  function removeFilter(scope, moduleId, dimId, valId) {
    var bucket = getActiveBucket(scope, moduleId);
    if (!bucket[dimId]) return;
    bucket[dimId] = bucket[dimId].filter(function (v) {
      return v !== valId;
    });
    if (bucket[dimId].length === 0) delete bucket[dimId];
    syncCheckboxes();
    renderChips();
    filterVisibleRows();
    writeFilterToHash();
  }

  function syncCheckboxes() {
    for (var i = 0; i < filterItems.length; i++) {
      var item = filterItems[i];
      if (item.getAttribute("aria-disabled") === "true") continue;
      var dim = item.getAttribute("data-dim");
      var val = item.getAttribute("data-val");
      var scope = item.getAttribute("data-scope") || "page";
      var mid = item.getAttribute("data-module-id") || "";
      var bucket = getActiveBucket(scope, mid);
      var selected = bucket[dim] && bucket[dim].indexOf(val) !== -1;
      item.classList.toggle("kz-filter-item--selected", !!selected);
      var check = item.querySelector(".kz-filter-item__check");
      if (check) check.textContent = selected ? "✓" : "";
      item.setAttribute("aria-checked", String(!!selected));
    }
  }

  function mapMatches(map, row) {
    var keys = Object.keys(map);
    for (var k = 0; k < keys.length; k++) {
      var dim = keys[k];
      var vals = map[dim];
      if (!vals || !vals.length) continue;
      var rowVal = row[dim];
      if (!rowVal || vals.indexOf(rowVal) === -1) return false;
    }
    return true;
  }

  function rowMatches(row) {
    if (!mapMatches(pageFilters, row)) return false;
    var rowModule = row.module_id || "";
    if (rowModule && moduleFilters[rowModule]) {
      if (!mapMatches(moduleFilters[rowModule], row)) return false;
    }
    // Module filters for other modules do not affect this row
    return true;
  }

  function listRestrictionLines() {
    var lines = [];
    var pageKeys = Object.keys(pageFilters).sort();
    for (var i = 0; i < pageKeys.length; i++) {
      var dim = pageKeys[i];
      var vals = pageFilters[dim] || [];
      var labels = vals.map(function (v) {
        return getValLabel(dim, v);
      });
      if (labels.length) {
        lines.push("整份报告 · " + getDimLabel(dim) + "：" + labels.join("、"));
      }
    }
    var mods = Object.keys(moduleFilters).sort();
    for (var j = 0; j < mods.length; j++) {
      var mmap = moduleFilters[mods[j]] || {};
      var mkeys = Object.keys(mmap).sort();
      for (var k = 0; k < mkeys.length; k++) {
        var mdim = mkeys[k];
        var mvals = mmap[mdim] || [];
        var mlabels = mvals.map(function (v) {
          return getValLabel(mdim, v);
        });
        if (mlabels.length) {
          lines.push(
            (moduleLabels[mods[j]] || "当前数据") + " · " +
            getDimLabel(mdim) + "：" + mlabels.join("、")
          );
        }
      }
    }
    return lines;
  }

  function filterVisibleRows() {
    var count = 0;
    for (var r = 0; r < syntheticRows.length; r++) {
      var row = syntheticRows[r];
      var visible = rowMatches(row);
      var rowEls = document.querySelectorAll(
        '[data-filter-row-id="' + row.id + '"]'
      );
      var rowEl = document.getElementById("filter-row-" + row.id);
      if (rowEl && rowEls.length === 0) {
        rowEl.style.display = visible ? "" : "none";
      }
      for (var re = 0; re < rowEls.length; re++) {
        rowEls[re].style.display = visible ? "" : "none";
      }
      if (visible) count++;
    }
    if (filterRowCount) {
      filterRowCount.textContent = "匹配 " + count + " 项结果";
    }
    var hasFilters =
      countFilters(pageFilters) > 0 ||
      Object.keys(moduleFilters).some(function (mid) {
        return countFilters(moduleFilters[mid] || {}) > 0;
      });
    if (filterEmpty) {
      var showEmpty = hasFilters && count === 0;
      filterEmpty.style.display = showEmpty ? "block" : "none";
      if (filterPanel) {
        filterPanel.classList.toggle("kz-filter-panel--inflow", showEmpty);
      }
      if (filterEmptyRestrictions) {
        var lines = listRestrictionLines();
        filterEmptyRestrictions.innerHTML = "";
        for (var i = 0; i < lines.length; i++) {
          var p = document.createElement("p");
          p.textContent = lines[i];
          filterEmptyRestrictions.appendChild(p);
        }
      }
    }
    var rowTable = document.getElementById("kz-filter-row-table");
    if (rowTable) {
      rowTable.style.display = count === 0 && hasFilters ? "none" : "";
    }
    if (
      window.__CHART_SYNC__ &&
      typeof window.__CHART_SYNC__.syncWithFilter === "function"
    ) {
      window.__CHART_SYNC__.syncWithFilter();
    }
    if (!applyingFromUrl && window.__EVIDENCE_DRAWER__) {
      var visibleIds = collectVisibleRowIds();
      if (visibleIds.length || document.querySelectorAll("[data-filter-row-id]").length) {
        syncingFilter = true;
        try {
          window.__EVIDENCE_DRAWER__.pruneToVisible(visibleIds);
          syncEvidenceVarsFromDrawer();
        } finally {
          syncingFilter = false;
        }
      }
    }
  }

  function resetPageFilters() {
    pageFilters = {};
    syncCheckboxes();
    renderChips();
    filterVisibleRows();
    writeFilterToHash();
  }

  function resetModuleFilters(moduleId) {
    var mid = moduleId || currentModuleId;
    if (mid && moduleFilters[mid]) {
      moduleFilters[mid] = {};
    } else if (!mid) {
      moduleFilters = {};
    }
    syncCheckboxes();
    renderChips();
    filterVisibleRows();
    writeFilterToHash();
  }

  function openPanel() {
    if (!filterPanel) return;
    lastFocusEl = document.activeElement;
    filterPanel.setAttribute("open", "");
    if (filterEntry) filterEntry.setAttribute("aria-expanded", "true");
  }

  function closePanel() {
    if (!filterPanel) return;
    filterPanel.removeAttribute("open");
    if (filterEntry) filterEntry.setAttribute("aria-expanded", "false");
    if (
      window.__CHART_SYNC__ &&
      typeof window.__CHART_SYNC__.clearSelection === "function"
    ) {
      window.__CHART_SYNC__.clearSelection();
    }
    if (lastFocusEl && typeof lastFocusEl.focus === "function") {
      lastFocusEl.focus();
    } else if (filterEntry) {
      filterEntry.focus();
    }
  }

  if (filterEntry) {
    filterEntry.addEventListener("click", function () {
      if (!filterPanel) return;
      if (filterPanel.hasAttribute("open")) closePanel();
      else openPanel();
    });
    filterEntry.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        filterEntry.click();
      }
    });
  }

  if (filterClose) {
    filterClose.addEventListener("click", function () {
      closePanel();
    });
  }

  document.addEventListener("keydown", function (e) {
    if (e.key !== "Escape" && e.key !== "Esc") return;
    if (window.__EVIDENCE_DRAWER__ && window.__EVIDENCE_DRAWER__.isOpen()) return;
    if (filterPanel && filterPanel.hasAttribute("open")) {
      closePanel();
    }
  });

  for (var fi = 0; fi < filterItems.length; fi++) {
    (function (item) {
      item.addEventListener("click", function () {
        if (item.getAttribute("aria-disabled") === "true" || item.disabled) {
          return;
        }
        var dim = item.getAttribute("data-dim");
        var val = item.getAttribute("data-val");
        var scope = item.getAttribute("data-scope") || "page";
        var mid = item.getAttribute("data-module-id") || "";
        if (!dim || !val) return;
        var bucket = getActiveBucket(scope, mid);
        if (!bucket[dim]) bucket[dim] = [];
        var idx = bucket[dim].indexOf(val);
        if (idx === -1) bucket[dim].push(val);
        else bucket[dim].splice(idx, 1);
        if (bucket[dim].length === 0) delete bucket[dim];
        syncCheckboxes();
        renderChips();
        filterVisibleRows();
        writeFilterToHash();
      });
      item.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          item.click();
        }
      });
    })(filterItems[fi]);
  }

  if (filterResetPage) {
    filterResetPage.addEventListener("click", resetPageFilters);
  }
  for (var rmi = 0; rmi < filterResetModules.length; rmi++) {
    (function (button) {
      button.addEventListener("click", function () {
        resetModuleFilters(button.getAttribute("data-module-id"));
      });
    })(filterResetModules[rmi]);
  }

  var emptyResetPage = document.getElementById("kz-filter-empty-reset-page");
  var emptyResetModules = document.querySelectorAll(
    ".kz-filter-empty-reset-module"
  );
  if (emptyResetPage) {
    emptyResetPage.addEventListener("click", resetPageFilters);
  }
  for (var ermi = 0; ermi < emptyResetModules.length; ermi++) {
    (function (button) {
      button.addEventListener("click", function () {
        resetModuleFilters(button.getAttribute("data-module-id"));
      });
    })(emptyResetModules[ermi]);
  }

  document.addEventListener("kz-evidence-drawer-change", function (ev) {
    if (applyingFromUrl || syncingFilter) return;
    var detail = (ev && ev.detail) || {};
    evidenceOpenId = detail.openRowId || null;
    evidenceIds = detail.pinnedRowIds || [];
    writeFilterToHash();
  });

  window.addEventListener("popstate", function () {
    readFilterFromHash();
    syncCheckboxes();
  });
  window.addEventListener("hashchange", function () {
    readFilterFromHash();
    syncCheckboxes();
  });

  buildAllowlists();
  readFilterFromHash();
  syncCheckboxes();

  window.__PORTAL_FILTER__ = {
    reapply: function () {
      syncCheckboxes();
      renderChips();
      filterVisibleRows();
    },
    restoreEvidence: restoreEvidenceFromUrl
  };
})();
