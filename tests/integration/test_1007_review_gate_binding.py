"""Source review is possible before PASS; that receipt cannot publish a report.

Issuer runner below is an explicit test seam, never a real clinical review.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from ci_workflow.application import scientific_review_transition as transition
from ci_workflow.application.review_issuer import ExternalProcessResult, issue_review_receipt
from ci_workflow.domain.enums import ReportKind
from ci_workflow.gates.models import GateUnitOutcome, GateUnitResult, ReportGateResult
from tests.integration import test_scientific_review_transition as fixture


def _gate(*, blocked: bool = False, kind: str = "B") -> ReportGateResult:
    unit = GateUnitResult(
        unit_id="critical-source", report_kind=ReportKind(kind), object_id="trial-1",
        applicable=True, outcome=GateUnitOutcome.BLOCKED if blocked else GateUnitOutcome.SATISFIED,
        blocking=blocked, threshold=1, satisfied_count=0 if blocked else 1,
        fact_version_ids=() if blocked else ("fact-version-1",),
        user_note_zh="来源待独立复核" if blocked else None,
    )
    return ReportGateResult.from_unit_results(
        report_kind=ReportKind(kind), unit_results=(unit,),
        evidence_snapshot_id="evidence-snapshot_1",
        candidate_snapshot_digest=fixture.CANDIDATE_DIGEST,
        spec_version=f"{kind}-v1", contract_version="1.0", universe_summary="test-universe",
        spec_fingerprint="test-policy",
    )


def _prepare(root: Path, gate: ReportGateResult | None, *, kind: str = "B"):
    context = fixture._context(
        report_kind=kind, criteria_version=f"{kind}-v1",
        gate_result_key=_gate(kind=kind).result_key,
    )
    fixture._portal_site(root)
    binding = fixture._portal_binding(root)
    kwargs = {} if gate is None else {"gate_result": gate}
    scope = transition.prepare_rendered_scientific_review(
        project_root=root, report_kind=kind, context=context,
        producer_session_id="producer-session-1", produced_at=fixture.PRODUCED_AT,
        portal_binding=binding, **kwargs,
    )
    return context, scope


def _issue(root: Path, context):
    artifact = fixture._artifact_file(context, root)
    request_path = root / transition.scientific_review_request_path(context.report_kind.value)
    request = json.loads(request_path.read_bytes())
    path = root / artifact.path
    verdict = json.loads(path.read_bytes())
    verdict["review_input_digest"] = request["review_input_digest"]
    path.write_text(json.dumps(verdict, ensure_ascii=False), encoding="utf-8")

    def runner(argv, cwd, timeout):
        return ExternalProcessResult(
            pid=4242, argv=argv, cwd=cwd, started_at=fixture.REVIEW_STARTED_AT,
            finished_at=fixture.REVIEW_FINISHED_AT, returncode=0,
        )

    return issue_review_receipt(
        project_root=root, report_kind=context.report_kind.value,
        reviewer_id="independent-reviewer", review_session_id="review-session-9", host="codex",
        host_executable=fixture._review_evidence().host_executable,
        review_argv=("exec", "scientific-review"), verdict_relative_path=artifact.path,
        session=fixture._review_evidence().session, runner=runner, clock=lambda: fixture.ISSUED_AT,
    ).receipt


@pytest.mark.parametrize("kind", ["B", "C"])
@pytest.mark.parametrize("blocked", [False, True])
def test_actual_gate_is_bound_to_request_receipt_and_promotion(tmp_path, kind, blocked):
    gate = _gate(kind=kind, blocked=blocked)
    context, scope = _prepare(tmp_path, gate, kind=kind)
    request = json.loads((tmp_path / scope.review_request_relative).read_bytes())
    assert request["gate_result"] == gate.model_dump(mode="json")
    assert request["review_input_digest"] != fixture._review_bundle(context).input_digest
    receipt = _issue(tmp_path, context)
    # A blocked source review can be genuinely issued and reopened, not promoted.
    transition.accepted_verdict_from_receipt(
        project_root=tmp_path, context=context, receipt=receipt,
    )
    if blocked:
        with pytest.raises(transition.ScientificReviewTransitionError, match="门槛.*通过"):
            transition.promote_rendered_candidate(
                project_root=tmp_path, current_state=transition.RENDERED_UNREVIEWED,
                context=context, receipt=receipt,
            )
    else:
        assert transition.promote_rendered_candidate(
            project_root=tmp_path, current_state=transition.RENDERED_UNREVIEWED,
            context=context, receipt=receipt,
        ) == transition.SCIENTIFICALLY_REVIEWED_RENDERED_CANDIDATE


def test_legacy_c_request_cannot_authorize_new_promotion(tmp_path):
    context, _scope = _prepare(tmp_path, None, kind="C")
    receipt = _issue(tmp_path, context)
    with pytest.raises(transition.ScientificReviewTransitionError, match="门槛.*缺失"):
        transition.promote_rendered_candidate(
            project_root=tmp_path, current_state=transition.RENDERED_UNREVIEWED,
            context=context, receipt=receipt,
        )


@pytest.mark.parametrize("field,value", [
    ("candidate_snapshot_digest", "f" * 64), ("evidence_snapshot_id", "another-snapshot"),
    ("spec_version", "another-policy"), ("contract_version", "another-contract"),
])
def test_gate_from_other_context_cannot_be_published(tmp_path, field, value):
    raw = _gate().model_dump(mode="json")
    raw["report_kind"] = ReportKind.B
    raw[field] = value
    # Rebuild a coherent result, not merely an internally malformed model.
    gate = ReportGateResult.from_unit_results(
        **{key: raw[key] for key in (
            "report_kind", "evidence_snapshot_id", "candidate_snapshot_digest", "spec_version",
            "contract_version", "universe_summary", "spec_fingerprint",
        )}, unit_results=_gate().unit_results,
    )
    with pytest.raises(transition.ScientificReviewTransitionError, match="门槛.*绑定"):
        _prepare(tmp_path, gate)
    assert not (tmp_path / transition.scientific_review_request_path("B")).exists()


def test_republish_cannot_change_decision_under_same_decision_blind_key(tmp_path):
    context, scope = _prepare(tmp_path, _gate(blocked=True))
    before = (tmp_path / scope.review_request_relative).read_bytes()
    with pytest.raises(transition.ScientificReviewTransitionError, match="门槛.*首次"):
        _prepare(tmp_path, _gate(blocked=False))
    assert (tmp_path / scope.review_request_relative).read_bytes() == before
    assert context.gate_result_key == _gate().result_key == _gate(blocked=True).result_key


def test_rehashed_decision_change_still_invalidates_review_input(tmp_path):
    context, scope = _prepare(tmp_path, _gate(blocked=True))
    receipt = _issue(tmp_path, context)
    path = tmp_path / scope.review_request_relative
    raw = json.loads(path.read_bytes())
    raw["gate_result"] = _gate().model_dump(mode="json")
    raw.pop("request_digest")
    raw["request_digest"] = hashlib.sha256(
        (json.dumps(raw, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
    ).hexdigest()
    path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(transition.ScientificReviewTransitionError, match="审阅输入摘要"):
        transition.promote_rendered_candidate(
            project_root=tmp_path, current_state=transition.RENDERED_UNREVIEWED,
            context=context, receipt=receipt,
        )


def test_epoch_carries_actual_result_and_rejects_changed_exact_replay(tmp_path):
    previous, old_scope = _prepare(tmp_path, _gate(blocked=True))
    old_request = (tmp_path / old_scope.review_request_relative).read_bytes()
    gate = _gate()
    candidate_digest = "e" * 64
    next_gate = ReportGateResult.from_unit_results(
        report_kind=gate.report_kind, unit_results=gate.unit_results,
        evidence_snapshot_id=gate.evidence_snapshot_id,
        candidate_snapshot_digest=candidate_digest, spec_version=gate.spec_version,
        contract_version=gate.contract_version, universe_summary=gate.universe_summary,
        spec_fingerprint=gate.spec_fingerprint,
    )
    context = fixture._context(
        candidate_content_digest=candidate_digest, gate_result_key=next_gate.result_key,
    )
    args = dict(
        project_root=tmp_path, report_kind="B", expected_predecessor_context=previous,
        next_context=context, producer_session_id="next-producer-session",
        produced_at=fixture.PRODUCED_AT, portal_binding=fixture._portal_binding(tmp_path),
    )
    advanced = transition.advance_scientific_review_epoch(**args, gate_result=next_gate)
    assert advanced.activated_epoch == 1
    assert transition.advance_scientific_review_epoch(**args, gate_result=next_gate) == advanced
    request = json.loads((tmp_path / advanced.review_request_relative).read_bytes())
    assert request["gate_result"] == next_gate.model_dump(mode="json")
    assert (tmp_path / old_scope.review_request_relative).read_bytes() == old_request
    with pytest.raises(transition.ScientificReviewTransitionError, match="重放.*绑定"):
        # Missing result is not the same request.
        transition.advance_scientific_review_epoch(**args)


def test_gate_pass_flag_cannot_replace_a_valid_evaluated_result(tmp_path):
    context = fixture._context()
    fixture._portal_site(tmp_path)
    with pytest.raises(transition.ScientificReviewTransitionError, match="门槛.*无效"):
        transition.prepare_rendered_scientific_review(
            project_root=tmp_path, report_kind="B", context=context,
            producer_session_id="producer-session-1", produced_at=fixture.PRODUCED_AT,
            portal_binding=fixture._portal_binding(tmp_path), gate_result=True,
        )
    assert not (tmp_path / transition.scientific_review_request_path("B")).exists()
