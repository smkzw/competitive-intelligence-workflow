from __future__ import annotations

from pathlib import Path
from typing import cast

import yaml

ROOT = Path(__file__).resolve().parents[2]
FORMAT_ROOT = ROOT / "docs/architecture/format-contracts"
EXPECTED_FORMATS = {"html", "pdf", "html-ppt", "pptx"}
CURRENT_DESIGN_MANIFEST = "contracts/kangzhe/manifest.json"


def _load(name: str) -> dict[str, object]:
    value = yaml.safe_load((FORMAT_ROOT / f"{name}.yaml").read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return cast(dict[str, object], value)


def test_all_formats_bind_one_snapshot_coverage_and_project_design_contract() -> None:
    for format_id in EXPECTED_FORMATS:
        contract = _load(format_id)
        assert contract["contract_version"] == "1.0"
        assert contract["format"] == format_id
        assert str(contract["user_label"]).strip()
        assert contract["design_contract"] == {
            "manifest": CURRENT_DESIGN_MANIFEST,
            "policy": "项目内冻结合同，后续不自动同步通用版",
        }
        source = cast(dict[str, object], contract["source_contract"])
        assert source["same_locked_report_snapshot"] is True
        assert source["same_claim_and_evidence_sets"] is True
        assert source["canonical_coverage_set_required"] is True
        assert source["coverage_projection_required"] is True
        assert source["unexplained_coverage_difference_fails"] is True
        assert source["filtered_export_is_distinct_artifact"] is True
        assert source["filtered_export_has_no_scope_explanation_page"] is True


def test_html_pdf_keep_complete_tables_and_presentations_require_equivalence() -> None:
    for format_id in ("html", "pdf"):
        content = cast(dict[str, object], _load(format_id)["content_contract"])
        assert content["chart_before_table"] is True
        assert content["complete_table_after_chart"] is True
        assert content["table_omission_allowed"] is False
    for format_id in ("html-ppt", "pptx"):
        content = cast(dict[str, object], _load(format_id)["content_contract"])
        assert content["visual_first"] is True
        assert content["table_omission_allowed_only_when_chart_is_equivalent"] is True
        assert content["coverage_exception_receipt_required"] is True
        assert content["unlimited_pages_before_shrinking_or_deleting"] is True


def test_each_format_is_native_not_a_screenshot_or_cross_format_copy() -> None:
    html = _load("html")
    assert cast(dict[str, object], html["runtime"])["minimum_physical_pages"] == 2
    assert cast(dict[str, object], html["runtime"])["file_and_static_server"] is True
    assert cast(dict[str, object], html["runtime"])["remote_runtime_assets_allowed"] is False

    pdf = _load("pdf")
    assert cast(dict[str, object], pdf["runtime"])["native_pdf_not_web_or_slide_capture"] is True
    assert cast(dict[str, object], pdf["runtime"])["searchable_selectable_text"] is True
    assert cast(dict[str, object], pdf["runtime"])["default_page"] == "A4 纵向"
    pdf_runtime = cast(dict[str, object], pdf["runtime"])
    assert pdf_runtime["landscape_auto_switch"] == [
        "宽表",
        "森林图",
        "纵向多系列",
        "设计时间线",
        "终点矩阵",
    ]
    assert pdf_runtime["orientation_change_only_at_page_boundary"] is True
    assert pdf_runtime["bookmarks_required"] is True

    html_ppt = _load("html-ppt")
    html_ppt_runtime = cast(dict[str, object], html_ppt["runtime"])
    assert html_ppt_runtime["canvas"] == "1280×720"
    assert html_ppt_runtime["speaker_view_key"] == "S"
    assert html_ppt_runtime["speaker_notes_chinese_characters"] == "150–300"
    assert html_ppt_runtime["speaker_view_contents"] == [
        "当前页",
        "下一页",
        "逐字稿",
        "计时器",
    ]
    assert html_ppt_runtime["site_page_capture_allowed"] is False
    assert html_ppt_runtime["visual_acceptance_viewports"] == [
        "1280×720",
        "1920×1080",
        "2048×1024",
        "用户实际最大化窗口",
    ]
    assert html_ppt_runtime["page_number_excluded_page_types"] == [
        "封面",
        "目录",
        "章节首页",
        "结束页",
    ]

    pptx = _load("pptx")
    runtime = cast(dict[str, object], pptx["runtime"])
    assert runtime["generator"] == "PPT Master"
    assert runtime["editable_objects_required"] is True
    assert runtime["html_or_image_page_allowed"] is False
    assert runtime["serial_steps"] == [
        "初始化",
        "内容策略与设计锁定",
        "逐页 SVG",
        "质量检查",
        "备注",
        "收尾处理",
        "原生导出",
        "可编辑性核验",
        "原分辨率逐页视觉检查",
    ]


def test_each_format_names_shortcuts_to_reject_and_real_checks_to_run() -> None:
    for format_id in EXPECTED_FORMATS:
        contract = _load(format_id)
        shortcuts = cast(list[str], contract["forbidden_shortcuts"])
        verification = cast(list[str], contract["verification"])
        assert len(shortcuts) >= 4
        assert len(verification) >= 4
        assert all(item.strip() for item in shortcuts + verification)

    assert "在合同视口逐页进行真实视觉检查" in cast(
        list[str], _load("html")["verification"]
    )
    pdf_checks = cast(list[str], _load("pdf")["verification"])
    assert "标准 PDF 阅读器可打开" in pdf_checks
    assert "百分之百缩放与打印均可读" in pdf_checks
