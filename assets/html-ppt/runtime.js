/*
 * 竞品调研 HTML-PPT 固定运行时。
 * 衍生自 lewislulu/html-ppt-skill f3a8435；删除通用主题、演示动画和缩略总览。
 * 视觉层由项目内康哲设计合同提供。
 */

(() => {
  "use strict";

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
    let currentIndex = initialIndex();

    try {
      channel = new BroadcastChannel(channelName);
    } catch (_error) {
      channel = null;
    }

    const progress = createProgress();
    const notesDrawer = createNotesDrawer();

    function stableChannelId(value) {
      let hash = 2166136261;
      for (let index = 0; index < value.length; index += 1) {
        hash ^= value.charCodeAt(index);
        hash = Math.imul(hash, 16777619);
      }
      return (hash >>> 0).toString(16);
    }

    function initialIndex() {
      if (previewMode) return previewIndex;
      const match = /^#\/(\d+)$/.exec(window.location.hash);
      if (!match) return 0;
      return clamp(Number.parseInt(match[1], 10) - 1);
    }

    function clamp(index) {
      return Math.max(0, Math.min(total - 1, index));
    }

    function createProgress() {
      const root = document.createElement("div");
      root.className = "deck-progress";
      root.setAttribute("aria-hidden", "true");
      const fill = document.createElement("span");
      root.append(fill);
      document.body.append(root);
      return fill;
    }

    function createNotesDrawer() {
      const drawer = document.createElement("section");
      drawer.className = "deck-notes-drawer";
      drawer.setAttribute("aria-label", "逐字稿");
      drawer.innerHTML = [
        '<h2 class="deck-notes-drawer__title">逐字稿</h2>',
        '<div class="deck-notes-drawer__body"></div>',
      ].join("");
      document.body.append(drawer);
      return drawer;
    }

    function updateScale() {
      if (previewMode) return;
      const scale = Math.min(window.innerWidth / 1280, window.innerHeight / 720);
      deck.style.setProperty("--deck-scale", String(scale));
    }

    function noteHtml(index) {
      const note = slides[index]?.querySelector("aside.notes");
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

      if (!previewMode && window.location.hash !== `#/${currentIndex + 1}`) {
        window.history.replaceState(null, "", `#/${currentIndex + 1}`);
      }
      if (!previewMode && options.broadcast !== false && channel) {
        channel.postMessage({ type: "slide", index: currentIndex });
      }
      document.dispatchEvent(
        new CustomEvent("ci:slidechange", { detail: { index: currentIndex, total } }),
      );
    }

    function toggleNotes(force) {
      const shouldOpen =
        typeof force === "boolean" ? force : !notesDrawer.classList.contains("is-open");
      notesDrawer.classList.toggle("is-open", shouldOpen);
    }

    function requestFullscreen() {
      if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen?.();
      } else {
        document.exitFullscreen?.();
      }
    }

    function resetPresenterTimer() {
      channel?.postMessage({ type: "reset-timer" });
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
        return;
      }
      presenterWindow = window.open("", "ci-html-ppt-presenter", "popup,width=1440,height=900");
      if (!presenterWindow) return;

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
  .presenter-preview{padding:0;background:#090909}.presenter-preview iframe{width:100%;height:100%;border:0;background:white}
  .presenter-script{font-size:21px;line-height:1.7}.presenter-script p{margin:.2em 0 .8em}
  .presenter-controls{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:14px}
  .presenter-timer{font-variant-numeric:tabular-nums;font-size:52px;font-weight:700}
  .presenter-page{font-size:18px;color:#d6d6d6}.presenter-buttons{display:flex;gap:8px;flex-wrap:wrap;justify-content:center}
  button{min-width:100px;padding:10px 14px;border:1px solid #686868;border-radius:7px;background:#383838;color:#fff;font:inherit;cursor:pointer}button:hover{background:#4b4b4b}
  .presenter-end{display:grid;place-items:center;height:100%;font-size:30px;color:#bbb}
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
    <div class="presenter-panel__body presenter-preview" id="next-body"><iframe id="next-preview" title="下一页预览"></iframe></div>
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
  const nextBody = document.querySelector("#next-body");
  const script = document.querySelector("#script");
  const timer = document.querySelector("#timer");

  function previewUrl(slideIndex) {
    return context.baseUrl + "?preview=" + (slideIndex + 1);
  }
  function resetTimer() { startedAt = Date.now(); timer.textContent = "00:00"; }
  function tick() {
    const elapsed = Math.floor((Date.now() - startedAt) / 1000);
    const minutes = String(Math.floor(elapsed / 60)).padStart(2, "0");
    const seconds = String(elapsed % 60).padStart(2, "0");
    timer.textContent = minutes + ":" + seconds;
  }
  function update(nextIndex) {
    index = Math.max(0, Math.min(context.total - 1, nextIndex));
    currentPreview.src = previewUrl(index);
    document.querySelector("#current-title").textContent = context.metadata[index].title;
    script.innerHTML = context.metadata[index].notes;
    document.querySelector("#page").textContent = "页码 " + (index + 1) + " / " + context.total;
    document.querySelector("#page-detail").textContent = "第" + (index + 1) + "页，共" + context.total + "页";
    if (index + 1 < context.total) {
      nextBody.innerHTML = '<iframe id="next-preview" title="下一页预览"></iframe>';
      document.querySelector("#next-preview").src = previewUrl(index + 1);
      document.querySelector("#next-title").textContent = context.metadata[index + 1].title;
    } else {
      nextBody.innerHTML = '<div class="presenter-end">演示结束</div>';
      document.querySelector("#next-title").textContent = "";
    }
  }
  function go(nextIndex) {
    const bounded = Math.max(0, Math.min(context.total - 1, nextIndex));
    channel?.postMessage({ type: "go", index: bounded });
    update(bounded);
  }
  channel?.addEventListener("message", (event) => {
    if (event.data?.type === "slide") update(event.data.index);
    if (event.data?.type === "reset-timer") resetTimer();
  });
  document.querySelector("#previous").addEventListener("click", () => go(index - 1));
  document.querySelector("#next").addEventListener("click", () => go(index + 1));
  document.querySelector("#reset").addEventListener("click", resetTimer);
  document.addEventListener("keydown", (event) => {
    if (event.key === "ArrowLeft" || event.key === "PageUp") go(index - 1);
    if (event.key === "ArrowRight" || event.key === "PageDown" || event.key === " ") go(index + 1);
    if (event.key.toLowerCase() === "r") resetTimer();
    if (event.key === "Escape") window.close();
  });
  window.setInterval(tick, 1000);
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

    function readHash() {
      if (previewMode) return;
      const match = /^#\/(\d+)$/.exec(window.location.hash);
      if (match) showSlide(Number.parseInt(match[1], 10) - 1);
    }

    if (previewMode) {
      document.documentElement.setAttribute("data-preview", "true");
      window.addEventListener("message", (event) => {
        if (event.data?.type === "preview-goto") showSlide(event.data.index, { broadcast: false });
      });
      showSlide(previewIndex, { broadcast: false });
      window.parent?.postMessage({ type: "preview-ready" }, "*");
      return;
    }

    channel?.addEventListener("message", (event) => {
      if (event.data?.type === "go") showSlide(event.data.index, { broadcast: false });
    });
    window.addEventListener("resize", updateScale);
    window.addEventListener("hashchange", readHash);
    document.addEventListener("keydown", handleKey);
    updatePerSlideNumbers();
    updateScale();
    showSlide(currentIndex);
  });
})();
