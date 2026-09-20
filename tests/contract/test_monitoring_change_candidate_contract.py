"""Task 9.3 监测变更候选合同：Schema、Python 合同、稳定去重摘要与双布局登记。

Schema（``schemas/monitoring-change-candidate.schema.json``）是 v1.2 §17.3
的机器合同。本测试以正/负例向量驱动四条不变式在边界上真实生效：

1. 同一业务变化的重复发现保持同一候选身份；同一来源的不同定位、版本或
   候选值形成不同候选（去重摘要参与字段精确冻结）；
2. 构造边界重算摘要与候选/交接单标识；``model_copy`` 漂移在聚合边界的
   重推导下失败关闭（quality-guidelines 对抗测试）；
3. 交接单只能来自“启动正常刷新”的用户决定，内容寻址且幂等重放同标识；
4. 观察结果四类可区分并转译为不含内部工程化标签的自然中文。
"""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from ci_workflow.domain.monitoring import (
    MONITORING_CANDIDATE_DIAGNOSTIC_EVENT,
    MONITORING_CANDIDATE_DISCOVERED_EVENT,
    MONITORING_CANDIDATE_DISPOSITION_EVENT,
    MONITORING_CANDIDATE_REDISCOVERED_EVENT,
    MONITORING_REFRESH_HANDOFF_EVENT,
    MonitoringChangeCandidate,
    MonitoringContractError,
    MonitoringDiagnosticRecord,
    MonitoringRefreshHandoff,
    MonitoringSourceIdentity,
    MonitoringUserDispositionRecord,
    acquisition_status_zh,
    build_change_candidate,
    build_refresh_handoff,
    candidate_id_from_digest,
    change_type_zh,
    diagnostic_status_zh,
    disposition_zh,
    failure_category_zh,
    monitoring_dedupe_digest,
    outcome_guidance_zh,
    verify_candidate_dedupe_identity,
    verify_refresh_handoff_addressing,
)

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas" / "monitoring-change-candidate.schema.json"
PACKAGED_SCHEMA_PATH = (
    ROOT / "src" / "ci_workflow" / "schemas" / "monitoring-change-candidate.schema.json"
)
CST = timezone(timedelta(hours=8))
DISCOVERED_AT = datetime(2026, 9, 1, 3, 0, tzinfo=CST)


def _source() -> MonitoringSourceIdentity:
    return MonitoringSourceIdentity(
        source_stable_id="source_" + "a" * 24,
        source_version_id=" ClinicalTrials.gov-NCT048-results-content-v1 ",
        locator="结果章节/表 2/ORR 行",
        source_url="https://example.org/trial/NCT048/results",
    )


def _candidate_kwargs() -> dict[str, Any]:
    return {
        "project_id": "项目-特应性皮炎-A",
        "source_identity": _source(),
        "discovered_at": DISCOVERED_AT,
        "observer": "监测运行 monitoring-nightly",
        "discovery_note_zh": "登记平台结果页的总体缓解率行已更新为最终值。",
        "entity_id": "trial_" + "b" * 24,
        "claim_domain": "疗效终点",
        "change_type": "value_updated",
        "current_value": "ORR 45%（95% CI 40–50）",
        "candidate_value": "ORR 52%（95% CI 47–57）",
        "possibly_affected_reports": ("A",),
        "possibly_affected_page_ids": ("efficacy",),
    }


def _candidate() -> MonitoringChangeCandidate:
    return build_change_candidate(**_candidate_kwargs())


def _load_schema() -> dict[str, Any]:
    value: dict[str, Any] = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return value


def _validator() -> Draft202012Validator:
    return Draft202012Validator(
        _load_schema(), format_checker=Draft202012Validator.FORMAT_CHECKER
    )


def _assert_valid(validator: Draft202012Validator, payload: dict[str, Any]) -> None:
    messages = sorted(error.message for error in validator.iter_errors(payload))
    assert not messages, messages


def _assert_invalid(validator: Draft202012Validator, payload: dict[str, Any]) -> None:
    messages = sorted(error.message for error in validator.iter_errors(payload))
    assert messages, "预期被 Schema 拒绝的载荷竟然通过"


# ── Schema 与双布局登记 ──────────────────────────────────────────────────────


def test_schema_is_valid_draft_2020_12() -> None:
    Draft202012Validator.check_schema(_load_schema())


def test_packaged_copy_matches_directory_contract() -> None:
    """目录包与随包分发的运行时 Schema 必须逐字一致，避免安装后口径漂移。"""

    assert PACKAGED_SCHEMA_PATH.read_bytes() == SCHEMA_PATH.read_bytes()


def test_deferred_monitoring_schema_is_not_registered_in_v1_package_manifest() -> None:
    manifest: dict[str, Any] = json.loads(
        (ROOT / "package-manifest.json").read_text(encoding="utf-8")
    )
    schemas = manifest["components"]["schemas"]
    assert isinstance(schemas, list)
    assert "schemas/monitoring-change-candidate.schema.json" not in schemas
    assert SCHEMA_PATH.exists() and PACKAGED_SCHEMA_PATH.exists()


# ── Pydantic 合同与 Schema 的一致性 ──────────────────────────────────────────


def test_built_candidate_roundtrip_passes_schema() -> None:
    """规范构造入口产出的候选整体通过打包 Schema（monitoring/inbox 投影合同）。"""

    payload = _candidate().model_dump(mode="json")
    _assert_valid(_validator(), payload)


def test_candidate_lifecycle_passes_schema_at_every_stage() -> None:
    validator = _validator()
    base = _candidate().model_dump(mode="json")

    rediscovered = MonitoringChangeCandidate.model_validate(
        {
            **base,
            "discoveries": [
                *base["discoveries"],
                {
                    "observed_at": "2026-09-02T03:00:00+08:00",
                    "observer": "监测运行 monitoring-nightly",
                    "outcome": "change_found",
                    "note_zh": "同一变化再次出现，已合并为同一候选。",
                },
            ],
        }
    )
    _assert_valid(validator, rediscovered.model_dump(mode="json"))

    diagnosed = MonitoringChangeCandidate.model_validate(
        {
            **rediscovered.model_dump(mode="json"),
            "diagnostic_status": "technical_failure_recoverable",
            "diagnostics": [
                {
                    "diagnostic_id": "诊断-001",
                    "status": "technical_failure_recoverable",
                    "failure_category": "rate_limit",
                    "attempts": 2,
                    "methods_tried_zh": ["按恢复策略间隔重试", "切换备用镜像"],
                    "next_step_zh": "等待限流窗口结束后继续自动重试。",
                    "user_guidance_zh": "来源限流，正在自动恢复，暂不需要您处理。",
                    "recorded_at": "2026-09-03T03:00:00+08:00",
                }
            ],
        }
    )
    _assert_valid(validator, diagnosed.model_dump(mode="json"))

    recovered = MonitoringChangeCandidate.model_validate(
        {
            **diagnosed.model_dump(mode="json"),
            "diagnostic_status": "healthy",
            "diagnostics": [
                *diagnosed.model_dump(mode="json")["diagnostics"],
                {
                    "diagnostic_id": "诊断-002",
                    "status": "recovered",
                    "failure_category": "rate_limit",
                    "attempts": 2,
                    "methods_tried_zh": ["按恢复策略间隔重试"],
                    "next_step_zh": "限流窗口已结束，恢复正常监测。",
                    "user_guidance_zh": "来源访问已恢复，无需您处理。",
                    "recorded_at": "2026-09-04T03:00:00+08:00",
                },
            ],
        }
    )
    _assert_valid(validator, recovered.model_dump(mode="json"))

    handoff = build_refresh_handoff(
        candidate=recovered,
        project_contract_version=3,
        suggested_review_scope_zh="复核 A 报告疗效页的总体缓解率行及其证据抽屉。",
        created_at=datetime(2026, 9, 5, 9, 0, tzinfo=CST),
    )
    accepted = MonitoringChangeCandidate.model_validate(
        {
            **recovered.model_dump(mode="json"),
            "user_disposition": "start_normal_refresh",
            "disposition_records": [
                {
                    "disposition": "start_normal_refresh",
                    "decided_by": "医学负责人",
                    "decided_at": "2026-09-05T09:00:00+08:00",
                    "reason_zh": "同意按候选启动正常刷新重新核验。",
                }
            ],
            "refresh_handoff": json.loads(handoff.model_dump_json()),
        }
    )
    _assert_valid(validator, accepted.model_dump(mode="json"))
    verify_candidate_dedupe_identity(accepted)
    verify_refresh_handoff_addressing(accepted.refresh_handoff)


def test_schema_rejects_detached_identity_and_label_leakage() -> None:
    validator = _validator()
    payload = _candidate().model_dump(mode="json")

    missing_digest = deepcopy(payload)
    del missing_digest["dedupe_digest"]
    _assert_invalid(validator, missing_digest)

    bad_digest = deepcopy(payload)
    bad_digest["dedupe_digest"] = "X" * 64
    _assert_invalid(validator, bad_digest)

    bad_candidate_id = deepcopy(payload)
    bad_candidate_id["candidate_id"] = "candidate-001"
    _assert_invalid(validator, bad_candidate_id)

    label_leak = deepcopy(payload)
    label_leak["discoveries"][0]["note_zh"] = "value_updated"
    _assert_invalid(validator, label_leak)

    naive_time = deepcopy(payload)
    naive_time["discovered_at"] = "2026-09-01T03:00:00"
    _assert_invalid(validator, naive_time)


def test_schema_rejects_handoff_without_refresh_decision() -> None:
    validator = _validator()
    payload = _candidate().model_dump(mode="json")
    handoff = build_refresh_handoff(
        candidate=_candidate(),
        project_contract_version=1,
        suggested_review_scope_zh="复核 A 报告疗效页。",
        created_at=datetime(2026, 9, 5, 9, 0, tzinfo=CST),
    )
    payload["refresh_handoff"] = json.loads(handoff.model_dump_json())
    payload["user_disposition"] = "pending"
    _assert_invalid(validator, payload)

    decided_without_records = deepcopy(payload)
    decided_without_records["user_disposition"] = "start_normal_refresh"
    _assert_invalid(validator, decided_without_records)

    # Schema 只能约束“有决定记录”，成员与当前处置一致由 Python 合同 fail-closed：
    # 启动刷新的决定必须由同种处置记录支撑，暂不处理的记录不能替代。
    decided = deepcopy(decided_without_records)
    decided["disposition_records"] = [
        {
            "disposition": "deferred",
            "decided_by": "医学负责人",
            "decided_at": "2026-09-05T09:00:00+08:00",
            "reason_zh": "暂不处理。",
        }
    ]
    _assert_valid(validator, decided)
    with pytest.raises(ValidationError, match="当前处置必须有对应的用户决定记录"):
        MonitoringChangeCandidate.model_validate(decided)


def test_schema_requires_methods_before_user_assistance() -> None:
    validator = _validator()
    payload = _candidate().model_dump(mode="json")
    payload["diagnostic_status"] = "needs_user_assistance"
    payload["diagnostics"] = [
        {
            "diagnostic_id": "诊断-003",
            "status": "needs_user_assistance",
            "failure_category": "captcha_or_login",
            "attempts": 3,
            "methods_tried_zh": [],
            "next_step_zh": "等待用户协助。",
            "user_guidance_zh": "需要您在浏览器中协助完成访问。",
            "recorded_at": "2026-09-03T03:00:00+08:00",
        }
    ]
    _assert_invalid(validator, payload)
    payload["diagnostics"][0]["methods_tried_zh"] = ["自动重试", "备用镜像"]
    _assert_valid(validator, payload)
    with pytest.raises(ValidationError, match="需要用户协助的诊断必须提供"):
        MonitoringChangeCandidate.model_validate(
            {
                **_candidate().model_dump(),
                "diagnostic_status": "needs_user_assistance",
                "diagnostics": [
                    MonitoringDiagnosticRecord(
                        diagnostic_id="诊断-003",
                        status="needs_user_assistance",
                        failure_category="captcha_or_login",
                        attempts=3,
                        methods_tried_zh=(),
                        next_step_zh="等待用户协助。",
                        user_guidance_zh="需要您在浏览器中协助完成访问。",
                        recorded_at=datetime(2026, 9, 3, 3, 0, tzinfo=CST),
                    )
                ],
            }
        )


# ── 稳定去重摘要与候选标识 ──────────────────────────────────────────────────


def test_same_business_change_keeps_one_candidate_identity() -> None:
    first = _candidate()
    again_kwargs = _candidate_kwargs()
    again_kwargs["discovered_at"] = datetime(2026, 9, 8, 3, 0, tzinfo=CST)
    again_kwargs["discovery_note_zh"] = "重复发现同一变化，仅追加发现记录。"
    again = build_change_candidate(**again_kwargs)

    assert again.candidate_id == first.candidate_id
    assert again.dedupe_digest == first.dedupe_digest
    assert first.candidate_id.startswith("monitoring-candidate_")
    assert candidate_id_from_digest(first.dedupe_digest) == first.candidate_id

    url_variant_kwargs = _candidate_kwargs()
    url_variant_kwargs["source_identity"] = _source().model_copy(
        update={"source_url": "https://mirror.example.org/nct048/results"}
    )
    url_variant = build_change_candidate(**url_variant_kwargs)
    assert url_variant.candidate_id == first.candidate_id


def test_distinct_locator_version_or_value_forms_distinct_candidates() -> None:
    base = _candidate_kwargs()
    variations: dict[str, dict[str, Any]] = {
        "locator": {
            **base,
            "source_identity": _source().model_copy(
                update={"locator": "结果章节/表 3/ORR 行"}
            ),
        },
        "source_version_id": {
            **base,
            "source_identity": _source().model_copy(
                update={"source_version_id": "ClinicalTrials.gov-NCT048-results-content-v2"}
            ),
        },
        "candidate_value": {**base, "candidate_value": "ORR 55%（95% CI 50–60）"},
        "entity_id": {**base, "entity_id": "trial_" + "c" * 24},
        "claim_domain": {**base, "claim_domain": "安全性"},
        "change_type": {**base, "change_type": "value_corrected"},
        "project_id": {**base, "project_id": "项目-特应性皮炎-B"},
    }
    for label, kwargs in variations.items():
        assert (
            build_change_candidate(**kwargs).candidate_id != _candidate().candidate_id
        ), label


def test_direct_construction_with_drifted_digest_fails_closed() -> None:
    """构造边界重算摘要：自带不一致摘要或候选标识的载荷失败关闭。"""

    payload = _candidate().model_dump()
    with pytest.raises(ValidationError, match="去重摘要与候选当前内容不一致"):
        MonitoringChangeCandidate.model_validate({**payload, "dedupe_digest": "f" * 64})
    with pytest.raises(ValidationError, match="候选标识与去重摘要不一致"):
        MonitoringChangeCandidate.model_validate(
            {**payload, "candidate_id": "monitoring-candidate_" + "0" * 24}
        )


def test_aggregation_boundaries_reject_model_copy_drift() -> None:
    """``model_copy(update=...)`` 绕过构造校验；聚合边界重推导失败关闭。"""

    candidate = _candidate()
    verify_candidate_dedupe_identity(candidate)

    drifted_value = candidate.model_copy(update={"candidate_value": "ORR 60%"})
    with pytest.raises(MonitoringContractError, match="去重摘要与当前内容不一致"):
        verify_candidate_dedupe_identity(drifted_value)

    drifted_digest = candidate.model_copy(update={"dedupe_digest": "e" * 64})
    with pytest.raises(MonitoringContractError, match="去重摘要与当前内容不一致"):
        verify_candidate_dedupe_identity(drifted_digest)

    drifted_id = candidate.model_copy(update={"candidate_id": "monitoring-candidate_" + "1" * 24})
    with pytest.raises(MonitoringContractError, match="候选标识与去重摘要不一致"):
        verify_candidate_dedupe_identity(drifted_id)

    disposition = {
        "disposition": "start_normal_refresh",
        "decided_by": "医学负责人",
        "decided_at": "2026-09-05T09:00:00+08:00",
        "reason_zh": "同意启动正常刷新重新核验。",
    }
    handoff = build_refresh_handoff(
        candidate=candidate,
        project_contract_version=1,
        suggested_review_scope_zh="复核 A 报告相关页面。",
        created_at=datetime(2026, 9, 5, 9, 0, tzinfo=CST),
    )
    bound = MonitoringChangeCandidate.model_validate(
        {
            **candidate.model_dump(mode="json"),
            "user_disposition": "start_normal_refresh",
            "disposition_records": [disposition],
            "refresh_handoff": handoff.model_dump(mode="json"),
        }
    )
    drifted_binding = bound.model_copy(
        update={
            "user_disposition": "deferred",
            "disposition_records": (
                *bound.disposition_records,
                MonitoringUserDispositionRecord(
                    disposition="deferred",
                    decided_by="医学负责人",
                    decided_at=datetime(2026, 9, 6, 9, 0, tzinfo=CST),
                    reason_zh="暂不处理。",
                ),
            ),
        }
    )
    with pytest.raises(MonitoringContractError, match="完整合同"):
        verify_candidate_dedupe_identity(drifted_binding)


def test_domain_contract_rejects_ascii_user_visible_prose() -> None:
    kwargs = _candidate_kwargs()
    kwargs["discovery_note_zh"] = "plain ascii note"
    with pytest.raises(ValidationError, match="必须包含中文"):
        build_change_candidate(**kwargs)

    with pytest.raises(ValidationError, match="恢复方法不得重复"):
        MonitoringDiagnosticRecord(
            diagnostic_id="诊断-重复方法",
            status="technical_failure_recoverable",
            failure_category="network",
            attempts=2,
            methods_tried_zh=("自动重试", "自动重试"),
            next_step_zh="继续自动恢复。",
            user_guidance_zh="网络访问暂时失败，正在自动恢复。",
            recorded_at=DISCOVERED_AT,
        )


def test_digest_helper_normalizes_and_freezes_participating_fields() -> None:
    digest = monitoring_dedupe_digest(
        project_id=" 项目-特应性皮炎-A ",
        source_identity=_source(),
        entity_id="trial_" + "b" * 24,
        claim_domain="疗效终点",
        change_type="value_updated",
        current_value="ORR 45%（95% CI 40–50）",
        candidate_value="ORR 52%（95% CI 47–57）",
    )
    assert digest == _candidate().dedupe_digest


# ── 处置与刷新交接单 ────────────────────────────────────────────────────────


def test_handoff_is_content_addressed_and_replay_idempotent() -> None:
    candidate = _candidate()
    handoff = build_refresh_handoff(
        candidate=candidate,
        project_contract_version=3,
        suggested_review_scope_zh="复核 A 报告疗效页的总体缓解率行。",
        created_at=datetime(2026, 9, 5, 9, 0, tzinfo=CST),
    )
    assert handoff.handoff_id.startswith("monitoring-refresh_")
    verify_refresh_handoff_addressing(handoff)

    replay = build_refresh_handoff(
        candidate=candidate,
        project_contract_version=3,
        suggested_review_scope_zh="复核 A 报告疗效页的总体缓解率行。",
        created_at=datetime(2026, 9, 6, 9, 0, tzinfo=CST),
    )
    assert replay.handoff_id == handoff.handoff_id

    changed_scope = build_refresh_handoff(
        candidate=candidate,
        project_contract_version=3,
        suggested_review_scope_zh="复核 A 报告安全性页。",
        created_at=datetime(2026, 9, 5, 9, 0, tzinfo=CST),
    )
    assert changed_scope.handoff_id != handoff.handoff_id


def test_handoff_aggregation_boundary_rejects_model_copy_drift() -> None:
    handoff = build_refresh_handoff(
        candidate=_candidate(),
        project_contract_version=2,
        suggested_review_scope_zh="复核 A 报告疗效页。",
        created_at=datetime(2026, 9, 5, 9, 0, tzinfo=CST),
    )
    verify_refresh_handoff_addressing(handoff)

    drifted = handoff.model_copy(
        update={"suggested_review_scope_zh": "复核 A 报告安全性页。"}
    )
    with pytest.raises(MonitoringContractError, match="交接单标识与绑定内容不一致"):
        verify_refresh_handoff_addressing(drifted)


def test_pending_candidate_cannot_carry_handoff_and_records_back_dispositions() -> None:
    payload = _candidate().model_dump()
    handoff = build_refresh_handoff(
        candidate=_candidate(),
        project_contract_version=1,
        suggested_review_scope_zh="复核 A 报告疗效页。",
        created_at=datetime(2026, 9, 5, 9, 0, tzinfo=CST),
    )
    with pytest.raises(ValidationError, match="待处理候选不能携带刷新交接单"):
        MonitoringChangeCandidate.model_validate(
            {**payload, "refresh_handoff": json.loads(handoff.model_dump_json())}
        )

    with pytest.raises(ValidationError, match="当前处置必须有对应的用户决定记录"):
        MonitoringChangeCandidate.model_validate(
            {**payload, "user_disposition": "deferred"}
        )

    deferred = MonitoringChangeCandidate.model_validate(
        {
            **payload,
            "user_disposition": "deferred",
            "disposition_records": [
                {
                    "disposition": "deferred",
                    "decided_by": "医学负责人",
                    "decided_at": "2026-09-05T09:00:00+08:00",
                    "reason_zh": "暂不处理，保留候选与历史。",
                }
            ],
        }
    )
    assert deferred.refresh_handoff is None
    verify_candidate_dedupe_identity(deferred)


def test_diagnostic_status_must_follow_latest_record() -> None:
    payload = _candidate().model_dump(mode="json")
    failure = {
        "diagnostic_id": "诊断-004",
        "status": "technical_failure_recoverable",
        "failure_category": "network",
        "attempts": 1,
        "methods_tried_zh": ["自动重试"],
        "next_step_zh": "继续自动重试。",
        "user_guidance_zh": "网络问题，正在自动恢复。",
        "recorded_at": "2026-09-03T03:00:00+08:00",
    }
    with pytest.raises(ValidationError, match="技术失败状态必须由诊断记录支撑"):
        MonitoringChangeCandidate.model_validate(
            {**payload, "diagnostic_status": "technical_failure_recoverable"}
        )
    with pytest.raises(ValidationError, match="诊断状态必须与最新诊断记录一致"):
        MonitoringChangeCandidate.model_validate(
            {
                **payload,
                "diagnostic_status": "needs_user_assistance",
                "diagnostics": [failure],
            }
        )


# ── 中文转译与事件词表 ──────────────────────────────────────────────────────


def test_four_outcome_categories_are_distinguishable_in_chinese() -> None:
    outcomes = [
        "change_found",
        "no_change",
        "confirmed_not_public",
        "technical_failure_recoverable",
        "needs_user_assistance",
    ]
    guidance = {outcome: outcome_guidance_zh(outcome) for outcome in outcomes}
    assert len(set(guidance.values())) == len(outcomes)
    for outcome, text in guidance.items():
        assert any("\u4e00" <= char <= "\u9fff" for char in text)
        assert outcome not in text

    # “未发现”与“技术失败”的中文提示不得互相混淆
    assert "没有变化" in guidance["no_change"]
    assert "尚未公开" in guidance["confirmed_not_public"]
    assert "技术问题" in guidance["technical_failure_recoverable"]
    assert "自动重试" in guidance["technical_failure_recoverable"]
    assert "协助" in guidance["needs_user_assistance"]

    with pytest.raises(MonitoringContractError, match="未声明的观察结果"):
        outcome_guidance_zh("sleeping")


def test_machine_vocabulary_translates_without_internal_labels() -> None:
    assert change_type_zh("value_updated") == "数值更新"
    assert disposition_zh("pending") == "待处理"
    assert disposition_zh("start_normal_refresh") == "已启动正常刷新"
    assert disposition_zh("deferred") == "暂不处理"
    assert "协助" in acquisition_status_zh("acquired_with_user_assistance")
    assert "自动恢复" in diagnostic_status_zh("technical_failure_recoverable")
    assert failure_category_zh("rate_limit") == "来源限流"
    for translator, key in (
        (change_type_zh, "value_withdrawn"),
        (disposition_zh, "pending"),
        (acquisition_status_zh, "acquired"),
        (diagnostic_status_zh, "healthy"),
        (failure_category_zh, "unknown"),
    ):
        assert key not in translator(key)


def test_append_event_vocabulary_is_frozen() -> None:
    assert MONITORING_CANDIDATE_DISCOVERED_EVENT == "monitoring.candidate.discovered"
    assert MONITORING_CANDIDATE_REDISCOVERED_EVENT == "monitoring.candidate.rediscovered"
    assert MONITORING_CANDIDATE_DIAGNOSTIC_EVENT == "monitoring.candidate.diagnostic_updated"
    assert MONITORING_CANDIDATE_DISPOSITION_EVENT == "monitoring.candidate.disposition_recorded"
    assert MONITORING_REFRESH_HANDOFF_EVENT == "monitoring.refresh_handoff.created"


def test_candidate_contract_is_closed_and_has_no_fact_write_surface() -> None:
    """合同拒绝未声明字段，且不携带任何写入事实/声明/快照/报告的能力字段。"""

    payload = _candidate().model_dump()
    with pytest.raises(ValidationError):
        MonitoringChangeCandidate.model_validate(
            {**payload, "accepted_fact_id": "fact_" + "d" * 24}
        )
    forbidden = {
        "fact_id",
        "claim_id",
        "snapshot_id",
        "report_version",
        "publish",
        "accepted",
    }
    assert not forbidden & MonitoringChangeCandidate.model_fields.keys()
    assert not forbidden & MonitoringRefreshHandoff.model_fields.keys()
