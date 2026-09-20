"""Task 9.1 来源关联修订建议包合同：自包含修订包唯一通过 Draft 2020-12 Schema。

Schema（``schemas/correction-proposal.schema.json``）是 v1.2 §17.1 的机器合同：
绑定项目、报告、快照、稳定目标 ID、旧值、建议值、理由、来源与影响集合。
本合同测试直接以正/负例向量驱动 Schema，保证四条不变量在边界上真实生效：

1. 六种修订状态与既有 ``RevisionApprovalState`` 冻结合同逐字一致；
2. 验证处置枚举不含批准，批准只能来自报告所有者显式决定（附批准 ID）；
3. 发布前置条件缺一不可：新快照、受影响内容重建、独立质控接受、新版本登记；
4. 用户可见文本字段禁止携带内部工程化标签。
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from ci_workflow.domain.enums import RevisionApprovalState

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas" / "correction-proposal.schema.json"
PACKAGED_SCHEMA_PATH = (
    ROOT / "src" / "ci_workflow" / "schemas" / "correction-proposal.schema.json"
)
DIGEST_A = "a" * 64
DIGEST_C = "c" * 64


def _load_schema() -> dict[str, Any]:
    value: dict[str, Any] = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return value


def _validator() -> Draft202012Validator:
    return Draft202012Validator(
        _load_schema(), format_checker=Draft202012Validator.FORMAT_CHECKER
    )


def _error_messages(validator: Draft202012Validator, payload: dict[str, Any]) -> list[str]:
    return sorted(error.message for error in validator.iter_errors(payload))


def _assert_valid(validator: Draft202012Validator, payload: dict[str, Any]) -> None:
    messages = _error_messages(validator, payload)
    assert not messages, messages


def _assert_invalid(validator: Draft202012Validator, payload: dict[str, Any]) -> list[str]:
    messages = _error_messages(validator, payload)
    assert messages, "预期被 Schema 拒绝的载荷竟然通过"
    return messages


def _proposal(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "proposal_id": "corr-proposal-001",
        "project_id": "project-demo",
        "report_kind": "A",
        "report_version": "a-v1",
        "snapshot_id": "snapshot-a-001",
        "snapshot_content_digest": DIGEST_A,
        "state": "submitted",
        "target": {
            "target_type": "claim",
            "target_id": "claim_" + "b" * 24,
            "target_label_zh": "疗效声明：奥马珠单抗 300mg 每 2 周一次皮下给药",
            "locator": {"section_zh": "疗效对比", "figure_zh": "图 1"},
        },
        "current_visible_value": "ORR 45%（95% CI 40–50）",
        "proposed_value": "ORR 52%（95% CI 47–57）",
        "proposed_explanation_zh": "原文引用中期分析数值，最终发表文章更新了 52 周随访数据。",
        "user_reason_zh": "页面显示的缓解率与 2025 年最终发表数据不一致，请核对更新。",
        "submitted_at": "2026-08-31T12:00:00Z",
        "attachments": [
            {
                "attachment_id": "att-001",
                "kind": "link",
                "url": "https://example.org/paper.pdf",
                "title_zh": "最终发表文献",
            }
        ],
        "evidence_items": [
            {
                "evidence_id": "ev-001",
                "source_url": "https://example.org/paper",
                "description_zh": "最终发表的 52 周疗效数据。",
            }
        ],
        "impact_set": {
            "affected_fact_ids": [],
            "affected_claim_ids": ["claim_" + "b" * 24],
            "affected_view_ids": ["efficacy"],
            "impact_summary_zh": "影响疗效页该声明的展示与对应证据抽屉。",
        },
    }
    payload.update(overrides)
    return payload


def _with_validation(payload: dict[str, Any]) -> dict[str, Any]:
    payload["validation"] = {
        "validation_id": "val-001",
        "validated_at": "2026-08-31T13:00:00Z",
        "validator_id": "agent-correction",
        "checks": {
            "identity_verified": True,
            "context_verified": True,
            "locator_verified": True,
            "conflict_check_done": True,
            "impact_check_done": True,
        },
        "disposition": "validated_pending_user_approval",
        "disposition_reason_zh": "来源身份、上下文与定位核验通过，未发现证据冲突。",
    }
    return payload


def _with_owner_approval(payload: dict[str, Any]) -> dict[str, Any]:
    payload["publish_idempotency_key"] = "publish-corr-proposal-001"
    payload["owner_decision"] = {
        "decision": "approve",
        "decided_by": "owner-med-01",
        "decided_at": "2026-08-31T14:00:00Z",
        "reason_zh": "确认与最终发表数据一致，同意按建议修订。",
        "approval_id": "approval-001",
    }
    return payload


def _as_published(payload: dict[str, Any]) -> dict[str, Any]:
    payload["state"] = "published"
    payload["new_snapshot_id"] = "snapshot-a-002"
    payload["new_snapshot_content_digest"] = DIGEST_C
    payload["rebuild_receipt"] = {
        "views_rebuilt": ["efficacy"],
        "rebuilt_at": "2026-08-31T15:00:00Z",
    }
    payload["independent_qc"] = {
        "qc_verdict_id": "qc-001",
        "qc_result": "accepted",
        "reviewer_id": "independent-reviewer-01",
        "qc_checked_at": "2026-08-31T16:00:00Z",
        "reviewed_snapshot_id": "snapshot-a-002",
        "reviewed_snapshot_content_digest": DIGEST_C,
    }
    payload["published_report_version_id"] = "a-v2"
    payload["published_at"] = "2026-08-31T17:00:00Z"
    return payload


def test_schema_is_valid_draft_2020_12() -> None:
    Draft202012Validator.check_schema(_load_schema())


def test_packaged_copy_matches_directory_contract() -> None:
    """目录包与随包分发的运行时 Schema 必须逐字一致，避免安装后口径漂移。"""
    assert PACKAGED_SCHEMA_PATH.read_bytes() == SCHEMA_PATH.read_bytes()


def test_schema_is_registered_in_package_manifest() -> None:
    manifest: dict[str, Any] = json.loads(
        (ROOT / "package-manifest.json").read_text(encoding="utf-8")
    )
    schemas = manifest["components"]["schemas"]
    assert isinstance(schemas, list)
    assert "schemas/correction-proposal.schema.json" in schemas
    assert (ROOT / "schemas" / "correction-proposal.schema.json").exists()


def test_state_enum_matches_frozen_revision_approval_contract() -> None:
    schema = _load_schema()
    state_values = set(schema["properties"]["state"]["enum"])
    assert state_values == {item.value for item in RevisionApprovalState}


def test_self_contained_package_passes_and_binds_contract_elements() -> None:
    payload = _proposal()
    _assert_valid(_validator(), payload)
    for key in (
        "project_id",
        "report_version",
        "snapshot_id",
        "snapshot_content_digest",
    ):
        assert payload[key]
    assert payload["target"]["target_id"]
    assert payload["current_visible_value"]
    assert payload["proposed_value"]
    assert payload["user_reason_zh"]
    assert payload["evidence_items"]
    assert payload["impact_set"]["affected_claim_ids"]


def test_proposal_lifecycle_passes_schema_at_every_stage() -> None:
    validator = _validator()
    submitted = _proposal()
    _assert_valid(validator, submitted)

    validated = _with_validation(deepcopy(submitted))
    validated["state"] = "validated_pending_user_approval"
    _assert_valid(validator, validated)

    approved = _with_owner_approval(deepcopy(validated))
    approved["state"] = "approved"
    _assert_valid(validator, approved)

    published = _as_published(deepcopy(approved))
    _assert_valid(validator, published)


def test_proposed_value_or_explanation_is_required() -> None:
    validator = _validator()
    neither = _proposal()
    del neither["proposed_value"], neither["proposed_explanation_zh"]
    _assert_invalid(validator, neither)
    _assert_valid(validator, _proposal(proposed_value="ORR 52%"))
    _assert_valid(
        validator,
        _proposal(
            proposed_explanation_zh="建议改为最终发表的 52 周随访缓解率。",
        ),
    )


def test_target_must_follow_stable_id_convention() -> None:
    validator = _validator()
    payload = _proposal()
    payload["target"]["target_id"] = "claim-001"
    _assert_invalid(validator, payload)


def test_attachment_and_evidence_shapes_are_enforced() -> None:
    validator = _validator()
    link_without_url = _proposal()
    del link_without_url["attachments"][0]["url"]
    _assert_invalid(validator, link_without_url)

    evidence_without_anchor = _proposal()
    del evidence_without_anchor["evidence_items"][0]["source_url"]
    _assert_invalid(validator, evidence_without_anchor)


def test_validation_disposition_cannot_write_approval() -> None:
    """验证处置枚举没有批准；仅凭验证记录也不能进入批准状态。"""
    validator = _validator()
    payload = _proposal()
    payload["validation"] = {
        "validation_id": "val-002",
        "validated_at": "2026-08-31T13:00:00Z",
        "validator_id": "agent-correction",
        "checks": {
            "identity_verified": True,
            "context_verified": True,
            "locator_verified": True,
            "conflict_check_done": True,
            "impact_check_done": True,
        },
        "disposition": "approved",
        "disposition_reason_zh": "验证通过。",
    }
    _assert_invalid(validator, payload)

    validation_only_approval = _with_validation(_proposal())
    validation_only_approval["state"] = "approved"
    _assert_invalid(validator, validation_only_approval)


def test_approval_requires_explicit_owner_decision_with_approval_id() -> None:
    validator = _validator()
    no_owner = _proposal()
    no_owner["state"] = "approved"
    _assert_invalid(validator, no_owner)

    approve_without_id = _with_owner_approval(_proposal())
    del approve_without_id["owner_decision"]["approval_id"]
    approve_without_id["state"] = "approved"
    _assert_invalid(validator, approve_without_id)

    approve_without_publish_key = _with_owner_approval(_proposal())
    del approve_without_publish_key["publish_idempotency_key"]
    approve_without_publish_key["state"] = "approved"
    _assert_invalid(validator, approve_without_publish_key)

    approved = _with_owner_approval(_proposal())
    approved["state"] = "approved"
    _assert_valid(validator, approved)


def test_publish_fails_closed_without_prerequisites() -> None:
    """新快照、受影响内容重建、独立质控接受、新版本登记缺一项即失败关闭。"""
    validator = _validator()
    complete = _as_published(_with_owner_approval(_with_validation(_proposal())))

    for field in (
        "new_snapshot_id",
        "new_snapshot_content_digest",
        "rebuild_receipt",
        "independent_qc",
        "published_report_version_id",
        "published_at",
    ):
        broken = deepcopy(complete)
        del broken[field]
        _assert_invalid(validator, broken)

    empty_rebuild = deepcopy(complete)
    empty_rebuild["rebuild_receipt"]["views_rebuilt"] = []
    _assert_invalid(validator, empty_rebuild)

    vetoed_qc = deepcopy(complete)
    vetoed_qc["independent_qc"]["qc_result"] = "rejected"
    _assert_invalid(validator, vetoed_qc)

    for field in ("reviewer_id", "reviewed_snapshot_id", "reviewed_snapshot_content_digest"):
        unbound_qc = deepcopy(complete)
        del unbound_qc["independent_qc"][field]
        _assert_invalid(validator, unbound_qc)

    bad_digest = deepcopy(complete)
    bad_digest["new_snapshot_content_digest"] = "not-a-digest"
    _assert_invalid(validator, bad_digest)


def test_rejected_state_requires_validation_or_owner_rejection() -> None:
    validator = _validator()
    silent = _proposal()
    silent["state"] = "rejected"
    _assert_invalid(validator, silent)

    rejected = _proposal()
    rejected["state"] = "rejected"
    rejected["validation"] = {
        "validation_id": "val-003",
        "validated_at": "2026-08-31T13:00:00Z",
        "validator_id": "agent-correction",
        "checks": {
            "identity_verified": False,
            "context_verified": False,
            "locator_verified": True,
            "conflict_check_done": True,
            "impact_check_done": True,
        },
        "disposition": "rejected",
        "disposition_reason_zh": "补充来源无法定位到原始文献，身份核验未通过。",
    }
    _assert_valid(validator, rejected)

    owner_rejected = _proposal()
    owner_rejected["state"] = "rejected"
    owner_rejected["owner_decision"] = {
        "decision": "reject",
        "decided_by": "owner-med-01",
        "decided_at": "2026-08-31T14:00:00Z",
        "reason_zh": "建议数值与当前证据整体不符，不予采纳。",
    }
    _assert_valid(validator, owner_rejected)


def test_validated_pending_state_requires_matching_validation() -> None:
    validator = _validator()
    without_validation = _proposal()
    without_validation["state"] = "validated_pending_user_approval"
    _assert_invalid(validator, without_validation)

    wrong_disposition = _with_validation(_proposal())
    wrong_disposition["state"] = "validated_pending_user_approval"
    wrong_disposition["validation"]["disposition"] = "needs_evidence"
    _assert_invalid(validator, wrong_disposition)


def test_user_visible_fields_reject_engineering_labels() -> None:
    """用户可见字段出现内部工程化标签时整包拒绝。"""
    validator = _validator()
    labeled_value = _proposal()
    labeled_value["current_visible_value"] = "validated_pending_user_approval"
    _assert_invalid(validator, labeled_value)

    labeled_reason = _proposal()
    labeled_reason["user_reason_zh"] = "approved"
    _assert_invalid(validator, labeled_reason)

    labeled_target = _proposal()
    labeled_target["target"]["target_label_zh"] = "needs_evidence"
    _assert_invalid(validator, labeled_target)


def test_user_visible_value_fields_allow_report_display_values() -> None:
    """显示值允许数字与拉丁字母（报告原样呈现），中文说明字段必须含汉字。"""
    validator = _validator()
    numeric = _proposal(
        current_visible_value="45.0% (95% CI 40-50)",
        proposed_value="52.0% (95% CI 47-57)",
    )
    _assert_valid(validator, numeric)

    ascii_reason = _proposal(user_reason_zh="please check the ORR value")
    _assert_invalid(validator, ascii_reason)


def test_timestamps_require_explicit_utc_offset() -> None:
    validator = _validator()
    naive = _proposal(submitted_at="2026-08-31T12:00:00")
    _assert_invalid(validator, naive)


def test_internal_label_guard_covers_runtime_vocabulary() -> None:
    """工程化标签词表必须覆盖修订状态、所有者决定、目标类型与质控结论。"""
    guard_enum = set(_load_schema()["$defs"]["InternalLabelGuard"]["not"]["enum"])
    expected = {item.value for item in RevisionApprovalState} | {
        "approve",
        "reject",
        "fact",
        "claim",
        "chart_point",
        "matrix_cell",
        "accepted",
    }
    assert guard_enum >= expected
