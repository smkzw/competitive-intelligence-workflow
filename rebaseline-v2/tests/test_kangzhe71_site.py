"""Kangzhe 7.1 desktop shell via the ordinary production renderer.

Grouped layout contract for A/B/C. Scientific rows, chart ids, and the shared
evidence reader stay in the rendered page. Not a visual or clinical acceptance.
"""
from pathlib import Path

from ciw2.harness.llm import ScriptedLLM
from ciw2.render.portal import REPORT_ZH, render_report
from ciw2.service import Service

ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / "src" / "ciw2" / "render" / "static" / "kangzhe.css"
INDICATION = "壳层适应症甲"
CHART = {"A": "chart-heat", "B": "chart-result", "C": "chart-size"}
TABLE = {"A": "tbl-a", "B": "tbl-b", "C": "tbl-c"}


def _pages(settings):
    svc = Service(settings, llm_factory=lambda s: (ScriptedLLM([]), None))
    pid = svc.create_project(INDICATION, ["A", "B", "C"], focus="通路比较")
    svc.db.upsert_entity(pid, "drug", "Known Drug", attrs={
        "targets": ["IL-31RA"], "highest_phase_global": "phase2"})
    trial, _ = svc.db.upsert_entity(pid, "trial", "NCT00000071")
    source = svc.db.add_source(pid, "ctgov", "https://example.org/kz71", "f" * 64)
    fact = {"project_id": pid, "entity_id": trial, "tier": "critical", "status": "verified",
            "source_id": source, "extracted_by": "code:test"}
    svc.db.add_fact({**fact, "field": "result.primary.value", "value": 1.5, "quote": "1.5",
                     "context": {"endpoint": "Clinical score", "endpoint_key": "clinical score",
                                 "timepoint": "Week 4", "class_title": "Week 4", "category": None,
                                 "arm": "Arm A", "group_id": "G1", "population": "ITT",
                                 "stat_type": "mean", "unit": "points", "param_type": "MEAN"}})
    svc.db.add_fact({**fact, "field": "design.sample_size", "value": 120,
                     "quote": "Original design evidence", "context": {}})
    return {report: render_report(svc.db, pid, report) for report in "ABC"}


def _header(html):
    return html.split('<header class="top"', 1)[1].split("</header>", 1)[0]


def _section(html, section_id):
    marker = f'id="{section_id}"'
    start = html.index(marker)
    return html[start:html.index("</section>", start)]


def test_abc_shell_puts_comparison_before_records(settings):
    pages = _pages(settings)
    report_navs = []
    for report, html in pages.items():
        assert html.count('<header class="top"') == 1
        header = _header(html)
        assert header.count('<nav') == 2
        assert "kz-header-row" in header
        assert INDICATION not in header
        assert 'href="#comparison"' in header
        assert header.count('class="on"') == 1
        for label in ("A 竞争格局", "B 疗效安全", "C 设计先例"):
            assert label in header
        report_navs.append(header.split("<nav", 1)[1].split("</nav>", 1)[0].replace('class="on"', 'class=""'))
        h1 = html.split("<h1>", 1)[1].split("</h1>", 1)[0]
        assert h1 == REPORT_ZH[report]
        assert INDICATION not in h1
        lede = html.split('class="kz-lede"', 1)[1].split("</p>", 1)[0]
        assert INDICATION in lede
        comparison = _section(html, "comparison")
        assert f'id="{CHART[report]}"' in comparison
        assert f'id="{TABLE[report]}"' not in comparison
        assert html.index('id="comparison"') < html.index(f'id="{TABLE[report]}"')
        assert f'data-filter="{TABLE[report]}"' in html
        assert html.count('id="design-evidence-dialog"') == 1
        assert "data-close-design-evidence" in html
        assert "kz-film" not in html and "kz-mark" not in html
        assert html.count('alt="康哲药业"') == 1
        assert html.count('class="kpis"') == 1
    assert report_navs[0] == report_navs[1] == report_navs[2]
    assert 'data-entity-id="' in pages["A"] and "Known Drug" in pages["A"]
    assert 'id="chart-phase"' in pages["A"] and 'id="landscape-count"' in pages["A"]
    assert 'data-fact-id="' in pages["B"] and 'id="result-query"' in pages["B"]
    assert "Original design evidence" in pages["C"] and 'id="tbl-c"' in pages["C"]
    assert "尚未取得试验设计资料" not in pages["C"]


def test_site_css_uses_desktop_tokens_without_clipping_or_film():
    css = CSS.read_text(encoding="utf-8")
    assert "--kz-type-site-body:18px" in css
    assert "--report-font-body:16px" in css
    assert "--kz-type-site-body-floor:16px" in css
    assert "var(--kz-type-site-body)" in css
    for width in ("1440", "1600", "1920", "2560"):
        assert width in css
    assert "max-width:1100" not in css and "max-width: 1100" not in css
    assert "text-overflow" not in css and "ellipsis" not in css and "line-clamp" not in css
    assert "!important" not in css
    assert "@media (max-width" not in css and "@media(max-width" not in css
    assert "kz-film" not in css and "100svh" not in css and "100vh" not in css
    assert "--kz-data-plane:" in css and "backdrop-filter:none" in css
    assert "border-left" not in css and "border-right" not in css


def test_title_and_counts_share_one_heading_band_not_four_stacked_rows(settings):
    for html in _pages(settings).values():
        band = _section(html, 'report-heading')
        assert '<h1>' in band and 'class="kz-lede"' in band and 'class="kpis"' in band
        assert html.index('id="report-heading"') < html.index('id="comparison"')


def test_design_search_label_and_field_have_a_shared_reading_row():
    css = CSS.read_text()
    assert '.kz-query>label{display:flex' in css
    assert '.kz-query .filter{flex:1' in css
