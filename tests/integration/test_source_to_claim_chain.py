from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from jsonschema import Draft202012Validator, FormatChecker, ValidationError

ROOT = Path(__file__).resolve().parents[2]


def test_extraction_preserves_raw_value_unit_arm_population_time_denominator_method_and_state() -> None:  # noqa: E501
    from ci_workflow.capabilities.extraction_normalization import (
        AtomicFactExtractionInput,
        extract_atomic_fact,
        verify_reopened_fragment,
    )
    from ci_workflow.domain.enums import FactDisclosureState, FactReviewState
    from ci_workflow.domain.evidence import EvidenceFragmentRecord, EvidenceLocator
    from ci_workflow.domain.facts import AtomicFactVersion

    fragment = EvidenceFragmentRecord(
        schema_version="1.0",
        fragment_id="fragment-primary-endpoint-arm-a-week-24",
        source_version_id="source-version-registry-results-001",
        locator=EvidenceLocator(
            document_role="临床试验登记结果",
            field_path="resultsSection.outcomeMeasuresModule.outcomeMeasures[0].classes[0].categories[0].measurements[0].value",
            url="https://clinicaltrials.gov/study/NCT01234567?format=json",
        ),
        original_text="-2.1",
        content_sha256=hashlib.sha256(b"-2.1").hexdigest(),
        created_at=datetime(2026, 8, 12, 0, 50, tzinfo=ZoneInfo("Asia/Shanghai")),
    )
    verified = verify_reopened_fragment(
        fragment,
        reopened_original_text="-2.1",
        source_version_id="source-version-registry-results-001",
    )
    extraction_input = AtomicFactExtractionInput(
            entity_id="trial-arm-CMS-K10-301-treatment",
            field_id="efficacy.nps.change_from_baseline",
            raw_value="-2.1",
            unit="分",
            context="双侧鼻息肉评分较基线变化",
            arm_id="arm-treatment-300mg-q4w",
            cohort_id="cohort-randomized",
            population="全分析集",
            timepoint="第 24 周",
            time_window=None,
            numerator=None,
            denominator=210,
            extraction_method="登记 JSON 精确字段抽取",
            quality_state="来源字段与组别、时间点交叉核对通过",
            disclosure_maturity="登记平台已发布结果",
            source_role="clinical_trial_registry",
            disclosure_state=FactDisclosureState.REPORTED_VALUE,
            review_state=FactReviewState.CANDIDATE,
            published_at=datetime(2026, 7, 1, 8, 0, tzinfo=ZoneInfo("Asia/Shanghai")),
            effective_at=None,
            created_at=datetime(2026, 8, 12, 0, 51, tzinfo=ZoneInfo("Asia/Shanghai")),
            verified_fragment=verified,
    )
    fact = extract_atomic_fact(extraction_input)
    next_day_same_fact = extract_atomic_fact(
        extraction_input.model_copy(
            update={
                "created_at": datetime(
                    2026, 8, 13, 0, 51, tzinfo=ZoneInfo("Asia/Shanghai")
                )
            }
        )
    )
    same_scientific_fact_after_review = extract_atomic_fact(
        extraction_input.model_copy(update={"review_state": FactReviewState.ACCEPTED})
    )

    assert fact.raw_value == "-2.1"
    assert fact.normalized_value is None
    assert fact.unit == "分"
    assert fact.context == "双侧鼻息肉评分较基线变化"
    assert fact.arm_id == "arm-treatment-300mg-q4w"
    assert fact.cohort_id == "cohort-randomized"
    assert fact.population == "全分析集"
    assert fact.timepoint == "第 24 周"
    assert fact.time_window is None
    assert fact.numerator is None
    assert fact.denominator == 210
    assert fact.primary_fragment_id == fragment.fragment_id
    assert fact.source_fragment_ids == (fragment.fragment_id,)
    assert fact.extraction_method == "登记 JSON 精确字段抽取"
    assert fact.quality_state == "来源字段与组别、时间点交叉核对通过"
    assert fact.disclosure_maturity == "登记平台已发布结果"
    assert fact.source_role == "clinical_trial_registry"
    assert fact.disclosure_state is FactDisclosureState.REPORTED_VALUE
    assert fact.review_state is FactReviewState.CANDIDATE
    assert fact.published_at is not None
    assert fact.published_at.isoformat() == "2026-07-01T08:00:00+08:00"
    assert fact.normalization is None
    assert fact.fact_id
    assert fact.fact_version_id
    assert next_day_same_fact.fact_version_id == fact.fact_version_id
    assert same_scientific_fact_after_review.fact_version_id == fact.fact_version_id
    fact_validator = Draft202012Validator(
        json.loads((ROOT / "schemas/fact.schema.json").read_text(encoding="utf-8")),
        format_checker=FormatChecker(),
    )
    fact_validator.validate(fact.model_dump(mode="json"))
    missing_time_document = {
        **fact.model_dump(mode="json"),
        "timepoint": None,
        "time_window": None,
    }
    with pytest.raises(ValidationError):
        fact_validator.validate(missing_time_document)
    reported_without_raw_document = {
        **fact.model_dump(mode="json"),
        "raw_value": None,
    }
    with pytest.raises(ValidationError):
        fact_validator.validate(reported_without_raw_document)
    with pytest.raises(ValueError, match="零值"):
        AtomicFactVersion.model_validate(
            {
                **fact.model_dump(),
                "raw_value": "5",
                "disclosure_state": FactDisclosureState.REPORTED_ZERO,
            }
        )
    for invalid_zero_value in ("0", True, False):
        with pytest.raises(ValueError, match="规范值必须为零"):
            AtomicFactVersion.model_validate(
                {
                    **fact.model_dump(),
                    "raw_value": "0",
                    "normalized_value": invalid_zero_value,
                    "normalized_unit": "分",
                    "normalization": {
                        "rule_id": "numeric-decimal-v1",
                        "rule_version": "1.0",
                        "method_zh": "解析数值",
                        "original_raw_value": "0",
                        "normalized_value": invalid_zero_value,
                        "normalized_unit": "分",
                        "reversible": True,
                        "reverse_expression": "返回原文 0",
                        "created_at": fact.created_at,
                    },
                    "disclosure_state": FactDisclosureState.REPORTED_ZERO,
                }
            )
    with pytest.raises(ValueError, match="不得携带数值型"):
        AtomicFactVersion.model_validate(
            {
                **fact.model_dump(),
                "raw_value": "-2.1 分",
                "disclosure_state": FactDisclosureState.NOT_REPORTED,
            }
        )
    missing_text = AtomicFactVersion.model_validate(
        {
            **fact.model_dump(),
            "raw_value": "结果未报告",
            "disclosure_state": FactDisclosureState.NOT_REPORTED,
        }
    )
    fact_validator.validate(missing_text.model_dump(mode="json"))
    fullwidth_numeric_missing_document = {
        **missing_text.model_dump(mode="json"),
        "raw_value": "５０％",
    }
    with pytest.raises(ValidationError):
        fact_validator.validate(fullwidth_numeric_missing_document)


def test_normalization_is_versioned_reversible_and_never_overwrites_raw_value() -> None:
    from ci_workflow.capabilities.extraction_normalization import (
        FactNormalizationInput,
        normalize_fact,
        reverse_normalized_fact,
    )
    from ci_workflow.domain.enums import FactDisclosureState, FactReviewState
    from ci_workflow.domain.facts import AtomicFactVersion

    raw_fact = AtomicFactVersion(
        fact_id="fact-nps-change-treatment-week-24",
        fact_version_id="fact-version-nps-change-raw-v1",
        entity_id="trial-arm-CMS-K10-301-treatment",
        field_id="efficacy.nps.change_from_baseline",
        raw_value="-2.10",
        normalized_value=None,
        unit="分",
        normalized_unit=None,
        context="双侧鼻息肉评分较基线变化",
        arm_id="arm-treatment-300mg-q4w",
        cohort_id="cohort-randomized",
        population="全分析集",
        timepoint="第 24 周",
        time_window=None,
        numerator=None,
        denominator=210,
        primary_fragment_id="fragment-primary-endpoint-arm-a-week-24",
        source_fragment_ids=("fragment-primary-endpoint-arm-a-week-24",),
        extraction_method="登记 JSON 精确字段抽取",
        quality_state="来源字段与组别、时间点交叉核对通过",
        disclosure_maturity="登记平台已发布结果",
        source_role="clinical_trial_registry",
        disclosure_state=FactDisclosureState.REPORTED_VALUE,
        review_state=FactReviewState.CANDIDATE,
        normalization=None,
        published_at=datetime(2026, 7, 1, 8, 0, tzinfo=ZoneInfo("Asia/Shanghai")),
        effective_at=None,
        created_at=datetime(2026, 8, 12, 0, 51, tzinfo=ZoneInfo("Asia/Shanghai")),
    )
    normalization_input = FactNormalizationInput(
            rule_id="numeric-decimal-v1",
            rule_version="1.0",
            method_zh="保留方向并将数值文本解析为十进制数",
            normalized_value=-2.1,
            normalized_unit="分",
            reverse_expression="按原始表达字段返回 -2.10",
            created_at=datetime(2026, 8, 12, 0, 52, tzinfo=ZoneInfo("Asia/Shanghai")),
    )
    normalized = normalize_fact(raw_fact, normalization_input)
    repeated_normalization = normalize_fact(
        raw_fact,
        normalization_input.model_copy(
            update={
                "created_at": datetime(
                    2026, 8, 13, 0, 52, tzinfo=ZoneInfo("Asia/Shanghai")
                )
            }
        ),
    )
    repeated_on_normalized = normalize_fact(
        normalized,
        normalization_input.model_copy(
            update={
                "created_at": datetime(
                    2026, 8, 14, 0, 52, tzinfo=ZoneInfo("Asia/Shanghai")
                )
            }
        ),
    )
    revised_rule = normalize_fact(
        normalized,
        FactNormalizationInput(
            rule_id="numeric-decimal-v1",
            rule_version="1.1",
            method_zh="升级解析器但保持原始表达和数值方向",
            normalized_value=-2.1,
            normalized_unit="分",
            reverse_expression="按原始表达字段返回 -2.10",
            created_at=datetime(2026, 8, 12, 0, 53, tzinfo=ZoneInfo("Asia/Shanghai")),
        ),
    )

    assert raw_fact.raw_value == "-2.10"
    assert raw_fact.normalized_value is None
    assert raw_fact.normalization is None
    assert normalized.raw_value == "-2.10"
    assert normalized.normalized_value == -2.1
    assert normalized.normalized_unit == "分"
    assert normalized.normalization is not None
    assert normalized.normalization.rule_version == "1.0"
    assert normalized.normalization.original_raw_value == "-2.10"
    assert normalized.supersedes_fact_version_id == raw_fact.fact_version_id
    assert normalized.fact_id == raw_fact.fact_id
    assert normalized.fact_version_id != raw_fact.fact_version_id
    assert repeated_normalization.fact_version_id == normalized.fact_version_id
    assert repeated_on_normalized == normalized
    with pytest.raises(ValueError, match="同一规范化规则版本不得产生不同结果"):
        normalize_fact(
            normalized,
            normalization_input.model_copy(update={"normalized_value": -9.9}),
        )
    assert reverse_normalized_fact(normalized) == "-2.10"
    assert revised_rule.normalization is not None
    assert revised_rule.normalization.rule_version == "1.1"
    assert revised_rule.fact_version_id != normalized.fact_version_id
    assert revised_rule.supersedes_fact_version_id == normalized.fact_version_id
    assert reverse_normalized_fact(revised_rule) == "-2.10"


def test_claim_kind_supporting_facts_and_deterministic_calculation_are_explicit() -> None:  # noqa: E501
    from ci_workflow.capabilities.resolution import (
        create_deterministic_difference_claim,
        create_direct_evidence_claim,
        create_synthesis_claim,
    )
    from ci_workflow.domain.claims import ClaimVersion
    from ci_workflow.domain.enums import FactDisclosureState, FactReviewState
    from ci_workflow.domain.facts import AtomicFactVersion

    def fact(
        *, value: str, arm_id: str, version_id: str, fragment_id: str
    ) -> AtomicFactVersion:
        return AtomicFactVersion(
            fact_id=f"fact-{arm_id}-nps-week24",
            fact_version_id=version_id,
            entity_id=f"trial-arm-{arm_id}",
            field_id="efficacy.nps.change_from_baseline",
            raw_value=value,
            normalized_value=None,
            unit="分",
            normalized_unit=None,
            context="双侧鼻息肉评分较基线变化",
            arm_id=arm_id,
            cohort_id="cohort-randomized",
            population="全分析集",
            timepoint="第 24 周",
            time_window=None,
            numerator=None,
            denominator=210,
            primary_fragment_id=fragment_id,
            source_fragment_ids=(fragment_id,),
            extraction_method="登记结果精确字段抽取",
            quality_state="已核对",
            disclosure_maturity="登记平台已发布结果",
            source_role="clinical_trial_registry",
            disclosure_state=FactDisclosureState.REPORTED_VALUE,
            review_state=FactReviewState.ACCEPTED,
            normalization=None,
            published_at=datetime(
                2026, 7, 1, 8, 0, tzinfo=ZoneInfo("Asia/Shanghai")
            ),
            effective_at=None,
            created_at=datetime(
                2026, 8, 12, 1, 10, tzinfo=ZoneInfo("Asia/Shanghai")
            ),
        )

    treatment = fact(
        value="-2.1",
        arm_id="treatment-300mg-q4w",
        version_id="fact-version-treatment",
        fragment_id="fragment-treatment",
    )
    control = fact(
        value="-0.8",
        arm_id="placebo-q4w",
        version_id="fact-version-control",
        fragment_id="fragment-control",
    )
    created_at = datetime(2026, 8, 12, 1, 11, tzinfo=ZoneInfo("Asia/Shanghai"))
    direct = create_direct_evidence_claim(
        claim_identity="claim-treatment-nps-week24",
        claim_text="试验组第 24 周 NPS 较基线变化为 -2.1 分。",
        supporting_facts=(treatment,),
        created_at=created_at,
    )
    calculated = create_deterministic_difference_claim(
        claim_identity="claim-between-arm-nps-week24",
        claim_text="第 24 周试验组与安慰剂组的组间差为 -1.3 分。",
        treatment_fact=treatment,
        control_fact=control,
        created_at=created_at,
    )
    magnitude_wording = create_deterministic_difference_claim(
        claim_identity="claim-between-arm-nps-week24-magnitude-wording",
        claim_text="试验组下降 2.1 分，安慰剂组下降 0.8 分，组间差为 1.3 分。",
        treatment_fact=treatment,
        control_fact=control,
        created_at=created_at,
    )
    synthesis = create_synthesis_claim(
        claim_identity="claim-nps-clinical-interpretation-week24",
        claim_text="AI 综合判断：试验组在第 24 周显示更大的 NPS 改善。",
        supporting_facts=(treatment, control),
        synthesis_method_zh="比较同一试验、同一人群和时间点的治疗组与安慰剂组方向和幅度",
        created_at=created_at,
    )

    assert direct.claim_kind == "direct_evidence"
    assert direct.supporting_fact_version_ids == (treatment.fact_version_id,)
    assert direct.calculation is None
    assert direct.synthesis_method_zh is None
    assert calculated.claim_kind == "deterministic_calculation"
    assert calculated.supporting_fact_version_ids == (
        control.fact_version_id,
        treatment.fact_version_id,
    )
    assert calculated.calculation is not None
    assert calculated.calculation.operation == "treatment_minus_control"
    assert calculated.calculation.input_values == (-2.1, -0.8)
    assert calculated.calculation.result == -1.3
    assert calculated.calculation.unit == "分"
    assert magnitude_wording.calculation is not None
    assert magnitude_wording.calculation.result == -1.3
    assert synthesis.claim_kind == "synthesis"
    assert synthesis.supporting_fact_version_ids == (
        control.fact_version_id,
        treatment.fact_version_id,
    )
    assert synthesis.calculation is None
    assert synthesis.synthesis_method_zh is not None
    assert synthesis.ai_disclosure_label_zh == "AI 综合判断"
    assert all(link.support_role == "supports" for link in synthesis.fact_links)
    claim_validator = Draft202012Validator(
        json.loads((ROOT / "schemas/claim.schema.json").read_text(encoding="utf-8")),
        format_checker=FormatChecker(),
    )
    for claim in (direct, calculated, synthesis):
        claim_validator.validate(claim.model_dump(mode="json"))
    with pytest.raises(ValueError, match="声明文字与复算结果不一致"):
        create_deterministic_difference_claim(
            claim_identity="claim-wrong-calculation-text",
            claim_text="第 24 周试验组与安慰剂组的组间差为 -9.9 分。",
            treatment_fact=treatment,
            control_fact=control,
            created_at=created_at,
        )
    for invalid_magnitude_text in (
        "试验组下降 9.9 分，安慰剂组下降 0.8 分，组间差为 1.3 分。",
        "试验组上升 2.1 分，安慰剂组上升 0.8 分，组间差为 1.3 分。",
        "试验组下降 2.1 分，组间差为 1.3 分，另次访视下降 9.9 分。",
    ):
        with pytest.raises(ValueError, match="声明文字与复算结果不一致"):
            create_deterministic_difference_claim(
                claim_identity="claim-invalid-magnitude-wording",
                claim_text=invalid_magnitude_text,
                treatment_fact=treatment,
                control_fact=control,
                created_at=created_at,
            )
    with pytest.raises(ValueError, match="声明文字与复算结果不一致"):
        create_deterministic_difference_claim(
            claim_identity="claim-contradictory-calculation-text",
            claim_text="组间差为 -1.3 分，但手算为 -9.9 分。",
            treatment_fact=treatment,
            control_fact=control,
            created_at=created_at,
        )
    with pytest.raises(ValueError, match="必须在文字中明确标识"):
        create_synthesis_claim(
            claim_identity="claim-unlabelled-ai-synthesis",
            claim_text="试验组在第 24 周显示更大的 NPS 改善。",
            supporting_facts=(treatment, control),
            synthesis_method_zh="比较同一试验、同一人群和时间点的组间差异",
            created_at=created_at,
        )
    with pytest.raises(ValueError, match="必须在文字中明确标识"):
        ClaimVersion.model_validate(
            {**synthesis.model_dump(), "claim_text": "试验组显示更大的改善。"}
        )
    with pytest.raises(ValueError):
        ClaimVersion.model_validate(
            {
                **direct.model_dump(),
                "fact_links": [
                    {
                        **direct.fact_links[0].model_dump(),
                        "fact_review_state": "candidate",
                    }
                ],
            }
        )
