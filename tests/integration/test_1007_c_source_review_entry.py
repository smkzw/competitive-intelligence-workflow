"""1007 C 待确认纯研究内容 → 真实来源复核入口（bootstrap）合同测试。

真实链路（真实项目合同、真实摄取与证据快照、真实 C 门户渲染事务、真实
复核请求发布；不写手写接受 SQL、不伪造复核回执、不渲染假 current）：

- 全部候选（无独立复核摘要）的待确认内容必须发布**真实阻断**的复核请求
  与未复核候选站点：门槛逐单元评估真实来自持久化事实谱系；数据库事实保持
  ``candidate``，不产生 current，不产生任何科学接受；
- 预览报告数据只改写来源谱系元数据（新证据快照标识、实际来源实例→版本
  映射、报告快照空），观察原文/取值/状态逐字节不变；内容输入文件保持
  原字节；
- 登记消费者必须精确覆盖全部报告行并指向实际持久化事实版本；证据闭包
  必须与输入来源、观察完全闭合；
- 预接受（accepted/user_modified）行、携带 scientific_review 摘要的包、
  合同不一致与篡改原文引用全部失败关闭，且失败不产生任何接受或静默翻转；
- 精确重放校验首次入口回执/绑定/字节并返回既有输出，不重渲染、不覆盖；
  回执、站点、预览数据或时间参数漂移一律失败关闭。
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pytest

from ci_workflow.application.c_source_review_entry import (
    CSourceReviewEntryError,
    prepare_c_source_review,
)
from ci_workflow.application.project_service import create_project_workspace
from ci_workflow.domain.contracts import create_project_contract
from ci_workflow.domain.enums import FactReviewState
from ci_workflow.gates.models import ReportDecision
from tests.integration.test_fresh_c_research_package import _content_payload

_AT = datetime(2026, 9, 2, 1, 0, tzinfo=UTC)
_PRODUCER_SESSION = "producer-session-1007"
_CUTOFF = datetime.combine(date(2026, 8, 31), time.max, tzinfo=ZoneInfo("Asia/Shanghai"))
_CONTRACT_CUTOFF = "2026-08-31"
_SITE_RELATIVE = "reports/C/v1/html"
_MANIFEST_RELATIVE = "reports/C/v1/html.manifest.json"


def _pending_content_payload() -> dict[str, object]:
    """全部候选、单一实际来源的最小待确认内容（无独立复核摘要）。

    复用既有 C 新鲜来源夹具的登记设计事实，但把每行显式降回候选、把数据
    截止对齐项目合同（既有 C 消费者登记要求报告头与锁定合同一致），并只
    保留观察实际引用的来源实例（来源实例→版本映射必须与锁定闭包一致）。
    """
    payload = _content_payload()
    for observation in payload["report_data"]["observations"]:
        observation["review_state"] = FactReviewState.CANDIDATE.value
    payload["data_cutoff"] = _CUTOFF
    payload["report_data"]["data_cutoff"] = _CUTOFF
    payload["sources"] = [
        source for source in payload["sources"] if source["source_id"] == "source-registry-1"
    ]
    return payload


def _write_content(project_root: Path, payload: dict[str, object]) -> Path:
    path = project_root / "inputs" / "c-source-review" / "pending-content.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, default=str), encoding="utf-8"
    )
    return path


@pytest.fixture(name="world")
def world_fixture(tmp_path: Path) -> tuple[Path, Path, dict[str, object]]:
    contract = create_project_contract(
        indication="特应性皮炎", reports=["C"], outputs=["html"], cutoff=_CONTRACT_CUTOFF
    )
    project_root = create_project_workspace(tmp_path / "入口项目", contract)
    payload = _pending_content_payload()
    content_path = _write_content(project_root, payload)
    return project_root, content_path, payload


def _prepare(root: Path, content_path: Path, **overrides: object) -> Any:
    arguments: dict[str, object] = {
        "project_root": root,
        "content_path": content_path,
        "producer_session_id": _PRODUCER_SESSION,
        "produced_at": _AT,
    }
    arguments.update(overrides)
    return prepare_c_source_review(**arguments)  # type: ignore[arg-type]


def _open_readonly(root: Path) -> sqlite3.Connection:
    uri = (root / "state/project.sqlite").resolve().as_uri() + "?mode=ro"
    return sqlite3.connect(uri, uri=True)


def _fact_states(root: Path) -> dict[str, str]:
    database = _open_readonly(root)
    try:
        rows = database.execute(
            "SELECT fact_id,review_state FROM fact_versions ORDER BY fact_id"
        ).fetchall()
    finally:
        database.close()
    return {str(row[0]): str(row[1]) for row in rows}


def _consumer_rows(root: Path) -> dict[str, str]:
    database = _open_readonly(root)
    try:
        rows = database.execute(
            "SELECT row_id,source_fact_version_id FROM source_portal_consumer_bindings "
            "WHERE report='C' ORDER BY row_id"
        ).fetchall()
    finally:
        database.close()
    return {str(row[0]): str(row[1]) for row in rows}


def _file_digests(root: Path, relative: str) -> dict[str, str]:
    base = root / relative
    if not base.exists():
        return {}
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(base.rglob("*"))
        if path.is_file()
    }


def test_entry_publishes_true_blocked_request_and_unreviewed_candidate_site(
    world: tuple[Path, Path, dict[str, object]],
) -> None:
    root, content_path, payload = world
    input_bytes = content_path.read_bytes()

    outcome = _prepare(root, content_path)

    # 门槛评估真实来自持久化谱系：全部候选 → 真实阻断，且复核键取自同一
    # 评估单元，不来自任何传入布尔或伪接受标记。
    assert outcome.gate.result.decision is ReportDecision.BLOCKED
    assert outcome.gate.review_result.decision is ReportDecision.BLOCKED
    assert outcome.gate.review_result.result_key == outcome.gate.gate_result_key
    assert outcome.scope.epoch == 0
    assert outcome.evidence_snapshot_id.startswith("evidence-snapshot_")
    assert outcome.claim_snapshot_id.startswith("claim-snapshot_")
    assert outcome.coverage_set_id.startswith("coverage-set_")

    # 复核请求：绑定真实上下文与阻断门槛，仍可独立复核，但不可晋级。
    request = json.loads((root / outcome.scope.review_request_relative).read_bytes())
    assert request["production"]["producer_session_id"] == _PRODUCER_SESSION
    assert request["production"]["produced_at"].startswith("2026-09-02T01:00:00")
    assert request["gate_result"]["decision"] == "blocked"
    assert request["gate_result"]["result_key"] == outcome.gate.review_result.result_key
    context = request["scientific_context"]
    assert context["candidate_snapshot_id"] == outcome.evidence_snapshot_id
    assert context["candidate_content_digest"] == outcome.gate.candidate_content_digest
    assert context["gate_result_key"] == outcome.gate.review_result.result_key
    assert context["context_digest"] == outcome.context.context_digest
    assert (root / outcome.scope.production_context_relative).is_file()

    # 未复核候选站点：真实渲染字节，状态显式候选，绝不 current。
    assert (root / _SITE_RELATIVE).is_dir()
    assert (root / _MANIFEST_RELATIVE).is_file()
    status = json.loads((root / _SITE_RELATIVE / "data/research-status.json").read_text())
    assert status["delivery_status"] == "unreviewed_candidate"
    from ci_workflow.application.latest_delivery import read_current_delivery

    assert read_current_delivery(root) is None

    # 数据库事实全部保持候选：无静默翻转、无当前提升。
    states = _fact_states(root)
    assert states and set(states.values()) == {"candidate"}
    assert set(states) == {
        observation["row_id"] for observation in payload["report_data"]["observations"]
    }

    # 预览报告数据：只改写来源谱系元数据，其余逐字节不变；原输入未改。
    from ci_workflow.application.fresh_c_research_package import validate_fresh_c_content

    report_data = json.loads(outcome.report_data_path.read_bytes())
    assert outcome.report_data_path == (
        root
        / "evidence/library/c-source-review"
        / outcome.gate.candidate_content_digest
        / "report-data.json"
    )
    assert report_data["report_snapshot_id"] is None
    assert report_data["source_evidence_snapshot_id"] == outcome.evidence_snapshot_id
    assert set(report_data["source_version_by_source_id"]) == {
        observation["source_version_id"]
        for observation in payload["report_data"]["observations"]
    }
    expected_report_data = validate_fresh_c_content(payload).report_data.model_dump(
        mode="json"
    )
    for field in ("products", "trials", "observations", "user_edits", "design_paths"):
        assert report_data[field] == expected_report_data[field]
    assert content_path.read_bytes() == input_bytes

    # 精确来源/消费者闭包：登记行精确覆盖全部报告行并指向持久化事实版本；
    # 证据闭包来源与输入来源实例一一对应。
    consumers = _consumer_rows(root)
    assert set(consumers) == set(states)
    snapshot = json.loads(
        (
            root / "snapshots" / "evidence" / f"{outcome.evidence_snapshot_id}.json"
        ).read_bytes()
    )
    closure = snapshot["closure"]
    version_by_capture = {
        str(entry["capture"]["source_id"]): str(entry["source_version_id"])
        for entry in closure["sources"]
    }
    assert version_by_capture == dict(report_data["source_version_by_source_id"])
    assert set(version_by_capture) == {item["source_id"] for item in payload["sources"]}
    closure_fact_versions = {
        str(entry["fact"]["fact_id"]): str(entry["fact_version_id"])
        for entry in closure["facts"]
    }
    assert closure_fact_versions == consumers
    assert len(outcome.consumers) == len(consumers)

    # 入口回执：绑定实际输入/来源/谱系/渲染/请求/门槛与后续步骤。
    receipt = json.loads(outcome.receipt_path.read_bytes())
    assert receipt["gate_decision"] == "blocked"
    assert receipt["content_digest"] == outcome.gate.candidate_content_digest
    assert receipt["evidence_snapshot_id"] == outcome.evidence_snapshot_id
    assert receipt["claim_snapshot_id"] == outcome.claim_snapshot_id
    assert receipt["coverage_set_id"] == outcome.coverage_set_id
    assert receipt["context_digest"] == outcome.context.context_digest
    assert receipt["site_relative"] == _SITE_RELATIVE
    assert receipt["review_request_relative"] == outcome.scope.review_request_relative
    assert receipt["next_steps"]


def test_exact_replay_validates_and_returns_existing_output_without_rerender(
    world: tuple[Path, Path, dict[str, object]],
) -> None:
    root, content_path, _payload = world
    first = _prepare(root, content_path)
    manifest_before = hashlib.sha256((root / _MANIFEST_RELATIVE).read_bytes()).hexdigest()
    site_before = _file_digests(root, _SITE_RELATIVE)
    request_before = _file_digests(
        root, str(Path(first.scope.review_request_relative).parent)
    )
    snapshots_before = _file_digests(root, "snapshots/reports/C")

    replay = _prepare(root, content_path, produced_at=None)

    assert replay.evidence_snapshot_id == first.evidence_snapshot_id
    assert replay.claim_snapshot_id == first.claim_snapshot_id
    assert replay.coverage_set_id == first.coverage_set_id
    assert replay.scope == first.scope
    assert replay.context.context_digest == first.context.context_digest
    assert replay.gate.review_result.result_key == first.gate.review_result.result_key
    assert replay.gate.result.decision is ReportDecision.BLOCKED
    assert replay.report_data_path == first.report_data_path
    assert replay.receipt_path == first.receipt_path
    assert replay.consumers == first.consumers
    # 未重渲染、未覆盖任何既有字节、未新增报告快照。
    assert hashlib.sha256((root / _MANIFEST_RELATIVE).read_bytes()).hexdigest() == manifest_before
    assert _file_digests(root, _SITE_RELATIVE) == site_before
    assert (
        _file_digests(root, str(Path(first.scope.review_request_relative).parent))
        == request_before
    )
    assert _file_digests(root, "snapshots/reports/C") == snapshots_before
    assert _fact_states(root) and set(_fact_states(root).values()) == {"candidate"}

    # 显式时间漂移不是精确重放：失败关闭。
    with pytest.raises(CSourceReviewEntryError, match="produced_at|漂移|不一致"):
        _prepare(root, content_path, produced_at=_AT + timedelta(minutes=5))
    # 生产者会话标识漂移：失败关闭。
    with pytest.raises(CSourceReviewEntryError, match="会话|漂移|不一致"):
        _prepare(root, content_path, producer_session_id="other-session")

    receipt_path = first.receipt_path
    original_receipt = receipt_path.read_bytes()
    # 篡改首次入口回执的门槛键：与重算评估不一致，拒绝。
    tampered = json.loads(original_receipt)
    tampered["gate_result_key"] = "gate-result_" + "0" * 24
    receipt_path.write_text(json.dumps(tampered, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(CSourceReviewEntryError):
        _prepare(root, content_path)
    receipt_path.write_bytes(original_receipt)

    # 篡改候选站点字节：门户绑定漂移，拒绝。
    status_path = root / _SITE_RELATIVE / "data/research-status.json"
    original_status = status_path.read_bytes()
    status_path.write_bytes(original_status + b" ")
    with pytest.raises(CSourceReviewEntryError):
        _prepare(root, content_path)
    status_path.write_bytes(original_status)

    # 篡改预览报告数据：报告数据字节与首次入口不一致，拒绝。
    original_report_data = first.report_data_path.read_bytes()
    tampered_report = json.loads(original_report_data)
    tampered_report["observations"][0]["source_text"] += "（篡改）"
    first.report_data_path.write_text(
        json.dumps(tampered_report, ensure_ascii=False), encoding="utf-8"
    )
    with pytest.raises(CSourceReviewEntryError):
        _prepare(root, content_path)
    first.report_data_path.write_bytes(original_report_data)

    # 完整恢复后仍可精确重放。
    assert _prepare(root, content_path, produced_at=None).evidence_snapshot_id == (
        first.evidence_snapshot_id
    )


def test_resume_reuses_first_attempt_without_rerender(
    world: tuple[Path, Path, dict[str, object]],
) -> None:
    """首次尝试在回执落盘前中断：复用既有产物恢复，不重渲染、不覆盖。"""
    root, content_path, _payload = world
    first = _prepare(root, content_path)
    manifest_before = hashlib.sha256((root / _MANIFEST_RELATIVE).read_bytes()).hexdigest()
    site_before = _file_digests(root, _SITE_RELATIVE)
    report_snapshots_before = _file_digests(root, "snapshots/reports/C")
    receipt_bytes = first.receipt_path.read_bytes()

    first.receipt_path.unlink()
    resumed = _prepare(root, content_path, produced_at=None)

    assert resumed.evidence_snapshot_id == first.evidence_snapshot_id
    assert resumed.claim_snapshot_id == first.claim_snapshot_id
    assert resumed.coverage_set_id == first.coverage_set_id
    assert resumed.context.context_digest == first.context.context_digest
    assert resumed.gate.review_result.result_key == first.gate.review_result.result_key
    assert hashlib.sha256((root / _MANIFEST_RELATIVE).read_bytes()).hexdigest() == manifest_before
    assert _file_digests(root, _SITE_RELATIVE) == site_before
    assert _file_digests(root, "snapshots/reports/C") == report_snapshots_before
    assert resumed.receipt_path.read_bytes() == receipt_bytes
    assert set(_fact_states(root).values()) == {"candidate"}


def test_entry_rejects_preaccepted_user_modified_and_scientific_review_payload(
    world: tuple[Path, Path, dict[str, object]],
) -> None:
    root, content_path, payload = world
    for review_state in (FactReviewState.ACCEPTED, FactReviewState.USER_MODIFIED):
        tampered = json.loads(json.dumps(payload, default=str))
        tampered["report_data"]["observations"][0]["review_state"] = review_state.value
        path = _write_content(root, tampered)
        with pytest.raises(CSourceReviewEntryError, match="候选|review_state"):
            _prepare(root, path)
        path.unlink()
    # 携带独立复核摘要的完整包不是本入口输入：失败关闭，不接受生产者批准。
    packaged = json.loads(json.dumps(payload, default=str))
    packaged["scientific_review"] = {
        "reviewer_id": "independent-reviewer-1",
        "reviewer_role": "independent_scientific_verifier",
        "status": "accepted",
        "reviewed_at": "2026-09-01T00:00:00+00:00",
        "reviewed_content_digest": "0" * 64,
        "observations": ("伪复核摘要。",),
    }
    package_path = _write_content(root, packaged)
    with pytest.raises(CSourceReviewEntryError, match="scientific_review|独立复核"):
        _prepare(root, package_path)
    package_path.unlink()

    # 失败关闭后：数据库/站点/快照/回执均未产生任何接受或残留。
    assert not (root / "evidence/library/c-source-review").exists()
    assert not (root / "reports/C/v1").exists()
    assert not any((root / "snapshots/evidence").iterdir())


def test_entry_rejects_contract_mismatch_and_tampered_source_quote(
    tmp_path: Path,
) -> None:
    # 适应症不一致：内容合同有效但与项目合同不一致，拒绝。
    contract = create_project_contract(
        indication="特应性皮炎", reports=["C"], outputs=["html"], cutoff=_CONTRACT_CUTOFF
    )
    root = create_project_workspace(tmp_path / "适应症项目", contract)
    payload = _pending_content_payload()
    payload["indication"] = "结节性痒疹"
    payload["report_data"]["indication"] = "结节性痒疹"
    payload["report_data"]["indication_id"] = "prurigo-nodularis"
    payload["indication_id"] = "prurigo-nodularis"
    content_path = _write_content(root, payload)
    with pytest.raises(CSourceReviewEntryError, match="适应症"):
        _prepare(root, content_path)

    # 截止日与项目合同不一致（既有 C 消费者登记要求报告头等于锁定合同）：拒绝。
    contract_late = create_project_contract(
        indication="特应性皮炎", reports=["C"], outputs=["html"], cutoff="2026-08-01"
    )
    late_root = create_project_workspace(tmp_path / "截止项目", contract_late)
    late_path = _write_content(late_root, _pending_content_payload())
    with pytest.raises(CSourceReviewEntryError, match="截止"):
        _prepare(late_root, late_path)

    # 项目合同不包含 C 类报告：拒绝。
    contract_b = create_project_contract(
        indication="特应性皮炎", reports=["B"], outputs=["html"], cutoff=_CONTRACT_CUTOFF
    )
    b_root = create_project_workspace(tmp_path / "B类项目", contract_b)
    b_path = _write_content(b_root, _pending_content_payload())
    with pytest.raises(CSourceReviewEntryError, match="C 类"):
        _prepare(b_root, b_path)

    # 报告版本不能构成既有站点产物路径合同：拒绝且无任何中间产物。
    version_root = create_project_workspace(
        tmp_path / "版本项目",
        create_project_contract(
            indication="特应性皮炎", reports=["C"], outputs=["html"], cutoff=_CONTRACT_CUTOFF
        ),
    )
    version_payload = _pending_content_payload()
    version_payload["report_version"] = "r24-source-review-candidate"
    version_payload["report_data"]["report_version"] = "r24-source-review-candidate"
    version_path = _write_content(version_root, version_payload)
    with pytest.raises(CSourceReviewEntryError, match="站点产物路径合同"):
        _prepare(version_root, version_path)
    assert not (version_root / "evidence/library/c-source-review").exists()
    assert not any((version_root / "snapshots/evidence").iterdir())

    # 篡改观察原文且不改来源字节：事实派生/引用重提取失败关闭。
    root_quote = create_project_workspace(
        tmp_path / "原文项目",
        create_project_contract(
            indication="特应性皮炎", reports=["C"], outputs=["html"], cutoff=_CONTRACT_CUTOFF
        ),
    )
    quote_payload = _pending_content_payload()
    quote_payload["report_data"]["observations"][0]["source_text"] += "（篡改）"
    quote_path = _write_content(root_quote, quote_payload)
    with pytest.raises(CSourceReviewEntryError, match="原文|重提取|引用"):
        _prepare(root_quote, quote_path)
    assert not (root_quote / "evidence/library/c-source-review").exists()
    assert not (root_quote / "reports/C/v1").exists()
    assert not any((root_quote / "snapshots/evidence").iterdir())


def test_cli_prepares_and_replays_without_accepting_facts(
    world: tuple[Path, Path, dict[str, object]], capsys: pytest.CaptureFixture[str],
) -> None:
    from ci_workflow.cli import main

    root, content_path, _payload = world
    argv = ["review", "prepare-source-c", "--root", str(root), "--content",
            str(content_path), "--producer-session-id", _PRODUCER_SESSION]
    assert main(argv) == 0
    first = json.loads(capsys.readouterr().out.split(" ", 1)[1])
    assert first["gate_decision"] == "blocked"
    assert first["delivery_status"] == "unreviewed_candidate"
    assert main(argv) == 0
    assert json.loads(capsys.readouterr().out.split(" ", 1)[1]) == first
    assert set(_fact_states(root).values()) == {"candidate"}


def test_frozen_entry_publish_never_overwrites_a_concurrent_writer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    import os

    from ci_workflow.application.c_source_review_entry import _write_frozen

    target = tmp_path / "entry-receipt.json"
    real_link = os.link

    def other_writer(source: object, destination: object) -> None:
        target.write_bytes(b"first-writer")
        real_link(source, destination)  # type: ignore[arg-type]

    monkeypatch.setattr(os, "link", other_writer)
    with pytest.raises(CSourceReviewEntryError, match="拒绝覆盖"):
        _write_frozen(target, b"second-writer", label="并发回执")
    assert target.read_bytes() == b"first-writer"


def test_corrected_display_prepares_new_epoch_without_reaccepting_source_facts(
    world: tuple[Path, Path, dict[str, object]],
) -> None:
    """A rejected translation is repaired as a new candidate, not overwritten."""
    from ci_workflow.application.latest_delivery import read_current_delivery

    root, content_path, payload = world
    first = _prepare(root, content_path)
    historical = {
        relative: (root / relative).read_bytes()
        for relative in (
            first.scope.review_request_relative,
            first.scope.production_context_relative,
            first.receipt_path.relative_to(root).as_posix(),
            _MANIFEST_RELATIVE,
        )
    }
    historical_site = _file_digests(root, _SITE_RELATIVE)
    fact_states = _fact_states(root)
    changed = json.loads(json.dumps(payload, default=str))
    changed["report_version"] = "v2"
    changed["report_data"]["report_version"] = "v2"
    changed["report_data"]["observations"][0]["display_text"] = "经原文核对的新中文呈现"
    next_input = content_path.with_name("corrected-content.json")
    next_input.write_text(json.dumps(changed, ensure_ascii=False), encoding="utf-8")

    second = _prepare(root, next_input, produced_at=_AT + timedelta(minutes=5))

    assert second.scope.epoch == 1
    assert second.context.context_digest != first.context.context_digest
    assert second.evidence_snapshot_id != first.evidence_snapshot_id
    assert second.gate.review_result.decision is ReportDecision.BLOCKED
    assert second.context.source_refs == first.context.source_refs
    assert _fact_states(root) == fact_states
    assert set(fact_states.values()) == {"candidate"}
    assert read_current_delivery(root) is None
    for relative, original_bytes in historical.items():
        assert (root / relative).read_bytes() == original_bytes
    assert _file_digests(root, _SITE_RELATIVE) == historical_site
    assert _prepare(root, next_input, produced_at=None).receipt_path == second.receipt_path
