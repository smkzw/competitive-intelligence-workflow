"""R24-192 已复核 C 来源状态只读投影合同测试。

真实链路（固定 CT.gov 证据、真实摄取与快照、真实登记、真实复核回执与
既有收据授权接受物化；不写手写接受 SQL，不 mock 生产证明）：

- 合法投影只把“精确已登记绑定 + 已物化接受 + 冲突已解决”的观察行
  ``review_state`` 翻为 accepted；其余行（包括来源已接受但未登记的行）与
  所有非 ``review_state`` 字段逐字节不变；
- 未物化接受、错误快照/回执/决策记录、篡改原始报告取值、替换行来源版本、
  缺失观察行、篡改锁定快照均失败关闭，且失败不隐式接受候选原子；
- 未解决冲突行保持候选与显式冲突处置，来源范围与披露字段不变；
- 投影不改原始报告文件、数据库逻辑内容、事件流、决策记录、既有站点与
  current；重复投影幂等；
- 即使来源事实已接受，普通待复核渲染仍标记 unreviewed_candidate。
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from ci_workflow.application.c_portal_consumer_registry import (
    CPortalReviewedProjectionError,
    project_reviewed_c_source_states,
    register_c_source_consumers,
)
from ci_workflow.application.fresh_research_primitives import ResearchClaim, ResearchFact
from ci_workflow.application.latest_delivery import read_current_delivery
from ci_workflow.application.project_service import verify_project_workspace
from ci_workflow.application.review_issuer import ExternalProcessResult, issue_review_receipt
from ci_workflow.application.scientific_review_transition import (
    build_scientific_review_context,
    capture_portal_artifact_binding,
    load_scientific_review_receipt,
    publish_production_context,
    publish_scientific_review_request,
)
from ci_workflow.application.source_fact_acceptance import (
    accept_reviewed_source_facts,
    source_fact_acceptance_decision_path,
)
from ci_workflow.application.source_research_service import SourceCapture
from ci_workflow.domain.enums import FactReviewState
from ci_workflow.domain.ids import stable_id
from ci_workflow.gates.models import ConflictDisposition
from ci_workflow.hosts.receipt import HostExecutableEvidence, HostSessionBinding
from ci_workflow.qc.scientific import ScientificQcReviewBundle, ScientificQcVerdict
from ci_workflow.renderers.portal.report_c import (
    ReportCPortalData,
    render_report_c_review_candidate,
)
from ci_workflow.storage.snapshot_store import LockedSnapshot, SnapshotStore
from tests.integration.test_r24_c_source_consumers import (
    _AT,
    _CUTOFF,
    _INDICATION,
    _PRODUCTS,
    _TRIALS,
    _raw,
)
from tests.integration.test_r24_ctgov_c_design_projection import _CAS_ROOT, _full_bindings
from tools.materialize_ctgov_c_candidate import materialize

_PRODUCED_AT = datetime(2026, 10, 3, 1, 0, tzinfo=UTC)
_REVIEW_STARTED_AT = datetime(2026, 10, 3, 2, 0, tzinfo=UTC)
_REVIEW_FINISHED_AT = datetime(2026, 10, 3, 2, 30, tzinfo=UTC)
_ISSUED_AT = datetime(2026, 10, 3, 3, 0, tzinfo=UTC)
_CHECKED_AT = datetime(2026, 10, 3, 4, 0, tzinfo=UTC)
_VALID_UNTIL = datetime(2099, 1, 1, tzinfo=UTC)

_HOST_PATH = "/opt/homebrew/bin/codex"
_REVIEW_ARGV = ("exec", "scientific-review")
_REVIEW_SESSION = HostSessionBinding(
    session_id="review-session-9", launcher_pid=777, launcher_parent_pid=1
)
_HOST_EXECUTABLE = HostExecutableEvidence(
    provenance="path_resolved",
    path=_HOST_PATH,
    resolved_realpath=_HOST_PATH,
    version="codex-cli 0.42.0",
)
_VERDICT_RELATIVE = "receipts/scientific_review/C/verdict.json"
_PORTAL_MANIFEST = "reports/C/review-candidate/html.manifest.json"
_PORTAL_SITE = "reports/C/review-candidate/html"

_DIRECT = "c-nct02264639-sample-size"
_SUBSET_ROWS = (
    "c-nct02264639-population",
    "c-nct02264639-inclusion",
    _DIRECT,
    "c-nct02264639-arm-0-label",
    "c-nct02264639-pri0-definition",
)
_LOGICAL_TABLES = (
    "claim_facts",
    "claim_versions",
    "conflict_sets",
    "evidence_fragments",
    "fact_evidence",
    "fact_versions",
    "idempotency_keys",
    "source_portal_consumer_bindings",
    "source_versions",
)


@dataclass(frozen=True)
class _ReviewedCWorld:
    root: Path
    snapshot: LockedSnapshot
    report: ReportCPortalData
    report_path: Path
    site: Path
    versions: Mapping[str, str]
    claim_snapshot_id: str


def _with_open_conflict(report: ReportCPortalData, row_id: str) -> ReportCPortalData:
    payload = report.model_dump(mode="json")
    matched = False
    for item in payload["observations"]:
        if item["row_id"] == row_id:
            item["conflict_disposition"] = ConflictDisposition.OPEN_CONFLICT_PRESERVED.value
            matched = True
    assert matched, f"固定候选缺少观察行：{row_id}"
    return ReportCPortalData.model_validate(payload)


def _review_verdict(context: Any) -> ScientificQcVerdict:
    bundle = ScientificQcReviewBundle(
        **{
            key: value
            for key, value in context.model_dump().items()
            if key in ScientificQcReviewBundle.model_fields
        }
    )
    return ScientificQcVerdict(
        criteria_version=context.criteria_version,
        verdict_id="verdict-independent-1",
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
        reviewed_at=_REVIEW_FINISHED_AT,
        valid_until=_VALID_UNTIL,
    )


def _issue_c_receipt(root: Path, context: Any) -> None:
    def _runner(argv: tuple[str, ...], cwd: str, timeout: float) -> ExternalProcessResult:
        assert argv == (_HOST_PATH, *_REVIEW_ARGV)
        assert cwd == str(root)
        assert timeout > 0
        verdict_path = root / _VERDICT_RELATIVE
        verdict_path.parent.mkdir(parents=True, exist_ok=True)
        verdict_path.write_text(
            json.dumps(_review_verdict(context).model_dump(mode="json"), ensure_ascii=False),
            encoding="utf-8",
        )
        return ExternalProcessResult(
            pid=4242,
            argv=argv,
            cwd=cwd,
            started_at=_REVIEW_STARTED_AT,
            finished_at=_REVIEW_FINISHED_AT,
            returncode=0,
            stdout_tail="SCIENTIFIC_REVIEW_DONE verdict=accepted\n",
            stderr_tail="",
        )

    issue_review_receipt(
        project_root=root,
        report_kind="C",
        reviewer_id="independent-reviewer",
        review_session_id="review-session-9",
        host="codex",
        host_executable=_HOST_EXECUTABLE,
        review_argv=_REVIEW_ARGV,
        verdict_relative_path=_VERDICT_RELATIVE,
        session=_REVIEW_SESSION,
        runner=_runner,
        clock=lambda: _ISSUED_AT,
    )


def _build_reviewed_c_world(
    tmp_path: Path,
    *,
    registered_rows: Sequence[str] | None = None,
    open_conflict_row: str | None = None,
    accepted: bool = True,
) -> _ReviewedCWorld:
    output = tmp_path / "c-source-candidate"
    manifest = materialize(
        source_root=_CAS_ROOT,
        raw_asset=_raw(),
        output=output,
        bindings=_full_bindings(),
        indication_id="pnh",
        indication=_INDICATION,
        cutoff=_CUTOFF,
        observed_at=_AT,
    )
    project = output / "project"
    snapshot = LockedSnapshot.model_validate(manifest["snapshot"])
    projection = json.loads((output / "projection.json").read_text(encoding="utf-8"))
    inputs = json.loads((output / "inputs.json").read_text(encoding="utf-8"))
    captures = {
        item["source_id"]: SourceCapture.model_validate(item) for item in inputs["sources"]
    }
    contract = verify_project_workspace(project).contract
    report = ReportCPortalData(
        schema_version="1.0",
        report_version="r24-c-reviewed-projection-test",
        indication_id="pnh",
        indication=contract.indication,
        data_cutoff=contract.data_cutoff,
        products=_PRODUCTS,
        trials=_TRIALS,
        observations=tuple(projection["observations"]),
    )
    if open_conflict_row is not None:
        report = _with_open_conflict(report, open_conflict_row)
    report_path = output / "review-portal-data.json"
    report_path.write_text(report.model_dump_json(), encoding="utf-8")
    site = project / _PORTAL_SITE
    render_report_c_review_candidate(
        report, site, publication_limitation_zh="测试候选：仅用于投影合同验证。"
    )
    (project / _PORTAL_MANIFEST).write_text(
        '{"kind":"artifact-manifest"}\n', encoding="utf-8"
    )
    versions = {str(key): str(value) for key, value in manifest["fact_version_by_ref"].items()}
    requested = (
        dict(versions)
        if registered_rows is None
        else {row_id: versions[row_id] for row_id in registered_rows}
    )
    register_c_source_consumers(
        project, snapshot, report, requested, captures, registered_at=_AT
    )

    payload = SnapshotStore(project).read(snapshot)
    closure = payload["closure"]
    typed_captures = tuple(
        SourceCapture.model_validate(item["capture"]) for item in closure["sources"]
    )
    typed_facts = tuple(
        ResearchFact.model_validate(
            {**item["fact"], "row_ref": item["consumer_binding"]["row_ref"]}
        )
        for item in closure["facts"]
    )
    typed_claims = tuple(
        ResearchClaim.model_validate(item["claim"]) for item in closure["claims"]
    )
    claim_snapshot_id = stable_id(
        "claim-snapshot",
        contract.project_id,
        payload["scientific_content_digest"],
        *sorted(item["claim_version_id"] for item in closure["claims"]),
    )
    coverage_set_id = stable_id(
        "coverage-set", contract.project_id, "C", snapshot.snapshot_id, claim_snapshot_id
    )
    context = build_scientific_review_context(
        project_id=contract.project_id,
        report_kind="C",
        report_version="review-candidate",
        producer_id="codex-ci-owner",
        candidate_snapshot_id=snapshot.snapshot_id,
        candidate_content_digest=payload["scientific_content_digest"],
        criteria_version="C-projection-v1",
        gate_result_key="projection-gate-1",
        contract_version=str(payload["contract_version"]),
        coverage_set_id=coverage_set_id,
        evidence_snapshot_id=snapshot.snapshot_id,
        claim_snapshot_id=claim_snapshot_id,
        sources=typed_captures,
        facts=typed_facts,
        claims=typed_claims,
        fact_version_by_ref={
            item["fact"]["fact_id"]: item["fact_version_id"] for item in closure["facts"]
        },
    )
    publish_production_context(project, "C", context)
    publish_scientific_review_request(
        project,
        "C",
        context,
        producer_session_id="producer-session-1",
        produced_at=_PRODUCED_AT,
        portal_binding=capture_portal_artifact_binding(
            project, "C", manifest_relative=_PORTAL_MANIFEST, site_relative=_PORTAL_SITE
        ),
    )
    _issue_c_receipt(project, context)
    if accepted:
        accept_reviewed_source_facts(
            project_root=project,
            report_kind="C",
            evidence_snapshot_id=snapshot.snapshot_id,
            claim_snapshot_id=claim_snapshot_id,
            checked_at=_CHECKED_AT,
        )
    return _ReviewedCWorld(
        root=project,
        snapshot=snapshot,
        report=report,
        report_path=report_path,
        site=site,
        versions=versions,
        claim_snapshot_id=claim_snapshot_id,
    )


def _project(world: _ReviewedCWorld, report_path: Path | None = None) -> ReportCPortalData:
    return project_reviewed_c_source_states(
        world.root, world.snapshot, world.report_path if report_path is None else report_path
    )


def _open_readonly(root: Path) -> sqlite3.Connection:
    uri = (root / "state/project.sqlite").resolve().as_uri() + "?mode=ro"
    return sqlite3.connect(uri, uri=True)


def _fact_states(root: Path) -> dict[str, str]:
    database = _open_readonly(root)
    try:
        rows = database.execute(
            "SELECT fact_version_id,review_state FROM fact_versions ORDER BY fact_version_id"
        ).fetchall()
    finally:
        database.close()
    return {str(row[0]): str(row[1]) for row in rows}


def _ledger_keys(root: Path) -> tuple[str, ...]:
    database = _open_readonly(root)
    try:
        rows = database.execute(
            "SELECT idempotency_key FROM idempotency_keys ORDER BY idempotency_key"
        ).fetchall()
    finally:
        database.close()
    return tuple(str(row[0]) for row in rows)


def _logical_database_digest(root: Path) -> str:
    database = _open_readonly(root)
    try:
        payload: dict[str, list[str]] = {}
        for table in _LOGICAL_TABLES:
            rows = database.execute(f"SELECT * FROM {table}").fetchall()
            payload[table] = sorted(str(row) for row in rows)
    finally:
        database.close()
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def _file_digests(root: Path, relative: str) -> dict[str, str]:
    base = root / relative
    if not base.exists():
        return {}
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(base.rglob("*"))
        if path.is_file()
    }


def _database_bytes(root: Path) -> dict[str, str]:
    state = root / "state"
    return {
        name: hashlib.sha256((state / name).read_bytes()).hexdigest()
        for name in ("project.sqlite", "project.sqlite-wal")
        if (state / name).exists()
    }


def _materialized_accepted_versions(root: Path) -> frozenset[str]:
    receipt = load_scientific_review_receipt(root, "C")
    path = root / source_fact_acceptance_decision_path("C", receipt.receipt_digest)
    payload = json.loads(path.read_bytes())
    return frozenset(str(item) for item in payload["accepted_fact_version_ids"])


def test_owner_read_accessor_reuses_acceptance_proof_without_write_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ci_workflow.application import source_fact_acceptance as acceptance

    world = _build_reviewed_c_world(tmp_path, registered_rows=_SUBSET_ROWS)
    # Establish the SQLite read transport before measuring the operation. A
    # first read of a checkpointed WAL-mode DB may create empty coordination
    # sidecars; it must not change main/WAL data or any logical/material evidence.
    before_logical = _logical_database_digest(world.root)
    before = (_database_bytes(world.root), _file_digests(world.root, "events"),
              _file_digests(world.root, "receipts"))

    def forbidden(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("a read accessor must not migrate, write, or append an event")

    monkeypatch.setattr(acceptance, "open_database", forbidden)
    monkeypatch.setattr(acceptance, "apply_migrations", forbidden)
    monkeypatch.setattr(acceptance, "_append_acceptance_event", forbidden)
    loader = acceptance.load_materialized_source_acceptance
    result = loader(project_root=world.root, report_kind="C",
                    evidence_snapshot_id=world.snapshot.snapshot_id)
    assert (frozenset(result.accepted_fact_version_ids)
            == _materialized_accepted_versions(world.root))
    assert result.claim_snapshot_id == world.claim_snapshot_id
    assert loader(project_root=world.root, report_kind="C",
                  evidence_snapshot_id=world.snapshot.snapshot_id) == result
    assert before == (_database_bytes(world.root), _file_digests(world.root, "events"),
                      _file_digests(world.root, "receipts"))
    assert _logical_database_digest(world.root) == before_logical


def test_owner_report_header_cannot_drift_from_locked_project_contract(tmp_path: Path) -> None:
    world = _build_reviewed_c_world(tmp_path, registered_rows=_SUBSET_ROWS)
    for field, value in (("indication", "特应性皮炎"),
                         ("data_cutoff", "2020-01-01T23:59:59+08:00")):
        payload = world.report.model_dump(mode="json")
        payload[field] = value
        forged = tmp_path / f"forged-{field}.json"
        forged.write_text(ReportCPortalData.model_validate(payload).model_dump_json(),
                          encoding="utf-8")
        with pytest.raises(CPortalReviewedProjectionError, match="合同|截止|适应症"):
            _project(world, forged)


def test_legal_projection_flips_only_registered_accepted_rows_and_preserves_everything_else(
    tmp_path: Path,
) -> None:
    world = _build_reviewed_c_world(tmp_path, registered_rows=_SUBSET_ROWS)
    original = ReportCPortalData.model_validate_json(world.report_path.read_bytes())
    accepted_versions = _materialized_accepted_versions(world.root)
    assert {world.versions[row_id] for row_id in _SUBSET_ROWS} <= accepted_versions
    before_report_sha256 = hashlib.sha256(world.report_path.read_bytes()).hexdigest()
    before_database = _logical_database_digest(world.root)
    before_database_bytes = _database_bytes(world.root)
    before_events = _file_digests(world.root, "events")
    before_receipts = _file_digests(world.root, "receipts")
    before_site = _file_digests(world.root, _PORTAL_SITE)

    projected = _project(world)

    assert projected is not original
    assert projected.model_dump(exclude={"observations"}) == original.model_dump(
        exclude={"observations"}
    )
    assert len(projected.observations) == len(original.observations)
    flipped: set[str] = set()
    for before_row, after_row in zip(
        original.observations, projected.observations, strict=True
    ):
        assert after_row.model_dump(exclude={"review_state"}) == before_row.model_dump(
            exclude={"review_state"}
        )
        assert after_row.review_state in {
            FactReviewState.CANDIDATE,
            FactReviewState.ACCEPTED,
        }
        if after_row.review_state is FactReviewState.ACCEPTED:
            assert before_row.review_state is FactReviewState.CANDIDATE
            flipped.add(after_row.row_id)
    # 只有精确“已登记 + 来源已接受”的行被翻转；来源已接受但未登记的 80 行保持候选。
    assert flipped == set(_SUBSET_ROWS)
    assert all(
        row.review_state is FactReviewState.CANDIDATE
        for row in projected.observations
        if row.row_id not in _SUBSET_ROWS
    )
    # 同一输入重复投影幂等。
    assert _project(world) == projected
    # 只读边界：原始报告文件、数据库逻辑内容、事件流、决策记录、既有站点均不变。
    assert hashlib.sha256(world.report_path.read_bytes()).hexdigest() == before_report_sha256
    assert _logical_database_digest(world.root) == before_database
    assert _database_bytes(world.root) == before_database_bytes
    assert _file_digests(world.root, "events") == before_events
    assert _file_digests(world.root, "receipts") == before_receipts
    assert _file_digests(world.root, _PORTAL_SITE) == before_site
    assert read_current_delivery(world.root) is None
    # 普通待复核渲染标记保持候选：来源接受不等于整包接受或 current。
    status = json.loads((world.site / "data/research-status.json").read_bytes())
    assert status["delivery_status"] == "unreviewed_candidate"


def test_projection_fails_closed_without_materialized_acceptance_and_never_accepts(
    tmp_path: Path,
) -> None:
    world = _build_reviewed_c_world(
        tmp_path, registered_rows=_SUBSET_ROWS, accepted=False
    )
    before_states = _fact_states(world.root)
    assert set(before_states.values()) == {"candidate"}
    with pytest.raises(CPortalReviewedProjectionError, match="尚未物化"):
        _project(world)
    # 失败关闭后候选原子未被隐式接受：无状态变化、无决策记录、无幂等台账。
    assert _fact_states(world.root) == before_states
    assert _file_digests(world.root, "receipts/source_fact_acceptance") == {}
    assert _ledger_keys(world.root) == ()
    # 既有接受入口仍然可以正常物化（本投影不替代也不削弱授权链）。
    result = accept_reviewed_source_facts(
        project_root=world.root,
        report_kind="C",
        evidence_snapshot_id=world.snapshot.snapshot_id,
        claim_snapshot_id=world.claim_snapshot_id,
        checked_at=_CHECKED_AT,
    )
    assert len(result.accepted_fact_version_ids) == len(world.versions)
    assert set(_fact_states(world.root).values()) == {"accepted"}


def test_projection_rejects_wrong_snapshot_receipt_report_bytes_and_rows(
    tmp_path: Path,
) -> None:
    world = _build_reviewed_c_world(tmp_path)
    # 错误快照：指向不存在的快照标识，完整性核验失败。
    wrong_snapshot = world.snapshot.model_copy(
        update={"snapshot_id": "evidence-snapshot_" + "0" * 24}
    )
    with pytest.raises(CPortalReviewedProjectionError):
        project_reviewed_c_source_states(world.root, wrong_snapshot, world.report_path)

    original_payload = json.loads(world.report_path.read_bytes())
    # 篡改原始报告取值：绑定行身份与锁定来源不再一致。
    tampered_value = json.loads(json.dumps(original_payload))
    tampered_value["observations"][0]["source_text"] += "（篡改）"
    tampered_value_path = tmp_path / "tampered-value.json"
    tampered_value_path.write_text(json.dumps(tampered_value, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(CPortalReviewedProjectionError):
        _project(world, tampered_value_path)
    # 替换行的来源版本：同一观察行指向另一来源捕获，证明失败。
    swapped = json.loads(json.dumps(original_payload))
    first = swapped["observations"][0]
    other = next(
        item
        for item in swapped["observations"]
        if item["source_version_id"] != first["source_version_id"]
    )
    first["source_version_id"] = other["source_version_id"]
    swapped_path = tmp_path / "tampered-version.json"
    swapped_path.write_text(json.dumps(swapped, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(CPortalReviewedProjectionError):
        _project(world, swapped_path)
    # 缺失已登记观察行：报告副本删除一行后不再能重建该登记绑定。
    missing = json.loads(json.dumps(original_payload))
    missing["observations"].pop(0)
    missing_path = tmp_path / "tampered-missing.json"
    missing_path.write_text(json.dumps(missing, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(CPortalReviewedProjectionError, match="不在原始报告"):
        _project(world, missing_path)

    # 篡改锁定快照文件字节：快照完整性核验失败（随后原样恢复）。
    snapshot_file = world.root / world.snapshot.relative_path
    snapshot_bytes = snapshot_file.read_bytes()
    try:
        snapshot_file.write_bytes(snapshot_bytes[:-1] + b" ")
        with pytest.raises(CPortalReviewedProjectionError):
            _project(world)
    finally:
        snapshot_file.write_bytes(snapshot_bytes)

    # 篡改独立复核回执：内容摘要与字段不再一致，活跃回执不可用（随后原样恢复）。
    receipt_file = world.root / "receipts/scientific_review/C/receipt.json"
    receipt_bytes = receipt_file.read_bytes()
    try:
        receipt_payload = json.loads(receipt_bytes)
        receipt_payload["issued_at"] = "2026-10-03T03:00:01+00:00"
        receipt_file.write_text(
            json.dumps(receipt_payload, ensure_ascii=False), encoding="utf-8"
        )
        with pytest.raises(CPortalReviewedProjectionError):
            _project(world)
    finally:
        receipt_file.write_bytes(receipt_bytes)

    # 篡改已物化接受决策记录：决策字节与幂等台账摘要不一致（最后执行，不恢复）。
    receipt = load_scientific_review_receipt(world.root, "C")
    decision_file = (
        world.root / source_fact_acceptance_decision_path("C", receipt.receipt_digest)
    )
    payload = json.loads(decision_file.read_bytes())
    payload["accepted_fact_version_ids"] = list(payload["accepted_fact_version_ids"])[::-1]
    decision_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(CPortalReviewedProjectionError, match="台账"):
        _project(world)


def test_projection_preserves_open_conflicts_and_source_scope(tmp_path: Path) -> None:
    world = _build_reviewed_c_world(
        tmp_path, registered_rows=_SUBSET_ROWS, open_conflict_row=_DIRECT
    )
    assert world.versions[_DIRECT] in _materialized_accepted_versions(world.root)

    projected = _project(world)

    rows = {row.row_id: row for row in projected.observations}
    originals = {row.row_id: row for row in world.report.observations}
    open_row = rows[_DIRECT]
    original_open = originals[_DIRECT]
    # 未解决冲突行保持候选与显式冲突处置：不得被来源接受升级为已接受设计事实。
    assert open_row.review_state is FactReviewState.CANDIDATE
    assert open_row.conflict_disposition is ConflictDisposition.OPEN_CONFLICT_PRESERVED
    assert open_row.model_dump(exclude={"review_state"}) == original_open.model_dump(
        exclude={"review_state"}
    )
    # 来源范围与披露字段逐项保留。
    assert open_row.source_role == original_open.source_role
    assert open_row.disclosure_maturity == original_open.disclosure_maturity
    assert open_row.disclosure_state == original_open.disclosure_state
    assert open_row.compatibility_rule == original_open.compatibility_rule
    # 同一批中冲突已解决的已登记行仍然合法翻转。
    flipped = {
        row_id
        for row_id, row in rows.items()
        if row.review_state is FactReviewState.ACCEPTED
    }
    assert flipped == set(_SUBSET_ROWS) - {_DIRECT}
