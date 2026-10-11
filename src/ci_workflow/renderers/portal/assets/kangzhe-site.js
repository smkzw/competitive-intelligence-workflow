/* Adapt motion to report-owned content, without injected narrative or scenes.
 * KZMotion owns reveal/light timing; clinical content belongs to the report.
 */
(function () {
  "use strict";
  var body = document.body;
  if (!body || body.dataset.kzDesign !== "6.0") return;
  var abort, motion, observer;
  var head = document.querySelector(".portal-page-head");
  if (!head || !window.KZMotion) return;
  function element(tag, className, text) {
    var node = document.createElement(tag);
    node.className = className;
    if (text) node.textContent = text;
    return node;
  }
  function hasDataPlane(card) {
    return !!card.querySelector("table, canvas, .kz-chart, input, textarea");
  }
  function willTilt(card) {
    return card.matches(".kz-a-summary, .kz-b-reading-notes, .kz-b-dossier-summary") && !hasDataPlane(card);
  }
  // Move responsive layout tokens onto the actual grid item. Never copy computed
  // pixel spans once at mount — class/attr contracts keep media-query lifecycle.
  function transferLayoutContract(from, to) {
    String(from.className || "").split(/\s+/).filter(Boolean).forEach(function (name) {
      if (name === "kz-a-summary--wide" || /--wide$/.test(name)) {
        to.classList.add(name);
        from.classList.remove(name);
      }
    });
    if (from.hasAttribute("data-grid-span")) {
      to.setAttribute("data-grid-span", from.getAttribute("data-grid-span"));
      from.removeAttribute("data-grid-span");
    }
    ["gridColumn", "gridRow", "gridArea"].forEach(function (key) {
      if (from.style && from.style[key]) {
        to.style[key] = from.style[key];
        from.style[key] = "";
      }
    });
  }
  function bindReveal(card) {
    if (card.hasAttribute("data-kz-reveal")) return;
    if (card.parentElement && card.parentElement.classList.contains("kz-content-reveal")) return;
    // Prefer preserving the layout-owning node when reveal is the only transform.
    if (!willTilt(card)) {
      card.dataset.kzReveal = "";
      return;
    }
    // layout shell → reveal → tilt glass → reading: transfer span ownership out.
    var shell = element("div", "kz-content-reveal");
    shell.dataset.kzReveal = "";
    transferLayoutContract(card, shell);
    card.before(shell);
    shell.appendChild(card);
  }
  function mount() {
    if (motion) return;
    abort = new AbortController();
    // Separate planar reveal ancestors from the glass hover owner; never animate
    // the same transform from two controllers or perspective-warp data planes.
    document.querySelectorAll(".kz-a-panel, .kz-a-summary, .kz-b-visual-section, .kz-b-reading-notes, .kz-c-visual-section, .kz-c-path-section").forEach(bindReveal);
    // Only non-data reading cards tilt; data and table coordinate planes stay flat.
    document.querySelectorAll(".kz-a-summary, .kz-b-reading-notes, .kz-b-dossier-summary").forEach(function (card) {
      if (!hasDataPlane(card)) card.dataset.kzTilt = "3";
      card.dataset.kzLight = "";
    });
    motion = window.KZMotion.mountPage(body);
    motion.enter();
    function synchronize() {
      var editing = !!document.querySelector("input:focus, textarea:focus, select:focus, [contenteditable=true]:focus");
      var overlay = !!document.querySelector(".kz-evidence-drawer:not([hidden]), .kz-evidence-panel:not([hidden]), .kz-a-insight-drawer:not([hidden])");
      body.classList.toggle("kz-background-paused", document.hidden || editing || overlay);
      if (document.hidden || editing || overlay) motion.finish();
    }
    observer = new MutationObserver(synchronize);
    document.querySelectorAll(".kz-evidence-drawer, .kz-evidence-panel, .kz-a-insight-drawer").forEach(function (node) {
      observer.observe(node, { attributes: true, attributeFilter: ["hidden"] });
    });
    document.addEventListener("focusin", synchronize, { signal: abort.signal });
    document.addEventListener("focusout", function () { queueMicrotask(synchronize); }, { signal: abort.signal });
    document.addEventListener("visibilitychange", synchronize, { signal: abort.signal });
    synchronize();
  }
  function dispose() {
    if (!motion) return;
    observer.disconnect();
    abort.abort();
    motion.dispose();
    motion = null;
  }
  window.addEventListener("pagehide", dispose);
  window.addEventListener("pageshow", mount);
  mount();
})();
