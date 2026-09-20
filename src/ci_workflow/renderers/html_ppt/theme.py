"""Kangzhe HTML-PPT theme CSS extracted from track_htmlppt §14.1–§14.7."""

KANGZHE_CSS = r"""
:root {
  color-scheme: only light;
  --deck-scale: 1;
  --kz-orange: #FF9900;
  --kz-orange-mid: #F5A000;
  --kz-yellow: #FFCC00;
  --kz-number: #FFA900;
  --kz-deep-text: #0F1115;
  --kz-body: #404040;
  --kz-title-gray: #595959;
  --kz-meta: #808080;
  --kz-risk: #C00000;
  --kz-border: #AAA6A1;
  --kz-border-weak: #D6D2CD;
  --kz-table-head: #F79646;
  --kz-table-soft: #FBE3D6;
  --kz-theme-warm-bg: #EEECE1;
  --kz-surface-warm: #FCF5E6;
  --kz-med-blue: #407AAA;
  --kz-blue-soft: #DCE6F2;
  --kz-stats-green: #587B3B;
  --kz-stats-soft: #DCE9C8;
  --kz-white: #FFFFFF;
  --bg: var(--kz-white);
  --text-1: var(--kz-deep-text);
  --accent: var(--kz-orange);
  --radius: 8px;
  --shadow: 0 5px 16px rgba(15,17,21,.09);
  --shadow-1: 0 1px 2px rgba(15,17,21,.06), 0 6px 18px rgba(15,17,21,.08);
  --font-sans: "Microsoft YaHei", "微软雅黑", "PingFang SC",
    "Noto Sans SC", "Helvetica Neue", Arial, sans-serif;
  --ease: cubic-bezier(.4,0,.2,1);
}
*, *::before, *::after { box-sizing: border-box; }
html, body {
  width: 100%; height: 100%; margin: 0; overflow: hidden;
  background: var(--kz-white);
}
body.tpl-kangzhe {
  display: grid; place-items: center;
  font-family: var(--font-sans); font-synthesis: none; color: var(--kz-deep-text);
}
.tpl-kangzhe .deck {
  position: relative; width: 1280px; height: 720px; flex: 0 0 1280px;
  overflow: hidden; background: var(--kz-white);
  transform: scale(var(--deck-scale, 1)); transform-origin: 50% 50%;
}
.tpl-kangzhe .slide {
  position: absolute; inset: 0; width: 1280px; height: 720px;
  display: flex; flex-direction: column; justify-content: flex-start; align-items: stretch;
  padding: 96px 56px 60px; overflow: hidden; background: var(--kz-white);
  transform: none; opacity: 0; visibility: hidden; pointer-events: none;
  transition: opacity .2s var(--ease);
}
.tpl-kangzhe .slide.is-active { opacity: 1; visibility: visible; pointer-events: auto; }
.tpl-kangzhe .slide-body > .grid.g2 {
  display:grid; grid-template-columns:564px 564px; gap:40px;
}
.tpl-kangzhe .slide-body > .grid.g3 {
  display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:16px;
}
.tpl-kangzhe .grid > * { min-width:0; }
.tpl-kangzhe .kz-card { transform:none; }
.tpl-kangzhe .slide.cover-slide { padding:0 !important; background:var(--kz-white); }
.cover-hero {
  position: absolute; inset: 0 0 auto; height: 565px;
  background-color: var(--kz-white); background-image: var(--cover-hero-image, none);
  background-position: center top; background-size: cover; background-repeat: no-repeat;
}
.cover-wordmark {
  position: absolute; left: 52px; top: 48px; z-index: 3;
  width: 240px; height: 50px; color: var(--kz-title-gray);
  font-size: 22px; line-height: 33px; font-weight: 700; white-space: nowrap;
}
.cover-main { position: absolute; inset: 0; text-align: center; z-index: 2; }
.cover-main h1 {
  position: absolute; top: 148px; left: 48px; right: 48px; margin: 0;
  color: var(--kz-body); font-size: 48px; line-height: 1.18; font-weight: 700;
}
.cover-department {
  position: absolute; top: 382px; left: 0; right: 0; margin: 0;
  color: var(--kz-title-gray); font-size: 32px; line-height: 1.25; font-weight: 700;
}
.cover-date {
  position: absolute; top: 468px; left: 0; right: 0; margin: 0;
  color: var(--kz-body); font-size: 22px; line-height: 1.2;
}
.cover-rule {
  position: absolute; left: 280px; right: 280px; top: 538px;
  height: 4px; background: var(--kz-yellow); z-index: 3;
}
.cover-ribbon-fallback {
  position: absolute; left: 0; bottom: 0; width: 1280px; height: 155px;
  background: var(--kz-white); text-align: center;
}
.ribbon-colorbar { display: grid; grid-template-columns: 1fr 1.55fr 3fr; height: 12px; }
.ribbon-colorbar i:nth-child(1) { background: var(--kz-yellow); }
.ribbon-colorbar i:nth-child(2) { background: var(--kz-orange-mid); }
.ribbon-colorbar i:nth-child(3) { background: var(--kz-orange); }
.ribbon-lockup {
  height: 143px; display: flex; align-items: center; justify-content: center;
  color: var(--kz-title-gray);
}
.ribbon-lockup > img { display:block; width:242px; height:50px; object-fit:contain; }
:is(.cover-wordmark,.toc-wordmark,.section-wordmark,.ending-wordmark) > img {
  display:block; width:100%; height:100%; object-fit:contain;
}
.tpl-kangzhe .slide.toc-slide { padding:0 !important; background:var(--kz-white); }
.toc-wordmark {
  position:absolute; right:52px; top:44px; width:200px; height:44px;
  color:var(--kz-title-gray); font-size:22px; line-height:33px;
  font-weight:700; white-space:nowrap; text-align:right; z-index:3;
}
.toc-title {
  position:absolute; left:68px; top:25px; margin:0;
  color:var(--kz-deep-text); font-size:48px; line-height:1.15; font-weight:700;
}
.toc-rule {
  position:absolute; left:68px; top:96px; width:582px; height:5px;
  background:var(--kz-yellow);
}
.toc-meta {
  position:absolute; left:68px; top:112px; margin:0;
  color:var(--kz-meta); font-size:20px; line-height:1.2; font-weight:400;
  white-space:nowrap;
}
.toc-board {
  position:absolute; left:68px; top:178px; width:1144px; height:392px;
  display:grid; grid-template-columns:repeat(2,minmax(0,1fr));
  grid-template-rows:repeat(2,186px); gap:20px 24px; margin:0; padding:0;
}
.toc-item {
  position:relative; display:grid; grid-template-columns:92px minmax(0,1fr);
  align-items:center; min-width:0; min-height:0; padding:24px 28px;
  border:1px solid var(--kz-border-weak); border-top:4px solid var(--kz-orange);
  border-radius:8px; background:var(--kz-white);
  box-shadow:var(--shadow-1,var(--shadow)); overflow:hidden;
}
.toc-item:nth-child(3) { border-top-color:var(--kz-med-blue); }
.toc-item:nth-child(4) { border-top-color:var(--kz-stats-green); }
.toc-item > div { min-width:0; }
.toc-item small {
  display:block; margin-top:12px; color:var(--kz-meta);
  font-size:16px; line-height:1.2; font-weight:600; white-space:nowrap;
}
.toc-index {
  color:var(--kz-number); font-family:Arial,var(--font-sans);
  font-size:52px; line-height:1; font-weight:700; font-variant-numeric:tabular-nums;
}
.toc-label {
  display:block; min-width:0; color:var(--kz-deep-text); font-size:30px;
  line-height:1.2; font-weight:700; white-space:nowrap;
}
.tpl-kangzhe .slide.section-slide { padding:0 !important; background:var(--kz-white); }
.section-wordmark {
  position:absolute; right:52px; top:44px; width:200px; height:44px;
  color:var(--kz-title-gray); font-size:22px; line-height:33px;
  font-weight:700; white-space:nowrap; text-align:right;
}
.section-number {
  position:absolute; left:108px; top:112px; width:260px; height:117px;
  color:var(--kz-number); font-family:Arial,var(--font-sans);
  font-size:117px; line-height:1; font-weight:700; font-variant-numeric:tabular-nums;
}
.section-rule {
  position:absolute; left:113px; top:261px; width:240px; height:5px;
  background:var(--kz-yellow);
}
.section-title {
  position:absolute; left:114px; right:100px; top:290px; margin:0;
  max-height:142px; color:var(--kz-deep-text); font-size:59px;
  line-height:1.2; font-weight:700;
}
.tpl-kangzhe .slide.ending-slide { padding:0 !important; background:var(--kz-white); }
.ending-hero {
  position:absolute; left:0; top:0; width:1280px; height:565px;
  background-color:var(--kz-white);
  background-image:var(--ending-hero-image,var(--cover-hero-image,none));
  background-position:center top; background-size:cover; background-repeat:no-repeat;
}
.ending-wordmark {
  position:absolute; left:52px; top:44px; width:240px; height:50px;
  color:var(--kz-title-gray); font-size:22px; line-height:33px;
  font-weight:700; white-space:nowrap; z-index:3;
}
.ending-focus {
  position:absolute; left:340px; top:220px; width:600px; height:200px;
  border:0; border-radius:0; background:transparent; box-shadow:none;
}
.ending-thanks {
  position:absolute; left:0; right:0; top:14px; margin:0;
  color:var(--kz-title-gray); font-size:68px; line-height:1.2;
  font-weight:700; text-align:center;
}
.ending-rule {
  position:absolute; left:380px; top:450px; width:520px; height:4px;
  background:var(--kz-yellow);
}
.ending-meta {
  position:absolute; left:0; right:0; top:495px; margin:0;
  color:var(--kz-body); font-size:18px; line-height:1.2;
  font-weight:400; text-align:center; white-space:nowrap;
}
.ending-ribbon-fallback {
  position:absolute; left:0; top:565px; width:1280px; height:155px;
  background:var(--kz-white); text-align:center;
}
.tpl-kangzhe .slide.content-slide {
  padding:96px 56px 60px !important; background:var(--kz-white);
}
.tpl-kangzhe .slide.content-slide::before {
  content: ""; position: absolute; left: 54px; right: 23px; top: 80px;
  height: 1.5px; background: var(--kz-orange); z-index: 2;
}
.title-row {
  position: absolute; top: 24px; left: 91px; right: 270px;
  min-height: 44px; display: flex; align-items: center; z-index: 3;
}
.title-row::before, .title-row::after {
  content: ""; position: absolute; z-index: -1;
  clip-path: polygon(44% 0,100% 0,57% 100%,0 100%);
}
.title-row::before {
  left: -67px; top: -15px; width: 70px; height: 62px; background: var(--kz-orange);
}
.title-row::after {
  left: -86px; top: 18px; width: 40px; height: 36px; background: var(--kz-yellow);
}
.page-title {
  margin: 0; color: var(--kz-deep-text); font-size: 32px;
  line-height: 1.2; font-weight: 700; letter-spacing: 0;
  min-width: 0; white-space: nowrap;
}
.brand-lockup {
  position: absolute; top: 45px; right: 91px; width: 158px; height: 33px;
  display: flex; align-items: center; justify-content: flex-end;
  color: var(--kz-title-gray); font-family: Arial,var(--font-sans);
  font-size: 17px; line-height: 1; font-weight: 700;
  white-space: nowrap; z-index: 4;
}
.brand-lockup > img { display:block; width:100%; height:100%; object-fit:contain; }
.slide-body {
  position:relative; width:1168px; height:564px;
  min-width:0; min-height:0; margin:0; padding:0 0 72px;
  color:var(--kz-body); font-size:19px; line-height:1.4; font-weight:400;
  overflow:hidden;
}
.slide-body p { margin:0 0 8px; }
.slide-body p:last-child { margin-bottom:0; }
.slide-body :is(strong,b) { font-weight:600; }
.deck-footer {
  position: absolute; bottom: 14px; left: 24px; right: 32px;
  display: flex; align-items: center; justify-content: space-between; gap: 16px;
  color: var(--kz-meta); font-size: 18px; line-height: 1.2; z-index: 5;
}
.footer-id { color: var(--kz-meta); font-weight: 400; white-space: nowrap; }
.slide-number { color: var(--kz-orange); font-weight: 700; white-space: nowrap; }
.slide-number::before, .slide-number::after { content: none; }
.progress-bar {
  position: fixed; left: 0; right: 0; bottom: 0; height: 3px;
  background: transparent; z-index: 100;
}
.progress-bar > span {
  display: block; width: var(--progress, 0%); height: 100%;
  background: var(--kz-orange);
}
.notes, aside.notes { display: none !important; }
.kz-card {
  min-width: 0; min-height: 0; padding: 12px 14px;
  border: 1px solid var(--kz-border); border-radius: 8px;
  background: var(--kz-white); box-shadow: var(--shadow);
  overflow: hidden;
}
.kz-card h3 {
  margin:0 0 6px; font-size:20px; line-height:1.25; font-weight:700;
  overflow-wrap:anywhere;
}
.kz-card p, .kz-card li {
  font-size:16px; line-height:1.35; font-weight:400; overflow-wrap:anywhere;
}
.kz-em-red { color: var(--kz-risk); font-weight: 700; }
.stat-strip {
  display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:16px; height:120px;
}
.stat-strip__item {
  display:flex; flex-direction:column; justify-content:center;
  padding:14px 16px; border:1px solid var(--kz-border-weak); border-radius:8px;
  background:var(--kz-white); box-shadow:var(--shadow-1);
}
.stat-strip__num { color:var(--kz-orange); font-size:32px; line-height:1.2; font-weight:700; }
.stat-strip__label { margin-top:8px; color:var(--kz-meta); font-size:16px; font-weight:600; }
.chart-stage { height:360px; }
.slide-body > .chart-stage { height:492px; }
.slide-body > .stat-strip + .chart-stage,
.two-layer .chart-stage { height:340px; }
.matrix-layout {
  display:grid; grid-template-columns:760px minmax(0,1fr); gap:24px;
  align-items:start; height:492px;
}
.matrix-chart { height:430px; }
.matrix-callouts { display:grid; gap:14px; align-content:start; }
.matrix-callouts .kz-card { min-height:0; }
.slide-body > .kz-card:first-child:nth-last-child(2) { min-height:412px; }
.slide-body > .kz-card:only-child { min-height:492px; }
.chart-stage svg { display:block; width:100%; height:auto; max-height:100%; }
.content-conclusion {
  position:absolute; left:0; right:0; bottom:0; min-height:52px; max-height:68px;
  display:flex; align-items:center; padding:8px 16px;
  border:1px solid var(--kz-border-weak); border-left:4px solid var(--kz-orange);
  border-radius:8px; background:var(--kz-white); box-shadow:var(--shadow-1);
  font-size:16px; line-height:1.3; color:var(--kz-deep-text);
  overflow:hidden;
}
.disclosure-list { display:grid; gap:6px; align-content:start; max-height:492px; }
.disclosure-list--dense { grid-template-columns:1fr 1fr; gap:6px 10px; }
.disclosure-row {
  display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1.4fr) minmax(72px,.5fr);
  gap:8px; align-items:start; min-width:0; min-height:0;
  padding:6px 8px; border:1px solid var(--kz-border-weak); border-radius:6px;
  font-size:16px; line-height:1.25;
}
.disclosure-row > span { min-width:0; overflow-wrap:break-word; word-break:keep-all; }
.disclosure-row .state {
  font-weight:700; color:var(--kz-orange);
  overflow-wrap:anywhere; white-space:normal;
}
.kz-card .disclosure-list { max-height:none; grid-template-columns:1fr; gap:4px; }
.kz-card .disclosure-row { padding:4px 6px; }
.endpoint-grid {
  grid-template-rows:repeat(2,minmax(0,1fr)); height:412px;
  align-items:stretch;
}
.endpoint-card {
  display:flex; flex-direction:column; justify-content:center;
  padding:18px 20px; overflow:hidden;
}
.endpoint-card h3 { margin-bottom:12px; font-size:18px; line-height:1.35; }
.endpoint-card p { margin:0; font-size:20px; line-height:1.4; color:var(--kz-deep-text); }
.two-layer { display:flex; flex-direction:column; height:564px; gap:16px; }
.two-layer .main { flex:1 1 auto; min-height:0; }
"""
