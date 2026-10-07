"""1007V1: reveal binding must preserve ABC grid layout ownership and remount shape.

Behavioral family checks only — not visual/PPT/browser acceptance.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "src/ci_workflow/renderers/portal/assets"

# Minimal DOM + stubs enough to execute production kangzhe-site.js mount path.
HARNESS = r"""
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const assets = process.argv[1];
const mode = process.argv[2];

function classList(el) {
  return {
    add(...names) {
      names.flatMap((n) => String(n).split(/\s+/)).filter(Boolean)
        .forEach((n) => el._classes.add(n));
      el.className = [...el._classes].join(' ');
    },
    remove(...names) {
      names.forEach((n) => el._classes.delete(n));
      el.className = [...el._classes].join(' ');
    },
    contains(name) { return el._classes.has(name); },
    toggle(name, force) {
      const on = force === undefined ? !el._classes.has(name) : !!force;
      if (on) el._classes.add(name); else el._classes.delete(name);
      el.className = [...el._classes].join(' ');
      return on;
    },
  };
}

function datasetProxy(el) {
  return new Proxy({}, {
    get(_t, key) {
      if (typeof key !== 'string') return undefined;
      const attr = 'data-' + key.replace(/[A-Z]/g, (m) => '-' + m.toLowerCase());
      return el._attrs[attr];
    },
    set(_t, key, value) {
      const attr = 'data-' + String(key).replace(/[A-Z]/g, (m) => '-' + m.toLowerCase());
      el._attrs[attr] = value === undefined || value === null ? '' : String(value);
      return true;
    },
    has(_t, key) {
      const attr = 'data-' + String(key).replace(/[A-Z]/g, (m) => '-' + m.toLowerCase());
      return Object.prototype.hasOwnProperty.call(el._attrs, attr);
    },
  });
}

function matchesSimple(el, selector) {
  selector = selector.trim();
  if (!selector) return false;
  if (selector.includes(':')) {
    const base = selector.split(':')[0];
    return base ? matchesSimple(el, base) : false;
  }
  if (selector.startsWith('.')) return el._classes.has(selector.slice(1));
  if (selector.startsWith('#')) return el.id === selector.slice(1);
  if (selector.startsWith('[') && selector.endsWith(']')) {
    const body = selector.slice(1, -1);
    if (body.startsWith('data-') && !body.includes('=')) return el.hasAttribute(body);
    const eq = body.indexOf('=');
    if (eq < 0) return el.hasAttribute(body);
    const key = body.slice(0, eq);
    let val = body.slice(eq + 1).trim();
    if ((val.startsWith('"') && val.endsWith('"'))
        || (val.startsWith("'") && val.endsWith("'"))) val = val.slice(1, -1);
    return el.getAttribute(key) === val;
  }
  return el.tagName.toLowerCase() === selector.toLowerCase();
}

function matches(el, selector) {
  return String(selector).split(',').some((part) => {
    const tokens = part.trim().split(/\s+/).filter(Boolean);
    return tokens.every((token) => matchesSimple(el, token));
  });
}

function createEl(tag, ownerDocument) {
  const el = {
    tagName: String(tag).toUpperCase(),
    ownerDocument,
    parentElement: null,
    childNodes: [],
    _classes: new Set(),
    _attrs: {},
    style: {},
    hidden: false,
    id: '',
    textContent: '',
    isConnected: true,
  };
  Object.defineProperty(el, 'className', {
    get() { return [...el._classes].join(' '); },
    set(value) {
      el._classes = new Set(String(value || '').split(/\s+/).filter(Boolean));
    },
  });
  el.classList = classList(el);
  el.dataset = datasetProxy(el);
  el.setAttribute = function (key, value) {
    if (key === 'class') { el.className = value; return; }
    if (key === 'id') { el.id = String(value); return; }
    el._attrs[key] = String(value);
  };
  el.getAttribute = function (key) {
    if (key === 'class') return el.className;
    if (key === 'id') return el.id || null;
    return Object.prototype.hasOwnProperty.call(el._attrs, key) ? el._attrs[key] : null;
  };
  el.hasAttribute = function (key) {
    if (key === 'class') return el._classes.size > 0;
    if (key === 'id') return !!el.id;
    return Object.prototype.hasOwnProperty.call(el._attrs, key);
  };
  el.removeAttribute = function (key) {
    if (key === 'class') { el._classes.clear(); return; }
    if (key === 'id') { el.id = ''; return; }
    delete el._attrs[key];
  };
  el.appendChild = function (child) {
    if (child.parentElement) child.parentElement.removeChild(child);
    child.parentElement = el;
    el.childNodes.push(child);
    return child;
  };
  el.append = function (...nodes) { nodes.forEach((n) => el.appendChild(n)); };
  el.removeChild = function (child) {
    const idx = el.childNodes.indexOf(child);
    if (idx >= 0) el.childNodes.splice(idx, 1);
    if (child.parentElement === el) child.parentElement = null;
    return child;
  };
  el.before = function (node) {
    const parent = el.parentElement;
    assert.ok(parent, 'before() requires parent');
    if (node.parentElement) node.parentElement.removeChild(node);
    const idx = parent.childNodes.indexOf(el);
    parent.childNodes.splice(idx, 0, node);
    node.parentElement = parent;
  };
  el.querySelector = function (selector) {
    const all = el.querySelectorAll(selector);
    return all[0] || null;
  };
  el.querySelectorAll = function (selector) {
    const out = [];
    (function walk(node) {
      for (const child of node.childNodes) {
        if (matches(child, selector)) out.push(child);
        walk(child);
      }
    })(el);
    return out;
  };
  el.matches = function (selector) { return matches(el, selector); };
  el.closest = function (selector) {
    for (let n = el; n; n = n.parentElement) if (matches(n, selector)) return n;
    return null;
  };
  Object.defineProperty(el, 'firstChild', { get() { return el.childNodes[0] || null; } });
  Object.defineProperty(el, 'firstElementChild', { get() { return el.childNodes[0] || null; } });
  Object.defineProperty(el, 'children', { get() { return el.childNodes.slice(); } });
  return el;
}

function buildDocument(siteClass) {
  const document = {
    hidden: false,
    body: null,
    _listeners: {},
  };
  document.createElement = (tag) => createEl(tag, document);
  document.querySelector = (selector) => {
    if (!document.documentElement) return null;
    if (matches(document.documentElement, selector)) return document.documentElement;
    if (document.body && matches(document.body, selector)) return document.body;
    return document.documentElement.querySelector(selector);
  };
  document.querySelectorAll = (selector) => {
    const out = [];
    if (document.body && matches(document.body, selector)) out.push(document.body);
    if (document.documentElement) out.push(...document.documentElement.querySelectorAll(selector));
    return out;
  };
  document.addEventListener = (type, fn, opts) => {
    (document._listeners[type] ||= []).push({ fn, opts });
  };
  document.documentElement = createEl('html', document);
  const body = createEl('body', document);
  body.className = siteClass;
  body.dataset.kzDesign = '6.0';
  document.body = body;
  document.documentElement.appendChild(body);

  const head = createEl('header', document);
  head.className = 'portal-page-head';
  body.appendChild(head);

  // A: sparse / dense / mixed-span ownership inside one grid.
  const hero = createEl('section', document);
  hero.className = 'kz-a-hero-grid';
  hero.setAttribute('data-grid-owner', 'a-hero');
  const wide = createEl('article', document);
  wide.className = 'kz-a-summary kz-a-summary--wide';
  wide.setAttribute('data-summary-module', 'landscape');
  wide.setAttribute('data-fact', 'wide-landscape');
  const chart = createEl('div', document);
  chart.className = 'kz-chart';
  chart.textContent = 'chart-fact';
  wide.appendChild(chart);
  const dense = createEl('article', document);
  dense.className = 'kz-a-summary';
  dense.setAttribute('data-grid-span', '12');
  dense.setAttribute('data-fact', 'dense-12');
  const note = createEl('p', document);
  note.textContent = 'dense-text';
  dense.appendChild(note);
  const mixed4 = createEl('article', document);
  mixed4.className = 'kz-a-summary';
  mixed4.setAttribute('data-grid-span', '4');
  mixed4.setAttribute('data-fact', 'span-4');
  mixed4.appendChild(Object.assign(createEl('div', document),
    { className: 'kz-chart', textContent: 'm4' }));
  const mixed6 = createEl('article', document);
  mixed6.className = 'kz-a-summary';
  mixed6.setAttribute('data-grid-span', '6');
  mixed6.setAttribute('data-fact', 'span-6');
  mixed6.appendChild(Object.assign(createEl('div', document),
    { className: 'kz-chart', textContent: 'm6' }));
  hero.append(wide, dense, mixed4, mixed6);
  body.appendChild(hero);

  // B/C section hosts (non-tilt path keeps id/direct-child contracts).
  const bVisual = createEl('section', document);
  bVisual.className = 'kz-b-visual-section';
  bVisual.setAttribute('data-fact', 'b-visual');
  bVisual.appendChild(Object.assign(createEl('h2', document), { textContent: 'B视觉' }));
  const bNotes = createEl('section', document);
  bNotes.className = 'kz-b-reading-notes';
  bNotes.setAttribute('data-fact', 'b-notes');
  bNotes.appendChild(Object.assign(createEl('p', document), { textContent: 'reading-fact' }));
  const cPath = createEl('section', document);
  cPath.className = 'kz-c-path-section';
  cPath.id = 'kz-design-paths';
  cPath.setAttribute('data-fact', 'c-path');
  cPath.appendChild(Object.assign(createEl('h2', document), { textContent: '路径' }));
  const cVisual = createEl('section', document);
  cVisual.className = 'kz-c-visual-section';
  cVisual.setAttribute('data-fact', 'c-visual');
  body.append(bVisual, bNotes, cPath, cVisual);

  const panel = createEl('section', document);
  panel.className = 'kz-a-panel';
  panel.setAttribute('data-module', 'safety');
  panel.setAttribute('data-fact', 'a-panel');
  panel.appendChild(Object.assign(createEl('h2', document), { textContent: '安全' }));
  body.appendChild(panel);

  return { document, head, hero, wide, dense, mixed4, mixed6, bNotes, cPath, panel };
}

function installMotionStub(window) {
  window.KZMotion = {
    mountPage() {
      return { enter() {}, finish() {}, dispose() {} };
    },
    Film: class {
      constructor() {}
      pause() {}
      resume() {}
      dispose() {}
      snapshot() { return { ok: true }; }
    },
  };
}

function loadSite(window, document) {
  const sandbox = {
    window,
    document,
    AbortController,
    MutationObserver: class { constructor() {} observe() {} disconnect() {} },
    queueMicrotask,
    console,
  };
  sandbox.global = sandbox;
  sandbox.self = sandbox;
  installMotionStub(window);
  window.document = document;
  window.addEventListener = (type, fn) => {
    (window._listeners ||= {})[type] ||= []; window._listeners[type].push(fn);
  };
  window.matchMedia = (query) => ({
    matches: String(query).includes('prefers-reduced-motion') && window.__RM === true,
    addEventListener() {},
    removeEventListener() {},
  });
  vm.runInNewContext(fs.readFileSync(assets + '/kangzhe-site.js', 'utf8'), sandbox);
  return sandbox;
}

function gridItemFor(factNode) {
  let n = factNode;
  while (n && n.parentElement && !n.parentElement.classList.contains('kz-a-hero-grid')
    && n.parentElement.id !== 'kz-chart-module'
    && !n.parentElement.classList.contains('kz-chart-module')) {
    // climb to the element that sits in the layout parent
    if (n.parentElement.classList.contains('kz-a-hero-grid')) break;
    n = n.parentElement;
  }
  // Prefer the direct child of the hero grid when present.
  if (factNode.closest) {
    const hero = factNode.closest('.kz-a-hero-grid');
    if (hero) {
      for (const child of hero.childNodes) {
        const fact = factNode.getAttribute('data-fact');
        if (child === factNode
            || child.querySelector && child.querySelector(`[data-fact="${fact}"]`)
            || child.getAttribute?.('data-fact') === fact) {
          return child;
        }
      }
    }
  }
  return factNode.parentElement && factNode.parentElement.classList.contains('kz-content-reveal')
    ? factNode.parentElement
    : factNode;
}

function assertOwnership(document) {
  const hero = document.querySelector('.kz-a-hero-grid');
  assert.ok(hero);
  const items = hero.childNodes.slice();
  assert.equal(items.length, 4, 'hero grid must keep four layout items');

  function itemFor(fact) {
    for (const child of items) {
      if (child.getAttribute('data-fact') === fact) return child;
      if (child.querySelector && child.querySelector(`[data-fact="${fact}"]`)) return child;
    }
    return null;
  }

  const wideItem = itemFor('wide-landscape');
  assert.ok(wideItem, 'wide fact missing');
  assert.equal(
    wideItem.classList.contains('kz-a-summary--wide')
      || wideItem.getAttribute('data-grid-span') === '12',
    true,
    'wide/full-span layout contract must live on the grid item',
  );
  assert.ok(wideItem.hasAttribute('data-kz-reveal')
      || wideItem.classList.contains('kz-content-reveal'),
    'wide item must participate in reveal without losing layout');

  const denseItem = itemFor('dense-12');
  assert.ok(denseItem);
  assert.equal(denseItem.getAttribute('data-grid-span'), '12', 'dense span must stay on grid item');

  const span4 = itemFor('span-4');
  const span6 = itemFor('span-6');
  assert.equal(span4.getAttribute('data-grid-span'), '4');
  assert.equal(span6.getAttribute('data-grid-span'), '6');

  // C path keeps id on the layout-owning node (direct-child CSS contract).
  const path = document.querySelector('#kz-design-paths');
  assert.ok(path);
  assert.equal(path.classList.contains('kz-c-path-section'), true);
  assert.equal(path.hasAttribute('data-kz-reveal'), true, 'path reveal should bind in place');
  assert.equal(path.parentElement.classList.contains('kz-content-reveal'), false,
    'path must not be outer-wrapped away from id/direct-child selectors');
  assert.equal(path.querySelector('h2').textContent, '路径');

  // Panel child heading contract preserved (no inner drain of > h2).
  const panel = document.querySelector('.kz-a-panel');
  assert.equal(panel.hasAttribute('data-kz-reveal'), true);
  assert.equal(panel.childNodes.some((n) => n.tagName === 'H2'), true);

  // Facts survive.
  for (const fact of ['wide-landscape', 'dense-12', 'span-4', 'span-6',
      'b-visual', 'b-notes', 'c-path', 'a-panel']) {
    assert.ok(document.querySelector(`[data-fact="${fact}"]`), 'missing fact ' + fact);
  }
}

function remount(window) {
  const hide = (window._listeners || {}).pagehide || [];
  const show = (window._listeners || {}).pageshow || [];
  hide.forEach((fn) => fn({}));
  show.forEach((fn) => fn({}));
}

function countRevealShells(document) {
  return document.querySelectorAll('.kz-content-reveal').length;
}

function countRevealTargets(document) {
  return document.querySelectorAll('[data-kz-reveal]').length;
}

if (mode === 'ownership') {
  const { document } = buildDocument('kz-a-site kz-b-site kz-c-site');
  const window = { __RM: false };
  loadSite(window, document);
  assertOwnership(document);
  const notes = document.querySelector('.kz-b-reading-notes');
  assert.ok(notes);
  // Reading notes have no data plane: reveal+tilt must not share one transform owner.
  const tiltOnNotes = notes.hasAttribute('data-kz-tilt');
  const revealOnNotes = notes.hasAttribute('data-kz-reveal');
  if (tiltOnNotes && revealOnNotes) {
    assert.fail('tilt and reveal must not share the notes node transform');
  }
  if (tiltOnNotes) {
    assert.equal(notes.parentElement.classList.contains('kz-content-reveal'), true);
    assert.equal(notes.parentElement.hasAttribute('data-kz-reveal'), true);
  }
} else if (mode === 'lifecycle') {
  const { document } = buildDocument('kz-a-site');
  const window = { __RM: false };
  loadSite(window, document);
  assertOwnership(document);
  const beforeShells = countRevealShells(document);
  const beforeTargets = countRevealTargets(document);
  const beforeFacts = document.querySelectorAll('[data-fact]')
    .map((n) => n.getAttribute('data-fact')).sort().join(',');
  remount(window);
  remount(window);
  assertOwnership(document);
  assert.equal(countRevealShells(document), beforeShells, 'remount must not nest reveal shells');
  assert.equal(countRevealTargets(document), beforeTargets,
    'remount must not duplicate reveal targets');
  const afterFacts = document.querySelectorAll('[data-fact]')
    .map((n) => n.getAttribute('data-fact')).sort().join(',');
  assert.equal(afterFacts, beforeFacts, 'remount must not move/drop facts');
} else if (mode === 'reduced-motion') {
  const { document } = buildDocument('kz-a-site kz-c-site');
  const window = { __RM: true };
  loadSite(window, document);
  assertOwnership(document);
  assert.ok(countRevealTargets(document) > 0, 'RM still keeps reveal structure targets');
  const path = document.querySelector('#kz-design-paths');
  assert.equal(path.hasAttribute('data-kz-reveal'), true);
} else {
  assert.fail('unknown mode ' + mode);
}
"""


@pytest.mark.parametrize("mode", ["ownership", "lifecycle", "reduced-motion"])
def test_reveal_preserves_abc_grid_layout_ownership_family(mode: str) -> None:
    result = subprocess.run(
        ["node", "-e", HARNESS, str(ASSETS), mode],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
