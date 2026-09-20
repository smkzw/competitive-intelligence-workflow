from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from ci_workflow.reports.common.study_roles import (
    DecisionDomain,
    DevelopmentContext,
    IndicationRelation,
    ProblemDomain,
    StudyCandidate,
    StudyDesignCategory,
    StudyEvidenceType,
    StudyPhase,
    StudyRole,
    evaluate_study_role,
    load_study_role_policy,
)

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "policies" / "studies" / "study-role-v1.yaml"


def _candidate(**overrides: object) -> StudyCandidate:
    fields: dict[str, object] = {
        "study_id": "study-001",
        "report_kind": "B",
        "indication_relation": IndicationRelation.TARGET,
        "phase": StudyPhase.PHASE_II,
        "design_category": StudyDesignCategory.INTERVENTIONAL,
        "has_results": True,
        "is_key_or_registration": True,
        "development_contexts": (DevelopmentContext.ORDINARY,),
        "evidence_version": "evidence-v1",
    }
    fields.update(overrides)
    return StudyCandidate.model_validate(fields)


@pytest.mark.parametrize(
    ("design_category", "indication_relation", "rule_id"),
    [
        (
            StudyDesignCategory.HEALTHY_VOLUNTEER,
            IndicationRelation.TARGET,
            "exclude_healthy_volunteer",
        ),
        (
            StudyDesignCategory.PURE_PK_OR_BE,
            IndicationRelation.TARGET,
            "exclude_pure_pk_or_be",
        ),
        (
            StudyDesignCategory.INTERVENTIONAL,
            IndicationRelation.UNRELATED,
            "exclude_unrelated_indication",
        ),
        (
            StudyDesignCategory.OBSERVATIONAL,
            IndicationRelation.TARGET,
            "exclude_observational",
        ),
        (
            StudyDesignCategory.EAP_OR_COMPASSIONATE_USE,
            IndicationRelation.TARGET,
            "exclude_eap_compassionate_use",
        ),
    ],
)
def test_default_exclusion_rules_mechanically_exclude_five_study_classes(
    design_category: StudyDesignCategory,
    indication_relation: IndicationRelation,
    rule_id: str,
) -> None:
    decision = evaluate_study_role(
        _candidate(
            design_category=design_category,
            indication_relation=indication_relation,
        ),
        policy=load_study_role_policy(POLICY_PATH),
    )

    assert decision.study_role is StudyRole.EXCLUDED
    assert rule_id in decision.matched_rule_ids
    assert decision.evidence_version == "evidence-v1"


def test_supporting_layer_requires_named_problem_and_irreplaceable_evidence() -> None:
    policy = load_study_role_policy(POLICY_PATH)
    base = {
        "design_category": StudyDesignCategory.PURE_PK_OR_BE,
        "named_issue": "肝肾功能人群安全性证据",
        "issue_domain": ProblemDomain.SAFETY,
        "inclusion_rationale_zh": "该研究提供核心疗效试验无法替代的肝肾功能人群安全性证据。",
        "evidence_is_irreplaceable": True,
    }

    accepted = evaluate_study_role(_candidate(**base), policy=policy)
    assert accepted.study_role is StudyRole.SUPPORTING
    assert "support_named_problem" in accepted.matched_rule_ids
    assert accepted.inclusion_rationale_zh == base["inclusion_rationale_zh"]

    rejected = evaluate_study_role(
        _candidate(**{**base, "evidence_is_irreplaceable": False}),
        policy=policy,
    )
    assert rejected.study_role is StudyRole.EXCLUDED


def test_special_core_requires_named_context_and_irreplaceable_evidence() -> None:
    policy = load_study_role_policy(POLICY_PATH)
    base = {
        "phase": StudyPhase.PHASE_I,
        "development_contexts": (DevelopmentContext.RARE_DISEASE,),
        "named_issue": "罕见病人群的剂量与安全性决策证据",
        "issue_domain": ProblemDomain.SPECIAL_POPULATION,
        "decision_domain": DecisionDomain.DOSE,
        "inclusion_rationale_zh": "该早期试验提供罕见病剂量决策所需且核心试验无法替代的证据。",
        "evidence_is_irreplaceable": True,
    }

    accepted = evaluate_study_role(_candidate(**base), policy=policy)
    assert accepted.study_role is StudyRole.SPECIAL_CORE
    assert "special_core_early" in accepted.matched_rule_ids

    rejected = evaluate_study_role(
        _candidate(**{**base, "evidence_is_irreplaceable": False}),
        policy=policy,
    )
    assert rejected.study_role is StudyRole.SUPPORTING
    assert "special_core_early" not in rejected.matched_rule_ids

    no_result = evaluate_study_role(
        _candidate(**{**base, "has_results": False}),
        policy=policy,
    )
    assert no_result.study_role is StudyRole.SUPPORTING
    assert "special_core_early" not in no_result.matched_rule_ids


def test_c_early_study_accepts_only_specific_decision_domain() -> None:
    policy = load_study_role_policy(POLICY_PATH)
    accepted = evaluate_study_role(
        _candidate(
            report_kind="C",
            phase=StudyPhase.PHASE_I,
            has_results=False,
            is_key_or_registration=False,
            decision_domain=DecisionDomain.ADAPTIVE_DESIGN,
            inclusion_rationale_zh="用于评估无缝适应性设计的停步与扩展决策。",
        ),
        policy=policy,
    )
    assert accepted.study_role is StudyRole.CORE
    assert "c_early_decision_domain" in accepted.matched_rule_ids

    rejected = evaluate_study_role(
        _candidate(
            report_kind="C",
            phase=StudyPhase.PHASE_I,
            has_results=False,
            is_key_or_registration=False,
            inclusion_rationale_zh="这项研究很重要。",
        ),
        policy=policy,
    )
    assert rejected.study_role is StudyRole.EXCLUDED

    generic_rationale = evaluate_study_role(
        _candidate(
            report_kind="C",
            phase=StudyPhase.PHASE_I,
            has_results=False,
            is_key_or_registration=False,
            decision_domain=DecisionDomain.DOSE,
            inclusion_rationale_zh="这项研究很重要。",
        ),
        policy=policy,
    )
    assert generic_rationale.study_role is StudyRole.EXCLUDED

    weak_domain_reference = evaluate_study_role(
        _candidate(
            report_kind="C",
            phase=StudyPhase.PHASE_I,
            has_results=False,
            is_key_or_registration=False,
            decision_domain=DecisionDomain.DOSE,
            inclusion_rationale_zh="这是需要关注的重要证据。",
        ),
        policy=policy,
    )
    assert weak_domain_reference.study_role is StudyRole.EXCLUDED


@pytest.mark.parametrize(
    "evidence_type",
    [
        StudyEvidenceType.EXTENSION,
        StudyEvidenceType.SUBGROUP,
        StudyEvidenceType.POST_HOC,
        StudyEvidenceType.REAL_WORLD,
    ],
)
def test_b_named_supporting_evidence_types_are_not_silently_discarded(
    evidence_type: StudyEvidenceType,
) -> None:
    decision = evaluate_study_role(
        _candidate(
            phase=StudyPhase.PHASE_I,
            design_category=(
                StudyDesignCategory.OBSERVATIONAL
                if evidence_type is StudyEvidenceType.REAL_WORLD
                else StudyDesignCategory.INTERVENTIONAL
            ),
            is_key_or_registration=False,
            evidence_type=evidence_type,
            inclusion_rationale_zh="该结果用于补充核心试验未覆盖的长期或特定人群观察。",
        ),
        policy=load_study_role_policy(POLICY_PATH),
    )

    assert decision.study_role is StudyRole.SUPPORTING
    assert "support_b_contextual_evidence" in decision.matched_rule_ids


@pytest.mark.parametrize(
    "evidence_type",
    [
        StudyEvidenceType.EXTENSION,
        StudyEvidenceType.SUBGROUP,
        StudyEvidenceType.POST_HOC,
        StudyEvidenceType.REAL_WORLD,
    ],
)
def test_key_phase_iii_contextual_evidence_stays_supporting(
    evidence_type: StudyEvidenceType,
) -> None:
    decision = evaluate_study_role(
        _candidate(
            phase=StudyPhase.PHASE_III,
            design_category=StudyDesignCategory.INTERVENTIONAL,
            is_key_or_registration=True,
            evidence_type=evidence_type,
            inclusion_rationale_zh="该结果用于补充母试验未覆盖的长期或特定人群观察。",
        ),
        policy=load_study_role_policy(POLICY_PATH),
    )

    assert decision.study_role is StudyRole.SUPPORTING
    assert "core_b_phase_ii_iii" not in decision.matched_rule_ids
    assert "support_b_contextual_evidence" in decision.matched_rule_ids


def test_b_result_bearing_early_trial_enters_supporting_layer() -> None:
    decision = evaluate_study_role(
        _candidate(
            phase=StudyPhase.PHASE_I,
            is_key_or_registration=False,
            inclusion_rationale_zh="该早期结果用于补充剂量探索与初步疗效观察。",
        ),
        policy=load_study_role_policy(POLICY_PATH),
    )

    assert decision.study_role is StudyRole.SUPPORTING
    assert "support_b_early_result" in decision.matched_rule_ids


def test_study_policy_rejects_semantically_duplicated_role_rules(
    tmp_path: Path,
) -> None:
    payload = yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    rules = payload["rules"]
    assert isinstance(rules, list)
    duplicated = dict(rules[1])
    duplicated["rule_id"] = "duplicate-core-rule"
    duplicated["rationale_zh"] = "换一种说法但判定条件完全相同。"
    rules.append(duplicated)
    path = tmp_path / "ambiguous-study-role.yaml"
    path.write_text(yaml.safe_dump(payload, allow_unicode=True), encoding="utf-8")

    with pytest.raises(ValueError, match="重复|歧义"):
        load_study_role_policy(path)


def test_study_policy_rejects_same_eligibility_with_conflicting_roles(
    tmp_path: Path,
) -> None:
    payload = yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    rules = payload["rules"]
    assert isinstance(rules, list)
    conflicting = dict(rules[2])
    conflicting.update(
        {
            "rule_id": "conflicting-core-eligibility",
            "role": "supporting",
            "priority": 81,
            "requires_specific_rationale": True,
            "rationale_zh": "相同适用条件不得依靠优先级改写研究角色。",
        }
    )
    rules.append(conflicting)
    path = tmp_path / "conflicting-study-role.yaml"
    path.write_text(yaml.safe_dump(payload, allow_unicode=True), encoding="utf-8")

    with pytest.raises(ValueError, match="角色冲突"):
        load_study_role_policy(path)


def test_model_copy_unknown_field_fails_closed() -> None:
    forged = _candidate().model_copy(update={"study_role": "core"})

    with pytest.raises(ValueError, match="重新校验"):
        evaluate_study_role(forged)


def test_study_role_is_derived_without_publication_role_override() -> None:
    policy = load_study_role_policy(POLICY_PATH)
    candidate = _candidate()
    decision = evaluate_study_role(candidate, policy=policy)

    assert decision.study_role is StudyRole.CORE
    assert "publication_role" not in type(decision).model_fields
    assert decision.policy_version == policy.version
    assert decision.evidence_version == candidate.evidence_version
