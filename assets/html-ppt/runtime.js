/*
 * 竞品调研 HTML-PPT 固定运行时。
 * 衍生自 lewislulu/html-ppt-skill f3a8435；删除通用主题、演示动画和缩略总览。
 * 视觉层由项目内康哲设计合同提供。缩放合同对齐 track_htmlppt.md §14.2–§14.3。
 */

(() => {
  "use strict";

  const DESIGN_WIDTH = 1280;
  const DESIGN_HEIGHT = 720;

  const ready = (callback) => {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", callback, { once: true });
      return;
    }
    callback();
  };

  ready(() => {
    const deck = document.querySelector(".deck");
    const slides = Array.from(document.querySelectorAll(".deck > .slide"));
    if (!deck || slides.length === 0) return;

    const total = slides.length;
    const previewMatch = new URLSearchParams(window.location.search).get("preview");
    const previewIndex = previewMatch ? Number.parseInt(previewMatch, 10) - 1 : -1;
    const previewMode = previewIndex >= 0 && previewIndex < total;
    const channelName = `ci-html-ppt-${stableChannelId(window.location.pathname)}`;
    let channel = null;
    let presenterWindow = null;
    let currentIndex = 0;
    let fitRaf = 0;

    try {
      channel = new BroadcastChannel(channelName);
    } catch (_error) {
      channel = null;
    }

    const progress = createProgress();
    const notesDrawer = createNotesDrawer();
    currentIndex = initialIndex();

    function stableChannelId(value) {
      let hash = 2166136261;
      for (let index = 0; index < value.length; index += 1) {
        hash ^= value.charCodeAt(index);
        hash = Math.imul(hash, 16777619);
      }
      return (hash >>> 0).toString(16);
    }

    function indexFromHash() {
      const match = /^#\/(\d+)$/.exec(window.location.hash);
      if (!match) return 0;
      return clamp(Number.parseInt(match[1], 10) - 1);
    }

    function writeSlideHash(index) {
      const next = `#/${index + 1}`;
      if (window.location.hash !== next) {
        window.history.replaceState(null, "", next);
      }
    }

    function initialIndex() {
      if (previewMode) return previewIndex;
      return indexFromHash();
    }

    function clamp(index) {
      return Math.max(0, Math.min(total - 1, index));
    }

    function createProgress() {
      let root = document.querySelector(".deck-progress, .progress-bar");
      if (!root) {
        root = document.createElement("div");
        document.body.append(root);
      }
      root.classList.add("deck-progress", "progress-bar");
      root.setAttribute("aria-hidden", "true");
      let fill = root.querySelector("span");
      if (!fill) {
        fill = document.createElement("span");
        root.append(fill);
      }
      return fill;
    }

    function createNotesDrawer() {
      let drawer = document.querySelector(".deck-notes-drawer");
      if (!drawer) {
        drawer = document.createElement("section");
        document.body.append(drawer);
      }
      drawer.classList.add("deck-notes-drawer", "notes-overlay");
      drawer.setAttribute("aria-label", "逐字稿");
      drawer.setAttribute("aria-hidden", "true");
      if (!drawer.querySelector(".deck-notes-drawer__title")) {
        drawer.innerHTML = [
          '<h2 class="deck-notes-drawer__title">逐字稿</h2>',
          '<div class="deck-notes-drawer__body"></div>',
        ].join("");
      }
      return drawer;
    }

    function fitDeckToViewport() {
      fitRaf = 0;
      const viewportWidth = document.documentElement.clientWidth || window.innerWidth;
      const viewportHeight = document.documentElement.clientHeight || window.innerHeight;
      const scale = Math.min(viewportWidth / DESIGN_WIDTH, viewportHeight / DESIGN_HEIGHT);
      const value = String(scale);
      document.documentElement.style.setProperty("--deck-scale", value);
      deck.style.setProperty("--deck-scale", value);
    }

    function scheduleDeckFit() {
      if (!fitRaf) fitRaf = window.requestAnimationFrame(fitDeckToViewport);
    }

    function noteHtml(index) {
      const note = slides[index]?.querySelector("aside.notes, .notes, .speaker-notes");
      return note ? note.innerHTML : "<p>这一页暂未提供逐字稿。</p>";
    }

    function slideTitle(index) {
      const slide = slides[index];
      return (
        slide?.getAttribute("data-title") ||
        slide?.querySelector("h1, h2")?.textContent?.trim() ||
        `第${index + 1}页`
      );
    }

    function updatePerSlideNumbers() {
      slides.forEach((slide, index) => {
        const number = slide.querySelector(".slide-number");
        if (!number) return;
        number.setAttribute("data-current", String(index + 1));
        number.setAttribute("data-total", String(total));
        number.textContent = `${index + 1} / ${total}`;
      });
    }

    function showSlide(index, options = {}) {
      currentIndex = clamp(index);
      slides.forEach((slide, slideIndex) => {
        const active = slideIndex === currentIndex;
        slide.classList.toggle("is-active", active);
        slide.setAttribute("aria-hidden", active ? "false" : "true");
      });
      progress.style.width = `${((currentIndex + 1) / total) * 100}%`;
      const notesBody = notesDrawer.querySelector(".deck-notes-drawer__body");
      if (notesBody) notesBody.innerHTML = noteHtml(currentIndex);

      if (!previewMode && options.writeHash !== false) {
        writeSlideHash(currentIndex);
      }
      if (!previewMode && options.broadcast !== false) {
        postSync({ type: "go", index: currentIndex, idx: currentIndex });
      }
      document.dispatchEvent(
        new CustomEvent("ci:slidechange", { detail: { index: currentIndex, total } }),
      );
    }

    function toggleNotes(force) {
      const shouldOpen =
        typeof force === "boolean" ? force : !notesDrawer.classList.contains("is-open");
      notesDrawer.classList.toggle("is-open", shouldOpen);
      notesDrawer.setAttribute("aria-hidden", shouldOpen ? "false" : "true");
    }

    function requestFullscreen() {
      const root = document.documentElement;
      if (!document.fullscreenElement && !document.webkitFullscreenElement) {
        (root.requestFullscreen || root.webkitRequestFullscreen)?.call(root);
      } else {
        (document.exitFullscreen || document.webkitExitFullscreen)?.call(document);
      }
    }

    function syncEnvelope(payload) {
      return {
        source: "ci-html-ppt",
        channel: channelName,
        ...payload,
      };
    }

    function postSync(payload) {
      const message = syncEnvelope(payload);
      try { channel?.postMessage(message); } catch (_error) {}
      try {
        if (presenterWindow && !presenterWindow.closed) {
          presenterWindow.postMessage(message, "*");
        }
      } catch (_error) {}
      try { window.opener?.postMessage(message, "*"); } catch (_error) {}
    }

    function remoteIndex(data) {
      if (!data || data.source !== "ci-html-ppt") return null;
      if (data.channel && data.channel !== channelName) return null;
      const next = data.index ?? data.idx;
      return typeof next === "number" && Number.isFinite(next) ? next : null;
    }

    function resetPresenterTimer() {
      postSync({ type: "reset-timer" });
    }

    function cleanDeckUrl() {
      const url = new URL(window.location.href);
      url.search = "";
      url.hash = "";
      return url.href;
    }

    function openPresenter() {
      if (presenterWindow && !presenterWindow.closed) {
        presenterWindow.focus();
        postSync({ type: "go", index: currentIndex, idx: currentIndex });
        return;
      }
      presenterWindow = window.open("", "ci-html-ppt-presenter", "popup,width=1440,height=900");
      if (!presenterWindow) {
        window.alert("请允许弹出窗口以使用演讲者视图");
        return;
      }

      const metadata = slides.map((_slide, index) => ({
        title: slideTitle(index),
        notes: noteHtml(index),
      }));
      presenterWindow.document.open();
      presenterWindow.document.write(
        presenterMarkup({
          baseUrl: cleanDeckUrl(),
          channelName,
          currentIndex,
          metadata,
          total,
        }),
      );
      presenterWindow.document.close();
    }

    function presenterMarkup(context) {
      const serialized = JSON.stringify(context).replaceAll("<", "\\u003c");
      return `<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>演讲者视图</title>
<style>
  :root{color-scheme:dark;font-family:"Microsoft YaHei","PingFang SC",sans-serif}
  *{box-sizing:border-box} body{margin:0;background:#171717;color:#f5f5f5;overflow:hidden}
  .presenter-shell{display:grid;grid-template-columns:minmax(0,1.45fr) minmax(340px,.75fr);grid-template-rows:minmax(0,1fr) minmax(210px,.44fr);gap:12px;height:100vh;padding:12px}
  .presenter-panel{min-width:0;min-height:0;border:1px solid #454545;border-radius:10px;background:#242424;overflow:hidden}
  .presenter-panel__head{display:flex;align-items:center;justify-content:space-between;height:42px;padding:0 14px;background:#303030;font-size:15px;font-weight:700}
  .presenter-panel__body{height:calc(100% - 42px);padding:12px;overflow:auto}
  .presenter-preview{position:relative;padding:0;background:#090909;overflow:hidden}
  .presenter-preview iframe{position:absolute;top:0;left:0;width:1280px;height:720px;border:0;background:white;transform-origin:top left;pointer-events:none}
  .presenter-script{font-size:21px;line-height:1.7}.presenter-script p{margin:.2em 0 .8em}
  .presenter-controls{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:14px}
  .presenter-timer{font-variant-numeric:tabular-nums;font-size:52px;font-weight:700}
  .presenter-page{font-size:18px;color:#d6d6d6}.presenter-buttons{display:flex;gap:8px;flex-wrap:wrap;justify-content:center}
  button{min-width:100px;padding:10px 14px;border:1px solid #686868;border-radius:7px;background:#383838;color:#fff;font:inherit;cursor:pointer}button:hover{background:#4b4b4b}
  .presenter-end{display:grid;place-items:center;height:100%;font-size:30px;color:#bbb}.presenter-end[hidden]{display:none}
</style>
</head>
<body>
<main class="presenter-shell">
  <section class="presenter-panel">
    <div class="presenter-panel__head"><span>当前页</span><span id="current-title"></span></div>
    <div class="presenter-panel__body presenter-preview"><iframe id="current-preview" title="当前页预览"></iframe></div>
  </section>
  <section class="presenter-panel">
    <div class="presenter-panel__head"><span>下一页</span><span id="next-title"></span></div>
    <div class="presenter-panel__body presenter-preview" id="next-body">
      <iframe id="next-preview" title="下一页预览"></iframe>
      <div class="presenter-end" id="next-end" hidden>演示结束</div>
    </div>
  </section>
  <section class="presenter-panel">
    <div class="presenter-panel__head"><span>逐字稿</span><span>演讲者视图</span></div>
    <div class="presenter-panel__body presenter-script" id="script"></div>
  </section>
  <section class="presenter-panel">
    <div class="presenter-panel__head"><span>计时</span><span id="page"></span></div>
    <div class="presenter-panel__body presenter-controls">
      <div class="presenter-timer" id="timer">00:00</div>
      <div class="presenter-page" id="page-detail"></div>
      <div class="presenter-buttons">
        <button id="previous" type="button">上一页</button>
        <button id="next" type="button">下一页</button>
        <button id="reset" type="button">重新计时</button>
      </div>
    </div>
  </section>
</main>
<script>
(() => {
  "use strict";
  const context = ${serialized};
  let index = context.currentIndex;
  let startedAt = Date.now();
  let channel = null;
  try { channel = new BroadcastChannel(context.channelName); } catch (_error) { channel = null; }
  const currentPreview = document.querySelector("#current-preview");
  const nextPreview = document.querySelector("#next-preview");
  const nextEnd = document.querySelector("#next-end");
  const script = document.querySelector("#script");
  const timer = document.querySelector("#timer");
  const iframeReady = { current: false, next: false };

  function envelope(payload) {
    return { source: "ci-html-ppt", channel: context.channelName, ...payload };
  }
  function postSync(payload) {
    const message = envelope(payload);
    try { channel?.postMessage(message); } catch (_error) {}
    try { window.opener?.postMessage(message, "*"); } catch (_error) {}
  }
  function previewUrl(slideIndex) {
    return context.baseUrl + "?preview=" + (slideIndex + 1);
  }
  function rescaleIframe(iframe) {
    const host = iframe.parentElement;
    if (!host) return;
    const scale = Math.min(host.clientWidth / 1280, host.clientHeight / 720);
    iframe.style.transform = "scale(" + scale + ")";
  }
  function rescaleAll() {
    rescaleIframe(currentPreview);
    if (nextPreview && !nextPreview.hidden) rescaleIframe(nextPreview);
  }
  function postGoto(iframe, slideIndex) {
    try { iframe.contentWindow.postMessage({ type: "preview-goto", index: slideIndex, idx: slideIndex }, "*"); } catch (_error) {}
  }
  function resetTimer() { startedAt = Date.now(); tick(); }
  function tick() {
    const elapsed = Math.floor((Date.now() - startedAt) / 1000);
    const minutes = String(Math.floor(elapsed / 60)).padStart(2, "0");
    const seconds = String(elapsed % 60).padStart(2, "0");
    timer.textContent = minutes + ":" + seconds;
  }
  function applyRemote(data) {
    if (!data || data.source !== "ci-html-ppt") return;
    if (data.channel && data.channel !== context.channelName) return;
    if (data.type === "reset-timer") { resetTimer(); return; }
    if (data.type === "go" || data.type === "slide") {
      const next = data.index ?? data.idx;
      if (typeof next === "number") update(next);
    }
  }
  function update(nextIndex) {
    index = Math.max(0, Math.min(context.total - 1, nextIndex));
    document.querySelector("#current-title").textContent = context.metadata[index].title;
    script.innerHTML = context.metadata[index].notes;
    document.querySelector("#page").textContent = "页码 " + (index + 1) + " / " + context.total;
    document.querySelector("#page-detail").textContent = "第" + (index + 1) + "页，共" + context.total + "页";
    if (iframeReady.current) postGoto(currentPreview, index);
    if (index + 1 < context.total) {
      nextPreview.hidden = false;
      nextEnd.hidden = true;
      document.querySelector("#next-title").textContent = context.metadata[index + 1].title;
      if (iframeReady.next) postGoto(nextPreview, index + 1);
    } else {
      nextPreview.hidden = true;
      nextEnd.hidden = false;
      document.querySelector("#next-title").textContent = "";
    }
    rescaleAll();
  }
  function go(nextIndex) {
    const bounded = Math.max(0, Math.min(context.total - 1, nextIndex));
    postSync({ type: "go", index: bounded, idx: bounded });
    update(bounded);
  }
  window.addEventListener("message", (event) => {
    if (event.data?.type === "preview-ready") {
      if (event.source === currentPreview.contentWindow) {
        iframeReady.current = true;
        postGoto(currentPreview, index);
        rescaleIframe(currentPreview);
      } else if (event.source === nextPreview.contentWindow) {
        iframeReady.next = true;
        if (index + 1 < context.total) postGoto(nextPreview, index + 1);
        rescaleIframe(nextPreview);
      }
      return;
    }
    applyRemote(event.data);
  });
  channel?.addEventListener("message", (event) => applyRemote(event.data));
  document.querySelector("#previous").addEventListener("click", () => go(index - 1));
  document.querySelector("#next").addEventListener("click", () => go(index + 1));
  document.querySelector("#reset").addEventListener("click", () => {
    resetTimer();
    postSync({ type: "reset-timer" });
  });
  document.addEventListener("keydown", (event) => {
    if (event.metaKey || event.ctrlKey || event.altKey) return;
    const key = event.key.length === 1 ? event.key.toLowerCase() : event.key;
    let handled = true;
    if (key === "ArrowLeft" || key === "PageUp") go(index - 1);
    else if (key === "ArrowRight" || key === "PageDown" || key === " ") go(index + 1);
    else if (key === "Home") go(0);
    else if (key === "End") go(context.total - 1);
    else if (key === "r") { resetTimer(); postSync({ type: "reset-timer" }); }
    else if (key === "Escape") window.close();
    else handled = false;
    if (handled) event.preventDefault();
  });
  window.addEventListener("resize", rescaleAll);
  currentPreview.addEventListener("load", () => rescaleIframe(currentPreview));
  nextPreview.addEventListener("load", () => rescaleIframe(nextPreview));
  tick();
  window.setInterval(tick, 250);
  currentPreview.src = previewUrl(index);
  nextPreview.src = previewUrl(index + 1 < context.total ? index + 1 : index);
  update(index);
})();
<\/script>
</body>
</html>`;
    }

    function handleKey(event) {
      if (event.defaultPrevented || event.metaKey || event.ctrlKey || event.altKey) return;
      const target = event.target;
      if (target instanceof HTMLElement && target.closest("input, textarea, select, [contenteditable]")) {
        return;
      }

      const key = event.key.length === 1 ? event.key.toLowerCase() : event.key;
      switch (key) {
        case "ArrowLeft":
        case "PageUp":
          showSlide(currentIndex - 1);
          break;
        case "ArrowRight":
        case "PageDown":
        case " ":
          showSlide(currentIndex + 1);
          break;
        case "Home":
          showSlide(0);
          break;
        case "End":
          showSlide(total - 1);
          break;
        case "f":
          requestFullscreen();
          break;
        case "s":
          openPresenter();
          break;
        case "n":
          toggleNotes();
          break;
        case "r":
          resetPresenterTimer();
          break;
        case "Escape":
          toggleNotes(false);
          break;
        default:
          return;
      }
      event.preventDefault();
    }

    function freezePreviewKeys(event) {
      if (event.metaKey || event.ctrlKey || event.altKey) return;
      const target = event.target;
      if (target instanceof HTMLElement && target.closest("input, textarea, select, [contenteditable]")) {
        return;
      }
      const key = event.key.length === 1 ? event.key.toLowerCase() : event.key;
      if (
        key === "ArrowLeft" ||
        key === "ArrowRight" ||
        key === "PageUp" ||
        key === "PageDown" ||
        key === " " ||
        key === "Home" ||
        key === "End" ||
        key === "n" ||
        key === "s" ||
        key === "f" ||
        key === "t" ||
        key === "a" ||
        key === "o" ||
        key === "r"
      ) {
        event.preventDefault();
      }
    }

    function readHash() {
      if (previewMode) return;
      showSlide(indexFromHash(), { writeHash: false });
    }

    function onRemoteSync(event) {
      const data = event.data;
      if (!data || data.source !== "ci-html-ppt") return;
      if (data.channel && data.channel !== channelName) return;
      if (data.type === "reset-timer") return;
      const next = remoteIndex(data);
      if ((data.type === "go" || data.type === "slide") && next !== null) {
        showSlide(next, { broadcast: false });
      }
    }

    function bindScaleListeners() {
      window.addEventListener("resize", scheduleDeckFit, { passive: true });
      window.visualViewport?.addEventListener("resize", scheduleDeckFit, { passive: true });
      document.fonts?.ready.then(scheduleDeckFit);
    }

    updatePerSlideNumbers();

    if (previewMode) {
      document.documentElement.setAttribute("data-preview", "true");
      document.body.setAttribute("data-preview", "true");
      window.addEventListener("message", (event) => {
        if (event.data?.type !== "preview-goto") return;
        const next = event.data.index ?? event.data.idx;
        if (typeof next === "number") showSlide(next, { broadcast: false, writeHash: false });
      });
      document.addEventListener("keydown", freezePreviewKeys);
      showSlide(previewIndex, { broadcast: false, writeHash: false });
      window.parent?.postMessage({ type: "preview-ready" }, "*");
      return;
    }

    channel?.addEventListener("message", onRemoteSync);
    window.addEventListener("message", onRemoteSync);
    bindScaleListeners();
    document.addEventListener("keydown", handleKey);
    window.addEventListener("hashchange", readHash);
    fitDeckToViewport();
    showSlide(currentIndex);
  });
})();
