"""B 类 fresh-source 研究包：类型化内容、GateSpec 评估、独立 QC 绑定与报告快照投影。

合同来源：v1.3 第 3、5、6、8 节；R2.4/R3.2 与
reviews/codex_conference_ci-rebaseline-r2-science-review-20260905_review.md
确认的 B/C research-to-gate-to-snapshot-to-independent-QC 断点。
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from ci_workflow.application.capability_preflight import StaticCapabilityProbe
from ci_workflow.application.fresh_b_research_package import (
    FreshBEvidenceLineage,
    FreshBResearchPackageError,
    compute_fresh_b_research_content_digest,
    evaluate_fresh_b_gate,
    load_fresh_b_research_package,
    project_fresh_b_report_snapshot,
)
from ci_workflow.application.fresh_research_ingestion import ingest_research_evidence
from ci_workflow.application.project_service import create_project_workspace
from ci_workflow.application.run_service import (
    MANIFEST_RELATIVE_PATH,
    ContractConfigError,
    RunContext,
)
from ci_workflow.application.run_service import (
    run_project as _run_project,
)
from ci_workflow.domain.contracts import ProjectContract, create_project_contract
from ci_workflow.gates.models import GateUnitOutcome, ReportDecision
from ci_workflow.storage.snapshot_store import EvidenceSnapshotManifest, SnapshotStore

_PROJECT_ID = "project_b0000000000000000000001"
_DATA_CUTOFF = "2026-07-31T00:00:00+08:00"
_CREATED_AT = "2026-08-18T12:00:00+08:00"
_SOURCE_ID = "source-primary-report"


def run_project(project_root: Path, **kwargs: Any) -> Any:
    """B unit scenarios declare a deterministic capable host explicitly."""
    return _run_project(
        project_root,
        capability_probe=StaticCapabilityProbe(),
        **kwargs,
    )


def _locator(field_path: str) -> dict[str, object]:
    return {
        "document_role": "主要试验报告",
        "field_path": field_path,
        "url": "https://journal.example/study-1",
    }


def _provenance(fact_id: str, *, source_location: str | None = None) -> dict[str, object]:
    payload: dict[str, object] = {
        "source_id": _SOURCE_ID,
        "source_role": "primary_trial_report",
        "disclosure_maturity": "registry_result_or_primary_report",
        "disclosure_state": "reported_value",
        "review_state": "accepted",
        "conflict_disposition": "resolved_selected_accepted_fact",
        "fact_id": fact_id,
        "fact_version_id": f"{fact_id}@1",
    }
    if source_location is not None:
        payload["source_location"] = source_location
    return payload


def _fact(row_ref: str, entity_id: str, entity_type: str, field_id: str) -> dict[str, object]:
    return {
        "fact_id": f"fact-{row_ref}",
        "row_ref": row_ref,
        "entity_id": entity_id,
        "entity_type": entity_type,
        "canonical_name": "Study-1",
        "field_id": field_id,
        "raw_value": "来源原文",
        "normalized_value": "规范化值",
        "disclosure_state": "reported_value",
        "source_id": _SOURCE_ID,
        "locator": _locator("$.facts[0].quote"),
        "original_text": f"{row_ref} 来源原文",
    }


def _baseline(kind: str, group_id: str, **extra: object) -> dict[str, object]:
    payloads: dict[str, dict[str, object]] = {
        "sample_size": {
            "row_id": f"base-{kind}-{group_id}",
            "variable_domain": "demographics",
            "data_type": "count",
            "statistic_form": "sample_size",
            "standardized_concept": "baseline_sample_size",
            "value": 96 if group_id == "grp-treat" else 99,
            "unit": "人",
            "denominator": 96 if group_id == "grp-treat" else 99,
            "raw_value": "96" if group_id == "grp-treat" else "99",
            "baseline_definition": "随机化并接受治疗的受试者人数",
        },
        "age": {
            "row_id": f"base-{kind}-{group_id}",
            "variable_domain": "demographics",
            "data_type": "continuous",
            "statistic_form": "mean",
            "standardized_concept": "baseline_age",
            "value": 38.3,
            "dispersion": 12.1,
            "unit": "岁",
            "raw_value": "38.3（SD 12.1）",
            "baseline_definition": "受试者入组时年龄均值",
        },
        "sex": {
            "row_id": f"base-{kind}-{group_id}",
            "variable_domain": "demographics",
            "data_type": "categorical",
            "statistic_form": "proportion",
            "standardized_concept": "baseline_sex",
            "value": 55.2,
            "unit": "%",
            "numerator": 53,
            "denominator": 96 if group_id == "grp-treat" else 99,
            "category_level": "男性",
            "raw_value": "55.2%",
            "baseline_definition": "男性受试者比例",
        },
        "severity": {
            "row_id": f"base-{kind}-{group_id}",
            "variable_domain": "baseline_severity",
            "data_type": "continuous",
            "statistic_form": "mean",
            "standardized_concept": "easi",
            "value": 28.4,
            "unit": "分",
            "scale": "EASI",
            "scale_version": "v1.0",
            "direction": "lower_is_better",
            "theoretical_range": "0-72",
            "raw_value": "28.4",
            "baseline_definition": "湿疹面积及严重程度指数总分",
        },
    }
    payload: dict[str, object] = {
        "source_row_id": f"study-1-table-3-{kind}",
        "observation_id": f"obs-{kind}-{group_id}",
        "product_id": "prod-1",
        "trial_id": "study-1",
        "cohort_id": "cohort-main",
        "group_id": group_id,
        "analysis_population": "FAS",
        "source_name": "基线特征表",
        "source_definition": "基线特征汇总",
        "baseline_timepoint": "基线",
        "source_version_id": _SOURCE_ID,
        "source_locator": _locator(f"tables/baseline/{kind}"),
        "source_role": "primary_trial_report",
        "disclosure_maturity": "registry_result_or_primary_report",
        "review_state": "accepted",
        "disclosure_state": "reported_value",
        "conflict_disposition": "resolved_selected_accepted_fact",
        "compatibility_rule": "baseline-compat-v1",
        **payloads[kind],
        **extra,
    }
    return payload


def _efficacy_row(group_id: str, arm_role: str, numerator: int) -> dict[str, object]:
    denominator = 96 if group_id == "grp-treat" else 99
    return {
        "row_id": f"eff-easi75-{group_id}",
        "source_row_id": f"study-1-table-12-{group_id}",
        "observation_id": "obs-easi75-w12",
        "product_id": "prod-1",
        "trial_id": "study-1",
        "endpoint_family_id": "endpoint-easi75-response-v1",
        "original_endpoint": "easi75_response",
        "original_definition": "EASI 较基线改善至少75%的受试者比例",
        "endpoint_role": "primary",
        "direction": "higher_is_better",
        "unit": "%",
        "analysis_form": "response_rate",
        "actual_timepoint": 12,
        "actual_timepoint_unit": "week",
        "analysis_population": "FAS",
        "arm_role": arm_role,
        "arm_id": group_id,
        "arm_label": "试验药物治疗组" if arm_role == "treatment" else "安慰剂对照组",
        "value": round(numerator / denominator * 100, 1),
        "numerator": numerator,
        "denominator": denominator,
        "comparison_id": "cmp-1",
        "source_version_id": _SOURCE_ID,
        "source_locator": _locator(f"tables/efficacy/{group_id}"),
    }


def _safety_row(family: str, group_id: str, arm_role: str, numerator: int) -> dict[str, object]:
    denominator = 96 if group_id == "grp-treat" else 99
    value = round(numerator / denominator * 100, 1)
    return {
        "row_id": f"saf-{family}-{group_id}",
        "source_row_id": f"study-1-table-20-{family}-{group_id}",
        "product_id": "prod-1",
        "trial_id": "study-1",
        "family": family,
        "source_term": "任何TEAE" if family == "teae" else "任何SAE",
        "event_definition_zh": ("治疗期间出现的不良事件" if family == "teae" else "严重不良事件"),
        "time_window_zh": "自首次给药至安全随访结束",
        "analysis_population_zh": "安全分析集",
        "arm_role": arm_role,
        "arm_id": group_id,
        "arm_label": "试验药物治疗组" if arm_role == "treatment" else "安慰剂对照组",
        "value": value,
        "raw_value": f"{value}%",
        "numerator": numerator,
        "denominator": denominator,
        "unit": "%",
        "disclosure_state": "reported_value",
        "source_version_id": _SOURCE_ID,
        "source_locator": _locator(f"tables/safety/{family}/{group_id}"),
    }


def _disposition_reported() -> dict[str, object]:
    return {
        "row_id": "disp-completed-study",
        "source_row_id": "study-1-figure-2",
        "observation_id": "obs-completed-study",
        "product_id": "prod-1",
        "trial_id": "study-1",
        "period_id": "treatment-period",
        "cohort_id": None,
        "group_id": None,
        "scope_level": "overall",
        "analysis_population": "随机化人群",
        "field_family": "participant_flow",
        "field": "completed_study",
        "source_field_name": "完成研究受试者",
        "source_field_definition": "完成全部访视的受试者人数",
        "measure_object": "subject",
        "statistic_form": "count",
        "value": 88,
        "raw_value": "88",
        "numerator": 88,
        "denominator": 195,
        "denominator_role": "randomized",
        "time_window": "随机化至研究结束",
        "source_version_id": _SOURCE_ID,
        "source_locator": _locator("figures/disposition"),
        "source_role": "primary_trial_report",
        "disclosure_maturity": "registry_result_or_primary_report",
        "review_state": "accepted",
        "disclosure_state": "reported_value",
        "conflict_disposition": "resolved_selected_accepted_fact",
        "compatibility_rule": "disposition-compat-v1",
    }


def _disposition_not_reported() -> dict[str, object]:
    return {
        "row_id": "disp-lost-followup",
        "source_row_id": "study-1-figure-2",
        "observation_id": "obs-lost-followup",
        "product_id": "prod-1",
        "trial_id": "study-1",
        "period_id": "treatment-period",
        "cohort_id": None,
        "group_id": None,
        "scope_level": "overall",
        "analysis_population": "随机化人群",
        "field_family": "participant_flow",
        "field": "lost_to_follow_up",
        "source_field_name": "失访受试者",
        "source_field_definition": "研究期间失访的受试者人数",
        "measure_object": "subject",
        "statistic_form": "count",
        "denominator_role": "randomized",
        "time_window": "随机化至研究结束",
        "source_version_id": _SOURCE_ID,
        "source_locator": _locator("figures/disposition"),
        "source_role": "primary_trial_report",
        "disclosure_maturity": "registry_result_or_primary_report",
        "review_state": "accepted",
        "disclosure_state": "not_reported",
        "conflict_disposition": "resolved_selected_accepted_fact",
        "compatibility_rule": "disposition-compat-v1",
        "difference_labels_zh": ["来源未单列失访人数"],
    }


def _trial_record() -> dict[str, object]:
    return {
        "trial_id": "study-1",
        "product_id": "prod-1",
        "display_name": "Study-1",
        "phase": "III期",
        "study_role": "pivotal",
        "design_kind": "comparative",
        "target_population_zh": "成人中重度特应性皮炎受试者",
        "group_ids": ["grp-treat", "grp-control"],
        "groups": [
            {
                "group_id": "grp-treat",
                "trial_id": "study-1",
                "label_zh": "试验药物治疗组",
                "arm_role": "treatment",
            },
            {
                "group_id": "grp-control",
                "trial_id": "study-1",
                "label_zh": "安慰剂对照组",
                "arm_role": "control",
            },
        ],
        "endpoints": [
            {
                "endpoint_id": "endpoint-easi75-response-v1",
                "trial_id": "study-1",
                "endpoint_role": "primary",
                "label": "EASI-75 应答率",
                "definition": "EASI 较基线改善至少75%的受试者比例",
            }
        ],
        "comparison": {
            "comparison_id": "cmp-1",
            "trial_id": "study-1",
            "treatment_group_id": "grp-treat",
            "control_group_id": "grp-control",
            "treatment_group_label_zh": "试验药物治疗组",
            "control_group_label_zh": "安慰剂对照组",
            "endpoint_ids": ["endpoint-easi75-response-v1"],
            "provenance": _provenance(
                "trial:study-1:comparison", source_location="主要报告 第2.1节"
            ),
        },
        "effect_differences": [
            {
                "difference_id": "diff-easi75-w12",
                "trial_id": "study-1",
                "comparison_id": "cmp-1",
                "endpoint_id": "endpoint-easi75-response-v1",
                "definition": "两组 EASI-75 应答率差值",
                "direction": "higher_is_better",
                "unit": "百分点",
                "value": 32.2,
                "source_location": "主要报告 表25",
                "provenance": _provenance(
                    "trial:study-1:effect-difference", source_location="主要报告 表25"
                ),
            }
        ],
        "identity_provenance": _provenance(
            "trial:study-1:identity", source_location="主要报告 第1章"
        ),
        "population_provenance": _provenance(
            "trial:study-1:population", source_location="主要报告 第3.1节"
        ),
        "result_source_provenance": _provenance(
            "trial:study-1:result-source", source_location="主要报告 结果部分"
        ),
    }


def _package_payload(project_id: str = _PROJECT_ID) -> dict[str, object]:
    groups = ("grp-treat", "grp-control")
    baseline = [
        _baseline(kind, group_id)
        for kind in ("sample_size", "age", "sex", "severity")
        for group_id in groups
    ]
    efficacy = [
        _efficacy_row("grp-treat", "treatment", 60),
        _efficacy_row("grp-control", "control", 30),
    ]
    safety = [
        _safety_row("teae", "grp-treat", "treatment", 65),
        _safety_row("teae", "grp-control", "control", 60),
        _safety_row("sae", "grp-treat", "treatment", 4),
        _safety_row("sae", "grp-control", "control", 3),
    ]
    disposition = [_disposition_reported(), _disposition_not_reported()]
    trial = _trial_record()

    def fact_ref(row: dict[str, object]) -> str:
        row_id = str(row["row_id"])
        if row_id.startswith(("eff-", "saf-")):
            return row_id
        return str(row["observation_id"])

    facts = [
        _fact(ref, "study-1" if ref.startswith("trial:") else "prod-1", "trial", "trial.record")
        for ref in (
            "trial:study-1:identity",
            "trial:study-1:population",
            "trial:study-1:result-source",
            "trial:study-1:comparison",
            "trial:study-1:effect-difference",
        )
    ]
    facts.extend(
        _fact(fact_ref(row), "study-1", "trial", "b.observation")  # type: ignore[arg-type]
        for row in (*baseline, *efficacy, *safety, *disposition)
    )
    # W01 trust contract: the claimed original quote is replayable from the
    # persisted JSON bytes at one exact wildcard-free path.
    for index, item in enumerate(facts):
        item["locator"] = _locator(f"$.facts[{index}].quote")
    source_document = {
        "facts": [
            {"row_ref": item["row_ref"], "quote": item["original_text"]}
            for item in facts
        ]
    }
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "report_kind": "B",
        "project_id": project_id,
        "indication": "特应性皮炎",
        "data_cutoff": _DATA_CUTOFF,
        "report_version": "v1",
        "producer_id": "host-agent-builder",
        "universe_closed": True,
        "universe_product_ids": ["prod-1"],
        "research_role_set_id": "research-roles-core-v1",
        "indication_rule_set_id": "indication-rules-atopic-v1",
        "severity_anchor_concepts": ["easi"],
        "trials": [trial],
        "baseline": baseline,
        "efficacy": efficacy,
        "safety": safety,
        "disposition": disposition,
        "efficacy_review": [
            {
                "row_id": row["row_id"],
                "review_state": "accepted",
                "disclosure_maturity": "attributable_numeric_disclosure",
                "source_role": "primary_trial_report",
                "conflict_disposition": "resolved_selected_accepted_fact",
            }
            for row in efficacy
        ],
        "safety_review": [
            {
                "row_id": row["row_id"],
                "review_state": "accepted",
                "disclosure_maturity": "attributable_numeric_disclosure",
                "source_role": "primary_trial_report",
                "conflict_disposition": "resolved_selected_accepted_fact",
            }
            for row in safety
        ],
        "sources": [
            {
                "source_id": _SOURCE_ID,
                "route_id": "primary-trial-report-route",
                "source_type": "primary_trial_report",
                "title": "Study-1 主要研究报告",
                "url": "https://journal.example/study-1",
                "query_or_identifier": "Study-1 主要研究报告",
                "language": "zh",
                "access_method": "official_page",
                "content_text": json.dumps(source_document, ensure_ascii=False),
                "acquired_at": _CREATED_AT,
                "published_at": "2026-05-01T00:00:00+00:00",
                "effective_at": None,
                "first_disclosed_at": "2026-05-01T00:00:00+00:00",
                "locator": _locator("$.facts"),
            }
        ],
        "facts": facts,
        "claims": [
            {
                "claim_id": "claim-b-core",
                "claim_text": "B 类核心比较事实均可回到已存主要研究报告。",
                "claim_kind": "direct_evidence",
                "fact_ids": [item["fact_id"] for item in facts],
            }
        ],
        "report_data": {
            "schema_version": "1.0",
            "report_version": "v1",
            "indication": "特应性皮炎",
            "data_cutoff": _DATA_CUTOFF,
            "products": [
                {
                    "id": "prod-1",
                    "name": "示例药物",
                    "target": "IL-4Rα",
                    "modality": "单克隆抗体",
                    "phase": "III期",
                    "status": "开展中",
                    "regions": ["全球"],
                    "route": "皮下注射",
                    "developer": "示例企业",
                    "mechanism": "阻断 IL-4/IL-13 信号",
                    "result_status": "已有部分公开结果",
                }
            ],
            "trials": [
                {
                    "id": "study-1",
                    "display_id": "Study-1",
                    "product_id": "prod-1",
                    "name": "Study-1",
                    "phase": "III期",
                    "region": "全球",
                    "status": "已完成",
                    "sample_size": 195,
                    "treatment_sample_size": 96,
                    "role": "核心试验",
                }
            ],
            "efficacy": [
                {
                    "row_id": row["row_id"],
                    "product_id": row["product_id"],
                    "trial_id": row["trial_id"],
                    "endpoint": row["original_endpoint"],
                "timepoint": f"第{row['actual_timepoint']}周",
                "arm": row["arm_label"],
                "value": row["value"],
                "numerator": row["numerator"],
                "denominator": row["denominator"],
                "unit": row["unit"],
                    "population": row["analysis_population"],
                }
                for row in efficacy
            ],
            "safety": [
                {
                    "row_id": row["row_id"],
                    "product_id": row["product_id"],
                    "trial_id": row["trial_id"],
                    "arm": row["arm_label"],
                    "category": "治疗期间不良事件" if row["family"] == "teae" else "严重不良事件",
                    "term": row["source_term"],
                    "value": row["value"],
                    "numerator": row["numerator"],
                    "denominator": row["denominator"],
                    "unit": row["unit"],
                    "time_window": row["time_window_zh"],
                    "disclosure_state": "已公开",
                }
                for row in safety
            ],
            "regulatory": [
                {
                    "product_id": "prod-1",
                    "track": "全球",
                    "event": "临床开发",
                    "date": "2026-05-01",
                    "status": "开展中",
                }
            ],
            "companies": [
                {
                    "product_id": "prod-1",
                    "relationship": "研发",
                    "licensor": "示例企业",
                    "licensee": "示例企业",
                    "territory": "全球",
                    "transaction": "自主研发",
                }
            ],
            "patents": [
                {
                    "product_id": "prod-1",
                    "family": "未公开",
                    "display_family": "未公开",
                    "jurisdiction": "全球",
                    "scope": "未公开",
                    "expiry": "未公开",
                    "exclusivity": "未公开",
                }
            ],
            "history": [
                {
                    "product_id": "prod-1",
                    "status": "开展中",
                    "date": "2026-05-01",
                    "observation": "主要结果已披露",
                }
            ],
            "sources": [
                {
                    "source": "Study-1 主要研究报告",
                    "scope": "疗效与安全性",
                    "maturity": "主要报告",
                    "limitation": "测试数据",
                }
            ],
            "baseline_views": {"facts": baseline},
            "disposition_views": {"facts": disposition},
            "efficacy_views": {"facts": efficacy},
            "safety_views": {"facts": safety},
        },
    }
    return payload


def _with_review(payload: dict[str, object], **overrides: object) -> dict[str, object]:
    review: dict[str, object] = {
        "reviewer_id": "reviewer-independent-1",
        "reviewer_role": "independent_scientific_verifier",
        "status": "accepted",
        "reviewed_at": "2026-08-18T15:00:00+08:00",
        "reviewed_content_digest": compute_fresh_b_research_content_digest(payload),
        "observations": ["已核对 B 类核心比较事实与来源绑定"],
    }
    review.update(overrides)
    payload["scientific_review"] = review
    return payload


def _sync_portal_facts(payload: dict[str, object]) -> None:
    report_data = payload["report_data"]
    assert isinstance(report_data, dict)
    for name in ("baseline", "efficacy", "safety", "disposition"):
        view = report_data[f"{name}_views"]
        assert isinstance(view, dict)
        view["facts"] = payload[name]
    report_data["efficacy"] = [
        row
        for row in report_data["efficacy"]  # type: ignore[index]
        if any(item["row_id"] == row["row_id"] for item in payload["efficacy"])  # type: ignore[index]
    ]
    report_data["safety"] = [
        row
        for row in report_data["safety"]  # type: ignore[index]
        if any(item["row_id"] == row["row_id"] for item in payload["safety"])  # type: ignore[index]
    ]


def _write_package(tmp_path: Path, payload: dict[str, object]) -> Path:
    path = tmp_path / "b-research-package.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def _load(tmp_path: Path, payload: dict[str, object]) -> Any:
    return load_fresh_b_research_package(_write_package(tmp_path, payload))


def _project(tmp_path: Path) -> tuple[Path, ProjectContract]:
    contract = create_project_contract(
        indication="特应性皮炎",
        reports=["B"],
        outputs=["html"],
        cutoff="2026-07-31",
    )
    return create_project_workspace(tmp_path / "项目", contract), contract


def _lineage(
    project_root: Path, digest: str, project_id: str = _PROJECT_ID
) -> FreshBEvidenceLineage:
    manifest = EvidenceSnapshotManifest(
        schema_version="1.0",
        project_id=project_id,
        contract_version=1,
        data_cutoff=datetime.fromisoformat(_DATA_CUTOFF),
        source_version_ids=("srcver-primary-report",),
        fragment_ids=("frag-primary-report",),
        fact_version_ids=("fact-version-1",),
        scientific_content_digest=digest,
        created_at=datetime.fromisoformat(_CREATED_AT),
    )
    locked = SnapshotStore(project_root).lock_evidence_snapshot(manifest.model_dump(mode="json"))
    return FreshBEvidenceLineage(
        evidence_snapshot=locked,
        source_version_ids=("srcver-primary-report",),
        fragment_ids=("frag-primary-report",),
        fact_version_ids=("fact-version-1",),
    )


def test_package_binds_content_digest_and_independent_review(tmp_path: Path) -> None:
    package = _load(tmp_path, _with_review(_package_payload()))
    assert package.report_kind == "B"
    assert package.research_content_digest == (
        compute_fresh_b_research_content_digest(_package_payload())
    )
    assert package.scientific_review.status == "accepted"


def test_rejects_portal_projection_that_changes_a_clinical_value(tmp_path: Path) -> None:
    payload = _package_payload()
    report_data = payload["report_data"]
    assert isinstance(report_data, dict)
    efficacy = report_data["efficacy"]
    assert isinstance(efficacy, list)
    efficacy[0]["value"] = 99.9
    with pytest.raises(FreshBResearchPackageError, match="门户疗效投影"):
        _load(tmp_path, _with_review(payload))


def test_rejects_portal_efficacy_numerator_without_typed_scientific_fact(
    tmp_path: Path,
) -> None:
    payload = _package_payload()
    report_data = payload["report_data"]
    assert isinstance(report_data, dict)
    efficacy = report_data["efficacy"]
    assert isinstance(efficacy, list)
    efficacy[0]["numerator"] = 95
    efficacy[0]["denominator"] = 96
    with pytest.raises(FreshBResearchPackageError, match="门户疗效投影"):
        _load(tmp_path, _with_review(payload))


def test_gate_covers_baseline_efficacy_safety_and_disposition_units(tmp_path: Path) -> None:
    package = _load(tmp_path, _with_review(_package_payload()))
    result = evaluate_fresh_b_gate(package, evidence_snapshot_id="snap-test", contract_version="1")
    assert result.decision == "passed"
    applicable = set(result.applicable_unit_ids)
    assert {
        "b_trial_identity_role",
        "b_target_population_groups",
        "b_treatment_control_identity",
        "b_baseline_sample_size",
        "b_baseline_age",
        "b_baseline_sex",
        "b_baseline_severity_anchor",
        "b_core_efficacy_endpoint",
        "b_effect_difference_support",
        "b_safety_minimum_record",
        "b_source_role_maturity_location",
    } <= applicable
    disposition_results = [
        item for item in result.unit_results if item.unit_id == "b_trial_disposition"
    ]
    assert disposition_results
    assert all(item.outcome is not GateUnitOutcome.BLOCKED for item in disposition_results)


def test_rejects_rejected_independent_review(tmp_path: Path) -> None:
    with pytest.raises(FreshBResearchPackageError, match="独立科学复核"):
        _load(tmp_path, _with_review(_package_payload(), status="rejected"))


def test_rejects_digest_mismatched_independent_review(tmp_path: Path) -> None:
    payload = _with_review(_package_payload())
    payload["producer_id"] = "different-producer"
    with pytest.raises(FreshBResearchPackageError, match="摘要"):
        _load(tmp_path, payload)


def test_rejects_review_from_producer_identity(tmp_path: Path) -> None:
    with pytest.raises(FreshBResearchPackageError, match="生产者"):
        _load(
            tmp_path,
            _with_review(_package_payload(), reviewer_id="host-agent-builder"),
        )


def test_rejects_review_that_predates_captured_sources(tmp_path: Path) -> None:
    payload = _package_payload()
    with pytest.raises(
        FreshBResearchPackageError, match="不得早于研究包来源获取时间"
    ):
        _load(
            tmp_path,
            _with_review(payload, reviewed_at="2026-08-18T11:59:59+08:00"),
        )


def test_rejects_source_disclosed_after_cutoff(tmp_path: Path) -> None:
    payload = _package_payload()
    payload["sources"][0]["first_disclosed_at"] = "2026-08-01T00:00:00+00:00"  # type: ignore[index]
    with pytest.raises(FreshBResearchPackageError, match="截止"):
        _load(tmp_path, _with_review(payload))


def test_missing_critical_baseline_anchor_remains_a_gate_block(tmp_path: Path) -> None:
    payload = _package_payload()
    payload["baseline"] = [  # type: ignore[index]
        row
        for row in payload["baseline"]  # type: ignore[index]
        if not (row["standardized_concept"] == "easi" and row["group_id"] == "grp-control")  # type: ignore[index]
    ]
    payload["facts"] = [  # type: ignore[index]
        fact
        for fact in payload["facts"]  # type: ignore[index]
        if fact["row_ref"] != "obs-severity-grp-control"  # type: ignore[index]
    ]
    payload["claims"][0]["fact_ids"] = [  # type: ignore[index]
        item["fact_id"]
        for item in payload["facts"]  # type: ignore[index]
    ]
    payload.pop("report_data")
    package = _load(tmp_path, _with_review(payload))
    result = evaluate_fresh_b_gate(
        package, evidence_snapshot_id="snap-blocked", contract_version="1"
    )
    assert result.decision is ReportDecision.BLOCKED
    assert "b_baseline_severity_anchor" in result.blocked_unit_ids


def test_missing_safety_minimum_record_remains_a_gate_block(tmp_path: Path) -> None:
    payload = _package_payload()
    payload["safety"] = []  # type: ignore[index]
    payload["safety_review"] = []  # type: ignore[index]
    payload["facts"] = [  # type: ignore[index]
        fact
        for fact in payload["facts"]  # type: ignore[index]
        if not str(fact["row_ref"]).startswith("saf-")  # type: ignore[index]
    ]
    payload["claims"][0]["fact_ids"] = [  # type: ignore[index]
        item["fact_id"]
        for item in payload["facts"]  # type: ignore[index]
    ]
    payload.pop("report_data")
    package = _load(tmp_path, _with_review(payload))
    result = evaluate_fresh_b_gate(
        package, evidence_snapshot_id="snap-blocked", contract_version="1"
    )
    assert result.decision is ReportDecision.BLOCKED
    assert "b_safety_minimum_record" in result.blocked_unit_ids


def test_missing_disposition_keeps_extension_state_without_blocking(tmp_path: Path) -> None:
    payload = _package_payload()
    payload["disposition"] = []  # type: ignore[index]
    payload["facts"] = [  # type: ignore[index]
        fact
        for fact in payload["facts"]  # type: ignore[index]
        if not str(fact["row_ref"]).startswith(  # type: ignore[index]
            ("obs-completed-study", "obs-lost-followup")
        )
    ]
    payload["claims"][0]["fact_ids"] = [  # type: ignore[index]
        item["fact_id"]
        for item in payload["facts"]  # type: ignore[index]
    ]
    _sync_portal_facts(payload)
    package = _load(tmp_path, _with_review(payload))
    result = evaluate_fresh_b_gate(package, evidence_snapshot_id="snap-test", contract_version="1")
    assert result.decision == "passed"
    disposition = [item for item in result.unit_results if item.unit_id == "b_trial_disposition"]
    assert {item.outcome for item in disposition} == {GateUnitOutcome.EXTENSION_MISSING}


def test_report_kind_mismatch_is_rejected(tmp_path: Path) -> None:
    payload = _package_payload()
    payload["report_kind"] = "C"  # type: ignore[index]
    with pytest.raises(FreshBResearchPackageError):
        _load(tmp_path, _with_review(payload))


def test_fails_closed_on_unbound_observation_fact(tmp_path: Path) -> None:
    payload = _package_payload()
    payload["facts"] = [  # type: ignore[index]
        fact
        for fact in payload["facts"]  # type: ignore[index]
        if fact["row_ref"] != "eff-easi75-grp-control"  # type: ignore[index]
    ]
    payload["claims"][0]["fact_ids"] = [  # type: ignore[index]
        item["fact_id"]
        for item in payload["facts"]  # type: ignore[index]
    ]
    _sync_portal_facts(payload)
    with pytest.raises(FreshBResearchPackageError, match="来源绑定"):
        _load(tmp_path, _with_review(payload))


def test_single_arm_core_trial_keeps_results_without_inventing_control(tmp_path: Path) -> None:
    payload = _package_payload()
    trial = payload["trials"][0]  # type: ignore[index]
    trial["design_kind"] = "single_arm"  # type: ignore[index]
    trial["comparison"] = None  # type: ignore[index]
    trial["effect_differences"] = []  # type: ignore[index]
    trial["group_ids"] = ["grp-treat"]  # type: ignore[index]
    trial["groups"] = [  # type: ignore[index]
        group
        for group in trial["groups"]
        if group["group_id"] == "grp-treat"  # type: ignore[index]
    ]
    payload["baseline"] = [  # type: ignore[index]
        row
        for row in payload["baseline"]
        if row["group_id"] == "grp-treat"  # type: ignore[index]
    ]
    payload["efficacy"] = payload["efficacy"][:1]  # type: ignore[index]
    payload["efficacy_review"] = payload["efficacy_review"][:1]  # type: ignore[index]
    payload["safety"] = payload["safety"][:1] + payload["safety"][2:3]  # type: ignore[index]
    payload["safety_review"] = payload["safety_review"][:1] + payload["safety_review"][2:3]  # type: ignore[index]

    def fact_ref(row: dict[str, object]) -> str:
        row_id = str(row["row_id"])
        return row_id if row_id.startswith(("eff-", "saf-")) else str(row["observation_id"])

    kept_refs = {
        fact_ref(row)  # type: ignore[arg-type]
        for row in (
            *payload["baseline"],  # type: ignore[operator]
            *payload["efficacy"],  # type: ignore[operator]
            *payload["safety"],  # type: ignore[operator]
            *payload["disposition"],  # type: ignore[operator]
        )
    } | {
        "trial:study-1:identity",
        "trial:study-1:population",
        "trial:study-1:result-source",
    }
    payload["facts"] = [  # type: ignore[index]
        fact
        for fact in payload["facts"]
        if fact["row_ref"] in kept_refs  # type: ignore[index]
    ]
    payload["claims"][0]["fact_ids"] = [  # type: ignore[index]
        item["fact_id"]
        for item in payload["facts"]  # type: ignore[index]
    ]
    _sync_portal_facts(payload)
    package = _load(tmp_path, _with_review(payload))
    result = evaluate_fresh_b_gate(
        package, evidence_snapshot_id="snap-single-arm", contract_version="1"
    )
    assert result.decision is ReportDecision.PASSED
    assert not any(
        item.unit_id == "b_treatment_control_identity" and item.blocking
        for item in result.unit_results
    )


def test_projection_locks_b_report_snapshot_bound_to_lineage(tmp_path: Path) -> None:
    project_root, contract = _project(tmp_path)
    package = _load(tmp_path, _with_review(_package_payload(contract.project_id)))
    lineage = _lineage(project_root, package.research_content_digest, contract.project_id)
    created_at = datetime.fromisoformat(_CREATED_AT)

    projection = project_fresh_b_report_snapshot(
        package,
        project_root=project_root,
        project_id=contract.project_id,
        contract_version=1,
        lineage=lineage,
        created_at=created_at,
    )

    snapshot_path = project_root / projection.report_snapshot.relative_path
    assert snapshot_path.is_file()
    assert projection.evidence_snapshot_id == lineage.evidence_snapshot.snapshot_id
    assert projection.gate_result.decision == "passed"
    assert projection.manifest.report_version == "v1"
    with sqlite3.connect(project_root / "state/project.sqlite") as database:
        gate_row = database.execute(
            "SELECT report_kind, result FROM gate_evaluations WHERE report_kind = 'B'"
        ).fetchone()
        # 覆盖集合行引用渲染产物快照，渲染前的投影不得预写。
        coverage_row = database.execute(
            "SELECT report_kind FROM coverage_sets WHERE report_kind = 'B'"
        ).fetchone()
    assert gate_row == ("B", "passed")
    assert coverage_row is None

    again = project_fresh_b_report_snapshot(
        package,
        project_root=project_root,
        project_id=contract.project_id,
        contract_version=1,
        lineage=lineage,
        created_at=created_at,
    )
    assert again.report_snapshot.snapshot_id == projection.report_snapshot.snapshot_id
    assert again.claim_snapshot_id == projection.claim_snapshot_id
    assert again.coverage_set_id == projection.coverage_set_id


def test_shared_ingestion_is_idempotent_and_never_persists_a_gate_claim(
    tmp_path: Path,
) -> None:
    project_root, contract = _project(tmp_path)
    package = _load(tmp_path, _with_review(_package_payload(contract.project_id)))
    kwargs = {
        "project_root": project_root,
        "project_id": contract.project_id,
        "contract_version": 1,
        "report_kind": "B",
        "data_cutoff": package.data_cutoff,
        "scientific_content_digest": package.research_content_digest,
        "created_at": package.scientific_review.reviewed_at,
        "sources": package.sources,
        "route_attempts": package.route_attempts,
        "facts": package.facts,
        "claims": package.claims,
    }
    first = ingest_research_evidence(**kwargs)
    second = ingest_research_evidence(**kwargs)
    assert second.evidence_snapshot.snapshot_id == first.evidence_snapshot.snapshot_id
    assert second.fact_version_ids == first.fact_version_ids
    with sqlite3.connect(project_root / "state/project.sqlite") as database:
        assert database.execute("SELECT count(*) FROM gate_evaluations").fetchone() == (0,)


def test_run_service_executes_b_research_lineage_before_render(tmp_path: Path) -> None:
    project_root, contract = _project(tmp_path)
    package_path = _write_package(
        tmp_path, _with_review(_package_payload(contract.project_id))
    )
    result = run_project(
        project_root,
        run_context=RunContext(
            project_root=project_root,
            contract=contract,
            research_package_path=package_path,
        ),
    )
    assert result.outcome == "completed"
    assert {
        "ingest",
        "gate:B",
        "snapshot:B",
        "analyze:B",
        "format:B",
    } <= result.node_summary.keys()
    manifest = json.loads(
        (project_root / "reports/B/v1/html.manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["evidence_snapshot_id"].startswith("evidence-snapshot_")
    assert manifest["report_snapshot_id"].startswith("report-snapshot_")


def test_run_service_discovers_canonical_b_package(tmp_path: Path) -> None:
    project_root, contract = _project(tmp_path)
    package_path = project_root / "evidence/library/b-research-package.json"
    package_path.parent.mkdir(parents=True, exist_ok=True)
    package_path.write_text(
        json.dumps(
            _with_review(_package_payload(contract.project_id)), ensure_ascii=False
        ),
        encoding="utf-8",
    )
    result = run_project(project_root)
    assert result.outcome == "completed"
    assert result.input_hashes["evidence/library/b-research-package.json"]


def _write_verified_scientific_review(
    project_root: Path, context_payload: dict[str, Any]
) -> None:
    from ci_workflow.application.review_issuer import (
        ExternalProcessResult,
        issue_review_receipt,
    )
    from ci_workflow.hosts.receipt import (
        HostExecutableEvidence,
        HostSessionBinding,
    )
    from ci_workflow.qc.scientific import (
        ScientificQcCurrentContext,
        ScientificQcReviewBundle,
        ScientificQcVerdict,
    )

    context = ScientificQcCurrentContext.model_validate(
        {key: value for key, value in context_payload.items() if key != "context_digest"}
    )
    report_kind = context.report_kind.value
    bundle = ScientificQcReviewBundle(
        producer_id=context.producer_id,
        project_id=context.project_id,
        report_kind=context.report_kind,
        report_version=context.report_version,
        report_object_id=context.report_object_id,
        candidate_snapshot_id=context.candidate_snapshot_id,
        candidate_content_digest=context.candidate_content_digest,
        criteria_version=context.criteria_version,
        gate_result_key=context.gate_result_key,
        coverage_set_id=context.coverage_set_id,
        coverage_digest=context.coverage_digest,
        source_refs=context.source_refs,
        locators=context.locators,
    )
    request = json.loads(
        (
            project_root
            / f"state/scientific_review/{report_kind}/review_request.json"
        ).read_text(
            encoding="utf-8"
        )
    )
    produced_at = datetime.fromisoformat(request["production"]["produced_at"])
    started_at = produced_at + timedelta(microseconds=1)
    finished_at = produced_at + timedelta(microseconds=2)
    issued_at = produced_at + timedelta(microseconds=3)
    verdict = ScientificQcVerdict(
        criteria_version=context.criteria_version,
        verdict_id="verdict-b-independent",
        verdict="accepted",
        project_id=context.project_id,
        contract_version=context.contract_version,
        report_kind=context.report_kind,
        report_version=context.report_version,
        report_object_id=context.report_object_id,
        candidate_snapshot_id=context.candidate_snapshot_id,
        candidate_content_digest=context.candidate_content_digest,
        gate_result_key=context.gate_result_key,
        coverage_set_id=context.coverage_set_id,
        coverage_digest=context.coverage_digest,
        source_refs=context.source_refs,
        locators=context.locators,
        reviewer_id="independent-reviewer",
        review_input_digest=bundle.input_digest,
        reviewed_at=finished_at,
        valid_until=issued_at + timedelta(days=7),
    )
    artifact_relative = f"receipts/scientific_review/{report_kind}/verdict.json"
    artifact_path = project_root / artifact_relative
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(
        json.dumps(verdict.model_dump(mode="json"), ensure_ascii=False),
        encoding="utf-8",
    )
    executable = "/opt/homebrew/bin/codex"
    executable = "/opt/homebrew/bin/codex"
    issue_review_receipt(
        project_root=project_root,
        report_kind=report_kind,
        reviewer_id="independent-reviewer",
        review_session_id="independent-session",
        host="codex",
        host_executable=HostExecutableEvidence(
            provenance="path_resolved",
            path=executable,
            resolved_realpath=executable,
            version="codex-cli-test",
        ),
        review_argv=("exec", "scientific-review"),
        verdict_relative_path=artifact_relative,
        session=HostSessionBinding(
            session_id="independent-session", launcher_pid=701, launcher_parent_pid=1
        ),
        runner=lambda argv, cwd, _timeout: ExternalProcessResult(
            pid=702,
            argv=argv,
            cwd=cwd,
            started_at=started_at,
            finished_at=finished_at,
            returncode=0,
        ),
        clock=lambda: issued_at,
    )


def test_b_candidate_requires_valid_verdict_artifact_before_promotion(
    tmp_path: Path,
) -> None:
    project_root, contract = _project(tmp_path)
    package_path = _write_package(
        tmp_path, _with_review(_package_payload(contract.project_id))
    )
    context = RunContext(
        project_root=project_root,
        contract=contract,
        research_package_path=package_path,
    )
    assert run_project(project_root, run_context=context).outcome == "completed"
    run_manifest = json.loads(
        (project_root / MANIFEST_RELATIVE_PATH).read_text(encoding="utf-8")
    )
    assert run_manifest["report_states"] == {"B": "rendered_unreviewed"}
    _write_verified_scientific_review(
        project_root, run_manifest["scientific_review_contexts"]["B"]
    )
    assert run_project(project_root, resume=True, run_context=context).outcome == "completed"
    resumed = json.loads(
        (project_root / MANIFEST_RELATIVE_PATH).read_text(encoding="utf-8")
    )
    assert resumed["report_states"] == {
        "B": "scientifically_reviewed_rendered_candidate"
    }


def _b_run(tmp_path: Path) -> tuple[Path, Any, RunContext]:
    project_root, contract = _project(tmp_path)
    package_path = _write_package(
        tmp_path, _with_review(_package_payload(contract.project_id))
    )
    context = RunContext(
        project_root=project_root,
        contract=contract,
        research_package_path=package_path,
    )
    return project_root, contract, context


def _b_run_manifest(project_root: Path) -> dict[str, Any]:
    return json.loads(  # type: ignore[no-any-return]
        (project_root / MANIFEST_RELATIVE_PATH).read_text(encoding="utf-8")
    )


def _b_site_index(project_root: Path) -> Path:
    version_root = next(
        (project_root / "reports/B").glob("*/html/*.html"), None
    )
    assert version_root is not None
    return version_root


def test_b_resume_without_receipt_is_controlled_and_byte_verified(
    tmp_path: Path,
) -> None:
    """等待回执期间允许多次受控 resume；站点字节漂移必须失败关闭。"""
    project_root, _contract, context = _b_run(tmp_path)
    assert run_project(project_root, run_context=context).outcome == "completed"
    assert _b_run_manifest(project_root)["report_states"] == {"B": "rendered_unreviewed"}
    request_before = (
        project_root / "state/scientific_review/B/review_request.json"
    ).read_bytes()

    # 多次等待回执的 resume：状态不晋级，请求保持首次绑定
    for _ in range(2):
        assert (
            run_project(project_root, resume=True, run_context=context).outcome
            == "completed"
        )
        assert _b_run_manifest(project_root)["report_states"] == {
            "B": "rendered_unreviewed"
        }
    assert (
        project_root / "state/scientific_review/B/review_request.json"
    ).read_bytes() == request_before

    # 恢复时重验字节：站点被篡改后 resume 失败关闭
    index = _b_site_index(project_root)
    original = index.read_bytes()
    index.write_bytes(original + b"<!-- tampered -->")
    with pytest.raises(ContractConfigError, match="门户"):
        run_project(project_root, resume=True, run_context=context)
    index.write_bytes(original)
    assert (
        run_project(project_root, resume=True, run_context=context).outcome
        == "completed"
    )


def test_b_promotion_runs_after_format_and_is_idempotent(tmp_path: Path) -> None:
    """回执晋级发生在 format 完成之后，且晋级后重复 resume 幂等。"""
    project_root, _contract, context = _b_run(tmp_path)
    assert run_project(project_root, run_context=context).outcome == "completed"
    _write_verified_scientific_review(
        project_root, _b_run_manifest(project_root)["scientific_review_contexts"]["B"]
    )
    assert (
        run_project(project_root, resume=True, run_context=context).outcome
        == "completed"
    )
    assert _b_run_manifest(project_root)["report_states"] == {
        "B": "scientifically_reviewed_rendered_candidate"
    }
    from ci_workflow.storage.event_store import EventStore

    order: list[tuple[str, str]] = []
    for event in EventStore(project_root).read_all():
        if event.event_type == "graph.node.completed":
            order.append(
                (str(event.payload["node_id"]), str(event.payload.get("report_kind")))
            )
    assert order.index(("format", "B")) < order.index(("scientific_qc", "B"))

    # 晋级后再次 resume：幂等，状态保持已晋级
    assert (
        run_project(project_root, resume=True, run_context=context).outcome
        == "completed"
    )
    assert _b_run_manifest(project_root)["report_states"] == {
        "B": "scientifically_reviewed_rendered_candidate"
    }
    from ci_workflow.application.real_source_acceptance import _assert_fresh_run

    current = _b_run_manifest(project_root)
    started_at, _finished_at, artifact_run_id = _assert_fresh_run(
        project_root,
        current,
        project_id=current["project_id"],
        run_id=current["run_id"],
    )
    assert started_at.tzinfo is not None
    assert artifact_run_id != current["run_id"]


def test_b_promoted_candidate_never_regresses_without_receipt(
    tmp_path: Path,
) -> None:
    """已晋级候选的回执缺失时 resume 不得静默回退到未复核状态。"""
    project_root, _contract, context = _b_run(tmp_path)
    assert run_project(project_root, run_context=context).outcome == "completed"
    _write_verified_scientific_review(
        project_root, _b_run_manifest(project_root)["scientific_review_contexts"]["B"]
    )
    assert (
        run_project(project_root, resume=True, run_context=context).outcome
        == "completed"
    )
    (project_root / "receipts/scientific_review/B/receipt.json").unlink()
    with pytest.raises(ContractConfigError, match="回执"):
        run_project(project_root, resume=True, run_context=context)
    assert _b_run_manifest(project_root)["report_states"] == {
        "B": "scientifically_reviewed_rendered_candidate"
    }


def test_run_service_persists_recovery_state_for_blocked_b_evidence(
    tmp_path: Path,
) -> None:
    project_root, contract = _project(tmp_path)
    payload = _package_payload(contract.project_id)
    payload["safety"] = []
    payload["safety_review"] = []
    payload["facts"] = [
        fact
        for fact in payload["facts"]  # type: ignore[union-attr]
        if not str(fact["row_ref"]).startswith("saf-")
    ]
    payload["claims"][0]["fact_ids"] = [  # type: ignore[index]
        item["fact_id"] for item in payload["facts"]  # type: ignore[index]
    ]
    payload.pop("report_data")
    package_path = _write_package(tmp_path, _with_review(payload))
    result = run_project(
        project_root,
        run_context=RunContext(
            project_root=project_root,
            contract=contract,
            research_package_path=package_path,
        ),
    )
    assert result.outcome == "running"
    assert result.node_summary["gate:B"] == "completed"
    assert result.node_summary["recovery:B"] == "awaiting_recovery"
    recovery = json.loads(
        (project_root / "state/work-items/b-evidence-recovery.json").read_text(
            encoding="utf-8"
        )
    )
    assert "b_safety_minimum_record" in recovery["blocked_unit_ids"]
    assert (project_root / "manifests/current_run.json").is_file()
    assert not (project_root / "reports/B/v1/html").exists()


def test_run_service_rejects_report_kind_mismatch(tmp_path: Path) -> None:
    contract = create_project_contract(
        indication="特应性皮炎", reports=["C"], outputs=["html"]
    )
    project_root = create_project_workspace(tmp_path / "项目", contract)
    package_path = _write_package(
        tmp_path, _with_review(_package_payload(contract.project_id))
    )
    with pytest.raises(ContractConfigError, match="C 类新鲜来源研究包"):
        run_project(
            project_root,
            run_context=RunContext(
                project_root=project_root,
                contract=contract,
                research_package_path=package_path,
            ),
        )


def test_projection_rejects_lineage_digest_mismatch(tmp_path: Path) -> None:
    project_root, contract = _project(tmp_path)
    package = _load(tmp_path, _with_review(_package_payload(contract.project_id)))
    lineage = _lineage(project_root, "0" * 64, contract.project_id)
    with pytest.raises(FreshBResearchPackageError, match="证据快照"):
        project_fresh_b_report_snapshot(
            package,
            project_root=project_root,
            project_id=contract.project_id,
            contract_version=1,
            lineage=lineage,
            created_at=datetime.fromisoformat(_CREATED_AT),
        )


def test_load_rejects_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "broken.json"
    path.write_text("{not-json", encoding="utf-8")
    with pytest.raises(FreshBResearchPackageError, match="研究包"):
        load_fresh_b_research_package(path)


def test_validation_error_wrapped_as_package_error(tmp_path: Path) -> None:
    payload = _package_payload()
    del payload["trials"]
    with pytest.raises(FreshBResearchPackageError):
        _load(tmp_path, _with_review(payload))
