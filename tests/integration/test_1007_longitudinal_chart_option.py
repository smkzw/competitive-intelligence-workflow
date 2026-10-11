"""Production charts.js longitudinal line option. Node is not browser acceptance."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CHARTS = ROOT / "src/ci_workflow/renderers/portal/assets/charts.js"

PROBE = r"""
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(process.argv[1], 'utf8');

const byId = {};
function hasClass(el, name) {
  if (el.classSet && el.classSet.has(name)) return true;
  return String(el.className || '').split(/\s+/).includes(name);
}
function matches(el, sel) {
  if (!el || !sel) return false;
  const classMatch = sel.match(/^\.([^[\s]+)/);
  if (classMatch && !hasClass(el, classMatch[1])) return false;
  const attr = sel.match(/\[([^\]]+)="([^"]*)"\]/);
  if (attr && el.attributes[attr[1]] !== attr[2]) return false;
  return !!(classMatch || attr);
}
function walk(root, sel) {
  const out = [];
  (function rec(node) {
    for (const child of node.children || []) {
      if (matches(child, sel)) out.push(child);
      rec(child);
    }
  })(root);
  return out;
}
function createNode() {
  const el = {
    style: {},
    attributes: {},
    children: [],
    className: '',
    textContent: '',
    hidden: false,
    parentElement: null,
    tabIndex: 0,
    classSet: new Set(),
    setAttribute(key, value) {
      this.attributes[key] = String(value);
      if (key === 'id') byId[String(value)] = this;
    },
    getAttribute(key) { return this.attributes[key]; },
    removeAttribute(key) { delete this.attributes[key]; },
    appendChild(child) {
      child.parentElement = this;
      this.children.push(child);
      return child;
    },
    insertBefore(child) { return this.appendChild(child); },
    remove() {
      const parent = this.parentElement;
      if (!parent) return;
      const index = parent.children.indexOf(this);
      if (index >= 0) parent.children.splice(index, 1);
      this.parentElement = null;
    },
    addEventListener() {},
    querySelectorAll(sel) { return walk(this, sel); },
    querySelector(sel) { return walk(this, sel)[0] || null; },
    closest(sel) {
      let node = this;
      while (node) {
        if (matches(node, sel)) return node;
        node = node.parentElement;
      }
      return null;
    },
    scrollIntoView() {},
    focus() {},
  };
  el.classList = {
    add(name) {
      el.classSet.add(name);
      el.className = Array.from(el.classSet).join(' ');
    },
    remove(name) {
      el.classSet.delete(name);
      el.className = Array.from(el.classSet).join(' ');
    },
    toggle(name, on) { if (on) el.classList.add(name); else el.classList.remove(name); },
    contains(name) { return hasClass(el, name); },
  };
  let html = '';
  Object.defineProperty(el, 'innerHTML', {
    get() { return html; },
    set(value) { html = String(value); el.children = []; },
  });
  Object.defineProperty(el, 'id', {
    get() { return el.attributes.id || ''; },
    set(value) { el.setAttribute('id', value); },
  });
  return el;
}

const moduleEl = createNode();
moduleEl.setAttribute('id', 'kz-chart-module');
const documentRef = {
  readyState: 'loading',
  getElementById(id) { return byId[id] || null; },
  createElement() { return createNode(); },
  querySelectorAll(sel) { return walk(moduleEl, sel); },
  querySelector(sel) { return walk(moduleEl, sel)[0] || null; },
  addEventListener() {},
};

const charts = [];
const resizeHandlers = [];
const windowRef = {
  __FILTER_ROWS__: [{id: 'treat-1'}, {id: 'treat-4'}, {id: 'ctrl-4'}],
  __CHART_GROUPS__: [],
  echarts: {
    init(dom) {
      const inst = {
        disposed: false,
        option: null,
        handlers: {},
        dom,
        resized: 0,
        setOption(option) { this.option = option; },
        on(type, fn) { this.handlers[type] = fn; },
        off() {},
        resize() { this.resized += 1; },
        isDisposed() { return this.disposed; },
        dispose() { this.disposed = true; },
        dispatchAction() {},
        getOption() { return this.option || {series: []}; },
      };
      charts.push(inst);
      return inst;
    },
  },
  document: documentRef,
  addEventListener(type, fn) { if (type === 'resize') resizeHandlers.push(fn); },
};
windowRef.window = windowRef;

vm.runInNewContext(source, {
  window: windowRef,
  document: documentRef,
  console,
  Array,
  Object,
  String,
  Math,
  Number,
  Boolean,
  Error,
  JSON,
  Set,
  RegExp,
  isFinite: Number.isFinite,
  parseInt,
  parseFloat,
});

const api = windowRef.__CHART_SYNC__;
const failures = [];
function check(condition, message) {
  if (!condition) failures.push(message);
}
function liveChart() {
  const alive = charts.filter((chart) => !chart.disposed);
  return alive[alive.length - 1] || null;
}
function renderOption(group) {
  charts.length = 0;
  api.clearSelection();
  api.replaceGroups([group]);
  const chart = liveChart();
  if (!chart || !chart.option) throw new Error('line chart option was not built');
  return chart.option;
}
function pointsOf(option) {
  const points = [];
  for (const series of option.series || []) {
    for (const point of series.data || []) points.push({series, point});
  }
  return points;
}
function idsOf(option) {
  return pointsOf(option).map((item) => item.point && item.point._row_id);
}
function yOf(point) {
  if (!point) return undefined;
  const value = point.value;
  return Array.isArray(value) ? value[1] : value;
}
function xOf(point) {
  if (!point || !Array.isArray(point.value)) return null;
  return point.value[0];
}
function baseRow(extra) {
  return Object.assign({
    _chart_type: 'line',
    renderable: true,
    disclosure_state: 'reported_value',
    display_label_zh: 'EASI-75',
    product_zh: '药A',
    trial_zh: '试验A',
    _chart_identity_key: 'drug-a::trial-a',
    _chart_identity_label: '药A｜试验A',
    arm_role: 'treatment',
    _chart_series_key: 'treatment',
    _chart_series_label: '治疗组',
    unit: '%',
    time_window_band_label_zh: '12–24周',
    _chart_time_key: 'band-12-24',
  }, extra);
}
function qualified(rows, extra) {
  return Object.assign({
    identity_series: true,
    cross_trial: true,
    title_zh: 'EASI-75',
    x_axis_label_zh: '观察时间',
    rows,
  }, extra || {});
}

// Unordered actual visits 24 / 1 / 4 must keep real order and unequal distance.
const unordered = qualified([24, 1, 4].map((time) => baseRow({
  row_id: 'visit-' + time,
  actual_timepoint: time,
  actual_timepoint_unit: 'week',
  numeric_value: time + 10,
  n: 30 + time,
})));
let unorderedOption = null;
try {
  unorderedOption = renderOption(unordered);
  const series = unorderedOption.series[0];
  const xs = series.data.map((point) => point.value[0]);
  check(unorderedOption.xAxis.type === 'value',
    'unordered visits use a numeric time axis, got ' + unorderedOption.xAxis.type);
  check(JSON.stringify(xs) === JSON.stringify([1, 4, 24]), 'temporal order/distance got ' +
    JSON.stringify(xs));
  check(xs[1] - xs[0] !== xs[2] - xs[1], 'visit spacing must not collapse to equal categories');
  check(series.data.length === 3, 'unordered visits fabricated or dropped points');
  check(series.smooth === false && series.connectNulls === false,
    'line must not smooth or bridge gaps');
  check(series.areaStyle && series.areaStyle.opacity <= 0.2 && series.areaStyle.color ===
    series.itemStyle.color,
    'one series may use a low-opacity existing palette area');
  const shown = series.data.filter((point) => point.label && point.label.show).map((point) =>
    point.value[0]);
  check(JSON.stringify(shown) === JSON.stringify([1, 24]),
    'only the first and last of an unmarked series are labeled, got ' + JSON.stringify(shown));
  check(unorderedOption.xAxis.axisLabel.fontSize >= 16 &&
    unorderedOption.yAxis.axisLabel.fontSize >= 16,
    'axis text keeps the 16px floor');
  const tip = unorderedOption.tooltip.formatter({
    seriesName: '<b>治疗组</b>',
    data: series.data[1],
  });
  check(tip.includes('4 周') && tip.includes('14') && tip.includes('%') && tip.includes('N=34'),
    'tooltip missing time/value/unit/N: ' + tip);
  check(!tip.includes('<b>'), 'tooltip inserted source HTML: ' + tip);
  check(tip.includes('&lt;b&gt;'), 'tooltip did not escape native text: ' + tip);
} catch (error) {
  failures.push('unordered render: ' + (error && error.stack || error));
}

// Normal B source projection keeps original text while supplying verified plot coordinates.
try {
  const projected = qualified([24, 1, 4].map((time) => baseRow({
    row_id: 'source-' + time,
    actual_timepoint: 'Week ' + time,
    actual_timepoint_unit: '',
    time: 'Week ' + time,
    _plot_time_value: time,
    _plot_time_unit: 'week',
    numeric_value: time + 10,
    unit: 'participants percentage',
    unit_label_zh: '受试者百分比',
  })), {y_axis_label_zh: '受试者百分比'});
  const before = JSON.stringify(projected.rows);
  const option = renderOption(projected);
  check(option.xAxis.type === 'value', 'source-projected actual visits were not consumed');
  check(JSON.stringify(option.series[0].data.map(xOf)) === JSON.stringify([1, 4, 24]),
    'source-projected visit spacing lost');
  check(option.yAxis.name === '受试者百分比', 'longitudinal axis omitted its unit');
  const tip = option.tooltip.formatter({data: option.series[0].data[0]});
  check(tip.includes('1 周') && tip.includes('受试者百分比') &&
    !tip.includes('participants percentage'),
    'source-projected tooltip uses raw English in place of supplied Chinese: ' + tip);
  check(JSON.stringify(projected.rows) === before,
    'display projection changed original source fields');
} catch (error) {
  failures.push('source-projected visits: ' + (error && error.stack || error));
}

// Same semantic band must not merge week 12 and week 16.
try {
  const sameBand = qualified([12, 16].map((time) => baseRow({
    row_id: 'band-' + time,
    actual_timepoint: time,
    actual_timepoint_unit: 'week',
    numeric_value: time,
    time: '12–24周',
    time_window_band_label_zh: '12–24周',
    _chart_time_key: 'band-12-24',
  })));
  const option = renderOption(sameBand);
  const xs = option.series[0].data.map((point) => point.value[0]);
  check(option.xAxis.type === 'value', 'same-band numeric visits stay on a value axis');
  check(JSON.stringify(xs) === JSON.stringify([12, 16]), 'week 12 and 16 collapsed: ' +
    JSON.stringify(option.xAxis.data || xs));
  check(JSON.stringify(idsOf(option)) === JSON.stringify(['band-12', 'band-16']),
    'same-band row ids dropped');
} catch (error) {
  failures.push('same-band render: ' + (error && error.stack || error));
}

// Mixed units stay categorical original labels; no invented conversion.
try {
  const mixed = qualified([
    baseRow({row_id: 'day-16', actual_timepoint: 16, actual_timepoint_unit: 'day',
      numeric_value: 5, time: '<day>'}),
    baseRow({row_id: 'week-12', actual_timepoint: 12, actual_timepoint_unit: 'week',
      numeric_value: 9, time: '<week>'}),
  ]);
  const option = renderOption(mixed);
  check(option.xAxis.type === 'category', 'mixed units must not share a converted numeric axis');
  check(JSON.stringify(option.xAxis.data) === JSON.stringify(['16 天', '12 周']),
    'mixed-unit labels changed: ' + JSON.stringify(option.xAxis.data));
  check(JSON.stringify(option.series[0].data.map(yOf)) === JSON.stringify([5, 9]),
    'mixed-unit values were converted');
  const tip = option.tooltip.formatter({seriesName: '治疗组', data: option.series[0].data[0]});
  check(tip.includes('16 天') && tip.includes('5') && !tip.includes('<day>'), 'mixed tooltip: '
    + tip);
} catch (error) {
  failures.push('mixed-unit render: ' + (error && error.stack || error));
}

// Non-numeric old qualified groups keep original category labels and row ids.
try {
  const legacy = {
    title_zh: '旧折线',
    rows: [
      {_chart_type: 'line', row_id: 'late', time: '第24周', numeric_value: 3, renderable: true,
        unit: '%', n: 11},
      {_chart_type: 'line', row_id: 'early', time: '第1周<script>', numeric_value: 1, renderable:
        true, unit: '%'},
    ],
  };
  const option = renderOption(legacy);
  check(option.xAxis.type === 'category', 'non-numeric visits became a numeric axis');
  check(JSON.stringify(option.xAxis.data) === JSON.stringify(['第24周', '第1周<script>']),
    'original labels were parsed or rewritten: ' + JSON.stringify(option.xAxis.data));
  check(option.series.length === 1 && option.series[0].name === '趋势',
    'old single series name changed');
  check(option.series[0].smooth === false && option.series[0].connectNulls === false,
    'legacy line bridges nulls');
  check(JSON.stringify(idsOf(option)) === JSON.stringify(['late', 'early']),
    'legacy points lost row ids');
  const tip = option.tooltip.formatter({seriesName: option.series[0].name, data:
    option.series[0].data[1]});
  check(!tip.includes('<script>') && tip.includes('&lt;script&gt;'),
    'legacy tooltip inserted HTML: ' + tip);
} catch (error) {
  failures.push('legacy render: ' + (error && error.stack || error));
}

// True 0 stays 0; an explicit cleared row is a null gap and keeps its id.
try {
  const gap = qualified([
    baseRow({row_id: 0, actual_timepoint: 0, actual_timepoint_unit: 'week', numeric_value: 0,
      n: 20}),
    baseRow({
      row_id: 'cleared', actual_timepoint: 4, actual_timepoint_unit: 'week',
      numeric_value: null, value: null, renderable: false, disclosure_state: 'user_cleared', n: 18,
    }),
    baseRow({row_id: 'end', actual_timepoint: 24, actual_timepoint_unit: 'week', numeric_value:
      8, n: 0}),
  ]);
  const option = renderOption(gap);
  const data = option.series[0].data;
  check(JSON.stringify(data.map(xOf)) === JSON.stringify([0, 4, 24]),
    'cleared visit was dropped or invented: ' + JSON.stringify(data.map(xOf)));
  check(JSON.stringify(data.map(yOf)) === JSON.stringify([0, null, 8]),
    '0/null values changed: ' + JSON.stringify(data.map(yOf)));
  check(data[0]._row_id === '0' && data[1]._row_id === 'cleared', 'null gap or zero id lost');
  check(option._rowIds[0] === 0 && option._rowIds[1] === 'cleared' && option._rowIds[2] === 'end',
    'complete row id list changed: ' + JSON.stringify(option._rowIds));
  check(data.length === 3, 'fabricated a visit around the gap');
  const zeroTip = option.tooltip.formatter({seriesName: '治疗组', data: data[0]});
  const gapTip = option.tooltip.formatter({seriesName: '治疗组', data: data[1]});
  const endTip = option.tooltip.formatter({seriesName: '治疗组', data: data[2]});
  check(zeroTip.includes('0 周') && zeroTip.includes('0') && zeroTip.includes('N=20'),
    'zero tooltip: ' + zeroTip);
  check(gapTip.includes('4 周') && !gapTip.includes('N=0') && gapTip.includes('用户清除'),
    'cleared tooltip fabricated a value: ' + gapTip);
  check(endTip.includes('N=0'), 'available zero N was dropped: ' + endTip);
} catch (error) {
  failures.push('zero/null render: ' + (error && error.stack || error));
}

// 24 visits: label only the ends and a supplied landmark.
try {
  const denseRows = [];
  for (let time = 24; time >= 1; time -= 1) {
    denseRows.push(baseRow({
      row_id: 'd' + time,
      actual_timepoint: time,
      actual_timepoint_unit: 'week',
      numeric_value: time,
      clinical_landmark: time === 8,
    }));
  }
  const option = renderOption(qualified(denseRows));
  const data = option.series[0].data;
  check(data.length === 24 && data[0].value[0] === 1 && data[23].value[0] === 24,
    '24 visits were resampled');
  const shown = data.filter((point) => point.label && point.label.show).map((point) =>
    point.value[0]);
  check(JSON.stringify(shown) === JSON.stringify([1, 8, 24]), 'dense labels: ' +
    JSON.stringify(shown));
  check(data.every((point) => point.label.fontSize >= 16), 'point label text dropped below 16px');
} catch (error) {
  failures.push('dense render: ' + (error && error.stack || error));
}

// Duplicate coordinates are retained. Multiple series do not use array order or area fill.
try {
  const rows = [
    baseRow({
      row_id: 'ctrl-dup', arm_role: 'control', _chart_series_key: 'control',
        _chart_series_label: '对照组',
      actual_timepoint: 12, actual_timepoint_unit: 'week', numeric_value: 2,
    }),
    baseRow({
      row_id: 'treat-a', actual_timepoint: 12, actual_timepoint_unit: 'week', numeric_value: 1,
    }),
    baseRow({
      row_id: 'treat-b', actual_timepoint: 12, actual_timepoint_unit: 'week', numeric_value: 7,
    }),
    baseRow({
      row_id: 'other-1', arm_role: 'unknown', _chart_series_key: 'bg-3',
      _chart_series_label: '第三组',
      actual_timepoint: 16, actual_timepoint_unit: 'week', numeric_value: 4,
    }),
  ];
  const option = renderOption(qualified(rows));
  const reversed = renderOption(qualified(rows.slice().reverse()));
  const values = pointsOf(option).map((item) => yOf(item.point)).sort();
  check(JSON.stringify(values) === JSON.stringify([1, 2, 4, 7]),
    'duplicate coordinate dropped values: ' + JSON.stringify(values));
  check(new Set(idsOf(option).filter((id) => id != null)).size === 4,
    'duplicate coordinate dropped ids: ' + JSON.stringify(idsOf(option)));
  check(option._rowIds.join(',') === 'ctrl-dup,treat-a,treat-b,other-1',
    'table id list lost a duplicate');
  check(option.series.length === 4, 'same-time observations were overwritten, series=' +
    option.series.length);
  check(option.series.every((series) => series.areaStyle == null),
    'more than two series must not fill area');
  check(option.series[0].itemStyle.color === '#FF9900',
    'series order followed array position instead of the treatment role');
  check(!option.series.some((series) => series.name === '治疗组' && series.data.length === 1 &&
    yOf(series.data[0]) !== 1 && yOf(series.data[0]) !== 7),
    'one duplicate treatment value replaced the other');
  const colorById = {};
  for (const item of pointsOf(option)) colorById[item.point._row_id] = item.series.itemStyle.color;
  for (const item of pointsOf(reversed)) {
    check(item.series.itemStyle.color === colorById[item.point._row_id], 'reorder recolored ' +
      item.point._row_id);
  }
  check(option.legend.textStyle.fontSize >= 16 && option.legend.textStyle.color === '#0F1115',
    'legend text is not the stable 16px color');
  check(option.series.every((series) => series.smooth === false && series.connectNulls ===
    false), 'multi-series line bridges gaps');
} catch (error) {
  failures.push('duplicate/multi render: ' + (error && error.stack || error));
}

if (typeof api.buildLineOption !== 'function') {
  failures.push('buildLineOption is not exported for the production line option');
} else {
  try {
    const direct = api.buildLineOption(unordered);
    check(direct.xAxis.type === 'value', 'buildLineOption did not use the numeric axis');
    check(JSON.stringify(direct.series[0].data.map((point) => point.value[0])) ===
      JSON.stringify([1, 4, 24]),
      'buildLineOption lost temporal distance');
    check(direct.series[0].smooth === false && direct.series[0].connectNulls === false,
      'buildLineOption smooth/connectNulls');
  } catch (error) {
    failures.push('buildLineOption: ' + (error && error.stack || error));
  }
}

// Point identity survives numeric [x, y] click payloads, including 0, and does not misroute series.
try {
  const clickRows = [
    baseRow({row_id: 'treat-1', actual_timepoint: 1, actual_timepoint_unit: 'week',
      numeric_value: 1, n: 10}),
    baseRow({row_id: 'treat-4', actual_timepoint: 4, actual_timepoint_unit: 'week',
      numeric_value: 9, n: 10}),
    baseRow({
      row_id: 'ctrl-4', arm_role: 'control', _chart_series_key: 'control', _chart_series_label:
        '对照组',
      actual_timepoint: 4, actual_timepoint_unit: 'week', numeric_value: 3, n: 9,
    }),
  ];
  renderOption(qualified(clickRows));
  let chart = liveChart();
  chart.handlers.click({data: [4, 3], value: [4, 3], seriesIndex: 1, dataIndex: 0});
  check(api.getSelectedRowId() === 'ctrl-4', 'array click misrouted control to ' +
    api.getSelectedRowId());
  chart.handlers.click({data: {_row_id: 'treat-4', value: [4, 9]}, seriesIndex: 0, dataIndex: 1});
  check(api.getSelectedRowId() === 'treat-4', 'object click lost treat-4, got ' +
    api.getSelectedRowId());

  const zeroRows = [
    baseRow({row_id: 'other', actual_timepoint: 4, actual_timepoint_unit: 'week',
      numeric_value: 6}),
    baseRow({row_id: 0, actual_timepoint: 0, actual_timepoint_unit: 'week', numeric_value: 0}),
  ];
  renderOption(qualified(zeroRows));
  chart = liveChart();
  chart.handlers.click({data: [0, 0], value: [0, 0], seriesIndex: 0, dataIndex: 0});
  check(api.getSelectedRowId() === '0', 'zero row id click resolved to ' + api.getSelectedRowId());

  const nullRows = [
    baseRow({row_id: null, actual_timepoint: 1, actual_timepoint_unit: 'week', numeric_value: 5}),
    baseRow({row_id: 'kept', actual_timepoint: 4, actual_timepoint_unit: 'week', numeric_value: 6}),
  ];
  renderOption(qualified(nullRows));
  chart = liveChart();
  check(JSON.stringify(idsOf(chart.option)) === JSON.stringify([null, 'kept']),
    'null id was stringified: ' + JSON.stringify(idsOf(chart.option)));
  chart.handlers.click({data: {_row_id: null, value: [1, 5]}, seriesIndex: 0, dataIndex: 0});
  check(api.getSelectedRowId() == null, 'null row id was rewritten to ' +
    JSON.stringify(api.getSelectedRowId()));

  renderOption(qualified(clickRows));
  const hidden = documentRef.querySelector('[data-filter-row-id="treat-1"]');
  check(!!hidden, 'filter target row was not rendered');
  if (hidden) hidden.style.display = 'none';
  api.syncWithFilter();
  chart = liveChart();
  const remaining = idsOf(chart.option);
  check(remaining.includes('treat-4') && remaining.includes('ctrl-4') &&
    !remaining.includes('treat-1'),
    'filter kept the wrong points: ' + JSON.stringify(remaining));
  chart.handlers.click({data: [4, 3], value: [4, 3], seriesIndex: 1, dataIndex: 0});
  check(api.getSelectedRowId() === 'ctrl-4', 'filtered click misrouted to ' +
    api.getSelectedRowId());
  api.clearSelection();
  resizeHandlers.forEach((handler) => handler());
  check(chart.resized >= 1 || liveChart().resized >= 1, 'resize did not reach the active chart');
  liveChart().handlers.click({data: [4, 3], value: [4, 3], seriesIndex: 1, dataIndex: 0});
  check(api.getSelectedRowId() === 'ctrl-4', 'resize click misrouted to ' + api.getSelectedRowId());
} catch (error) {
  failures.push('click/filter: ' + (error && error.stack || error));
}

if (failures.length) {
  throw new Error(failures.join('\n'));
}
"""


def test_longitudinal_line_option_keeps_visit_distance_and_row_identity() -> None:
    result = subprocess.run(
        ["node", "-e", PROBE, str(CHARTS)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout


@pytest.mark.parametrize("kind", (
    "bar", "horizontal_bar", "identity_bar", "line", "forest", "bubble",
    "scatter_interval", "timeline", "heatmap", "status_matrix",
))
def test_numeric_ticks_stay_horizontal_and_unbroken_without_changing_categories(kind: str) -> None:
    """Run production builders, not source-text assertions or browser acceptance."""
    setup = PROBE.split("// Unordered actual visits", 1)[0]
    # Expose the real private dispatcher only inside this isolated VM. These
    # option tests do not need the unrelated DOM legend/heatmap mount adapters.
    setup = setup.replace(
        "vm.runInNewContext(source, {",
        "vm.runInNewContext(source.replace('window.__PRESENTATION_PLAN__ = presentationPlan;', "
        "'window.__AXIS_TEST_BUILD__ = buildOption; "
        "window.__PRESENTATION_PLAN__ = presentationPlan;'), {",
    )
    probe = r"""
const kind = JSON.parse(process.argv[2]);
const type = kind.endsWith('bar') ? 'bar' : kind;
const rows = [0, 4, 24].map((time, index) => baseRow({
  _chart_type: type, row_id: 'axis-' + index, actual_timepoint: time,
  actual_timepoint_unit: 'week', numeric_value: index * 7.25, value: index * 7.25,
  display_label_zh: '保留完整研究与方案名称' + index,
  category: '保留完整研究与方案名称' + index,
  group_id: 'declared-' + index, time: '第' + time + '周',
  effect: index * 7.25, center: index * 7.25, ci_lower: 1.5, ci_upper: 20.5,
  x_value: index * 7.25, y_value: index + 2, size: 50,
  event: '事件' + index, value_matrix: index, coverage: index / 2, status: '进行中',
}));
const group = {title_zh: '数值刻度', rows};
if (kind === 'horizontal_bar') group.orientation = 'horizontal';
if (kind === 'identity_bar') {
  group.identity_series = true;
  rows.forEach((row, index) => {
    row._chart_identity_key = 'identity-' + index;
    row._chart_comparison_context_key = 'context-' + index;
  });
}
const before = JSON.stringify(rows);
const option = windowRef.__AXIS_TEST_BUILD__(group);
for (const dimension of ['xAxis', 'yAxis']) {
  const axes = Array.isArray(option[dimension]) ? option[dimension] : [option[dimension]];
  for (const axis of axes) {
    if (!axis || !['value', 'log'].includes(axis.type) || axis.show === false) continue;
    check(axis.axisLabel && axis.axisLabel.rotate === 0, kind + ' ' + dimension + ' tilted tick');
    check(!axis.axisLabel.overflow && axis.axisLabel.width == null,
      kind + ' ' + dimension + ' numeric tick can be split or truncated');
    check(axis.axisLabel.fontSize >= 16, kind + ' reduced tick type');
  }
}
check(JSON.stringify(rows) === before, kind + ' changed original observations');
check(option._rowIds.join(',') === 'axis-0,axis-1,axis-2', kind + ' lost source identities');
if (type === 'line') {
  check(JSON.stringify(option.series[0].data.map(xOf)) === '[0,4,24]', 'lost real visit spacing');
  check(option.series[0].data[0].value[1] === 0, 'zero changed');
}
if (kind === 'forest' || kind === 'scatter_interval') {
  check(option.yAxis.axisLabel.rotate === 25, 'category policy was overwritten');
  check(option.yAxis.data[2] === rows[2].display_label_zh, 'category was shortened');
}
if (failures.length) throw new Error(failures.join('\n'));
"""
    result = subprocess.run(
        ["node", "-e", setup + probe, str(CHARTS), json.dumps(kind)],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
