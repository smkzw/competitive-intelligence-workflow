/* Kangzhe HTML-PPT FX v1.1 — copy verbatim from design_specs/assets/htmlppt/gx_fx.js */
(function () {
  'use strict';
  if (document.getElementById('gx-fx-boot')) return;
  var mark = document.createElement('meta');
  mark.id = 'gx-fx-boot';
  document.head.appendChild(mark);

  function frozen() {
    var d = document.documentElement;
    return d.dataset.export === 'true' || d.dataset.qc === 'true';
  }
  function reduce() {
    return window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }
  function heroSlide(s) {
    return s && (s.classList.contains('cover-slide') || s.classList.contains('toc-slide') ||
      s.classList.contains('section-slide') || s.classList.contains('ending-slide'));
  }

  var SVG = '' +
    '<svg class="gx-svg-defs" aria-hidden="true" width="0" height="0" focusable="false">' +
      '<filter id="gx-glass" x="-8%" y="-8%" width="116%" height="116%" filterUnits="objectBoundingBox" color-interpolation-filters="sRGB">' +
        '<feTurbulence type="fractalNoise" baseFrequency="0.009 0.012" numOctaves="1" seed="7" result="turb"/>' +
        '<feGaussianBlur in="turb" stdDeviation="1.4" result="soft"/>' +
        '<feDisplacementMap in="SourceGraphic" in2="soft" scale="16" xChannelSelector="R" yChannelSelector="G"/>' +
      '</filter>' +
    '</svg>';

  function ensureSvg() {
    if (!document.querySelector('.gx-svg-defs')) document.body.insertAdjacentHTML('afterbegin', SVG);
  }
  function ensureGrain() {
    if (document.querySelector('.gx-grain')) return;
    var g = document.createElement('div');
    g.className = 'gx-grain';
    g.setAttribute('aria-hidden', 'true');
    document.body.appendChild(g);
  }
  function addEnv(slide) {
    if (!slide || !heroSlide(slide) || slide.querySelector(':scope > .gx-env')) return;
    var env = document.createElement('div');
    env.className = 'gx-env';
    env.setAttribute('aria-hidden', 'true');
    env.innerHTML = '<i class="gx-blob a"></i><i class="gx-blob b"></i><i class="gx-blob c"></i><i class="gx-caustic"></i><i class="gx-dust"></i>';
    slide.insertBefore(env, slide.firstChild);
  }

  var GLASS_SEL = '.toc-item';
  function layerGlass(root) {
    (root || document).querySelectorAll(GLASS_SEL).forEach(function (c) {
      if (c.querySelector(':scope > .gx-refract')) return;
      var fx = document.createElement('div');
      fx.className = 'gx-refract';
      fx.setAttribute('aria-hidden', 'true');
      c.insertBefore(fx, c.firstChild);
      if (!c.querySelector(':scope > .gx-sheen')) {
        var sh = document.createElement('div');
        sh.className = 'gx-sheen';
        sh.setAttribute('aria-hidden', 'true');
        c.appendChild(sh);
      }
    });
  }

  function netFor(slide, extra) {
    if (!slide || slide.querySelector(':scope > canvas.gx-net') || reduce()) return;
    var canvas = document.createElement('canvas');
    canvas.className = 'gx-net';
    canvas.setAttribute('aria-hidden', 'true');
    slide.insertBefore(canvas, slide.firstChild);
    var ctx = canvas.getContext('2d');
    if (!ctx) return;
    var dpr = Math.min(window.devicePixelRatio || 1, 1.5);
    var W = 1280, H = 720, nodes = [], raf = null;
    var nCount = extra ? 48 : 32;
    function size() {
      canvas.width = W * dpr; canvas.height = H * dpr;
      canvas.style.width = W + 'px'; canvas.style.height = H + 'px';
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    function seed() {
      nodes = [];
      for (var i = 0; i < nCount; i++) {
        nodes.push({
          x: Math.random() * W, y: Math.random() * H,
          vx: (Math.random() - .5) * .18, vy: (Math.random() - .5) * .18,
          r: 1 + Math.random() * 1.4,
          c: i % 3 === 0 ? '64,122,170' : (i % 3 === 1 ? '255,153,0' : '255,204,0')
        });
      }
    }
    function draw() {
      ctx.clearRect(0, 0, W, H);
      var i, j, a, b, d;
      for (i = 0; i < nodes.length; i++) {
        a = nodes[i];
        a.x += a.vx; a.y += a.vy;
        if (a.x < 0 || a.x > W) a.vx *= -1;
        if (a.y < 0 || a.y > H) a.vy *= -1;
        ctx.fillStyle = 'rgba(' + a.c + ',.32)';
        ctx.beginPath(); ctx.arc(a.x, a.y, a.r, 0, 6.2832); ctx.fill();
        for (j = i + 1; j < nodes.length; j++) {
          b = nodes[j];
          d = Math.hypot(a.x - b.x, a.y - b.y);
          if (d < 108) {
            ctx.strokeStyle = 'rgba(255,153,0,' + ((1 - d / 108) * .13).toFixed(3) + ')';
            ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
          }
        }
      }
    }
    function loop() { draw(); raf = requestAnimationFrame(loop); }
    function live() { return slide.classList.contains('is-active') && !frozen() && !document.hidden && !reduce(); }
    function sync() {
      if (live() && raf === null) loop();
      else if (!live() && raf !== null) { cancelAnimationFrame(raf); raf = null; ctx.clearRect(0, 0, W, H); }
    }
    size(); seed();
    new MutationObserver(sync).observe(slide, { attributes: true, attributeFilter: ['class'] });
    document.addEventListener('visibilitychange', sync);
    window.addEventListener('hashchange', function () { setTimeout(sync, 80); });
    sync();
  }

  var GEM_RE = /^(Q4W|Q2W|W24|W16|W52|W12|W2|W4|D9|D8|D15|D29|1:1|600\s*mg|300\s*mg|210|175|1505)$/i;
  function markGems(root) {
    if (!root) return;
    var body = root.querySelector('.slide-body') || root;
    var ems = body.querySelectorAll('strong, b, .kz-em-red, .kz-em-underline, .r');
    for (var e = 0; e < ems.length; e++) {
      var em = ems[e];
      if (em.closest('aside, .notes')) continue;
      em.classList.add('gx-em');
      if (em.classList.contains('kz-em-red') || em.classList.contains('r')) em.classList.add('gx-em-red');
      var et = (em.textContent || '').trim();
      if (et.length > 0 && et.length <= 18) em.classList.add('gx-em-short');
    }
    var nodes = body.querySelectorAll('div, span, .stat-strip__num, .anchor-cell .v');
    for (var i = 0; i < nodes.length; i++) {
      var el = nodes[i];
      if (el.closest('aside, .notes')) continue;
      if (el.classList.contains('gx-gem') || el.classList.contains('gx-em')) continue;
      if (el.children.length) continue;
      var t = (el.textContent || '').trim();
      if (GEM_RE.test(t) && (el.tagName === 'STRONG' || el.tagName === 'B' || el.classList.contains('r') || el.classList.contains('kz-em-red'))) {
        el.classList.add('gx-gem');
      }
    }
  }

  function isBrandFill(el) {
    var f = (el.getAttribute('fill') || '').toLowerCase();
    if (!f || f === 'none' || f === '#fff' || f === '#ffffff' || f === 'white') return false;
    return /#ff9|#ffa|#ffc|#f79|#d99|#407|#587|#c00|#a85|#f5a|#ed8|#e08|#b06|#2e7|#fac|#fbe/.test(f);
  }
  function isBrandStroke(el) {
    var s = (el.getAttribute('stroke') || '').toLowerCase();
    if (!s || s === 'none' || s === '#e8e4de' || s === '#aaa6a1' || s === '#efefef' || s === '#d6d2cd') return false;
    return /#ff9|#ffa|#407|#c00|#587|#a85|#f79/.test(s) || (el.getAttribute('stroke-width') && parseFloat(el.getAttribute('stroke-width')) >= 2 && s !== '#404040');
  }
  function animateCharts(slide) {
    if (!slide || reduce() || slide.dataset.gxChart === '1') return;
    var svgs = slide.querySelectorAll('.slide-body svg');
    if (!svgs.length) return;
    slide.dataset.gxChart = '1';
    for (var s = 0; s < svgs.length; s++) {
      var svg = svgs[s];
      var rects = svg.querySelectorAll('rect');
      for (var i = 0; i < rects.length; i++) {
        var r = rects[i];
        var w = parseFloat(r.getAttribute('width') || 0);
        var h = parseFloat(r.getAttribute('height') || 0);
        if (w < 6 || h < 6) continue;
        if (!isBrandFill(r) && w < 40 && h < 16) continue;
        if (!isBrandFill(r) && h <= 4) continue;
        if (!isBrandFill(r)) continue;
        r.classList.add(w > h * 1.5 ? 'gx-bar-h' : 'gx-bar-v');
        r.style.animationDelay = (i % 8) * 0.05 + 's';
      }
      var strokes = svg.querySelectorAll('polyline, path, line');
      for (var j = 0; j < strokes.length; j++) {
        var p = strokes[j];
        if (!isBrandStroke(p) && p.tagName.toLowerCase() !== 'polyline') continue;
        if (p.tagName.toLowerCase() === 'line' && !isBrandStroke(p)) continue;
        try {
          var len = p.getTotalLength ? p.getTotalLength() : 0;
          if (!len || len < 12 || len > 4000) continue;
          p.style.setProperty('--gx-len', String(Math.round(len)));
          p.classList.add('gx-draw');
        } catch (e) {}
      }
    }
  }

  var CARD_SEL = '.toc-item, .blk, .stat-strip__item, .anchor-cell';
  var deck = document.querySelector('.deck');
  var hoverCard = null, raf = 0, px = 0, py = 0;

  function applyHover() {
    raf = 0;
    if (frozen() || !deck) return;
    var r = deck.getBoundingClientRect();
    deck.style.setProperty('--mx', (((px - r.left) / r.width) * 100).toFixed(2) + '%');
    deck.style.setProperty('--my', (((py - r.top) / r.height) * 100).toFixed(2) + '%');
    var el = document.elementFromPoint(px, py);
    var card = el && el.closest ? el.closest(CARD_SEL) : null;
    if (hoverCard && hoverCard !== card) {
      hoverCard.classList.remove('is-lit');
      hoverCard.style.removeProperty('transform');
      hoverCard.style.setProperty('--lx', '-200%');
      hoverCard.style.setProperty('--ly', '-200%');
      hoverCard = null;
    }
    if (!card || reduce()) return;
    hoverCard = card;
    card.classList.add('is-lit');
    var cr = card.getBoundingClientRect();
    var lx = (px - cr.left) / cr.width;
    var ly = (py - cr.top) / cr.height;
    card.style.setProperty('--lx', (lx * 100).toFixed(1) + '%');
    card.style.setProperty('--ly', (ly * 100).toFixed(1) + '%');
    var rx = Math.max(-5, Math.min(5, (ly - .5) * -8));
    var ry = Math.max(-6, Math.min(6, (lx - .5) * 10));
    card.style.transform = 'perspective(860px) rotateX(' + rx.toFixed(2) + 'deg) rotateY(' + ry.toFixed(2) + 'deg) translateY(-2px)';
  }

  window.addEventListener('pointermove', function (e) {
    if (frozen()) return;
    px = e.clientX; py = e.clientY;
    if (!raf) raf = requestAnimationFrame(applyHover);
  }, { passive: true });
  window.addEventListener('pointerleave', function () {
    if (hoverCard) {
      hoverCard.classList.remove('is-lit');
      hoverCard.style.removeProperty('transform');
      hoverCard = null;
    }
  }, { passive: true });

  function onSlide(slide) {
    if (!slide) return;
    markGems(slide);
    animateCharts(slide);
  }

  function wireToc() {
    var slides = Array.prototype.slice.call(document.querySelectorAll('.deck > .slide'));
    var sections = [];
    for (var i = 0; i < slides.length; i++) {
      if (slides[i].classList.contains('section-slide')) sections.push(i);
    }
    document.querySelectorAll('.toc-slide .toc-item').forEach(function (card, idx) {
      var dest = sections[idx];
      if (dest == null) return;
      card.style.cursor = 'pointer';
      card.setAttribute('role', 'link');
      card.setAttribute('aria-label', '跳转到' + ((card.querySelector('.toc-label') || {}).textContent || '本章'));
      function jump(e) {
        e.preventDefault();
        e.stopPropagation();
        var all = document.querySelectorAll('.deck > .slide');
        for (var k = 0; k < all.length; k++) all[k].classList.toggle('is-active', k === dest);
        var next = '#/' + (dest + 1);
        if (location.hash !== next) {
          try { history.replaceState(null, '', location.pathname + location.search + next); }
          catch (err) { location.hash = next; }
        }
      }
      card.addEventListener('click', jump);
      card.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') jump(e);
      });
    });
  }

  function boot() {
    if (frozen() || /[?&]preview=/.test(location.search || '') || /[?&]presenter=1/.test(location.search || '')) return;
    ensureSvg();
    ensureGrain();
    wireToc();
    var slides = document.querySelectorAll('.deck > .slide');
    for (var i = 0; i < slides.length; i++) {
      var s = slides[i];
      if (heroSlide(s)) {
        addEnv(s);
        layerGlass(s);
        if (!reduce()) netFor(s, s.classList.contains('cover-slide') || s.classList.contains('ending-slide'));
      }
    }
    var active = document.querySelector('.slide.is-active');
    onSlide(active);
    slides.forEach(function (s) {
      new MutationObserver(function () {
        if (s.classList.contains('is-active')) onSlide(s);
      }).observe(s, { attributes: true, attributeFilter: ['class'] });
    });
    window.addEventListener('hashchange', function () {
      setTimeout(function () { onSlide(document.querySelector('.slide.is-active')); }, 80);
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
