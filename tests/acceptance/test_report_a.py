"""Task 5.5：A 类真实纵向切片与四类历史失败样本的独立验收。"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from playwright.sync_api import Browser, Page, sync_playwright

from ci_workflow.application.source_research_service import (
    FreshAResearchContent,
    compute_research_content_digest,
)
from ci_workflow.qc.report_a_acceptance import inspect_legacy_report_a_sample
from ci_workflow.renderers.portal.report_a import (
    ReportAPortalData,
    render_report_a_site,
)

ROOT = Path(__file__).resolve().parents[2]
FRESH_CONTENT = ROOT / "fixtures/positive/a-atopic-dermatitis/research-content.json"
NEGATIVE_ROOT = ROOT / "fixtures/negative"
EXPECTED_CONTENT_DIGEST = "dc439a8c872e8f85224718bcb53eb1e170f51a2192a2a19178bf32865e45abc4"


@pytest.fixture(scope="module")
def rendered_ad_site(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("report-a-medical-manager")
    data = ReportAPortalData.model_validate(_payload()["report_data"])
    render_report_a_site(data, root)
    return root


@pytest.fixture(scope="module")
def chromium_browser() -> Browser:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        yield browser
        browser.close()


@pytest.fixture
def page(chromium_browser: Browser) -> Page:
    page = chromium_browser.new_page()
    yield page
    page.close()


def _open(page: Page, path: Path, *, width: int = 1280, height: int = 900) -> None:
    page.set_viewport_size({"width": width, "height": height})
    page.goto(path.as_uri())
    page.wait_for_function("document.readyState === 'complete'")


def _payload() -> dict[str, object]:
    return json.loads(FRESH_CONTENT.read_text(encoding="utf-8"))


def _rows(payload: dict[str, object], section: str, product_id: str) -> list[dict[str, object]]:
    report = payload["report_data"]
    assert isinstance(report, dict)
    values = report[section]
    assert isinstance(values, list)
    return [row for row in values if row["product_id"] == product_id]


def test_fresh_ad_content_is_frozen_complete_and_native_chinese() -> None:
    payload = _payload()
    content = FreshAResearchContent.model_validate(payload)

    assert compute_research_content_digest(payload) == EXPECTED_CONTENT_DIGEST
    assert content.indication == "特应性皮炎"
    assert len(content.report_data.products) == 38
    assert len(content.report_data.trials) == 43
    assert len(content.sources) == 65
    assert len(content.facts) == 271
    assert all(source.first_disclosed_at <= content.data_cutoff for source in content.sources)
    visible_text = json.dumps(content.report_data.model_dump(mode="json"), ensure_ascii=False)
    for forbidden in (
        "Gate",
        "Signal",
        "AI EVIDENCE",
        "Registry-only",
        "闭合",
        " AD ",
        "未从官方页面",
        "待更新",
    ):
        assert forbidden not in visible_text


def test_latest_phase_three_results_and_current_stop_decisions_are_not_overwritten() -> None:
    payload = _payload()
    amlitelimab = _rows(payload, "efficacy", "amlitelimab")
    rocatinlimab = _rows(payload, "efficacy", "rocatinlimab")
    rademikibart = _rows(payload, "efficacy", "sim0718")

    assert {(row["trial_id"], row["arm"], row["value"]) for row in amlitelimab} == {
        ("nct06130566", "治疗组", 39.1),
        ("nct06130566", "对照组", 19.1),
    }
    assert {(row["trial_id"], row["arm"], row["value"]) for row in rocatinlimab} == {
        ("nct05651711", "治疗组", 32.8),
        ("nct05651711", "对照组", 13.7),
    }
    assert {(row["trial_id"], row["arm"], row["value"]) for row in rademikibart} == {
        ("nct06477835", "治疗组", 74.2),
        ("nct06477835", "对照组", 34.4),
    }
    products = {
        row["id"]: row
        for row in payload["report_data"]["products"]  # type: ignore[index]
    }
    assert products["amlitelimab"]["status"] == "2026年7月停止特应性皮炎开发，不再申报"
    assert products["rocatinlimab"]["status"] == "2026年3月停止全部临床试验并继续安全随访"
    assert products["sim0718"]["status"] == "中国NDA审评中；2026年4月重新受理"


def test_approved_product_statuses_are_bound_to_regulatory_or_official_approval_sources() -> None:
    payload = _payload()
    source_by_id = {row["source_id"]: row for row in payload["sources"]}  # type: ignore[index]
    approved_products = {
        "dupilumab",
        "tralokinumab",
        "lebrikizumab",
        "nemolizumab",
        "abrocitinib",
        "upadacitinib",
        "baricitinib",
        "ruxolitinib-cream",
        "crisaborole",
        "tapinarof",
        "roflumilast-cream",
        "stapokibart",
    }
    facts = {
        row["entity_id"]: row
        for row in payload["facts"]  # type: ignore[index]
        if row["field_id"] == "product.current_status"
        and row["entity_id"] in approved_products
    }
    assert set(facts) == approved_products
    for product_id, fact in facts.items():
        source = source_by_id[fact["source_id"]]
        assert source["source_type"] == "regulatory_label_or_approval", product_id
        assert source["source_type"] != "clinical_trial_registry", product_id


def test_shr1819_and_ak120_keep_current_and_historical_trials_separate() -> None:
    payload = _payload()
    products = {
        row["id"]: row
        for row in payload["report_data"]["products"]  # type: ignore[index]
    }
    shr1819 = _rows(payload, "efficacy", "shr-1819")
    shr1819_sae = [
        row for row in _rows(payload, "safety", "shr-1819") if row["term"] == "任何SAE"
    ]

    trials = payload["report_data"]["trials"]  # type: ignore[index]
    history = payload["report_data"]["history"]  # type: ignore[index]

    assert products["shr-1819"]["phase"] == "III期"
    assert products["shr-1819"]["status"] == "III期青少年研究招募中"
    assert {(row["arm"], row["value"]) for row in shr1819} == {
        ("治疗组", 85.4),
        ("对照组", 37.8),
    }
    assert {(row["arm"], row["numerator"], row["denominator"]) for row in shr1819_sae} == {
        ("治疗组", 7, 120),
        ("对照组", 3, 37),
    }
    assert {
        (row["display_id"], row["phase"], row["status"])
        for row in trials
        if row["product_id"] == "shr-1819"
    } == {
        ("NCT05549947", "II期", "COMPLETED"),
        ("NCT06468956", "III期", "ACTIVE_NOT_RECRUITING"),
        ("NCT07309055", "III期", "RECRUITING"),
    }
    assert products["ak120"]["status"] == "III期登记状态未知；未公开登记结果"
    assert {
        (row["display_id"], row["phase"], row["status"])
        for row in trials
        if row["product_id"] == "ak120"
    } == {
        ("NCT06383468", "III期", "UNKNOWN"),
        ("NCT05048056", "II期", "TERMINATED"),
    }
    assert any(
        row["product_id"] == "ak120"
        and "NCT05048056" in row["status"]
        and "开发策略调整终止" in row["status"]
        for row in history
    )


def test_every_result_bearing_product_has_treatment_control_efficacy_and_key_safety() -> None:
    payload = _payload()
    report = payload["report_data"]
    products = {
        row["id"]
        for row in report["products"]  # type: ignore[index]
        if row["result_status"] == "有公开关键结果"
    }
    for product_id in products:
        efficacy = _rows(payload, "efficacy", product_id)
        safety = [
            row
            for row in _rows(payload, "safety", product_id)
            if row["value"] is not None and row["term"] in {"任何TEAE", "任何SAE"}
        ]
        assert {row["arm"] for row in efficacy} >= {"治疗组", "对照组"}, product_id
        assert {row["arm"] for row in safety} >= {"治疗组", "对照组"}, product_id


def test_registry_sae_values_match_embedded_event_group_numerators_and_denominators() -> None:
    payload = _payload()
    source_by_id = {row["source_id"]: row for row in payload["sources"]}  # type: ignore[index]
    fact_by_ref = {row["row_ref"]: row for row in payload["facts"]}  # type: ignore[index]
    for row in payload["report_data"]["safety"]:  # type: ignore[index]
        if row["term"] != "任何SAE" or row["value"] is None:
            continue
        fact = fact_by_ref[f"safety:{row['row_id']}"]
        source = source_by_id[fact["source_id"]]
        if source["source_type"] != "clinical_trial_registry":
            continue
        registry = json.loads(source["content_text"])
        groups = registry["resultsSection"]["adverseEventsModule"]["eventGroups"]
        assert any(
            group.get("seriousNumAffected") == row["numerator"]
            and group.get("seriousNumAtRisk") == row["denominator"]
            for group in groups
        ), row["row_id"]


def test_registry_other_event_total_is_never_mislabeled_as_any_teae() -> None:
    payload = _payload()
    source_by_id = {row["source_id"]: row for row in payload["sources"]}  # type: ignore[index]
    fact_by_ref = {row["row_ref"]: row for row in payload["facts"]}  # type: ignore[index]
    registry_teae = []
    for row in payload["report_data"]["safety"]:  # type: ignore[index]
        if row["term"] == "任何TEAE" and row["value"] is not None:
            fact = fact_by_ref[f"safety:{row['row_id']}"]
            if source_by_id[fact["source_id"]]["source_type"] == "clinical_trial_registry":
                registry_teae.append(row["row_id"])
    assert registry_teae == []


def test_result_bearing_product_without_key_safety_is_rejected_before_review() -> None:
    payload = copy.deepcopy(_payload())
    for row in payload["report_data"]["safety"]:  # type: ignore[index]
        if row["product_id"] == "dupilumab":
            row["value"] = None
            row["numerator"] = None
            row["denominator"] = None
            row["disclosure_state"] = "未公开"
    with pytest.raises(ValueError, match="缺少治疗组与对照组TEAE或SAE"):
        FreshAResearchContent.model_validate(payload)


@pytest.mark.parametrize(
    ("directory", "expected_issue"),
    [
        ("legacy-a-five-products-zero-trials", "products_without_trials"),
        ("legacy-a-style-break", "malformed_stylesheet"),
        ("legacy-a-false-green", "zero_card_false_green"),
        ("legacy-a-ad-shell", "unanchored_report_shell"),
    ],
)
def test_legacy_report_a_failures_are_rejected(directory: str, expected_issue: str) -> None:
    sample_root = NEGATIVE_ROOT / directory
    metadata = json.loads((sample_root / "sample.json").read_text(encoding="utf-8"))
    issues = inspect_legacy_report_a_sample(sample_root)
    assert metadata["expected_issue"] == expected_issue
    assert expected_issue in {issue.code for issue in issues}


def test_default_efficacy_view_is_truthful_compact_and_resettable(
    page: Page, rendered_ad_site: Path
) -> None:
    _open(page, rendered_ad_site / "efficacy.html")

    product_picker = page.locator("details[data-filter-dimension='product']")
    assert product_picker.count() == 1
    assert not product_picker.get_attribute("open")
    assert page.locator("[data-filter-reset]").get_by_text("清除筛选").count() == 1
    assert page.locator("[data-filter-value='EASI-75'][aria-pressed='true']").count() == 1
    assert page.locator("[data-filter-value='第16周'][aria-pressed='true']").count() == 1
    assert page.locator("[data-chart-id='efficacy-full']").bounding_box()["y"] < 820  # type: ignore[index]
    visible = page.locator("tbody tr:visible")
    assert visible.count() > 0
    assert {
        visible.nth(index).get_attribute("data-endpoint")
        for index in range(visible.count())
    } == {"EASI-75"}
    assert {
        visible.nth(index).get_attribute("data-timepoint")
        for index in range(visible.count())
    } == {"第16周"}


def test_safety_heatmap_is_scrollable_and_product_filter_updates_the_chart(
    page: Page, rendered_ad_site: Path
) -> None:
    _open(page, rendered_ad_site / "safety.html")

    host = page.locator("[data-chart-id='safety-full']")
    assert host.evaluate("node => getComputedStyle(node).overflowX") == "auto"
    page.locator("details[data-filter-dimension='product']").click()
    page.locator("[data-filter-dimension='product'] [data-filter-value='度普利尤单抗']").click()
    assert host.locator(".kz-a-heat-label").count() == 6
    assert host.locator(".kz-a-heat-label").nth(1).inner_text() == "度普利尤单抗"
    assert "已选择 1 项" in page.locator("[data-filter-selection-count='product']").inner_text()


def test_landscape_assigns_each_product_once_and_regulatory_timeline_is_directly_split(
    page: Page, rendered_ad_site: Path
) -> None:
    _open(page, rendered_ad_site / "landscape.html")
    chips = page.locator("[data-chart-id='landscape-full'] [data-visual-node='product']")
    names = [chips.nth(index).inner_text() for index in range(chips.count())]
    assert len(names) == len(set(names)) == 38

    _open(page, rendered_ad_site / "regulatory.html")
    page.locator("details[data-filter-dimension='product']").click()
    page.locator("[data-filter-dimension='product'] [data-filter-value='度普利尤单抗']").click()
    events = page.locator("[data-chart-id='regulatory-timeline'] [data-visual-node='event']")
    assert events.count() >= 2
    for index in range(events.count()):
        assert events.nth(index).locator("strong").inner_text() == "度普利尤单抗"
        assert events.nth(index).locator("b").inner_text().startswith(("中国｜", "境外｜"))


def test_trial_labels_are_native_chinese_and_header_collapses_before_it_clips(
    page: Page, rendered_ad_site: Path
) -> None:
    _open(page, rendered_ad_site / "products" / "shr-1819.html")
    visible = page.locator("body").inner_text()
    for raw_status in (
        "COMPLETED",
        "RECRUITING",
        "ACTIVE_NOT_RECRUITING",
        "TERMINATED",
        "UNKNOWN",
    ):
        assert raw_status not in visible
    assert "已完成" in visible
    assert "招募中" in visible
    assert "NCT05549947" in visible
    assert page.locator("#menu-toggle").is_visible()
    assert not page.locator("#global-search-input").is_visible()


def test_matrix_uses_numbered_bubbles_and_readable_product_legend(
    page: Page, rendered_ad_site: Path
) -> None:
    _open(page, rendered_ad_site / "matrix.html")
    page.locator("[data-matrix-control='safety-axis']").select_option(index=1)
    bubbles = page.locator("[data-chart-id='matrix-full'] .kz-a-bubble")
    legend = page.locator("[data-chart-id='matrix-full'] .kz-a-bubble-key")
    assert bubbles.count() == legend.locator("li").count()
    assert bubbles.count() >= 2
    for index in range(bubbles.count()):
        assert bubbles.nth(index).inner_text() == str(index + 1)
