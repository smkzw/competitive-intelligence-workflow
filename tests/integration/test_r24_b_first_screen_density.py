"""B desktop first-screen density is a presentation contract, not a science change.

Ordinary B pages must mount personal save/import/export configuration inside a
collapsed progressive disclosure in the filter panel (portal.js mounts into the
first ``.kz-a-workspace-bar__actions`` in main), keep the active filter count
and quick filter/search entries in the initial DOM, and compact consecutive
identical chart titles without removing the accessible text.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from ci_workflow.renderers.portal.report_b import (
    ReportBPortalData,
    render_report_b_site,
)

ROOT = Path(__file__).resolve().parents[2]


def _render_safety_page(tmp_path: Path) -> str:
    payload = json.loads(
        (ROOT / "fixtures/synthetic/a-complete/inputs/report-data.json").read_text()
    )
    render_report_b_site(ReportBPortalData.model_validate(payload), tmp_path)
    return (tmp_path / "safety.html").read_text(encoding="utf-8")


def test_personal_config_mounts_collapsed_inside_filter_panel(tmp_path: Path) -> None:
    page = _render_safety_page(tmp_path)
    panel = page.index('id="kz-filter-panel"')
    disclosure = page.index('<details class="kz-b-personal">')
    seam = page.index("kz-a-workspace-bar__actions")
    assert panel < disclosure < seam, "config disclosure must live in the filter panel"
    assert page.count("kz-a-workspace-bar__actions") == 1, "portal.js mounts the first seam"
    opening_tag = page[disclosure : page.index(">", disclosure) + 1]
    assert " open" not in opening_tag, "configuration must be collapsed by default"
    body = page[disclosure : page.index("</details>", seam)]
    assert "kz-b-personal__body" in body, "seam needs the B-scoped body hook"


def test_active_query_counts_and_filter_search_entries_stay_in_initial_dom(
    tmp_path: Path,
) -> None:
    page = _render_safety_page(tmp_path)
    summary = page.index("data-filter-summary")
    status = page.index("data-filter-status")
    disclosure = page.index('<details class="kz-b-personal">')
    assert summary < disclosure and status < disclosure, (
        "active query and counts must stay visible without opening the config disclosure"
    )
    quick = page.index('kz-b-filter-quick__button')
    assert quick < page.index('id="kz-filter-panel"'), "quick product entry stays above the panel"
    assert 'id="global-search-input"' in page, "global search stays reachable"
    assert page.count('class="kz-b-filter-button kz-b-filter-quick__button"') >= 1
    assert 'data-filter-reset' in page, "clear-filter action stays reachable"


def test_unified_filter_bar_wraps_quick_and_panel_without_dropping_options(
    tmp_path: Path,
) -> None:
    page = _render_safety_page(tmp_path)
    bar = page.index('<div class="kz-b-filter-bar">')
    quick = page.index('kz-b-filter-quick')
    panel_close = page.index('</details>', page.index('id="kz-filter-panel"'))
    assert bar < quick < panel_close, "one filter card serves quick chips and the panel"
    assert page.count("kz-b-filter-group") >= 1, "complete filter options remain listed"


def test_consecutive_identical_chart_titles_compact_accessibly() -> None:
    source = ROOT / "src/ci_workflow/renderers/portal/assets/report-b.js"
    probe = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const text=fs.readFileSync(process.argv[1],'utf8').replace(
 '  function compactRepeatedGroupTitles(',
 '  window.__TEST_COMPACT__=compactRepeatedGroupTitles;\n  function compactRepeatedGroupTitles(');
function card(titleText){
 const title={textContent:titleText,classes:new Set(),
  classList:{
   add(name){this._own.classes.add(name);},
   remove(name){this._own.classes.delete(name);},
   contains(name){return this._own.classes.has(name);}},
  _own:null};
 title.classList._own=title;
 return {title,querySelector(selector){
  return selector==='.kz-chart-group__title'?title:null;}};
}
const same='安全性 · 严重不良事件 · 受累人数（例）';
const cards=[same,same,same,'安全性 · 感染相关事件 · 受累人数（例）',same].map(card);
const sandbox={window:{},
 document:{readyState:'loading',addEventListener(){},querySelectorAll(selector){
  return selector==='#kz-chart-module .kz-chart-module__group'?cards:[];}}};
vm.runInNewContext(text,sandbox);
const compact=sandbox.window.__TEST_COMPACT__;
assert.equal(typeof compact,'function','production compaction must be reachable');
compact();
assert.equal(cards[0].title.classList.contains('kz-chart-group__title--repeat'),false,
 'first occurrence keeps its visible label');
assert.equal(cards[1].title.classList.contains('kz-chart-group__title--repeat'),true);
assert.equal(cards[2].title.classList.contains('kz-chart-group__title--repeat'),true);
assert.equal(cards[3].title.classList.contains('kz-chart-group__title--repeat'),false,
 'a different label breaks the repeated run');
assert.equal(cards[4].title.classList.contains('kz-chart-group__title--repeat'),false,
 'after an intervening label the title is shown again (adjacent-duplicates only)');
compact();
assert.equal(cards[1].title.classList.contains('kz-chart-group__title--repeat'),true,
 're-running the compaction is idempotent');
assert.equal(cards[0].title.classList.contains('kz-chart-group__title--repeat'),false);
"""
    result = subprocess.run(
        ["node", "-e", probe, str(source)], capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr


def test_repeat_title_utility_hides_visual_weight_not_accessible_text() -> None:
    css = (ROOT / "src/ci_workflow/renderers/portal/assets/report-b.css").read_text()
    marker = css.index(".kz-chart-group__title--repeat")
    block = css[marker : css.index("}", marker)]
    assert "clip-path" in block or "clip:" in block, "use the visually-hidden clip pattern"
    assert "display" not in block and "visibility" not in block, (
        "the duplicate label must stay in the accessibility tree"
    )
    assert "!important" not in block, "no forced overrides for the utility"
    assert "font-size" not in block, "compaction never shrinks the shared label size"
