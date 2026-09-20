from __future__ import annotations

from pathlib import Path

import pytest

from ci_workflow.reports.b.contracts import (
    TrialRoleOutput,
    build_trial_role_output,
)
from ci_workflow.reports.common.study_roles import (
    IndicationRelation,
    StudyCandidate,
    StudyDesignCategory,
    StudyPhase,
    StudyRole,
    load_study_role_policy,
)
from ci_workflow.sources.connectors.pubmed import (
    ClassifiedPublication,
    PubMedRecord,
    classify_pubmed_records,
)

ROOT = Path(__file__).resolve().parents[3]
POLICY_PATH = ROOT / "policies" / "studies" / "study-role-v1.yaml"


def _candidate(**overrides: object) -> StudyCandidate:
    fields: dict[str, object] = {
        "study_id": "NCT00000001",
        "report_kind": "B",
        "indication_relation": IndicationRelation.TARGET,
        "phase": StudyPhase.PHASE_III,
        "design_category": StudyDesignCategory.INTERVENTIONAL,
        "has_results": True,
        "is_key_or_registration": True,
        "evidence_version": "evidence-v1",
    }
    fields.update(overrides)
    return StudyCandidate.model_validate(fields)


def _publication(
    *,
    pmid: str,
    title: str,
    abstract: str,
    publication_types: tuple[str, ...] = (),
) -> ClassifiedPublication:
    record = PubMedRecord(
        pmid=pmid,
        title=title,
        abstract=abstract,
        publication_types=publication_types,
    )
    return classify_pubmed_records((record,), target_nct_ids=("NCT00000001",))[0]


def test_b_output_keeps_study_and_publication_roles_in_separate_fields() -> None:
    publication = _publication(
        pmid="1001",
        title="NCT00000001 phase 3 primary endpoint results",
        abstract=(
            "NCT00000001 was a randomized controlled trial. "
            "The primary endpoint results showed efficacy and safety."
        ),
        publication_types=("Randomized Controlled Trial",),
    )

    output = build_trial_role_output(
        _candidate(),
        publication=publication,
        policy=load_study_role_policy(POLICY_PATH),
    )

    assert isinstance(output, TrialRoleOutput)
    assert output.study_id == "NCT00000001"
    assert output.study_role is StudyRole.CORE
    assert output.publication_role == "primary_report"
    assert output.study_role != output.publication_role
    assert output.publication_id == "1001"
    assert output.study_role_policy_version == "1.0"
    assert output.evidence_version == "evidence-v1"
    assert {"study_role", "publication_role"} <= output.model_fields_set


def test_publication_role_change_does_not_rewrite_mother_trial_role() -> None:
    candidate = _candidate()
    primary = _publication(
        pmid="1001",
        title="NCT00000001 phase 3 primary endpoint results",
        abstract=(
            "NCT00000001 was a randomized controlled trial. "
            "The primary endpoint results showed efficacy and safety."
        ),
        publication_types=("Randomized Controlled Trial",),
    )
    post_hoc = _publication(
        pmid="1002",
        title="Post hoc subgroup analysis of NCT00000001",
        abstract="NCT00000001 reported an exploratory analysis.",
    )

    primary_output = build_trial_role_output(candidate, publication=primary)
    post_hoc_output = build_trial_role_output(candidate, publication=post_hoc)

    assert primary_output.study_role is StudyRole.CORE
    assert post_hoc_output.study_role is StudyRole.CORE
    assert primary_output.publication_role == "primary_report"
    assert post_hoc_output.publication_role == "ad_hoc_analysis"
    assert primary_output.study_role_policy_version == post_hoc_output.study_role_policy_version
    assert primary_output.evidence_version == post_hoc_output.evidence_version


def test_non_default_study_role_output_retains_rule_and_evidence_lineage() -> None:
    output = build_trial_role_output(
        _candidate(
            design_category=StudyDesignCategory.PURE_PK_OR_BE,
            named_issue="肝肾功能人群安全性证据",
            issue_domain="safety",
            evidence_is_irreplaceable=True,
            inclusion_rationale_zh="该研究提供核心疗效试验无法替代的肝肾功能人群安全性证据。",
        )
    )

    assert output.study_role is StudyRole.SUPPORTING
    assert output.matched_study_rule_ids[0] == "support_named_problem"
    assert "exclude_pure_pk_or_be" in output.matched_study_rule_ids
    assert output.study_role_policy_id == "study-role-v1"
    assert output.study_role_policy_version == "1.0"
    assert output.evidence_version == "evidence-v1"
    assert output.inclusion_rationale_zh.startswith("该研究提供")
    assert output.publication_role == "unclassified"


def test_output_rejects_manual_study_role_override() -> None:
    candidate = _candidate().model_dump(mode="python")
    candidate["study_role"] = "excluded"

    with pytest.raises(ValueError):
        build_trial_role_output(candidate)


def test_output_reclassifies_model_copy_tampered_publication() -> None:
    publication = _publication(
        pmid="1001",
        title="NCT00000001 phase 3 primary endpoint results",
        abstract=(
            "NCT00000001 was a randomized controlled trial. "
            "The primary endpoint results showed efficacy and safety."
        ),
        publication_types=("Randomized Controlled Trial",),
    )
    forged = publication.model_copy(update={"role": "review", "matched_nct_ids": ()})

    with pytest.raises(ValueError, match="重新分类"):
        build_trial_role_output(_candidate(), publication=forged)


def test_non_nct_publication_role_fails_closed_until_identity_can_be_recomputed() -> None:
    publication = _publication(
        pmid="1001",
        title="NCT00000001 phase 3 primary endpoint results",
        abstract=(
            "NCT00000001 was a randomized controlled trial. "
            "The primary endpoint results showed efficacy and safety."
        ),
        publication_types=("Randomized Controlled Trial",),
    )

    with pytest.raises(ValueError, match="非 NCT|重新计算"):
        build_trial_role_output(_candidate(study_id="ChiCTR2100000001"), publication=publication)
