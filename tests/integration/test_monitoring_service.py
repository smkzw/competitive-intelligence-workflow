"""Task 9.3 可选监测服务集成测试（worker_02 工作项）。

覆盖 PRD §验收 1–6 中属于监测服务的部分，全部运行在
:mod:`ci_workflow.domain.monitoring` 的机器合同与 §17.3 JSON Schema 之上：

1. 候选合同保存 §17.3 最低字段集，投影写入 ``monitoring/inbox/`` 且在
   生命周期每个阶段都通过 Schema 校验。
2. 相同业务变化重复发现返回同一候选并追加发现历史；同一来源但不同
   定位、版本或候选值形成不同候选。
3. 候选投影丢失/漂移时由规范事件流自愈重建；同一幂等键不同载荷失败关闭。
4. 监测成功但无变化、证据未公开、技术获取失败、需要用户协助四类结果
   可区分，中文提示说明阻断原因与用户要做什么；无变化观察不创建空候选。
5. 用户"启动正常刷新"的处置与只读交接单同拍落账，交接单绑定项目、候选
   和当前合同版本；不改事实/声明表、正式快照或报告，不产生刷新计划事件。
6. "暂不处理"保留候选及历史；处置重放幂等。
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from ci_workflow.application.monitoring_service import (
    MonitoringAssistanceError,
    MonitoringConflictError,
    MonitoringNotFoundError,
    MonitoringObservation,
    MonitoringObservationError,
    MonitoringObservationReceipt,
    MonitoringRefreshHandoff,
    MonitoringService,
    MonitoringServiceError,
    MonitoringSourceIdentity,
    MonitoringStateError,
)
from ci_workflow.application.project_service import (
    create_project_workspace,
    verify_project_workspace,
)
from ci_workflow.domain.contracts import create_project_contract
from ci_workflow.domain.monitoring import (
    MONITORING_CANDIDATE_DIAGNOSTIC_EVENT,
    MONITORING_CANDIDATE_DISCOVERED_EVENT,
    MONITORING_CANDIDATE_DISPOSITION_EVENT,
    MONITORING_CANDIDATE_REDISCOVERED_EVENT,
    MONITORING_REFRESH_HANDOFF_EVENT,
    MonitoringChangeCandidate,
    MonitoringUserDispositionRecord,
    build_refresh_handoff,
    candidate_id_from_digest,
    monitoring_dedupe_digest,
)
from ci_workflow.storage.event_store import EventConflictError, EventStore, WorkflowEvent

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas" / "monitoring-change-candidate.schema.json"
TZ = timezone(timedelta(hours=8))
DISCOVERED_AT = datetime(2026, 9, 1, 9, 0, 0, tzinfo=TZ)
REDISCOVERED_AT = datetime(2026, 9, 2, 9, 0, 0, tzinfo=TZ)
DECIDED_AT = datetime(2026, 9, 2, 12, 0, 0, tzinfo=TZ)
HANDOFF_AT = datetime(2026, 9, 2, 12, 30, 0, tzinfo=TZ)

OWNER = "owner-test"
OBSERVER = "monitor-nightly"
OBSERVER_2 = "monitor-nightly-2"

SOURCE_STABLE_ID = "source_" + "a" * 24
ENTITY_ID = "trial_" + "b" * 24


def _build_project(tmp_path: Path):
    contract = create_project_contract(
        indication="特应性皮炎",
        reports=["A", "B"],
        outputs=["html"],
        created_at=datetime(2026, 8, 30, 10, 0, 0, tzinfo=TZ),
    )
    project_root = create_project_workspace(tmp_path / "project", contract)
    return project_root, contract


def _source(**overrides) -> MonitoringSourceIdentity:
    fields: dict[str, Any] = {
        "source_stable_id": SOURCE_STABLE_ID,
        "source_version_id": "NCT048-results-content-v1",
        "locator": "结果章节/表 2/ORR 行",
        "source_url": "https://example.org/trial/NCT048/results",
    }
    fields.update(overrides)
    return MonitoringSourceIdentity(**fields)


def _change_observation(project_id: str, **overrides) -> MonitoringObservation:
    fields: dict[str, Any] = {
        "project_id": project_id,
        "source_identity": _source(),
        "outcome": "change_found",
        "observed_at": DISCOVERED_AT,
        "observer": OBSERVER,
        "discovery_note_zh": "登记平台结果页的总体缓解率行已更新为最终值。",
        "entity_id": ENTITY_ID,
        "claim_domain": "疗效终点",
        "change_type": "value_updated",
        "current_value": "ORR 45%（95% CI 40–50）",
        "candidate_value": "ORR 52%（95% CI 47–57）",
        "possibly_affected_reports": ("A",),
        "possibly_affected_page_ids": ("a-efficacy-matrix",),
    }
    fields.update(overrides)
    return MonitoringObservation(**fields)


def _diagnosis_fields(**overrides) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "status": "technical_failure_recoverable",
        "failure_category": "rate_limit",
        "attempts": 1,
        "methods_tried_zh": ("直接抓取", "只读镜像"),
        "next_step_zh": "等待下一轮自动重试",
        "recorded_at": REDISCOVERED_AT,
        "recorded_by": OBSERVER,
    }
    fields.update(overrides)
    return fields


def _assert_projection_matches_schema(service: MonitoringService, candidate_id: str) -> None:
    """服务写出的收件投影必须在每个生命周期阶段通过 §17.3 Schema。"""

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)
    payload = json.loads(
        (service.project_root / "monitoring" / "inbox" / f"{candidate_id}.json").read_text(
            encoding="utf-8"
        )
    )
    messages = sorted(error.message for error in validator.iter_errors(payload))
    assert not messages, messages


@pytest.fixture()
def workspace(tmp_path: Path):
    project_root, contract = _build_project(tmp_path)
    service = MonitoringService(project_root)
    return project_root, contract, service


# ── 验收 1：候选合同最低字段集、投影位置与 Schema 一致 ─────────────────────


def test_first_discovery_creates_candidate_with_minimum_contract_fields(workspace):
    project_root, contract, service = workspace

    receipt = service.submit_observation(_change_observation(contract.project_id))

    assert isinstance(receipt, MonitoringObservationReceipt)
    assert receipt.candidate_id is not None
    assert receipt.rediscovered is False
    candidate = service.load(receipt.candidate_id)

    # §17.3 最低字段集全部在机器合同中
    assert candidate.candidate_id == receipt.candidate_id
    assert candidate.project_id == contract.project_id
    assert candidate.contract_version == "1.0"
    assert candidate.source_identity.source_stable_id == SOURCE_STABLE_ID
    assert candidate.source_identity.source_version_id.startswith("NCT048")
    assert candidate.source_identity.locator.endswith("ORR 行")
    assert candidate.source_identity.source_url.startswith("https://")
    assert candidate.discovered_at == DISCOVERED_AT
    assert len(candidate.discoveries) == 1
    assert candidate.entity_id == ENTITY_ID
    assert candidate.claim_domain == "疗效终点"
    assert candidate.change_type == "value_updated"
    assert candidate.current_value.startswith("ORR 45%")
    assert candidate.candidate_value.startswith("ORR 52%")
    assert candidate.dedupe_digest == monitoring_dedupe_digest(
        project_id=contract.project_id,
        source_identity=candidate.source_identity,
        entity_id=ENTITY_ID,
        claim_domain="疗效终点",
        change_type="value_updated",
        current_value="ORR 45%（95% CI 40–50）",
        candidate_value="ORR 52%（95% CI 47–57）",
    )
    assert candidate.candidate_id == candidate_id_from_digest(candidate.dedupe_digest)
    assert candidate.possibly_affected_reports == ("A",)
    assert candidate.possibly_affected_page_ids == ("a-efficacy-matrix",)
    assert candidate.acquisition_status == "acquired"
    assert candidate.diagnostic_status == "healthy"
    assert candidate.user_disposition == "pending"
    assert candidate.refresh_handoff is None

    projection = project_root / "monitoring" / "inbox" / f"{candidate.candidate_id}.json"
    assert projection.is_file()
    _assert_projection_matches_schema(service, candidate.candidate_id)

    event_types = [event.event_type for event in service.event_store.read_all()]
    assert MONITORING_CANDIDATE_DISCOVERED_EVENT in event_types


# ── 验收 2：去重身份与重复发现 ──────────────────────────────────────────────


def test_duplicate_discovery_returns_same_candidate_and_appends_history(workspace):
    _, contract, service = workspace

    first = service.submit_observation(_change_observation(contract.project_id))
    second = service.submit_observation(
        _change_observation(
            contract.project_id,
            observed_at=REDISCOVERED_AT,
            observer=OBSERVER_2,
            discovery_note_zh="次日复核确认该缓解率行仍为更新后的最终值。",
        )
    )

    assert second.candidate_id == first.candidate_id
    assert second.rediscovered is True
    assert "不会重复提醒" in second.guidance_zh
    candidate = service.load(first.candidate_id)
    assert len(candidate.discoveries) == 2
    assert candidate.discoveries[0].observer == OBSERVER
    assert candidate.discoveries[1].observer == OBSERVER_2
    # 仍然只有一个候选投影文件
    inbox = list((service.project_root / "monitoring" / "inbox").glob("*.json"))
    assert [path.name for path in inbox] == [f"{first.candidate_id}.json"]
    _assert_projection_matches_schema(service, first.candidate_id)


def test_exact_replay_of_discovery_is_idempotent(workspace):
    _, contract, service = workspace

    first = service.submit_observation(_change_observation(contract.project_id))
    replay = service.submit_observation(_change_observation(contract.project_id))

    assert replay.candidate_id == first.candidate_id
    assert replay.receipt_id == first.receipt_id
    assert replay.rediscovered is False
    candidate = service.load(first.candidate_id)
    assert len(candidate.discoveries) == 1
    discovered_events = [
        event
        for event in service.event_store.read_all()
        if event.event_type == MONITORING_CANDIDATE_DISCOVERED_EVENT
    ]
    assert len(discovered_events) == 1


def test_same_source_different_locator_version_or_value_forms_distinct_candidates(
    workspace,
):
    _, contract, service = workspace

    base = service.submit_observation(_change_observation(contract.project_id))
    by_locator = service.submit_observation(
        _change_observation(
            contract.project_id,
            source_identity=_source(locator="基线特征/表 1/年龄行"),
            observed_at=REDISCOVERED_AT,
        )
    )
    by_version = service.submit_observation(
        _change_observation(
            contract.project_id,
            source_identity=_source(source_version_id="NCT048-results-content-v2"),
            observed_at=REDISCOVERED_AT,
        )
    )
    by_value = service.submit_observation(
        _change_observation(
            contract.project_id,
            candidate_value="ORR 55%（95% CI 50–60）",
            observed_at=REDISCOVERED_AT,
        )
    )

    ids = {
        base.candidate_id,
        by_locator.candidate_id,
        by_version.candidate_id,
        by_value.candidate_id,
    }
    assert len(ids) == 4
    assert len(service.list_candidates()) == 4
    assert len(service.list_candidates(source_stable_id=SOURCE_STABLE_ID)) == 4


# ── 验收 3：投影恢复与幂等冲突 ─────────────────────────────────────────────


def test_projection_loss_and_drift_self_heal_from_events(workspace):
    project_root, contract, service = workspace

    receipt = service.submit_observation(_change_observation(contract.project_id))
    candidate_id = receipt.candidate_id
    canonical = service.load(candidate_id)
    projection = project_root / "monitoring" / "inbox" / f"{candidate_id}.json"

    projection.unlink()
    recovered = service.load(candidate_id)
    assert recovered == canonical
    assert projection.is_file()

    projection.write_text('{"candidate_id": "drifted"}', encoding="utf-8")
    healed = service.load(candidate_id)
    assert healed == canonical
    assert json.loads(projection.read_text(encoding="utf-8"))["candidate_id"] == candidate_id


def test_same_idempotency_key_with_different_payload_fails_closed(workspace):
    _, contract, service = workspace

    # 预先占住目标候选的首次发现幂等键：事件载荷属于另一个合法候选，
    # 归约时不会命中本候选，但同键不同载荷必须失败关闭。
    victim = _change_observation(contract.project_id)
    victim_digest = monitoring_dedupe_digest(
        project_id=victim.project_id,
        source_identity=victim.source_identity,
        entity_id=ENTITY_ID,
        claim_domain="疗效终点",
        change_type="value_updated",
        current_value="ORR 45%（95% CI 40–50）",
        candidate_value="ORR 52%（95% CI 47–57）",
    )
    victim_id = candidate_id_from_digest(victim_digest)
    other = service.submit_observation(
        _change_observation(
            contract.project_id,
            entity_id="trial_" + "c" * 24,
            observed_at=REDISCOVERED_AT,
        )
    )
    other_candidate = service.load(other.candidate_id)
    store = EventStore(service.project_root)
    squatter = WorkflowEvent(
        schema_version="1.0",
        event_id="monitoring-discovery_squatterevent000000000001",
        project_id=contract.project_id,
        run_id="monitoring",
        event_type=MONITORING_CANDIDATE_DISCOVERED_EVENT,
        occurred_at=REDISCOVERED_AT,
        actor_id=OBSERVER,
        idempotency_key=f"monitoring.candidate.discovered:{victim_id}",
        payload={"candidate": other_candidate.model_dump(mode="json")},
    )
    store.append(squatter)

    with pytest.raises(EventConflictError):
        service.submit_observation(victim)


def test_submission_rejects_foreign_project_without_writing(workspace):
    project_root, _, service = workspace
    events_before = (project_root / "events" / "events.jsonl").read_bytes()
    inbox_before = tuple((project_root / "monitoring" / "inbox").iterdir())

    with pytest.raises(MonitoringObservationError, match="所属项目与当前项目不一致"):
        service.submit_observation(_change_observation("foreign-project"))

    assert (project_root / "events" / "events.jsonl").read_bytes() == events_before
    assert tuple((project_root / "monitoring" / "inbox").iterdir()) == inbox_before


# ── 验收 4：四类结果可区分、中文提示与空候选禁止 ──────────────────────────


def test_no_change_and_not_public_write_receipts_without_candidates(workspace):
    project_root, contract, service = workspace

    no_change = service.submit_observation(
        MonitoringObservation(
            project_id=contract.project_id,
            source_identity=_source(),
            outcome="no_change",
            observed_at=DISCOVERED_AT,
            observer=OBSERVER,
        )
    )
    not_public = service.submit_observation(
        MonitoringObservation(
            project_id=contract.project_id,
            source_identity=_source(source_stable_id="source_" + "d" * 24),
            outcome="confirmed_not_public",
            observed_at=REDISCOVERED_AT,
            observer=OBSERVER,
        )
    )

    assert no_change.outcome == "no_change"
    assert not_public.outcome == "confirmed_not_public"
    assert no_change.guidance_zh != not_public.guidance_zh
    assert "没有变化" in no_change.guidance_zh
    assert "尚未公开" in not_public.guidance_zh
    # 无变化/未公开不创建空候选
    assert list((project_root / "monitoring" / "inbox").glob("*.json")) == []
    with pytest.raises(MonitoringNotFoundError):
        service.load("monitoring-candidate_" + "0" * 24)

    receipts = service.observation_receipts()
    assert [receipt.outcome for receipt in receipts] == [
        "no_change",
        "confirmed_not_public",
    ]
    receipt_lines = (
        (project_root / "receipts" / "monitoring_observations.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    )
    assert len(receipt_lines) == 2


def test_receipt_projection_self_heals_from_events(workspace):
    project_root, contract, service = workspace

    service.submit_observation(
        MonitoringObservation(
            project_id=contract.project_id,
            source_identity=_source(),
            outcome="no_change",
            observed_at=DISCOVERED_AT,
            observer=OBSERVER,
        )
    )
    receipt_path = project_root / "receipts" / "monitoring_observations.jsonl"
    receipt_path.unlink()

    receipts = service.observation_receipts()

    assert len(receipts) == 1
    assert receipt_path.is_file()


def test_technical_failure_distinct_from_no_change_with_chinese_guidance(workspace):
    project_root, contract, service = workspace

    failure = service.submit_observation(
        MonitoringObservation(
            project_id=contract.project_id,
            source_identity=_source(),
            outcome="technical_failure_recoverable",
            observed_at=DISCOVERED_AT,
            observer=OBSERVER,
            failure_category="rate_limit",
            attempts=1,
            methods_tried_zh=("直接抓取",),
            next_step_zh="按退避策略自动重试",
        )
    )

    assert failure.outcome == "technical_failure_recoverable"
    assert failure.failure_category == "rate_limit"
    assert failure.attempts == 1
    assert failure.methods_tried_zh == ("直接抓取",)
    assert "来源限流" in failure.guidance_zh
    assert "自动重试" in failure.guidance_zh
    assert "暂时不需要您处理" in failure.guidance_zh
    # 技术失败也不创建空候选
    assert list((project_root / "monitoring" / "inbox").glob("*.json")) == []


def test_needs_user_assistance_requires_exhausted_recovery(workspace):
    _, contract, service = workspace

    with pytest.raises(MonitoringAssistanceError):
        service.submit_observation(
            MonitoringObservation(
                project_id=contract.project_id,
                source_identity=_source(),
                outcome="needs_user_assistance",
                observed_at=DISCOVERED_AT,
                observer=OBSERVER,
                failure_category="captcha_or_login",
                attempts=2,
                methods_tried_zh=("直接抓取", "只读镜像"),
                next_step_zh="在浏览器中完成该来源登录",
            )
        )
    with pytest.raises(ValidationError):
        MonitoringObservation(
            project_id=contract.project_id,
            source_identity=_source(),
            outcome="needs_user_assistance",
            observed_at=DISCOVERED_AT,
            observer=OBSERVER,
            failure_category="captcha_or_login",
            attempts=3,
            methods_tried_zh=(),
            next_step_zh="在浏览器中完成该来源登录",
        )
    with pytest.raises(MonitoringAssistanceError):
        # 达到上限后继续标为可自动恢复同样失败关闭
        service.submit_observation(
            MonitoringObservation(
                project_id=contract.project_id,
                source_identity=_source(),
                outcome="technical_failure_recoverable",
                observed_at=DISCOVERED_AT,
                observer=OBSERVER,
                failure_category="rate_limit",
                attempts=3,
                methods_tried_zh=("直接抓取",),
                next_step_zh="按退避策略自动重试",
            )
        )

    assistance = service.submit_observation(
        MonitoringObservation(
            project_id=contract.project_id,
            source_identity=_source(),
            outcome="needs_user_assistance",
            observed_at=DISCOVERED_AT,
            observer=OBSERVER,
            failure_category="captcha_or_login",
            attempts=3,
            methods_tried_zh=("直接抓取", "只读镜像", "换出口重试"),
            next_step_zh="在浏览器中完成该来源登录",
        )
    )
    assert assistance.outcome == "needs_user_assistance"
    assert "需要验证码或登录" in assistance.guidance_zh
    assert "在浏览器中完成该来源登录" in assistance.guidance_zh
    assert "3 轮" in assistance.guidance_zh


def test_observation_payload_must_match_outcome(workspace):
    _, contract, service = workspace

    with pytest.raises(ValidationError):
        _change_observation(contract.project_id, entity_id=None)
    with pytest.raises(ValidationError):
        _change_observation(contract.project_id, possibly_affected_reports=())
    with pytest.raises(ValidationError):
        MonitoringObservation(
            project_id=contract.project_id,
            source_identity=_source(),
            outcome="no_change",
            observed_at=DISCOVERED_AT,
            observer=OBSERVER,
            entity_id=ENTITY_ID,
        )
    with pytest.raises(ValidationError):
        MonitoringObservation(
            project_id=contract.project_id,
            source_identity=_source(),
            outcome="technical_failure_recoverable",
            observed_at=DISCOVERED_AT,
            observer=OBSERVER,
            attempts=1,
            methods_tried_zh=("直接抓取",),
            next_step_zh="重试",
        )
    with pytest.raises(ValidationError):
        _change_observation(contract.project_id, possibly_affected_reports=("D",))
    with pytest.raises(ValidationError):
        # 发现说明在观察输入边界即须是面向用户的中文说明。
        _change_observation(contract.project_id, discovery_note_zh="plain ascii note")


@pytest.mark.parametrize(
    ("methods", "next_step"),
    [
        (("automatic retry",), "等待下一轮自动重试"),
        (("直接抓取",), "please login"),
        (("直接抓取", "直接抓取"), "等待下一轮自动重试"),
    ],
)
def test_observation_rejects_ascii_or_duplicate_recovery_text(
    workspace, methods, next_step
):
    _, contract, _ = workspace
    with pytest.raises(ValidationError):
        MonitoringObservation(
            project_id=contract.project_id,
            source_identity=_source(),
            outcome="technical_failure_recoverable",
            observed_at=DISCOVERED_AT,
            observer=OBSERVER,
            failure_category="rate_limit",
            attempts=1,
            methods_tried_zh=methods,
            next_step_zh=next_step,
        )


# ── 候选诊断：技术诊断真实性与恢复合同 ────────────────────────────────────


def test_record_diagnosis_updates_candidate_and_is_idempotent(workspace):
    _, contract, service = workspace

    receipt = service.submit_observation(_change_observation(contract.project_id))
    candidate_id = receipt.candidate_id

    recovering = service.record_diagnosis(candidate_id, **_diagnosis_fields())

    assert recovering.diagnostic_status == "technical_failure_recoverable"
    assert len(recovering.diagnostics) == 1
    assert "来源限流" in recovering.diagnostics[0].user_guidance_zh
    assert "自动重试" in recovering.diagnostics[0].user_guidance_zh
    _assert_projection_matches_schema(service, candidate_id)

    replay = service.record_diagnosis(candidate_id, **_diagnosis_fields())
    assert replay == recovering
    assert len(service.load(candidate_id).diagnostics) == 1

    escalation = service.record_diagnosis(
        candidate_id,
        **_diagnosis_fields(
            status="needs_user_assistance",
            attempts=3,
            next_step_zh="在浏览器中完成该来源登录",
        ),
    )
    assert escalation.diagnostic_status == "needs_user_assistance"
    assert "在浏览器中完成该来源登录" in escalation.diagnostics[-1].user_guidance_zh
    _assert_projection_matches_schema(service, candidate_id)

    recovered = service.record_diagnosis(
        candidate_id,
        **_diagnosis_fields(
            status="recovered",
            attempts=3,
            next_step_zh="无需进一步处理",
        ),
    )
    assert recovered.diagnostic_status == "healthy"
    assert len(recovered.diagnostics) == 3  # 恢复不删除历史失败记录
    _assert_projection_matches_schema(service, candidate_id)


def test_candidate_diagnosis_assistance_gate_fails_closed(workspace):
    _, contract, service = workspace

    receipt = service.submit_observation(_change_observation(contract.project_id))
    candidate_id = receipt.candidate_id

    with pytest.raises(MonitoringAssistanceError):
        service.record_diagnosis(
            candidate_id,
            **_diagnosis_fields(status="needs_user_assistance", attempts=2),
        )
    with pytest.raises(MonitoringAssistanceError):
        service.record_diagnosis(
            candidate_id,
            **_diagnosis_fields(attempts=3),
        )
    with pytest.raises(MonitoringStateError):
        # 没有未解决的技术失败记录时不得登记恢复
        service.record_diagnosis(
            candidate_id,
            **_diagnosis_fields(status="recovered", attempts=1),
        )
    assert len(service.load(candidate_id).diagnostics) == 0


def test_diagnosis_history_survives_projection_loss(workspace):
    _, contract, service = workspace

    receipt = service.submit_observation(_change_observation(contract.project_id))
    candidate_id = receipt.candidate_id
    diagnosed = service.record_diagnosis(candidate_id, **_diagnosis_fields())
    (service.project_root / "monitoring" / "inbox" / f"{candidate_id}.json").unlink()

    recovered = service.load(candidate_id)

    assert recovered == diagnosed


# ── 验收 6：用户处置追加与幂等 ─────────────────────────────────────────────


def test_dispositions_append_only_and_replay_idempotent(workspace):
    _, contract, service = workspace

    receipt = service.submit_observation(_change_observation(contract.project_id))
    candidate_id = receipt.candidate_id

    deferred = service.apply_disposition(
        candidate_id,
        disposition="deferred",
        decided_by=OWNER,
        decided_at=DECIDED_AT,
        reason_zh="等季度评审时再统一处理。",
    )
    assert deferred.user_disposition == "deferred"
    assert len(deferred.disposition_records) == 1
    _assert_projection_matches_schema(service, candidate_id)

    replay = service.apply_disposition(
        candidate_id,
        disposition="deferred",
        decided_by=OWNER,
        decided_at=DECIDED_AT,
        reason_zh="等季度评审时再统一处理。",
    )
    assert replay == deferred
    assert len(service.load(candidate_id).disposition_records) == 1

    # 用户可从暂不处理改为启动刷新；交接生成后决定锁定。
    refreshed = service.apply_disposition(
        candidate_id,
        disposition="start_normal_refresh",
        decided_by=OWNER,
        decided_at=HANDOFF_AT,
        reason_zh="该变化影响结论表述，需要尽快刷新核验。",
    )
    assert refreshed.user_disposition == "start_normal_refresh"
    assert len(refreshed.disposition_records) == 2
    assert [record.disposition for record in refreshed.disposition_records] == [
        "deferred",
        "start_normal_refresh",
    ]
    _assert_projection_matches_schema(service, candidate_id)


def test_disposition_cannot_change_after_refresh_handoff(workspace):
    _, contract, service = workspace
    receipt = service.submit_observation(_change_observation(contract.project_id))
    candidate_id = receipt.candidate_id
    started = service.apply_disposition(
        candidate_id,
        disposition="start_normal_refresh",
        decided_by=OWNER,
        decided_at=DECIDED_AT,
        reason_zh="该变化影响结论表述，需要尽快刷新核验。",
    )
    event_count = len(service.event_store.read_all())

    with pytest.raises(MonitoringStateError, match="已交给正常刷新"):
        service.apply_disposition(
            candidate_id,
            disposition="deferred",
            decided_by=OWNER,
            decided_at=HANDOFF_AT,
            reason_zh="改主意，暂不处理。",
        )

    assert len(service.event_store.read_all()) == event_count
    assert service.load(candidate_id) == started
    _assert_projection_matches_schema(service, candidate_id)


def test_disposition_preserves_candidate_and_history(workspace):
    _, contract, service = workspace

    receipt = service.submit_observation(_change_observation(contract.project_id))
    candidate_id = receipt.candidate_id
    service.apply_disposition(
        candidate_id,
        disposition="deferred",
        decided_by=OWNER,
        decided_at=DECIDED_AT,
        reason_zh="等季度评审时再统一处理。",
    )

    candidate = service.load(candidate_id)

    assert candidate.candidate_id == candidate_id
    assert len(candidate.discoveries) == 1
    assert len(candidate.disposition_records) == 1
    assert (service.project_root / "monitoring" / "inbox" / f"{candidate_id}.json").is_file()


# ── 验收 5：只读刷新交接 ───────────────────────────────────────────────────


def test_refresh_handoff_requires_explicit_user_decision(workspace):
    _, contract, service = workspace

    receipt = service.submit_observation(_change_observation(contract.project_id))
    candidate_id = receipt.candidate_id

    with pytest.raises(MonitoringStateError):
        service.create_refresh_handoff(candidate_id, occurred_at=HANDOFF_AT, actor_id=OWNER)

    service.apply_disposition(
        candidate_id,
        disposition="deferred",
        decided_by=OWNER,
        decided_at=DECIDED_AT,
        reason_zh="等季度评审时再统一处理。",
    )
    with pytest.raises(MonitoringStateError):
        service.create_refresh_handoff(candidate_id, occurred_at=HANDOFF_AT, actor_id=OWNER)


def test_start_normal_refresh_records_disposition_and_handoff_together(workspace):
    project_root, contract, service = workspace

    receipt = service.submit_observation(_change_observation(contract.project_id))
    candidate_id = receipt.candidate_id
    candidate = service.load(candidate_id)
    database_before = (project_root / "state" / "project.sqlite").read_bytes()
    project_yaml_before = (project_root / "project.yaml").read_bytes()
    snapshot_files_before = {
        str(path.relative_to(project_root))
        for path in (project_root / "snapshots").rglob("*")
        if path.is_file()
    }
    report_files_before = {
        str(path.relative_to(project_root))
        for path in (project_root / "reports").rglob("*")
        if path.is_file()
    }

    refreshed = service.apply_disposition(
        candidate_id,
        disposition="start_normal_refresh",
        decided_by=OWNER,
        decided_at=DECIDED_AT,
        reason_zh="该变化影响结论表述，需要尽快刷新核验。",
    )

    # 处置与交接单同拍落账：启动正常刷新的投影必须携带交接单（§17.3）
    handoff = refreshed.refresh_handoff
    assert isinstance(handoff, MonitoringRefreshHandoff)
    assert handoff.candidate_id == candidate_id
    assert handoff.dedupe_digest == candidate.dedupe_digest
    assert handoff.project_id == contract.project_id
    assert handoff.project_contract_version == 1
    assert handoff.source_identity == candidate.source_identity
    assert "建议复核" in handoff.suggested_review_scope_zh
    assert "重新核验" in handoff.suggested_review_scope_zh
    assert "a-efficacy-matrix" not in handoff.suggested_review_scope_zh
    _assert_projection_matches_schema(service, candidate_id)

    # 精确重放返回同一交接单，不重复登记
    replay = service.apply_disposition(
        candidate_id,
        disposition="start_normal_refresh",
        decided_by=OWNER,
        decided_at=DECIDED_AT,
        reason_zh="该变化影响结论表述，需要尽快刷新核验。",
    )
    assert replay.refresh_handoff == handoff
    handoff_events = [
        event
        for event in service.event_store.read_all()
        if event.event_type == MONITORING_REFRESH_HANDOFF_EVENT
    ]
    assert len(handoff_events) == 1

    # 只读边界：不写数据库、不改项目文件、不建正式快照、不写报告、无刷新计划
    assert (project_root / "state" / "project.sqlite").read_bytes() == database_before
    assert (project_root / "project.yaml").read_bytes() == project_yaml_before
    assert {
        str(path.relative_to(project_root))
        for path in (project_root / "snapshots").rglob("*")
        if path.is_file()
    } == snapshot_files_before
    assert {
        str(path.relative_to(project_root))
        for path in (project_root / "reports").rglob("*")
        if path.is_file()
    } == report_files_before
    event_types = [event.event_type for event in service.event_store.read_all()]
    assert not [item for item in event_types if item.startswith("refresh.")]

    # 交接单投影可恢复，并回填到候选投影
    handoff_path = project_root / "monitoring" / "handoffs" / f"{handoff.handoff_id}.json"
    assert handoff_path.is_file()
    handoff_path.unlink()
    assert service.create_refresh_handoff(
        candidate_id, occurred_at=HANDOFF_AT, actor_id=OWNER
    ) == handoff
    assert handoff_path.is_file()
    handoff_path.unlink()
    assert service.load_handoff(handoff.handoff_id) == handoff
    assert handoff_path.is_file()
    assert service.load(candidate_id).refresh_handoff == handoff

    # 项目工作区核心校验不受监测影响
    verification = verify_project_workspace(project_root)
    assert verification.contract.project_id == contract.project_id


def test_handoff_rejects_foreign_project_identity(tmp_path: Path):
    project_root, contract = _build_project(tmp_path)
    service = MonitoringService(project_root)
    receipt = service.submit_observation(_change_observation(contract.project_id))
    refreshed = service.apply_disposition(
        receipt.candidate_id,
        disposition="start_normal_refresh",
        decided_by=OWNER,
        decided_at=DECIDED_AT,
        reason_zh="该变化影响结论表述，需要尽快刷新核验。",
    )
    assert refreshed.refresh_handoff is not None

    document = json.loads((project_root / "project.yaml").read_text(encoding="utf-8"))
    document["project_contract_versions"][0]["project_id"] = "other-project"
    (project_root / "project.yaml").write_text(
        json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 项目身份漂移后，恢复路径上的交接单生成必须失败关闭
    with pytest.raises(MonitoringStateError):
        service.create_refresh_handoff(receipt.candidate_id, occurred_at=HANDOFF_AT, actor_id=OWNER)


def test_second_handoff_with_different_identity_fails_closed(workspace):
    project_root, contract, service = workspace

    receipt = service.submit_observation(_change_observation(contract.project_id))
    candidate_id = receipt.candidate_id
    refreshed = service.apply_disposition(
        candidate_id,
        disposition="start_normal_refresh",
        decided_by=OWNER,
        decided_at=DECIDED_AT,
        reason_zh="该变化影响结论表述，需要尽快刷新核验。",
    )
    first = refreshed.refresh_handoff
    assert first is not None

    # 篡改当前合同版本，制造不同交接身份：同一候选不得绑定第二份交接单
    document = json.loads((project_root / "project.yaml").read_text(encoding="utf-8"))
    document["active_contract_version"] = 2
    document["project_contract_versions"].append(
        {**document["project_contract_versions"][0], "contract_version": 2}
    )
    (project_root / "project.yaml").write_text(
        json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    with pytest.raises(MonitoringConflictError):
        service.create_refresh_handoff(candidate_id, occurred_at=HANDOFF_AT, actor_id=OWNER)
    assert service.load(candidate_id).refresh_handoff == first


def test_reducer_rejects_handoff_bound_to_another_candidate(workspace):
    _, contract, service = workspace
    first_receipt = service.submit_observation(_change_observation(contract.project_id))
    second_receipt = service.submit_observation(
        _change_observation(
            contract.project_id,
            candidate_value="ORR 55%（95% CI 50–60）",
            observed_at=REDISCOVERED_AT,
        )
    )
    first = service.load(first_receipt.candidate_id)
    second = service.load(second_receipt.candidate_id)
    decision = MonitoringUserDispositionRecord(
        disposition="start_normal_refresh",
        decided_by=OWNER,
        decided_at=DECIDED_AT,
        reason_zh="同意启动正常刷新重新核验。",
    )
    foreign_handoff = build_refresh_handoff(
        candidate=second,
        project_contract_version=1,
        suggested_review_scope_zh="建议复核 A 报告相关页面。",
        created_at=HANDOFF_AT,
    )
    store = EventStore(service.project_root)
    store.append(
        WorkflowEvent(
            schema_version="1.0",
            event_id="monitoring-disposition_adversarial0000000001",
            project_id=contract.project_id,
            run_id="monitoring",
            event_type=MONITORING_CANDIDATE_DISPOSITION_EVENT,
            occurred_at=DECIDED_AT,
            actor_id=OWNER,
            idempotency_key="monitoring.adversarial.disposition",
            payload={
                "candidate_id": first.candidate_id,
                "disposition": decision.model_dump(mode="json"),
            },
        )
    )
    store.append(
        WorkflowEvent(
            schema_version="1.0",
            event_id="monitoring-handoff_adversarial000000000001",
            project_id=contract.project_id,
            run_id="monitoring",
            event_type=MONITORING_REFRESH_HANDOFF_EVENT,
            occurred_at=HANDOFF_AT,
            actor_id=OWNER,
            idempotency_key="monitoring.adversarial.handoff",
            payload={
                "candidate_id": first.candidate_id,
                "handoff": foreign_handoff.model_dump(mode="json"),
            },
        )
    )

    with pytest.raises(MonitoringConflictError, match="完整绑定合同"):
        service.load(first.candidate_id)


# ── 事件词表与回执账本边界 ─────────────────────────────────────────────────


def test_append_event_types_follow_frozen_vocabulary(workspace):
    _, contract, service = workspace

    receipt = service.submit_observation(_change_observation(contract.project_id))
    candidate_id = receipt.candidate_id
    service.record_diagnosis(candidate_id, **_diagnosis_fields())
    service.apply_disposition(
        candidate_id,
        disposition="start_normal_refresh",
        decided_by=OWNER,
        decided_at=DECIDED_AT,
        reason_zh="该变化影响结论表述，需要尽快刷新核验。",
    )
    service.submit_observation(
        _change_observation(
            contract.project_id,
            observed_at=REDISCOVERED_AT,
            observer=OBSERVER_2,
            discovery_note_zh="交接后再次确认该变化仍在。",
        )
    )

    event_types = [event.event_type for event in service.event_store.read_all()]
    assert MONITORING_CANDIDATE_DISCOVERED_EVENT in event_types
    assert MONITORING_CANDIDATE_REDISCOVERED_EVENT in event_types
    assert MONITORING_CANDIDATE_DIAGNOSTIC_EVENT in event_types
    assert MONITORING_CANDIDATE_DISPOSITION_EVENT in event_types
    assert MONITORING_REFRESH_HANDOFF_EVENT in event_types


def test_change_receipt_is_not_written_to_observation_receipt_ledger(workspace):
    _, contract, service = workspace

    service.submit_observation(_change_observation(contract.project_id))
    service.submit_observation(
        MonitoringObservation(
            project_id=contract.project_id,
            source_identity=_source(),
            outcome="no_change",
            observed_at=DISCOVERED_AT,
            observer=OBSERVER,
        )
    )

    # 回执账本只承载无变化/未公开/技术失败观察；变化观察的记录在候选事件里
    assert [receipt.outcome for receipt in service.observation_receipts()] == ["no_change"]


# ── 服务构造合同与防篡改边界 ───────────────────────────────────────────────


def test_invalid_recovery_limit_rejected(tmp_path: Path):
    project_root, _ = _build_project(tmp_path)
    with pytest.raises(MonitoringServiceError):
        MonitoringService(project_root, recovery_attempt_limit=0)


def test_domain_contract_rejects_handoff_without_refresh_decision(workspace):
    """未处置候选携带交接单：§17.3 合同在构造边界拒绝（防篡改）。"""

    _, contract, service = workspace
    receipt = service.submit_observation(_change_observation(contract.project_id))
    candidate = service.load(receipt.candidate_id)
    handoff_payload = {
        "handoff_id": "monitoring-refresh_" + "e" * 24,
        "candidate_id": candidate.candidate_id,
        "dedupe_digest": candidate.dedupe_digest,
        "project_id": candidate.project_id,
        "project_contract_version": 1,
        "source_identity": candidate.source_identity.model_dump(mode="json"),
        "suggested_review_scope_zh": "建议复核 A 报告；刷新时仍需重新核验。",
        "created_at": HANDOFF_AT.isoformat(),
    }

    with pytest.raises(ValueError):
        MonitoringChangeCandidate.model_validate(
            candidate.model_dump(mode="json") | {"refresh_handoff": handoff_payload}
        )
