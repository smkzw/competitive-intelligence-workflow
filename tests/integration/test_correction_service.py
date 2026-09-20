"""Task 9.1 修订服务生命周期：绑定、验证处置、所有者决定与幂等发布。

验收计划对应 PRD：六态迁移全部经既有 revision_approval 声明边与守卫；
验证动作不能写入批准；发布前置条件（新快照、重建、独立质控）缺一失败
关闭；历史追加保存，重复提交/批准/发布不重复创建版本或产物。
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from ci_workflow.application.correction_service import (
    CorrectionAttachment,
    CorrectionBindingError,
    CorrectionNotFoundError,
    CorrectionOwnerError,
    CorrectionProposal,
    CorrectionPublishError,
    CorrectionService,
    CorrectionServiceError,
    CorrectionStateError,
    state_progress_zh,
)
from ci_workflow.domain.contracts import ProjectContract
from ci_workflow.domain.enums import OutputFormat, ReportKind, RevisionApprovalState
from ci_workflow.domain.ids import stable_id
from ci_workflow.storage.event_store import EventStore
from ci_workflow.storage.migrations import apply_migrations, persist_project_contract
from ci_workflow.storage.snapshot_store import SnapshotStore, compute_locked_snapshot

_NOW = datetime(2026, 8, 31, 10, 0, tzinfo=UTC)
_TARGET_ID = stable_id("claim", "correction-target")
_SECOND_TARGET_ID = stable_id("claim", "correction-target-2")


def _persist_lineage(root: Path) -> None:
    """登记项目合同版本：修订表与快照表的血统守卫要求项目已确立。"""
    persist_project_contract(
        root / "state" / "project.sqlite",
        ProjectContract(
            contract_version=1,
            project_id="p1",
            indication="特应性皮炎",
            reports=(ReportKind.A,),
            outputs=(OutputFormat.HTML,),
            timezone="Asia/Shanghai",
            data_cutoff=datetime(2026, 8, 1, tzinfo=UTC),
            cutoff_was_user_supplied=True,
            created_at=datetime(2026, 8, 1, tzinfo=UTC),
        ),
    )


def _manifest(
    version: str, created_at: str, *, claim_snapshot: str, claims: tuple[str, ...]
) -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "project_id": "p1",
        "contract_version": 1,
        "report": "A",
        "report_version": version,
        "data_cutoff": "2026-08-01T00:00:00+00:00",
        "evidence_snapshot_id": "evd-1",
        "claim_snapshot_id": claim_snapshot,
        "coverage_set_id": "cov-1",
        "claim_ids": list(claims),
        "created_at": created_at,
    }


def _prepare_project(root: Path) -> tuple[str, dict[str, object]]:
    """锁定 v1 报告快照并登记 SQLite 版本行，返回（快照摘要, 清单）。"""
    manifest = _manifest(
        "v1",
        "2026-08-01T08:00:00+00:00",
        claim_snapshot="claim-snap-1",
        claims=(_TARGET_ID, "c2"),
    )
    locked = SnapshotStore(root).lock_report_snapshot(report="A", manifest=manifest)
    apply_migrations(root / "state" / "project.sqlite")
    _persist_lineage(root)
    with sqlite3.connect(root / "state" / "project.sqlite") as database:
        database.execute(
            """
            INSERT INTO report_snapshots (
                snapshot_id, project_id, report_kind, report_version,
                evidence_state, manifest_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                locked.snapshot_id,
                "p1",
                "A",
                "v1",
                "snapshot_locked",
                json.dumps(manifest, ensure_ascii=False, sort_keys=True),
                "2026-08-01T08:00:00+00:00",
            ),
        )
    raw = (root / "snapshots" / "reports" / "A" / f"{locked.snapshot_id}.json").read_bytes()
    return hashlib.sha256(raw).hexdigest(), manifest


def _submit_kwargs(snapshot_id: str, snapshot_sha256: str) -> dict[str, Any]:
    return {
        "project_id": "p1",
        "report": "A",
        "snapshot_id": snapshot_id,
        "snapshot_sha256": snapshot_sha256,
        "target_type": "claim",
        "target_id": _TARGET_ID,
        "current_visible_value": "客观缓解率 62%",
        "proposed_value": "客观缓解率 58%",
        "rationale_zh": "正文表格与图示数值不一致，应以论文表格为准。",
        "submitted_by": "医学经理-张三",
        "report_owner_id": "医学经理-张三",
        "attachments": (CorrectionAttachment(label="论文表格截图", url="https://example.org/t1"),),
        "occurred_at": _NOW,
    }


def _publish_materials(
    manifest: dict[str, object],
) -> tuple[dict[str, Any], tuple[dict[str, str], ...], dict[str, str]]:
    new_manifest = dict(manifest)
    new_manifest.update(
        {
            "report_version": "v2",
            "claim_snapshot_id": "claim-snap-2",
            "claim_ids": [_TARGET_ID, _SECOND_TARGET_ID, "c2-corrected"],
            "created_at": "2026-08-31T09:00:00+00:00",
        }
    )
    artifacts = ({"artifact_id": "artifact-1", "sha256": "a" * 64},)
    candidate = compute_locked_snapshot(kind="report", report="A", manifest=new_manifest)
    qc = {
        "qc_verdict_id": "qc-verdict-1",
        "qc_result": "accepted",
        "reviewer_id": "独立质控-李四",
        "qc_checked_at": "2026-08-31T14:30:00+00:00",
        "reviewed_snapshot_id": candidate.snapshot_id,
        "reviewed_snapshot_content_digest": candidate.sha256,
    }
    return new_manifest, artifacts, qc


def _prepare_approved_correction(
    root: Path,
) -> tuple[CorrectionService, CorrectionProposal, dict[str, object]]:
    """建立一个等待发布的批准建议，供失败关闭边界逐项验证。"""
    snapshot_sha256, manifest = _prepare_project(root)
    service = CorrectionService(root)
    snapshot_id = next((root / "snapshots" / "reports" / "A").glob("*.json")).stem
    proposal = service.submit(**_submit_kwargs(snapshot_id, snapshot_sha256))
    service.validate(
        proposal.proposal_id,
        outcome="passed",
        disposition_reason_zh="来源、定位、冲突与影响范围均已核清。",
        validated_by="调研代理",
        occurred_at=datetime(2026, 8, 31, 13, 0, tzinfo=UTC),
        impact_set=(_TARGET_ID,),
    )
    approved = service.record_owner_decision(
        proposal.proposal_id,
        decision="approve",
        decided_by="医学经理-张三",
        reason_zh="核对来源后同意修订。",
        occurred_at=datetime(2026, 8, 31, 14, 0, tzinfo=UTC),
    )
    return service, approved, manifest


def test_passed_validation_requires_every_check_and_impact_scope(tmp_path: Path) -> None:
    root = tmp_path / "项目"
    root.mkdir()
    snapshot_sha256, _ = _prepare_project(root)
    service = CorrectionService(root)
    snapshot_id = next((root / "snapshots" / "reports" / "A").glob("*.json")).stem
    proposal = service.submit(**_submit_kwargs(snapshot_id, snapshot_sha256))

    for missing in (
        "identity_verified",
        "context_located",
        "locator_verified",
        "conflicts_checked",
        "impact_checked",
    ):
        checks = {
            "identity_verified": True,
            "context_located": True,
            "locator_verified": True,
            "conflicts_checked": True,
            "impact_checked": True,
        }
        checks[missing] = False
        with pytest.raises(CorrectionStateError):
            service.validate(
                proposal.proposal_id,
                outcome="passed",
                disposition_reason_zh="核验尚未完整。",
                validated_by="调研代理",
                occurred_at=_NOW,
                impact_set=(_TARGET_ID,),
                identity_verified=checks["identity_verified"],
                context_located=checks["context_located"],
                locator_verified=checks["locator_verified"],
                conflicts_checked=checks["conflicts_checked"],
                impact_checked=checks["impact_checked"],
            )
    with pytest.raises(CorrectionStateError):
        service.validate(
            proposal.proposal_id,
            outcome="passed",
            disposition_reason_zh="影响范围尚未确认。",
            validated_by="调研代理",
            occurred_at=_NOW,
        )
    assert service.load(proposal.proposal_id).state == RevisionApprovalState.SUBMITTED.value


def test_submit_rejects_non_stable_target_id(tmp_path: Path) -> None:
    root = tmp_path / "项目"
    root.mkdir()
    snapshot_sha256, _ = _prepare_project(root)
    service = CorrectionService(root)
    snapshot_id = next((root / "snapshots" / "reports" / "A").glob("*.json")).stem
    with pytest.raises(CorrectionBindingError, match="稳定标识"):
        service.submit(
            **{
                **_submit_kwargs(snapshot_id, snapshot_sha256),
                "target_id": "claim-stable-1",
            }
        )


def test_publish_rejects_unaccepted_or_non_independent_qc_and_bad_manifest(
    tmp_path: Path,
) -> None:
    root = tmp_path / "项目"
    root.mkdir()
    service, approved, manifest = _prepare_approved_correction(root)
    new_manifest, artifacts, qc = _publish_materials(manifest)
    proposal_id = approved.proposal_id
    snapshot_dir = root / "snapshots" / "reports" / "A"
    initial_files = {path.name for path in snapshot_dir.glob("*.json")}

    rejected_qc = {**qc, "qc_result": "rejected"}
    owner_qc = {**qc, "reviewer_id": "医学经理-张三"}
    unbound_qc = {**qc, "reviewed_snapshot_id": "other-snapshot"}
    naive_qc_time = {**qc, "qc_checked_at": "2026-08-31T14:30:00"}
    wrong_project = {**new_manifest, "project_id": "p2"}
    skipped_version = {**new_manifest, "report_version": "v9"}
    for materials in (
        {"new_snapshot_manifest": new_manifest, "independent_qc": rejected_qc},
        {"new_snapshot_manifest": new_manifest, "independent_qc": owner_qc},
        {"new_snapshot_manifest": new_manifest, "independent_qc": unbound_qc},
        {"new_snapshot_manifest": new_manifest, "independent_qc": naive_qc_time},
        {"new_snapshot_manifest": wrong_project, "independent_qc": qc},
        {"new_snapshot_manifest": skipped_version, "independent_qc": qc},
    ):
        with pytest.raises(CorrectionPublishError):
            service.publish(
                proposal_id,
                rebuilt_artifacts=artifacts,
                occurred_at=_NOW,
                **materials,
            )

    assert service.load(proposal_id).state == RevisionApprovalState.APPROVED.value
    assert {path.name for path in snapshot_dir.glob("*.json")} == initial_files


def test_current_snapshot_accepts_a_second_correction_after_publish(tmp_path: Path) -> None:
    root = tmp_path / "项目"
    root.mkdir()
    service, approved, manifest = _prepare_approved_correction(root)
    new_manifest, artifacts, qc = _publish_materials(manifest)
    published = service.publish(
        approved.proposal_id,
        new_snapshot_manifest=new_manifest,
        rebuilt_artifacts=artifacts,
        independent_qc=qc,
        occurred_at=datetime(2026, 8, 31, 15, 0, tzinfo=UTC),
    )
    assert published.published_version is not None
    snapshot_id = published.published_version.snapshot_id
    raw = (root / "snapshots" / "reports" / "A" / f"{snapshot_id}.json").read_bytes()

    second = service.submit(
        **{
            **_submit_kwargs(snapshot_id, hashlib.sha256(raw).hexdigest()),
            "target_id": _SECOND_TARGET_ID,
            "current_visible_value": "客观缓解率 41%",
            "proposed_value": "客观缓解率 44%",
        }
    )
    assert second.state == RevisionApprovalState.SUBMITTED.value
    assert second.snapshot_id == snapshot_id


def test_add_evidence_retry_recovers_transition_after_interruption(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "项目"
    root.mkdir()
    snapshot_sha256, _ = _prepare_project(root)
    service = CorrectionService(root)
    snapshot_id = next((root / "snapshots" / "reports" / "A").glob("*.json")).stem
    proposal = service.submit(**_submit_kwargs(snapshot_id, snapshot_sha256))
    service.validate(
        proposal.proposal_id,
        outcome="needs_evidence",
        disposition_reason_zh="需要补充来源页码。",
        validated_by="调研代理",
        occurred_at=_NOW,
    )
    original_transition = service._transition

    def interrupt_transition(**_: Any) -> None:
        raise RuntimeError("模拟追加记录写入后中断")

    monkeypatch.setattr(service, "_transition", interrupt_transition)
    with pytest.raises(RuntimeError, match="模拟"):
        service.add_evidence(
            proposal.proposal_id,
            note_zh="补充论文表格第 5 页定位。",
            recorded_by="医学经理-张三",
            occurred_at=datetime(2026, 8, 31, 12, 0, tzinfo=UTC),
        )
    monkeypatch.setattr(service, "_transition", original_transition)
    recovered = service.add_evidence(
        proposal.proposal_id,
        note_zh="补充论文表格第 5 页定位。",
        recorded_by="医学经理-张三",
        occurred_at=datetime(2026, 8, 31, 12, 0, tzinfo=UTC),
    )
    assert recovered.state == RevisionApprovalState.SUBMITTED.value
    assert len(recovered.source_records) == 1


def test_published_recovery_rejects_different_materials_for_same_approval(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "项目"
    root.mkdir()
    service, approved, manifest = _prepare_approved_correction(root)
    new_manifest, artifacts, qc = _publish_materials(manifest)
    monkeypatch.setattr(service, "_claim", lambda **_: False)
    published = service.publish(
        approved.proposal_id,
        new_snapshot_manifest=new_manifest,
        rebuilt_artifacts=artifacts,
        independent_qc=qc,
        occurred_at=datetime(2026, 8, 31, 15, 0, tzinfo=UTC),
    )
    assert published.published_version is not None
    files_before = {
        path.name for path in (root / "snapshots" / "reports" / "A").glob("*.json")
    }

    changed_manifest = {
        **new_manifest,
        "claim_snapshot_id": "claim-snap-different",
        "claim_ids": [_TARGET_ID, _SECOND_TARGET_ID, "another-change"],
    }
    changed_candidate = compute_locked_snapshot(
        kind="report", report="A", manifest=changed_manifest
    )
    changed_qc = {
        **qc,
        "reviewed_snapshot_id": changed_candidate.snapshot_id,
        "reviewed_snapshot_content_digest": changed_candidate.sha256,
    }
    with pytest.raises(CorrectionPublishError, match="另一份发布结果"):
        service.publish(
            approved.proposal_id,
            new_snapshot_manifest=changed_manifest,
            rebuilt_artifacts=artifacts,
            independent_qc=changed_qc,
            occurred_at=datetime(2026, 8, 31, 16, 0, tzinfo=UTC),
        )
    assert {
        path.name for path in (root / "snapshots" / "reports" / "A").glob("*.json")
    } == files_before


def test_correction_service_lifecycle() -> None:
    """一个顶层测试节点覆盖：提交绑定、验证处置、所有者决定、幂等发布与恢复。"""
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "项目"
        root.mkdir(parents=True)
        snapshot_sha256, manifest = _prepare_project(root)
        service = CorrectionService(root)
        snapshot_files = list((root / "snapshots" / "reports" / "A").glob("*.json"))
        snapshot_id = snapshot_files[0].stem
        store = EventStore(root)

        # ── 子用例 1：提交与项目/当前快照绑定 ────────────────────────────
        proposal = service.submit(**_submit_kwargs(snapshot_id, snapshot_sha256))
        if proposal.state != RevisionApprovalState.SUBMITTED.value:
            failures.append("子用例1：首次提交后状态不是 submitted")
        replay = service.submit(
            **{
                **_submit_kwargs(snapshot_id, snapshot_sha256),
                "occurred_at": datetime(2026, 8, 31, 11, 0, tzinfo=UTC),
            }
        )
        if (
            replay.proposal_id != proposal.proposal_id
            or replay.submitted_at != proposal.submitted_at
        ):
            failures.append("子用例1：重复提交未返回既有建议或改写了首次提交时间")
        try:
            service.submit(**{**_submit_kwargs(snapshot_id, "f" * 64), "occurred_at": _NOW})
            failures.append("子用例1：摘要不一致的快照绑定未被拒绝")
        except CorrectionBindingError:
            pass
        stale_manifest = _manifest(
            "v0", "2026-07-01T08:00:00+00:00", claim_snapshot="claim-snap-0", claims=("c0",)
        )
        stale_locked = SnapshotStore(root).lock_report_snapshot(report="A", manifest=stale_manifest)
        stale_raw = (
            root / "snapshots" / "reports" / "A" / f"{stale_locked.snapshot_id}.json"
        ).read_bytes()
        try:
            service.submit(
                **_submit_kwargs(stale_locked.snapshot_id, hashlib.sha256(stale_raw).hexdigest())
            )
            failures.append("子用例1：未绑定当前最新快照的建议未被拒绝")
        except CorrectionBindingError:
            pass
        try:
            service.submit(**{**_submit_kwargs(snapshot_id, snapshot_sha256), "project_id": "p2"})
            failures.append("子用例1：跨项目修订包未被拒绝")
        except CorrectionBindingError:
            pass

        # ── 子用例 2：验证处置——需补证据，且验证不能写入批准 ─────────────
        validated = service.validate(
            proposal.proposal_id,
            outcome="needs_evidence",
            disposition_reason_zh="来源身份可核，但缺少与现行声明冲突的定位证据。",
            validated_by="调研代理",
            occurred_at=_NOW,
            conflicts=("图示数值与表格数值不一致",),
            impact_set=(_TARGET_ID, stable_id("chart-point", "correction-target")),
        )
        if validated.state != RevisionApprovalState.NEEDS_EVIDENCE.value:
            failures.append("子用例2：needs_evidence 处置后状态不是 needs_evidence")
        try:
            service.publish(
                proposal.proposal_id,
                new_snapshot_manifest={},
                rebuilt_artifacts=(),
                independent_qc={},
                occurred_at=_NOW,
            )
            failures.append("子用例2：未批准的建议未被发布拒绝")
        except CorrectionStateError:
            pass

        # ── 子用例 3：补证据回到 submitted，原提交历史不覆盖 ─────────────
        before_events = store.read_all()
        evidenced = service.add_evidence(
            proposal.proposal_id,
            note_zh="补充论文表格第 5 页定位与 DOI 链接。",
            recorded_by="医学经理-张三",
            occurred_at=datetime(2026, 8, 31, 12, 0, tzinfo=UTC),
            source_refs=(CorrectionAttachment(label="论文 DOI", url="https://doi.org/10.1000/a1"),),
        )
        if evidenced.state != RevisionApprovalState.SUBMITTED.value:
            failures.append("子用例3：补证据后状态未回到 submitted")
        if len(evidenced.source_records) != 1 or len(evidenced.validations) != 1:
            failures.append("子用例3：追加历史不完整，原提交或验证记录被覆盖")
        after_events = store.read_all()
        if len(after_events) <= len(before_events):
            failures.append("子用例3：补证据没有追加新事件")
        prefix = [event.event_digest for event in before_events]
        if [event.event_digest for event in after_events[: len(prefix)]] != prefix:
            failures.append("子用例3：既有事件被改写")

        # ── 子用例 4：验证通过进入等待批准，但绝不等于批准 ───────────────
        passed = service.validate(
            proposal.proposal_id,
            outcome="passed",
            disposition_reason_zh="来源身份、上下文、定位与冲突核验通过，影响范围已确认。",
            validated_by="调研代理",
            occurred_at=datetime(2026, 8, 31, 13, 0, tzinfo=UTC),
            conflicts=("图示数值与表格数值不一致",),
            impact_set=(_TARGET_ID, stable_id("chart-point", "correction-target")),
        )
        if passed.state != RevisionApprovalState.VALIDATED_PENDING_USER_APPROVAL.value:
            failures.append("子用例4：验证通过后未进入等待用户批准状态")
        if passed.owner_decision is not None:
            failures.append("子用例4：验证动作写入了所有者决定")

        # ── 子用例 5：只有报告所有者能决定；决定可精确重放 ────────────────
        try:
            service.record_owner_decision(
                proposal.proposal_id,
                decision="approve",
                decided_by="非所有者-王五",
                reason_zh="同意采纳。",
                occurred_at=_NOW,
            )
            failures.append("子用例5：非报告所有者的批准被接受")
        except CorrectionOwnerError:
            pass
        approved = service.record_owner_decision(
            proposal.proposal_id,
            decision="approve",
            decided_by="医学经理-张三",
            reason_zh="核对来源后同意修订。",
            occurred_at=datetime(2026, 8, 31, 14, 0, tzinfo=UTC),
        )
        if approved.state != RevisionApprovalState.APPROVED.value:
            failures.append("子用例5：所有者批准后状态不是 approved")
        if not approved.publish_idempotency_key or approved.owner_decision is None:
            failures.append("子用例5：批准记录或发布幂等键缺失")
        approvals_path = root / "state" / "approvals.jsonl"
        decision = approved.owner_decision
        approval_id = decision.approval_id if decision is not None else None
        if (
            not approvals_path.is_file()
            or approval_id is None
            or approval_id not in approvals_path.read_text(encoding="utf-8")
        ):
            failures.append("子用例5：批准未进入审批账本")
        replayed_decision = service.record_owner_decision(
            proposal.proposal_id,
            decision="approve",
            decided_by="医学经理-张三",
            reason_zh="核对来源后同意修订。",
            occurred_at=datetime(2026, 8, 31, 14, 0, tzinfo=UTC),
        )
        if replayed_decision.state != RevisionApprovalState.APPROVED.value:
            failures.append("子用例5：批准的精确重放改变了状态")
        decisions = store.read_all()
        approve_events = [
            event for event in decisions if event.idempotency_key.startswith("correction.approve:")
        ]
        if len(approve_events) != 1:
            failures.append("子用例5：重复批准产生了重复审批事件")

        # ── 子用例 6：发布前置条件缺一失败关闭，批准状态保留 ─────────────
        new_manifest, artifacts, qc = _publish_materials(manifest)
        events_before_failures = len(store.read_all())
        for label, kwargs in (
            (
                "重建记录",
                {
                    "new_snapshot_manifest": new_manifest,
                    "rebuilt_artifacts": (),
                    "independent_qc": qc,
                },
            ),
            (
                "独立质控",
                {
                    "new_snapshot_manifest": new_manifest,
                    "rebuilt_artifacts": artifacts,
                    "independent_qc": {
                        "qc_verdict_id": "v",
                        "qc_result": "rejected",
                        "reviewer_id": "独立质控-李四",
                        "qc_checked_at": "2026-08-31T14:30:00+00:00",
                        "reviewed_snapshot_id": "snapshot-unbound",
                        "reviewed_snapshot_content_digest": "b" * 64,
                    },
                },
            ),
            (
                "新快照",
                {
                    "new_snapshot_manifest": dict(manifest),
                    "rebuilt_artifacts": artifacts,
                    "independent_qc": qc,
                },
            ),
        ):
            try:
                service.publish(proposal.proposal_id, occurred_at=_NOW, **kwargs)
                failures.append(f"子用例6：缺少{label}的发布未被拒绝")
            except CorrectionPublishError:
                pass
        if service.load(proposal.proposal_id).state != RevisionApprovalState.APPROVED.value:
            failures.append("子用例6：发布失败后批准状态未保留")
        failure_events = [
            event for event in store.read_all() if event.event_type == "correction.publish.failed"
        ]
        if len(failure_events) != 3 or len(store.read_all()) - events_before_failures != len(
            failure_events
        ):
            failures.append("子用例6：发布失败原因未按幂等方式完整入账")

        # ── 子用例 7：发布成功登记新版本；重复发布不重复创建 ─────────────
        old_snapshot_bytes = (
            root / "snapshots" / "reports" / "A" / f"{snapshot_id}.json"
        ).read_bytes()
        published = service.publish(
            proposal.proposal_id,
            new_snapshot_manifest=new_manifest,
            rebuilt_artifacts=artifacts,
            independent_qc=qc,
            occurred_at=datetime(2026, 8, 31, 15, 0, tzinfo=UTC),
        )
        if published.state != RevisionApprovalState.PUBLISHED.value:
            failures.append("子用例7：发布后状态不是 published")
        version = published.published_version
        if version is None or version.report_version != "v2":
            failures.append("子用例7：发布未登记 v2 新版本")
        if version is not None and version.supersedes_snapshot_id != snapshot_id:
            failures.append("子用例7：新版本缺少与旧版本的取代关系")
        with sqlite3.connect(root / "state" / "project.sqlite") as database:
            rows = database.execute(
                "SELECT snapshot_id, report_version FROM report_snapshots ORDER BY report_version"
            ).fetchall()
        versions = sorted(str(row[1]) for row in rows)
        if versions != ["v1", "v2"]:
            failures.append(f"子用例7：版本登记不是 v1+v2 并存：{versions}")
        if (
            root / "snapshots" / "reports" / "A" / f"{snapshot_id}.json"
        ).read_bytes() != old_snapshot_bytes:
            failures.append("子用例7：旧快照文件被改写")
        events_before_replay = store.read_all()
        replayed = service.publish(
            proposal.proposal_id,
            new_snapshot_manifest=new_manifest,
            rebuilt_artifacts=artifacts,
            independent_qc=qc,
            occurred_at=datetime(2026, 8, 31, 15, 0, tzinfo=UTC),
        )
        if replayed.published_version != published.published_version:
            failures.append("子用例7：重复发布返回了不同结果")
        if store.read_all() != events_before_replay:
            failures.append("子用例7：重复发布追加了重复事件")

        # ── 子用例 8：发布中断恢复与投影自愈（事件为真源） ────────────────
        with sqlite3.connect(root / "state" / "project.sqlite") as database:
            database.execute(
                "DELETE FROM correction_proposals WHERE proposal_id = ?", (proposal.proposal_id,)
            )
        recovered = service.load(proposal.proposal_id)
        if (
            recovered.state != RevisionApprovalState.PUBLISHED.value
            or recovered.published_version is None
            or recovered.owner_decision is None
        ):
            failures.append("子用例8：投影丢失后未能从事件流完整重建建议")
        recovered_again = service.publish(
            proposal.proposal_id,
            new_snapshot_manifest=new_manifest,
            rebuilt_artifacts=artifacts,
            independent_qc=qc,
            occurred_at=datetime(2026, 8, 31, 16, 0, tzinfo=UTC),
        )
        if recovered_again.published_version != published.published_version:
            failures.append("子用例8：发布中断恢复返回了不同结果")
        final_version = recovered_again.published_version
        if final_version is None:
            failures.append("子用例8：发布中断恢复后版本记录缺失")
            final_version = published.published_version
        assert final_version is not None
        with sqlite3.connect(root / "state" / "project.sqlite") as database:
            count = database.execute(
                "SELECT COUNT(*) FROM report_snapshots WHERE snapshot_id = ?",
                (final_version.snapshot_id,),
            ).fetchone()
            claim = database.execute(
                "SELECT COUNT(*) FROM idempotency_keys WHERE operation = 'correction.publish'"
            ).fetchone()
        if count is None or int(count[0]) != 1:
            failures.append("子用例8：发布中断恢复重复登记了版本")
        if claim is None or int(claim[0]) != 1:
            failures.append("子用例8：发布幂等键登记不唯一")

        # ── 子用例 9：终态保护、不存在建议与用户可见中文 ─────────────────
        try:
            service.add_evidence(
                proposal.proposal_id,
                note_zh="发布后再补来源。",
                recorded_by="医学经理-张三",
                occurred_at=_NOW,
            )
            failures.append("子用例9：published 终态仍允许追加来源")
        except CorrectionStateError:
            pass
        try:
            service.load("correction-proposal-不存在")
            failures.append("子用例9：不存在的建议未被拒绝")
        except CorrectionNotFoundError:
            pass
        for member in RevisionApprovalState:
            progress = state_progress_zh(member.value)
            if member.value in progress or any(ch.isascii() and ch.isalpha() for ch in progress):
                failures.append(f"子用例9：用户可见进度泄漏内部状态词：{progress}")
        for event in store.read_all():
            if event.event_type == "correction.proposal.submitted":
                exported = json.dumps(event.payload["proposal"], ensure_ascii=False)
                if "工程" in exported or "internal" in exported:
                    failures.append("子用例9：提交合同中出现工程化标签")
        try:
            raise CorrectionServiceError("unused")
        except CorrectionServiceError:
            pass

    if failures:
        raise AssertionError("；".join(failures))
