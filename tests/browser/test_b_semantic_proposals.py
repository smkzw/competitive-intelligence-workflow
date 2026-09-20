"""Synthetic bound proposals exercised through real B HTML and browser charts."""

import json
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from ci_workflow.renderers.portal.report_b import (
    ReportBPortalData,
    _display_trial_name,
    _efficacy_records,
    render_report_b_site,
)
from tests.reports.b.test_semantic_grouping_proposals import _proposal


def proposal_data() -> ReportBPortalData:
    root = Path(__file__).resolve().parents[2]
    payload = json.loads(
        (root / "fixtures/synthetic/a-complete/inputs/report-data.json").read_bytes(),
    )
    facts = []
    for index, trial in enumerate(payload["trials"][:2]):
        facts.append({
            "row_id": f"proposal-observation-{index}", "product_id": trial["product_id"],
            "trial_id": trial["id"], "original_endpoint": "EASI-75",
            "original_definition": "EASI改善至少75%的比例" if index else "EASI-75应答者比例",
            "actual_timepoint": 48 + index * 2, "actual_timepoint_unit": "week",
            "analysis_form": "response_rate", "analysis_population": "FAS",
            "arm_label": "active", "unit": "%", "value": 60 + index,
            "direction": "higher_is_better", "estimand": "treatment_policy",
            "denominator_semantics": "full_analysis_set", "instrument_or_scale": "EASI v1.0",
            "source_version_id": f"synthetic-source-{index}",
        })
    payload["efficacy_views"] = {"facts": facts}
    data = ReportBPortalData.model_validate(payload)
    names = {product.id: product.name for product in data.products}
    trials = {
        trial.id: _display_trial_name(trial, names[trial.product_id]) for trial in data.trials
    }
    records = _efficacy_records(data, names, trials)
    payload["semantic_proposals"] = [
        _proposal(records[0][0], records[1][0]).model_dump(mode="json")
    ]
    return ReportBPortalData.model_validate(payload)


@pytest.mark.parametrize("engine", ["chromium", "webkit"])
def test_dossier_uses_global_scientific_partition(tmp_path: Path, engine: str) -> None:
    payload = proposal_data().model_dump(mode="json")
    second = payload["efficacy_views"]["facts"][1]
    third_trial = dict(payload["trials"][1], id="synthetic-third-trial")
    payload["trials"].append(third_trial)
    payload["efficacy_views"]["facts"].append(dict(
        second, row_id="proposal-observation-2", trial_id=third_trial["id"],
        actual_timepoint=52, original_definition="第三种结果定义措辞",
    ))
    payload["semantic_proposals"] = []
    data = ReportBPortalData.model_validate(payload)
    names = {product.id: product.name for product in data.products}
    trials = {trial.id: _display_trial_name(trial, names[trial.product_id])
              for trial in data.trials}
    rows = _efficacy_records(data, names, trials)
    from tests.reports.b.test_semantic_grouping_proposals import _approved

    payload["semantic_proposals"] = [
        _proposal(rows[0][0], rows[1][0]).model_dump(mode="json"),
        _proposal(rows[1][0], rows[2][0]).model_dump(mode="json"),
    ]
    payload["semantic_adjudications"] = [
        _approved(rows[0][0], rows[1][0]).model_dump(mode="json"),
        _approved(rows[1][0], rows[2][0]).model_dump(mode="json"),
    ]
    site = tmp_path / "html"
    render_report_b_site(ReportBPortalData.model_validate(payload), site)
    with sync_playwright() as playwright:
        browser = getattr(playwright, engine).launch()
        page = browser.new_page()
        page.goto((site / "efficacy.html").as_uri())
        full = page.evaluate("window.__CHART_GROUPS__")
        expected = {row["row_id"]: group["scientific_group_id"]
                    for group in full for row in group["rows"]}
        page.goto((site / "products" / f'{second["product_id"]}.html').as_uri())
        detail = page.evaluate("window.__CHART_GROUPS__")
        selected = {row["row_id"]: group["scientific_group_id"]
                    for group in detail for row in group["rows"] if row["row_id"] in expected}
        assert selected == {key: expected[key] for key in
                            ("proposal-observation-1", "proposal-observation-2")}
        assert len(set(selected.values())) == 2
        browser.close()


@pytest.fixture(scope="module")
def proposal_site(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """合并消费套件专用：在纯候选载荷上显式加入已批准归并后整体重校验。"""
    from tests.reports.b.test_semantic_grouping_proposals import _approved

    site = tmp_path_factory.mktemp("b-semantic-proposal") / "html"
    data = proposal_data()
    names = {product.id: product.name for product in data.products}
    trials = {
        trial.id: _display_trial_name(trial, names[trial.product_id])
        for trial in data.trials
    }
    records = _efficacy_records(data, names, trials)
    payload = data.model_dump(mode="json")
    payload["semantic_adjudications"] = [
        _approved(records[0][0], records[1][0]).model_dump(mode="json")
    ]
    render_report_b_site(ReportBPortalData.model_validate(payload), site)
    return site


@pytest.mark.parametrize("engine", ["chromium", "webkit"])
def test_full_longitudinal_page_preserves_within_trial_time_series(
    tmp_path: Path, engine: str,
) -> None:
    payload = proposal_data().model_dump(mode="json")
    payload["semantic_proposals"] = []
    first = dict(payload["efficacy_views"]["facts"][0], actual_timepoint=12,
                 group_id="active-arm")
    payload["efficacy_views"]["facts"] = [
        first, dict(first, row_id="longitudinal-24", actual_timepoint=24, value=75),
    ]
    site = tmp_path / "html"
    render_report_b_site(ReportBPortalData.model_validate(payload), site)
    with sync_playwright() as playwright:
        browser = getattr(playwright, engine).launch()
        page = browser.new_page()
        page.goto((site / "longitudinal-results.html").as_uri())
        groups = page.evaluate("window.__CHART_GROUPS__")
        assert len(groups) == 1
        assert {row["actual_timepoint"] for row in groups[0]["rows"]} == {12, 24}
        assert {row["_chart_type"] for row in groups[0]["rows"]} == {"line"}
        assert groups[0]["cross_trial"] is False
        browser.close()


@pytest.mark.parametrize("engine", ["chromium", "webkit"])
@pytest.mark.parametrize("width", [1440, 768, 390, 320])
def test_html_consumes_bound_groups_and_keeps_raw_observations(
    proposal_site: Path, tmp_path: Path, engine: str, width: int,
) -> None:
    with sync_playwright() as playwright:
        browser = getattr(playwright, engine).launch()
        page = browser.new_page(viewport={"width": width, "height": 900})
        page.goto((proposal_site / "efficacy.html").as_uri())
        page.wait_for_function("window.__CHART_GROUPS__ && window.echarts")
        groups = page.evaluate("window.__CHART_GROUPS__")
        assert len(groups) == 1
        assert groups[0]["cross_trial"] is True
        assert {row["value"] for row in groups[0]["rows"]} == {60, 61}
        assert {row["actual_timepoint"] for row in groups[0]["rows"]} == {48, 50}
        chart_text = page.locator("#kz-chart-module").inner_text()
        assert "实际观察时间：" in chart_text and "48 周" in chart_text and "50 周" in chart_text
        assert "安澜双抗" in chart_text and "泰瑞奇单抗" in chart_text
        table_rows = page.locator('#kz-chart-module tr[data-row-id]')
        assert table_rows.count() == 2
        assert not table_rows.first.is_visible()
        page.get_by_text("展开完整数据表", exact=True).click()
        assert table_rows.first.is_visible()
        assert {row["row_id"] for row in groups[0]["rows"]} == set(
            table_rows.evaluate_all("rows => rows.map(row => row.dataset.rowId)"),
        )
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        assert "synthetic-model" not in page.locator("body").inner_text()
        page.locator("#kz-chart-module").screenshot(
            path=str(tmp_path / f"group-{engine}-{width}.png"),
        )
        browser.close()


@pytest.fixture(scope="module")
def dense_site(tmp_path_factory: pytest.TempPathFactory) -> Path:
    payload = proposal_data().model_dump(mode="json")
    payload.pop("semantic_proposals")
    template_trial = payload["trials"][0]
    template_fact = payload["efficacy_views"]["facts"][0]
    trials, facts = [], []
    for index in range(8):
        trial_id = f"dense-trial-{index}"
        trials.append(dict(template_trial, id=trial_id, name=f"合成研究{index + 1:02}",
                           display_id=f"合成研究{index + 1:02}"))
        facts.append(dict(template_fact, row_id=f"dense-fact-{index}", trial_id=trial_id))
    payload["trials"] = [*payload["trials"], *trials]
    payload["efficacy_views"] = {"facts": facts}
    site = tmp_path_factory.mktemp("b-dense-categories") / "html"
    render_report_b_site(ReportBPortalData.model_validate(payload), site)
    return site


@pytest.mark.parametrize("engine", ["chromium", "webkit"])
def test_all_categories_remain_keyboard_scrollable_after_resize(
    dense_site: Path, engine: str,
) -> None:
    with sync_playwright() as playwright:
        browser = getattr(playwright, engine).launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto((dense_site / "efficacy.html").as_uri())
        page.set_viewport_size({"width": 320, "height": 900})
        viewport = page.locator('[aria-label="完整图形，较宽时可左右滚动"]').first
        viewport.scroll_into_view_if_needed()
        page.wait_for_function(
            "document.querySelector('[data-chart-type=bar]').parentElement.tabIndex === 0",
        )
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        assert viewport.evaluate("node => node.scrollWidth > node.clientWidth")
        categories = page.evaluate("""() => {
          const node = document.querySelector('[data-chart-type=bar]');
          return window.echarts.getInstanceByDom(node).getOption().xAxis[0].data;
        }""")
        assert len(categories) == 8
        viewport.focus()
        page.keyboard.press("ArrowRight")
        page.wait_for_function(
            "document.querySelector('[data-chart-type=bar]').parentElement.scrollLeft > 0",
        )
        browser.close()
