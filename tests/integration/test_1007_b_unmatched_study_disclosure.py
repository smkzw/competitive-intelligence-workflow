"""Native reachability for query-empty study rows; actual pixels remain separate."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "src/ci_workflow/renderers/portal"


def test_empty_study_rows_have_a_named_native_control_not_removed_membership() -> None:
    template = (ROOT / "templates/b/page.html.j2").read_text()
    assert 'type="checkbox" data-comparison-unmatched-toggle' in template
    assert "本问题暂无匹配记录的其余研究" in template
    assert 'data-comparison-unmatched-count' in template
    assert "不代表未研究或零结果" in template


def test_native_checked_state_owns_empty_rows_and_matched_facts_never_hidden() -> None:
    css = (ROOT / "assets/report-b.css").read_text()
    assert ".kz-b-comparison-unmatched { display: none; }" in css
    assert ":has([data-comparison-unmatched-toggle]:checked)" in css
    assert ".kz-b-comparison-unmatched { display: table-row; }" in css
    assert "font-size: 16px" in css
    # No new persistence/query state, clinical qualification or membership filtering.
    source = (ROOT / "assets/report-b.js").read_text()
    assert 'position.searchParams.set("cmp_unmatched"' not in source


def test_long_filter_list_has_a_named_native_keyboard_scroll_region() -> None:
    template = (ROOT / "templates/b/page.html.j2").read_text()
    assert 'class="kz-b-filters" role="region" tabindex="0"' in template
    assert 'aria-label="筛选条件，全部选项可滚动查看"' in template


def test_expanded_filters_use_available_desktop_width_and_bounded_native_height() -> None:
    css = (ROOT / "assets/report-b.css").read_text()
    assert ".kz-b-filter-bar > .kz-b-filter-panel[open] { grid-column: 1 / -1; }" in css
    start = css.index(".kz-b-filter-bar .kz-b-filters {")
    rules = css[start:css.index("}", start)]
    assert "max-height: min(420px, 42vh)" in rules
    assert "overflow-y: auto" in rules
    assert "scrollbar-gutter: stable" in rules
    assert "overflow: hidden" not in rules
