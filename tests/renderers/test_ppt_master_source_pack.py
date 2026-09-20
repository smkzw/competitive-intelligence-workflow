"""PPT Master 来源包合同与确定性投影测试。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from ci_workflow.renderers.pptx_master.source_pack import (
    SourcePackBuildError,
    build_source_pack,
    load_page_strategy,
    load_source_pack_summary,
    validate_source_pack_summary,
    write_source_pack,
)

pytestmark = [pytest.mark.retained_legacy_format]

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "fixtures" / "synthetic" / "three-report-complete" / "inputs"


def _load(name: str) -> dict[str, Any]:
    return json.loads((FIXTURE / name).read_text(encoding="utf-8"))


def _snapshot(report: str, coverage_set_id: str) -> dict[str, Any]:
    return {
        "project_id": "project-three-report",
        "report": report,
        "report_version": "v-fixture-001",
        "snapshot_id": "snapshot-three-report-complete-001",
        "snapshot_sha256": "1" * 64,
        "claim_snapshot_id": "claim-snapshot-three-report-001",
        "evidence_snapshot_id": "evidence-snapshot-three-report-001",
        "coverage_set_id": coverage_set_id,
        "locked_at": "2026-08-31T12:00:00+08:00",
    }


def _coverage(report: str) -> dict[str, Any]:
    return {
        "coverage_set_id": f"coverage-set-{report.lower()}-001",
        "report": report,
        "report_version": "v-fixture-001",
        "evidence_snapshot_id": "evidence-snapshot-three-report-001",
        "claim_snapshot_id": "claim-snapshot-three-report-001",
        "items": [
            {
                "item_id": f"coverage-item-{report.lower()}-overview",
                "kind": "page",
                "page_responsibility_id": "overview",
                "label_zh": "首页",
                "referenced_ids": [f"report-{report.lower()}"],
            }
        ],
    }


def _design_contract() -> dict[str, Any]:
    return {
        "manifest": "contracts/kangzhe/manifest.json",
        "route": "pptx",
        "contract_version": "1.0",
        "digest": "2" * 64,
        "files": {"track_pptx.md": "3" * 64},
    }


def _build(report: str):
    data = _load(f"report-{report.lower()}-data.json")
    return build_source_pack(
        report,
        data,
        _snapshot(report, f"coverage-set-{report.lower()}-001"),
        _coverage(report),
        load_page_strategy(report),
        _design_contract(),
    )


def test_all_reports_share_locked_snapshot_and_have_independent_source_packs() -> None:
    packs = [_build(report) for report in ("A", "B", "C")]

    assert [pack.summary.report for pack in packs] == ["A", "B", "C"]
    assert {pack.summary.snapshot_id for pack in packs} == {"snapshot-three-report-complete-001"}
    assert {pack.summary.snapshot_sha256 for pack in packs} == {"1" * 64}
    assert len({pack.summary.source_pack_id for pack in packs}) == 3
    assert len({pack.summary.source_pack_sha256 for pack in packs}) == 3
    assert all("特应性皮炎" in pack.markdown for pack in packs)
    assert all("<svg" not in pack.markdown.lower() for pack in packs)
    assert all(pack.summary.no_svg is True for pack in packs)


def test_source_pack_preserves_report_facts_page_strategy_and_contract_binding() -> None:
    pack = _build("B")

    assert "泰瑞奇单抗" in pack.markdown
    assert "澄明-3" in pack.markdown
    assert "基线与人群总览" in pack.markdown
    assert "coverage-set-b-001" in pack.markdown
    assert pack.summary.page_count == len(load_page_strategy("B")["pages"])
    assert pack.summary.fact_counts["products"] == 2
    assert pack.summary.fact_counts["trials"] == 2
    assert pack.summary.design_contract_sha256 == "2" * 64
    assert pack.summary.design_contract.route == "pptx"
    validate_source_pack_summary(pack.summary, markdown=pack.markdown)


def test_write_and_reload_summary_without_svg_side_effects(tmp_path: Path) -> None:
    pack = _build("A")
    markdown_path, summary_path = write_source_pack(pack, tmp_path)

    assert markdown_path == tmp_path / "report-a.md"
    assert summary_path == tmp_path / "report-a.summary.json"
    assert markdown_path.read_text(encoding="utf-8") == pack.markdown
    loaded = load_source_pack_summary(summary_path)
    validate_source_pack_summary(loaded, markdown=markdown_path)
    assert not list(tmp_path.glob("*.svg"))
    assert not list(tmp_path.glob("*.pptx"))


def test_snapshot_identity_mismatch_fails_before_build() -> None:
    data = _load("report-a-data.json")
    snapshot = _snapshot("A", "coverage-set-a-001")
    data["report_snapshot_id"] = "different-snapshot"

    with pytest.raises(SourcePackBuildError, match="report_snapshot_id"):
        build_source_pack(
            "A",
            data,
            snapshot,
            _coverage("A"),
            load_page_strategy("A"),
            _design_contract(),
        )

def test_report_or_coverage_cross_binding_fails() -> None:
    data = _load("report-b-data.json")
    data["report"] = "B"
    with pytest.raises(SourcePackBuildError, match="报告类型"):
        build_source_pack(
            "A",
            data,
            _snapshot("A", "coverage-set-a-001"),
            _coverage("A"),
            load_page_strategy("A"),
            _design_contract(),
        )

    with pytest.raises(SourcePackBuildError, match="覆盖集标识"):
        build_source_pack(
            "B",
            data,
            _snapshot("B", "coverage-set-b-001"),
            _coverage("A"),
            load_page_strategy("B"),
            _design_contract(),
        )



def test_root_and_packaged_schema_are_identical_and_validate_output() -> None:
    root_schema = ROOT / "schemas" / "pptx-source-pack.schema.json"
    packaged_schema = ROOT / "src" / "ci_workflow" / "schemas" / "pptx-source-pack.schema.json"
    assert root_schema.read_text(encoding="utf-8") == packaged_schema.read_text(encoding="utf-8")
    schema = json.loads(root_schema.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    summary = _build("C").summary
    Draft202012Validator(schema).validate(summary.model_dump(mode="json"))
