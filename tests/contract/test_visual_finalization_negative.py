from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from ci_workflow.graph.visual_finalization import (
    VisualFinalizationError,
    validate_visual_finalization_plan,
)
from tests.contract.test_design_acceptance_contracts import (
    SHA_A,
    _valid_manifest,
    _valid_source_pack,
    _valid_verdict,
    _validate_run,
)
from tools.design_contract_validation import DesignContractError

ROOT = Path(__file__).resolve().parents[2]
A_FROZEN_SITE = ROOT / ".artifacts/a-values-matrix-fix-final-v5/reports/A/v1/html"
VISUAL_PLAN_SCHEMA = ROOT / "schemas/visual-finalization-plan.schema.json"
_USER_PIPELINE_TOKENS = re.compile(r"prompt|pipeline|accepted|pending|fixture|backend", re.I)
_TAGS = re.compile(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>|<[^>]+>", re.I)


def _html_interaction_states() -> list[dict[str, Any]]:
    labels = {
        "page_load": "首屏显示主要比较内容",
        "filter_change": "筛选后图表与表格同步更新",
        "drill_down": "下钻后定位到试验与具体指标",
        "search": "搜索后显示匹配结果并可恢复全量",
        "keyboard": "仅用键盘可完成主要操作",
        "reduced_motion": "关闭动效后内容仍完整可读",
    }
    return [
        {
            "state_id": trigger.replace("_", "-"),
            "trigger": trigger,
            "expected_behavior": behavior,
            "keyboard_accessible": True,
            "reduced_motion_behavior": "不依赖动效承载信息",
            "frozen_behavior": "导出时保留当前完整内容",
        }
        for trigger, behavior in labels.items()
    ]

def _valid_visual_plan() -> dict[str, Any]:
    return {
        "$schema": "schemas/visual-finalization-plan.schema.json",
        "schema_version": "1.0",
        "plan_id": "plan:A:html",
        "report_kind": "A",
        "report_version": "v1",
        "format": "html",
        "route_id": "portal",
        "report_snapshot_sha256": SHA_A,
        "report_snapshot": {
            "snapshot_id": "report-snapshot:A:v1",
            "report": "A",
            "report_version": "v1",
            "evidence_snapshot_id": "evidence-snapshot:A:v1",
            "claim_snapshot_id": "claim-snapshot:A:v1",
            "coverage_set_id": "coverage-set:A:v1",
        },
        "design_contract_sha256": "b" * 64,
        "design_contract": {
            "manifest": "contracts/kangzhe/manifest.json",
            "contract_version": "1.0",
            "route_id": "portal",
            "loaded_files": ["ROUTER.md", "core.md", "project_profile.md", "track_site.md"],
        },
        "scientific_snapshot_immutable": True,
        "audience": {
            "primary_role": "资深临床试验医学人员",
            "language": "zh-CN",
            "reading_tasks": ["比较竞品主要疗效与安全性"],
            "visible_program_state": False,
        },
        "page_responsibilities": [
            {
                "page_id": "overview",
                "page_type": "overview",
                "primary_question": "当前竞争格局与主要结果是什么？",
                "purpose": "首屏回答医学比较问题",
                "information_hierarchy": ["主要结论", "图表", "完整表格"],
                "claim_ids": ["claim-1"],
                "source_facts_preserved": True,
            }
        ],
        "visual_variables": {
            "theme": "kangzhe",
            "palette_tokens": ["kz-orange", "kz-med-blue"],
            "department_tokens": {
                "MED": "kz-orange",
                "CO": "kz-med-blue",
                "DMST": "kz-stats-green",
                "PV": "kz-pv",
            },
            "surface_tokens": ["kz-white", "kz-bg"],
            "font_stack": ["PingFang SC", "sans-serif"],
            "font_sizes_px": [16, 18],
            "spacing_tokens_px": [8, 16],
            "motion_tokens": ["none"],
            "reduced_motion_supported": True,
            "export_freeze_supported": True,
        },
        "chart_syntax": [
            {
                "chart_id": "chart-1",
                "question": "治疗组与对照组的主要终点如何比较？",
                "mark": "bar",
                "dimensions": {"x": "结果", "label": "产品"},
                "redundant_encoding": "direct_label",
                "source_claim_ids": ["claim-1"],
            }
        ],
        "table_syntax": [
            {
                "table_id": "table-1",
                "purpose": "保留完整比较数据",
                "columns": ["产品", "结果", "分母"],
                "completeness": "complete",
                "after_chart": True,
                "source_claim_ids": ["claim-1"],
            }
        ],
        "interaction_states": _html_interaction_states(),
        "acceptance_matrix": [
            {
                "domain": domain,
                "criteria": [f"在对应页面截图中核对{domain}的对象、状态和数值"],
                "required": True,
            }
            for domain in (
                "copy_zh",
                "hierarchy_density",
                "typography_spacing",
                "color_legibility",
                "charts_tables",
                "interaction_consistency",
                "format_rendering",
            )
        ],
        "planner_identity": "visual-planner-001",
        "planner_role": "visual-design-director",
        "created_at": "2026-08-29T09:00:00+08:00",
    }


def _visual_plan_errors(plan: dict[str, Any]) -> list[Any]:
    schema = json.loads(VISUAL_PLAN_SCHEMA.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    return list(validator.iter_errors(plan))


def test_visual_plan_schema_accepts_a_complete_bound_plan() -> None:
    assert VISUAL_PLAN_SCHEMA.is_file()
    assert _visual_plan_errors(_valid_visual_plan()) == []


def test_visual_plan_validator_accepts_a_complete_bound_plan() -> None:
    plan = _valid_visual_plan()

    validated = validate_visual_finalization_plan(
        plan,
        expected_report_snapshot_sha256=SHA_A,
        expected_design_contract_sha256="b" * 64,
    )

    assert validated["plan_id"] == plan["plan_id"]


def test_visual_plan_validator_rejects_authority_digest_drift() -> None:
    with pytest.raises(VisualFinalizationError, match="报告快照摘要"):
        validate_visual_finalization_plan(
            _valid_visual_plan(),
            expected_report_snapshot_sha256="c" * 64,
        )


def test_visual_plan_validator_rejects_format_route_mismatch() -> None:
    plan = _valid_visual_plan()
    plan["route_id"] = "pptx"

    with pytest.raises(VisualFinalizationError, match="Schema|route_id"):
        validate_visual_finalization_plan(plan)


def test_visual_plan_validator_rejects_mixed_design_tracks() -> None:
    plan = _valid_visual_plan()
    plan["design_contract"]["loaded_files"].append("track_pptx.md")

    with pytest.raises(VisualFinalizationError, match="混入其他媒介轨"):
        validate_visual_finalization_plan(plan)


def test_visual_plan_validator_rejects_color_only_heatmap() -> None:
    plan = _valid_visual_plan()
    chart = plan["chart_syntax"][0]
    chart["mark"] = "heatmap"
    chart["dimensions"] = {"x": "结果", "y": "产品", "color": "发生率"}
    chart["redundant_encoding"] = "none"

    with pytest.raises(VisualFinalizationError, match="不能只依赖颜色"):
        validate_visual_finalization_plan(plan)


def test_visual_plan_validator_rejects_incomplete_acceptance_domains() -> None:
    plan = _valid_visual_plan()
    plan["acceptance_matrix"][0]["domain"] = plan["acceptance_matrix"][1]["domain"]

    with pytest.raises(VisualFinalizationError, match="验收矩阵域"):
        validate_visual_finalization_plan(plan)


def test_visual_plan_validator_rejects_equivalent_chart_as_html_table() -> None:
    plan = _valid_visual_plan()
    plan["table_syntax"][0]["completeness"] = "equivalent_chart"

    with pytest.raises(VisualFinalizationError, match="Schema|completeness"):
        validate_visual_finalization_plan(plan)


def test_visual_plan_validator_rejects_missing_default_interaction_state() -> None:
    plan = _valid_visual_plan()
    plan["interaction_states"] = [
        state for state in plan["interaction_states"] if state["trigger"] != "page_load"
    ]

    with pytest.raises(VisualFinalizationError, match="page_load"):
        validate_visual_finalization_plan(plan)


@pytest.mark.parametrize(
    "trigger", ["filter_change", "drill_down", "search", "keyboard", "reduced_motion"]
)
def test_html_visual_plan_requires_each_real_use_interaction(trigger: str) -> None:
    plan = _valid_visual_plan()
    plan["interaction_states"] = [
        state for state in plan["interaction_states"] if state["trigger"] != trigger
    ]

    with pytest.raises(VisualFinalizationError, match=trigger):
        validate_visual_finalization_plan(plan)


def test_visual_plan_rejects_generic_acceptance_language() -> None:
    plan = _valid_visual_plan()
    plan["acceptance_matrix"][0]["criteria"] = ["通过当前格式专属检查"]

    with pytest.raises(VisualFinalizationError, match="笼统通过语句"):
        validate_visual_finalization_plan(plan)


def test_visual_plan_validator_rejects_a_page_that_drops_locked_facts() -> None:
    plan = _valid_visual_plan()
    plan["page_responsibilities"][0]["source_facts_preserved"] = False

    with pytest.raises(VisualFinalizationError):
        validate_visual_finalization_plan(plan)

@pytest.mark.parametrize(
    "field",
    [
        "report_snapshot_sha256",
        "design_contract_sha256",
        "visual_variables",
        "acceptance_matrix",
        "planner_identity",
    ],
)
def test_visual_plan_schema_rejects_missing_binding_or_review_field(field: str) -> None:
    plan = _valid_visual_plan()
    del plan[field]

    assert _visual_plan_errors(plan)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("report_kind", "X"),
        ("format", "rtf"),
        ("route_id", "site"),
        ("report_snapshot_sha256", "not-a-digest"),
        ("scientific_snapshot_immutable", False),
        ("planner_role", "render-deliver"),
    ],
)
def test_visual_plan_schema_rejects_invalid_binding_values(field: str, value: Any) -> None:
    plan = _valid_visual_plan()
    plan[field] = value

    assert _visual_plan_errors(plan)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("visual_variables", "palette_tokens"), ["kz-orange", "brand-purple"]),
        (("visual_variables", "font_sizes_px"), [15]),
        (("visual_variables", "spacing_tokens_px"), [7]),
        (("visual_variables", "motion_tokens"), ["bounce"]),
    ],
)
def test_visual_plan_schema_rejects_arbitrary_visual_tokens(
    path: tuple[str, str], value: Any
) -> None:
    plan = _valid_visual_plan()
    plan[path[0]][path[1]] = value

    assert _visual_plan_errors(plan)


def test_visual_plan_schema_rejects_a_short_acceptance_matrix() -> None:
    plan = _valid_visual_plan()
    plan["acceptance_matrix"].pop()

    assert _visual_plan_errors(plan)


def test_visual_plan_schema_rejects_unknown_program_state_fields() -> None:
    plan = _valid_visual_plan()
    plan["accepted"] = True

    assert _visual_plan_errors(plan)



def test_current_run_verdict_cannot_reuse_another_render_digest() -> None:
    verdict = _valid_verdict()
    verdict["render_sha256"] = SHA_A

    with pytest.raises(DesignContractError, match="渲染摘要"):
        _validate_run(_valid_manifest(), verdict)


@pytest.mark.parametrize("receipt_field", ["design_contract_sha256", "source_pack_sha256"])
def test_current_run_receipt_cannot_bind_a_foreign_contract(
    receipt_field: str,
) -> None:
    manifest = _valid_manifest()
    manifest["receipts"][0][receipt_field] = SHA_A

    with pytest.raises(DesignContractError, match="没有绑定当前运行"):
        _validate_run(manifest, _valid_verdict(manifest))


def test_visual_chart_occurrence_cannot_change_a_locked_claim_value() -> None:
    source_pack = _valid_source_pack()
    source_pack["occurrences"][0]["normalized_value"] = "-1.1分（第24周，全分析集，n=100）"

    from tools.design_contract_validation import validate_source_pack

    with pytest.raises(DesignContractError, match="归一化值不一致"):
        validate_source_pack(
            source_pack,
            ROOT / "contracts/kangzhe/design_specs/schemas/design-source-pack.schema.json",
        )


@pytest.mark.parametrize("check_name", ["current_run", "real_artifact", "real_render"])
def test_visual_verdict_cannot_omit_a_current_run_check(check_name: str) -> None:
    verdict = _valid_verdict()
    del verdict["checks"][check_name]

    with pytest.raises(DesignContractError, match=check_name):
        _validate_run(_valid_manifest(), verdict)


def _visible_text(path: Path) -> str:
    return html.unescape(_TAGS.sub(" ", path.read_text(encoding="utf-8")))


def test_frozen_a_portal_pages_are_chinese_and_pipeline_free() -> None:
    pages = sorted(A_FROZEN_SITE.rglob("*.html"))
    assert len(pages) == 50

    for page in pages:
        source = page.read_text(encoding="utf-8")
        assert '<html lang="zh-CN">' in source, page
        assert 'name="viewport"' in source, page
        visible = _visible_text(page)
        assert _USER_PIPELINE_TOKENS.search(visible) is None, page


def test_frozen_a_portal_sitemap_has_one_physical_target_per_route() -> None:
    sitemap: dict[str, Any] = json.loads(
        (A_FROZEN_SITE / "data/sitemap.json").read_text(encoding="utf-8")
    )
    routes = sitemap["routes"]
    assert len(routes) == 50
    assert len({item["route"] for item in routes}) == len(routes)

    for item in routes:
        target = A_FROZEN_SITE / item["path"]
        assert target.is_file(), item


def test_frozen_a_safety_and_home_keep_chart_before_complete_table() -> None:
    overview = (A_FROZEN_SITE / "overview.html").read_text(encoding="utf-8")
    assert 'data-chart-id="home-safety"' in overview

    safety = (A_FROZEN_SITE / "safety.html").read_text(encoding="utf-8")
    chart_position = safety.index('data-chart-id="safety-full"')
    table_position = safety.index("<table")
    assert chart_position < table_position
    for label in ("严重不良事件", "特别关注不良事件", "治疗期间不良事件", "常见不良事件"):
        assert label in safety
