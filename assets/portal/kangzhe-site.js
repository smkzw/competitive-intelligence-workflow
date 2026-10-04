/* User-selected Kangzhe 6.0: global_procedural_optical_field.
 * A continuous reading-path scene, not clinical results or an acceptance stamp.
 * KZMotion owns carrier geometry/time; this adapter owns its text and lifecycle.
 */
(function () {
  "use strict";
  var body = document.body;
  if (!body || body.dataset.kzDesign !== "6.0") return;
  var abort, motion, film, observer;
  var head = document.querySelector(".portal-page-head");
  if (!head || !window.KZMotion) return;
  function element(tag, className, text) {
    var node = document.createElement(tag);
    node.className = className;
    if (text) node.textContent = text;
    return node;
  }
  var root = element("section", "kz-site-story");
  root.setAttribute("aria-label", "阅读路径");
  var stage = element("div", "kz-film-stage");
  stage.setAttribute("aria-hidden", "true");
  var carrier = element("div", "kz-film-carrier");
  var label = element("strong", "kz-film-carrier-label");
  var details = element("div", "kz-site-story__details");
  var narrative = body.classList.contains("kz-c-site")
    ? { labels: ["设计先例", "人群、干预与终点", "并列条款与原文"],
        detail: ["选择研究", "定义与条件", "完整条款", "原文与定位"],
        summary: "先选择相关研究，再并列核对人群、干预和终点。完整条款及原文始终可查，不生成唯一最佳方案。" }
    : body.classList.contains("kz-b-site")
      ? { labels: ["相关研究", "人群、时间与口径", "结果明细与原文"],
          detail: ["相关研究", "比较条件", "完整结果", "原文与定位"],
          summary: "相关研究全部保留；能否同图比较另行判断。先核对人群、时间与统计口径，再查结果明细及原文。" }
      : { labels: ["竞品与机制", "开发阶段与试验", "结果与来源"],
          detail: ["竞品与机制", "开发状态", "相关试验", "原文与定位"],
          summary: "从竞品与机制查看开发阶段及相关试验，再核对结果和来源。图形不是竞品排名，缺失信息不补成零。" };
  narrative.detail.forEach(function (text) {
    details.appendChild(element("span", "", text));
  });
  carrier.append(label, details);
  stage.append(element("div", "kz-site-story__light"), carrier);
  var caption = element("p", "kz-film-caption", narrative.summary);
  root.append(stage, caption);
  head.appendChild(root);
  var states = [
    { label: narrative.labels[0], w: .43, caption: narrative.summary },
    { label: narrative.labels[1], w: .65, caption: narrative.summary },
    { label: narrative.labels[2], w: .92, caption: narrative.summary }
  ];
  var frames = states.map(function (state, index) {
    return { t: index / 3, x: .02, y: .05, w: state.w, h: .90, r: .16,
      tint: [255, 252, 245, .90], label: state.label, caption: state.caption };
  });
  frames.push(Object.assign({}, frames[0], { t: 1, tint: frames[0].tint.slice() }));
  function mount() {
    if (film) return;
    abort = new AbortController();
    // Separate planar reveal ancestors from the glass hover owner; never animate
    // the same transform from two controllers or perspective-warp data planes.
    document.querySelectorAll(".kz-a-panel, .kz-a-summary, .kz-b-visual-section, .kz-b-reading-notes, .kz-c-visual-section, .kz-c-path-section").forEach(function (card) {
      if (card.parentElement.classList.contains("kz-content-reveal")) return;
      var shell = element("div", "kz-content-reveal");
      shell.dataset.kzReveal = "";
      card.before(shell);
      shell.appendChild(card);
    });
    // Only non-data reading cards tilt; data and table coordinate planes stay flat.
    document.querySelectorAll(".kz-a-summary, .kz-b-reading-notes, .kz-b-dossier-summary").forEach(function (card) {
      if (!card.querySelector("table, canvas, .kz-chart, input, textarea")) card.dataset.kzTilt = "3";
      card.dataset.kzLight = "";
    });
    motion = window.KZMotion.mountPage(body);
    motion.enter();
    film = new window.KZMotion.Film(root, {
      frames: frames, duration: 36000, staticProgress: .66, managedText: false,
      onRender: function (frame) {
        var state = states[frame.index % states.length];
        label.textContent = state.label;
        // Do not shrink visible child text during contraction. The expanded
        // state alone displays its internal relation; static caption stays complete.
        details.hidden = frame.w < .86;
      }
    });
    function synchronize() {
      var editing = !!document.querySelector("input:focus, textarea:focus, select:focus, [contenteditable=true]:focus");
      var overlay = !!document.querySelector(".kz-evidence-drawer:not([hidden]), .kz-evidence-panel:not([hidden]), .kz-a-insight-drawer:not([hidden])");
      body.classList.toggle("kz-background-paused", document.hidden || editing || overlay);
      if (editing) film.pause("editing"); else film.resume("editing");
      if (overlay) film.pause("modal"); else film.resume("modal");
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
    // Internal QC only, no audience playback controls.
    window.__KZ_SITE_SCENE__ = { snapshot: function () { return film.snapshot(); } };
  }
  function dispose() {
    if (!film) return;
    observer.disconnect();
    abort.abort();
    film.dispose();
    motion.dispose();
    film = null;
    delete window.__KZ_SITE_SCENE__;
  }
  window.addEventListener("pagehide", dispose);
  window.addEventListener("pageshow", mount);
  mount();
})();
