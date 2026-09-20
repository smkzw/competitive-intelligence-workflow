from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, cast

import pytest
from jsonschema import Draft202012Validator

from ci_workflow.graph.visual_finalization import (
    VisualFinalizationError,
    _load_plan_schema,
    validate_visual_finalization_plan,
)

ROOT = Path(__file__).resolve().parents[2]
PLAN_SCHEMA = ROOT / "schemas" / "visual-finalization-plan.schema.json"
PACKAGED_PLAN_SCHEMA = (
    ROOT / "src" / "ci_workflow" / "schemas" / "visual-finalization-plan.schema.json"
)
SHA_A = "a" * 64
SHA_B = "b" * 64
ACCEPTANCE_DOMAINS = [
    "copy_zh",
    "hierarchy_density",
    "typography_spacing",
    "color_legibility",
    "charts_tables",
    "interaction_consistency",
    "format_rendering",
]


def _html_interaction_states() -> list[dict[str, Any]]:
    labels = {
        "page_load": "默认全量比较完整显示",
        "filter_change": "筛选后图表与表格同步更新",
        "drill_down": "下钻后定位到药物、试验与指标",
        "search": "搜索后仅保留匹配结果并可清除",
        "keyboard": "仅用键盘可完成主要浏览与操作",
        "reduced_motion": "减少动效时内容直接完整显示",
    }
    return [
        {
            "state_id": trigger.replace("_", "-"),
            "trigger": trigger,
            "expected_behavior": behavior,
            "keyboard_accessible": True,
            "reduced_motion_behavior": "不依赖动画承载信息",
            "frozen_behavior": "导出时保持稳定终态",
        }
        for trigger, behavior in labels.items()
    ]


def _plan(*, format_id: str = "html", route_id: str = "portal") -> dict[str, Any]:
    return {
        "$schema": "schemas/visual-finalization-plan.schema.json",
        "schema_version": "1.0",
        "plan_id": "visual-plan-A-html-v1",
        "report_kind": "A",
        "report_version": "v1",
        "format": format_id,
        "route_id": route_id,
        "report_snapshot_sha256": SHA_A,
        "report_snapshot": {
            "snapshot_id": "report-snapshot-A-v1",
            "report": "A",
            "report_version": "v1",
            "evidence_snapshot_id": "evidence-snapshot-A-v1",
            "claim_snapshot_id": "claim-snapshot-A-v1",
            "coverage_set_id": "coverage-set-A-v1",
        },
        "design_contract_sha256": SHA_B,
        "design_contract": {
            "manifest": "contracts/kangzhe/manifest.json",
            "contract_version": "1.0",
            "route_id": route_id,
            "loaded_files": [
                "contracts/kangzhe/design_specs/ROUTER.md",
                "contracts/kangzhe/design_specs/core.md",
                "contracts/kangzhe/design_specs/project_profile.md",
                "contracts/kangzhe/design_specs/track_site.md",
            ],
        },
        "scientific_snapshot_immutable": True,
        "audience": {
            "primary_role": "资深临床试验医学人员",
            "language": "zh-CN",
            "reading_tasks": ["比较疗效与安全性", "下钻到试验和证据定位"],
            "visible_program_state": False,
        },
        "page_responsibilities": [
            {
                "page_id": "overview",
                "page_type": "首页",
                "primary_question": "当前竞品格局的关键差异是什么？",
                "purpose": "先呈现总体比较，再提供详情入口",
                "information_hierarchy": ["总体结论", "关键疗效", "关键安全性"],
                "claim_ids": ["claim-a-001"],
                "source_facts_preserved": True,
            }
        ],
        "visual_variables": {
            "theme": "kangzhe",
            "palette_tokens": ["kz-orange", "kz-yellow", "kz-risk", "kz-med-blue"],
            "department_tokens": {
                "MED": "kz-orange",
                "CO": "kz-med-blue",
                "DMST": "kz-stats-green",
                "PV": "kz-pv",
            },
            "surface_tokens": ["kz-white", "kz-bg", "kz-surface-warm"],
            "font_stack": ["Microsoft YaHei", "Arial"],
            "font_sizes_px": [16, 19, 32],
            "spacing_tokens_px": [4, 8, 12, 16, 24, 32, 40, 56],
            "motion_tokens": ["none", "dur", "ease-out"],
            "reduced_motion_supported": True,
            "export_freeze_supported": True,
        },
        "chart_syntax": [
            {
                "chart_id": "efficacy-overview",
                "question": "各治疗组主要终点变化如何？",
                "mark": "bar",
                "dimensions": {
                    "x": "治疗组",
                    "y": "主要终点变化值",
                    "color": "治疗组",
                    "label": "数值与时间点",
                },
                "source_claim_ids": ["claim-a-001"],
            }
        ],
        "table_syntax": [
            {
                "table_id": "efficacy-detail",
                "purpose": "保留图表对应的完整数据行",
                "columns": ["产品", "终点", "时间点", "治疗组值", "对照组值"],
                "completeness": "complete",
                "after_chart": True,
                "source_claim_ids": ["claim-a-001"],
            }
        ],
        "interaction_states": _html_interaction_states(),
        "acceptance_matrix": [
            {
                "domain": domain,
                "criteria": [f"在真实呈现截图中核对{domain}的具体对象、状态与数值"],
                "required": True,
            }
            for domain in ACCEPTANCE_DOMAINS
        ],
        "planner_identity": "visual-design-director/run-001",
        "planner_role": "visual-design-director",
        "created_at": "2026-08-29T15:00:00+08:00",
    }


def test_schema_is_valid_and_packaged_copy_is_identical() -> None:
    schema = json.loads(PLAN_SCHEMA.read_text(encoding="utf-8"))
    assert isinstance(schema, dict)
    Draft202012Validator.check_schema(schema)
    assert PACKAGED_PLAN_SCHEMA.read_bytes() == PLAN_SCHEMA.read_bytes()


def test_visual_plan_validator_accepts_bound_plan() -> None:
    plan = _plan()
    validated = validate_visual_finalization_plan(
        plan,
        expected_report_snapshot_sha256=SHA_A,
        expected_design_contract_sha256=SHA_B,
    )
    assert validated["plan_id"] == "visual-plan-A-html-v1"


def test_visual_plan_validator_rejects_snapshot_digest_drift() -> None:
    with pytest.raises(VisualFinalizationError, match="报告快照摘要"):
        validate_visual_finalization_plan(_plan(), expected_report_snapshot_sha256=SHA_B)


def test_visual_plan_validator_rejects_format_route_mismatch() -> None:
    plan = _plan(format_id="html-ppt", route_id="portal")
    with pytest.raises(VisualFinalizationError, match="Schema|format"):
        validate_visual_finalization_plan(plan)


def test_visual_plan_validator_rejects_mixed_design_tracks() -> None:
    plan = _plan()
    cast(dict[str, Any], plan["design_contract"])["loaded_files"].append(
        "contracts/kangzhe/design_specs/track_htmlppt.md"
    )
    with pytest.raises(VisualFinalizationError, match="混入其他媒介轨"):
        validate_visual_finalization_plan(plan)


def test_visual_plan_validator_rejects_color_only_heatmap() -> None:
    plan = _plan()
    plan["chart_syntax"][0] = {
        "chart_id": "safety-heatmap",
        "question": "不同安全性维度的发生率如何？",
        "mark": "heatmap",
        "dimensions": {"x": "事件", "y": "产品", "color": "发生率"},
        "source_claim_ids": ["claim-a-001"],
    }
    with pytest.raises(VisualFinalizationError, match="不能只依赖颜色"):
        validate_visual_finalization_plan(plan)


def test_visual_plan_validator_rejects_incomplete_acceptance_domains() -> None:
    plan = copy.deepcopy(_plan())
    plan["acceptance_matrix"][-1]["domain"] = "copy_zh"
    with pytest.raises(VisualFinalizationError, match="验收矩阵"):
        validate_visual_finalization_plan(plan)


def test_plan_schema_resolves_from_packaged_layout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import ci_workflow.graph.visual_finalization as module

    packaged = tmp_path / "site-packages" / "ci_workflow" / "schemas"
    packaged.mkdir(parents=True)
    (packaged / PLAN_SCHEMA.name).write_bytes(PLAN_SCHEMA.read_bytes())
    monkeypatch.setattr(
        module,
        "__file__",
        str(tmp_path / "site-packages" / "ci_workflow" / "graph" / "visual_finalization.py"),
    )
    assert _load_plan_schema() == json.loads(PLAN_SCHEMA.read_text(encoding="utf-8"))
