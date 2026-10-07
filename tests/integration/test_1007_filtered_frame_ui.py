"""Production charts.js filtered-frame projection; Node is not browser acceptance."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHARTS = ROOT / "src/ci_workflow/renderers/portal/assets/charts.js"

PROBE = r"""
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = fs.readFileSync(process.argv[1], 'utf8');

function node() {
  return {
    style: {},
    attributes: {},
    children: [],
    className: '',
    textContent: '',
    hidden: false,
    setAttribute(k, v) { this.attributes[k] = String(v); },
    getAttribute(k) { return this.attributes[k]; },
    appendChild(child) { this.children.push(child); return child; },
    addEventListener() {},
    querySelectorAll() { return []; },
    querySelector() { return null; },
  };
}

const documentRef = {
  readyState: 'complete',
  getElementById(id) { return id === 'kz-chart-module' ? null : null; },
  createElement() { return node(); },
  querySelectorAll() { return []; },
  addEventListener() {},
};

const windowRef = {
  __CHART_GROUPS__: [],
  echarts: undefined,
  document: documentRef,
  addEventListener() {},
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
  Error,
  JSON,
});

assert.equal(typeof windowRef.__CHART_SYNC__.replaceGroups, 'function');
assert.equal(typeof windowRef.__CHART_SYNC__.projectVisibleFrame, 'function');

const note = '同框仅表示临床构念兼容，不代表时间点相同';
const parent = {
  scientific_group_id: 'frame-50-52',
  comparison_purpose: 'semantic_numeric_frame',
  title_complete: true,
  title_zh: 'EASI-75 · 实际观察时间：50 周 / 52 周 · ' + note,
  actual_times: ['50 周', '52 周'],
  time_window_note_zh: note,
  cross_trial: true,
  identity_series: true,
  rows: [
    {
      row_id: 'r50',
      actual_timepoint: 50,
      actual_timepoint_unit: 'week',
      renderable: true,
      disclosure_state: 'reported_value',
      value: 61,
      unit: '%',
      display_label_zh: 'EASI-75',
      product_zh: '药A',
      trial_zh: '试验A',
    },
    {
      row_id: 'r52',
      actual_timepoint: 52,
      actual_timepoint_unit: 'week',
      renderable: true,
      disclosure_state: 'reported_value',
      value: 70,
      unit: '%',
      display_label_zh: 'EASI-75',
      product_zh: '药B',
      trial_zh: '试验B',
    },
    {
      row_id: 'r-unknown',
      actual_timepoint: null,
      actual_timepoint_unit: null,
      renderable: false,
      disclosure_state: 'user_cleared',
      difference_note: '用户清除，待重新核实',
      display_label_zh: 'EASI-75',
      product_zh: '药C',
      trial_zh: '试验C',
    },
  ],
};

function subset(rowIds) {
  const allowed = Object.fromEntries(rowIds.map((id) => [id, true]));
  return Object.assign({}, parent, {
    rows: parent.rows.filter((row) => allowed[row.row_id]),
  });
}

function byReplace(groups) {
  windowRef.__CHART_SYNC__.replaceGroups(groups);
  return windowRef.__CHART_GROUPS__;
}

function timesOf(value) {
  return JSON.stringify(Array.from(value || []).map(String));
}

// 50-only from 50/52 parent: keep frame identity, project visible times.
const only50 = byReplace([subset(['r50'])])[0];
assert.equal(only50.scientific_group_id, parent.scientific_group_id);
assert.equal(only50.comparison_purpose, parent.comparison_purpose);
assert.equal(timesOf(only50.actual_times), timesOf(['50 周']));
assert.equal(timesOf(only50.frame_actual_times), timesOf(['50 周', '52 周']));
assert.match(only50.title_zh, /实际观察时间：50 周(?! \/)/);
assert.doesNotMatch(only50.title_zh, /实际观察时间：50 周 \/ 52 周/);
assert.equal(only50.time_window_note_zh, '原比较框：' + note);
assert.match(only50.title_zh, /原比较框：/);
assert.equal(parent.actual_times.join('|'), '50 周|52 周');
assert.equal(parent.time_window_note_zh, note);
assert.doesNotMatch(parent.title_zh, /原比较框：/);

// Sparse: known time + unknown time row -> visible times omit unknowns.
const sparse = windowRef.__CHART_SYNC__.projectVisibleFrame(subset(['r50', 'r-unknown']));
assert.equal(timesOf(sparse.actual_times), timesOf(['50 周']));
assert.equal(timesOf(sparse.frame_actual_times), timesOf(['50 周', '52 周']));
assert.equal(sparse.rows.map((row) => row.row_id).join(','), 'r50,r-unknown');
assert.equal(sparse.rows[1].disclosure_state, 'user_cleared');

// Unknown-only: no synthetic time labels.
const unknownOnly = windowRef.__CHART_SYNC__.projectVisibleFrame(subset(['r-unknown']));
assert.equal(timesOf(unknownOnly.actual_times), timesOf([]));
assert.equal(timesOf(unknownOnly.frame_actual_times), timesOf(['50 周', '52 周']));
assert.doesNotMatch(unknownOnly.title_zh, /实际观察时间：50 周 \/ 52 周/);

// Empty replaceGroups clears module groups without fabricating frames.
assert.equal(byReplace([]).length, 0);

// Restored full set from parent source: drop frame subset markers.
const restored = byReplace([Object.assign({}, parent, { rows: parent.rows.slice() })])[0];
assert.equal(timesOf(restored.actual_times), timesOf(['50 周', '52 周']));
assert.equal(restored.frame_actual_times, undefined);
assert.equal(restored.time_window_note_zh, note);
assert.doesNotMatch(restored.title_zh, /原比较框：/);
assert.match(restored.title_zh, /实际观察时间：50 周 \/ 52 周/);

// Repeated replaceGroups from the same parent subset stays stable / idempotent.
const first = byReplace([subset(['r52'])])[0];
const second = byReplace([subset(['r52'])])[0];
assert.equal(timesOf(first.actual_times), timesOf(['52 周']));
assert.equal(timesOf(second.actual_times), timesOf(['52 周']));
assert.equal(timesOf(first.frame_actual_times), timesOf(second.frame_actual_times));
assert.equal(first.title_zh, second.title_zh);
assert.equal(first.time_window_note_zh, second.time_window_note_zh);
assert.equal((first.time_window_note_zh.match(/原比较框：/g) || []).length, 1);

// Re-projecting an already projected subset must not double-prefix the note.
const again = windowRef.__CHART_SYNC__.projectVisibleFrame(first);
assert.equal(again.time_window_note_zh, '原比较框：' + note);
assert.equal((again.time_window_note_zh.match(/原比较框：/g) || []).length, 1);
assert.equal(timesOf(again.actual_times), timesOf(['52 周']));
assert.equal(timesOf(again.frame_actual_times), timesOf(['50 周', '52 周']));

// View row order is not a scientific time difference or a new parent frame.
const reverse = windowRef.__CHART_SYNC__.projectVisibleFrame(
  Object.assign({}, parent, { rows: parent.rows.slice().reverse() }));
assert.equal(timesOf(reverse.actual_times), timesOf(['50 周', '52 周']));
assert.equal(reverse.frame_actual_times, undefined);
assert.equal(reverse.time_window_note_zh, note);

// Missing markers and booleans cannot become time labels; actual zero is valid.
const badTime = windowRef.__CHART_SYNC__.projectVisibleFrame(
  Object.assign({}, parent, { rows: [{actual_timepoint: 'unknown', actual_timepoint_unit: 'week'},
    {actual_timepoint: false, actual_timepoint_unit: 'week'}] }));
assert.equal(timesOf(badTime.actual_times), timesOf([]));
assert.doesNotMatch(badTime.title_zh, /unknown 周|false 周/);
const zeroTime = windowRef.__CHART_SYNC__.projectVisibleFrame(
  Object.assign({}, parent, { rows: [{actual_timepoint: 0, actual_timepoint_unit: 'week'}] }));
assert.equal(timesOf(zeroTime.actual_times), timesOf(['0 周']));
"""


def test_filtered_frame_projects_visible_times_without_repartition() -> None:
    result = subprocess.run(
        ["node", "-e", PROBE, str(CHARTS)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
