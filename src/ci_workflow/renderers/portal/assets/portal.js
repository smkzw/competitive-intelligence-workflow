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
      searchResults.hidden = true;
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
})();
