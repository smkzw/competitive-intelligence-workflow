"""Real browser checks on synthetic observations, including non-percent values."""

from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from ci_workflow.renderers.portal.report_a import ReportAPortalData, render_report_a_site
from tests.integration.test_fresh_a_research_package import _package_payload


def test_serious_risk_axis_contains_all_reported_values(tmp_path: Path) -> None:
    payload = _package_payload()["report_data"]
    for row in payload["safety"]:
        if row["term"] == "任何SAE" and row["arm"] == "治疗组":
            row.update(value=25, numerator=None, denominator=None)
    data = ReportAPortalData.model_validate(payload)
    site = tmp_path / "site"
    render_report_a_site(data, site)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto((site / "matrix.html").as_uri())
        page.locator('[data-matrix-control="safety-axis"]').select_option(index=1)
        points = page.locator('[data-chart-id="matrix-full"] .kz-a-bubble')
        assert points.count() >= 2
        assert all(14 <= position <= 86 for position in points.evaluate_all(
            "nodes => nodes.map(node => parseFloat(node.style.bottom))"
        ))
        ticks = page.locator('.kz-a-axis-tick--y').all_inner_texts()
        assert max(float(value.rstrip("%")) for value in ticks) >= 25
        browser.close()


@pytest.mark.parametrize("engine", ["chromium", "webkit"])
@pytest.mark.parametrize("width", [1440, 768, 390, 320])
def test_matrix_bubbles_do_not_move_data_coordinates_to_avoid_collisions(
    tmp_path: Path, engine: str, width: int,
) -> None:
    data = ReportAPortalData.model_validate(_package_payload()["report_data"])
    site = tmp_path / "site"
    render_report_a_site(data, site)
    with sync_playwright() as playwright:
        browser = getattr(playwright, engine).launch()
        page = browser.new_page(viewport={"width": width, "height": 900})
        page.goto((site / "matrix.html").as_uri())
        coordinates = page.locator('[data-chart-id="matrix-full"] .kz-a-bubble').evaluate_all(
            "nodes => nodes.map(node => ({x: parseFloat(node.style.left), "
            "y: parseFloat(node.style.bottom), efficacy: Number(node.dataset.efficacyValue), "
            "rate: Number(node.dataset.eventRate)}))"
        )
        assert len(coordinates) >= 2
        for point in coordinates:
            assert point["x"] == pytest.approx(14 + 72 * point["efficacy"] / 100)
            assert point["y"] == pytest.approx(14 + 72 * (100 - point["rate"]) / 100)
        areas = page.locator('[data-chart-id="matrix-full"] .kz-a-bubble').evaluate_all(
            "nodes => nodes.map(node => ({diameter: parseFloat(node.style.width), "
            "n: window.REPORT_A.trials.find(trial => trial.id === node.dataset.trialId)"
            ".treatment_sample_size}))"
        )
        reference = areas[0]
        for point in areas:
            assert (point["diameter"] / reference["diameter"]) ** 2 == pytest.approx(
                point["n"] / reference["n"], rel=1e-5  # CSS serializes pixel decimals.
            )
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
        page.screenshot(path=str(tmp_path / f"matrix-{engine}-{width}.png"), full_page=True)
        browser.close()


@pytest.mark.parametrize("engine", ["chromium", "webkit"])
def test_safety_preserves_every_observation_window(tmp_path: Path, engine: str) -> None:
    payload = _package_payload()["report_data"]
    seed = payload["safety"][0]
    payload["safety"].extend([
        {**seed, "row_id": "window-low", "time_window": "第1至12周", "value": 2},
        {**seed, "row_id": "window-high", "time_window": "第1至52周", "value": 80},
    ])
    data = ReportAPortalData.model_validate(payload)
    site = tmp_path / "site"
    render_report_a_site(data, site)
    with sync_playwright() as playwright:
        browser = getattr(playwright, engine).launch()
        page = browser.new_page(viewport={"width": 320, "height": 900})
        page.goto((site / "safety.html").as_uri())
        chart = page.locator('[data-chart-id="safety-full"]')
        assert set(chart.locator("[data-row-id]").evaluate_all(
            "nodes => nodes.map(node => node.dataset.rowId)"
        )) == {row.row_id for row in data.safety}
        assert "第1至12周" in chart.inner_text()
        assert "第1至52周" in chart.inner_text()
        chart.locator('[data-row-id="window-low"]').click()
        summary = page.locator("#a-product-insight-summary")
        assert "第1至12周" in summary.inner_text()
        assert "2%" in summary.inner_text()
        page.keyboard.press("Escape")
        assert set(page.locator("tbody tr[data-row-id]").evaluate_all(
            "nodes => nodes.map(node => node.dataset.rowId)"
        )) == {row.row_id for row in data.safety}
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
        page.screenshot(path=str(tmp_path / f"safety-{engine}-320.png"), full_page=True)
        browser.close()


@pytest.mark.parametrize("kind", ["safety", "efficacy"])
def test_observation_pagination_retains_every_row_and_bounds_page_height(
    tmp_path: Path, kind: str,
) -> None:
    payload = _package_payload()["report_data"]
    seed = payload[kind][0]
    time_field = "time_window" if kind == "safety" else "timepoint"
    payload[kind].extend(
        {**seed, "row_id": f"many-{index}", time_field: f"第{index}周"}
        for index in range(121)
    )
    data = ReportAPortalData.model_validate(payload)
    site = tmp_path / "site"
    render_report_a_site(data, site)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 320, "height": 900})
        page.goto((site / f"{kind}.html").as_uri())
        chart = page.locator(f'[data-chart-id="{kind}-full"]')
        label = "安全性" if kind == "safety" else "疗效"
        navigation = chart.get_by_role("navigation", name=f"{label}图表翻页")
        seen: set[str] = set()
        while True:
            ids = chart.locator("[data-row-id]:not([hidden])").evaluate_all(
                "nodes => nodes.map(node => node.dataset.rowId)"
            )
            assert 0 < len(ids) <= 60
            seen.update(ids)
            assert page.evaluate("document.documentElement.scrollHeight") < 100_000
            following = navigation.get_by_role("button", name="下一页")
            if following.is_disabled():
                break
            following.click()
        assert seen == {row.row_id for row in getattr(data, kind)}
        browser.close()


@pytest.mark.parametrize("engine", ["chromium", "webkit"])
@pytest.mark.parametrize("width", [1440, 768, 390, 320])
def test_all_efficacy_observations_survive_chart_and_table(
    tmp_path: Path, engine: str, width: int,
) -> None:
    payload = _package_payload()["report_data"]
    payload["indication"] = "合成非皮肤适应症"
    seed = payload["efficacy"][0]
    for index, value in enumerate((-4, 0, 7)):
        payload["efficacy"].append({
            **seed, "row_id": f"synthetic-score-{index}", "endpoint": "合成评分变化",
            "timepoint": "第24周", "unit": "分", "value": value,
            "arm_detail": f"合成剂量{index}", "numerator": None, "denominator": None,
        })
    data = ReportAPortalData.model_validate(payload)
    site = tmp_path / "site"
    render_report_a_site(data, site)
    with sync_playwright() as playwright:
        browser = getattr(playwright, engine).launch()
        page = browser.new_page(viewport={"width": width, "height": 900})
        page.goto((site / "efficacy.html").as_uri())
        chart = page.locator('[data-chart-id="efficacy-full"]')
        assert "-4分" in chart.inner_text()
        expected = {row.row_id for row in data.efficacy}
        chart_ids = set(chart.locator("[data-row-id]").evaluate_all(
            "nodes => nodes.map(node => node.dataset.rowId)"
        ))
        assert chart_ids == expected
        table_ids = set(page.locator("tbody tr[data-row-id]").evaluate_all(
            "nodes => nodes.map(node => node.dataset.rowId)"
        ))
        assert table_ids == expected
        assert page.locator("details.kz-complete-table").get_attribute("open") is None
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
        page.screenshot(path=str(tmp_path / f"{engine}-{width}.png"), full_page=True)
        page.locator('[data-filter-dimension="endpoint"] button').filter(
            has_text="合成评分变化"
        ).click()
        selected_ids = {f"synthetic-score-{index}" for index in range(3)}
        assert set(chart.locator("[data-row-id]").evaluate_all(
            "nodes => nodes.map(node => node.dataset.rowId)"
        )) == selected_ids
        assert set(page.locator("tbody tr[data-row-id]:not([hidden])").evaluate_all(
            "nodes => nodes.map(node => node.dataset.rowId)"
        )) == selected_ids
        assert chart.locator('[data-row-id="synthetic-score-1"] .kz-a-bar').evaluate(
            "node => node.getBoundingClientRect().width"
        ) == 0
        chart.locator('[data-row-id="synthetic-score-0"]').get_by_role("button").click()
        panel = page.locator('[data-product-panel="efficacy"]')
        assert "合成评分变化" in panel.inner_text()
        assert "合成剂量0" in panel.inner_text()
        assert "-4分" in panel.inner_text()
        assert "第24周" in panel.inner_text()
        browser.close()
