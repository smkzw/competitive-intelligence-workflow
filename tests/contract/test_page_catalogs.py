from __future__ import annotations

from pathlib import Path
from typing import cast

import yaml

ROOT = Path(__file__).resolve().parents[2]
CATALOG_ROOT = ROOT / "docs/architecture/page-catalogs"
EXPECTED_PAGES = {
    "A": {
        "overview",
        "landscape",
        "product-overview",
        "clinical-portfolio",
        "efficacy",
        "safety",
        "matrix",
        "regulatory",
        "companies-transactions",
        "patents-protection",
        "historical-edge",
        "evidence-limitations",
    },
    "B": {
        "overview",
        "efficacy",
        "longitudinal-results",
        "safety",
        "baseline-overview",
        "baseline-demographics",
        "baseline-disease-context",
        "baseline-severity",
        "disposition-overview",
        "participant-flow",
        "adherence",
        "loss-exit",
        "screen-failure",
        "rescue-treatment",
        "prohibited-medication",
        "plan-deviation",
        "trial-exposure-context",
        "subgroups-supporting-evidence",
        "product-trial-profiles",
        "efficacy-safety-matrix",
        "evidence-limitations",
    },
    "C": {
        "overview",
        "design-map",
        "trial-profile",
        "population-disease-definition",
        "inclusion-criteria",
        "exclusion-criteria",
        "treatment-arms",
        "endpoint-timepoint-matrix",
        "visit-duration-followup",
        "sample-analysis-statistics",
        "design-patterns",
        "evidence-versions-limitations",
    },
}
FORBIDDEN_COPY = {
    "A 类关键字段门槛",
    "AI EVIDENCE SYNTHESIS",
    "Registry-only",
    "Publication 用于交叉核验",
    "evidence synthesis",
    "GateSpec",
    "prompt",
    "workflow",
    "检索次数",
    "覆盖率",
}


def _load(report: str) -> dict[str, object]:
    value = yaml.safe_load((CATALOG_ROOT / f"{report}.yaml").read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return cast(dict[str, object], value)


def test_a_b_c_page_catalogs_freeze_every_v12_responsibility_without_top_n() -> None:
    for report, expected_ids in EXPECTED_PAGES.items():
        catalog = _load(report)
        assert catalog["contract_version"] == "1.0"
        assert catalog["report"] == report
        selection = cast(dict[str, object], catalog["selection_policy"])
        assert selection == {
            "top_n_allowed": False,
            "all_in_scope_objects_visible": True,
            "default_product_order": "按靶点分组，组内按稳定产品标识",
        }
        assert catalog["presentation_policy"] == {
            "chart_before_table": True,
            "graph_and_table_same_fact_set": True,
            "complete_table_never_replaced_by_summary": True,
        }

        pages = cast(list[dict[str, object]], catalog["pages"])
        assert {str(page["id"]) for page in pages} == expected_ids
        assert len(pages) == len(expected_ids)
        for page in pages:
            assert str(page["title"]).strip()
            assert str(page["responsibility"]).strip()
            assert cast(list[str], page["visuals"])
            assert page["complete_table"] is True
            assert cast(list[str], page["filter_profiles"])
            assert str(page["evidence_drawer_profile"]).strip()
            assert page["route"] == f"/{report.casefold()}/{page['id']}"


def test_user_facing_page_copy_excludes_prompt_log_and_mixed_language_labels() -> None:
    for report in EXPECTED_PAGES:
        raw = (CATALOG_ROOT / f"{report}.yaml").read_text(encoding="utf-8")
        for forbidden in FORBIDDEN_COPY:
            assert forbidden.casefold() not in raw.casefold()
        catalog = _load(report)
        pages = cast(list[dict[str, object]], catalog["pages"])
        for page in pages:
            title = str(page["title"])
            assert "类报告" not in title
            assert "门槛" not in title
            assert "日志" not in title


def test_b_catalog_keeps_baseline_and_disposition_as_real_pages() -> None:
    pages = {
        str(page["id"]): page for page in cast(list[dict[str, object]], _load("B")["pages"])
    }
    baseline = {
        "baseline-overview",
        "baseline-demographics",
        "baseline-disease-context",
        "baseline-severity",
    }
    disposition = {
        "disposition-overview",
        "participant-flow",
        "adherence",
        "loss-exit",
        "screen-failure",
        "rescue-treatment",
        "prohibited-medication",
        "plan-deviation",
    }
    assert baseline | disposition <= set(pages)
    assert all(pages[page_id]["navigation_group"] == "基线与人群" for page_id in baseline)
    assert all(pages[page_id]["navigation_group"] == "试验完成情况" for page_id in disposition)
    assert pages["disposition-overview"]["empty_numeric_fallback"] == "披露状态矩阵"


def test_default_selection_rules_are_versioned_and_never_optimize_observed_results() -> None:
    for report in EXPECTED_PAGES:
        rules = cast(dict[str, object], _load(report)["selection_rules"])
        assert rules["version"] == "1.0"
        assert set(rules) >= {
            "anchor_trial",
            "endpoint_family",
            "common_ae_rows",
            "baseline_variable_order",
            "disposition_field_order",
        }
    for report in ("A", "B"):
        rules = cast(dict[str, object], _load(report)["selection_rules"])
        anchor_rule = str(rules["anchor_trial"])
        assert "不使用疗效或安全性数值偏好" in anchor_rule
        endpoint_rule = str(rules["endpoint_family"])
        assert "同时并列显示" in endpoint_rule
        assert "适用指导原则推荐" in endpoint_rule
        assert "核心竞品共同采用" in endpoint_rule
        common_ae_rule = str(rules["common_ae_rows"])
        assert "最大绝对治疗—对照差" in common_ae_rule
        assert "最高报告发生率" in common_ae_rule
        assert "不形成安全性排名" in common_ae_rule
    c_rules = cast(dict[str, object], _load("C")["selection_rules"])
    assert c_rules["minimum_candidate_design_paths"] == 2
    assert c_rules["unique_best_design_allowed"] is False

    b_rules = cast(dict[str, object], _load("B")["selection_rules"])
    assert str(b_rules["baseline_variable_order"]).startswith("疾病严重程度与关键判定指标")
    disposition_order = str(b_rules["disposition_field_order"])
    ordered_terms = ["筛选与筛败", "随机与接受治疗", "失访", "依从性", "补救治疗", "方案偏离"]
    positions = [disposition_order.index(term) for term in ordered_terms]
    assert positions == sorted(positions)


def test_a_and_b_bubble_charts_freeze_axis_direction_and_sample_size_radius() -> None:
    for report in ("A", "B"):
        bubble = cast(dict[str, object], _load(report)["bubble_chart_contract"])
        assert bubble["y_axis"] == "原始治疗期间不良事件发生率倒序"
        assert bubble["y_axis_annotation"] == (
            "向上 = 发生率更低 = 观察到的安全性位置更有利"
        )
        assert bubble["x_axis_direction"] == "越右表示所选疗效指标的观察信号越强"
        assert bubble["radius_formula"] == "r = k × sqrt(N/pi)"
        assert bubble["no_pooling"] is True
        assert bubble["no_composite_score"] is True
