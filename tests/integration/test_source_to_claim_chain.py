from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from jsonschema import Draft202012Validator, FormatChecker, ValidationError

ROOT = Path(__file__).resolve().parents[2]


def _repository_for_text(
    tmp_path: Path,
    *,
    content: str,
    source_id: str,
    timestamp: datetime,
    first_disclosed_at: datetime | None = None,
):
    from ci_workflow.domain.evidence import DateEvidence, EvidenceLocator
    from ci_workflow.storage.content_store import ContentAddressedStore, EvidenceRepository
    from ci_workflow.storage.migrations import apply_migrations

    project_root = tmp_path / source_id
    database_path = project_root / "state/project.sqlite"
    apply_migrations(database_path)
    repository = EvidenceRepository(database_path, ContentAddressedStore(project_root))
    locator = EvidenceLocator(document_role="测试来源原文", paragraph="已保存完整正文")
    disclosed = (
        DateEvidence(state="reported", value=first_disclosed_at, locator=locator)
        if first_disclosed_at is not None
        else DateEvidence(state="not_publicly_disclosed", value=None, locator=locator)
    )
    source_version = repository.add_source_version(
        source_id=source_id,
        content=content.encode("utf-8"),
        media_type="application/json",
        acquired_at=timestamp,
        published_at=disclosed,
        effective_at=DateEvidence(state="not_applicable", value=None, locator=locator),
        first_disclosed_at=disclosed,
    )
    return repository, source_version


def test_extraction_preserves_raw_value_unit_arm_population_time_denominator_method_and_state(
    tmp_path: Path,
) -> None:
    from ci_workflow.capabilities.extraction_normalization import (
        AtomicFactExtractionInput,
        extract_atomic_fact,
        verify_reopened_fragment,
    )
    from ci_workflow.domain.enums import FactDisclosureState, FactReviewState
    from ci_workflow.domain.evidence import EvidenceLocator
    from ci_workflow.domain.facts import AtomicFactVersion

    timestamp = datetime(2026, 8, 12, 0, 50, tzinfo=ZoneInfo("Asia/Shanghai"))
    repository, source_version = _repository_for_text(
        tmp_path,
        content="-2.1",
        source_id="source-registry-results-001",
        timestamp=timestamp,
    )
    fragment = repository.add_fragment(
        source_version_id=source_version.source_version_id,
        locator=EvidenceLocator(
            document_role="临床试验登记结果",
            field_path="resultsSection.outcomeMeasuresModule.outcomeMeasures[0].classes[0].categories[0].measurements[0].value",
            url="https://clinicaltrials.gov/study/NCT01234567?format=json",
        ),
        original_text="-2.1",
        created_at=timestamp,
    )
    verified = verify_reopened_fragment(
        fragment,
        reopened_original_text="-2.1",
        source_version_id=source_version.source_version_id,
        repository=repository,
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


def test_verified_fragment_must_reopen_from_project_truth_source(
    tmp_path: Path,
) -> None:
    from ci_workflow.capabilities.extraction_normalization import (
        verify_reopened_fragment,
    )
    from ci_workflow.domain.evidence import EvidenceLocator
    from ci_workflow.storage.content_store import ContentIntegrityError

    timestamp = datetime(2026, 8, 12, 0, 55, tzinfo=ZoneInfo("Asia/Shanghai"))
    repository, source_version = _repository_for_text(
        tmp_path,
        content="已保存原文只包含治疗组 -2.1。",
        source_id="source-fragment-reopen-negative",
        timestamp=timestamp,
    )
    fabricated = repository.add_fragment(
        source_version_id=source_version.source_version_id,
        locator=EvidenceLocator(
            document_role="临床试验登记结果",
            paragraph="并不存在的对照组 -9.9。",
        ),
        original_text="并不存在的对照组 -9.9。",
        created_at=timestamp,
    )
    with pytest.raises(ContentIntegrityError, match="不存在于已保存来源正文"):
        verify_reopened_fragment(
            fabricated,
            reopened_original_text=fabricated.original_text,
            source_version_id=source_version.source_version_id,
            repository=repository,
        )


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


def test_claim_kind_supporting_facts_and_deterministic_calculation_are_explicit(
    tmp_path: Path,
) -> None:
    from ci_workflow.capabilities.extraction_normalization import verify_reopened_fragment
    from ci_workflow.capabilities.lineage_registry import ScientificLineageRegistry
    from ci_workflow.capabilities.resolution import (
        create_deterministic_difference_claim,
        create_direct_evidence_claim,
        create_synthesis_claim,
    )
    from ci_workflow.domain.claims import ClaimVersion
    from ci_workflow.domain.enums import FactDisclosureState, FactReviewState
    from ci_workflow.domain.evidence import EvidenceLocator
    from ci_workflow.domain.facts import AtomicFactVersion

    def fact(
        *, value: str, arm_id: str, version_id: str, fragment_id: str
    ) -> AtomicFactVersion:
        return AtomicFactVersion(
            fact_id=f"fact-{arm_id}-nps-week24",
            fact_version_id=version_id,
            entity_id="trial-nps-week24",
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
            review_state=FactReviewState.CANDIDATE,
            normalization=None,
            published_at=datetime(
                2026, 7, 1, 8, 0, tzinfo=ZoneInfo("Asia/Shanghai")
            ),
            effective_at=None,
            created_at=datetime(
                2026, 8, 12, 1, 10, tzinfo=ZoneInfo("Asia/Shanghai")
            ),
        )

    created_at = datetime(2026, 8, 12, 1, 11, tzinfo=ZoneInfo("Asia/Shanghai"))
    repository, source_version = _repository_for_text(
        tmp_path,
        content="-2.1\n-0.8",
        source_id="source-version-claims-test",
        timestamp=created_at,
    )
    treatment_fragment = repository.add_fragment(
        source_version_id=source_version.source_version_id,
        locator=EvidenceLocator(
            document_role="临床试验登记结果",
            field_path="results.treatment-300mg-q4w",
        ),
        original_text="-2.1",
        created_at=created_at,
    )
    control_fragment = repository.add_fragment(
        source_version_id=source_version.source_version_id,
        locator=EvidenceLocator(
            document_role="临床试验登记结果",
            field_path="results.placebo-q4w",
        ),
        original_text="-0.8",
        created_at=created_at,
    )
    treatment_candidate = fact(
        value="-2.1",
        arm_id="treatment-300mg-q4w",
        version_id="fact-version-treatment",
        fragment_id=treatment_fragment.fragment_id,
    )
    control_candidate = fact(
        value="-0.8",
        arm_id="placebo-q4w",
        version_id="fact-version-control",
        fragment_id=control_fragment.fragment_id,
    )

    def verified_fragment(fact_value: AtomicFactVersion):
        assert fact_value.raw_value is not None
        fragment = repository.read_fragment(fact_value.primary_fragment_id)
        return verify_reopened_fragment(
            fragment,
            reopened_original_text=fact_value.raw_value,
            source_version_id=fragment.source_version_id,
            repository=repository,
        )

    lineage_registry = ScientificLineageRegistry.from_verified_fragments(
        (
            verified_fragment(treatment_candidate),
            verified_fragment(control_candidate),
        )
    )
    lineage_registry, treatment = lineage_registry.accept_candidate_fact(
        treatment_candidate
    )
    lineage_registry, control = lineage_registry.accept_candidate_fact(
        control_candidate
    )
    direct = create_direct_evidence_claim(
        claim_identity="claim-treatment-nps-week24",
        claim_text="试验组第 24 周 NPS 较基线变化为 -2.1 分。",
        supporting_facts=(treatment,),
        lineage_registry=lineage_registry,
        created_at=created_at,
    )
    calculated = create_deterministic_difference_claim(
        claim_identity="claim-between-arm-nps-week24",
        claim_text="第 24 周试验组与安慰剂组的组间差为 -1.3 分。",
        treatment_fact=treatment,
        control_fact=control,
        lineage_registry=lineage_registry,
        created_at=created_at,
    )
    magnitude_wording = create_deterministic_difference_claim(
        claim_identity="claim-between-arm-nps-week24-magnitude-wording",
        claim_text="试验组下降 2.1 分，安慰剂组下降 0.8 分，组间差为 1.3 分。",
        treatment_fact=treatment,
        control_fact=control,
        lineage_registry=lineage_registry,
        created_at=created_at,
    )
    synthesis = create_synthesis_claim(
        claim_identity="claim-nps-clinical-interpretation-week24",
        claim_text="AI 综合判断：试验组在第 24 周显示更大的 NPS 改善。",
        supporting_facts=(treatment, control),
        lineage_registry=lineage_registry,
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
            lineage_registry=lineage_registry,
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
                lineage_registry=lineage_registry,
                created_at=created_at,
            )
    with pytest.raises(ValueError, match="声明文字与复算结果不一致"):
        create_deterministic_difference_claim(
            claim_identity="claim-contradictory-calculation-text",
            claim_text="组间差为 -1.3 分，但手算为 -9.9 分。",
            treatment_fact=treatment,
            control_fact=control,
            lineage_registry=lineage_registry,
            created_at=created_at,
        )
    with pytest.raises(ValueError, match="必须在文字中明确标识"):
        create_synthesis_claim(
            claim_identity="claim-unlabelled-ai-synthesis",
            claim_text="试验组在第 24 周显示更大的 NPS 改善。",
            supporting_facts=(treatment, control),
            lineage_registry=lineage_registry,
            synthesis_method_zh="比较同一试验、同一人群和时间点的组间差异",
            created_at=created_at,
        )

    with pytest.raises(ValueError, match="未在科学证据注册表接受"):
        create_direct_evidence_claim(
            claim_identity="claim-unregistered-fact",
            claim_text="试验组第 24 周 NPS 较基线变化为 -2.1 分。",
            supporting_facts=(treatment,),
            lineage_registry=ScientificLineageRegistry.empty(),
            created_at=created_at,
        )

    other_trial_treatment = treatment.model_copy(
        update={
            "entity_id": "trial-other",
            "fact_id": "fact-other-treatment",
            "fact_version_id": "fact-version-other-treatment",
        }
    )
    cross_trial_registry = lineage_registry
    with pytest.raises(ValueError, match="同一试验实体"):
        create_deterministic_difference_claim(
            claim_identity="claim-cross-trial",
            claim_text="组间差为 -1.3 分。",
            treatment_fact=other_trial_treatment,
            control_fact=control,
            lineage_registry=cross_trial_registry,
            created_at=created_at,
        )
    with pytest.raises(ValueError, match="必须在文字中明确标识"):
        ClaimVersion.model_validate(
            {**synthesis.model_dump(), "claim_text": "试验组显示更大的改善。"},
            context={"lineage_registry": lineage_registry},
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
            },
            context={"lineage_registry": lineage_registry},
        )
    with pytest.raises(ValueError, match="必须通过科学证据注册表"):
        ClaimVersion.model_validate(direct.model_dump())
    with pytest.raises(ValueError, match="必须通过科学证据注册表"):
        ClaimVersion.model_validate(
            direct.model_dump(),
            context={"accepted_facts": (treatment,)},
        )


def test_phase2_recorded_registry_fixture_rebuilds_source_to_claim_and_route_lineage(
    tmp_path: Path,
) -> None:
    from ci_workflow.capabilities.extraction_normalization import (
        AtomicFactExtractionInput,
        extract_atomic_fact,
        verify_reopened_fragment,
    )
    from ci_workflow.capabilities.lineage_registry import ScientificLineageRegistry
    from ci_workflow.capabilities.ontology_universe import (
        InnovationOntology,
        TherapyComponent,
    )
    from ci_workflow.capabilities.resolution import create_direct_evidence_claim
    from ci_workflow.domain.entities import (
        EntityGraph,
        EntityIdentity,
        EntityRelation,
        EntityType,
        ExternalIdentifier,
    )
    from ci_workflow.domain.enums import FactDisclosureState, FactReviewState
    from ci_workflow.domain.evidence import EvidenceGap, InformationGainDiff, SourceReceipt
    from ci_workflow.ingestion.identity import CompetitorUniverse, EntityIdentityIndex
    from ci_workflow.ingestion.locators import (
        RegistryJsonSnapshot,
        create_registry_json_locator,
        reopen_registry_json_locator,
    )
    from ci_workflow.sources.connectors.authoritative_wechat import (
        APPROVED_WECHAT_ACCOUNT_LABELS,
    )
    from ci_workflow.sources.connectors.china_registries import (
        build_china_trial_search_url,
    )
    from ci_workflow.sources.connectors.clinicaltrials_gov import (
        ClinicalTrialsGovStudyVersion,
        create_publication_cross_references,
        extract_registry_observations,
    )
    from ci_workflow.sources.planner import (
        HistoricalCutoffState,
        RouteCompletion,
        RouteCompletionState,
        RouteProgress,
        assess_historical_source,
    )
    from ci_workflow.sources.policy import (
        ClaimDomain,
        SourceApplicability,
        SourceAuthority,
        SourceEligibility,
        SourcePolicy,
    )
    from ci_workflow.sources.receipts import (
        AttemptResultClass,
        EvidenceAuditBundle,
        RouteAttemptResult,
    )

    fixture_path = (
        ROOT
        / "fixtures"
        / "recorded"
        / "phase-2-lineage"
        / "nct02912468-minimal.json"
    )
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    record = fixture["record"]
    acquired_at = fixture["captured_at"]
    endpoint = fixture["endpoint"]

    study = ClinicalTrialsGovStudyVersion.from_api_record(
        record,
        acquired_at=acquired_at,
    )
    assert study.nct_id == "NCT02912468"
    assert study.record_url == "https://clinicaltrials.gov/study/NCT02912468"
    observations = extract_registry_observations(study)
    observation_by_path = {
        item.locator.field_path: item
        for item in observations
        if item.locator.field_path is not None
    }
    result_observation = observation_by_path[endpoint["field_path"]]
    assert result_observation.original_value == endpoint["expected_original_value"]
    assert result_observation.claim_domain == "trial_results"
    primary_outcome = record["resultsSection"]["outcomeMeasuresModule"][
        "outcomeMeasures"
    ][0]
    measurements = primary_outcome["classes"][0]["categories"][0]["measurements"]
    assert tuple(item["value"] for item in measurements) == ("-0.45", "-1.34")
    assert tuple(item["value"] for item in primary_outcome["denoms"][0]["counts"]) == (
        "133",
        "143",
    )
    assert record["protocolSection"]["designModule"]["enrollmentInfo"] == {
        "count": 276,
        "type": "ACTUAL",
    }
    assert record["protocolSection"]["statusModule"][
        "resultsFirstPostDateStruct"
    ]["date"] == "2019-07-25"
    primary_reports = create_publication_cross_references(study)
    assert any(item.pmid == "31543428" for item in primary_reports)

    captured = datetime.fromisoformat(acquired_at)
    first_disclosed = datetime.fromisoformat(fixture["results_first_disclosed_at"])
    canonical_record = json.dumps(
        record, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    repository, source_version = _repository_for_text(
        tmp_path,
        content=canonical_record,
        source_id="clinicaltrials_gov",
        timestamp=captured,
        first_disclosed_at=first_disclosed,
    )
    snapshot = RegistryJsonSnapshot.create(
        source_version_id=source_version.source_version_id,
        payload=record,
        source_url=study.record_url,
        document_role_label_zh="ClinicalTrials.gov 登记结果",
    )
    locator = create_registry_json_locator(
        snapshot,
        field_path=endpoint["field_path"],
    )
    reopened = reopen_registry_json_locator(snapshot, locator)
    assert reopened == endpoint["expected_original_value"]

    cutoff_assessment = assess_historical_source(
        source_version,
        cutoff=datetime.fromisoformat(fixture["data_cutoff"]),
        key_evidence=True,
    )
    assert cutoff_assessment.state is HistoricalCutoffState.SNAPSHOT_ELIGIBLE
    assert cutoff_assessment.can_enter_snapshot is True

    raw_text = str(reopened)
    fragment = repository.add_fragment(
        source_version_id=source_version.source_version_id,
        locator=locator.evidence_locator,
        original_text=raw_text,
        created_at=captured,
    )
    verified = verify_reopened_fragment(
        fragment,
        reopened_original_text=str(reopen_registry_json_locator(snapshot, locator)),
        source_version_id=source_version.source_version_id,
        repository=repository,
    )

    ontology = InnovationOntology.from_yaml(
        ROOT / "policies" / "ontology" / "innovation-therapy-v1.yaml"
    )
    candidates = fixture["universe_candidates"]
    candidate_paths = (
        "protocolSection.armsInterventionsModule.interventions[0].name",
        "protocolSection.armsInterventionsModule.interventions[2].name",
    )
    verified_universe_fragments = []
    for field_path in candidate_paths:
        candidate_locator = create_registry_json_locator(
            snapshot, field_path=field_path
        )
        candidate_text = str(
            reopen_registry_json_locator(snapshot, candidate_locator)
        )
        candidate_fragment = repository.add_fragment(
            source_version_id=source_version.source_version_id,
            locator=candidate_locator.evidence_locator,
            original_text=candidate_text,
            created_at=captured,
        )
        verified_universe_fragments.append(
            verify_reopened_fragment(
                candidate_fragment,
                reopened_original_text=candidate_text,
                source_version_id=source_version.source_version_id,
                repository=repository,
            )
        )
    eligibility = tuple(
        ontology.evaluate_component(
            TherapyComponent(
                name=item["canonical_name"],
                modality=item["modality"],
                evidence_fragment_ids=(verified.fragment.fragment_id,),
            )
        )
        for item, verified in zip(
            candidates, verified_universe_fragments, strict=True
        )
    )
    product_entities = tuple(
        EntityIdentity(
            entity_id=result.component_id,
            entity_type=EntityType.PRODUCT,
            canonical_name=item["canonical_name"],
            identity_basis=item["identity_basis"],
            aliases=(),
            external_identifiers=(),
        )
        for item, result in zip(candidates, eligibility, strict=True)
    )
    universe = CompetitorUniverse.build(
        entities=product_entities,
        eligibility=eligibility,
        evidence_registry=ScientificLineageRegistry.from_verified_fragments(
            tuple(verified_universe_fragments)
        ),
    )
    assert universe.universe_closed is True
    assert tuple(item.entity.canonical_name for item in universe.members) == (
        "度普利尤单抗",
    )
    assert any(
        item.component_name == "糠酸莫米松鼻喷雾剂"
        and item.decision == "excluded"
        for item in universe.eligibility_audit
    )

    product = universe.members[0].entity
    trial = EntityIdentity.create(
        EntityType.TRIAL,
        "SINUS-24",
        "sanofi-efc14146-trial-001",
        external_identifiers=(
            ExternalIdentifier(namespace="ClinicalTrials.gov", value=study.nct_id),
        ),
    )
    arm = EntityIdentity.create(
        EntityType.ARM,
        endpoint["arm_label_zh"],
        "nct02912468-arm-og001",
    )
    graph = EntityGraph()
    for entity in (product, trial, arm):
        graph.add_entity(entity)
    graph.add_relation(
        EntityRelation.create(product, "在试验中研究", trial, fragment.fragment_id)
    )
    graph.add_relation(
        EntityRelation.create(trial, "包含组别", arm, fragment.fragment_id)
    )
    index = EntityIdentityIndex()
    index.add(trial, evidence_fragment_id=fragment.fragment_id)
    resolved_trial = index.resolve_external_identifier(
        ExternalIdentifier(namespace="clinicaltrials.gov", value="nct02912468")
    )
    assert resolved_trial.selected_entity_id == trial.entity_id
    assert graph.related(product.entity_id, "在试验中研究") == (trial.entity_id,)

    candidate_fact = extract_atomic_fact(
        AtomicFactExtractionInput(
            entity_id=arm.entity_id,
            field_id="efficacy.nasal_congestion.change_from_baseline",
            raw_value=raw_text,
            unit=endpoint["unit"],
            context=endpoint["context_zh"],
            arm_id=arm.entity_id,
            cohort_id="cohort-intention-to-treat",
            population=endpoint["population_zh"],
            timepoint=endpoint["timepoint_zh"],
            time_window=None,
            numerator=None,
            denominator=endpoint["denominator"],
            extraction_method="ClinicalTrials.gov 官方 API 精确字段抽取",
            quality_state="来源版本、摘要、组别、时间点和分母已交叉核对",
            disclosure_maturity="登记平台已发布结果",
            source_role="clinical_trial_registry",
            disclosure_state=FactDisclosureState.REPORTED_VALUE,
            review_state=FactReviewState.CANDIDATE,
            published_at=first_disclosed,
            effective_at=None,
            created_at=captured,
            verified_fragment=verified,
        )
    )
    lineage_registry = ScientificLineageRegistry.empty().register_verified_fragment(
        verified
    )
    lineage_registry, accepted_fact = lineage_registry.accept_candidate_fact(
        candidate_fact
    )
    claim = create_direct_evidence_claim(
        claim_identity="nct02912468-og001-nc-week24",
        claim_text="度普利尤单抗组第 24 周鼻塞/阻塞症状评分较基线变化为 -1.34 分。",
        supporting_facts=(accepted_fact,),
        lineage_registry=lineage_registry,
        created_at=captured,
    )
    assert claim.supporting_fact_version_ids == (candidate_fact.fact_version_id,)
    assert accepted_fact.primary_fragment_id == fragment.fragment_id
    assert fragment.source_version_id == source_version.source_version_id
    assert fragment.locator.url == study.record_url

    receipt = SourceReceipt(
        schema_version="1.0",
        receipt_id="receipt-nct02912468-results-v1",
        route_id="clinicaltrials-global-baseline",
        strategy_unit_id="registry-nct-id",
        entity_id=trial.entity_id,
        gap_id="gap-nct02912468-primary-efficacy",
        claim_domain=ClaimDomain.EFFICACY_SAFETY_RESULTS.value,
        query_or_identifier=study.nct_id,
        language="en",
        access_method="ClinicalTrials.gov API v2",
        attempt_index=1,
        started_at=captured,
        ended_at=captured,
        scheduled_backoff_ms=0,
        actual_backoff_ms=0,
        result_class="content_acquired",
        error_class=None,
        completeness_checks=("NCT 身份一致", "主要结果、组别和分母字段完整"),
        alternative_paths=("登记网页", "NCT 号 PubMed 交叉引用"),
        source_version_id=source_version.source_version_id,
        content_sha256=snapshot.content_sha256,
        diagnostic_confidence="high",
        parent_attempt_id=None,
        recovery_round=0,
    )
    gap = EvidenceGap(
        schema_version="1.0",
        gap_id=receipt.gap_id,
        gate_spec_id="phase-2-lineage-anchor",
        object_type="trial",
        object_id=trial.entity_id,
        field_id="efficacy.nasal_congestion.change_from_baseline",
        current_state="unresolved_due_to_route",
        required_context="指标、组别、人群、时间点、分母和结果值",
        candidate_sources=("ClinicalTrials.gov", "PubMed", "申办方公开资料"),
        completed_strategies=(receipt.strategy_unit_id,),
        information_gain_diff=(
            InformationGainDiff(
                round=1,
                new_fields=("试验组第 24 周结果", "试验组分母"),
                new_source_versions=(source_version.source_version_id,),
            ),
        ),
        next_legal_action="将精确定位片段转为候选事实并执行独立科学质控",
    )
    source_eligibility = SourceEligibility(
        schema_version="1.0",
        source_eligibility_id="eligibility-nct02912468-results-v1",
        route_id=receipt.route_id,
        strategy_unit_id=receipt.strategy_unit_id,
        entity_id=trial.entity_id,
        gap_id=gap.gap_id,
        claim_domain=ClaimDomain.EFFICACY_SAFETY_RESULTS,
        applicability=SourceApplicability.APPLICABLE,
        required_by_policy=True,
        rationale_zh="该试验具有 NCT 标识，且登记平台已公开结构化结果",
        policy_id="source-policy-v1",
        policy_version="1.0",
        evidence_fragment_ids=(fragment.fragment_id,),
        decided_by="source-planner-v1",
        decided_at=captured,
    )
    completed_route = RouteProgress(
        route_id=receipt.route_id,
        attempts=(
            RouteAttemptResult(
                attempt_id=receipt.receipt_id,
                strategy_unit_id=receipt.strategy_unit_id,
                entity_id=receipt.entity_id,
                gap_id=receipt.gap_id,
                claim_domain=receipt.claim_domain,
                result_class=AttemptResultClass.CONTENT_ACQUIRED,
                detail_zh="已取得并保存官方登记结果",
            ),
        ),
    ).complete(
        RouteCompletion(
            state=RouteCompletionState.COMPLETED,
            rationale_zh="官方登记结果已取得并形成可重开事实与声明链",
            completed_strategy_unit_ids=(receipt.strategy_unit_id,),
        ),
        audit_bundle=EvidenceAuditBundle(
            source_receipts=(receipt,),
            source_versions=(source_version,),
            source_eligibilities=(source_eligibility,),
            evidence_gap=gap,
        ),
    )
    assert completed_route.is_complete is True

    policy = SourcePolicy.from_yaml(ROOT / "policies" / "sources" / "source-policy-v1.yaml")
    assert policy.authority_for(
        "clinicaltrials_gov", ClaimDomain.EFFICACY_SAFETY_RESULTS
    ) is SourceAuthority.DIRECT
    for source_id in fixture["china_route_expectations"][
        "required_official_source_ids"
    ]:
        assert policy.source(source_id).required_for_china is True
    assert (
        fixture["china_route_expectations"]["authoritative_secondary_accounts"]
        == APPROVED_WECHAT_ACCOUNT_LABELS
    )
    assert build_china_trial_search_url("CTR20260001").startswith(
        "https://www.chinadrugtrials.org.cn/"
    )
    for source_id in APPROVED_WECHAT_ACCOUNT_LABELS:
        assert policy.authority_for(
            source_id,
            ClaimDomain.EFFICACY_SAFETY_RESULTS,
        ) is SourceAuthority.DIRECT
