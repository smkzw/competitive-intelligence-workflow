"""独立科学复核宿主回执合同（scientific-review-v1）负向优先测试。

合同目标（R2 工作项 2）：回执不可变并绑定生产上下文、复核上下文、内容
摘要、review artifact digest 与时间顺序；宿主无独立上下文能力时失败关闭；
三宿主（codex/hermes/omp）可适配。单进程自证、同会话复核、生产者自审、
时间倒挂与摘要漂移都必须在结构层失败关闭。
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError
from pydantic import ValidationError

from ci_workflow.domain.enums import ReportKind
from ci_workflow.qc.review_receipt import (
    REVIEW_RECEIPT_KIND,
    ReviewArtifactBinding,
    ReviewContentBinding,
    ReviewContextEvidence,
    ReviewExecutableEvidence,
    ReviewHostSession,
    ReviewProcessEvidence,
    ReviewProductionContext,
    ScientificReviewReceipt,
    ScientificReviewReceiptError,
    ScientificReviewReceiptIntegrityError,
    bind_receipt_to_production_context,
    build_scientific_review_receipt,
    require_verified_review_receipt,
    validate_scientific_review_receipt_payload,
)
from ci_workflow.qc.scientific import (
    LocatorDetail,
    LocatorRef,
    ScientificQcCurrentContext,
    SourceRef,
)

ROOT = Path(__file__).resolve().parents[2]
PACKAGED_SCHEMA = ROOT / "src" / "ci_workflow" / "schemas" / "scientific-review-receipt.schema.json"

SH_CONTEXT = "c" * 64
SH_CANDIDATE = "a" * 64
SH_INPUT = "b" * 64
SH_ARTIFACT = "d" * 64

PRODUCED_AT = datetime(2026, 9, 5, 1, 0, 0, tzinfo=UTC)
REVIEW_STARTED_AT = datetime(2026, 9, 5, 2, 0, 0, tzinfo=UTC)
REVIEW_FINISHED_AT = datetime(2026, 9, 5, 2, 30, 0, tzinfo=UTC)
ISSUED_AT = datetime(2026, 9, 5, 3, 0, 0, tzinfo=UTC)


def _production_context(**overrides: Any) -> ReviewProductionContext:
    values: dict[str, Any] = {
        "project_id": "project-r2",
        "report_kind": "B",
        "report_version": "v1",
        "report_object_id": "report:B:v1",
        "candidate_snapshot_id": "snapshot-1",
        "candidate_content_digest": SH_CANDIDATE,
        "producer_id": "producer-agent",
        "producer_session_id": "producer-session-1",
        "criteria_version": "B-v1",
        "gate_result_key": "gate-key-1",
        "produced_at": PRODUCED_AT,
        "production_context_digest": SH_CONTEXT,
    }
    values.update(overrides)
    return ReviewProductionContext(**values)


def _review_context(**overrides: Any) -> ReviewContextEvidence:
    values: dict[str, Any] = {
        "reviewer_id": "independent-reviewer",
        "host_executable": ReviewExecutableEvidence(
            provenance="path_resolved",
            path="/opt/homebrew/bin/codex",
            resolved_realpath="/opt/homebrew/bin/codex",
            version="codex-cli 0.42.0",
        ),
        "session": ReviewHostSession(
            session_id="review-session-9",
            launcher_pid=777,
            launcher_parent_pid=1,
        ),
        "process": ReviewProcessEvidence(
            kind="external_subprocess",
            pid=4242,
            argv=("/opt/homebrew/bin/codex", "exec", "scientific-review"),
            cwd="/tmp/项目-r2",
            started_at=REVIEW_STARTED_AT,
            finished_at=REVIEW_FINISHED_AT,
            returncode=0,
        ),
        "independent_context": "external_subprocess_session",
    }
    values.update(overrides)
    return ReviewContextEvidence(**values)


def _content_binding(**overrides: Any) -> ReviewContentBinding:
    values: dict[str, Any] = {
        "reviewed_content_digest": SH_CANDIDATE,
        "review_input_digest": SH_INPUT,
    }
    values.update(overrides)
    return ReviewContentBinding(**values)


def _artifact(**overrides: Any) -> ReviewArtifactBinding:
    values: dict[str, Any] = {
        "artifact_kind": "scientific_qc_verdict",
        "path": "receipts/scientific_review/verdict.json",
        "artifact_sha256": SH_ARTIFACT,
    }
    values.update(overrides)
    return ReviewArtifactBinding(**values)


def _build_receipt(**overrides: Any) -> ScientificReviewReceipt:
    values: dict[str, Any] = {
        "host": "codex",
        "issued_at": ISSUED_AT,
        "production": _production_context(),
        "review": _review_context(),
        "content": _content_binding(),
        "artifact": _artifact(),
    }
    values.update(overrides)
    return build_scientific_review_receipt(**values)


def _authoritative_context() -> ScientificQcCurrentContext:
    locator = LocatorRef(
        fragment_id="frag-1",
        locator=LocatorDetail(document_role="primary_result", page=12, table="Table 2"),
    )
    source = SourceRef(
        source_version_id="src-1",
        fragment_ids=("frag-1",),
        claim_ids=("claim-1",),
        fact_version_ids=("fact-1",),
        locators=(locator,),
    )
    return ScientificQcCurrentContext(
        context_id="ctx-1",
        producer_id="producer-agent",
        project_id="project-r2",
        report_kind=ReportKind.B,
        report_version="v1",
        report_object_id="report:B:v1",
        candidate_snapshot_id="snapshot-1",
        candidate_content_digest=SH_CANDIDATE,
        criteria_version="B-v1",
        gate_result_key="gate-key-1",
        contract_version="1.0",
        coverage_set_id="coverage-1",
        coverage_digest=SH_INPUT,
        source_refs=(source,),
        locators=(locator,),
    )


# ─── 正向：绑定齐全、三宿主可适配且不可变 ──────────────────────────────────────


@pytest.mark.parametrize("host", ["codex", "hermes", "omp"])
def test_three_hosts_build_verified_receipt_with_full_bindings(
    host: str, tmp_path: Path
) -> None:
    artifact_path = tmp_path / "receipts/scientific_review/verdict.json"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_bytes(b'{"verdict":"accepted"}')
    receipt = _build_receipt(
        host=host,  # type: ignore[arg-type]
        artifact=_artifact(
            artifact_sha256=hashlib.sha256(artifact_path.read_bytes()).hexdigest()
        ),
    )
    assert receipt.status == "verified"
    assert receipt.receipt_kind == REVIEW_RECEIPT_KIND == "scientific-review-v1"
    assert receipt.production.project_id == "project-r2"
    assert receipt.review.reviewer_id == "independent-reviewer"
    assert receipt.content.reviewed_content_digest == SH_CANDIDATE
    assert receipt.artifact is not None
    assert receipt.artifact.artifact_sha256 == hashlib.sha256(
        artifact_path.read_bytes()
    ).hexdigest()
    receipt.verify_content_integrity()
    require_verified_review_receipt(receipt, project_root=tmp_path)


def test_receipt_digest_changes_with_any_bound_field() -> None:
    receipt = _build_receipt()
    payload = receipt.model_dump(mode="json", exclude={"receipt_digest"})
    changed = deepcopy(payload)
    changed["review"]["reviewer_id"] = "另一位复核者"
    recomputed = hashlib.sha256(
        json.dumps(changed, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    # 更换复核者必然改变回执摘要（不可变绑定）
    assert recomputed != receipt.receipt_digest


# ─── Schema 层：打包副本有效、结构失败关闭 ────────────────────────────────────


def test_packaged_schema_is_valid_and_accepts_built_receipt() -> None:
    assert PACKAGED_SCHEMA.is_file()
    schema: dict[str, Any] = json.loads(PACKAGED_SCHEMA.read_text(encoding="utf-8"))
    assert schema.get("$schema", "").endswith("2020-12/schema")
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(_build_receipt().model_dump(mode="json"))


def test_schema_rejects_unknown_and_missing_fields() -> None:
    schema: dict[str, Any] = json.loads(PACKAGED_SCHEMA.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    payload = _build_receipt().model_dump(mode="json")
    with_unknown = deepcopy(payload)
    with_unknown["self_asserted"] = True
    with pytest.raises(JsonSchemaValidationError):
        validator.validate(with_unknown)
    missing = deepcopy(payload)
    missing.pop("production")
    with pytest.raises(JsonSchemaValidationError):
        validator.validate(missing)


def test_validate_payload_roundtrip_and_rejects_forged_status() -> None:
    receipt = validate_scientific_review_receipt_payload(_build_receipt().model_dump(mode="json"))
    assert receipt.receipt_digest == _build_receipt().receipt_digest
    forged = _build_receipt(
        review=_review_context(
            host_executable=ReviewExecutableEvidence(provenance="unavailable"),
            independent_context="unavailable",
        ),
        unavailable_reason_zh="宿主无法创建独立上下文。",
        artifact=None,
    ).model_dump(mode="json")
    forged["status"] = "verified"
    forged["unavailable_reason_zh"] = None
    with pytest.raises(ScientificReviewReceiptError):
        validate_scientific_review_receipt_payload(forged)


# ─── 失败关闭：独立上下文伪造与能力缺失 ────────────────────────────────────────


def test_same_process_review_fails_closed() -> None:
    with pytest.raises(ValidationError, match="同进程"):
        _build_receipt(
            review=_review_context(
                session=ReviewHostSession(
                    session_id="review-session-9",
                    launcher_pid=4242,
                    launcher_parent_pid=1,
                ),
            )
        )


def test_producer_self_review_fails_closed() -> None:
    with pytest.raises(ValidationError, match="不同身份"):
        _build_receipt(review=_review_context(reviewer_id="producer-agent"))


def test_same_session_review_fails_closed() -> None:
    with pytest.raises(ValidationError, match="会话分离"):
        _build_receipt(
            review=_review_context(
                session=ReviewHostSession(
                    session_id="producer-session-1",
                    launcher_pid=778,
                    launcher_parent_pid=1,
                ),
            )
        )


def test_unavailable_context_yields_fail_closed_receipt(tmp_path: Path) -> None:
    receipt = _build_receipt(
        review=_review_context(
            host_executable=ReviewExecutableEvidence(provenance="unavailable"),
            independent_context="unavailable",
        ),
        unavailable_reason_zh="宿主无法创建独立上下文，复核被拒绝。",
        artifact=None,
    )
    assert receipt.status == "host_context_unavailable"
    with pytest.raises(ScientificReviewReceiptError):
        require_verified_review_receipt(receipt, project_root=tmp_path)


def test_unavailable_receipt_must_not_carry_artifact() -> None:
    with pytest.raises(ValidationError):
        _build_receipt(
            review=_review_context(
                host_executable=ReviewExecutableEvidence(provenance="unavailable"),
                independent_context="unavailable",
            ),
            unavailable_reason_zh="宿主无法创建独立上下文。",
        )


def test_unavailable_receipt_requires_chinese_reason() -> None:
    with pytest.raises(ValidationError):
        _build_receipt(
            review=_review_context(
                host_executable=ReviewExecutableEvidence(provenance="unavailable"),
                independent_context="unavailable",
            ),
            unavailable_reason_zh=None,
            artifact=None,
        )


def test_forged_verified_status_without_independence_fails_closed() -> None:
    forged = _build_receipt(
        review=_review_context(
            host_executable=ReviewExecutableEvidence(provenance="unavailable"),
            independent_context="unavailable",
        ),
        unavailable_reason_zh="宿主无法创建独立上下文。",
        artifact=None,
    ).model_dump(mode="json")
    forged["status"] = "verified"
    forged["unavailable_reason_zh"] = None
    with pytest.raises(ValidationError):
        ScientificReviewReceipt.model_validate(forged)


def test_verified_receipt_requires_artifact_and_success_process() -> None:
    with pytest.raises(ValidationError):
        _build_receipt(artifact=None)
    with pytest.raises(ValidationError):
        _build_receipt(
            review=_review_context(
                process=ReviewProcessEvidence(
                    kind="external_subprocess",
                    pid=4242,
                    argv=("/opt/homebrew/bin/codex", "exec", "scientific-review"),
                    cwd="/tmp/项目-r2",
                    started_at=REVIEW_STARTED_AT,
                    finished_at=REVIEW_FINISHED_AT,
                    returncode=1,
                ),
            )
        )


def test_verified_receipt_binds_host_executable_argv() -> None:
    with pytest.raises(ValidationError):
        _build_receipt(
            review=_review_context(
                process=ReviewProcessEvidence(
                    kind="external_subprocess",
                    pid=4242,
                    argv=("/usr/bin/false",),
                    cwd="/tmp/项目-r2",
                    started_at=REVIEW_STARTED_AT,
                    finished_at=REVIEW_FINISHED_AT,
                    returncode=0,
                ),
            )
        )


# ─── 失败关闭：内容摘要与时间顺序 ─────────────────────────────────────────────


def test_content_digest_mismatch_fails_closed() -> None:
    with pytest.raises(ValidationError, match="内容摘要绑定"):
        _build_receipt(content=_content_binding(reviewed_content_digest="e" * 64))


def test_review_starting_at_or_before_production_fails_closed() -> None:
    for started_at in (PRODUCED_AT, PRODUCED_AT - timedelta(minutes=1)):
        with pytest.raises(ValidationError, match="时间顺序"):
            _build_receipt(
                review=_review_context(
                    process=ReviewProcessEvidence(
                        kind="external_subprocess",
                        pid=4242,
                        argv=("/opt/homebrew/bin/codex", "exec", "scientific-review"),
                        cwd="/tmp/项目-r2",
                        started_at=started_at,
                        finished_at=REVIEW_FINISHED_AT,
                        returncode=0,
                    ),
                )
            )


def test_process_timeline_inversion_fails_closed() -> None:
    with pytest.raises(ValidationError):
        _build_receipt(
            review=_review_context(
                process=ReviewProcessEvidence(
                    kind="external_subprocess",
                    pid=4242,
                    argv=("/opt/homebrew/bin/codex", "exec", "scientific-review"),
                    cwd="/tmp/项目-r2",
                    started_at=REVIEW_FINISHED_AT,
                    finished_at=REVIEW_STARTED_AT,
                    returncode=0,
                ),
            )
        )


def test_issuance_before_review_completion_fails_closed() -> None:
    with pytest.raises(ValidationError, match="时间顺序"):
        _build_receipt(issued_at=REVIEW_FINISHED_AT - timedelta(minutes=1))


# ─── 失败关闭：摘要漂移与生产上下文绑定 ────────────────────────────────────────


def test_digest_drift_after_model_copy_fails_closed(tmp_path: Path) -> None:
    receipt = _build_receipt()
    tampered = receipt.model_copy(update={"issued_at": ISSUED_AT + timedelta(days=1)})
    with pytest.raises(ScientificReviewReceiptIntegrityError):
        tampered.verify_content_integrity()
    with pytest.raises(ScientificReviewReceiptError):
        require_verified_review_receipt(tampered, project_root=tmp_path)


def test_verified_receipt_reopens_bound_artifact_bytes(tmp_path: Path) -> None:
    artifact_path = tmp_path / "receipts/scientific_review/verdict.json"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_bytes(b'{"verdict":"accepted"}')
    digest = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    receipt = _build_receipt(artifact=_artifact(artifact_sha256=digest))
    require_verified_review_receipt(receipt, project_root=tmp_path)

    artifact_path.write_bytes(b'{"verdict":"changed"}')
    with pytest.raises(ScientificReviewReceiptError, match="实际字节"):
        require_verified_review_receipt(receipt, project_root=tmp_path)


def test_verified_receipt_rejects_missing_artifact(tmp_path: Path) -> None:
    with pytest.raises(ScientificReviewReceiptError, match="不存在"):
        require_verified_review_receipt(_build_receipt(), project_root=tmp_path)


def test_bind_receipt_to_authoritative_production_context() -> None:
    context = _authoritative_context()
    receipt = _build_receipt(
        production=_production_context(production_context_digest=context.context_digest),
    )
    bind_receipt_to_production_context(receipt, context)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("project_id", "project-other"),
        ("report_kind", "C"),
        ("report_version", "v2"),
        ("report_object_id", "report:B:v2"),
        ("candidate_snapshot_id", "snapshot-2"),
        ("candidate_content_digest", "f" * 64),
        ("producer_id", "producer-other"),
        ("criteria_version", "B-v2"),
        ("gate_result_key", "gate-key-2"),
        ("production_context_digest", "0" * 64),
    ],
)
def test_bind_rejects_any_production_context_mismatch(field: str, value: str) -> None:
    context = _authoritative_context()
    overrides: dict[str, Any] = {field: value}
    if field != "production_context_digest":
        overrides["production_context_digest"] = context.context_digest
    drifted = _production_context(**overrides)
    rebound = build_scientific_review_receipt(
        host="codex",
        issued_at=ISSUED_AT,
        production=drifted,
        review=_review_context(),
        content=_content_binding(reviewed_content_digest=drifted.candidate_content_digest),
        artifact=_artifact(),
    )
    with pytest.raises(ScientificReviewReceiptError):
        bind_receipt_to_production_context(rebound, context)
