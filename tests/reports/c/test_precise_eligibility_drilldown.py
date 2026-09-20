"""Task 7.2 C 类入排标准精确结构化和完整下钻链 RED 测试。

合同断言（先失败后通过）：
- 确定性观察语料覆盖疾病定义、病程、严重度、既往/背景/救援、洗脱、年龄、
  实验室/生物标志物、合并症、入选与排除等入排设计要素，并混入非入排观察；
- 参数化 case 身份集合必须等于语料中全部适用入排观察身份，禁止手抽子集；
- 每条适用观察投影后保留完整稳定链：适应症 → 产品 → 试验 → 队列/组别 →
  设计要素 → 原始字段 → 量表/评分适用性 → 筛选或评估时间 → 运算符/阈值/值/
  单位适用性 → 来源版本与完整 EvidenceLocator；
- 比较图、完整表与证据抽屉共用同一 drilldown_chain_id；
- 原文 byte-for-byte 保真，不得截短或改写；
- 无命名量表时明确 not_applicable + 适用性谓词，禁止空串或伪造量表名；
- 不同试验、组别、字段的稳定链不得碰撞。
"""

from __future__ import annotations

from collections.abc import Mapping
from types import ModuleType
from typing import Any

import pytest
from pydantic import ValidationError

from ci_workflow.domain.enums import FactDisclosureState, FactReviewState
from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.gates.models import ConflictDisposition, DisclosureMaturity, SourceRole
from ci_workflow.reports.c.contracts import DesignFieldFamily, DesignObservation

_INDICATION_ID = "indication-pnh"

_REGISTRY_LOCATOR_ALPHA = EvidenceLocator(
    document_role="clinical-trial-registry",
    field_path="protocolSection.eligibilityModule.eligibilityCriteria",
    heading="Eligibility Criteria",
    url="https://clinicaltrials.gov/study/NCT02912468",
    paragraph="Inclusion Criteria",
)

_REGISTRY_LOCATOR_BETA = EvidenceLocator(
    document_role="clinical-trial-registry",
    field_path="protocolSection.eligibilityModule.eligibilityCriteria",
    heading="Eligibility Criteria",
    url="https://clinicaltrials.gov/study/NCT00000002",
    paragraph="Exclusion Criteria",
)

# 入排设计要素封闭目录：参数化适用集必须由此从全量语料推导，不得手选。
_ELIGIBILITY_DESIGN_ELEMENTS = frozenset(
    {
        "disease_definition",
        "disease_course",
        "severity_or_activity",
        "prior_therapy",
        "background_therapy",
        "rescue_therapy",
        "washout",
        "age_rule",
        "lab_or_biomarker",
        "comorbidity_rule",
        "inclusion_criterion",
        "exclusion_criterion",
    }
)


def _design() -> ModuleType:
    """延迟导入计划中的 C 类入排投影；实现前每个用例精确失败而非收集期中断。"""

    try:
        from ci_workflow.reports.c import design as module
    except (ModuleNotFoundError, ImportError) as exc:
        pytest.fail(f"C 类入排精确下钻尚未实现：{exc}", pytrace=False)
    return module


def _observation(**overrides: object) -> DesignObservation:
    """构造一条已接受的登记来源设计观察；默认属于入排人群族。"""

    payload: dict[str, object] = {
        "schema_version": "1.0",
        "row_id": "design-row-eligibility",
        "source_row_id": "registry-row-eligibility",
        "observation_id": "design-observation-eligibility",
        "product_id": "product-ravulizumab",
        "trial_id": "trial-alpha",
        "cohort_id": "cohort-alpha",
        "group_id": "group-all-enrolled",
        "field_family": DesignFieldFamily.POPULATION,
        "field": "inclusion_criterion",
        "source_field_name": "Inclusion Criteria",
        "source_field_definition": "Registry inclusion criterion text",
        "source_text": "确诊 PNH，且筛选期 LDH ≥ 1.5×ULN。",
        "scale": None,
        "scale_version": None,
        "operator": None,
        "threshold_value": None,
        "threshold_unit": None,
        "assessment_timepoint": "筛选期",
        "stage": "III",
        "development_role": "关键注册试验",
        "randomization": None,
        "blinding": None,
        "source_version_id": "registry-version-alpha-1",
        "source_locator": _REGISTRY_LOCATOR_ALPHA,
        "source_role": SourceRole.CLINICAL_TRIAL_REGISTRY,
        "disclosure_maturity": DisclosureMaturity.REGISTRY_RESULT_OR_PRIMARY_REPORT,
        "review_state": FactReviewState.ACCEPTED,
        "disclosure_state": FactDisclosureState.REPORTED_VALUE,
        "conflict_disposition": ConflictDisposition.RESOLVED_SELECTED_ACCEPTED_FACT,
        "reported_zero_text": None,
        "route_receipt_id": None,
        "applicability_predicate_id": None,
        "compatibility_rule": "c-eligibility-v1",
        "difference_labels_zh": (),
    }
    payload.update(overrides)
    return DesignObservation.model_validate(payload)


def _eligibility_corpus() -> tuple[DesignObservation, ...]:
    """全量确定性登记观察语料：适用入排要素 + 非入排对照，供参数化推导。"""

    return (
        _observation(
            row_id="design-row-disease-definition",
            source_row_id="registry-row-disease-definition",
            observation_id="obs-disease-definition-alpha",
            field="disease_definition",
            source_field_name="Disease Definition",
            source_field_definition="Documented PNH diagnosis",
            source_text="经流式细胞术确认的 PNH 诊断（克隆≥10%）。",
            assessment_timepoint="筛选期",
        ),
        _observation(
            row_id="design-row-disease-course",
            source_row_id="registry-row-disease-course",
            observation_id="obs-disease-course-alpha",
            field="disease_course",
            source_field_name="Disease Course",
            source_field_definition="Minimum disease duration",
            source_text="PNH 确诊至少 6 个月。",
            operator=">=",
            threshold_value="6",
            threshold_unit="月",
            assessment_timepoint="筛选期",
        ),
        _observation(
            row_id="design-row-severity",
            source_row_id="registry-row-severity",
            observation_id="obs-severity-or-activity-alpha",
            field="severity_or_activity",
            source_field_name="Disease Severity / Activity",
            source_field_definition="FACIT-Fatigue score at screening",
            source_text="筛选期 FACIT-Fatigue 总分 ≤ 40。",
            scale="FACIT-Fatigue",
            scale_version="v4",
            operator="<=",
            threshold_value="40",
            threshold_unit="分",
            assessment_timepoint="筛选期",
        ),
        _observation(
            row_id="design-row-prior-therapy",
            source_row_id="registry-row-prior-therapy",
            observation_id="obs-prior-therapy-alpha",
            field="prior_therapy",
            source_field_name="Prior Therapy",
            source_field_definition="Prior complement inhibitor exposure",
            source_text="允许既往依库珠单抗治疗，但须完成规定洗脱。",
            assessment_timepoint=None,
        ),
        _observation(
            row_id="design-row-background-therapy",
            source_row_id="registry-row-background-therapy",
            observation_id="obs-background-therapy-alpha",
            field="background_therapy",
            source_field_name="Background Therapy",
            source_field_definition="Allowed background supportive care",
            source_text="允许稳定剂量的抗凝与叶酸支持治疗。",
            assessment_timepoint="基线",
        ),
        _observation(
            row_id="design-row-rescue-therapy",
            source_row_id="registry-row-rescue-therapy",
            observation_id="obs-rescue-therapy-alpha",
            field="rescue_therapy",
            source_field_name="Rescue Therapy",
            source_field_definition="Protocol-defined rescue transfusion",
            source_text="突破性溶血时可按方案给予红细胞输注救援。",
            assessment_timepoint=None,
        ),
        _observation(
            row_id="design-row-washout",
            source_row_id="registry-row-washout",
            observation_id="obs-washout-alpha",
            field="washout",
            source_field_name="Washout",
            source_field_definition="Washout from prior C5 inhibitor",
            source_text="末次依库珠单抗给药后须洗脱 ≥ 2 周。",
            operator=">=",
            threshold_value="2",
            threshold_unit="周",
            assessment_timepoint="筛选期",
        ),
        _observation(
            row_id="design-row-age-rule",
            source_row_id="registry-row-age-rule",
            observation_id="obs-age-rule-alpha",
            field="age_rule",
            source_field_name="Age",
            source_field_definition="Minimum age at informed consent",
            source_text="年龄 ≥ 18 岁。",
            operator=">=",
            threshold_value="18",
            threshold_unit="岁",
            assessment_timepoint="知情同意时",
        ),
        _observation(
            row_id="design-row-lab-biomarker",
            source_row_id="registry-row-lab-biomarker",
            observation_id="obs-lab-or-biomarker-alpha",
            field="lab_or_biomarker",
            source_field_name="Laboratory / Biomarker",
            source_field_definition="LDH relative to ULN at screening",
            # 保留换行与尾部空格，用于原文 byte-for-byte 保真断言。
            source_text="筛选期 LDH ≥ 1.5×ULN。\n ",
            operator=">=",
            threshold_value="1.5",
            threshold_unit="×ULN",
            assessment_timepoint="筛选期",
        ),
        _observation(
            row_id="design-row-comorbidity",
            source_row_id="registry-row-comorbidity",
            observation_id="obs-comorbidity-rule-alpha",
            field="comorbidity_rule",
            source_field_name="Comorbidity",
            source_field_definition="Important comorbidity exclusion/inclusion rules",
            source_text="活动性未控制感染为排除条件；稳定的再生障碍性贫血可入选。",
            assessment_timepoint="筛选期",
        ),
        _observation(
            row_id="design-row-inclusion",
            source_row_id="registry-row-inclusion",
            observation_id="obs-inclusion-criterion-alpha",
            field="inclusion_criterion",
            source_field_name="Inclusion Criteria",
            source_field_definition="Inclusion criterion without named scale",
            source_text="筛选期血红蛋白 ≤ 10.5 g/dL，且需在过去 12 个月内接受过输血。",
            operator="<=",
            threshold_value="10.5",
            threshold_unit="g/dL",
            assessment_timepoint="筛选期",
        ),
        _observation(
            row_id="design-row-exclusion",
            source_row_id="registry-row-exclusion",
            observation_id="obs-exclusion-criterion-alpha",
            field="exclusion_criterion",
            source_field_name="Exclusion Criteria",
            source_field_definition="Unnamed-scale exclusion criterion",
            source_text="妊娠或哺乳期女性不得入选。",
            assessment_timepoint="筛选期",
        ),
        # 跨试验/组别同名字段：稳定链必须隔离，不得碰撞。
        _observation(
            row_id="design-row-inclusion-beta",
            source_row_id="registry-row-inclusion-beta",
            observation_id="obs-inclusion-criterion-beta",
            product_id="product-eculizumab",
            trial_id="trial-beta",
            cohort_id="cohort-beta",
            group_id="group-experimental",
            field="inclusion_criterion",
            source_field_name="Inclusion Criteria",
            source_field_definition="Sibling-trial inclusion criterion",
            source_text="确诊 PNH，筛选期 LDH ≥ 1.5×ULN（试验 B）。",
            operator=">=",
            threshold_value="1.5",
            threshold_unit="×ULN",
            assessment_timepoint="筛选期",
            source_version_id="registry-version-beta-1",
            source_locator=_REGISTRY_LOCATOR_BETA,
        ),
        # 非入排对照：不得进入适用参数化集合。
        _observation(
            row_id="design-row-trial-identity",
            source_row_id="registry-row-trial-identity",
            observation_id="obs-trial-identity-alpha",
            field_family=DesignFieldFamily.TRIAL_IDENTITY,
            field="trial_identity_stage_role",
            source_field_name="Trial Identity",
            source_field_definition="Phase and development role",
            source_text="III 期关键注册试验。",
            assessment_timepoint=None,
            stage="III",
            development_role="关键注册试验",
        ),
        _observation(
            row_id="design-row-endpoint",
            source_row_id="registry-row-endpoint",
            observation_id="obs-primary-endpoint-alpha",
            field_family=DesignFieldFamily.ENDPOINT,
            field="primary_endpoint_definition",
            source_field_name="Primary Endpoint",
            source_field_definition="Primary efficacy endpoint",
            source_text="第 26 周 LDH 正常化比例。",
            assessment_timepoint="第26周",
        ),
        _observation(
            row_id="design-row-statistical",
            source_row_id="registry-row-statistical",
            observation_id="obs-analysis-population-alpha",
            field_family=DesignFieldFamily.STATISTICAL,
            field="analysis_population",
            source_field_name="Analysis Population",
            source_field_definition="Primary analysis population",
            source_text="全分析集（FAS）。",
            assessment_timepoint=None,
        ),
    )


def _is_applicable_eligibility_observation(observation: DesignObservation) -> bool:
    return (
        observation.field_family is DesignFieldFamily.POPULATION
        and observation.field in _ELIGIBILITY_DESIGN_ELEMENTS
    )


def _applicable_observations() -> tuple[DesignObservation, ...]:
    return tuple(
        item
        for item in _eligibility_corpus()
        if _is_applicable_eligibility_observation(item)
    )


_APPLICABLE_OBSERVATIONS = _applicable_observations()
_APPLICABLE_IDS = tuple(item.observation_id for item in _APPLICABLE_OBSERVATIONS)
_APPLICABLE_BY_ID = {
    item.observation_id: item for item in _APPLICABLE_OBSERVATIONS
}


def _project_view(design: ModuleType, observations: tuple[DesignObservation, ...]) -> Any:
    project = getattr(design, "project_eligibility_drilldown", None)
    if project is None:
        pytest.fail(
            "C 类入排精确下钻缺少 project_eligibility_drilldown",
            pytrace=False,
        )
    return project(observations, indication_id=_INDICATION_ID)


def _row_for_observation(view: Any, observation: DesignObservation) -> Any:
    table_rows = tuple(view.table_rows)
    matches = [
        row
        for row in table_rows
        if getattr(row, "observation_id", None) == observation.observation_id
    ]
    assert len(matches) == 1, (
        f"适用观察 {observation.observation_id!r} 必须恰好投影一行，实际 {len(matches)} 行"
    )
    return matches[0]


def _assert_complete_stable_chain(row: Any, observation: DesignObservation) -> None:
    assert row.indication_id == _INDICATION_ID
    assert row.product_id == observation.product_id
    assert row.trial_id == observation.trial_id
    assert row.cohort_id == observation.cohort_id
    assert row.group_id == observation.group_id
    assert row.design_element == observation.field
    assert row.source_field_name == observation.source_field_name
    assert row.source_text == observation.source_text
    # 原文不得截短：投影文本必须与观察原文完全一致（含空白/换行）。
    assert row.source_text.encode("utf-8") == observation.source_text.encode("utf-8")

    scale_applicability = row.scale_applicability
    scale_value = getattr(scale_applicability, "value", scale_applicability)
    if observation.scale is None:
        assert scale_value == "not_applicable"
        assert row.scale is None
        assert row.scale_version is None
        predicate = row.scale_applicability_predicate_id
        assert isinstance(predicate, str) and predicate.strip()
    else:
        assert scale_value != "not_applicable"
        assert row.scale == observation.scale
        assert row.scale_version == observation.scale_version

    assert row.assessment_timepoint == observation.assessment_timepoint
    assert row.operator == observation.operator
    assert row.threshold_value == observation.threshold_value
    assert row.threshold_unit == observation.threshold_unit

    threshold_bits = (
        observation.operator,
        observation.threshold_value,
        observation.threshold_unit,
    )
    threshold_applicability = row.operator_threshold_applicability
    threshold_value = getattr(threshold_applicability, "value", threshold_applicability)
    if all(item is None for item in threshold_bits):
        assert threshold_value == "not_applicable"
        predicate = row.operator_threshold_applicability_predicate_id
        assert isinstance(predicate, str) and predicate.strip()
    else:
        assert threshold_value != "not_applicable"

    assert row.source_version_id == observation.source_version_id
    assert row.source_locator == observation.source_locator
    assert row.source_locator.model_dump() == observation.source_locator.model_dump()
    assert isinstance(row.drilldown_chain_id, str) and row.drilldown_chain_id.strip()


def _assert_shared_surfaces(view: Any, observation: DesignObservation, row: Any) -> None:
    chart_rows = tuple(view.chart_rows)
    chart_ids = {
        item.drilldown_chain_id
        for item in chart_rows
        if item.observation_id == observation.observation_id
    }
    assert chart_ids == {row.drilldown_chain_id}

    evidence: Mapping[str, Any] = view.evidence_by_chain_id
    assert row.drilldown_chain_id in evidence
    linked = evidence[row.drilldown_chain_id]
    assert linked.observation_id == observation.observation_id
    assert linked.drilldown_chain_id == row.drilldown_chain_id
    assert linked.source_text.encode("utf-8") == observation.source_text.encode("utf-8")
    assert linked.source_locator == observation.source_locator


def test_parametrized_case_identities_equal_all_applicable_observation_identities() -> None:
    """参数 case 身份必须覆盖语料中全部适用观察，禁止手抽子集。"""

    corpus_ids = {item.observation_id for item in _eligibility_corpus()}
    applicable_ids = {item.observation_id for item in _APPLICABLE_OBSERVATIONS}
    parametrized_ids = set(_APPLICABLE_IDS)

    assert len(_APPLICABLE_OBSERVATIONS) >= len(_ELIGIBILITY_DESIGN_ELEMENTS)
    assert applicable_ids == parametrized_ids
    assert applicable_ids <= corpus_ids
    assert len(applicable_ids) == len(_APPLICABLE_OBSERVATIONS)
    # 非入排对照必须存在于全量语料，且不得混入适用集。
    assert "obs-trial-identity-alpha" in corpus_ids
    assert "obs-primary-endpoint-alpha" in corpus_ids
    assert "obs-analysis-population-alpha" in corpus_ids
    assert applicable_ids.isdisjoint(
        {
            "obs-trial-identity-alpha",
            "obs-primary-endpoint-alpha",
            "obs-analysis-population-alpha",
        }
    )


@pytest.mark.parametrize("observation_id", _APPLICABLE_IDS, ids=_APPLICABLE_IDS)
def test_every_applicable_design_observation_has_complete_locator_chain(
    observation_id: str,
) -> None:
    design = _design()
    observation = _APPLICABLE_BY_ID[observation_id]
    view = _project_view(design, _eligibility_corpus())

    projected_ids = {row.observation_id for row in view.table_rows}
    assert projected_ids == set(_APPLICABLE_IDS)

    row = _row_for_observation(view, observation)
    _assert_complete_stable_chain(row, observation)
    _assert_shared_surfaces(view, observation, row)

    # 跨试验同名字段不得共享稳定链。
    sibling_rows = [
        item
        for item in view.table_rows
        if item.design_element == observation.field
        and item.observation_id != observation.observation_id
    ]
    for sibling in sibling_rows:
        assert sibling.drilldown_chain_id != row.drilldown_chain_id
        assert (sibling.trial_id, sibling.group_id, sibling.design_element) != (
            row.trial_id,
            row.group_id,
            row.design_element,
        ) or sibling.product_id != row.product_id


def test_unnamed_scale_is_not_applicable_not_fabricated() -> None:
    design = _design()
    unnamed = next(
        item
        for item in _APPLICABLE_OBSERVATIONS
        if item.field == "exclusion_criterion" and item.scale is None
    )
    named = next(
        item
        for item in _APPLICABLE_OBSERVATIONS
        if item.field == "severity_or_activity" and item.scale is not None
    )

    view = _project_view(design, (unnamed, named))
    unnamed_row = _row_for_observation(view, unnamed)
    named_row = _row_for_observation(view, named)

    unnamed_applicability = getattr(
        unnamed_row.scale_applicability,
        "value",
        unnamed_row.scale_applicability,
    )
    assert unnamed_applicability == "not_applicable"
    assert unnamed_row.scale is None
    assert unnamed_row.scale_version is None
    assert unnamed_row.scale != ""
    assert unnamed_row.scale not in {"FACIT-Fatigue", "LDH", "ULN", "HAM-D", "NRS"}
    predicate = unnamed_row.scale_applicability_predicate_id
    assert isinstance(predicate, str) and predicate.strip()
    assert unnamed_row.source_text.encode("utf-8") == unnamed.source_text.encode("utf-8")

    named_applicability = getattr(
        named_row.scale_applicability,
        "value",
        named_row.scale_applicability,
    )
    assert named_applicability != "not_applicable"
    assert named_row.scale == "FACIT-Fatigue"
    assert named_row.scale_version == "v4"
    assert named_row.source_text.encode("utf-8") == named.source_text.encode("utf-8")


# ---------------------------------------------------------------------------
# Worker 03 adversarial audit: coverage, fidelity, isolation, shared contracts
# ---------------------------------------------------------------------------


def test_closed_catalog_every_design_element_appears_in_applicable_corpus() -> None:
    """封闭目录每个入排设计要素至少有一条适用观察，禁止目录与语料脱节。"""

    fields_in_corpus = {item.field for item in _APPLICABLE_OBSERVATIONS}
    assert fields_in_corpus == set(_ELIGIBILITY_DESIGN_ELEMENTS)
    assert len(_APPLICABLE_OBSERVATIONS) == 13


def test_non_eligibility_and_uncatalogued_population_fields_are_excluded() -> None:
    """非入排族与人口学族但未入封闭目录的字段不得进入投影。"""

    design = _design()
    uncatalogued_population = _observation(
        row_id="design-row-target-population",
        source_row_id="registry-row-target-population",
        observation_id="obs-target-population-alpha",
        field="target_population",
        source_field_name="Target Population",
        source_field_definition="Broad target population narrative",
        source_text="成人确诊 PNH 患者。",
    )
    mixed = _eligibility_corpus() + (uncatalogued_population,)
    view = _project_view(design, mixed)

    projected_ids = {row.observation_id for row in view.table_rows}
    assert projected_ids == set(_APPLICABLE_IDS)
    assert "obs-target-population-alpha" not in projected_ids
    assert "obs-trial-identity-alpha" not in projected_ids
    assert "obs-primary-endpoint-alpha" not in projected_ids
    assert "obs-analysis-population-alpha" not in projected_ids
    assert len(view.table_rows) == len(view.chart_rows) == len(view.evidence_by_chain_id)


def test_source_text_and_locator_anchors_are_byte_and_field_faithful() -> None:
    """原文含制表/CRLF/Unicode 时 byte-for-byte 保真；locator 全锚点字段原样保留。"""

    design = _design()
    rich_locator = EvidenceLocator(
        document_role="clinical-trial-registry",
        field_path="protocolSection.eligibilityModule.eligibilityCriteria",
        heading="Eligibility Criteria",
        page=3,
        table="Table E1",
        row="Inclusion-2",
        column="Criterion Text",
        paragraph="Inclusion Criteria",
        url="https://clinicaltrials.gov/study/NCT02912468#eligibility",
    )
    raw_text = "筛选期 LDH ≥ 1.5×ULN。\t保留制表符\r\n第二行 — café"
    observation = _observation(
        row_id="design-row-lab-fidelity",
        source_row_id="registry-row-lab-fidelity",
        observation_id="obs-lab-fidelity-adversarial",
        field="lab_or_biomarker",
        source_field_name="Laboratory / Biomarker",
        source_field_definition="Whitespace-preserving biomarker criterion",
        source_text=raw_text,
        operator=">=",
        threshold_value="1.5",
        threshold_unit="×ULN",
        assessment_timepoint="筛选期",
        source_locator=rich_locator,
    )
    before_text = observation.source_text
    before_locator = observation.source_locator.model_dump()

    view = _project_view(design, (observation,))
    row = _row_for_observation(view, observation)

    assert row.source_text == raw_text
    assert row.source_text.encode("utf-8") == raw_text.encode("utf-8")
    assert "\t" in row.source_text and "\r\n" in row.source_text
    assert row.source_locator == rich_locator
    assert row.source_locator.model_dump() == rich_locator.model_dump()
    for key in (
        "document_role",
        "field_path",
        "heading",
        "page",
        "table",
        "row",
        "column",
        "paragraph",
        "url",
    ):
        assert getattr(row.source_locator, key) == getattr(rich_locator, key)

    linked = view.evidence_by_chain_id[row.drilldown_chain_id]
    assert linked.source_text.encode("utf-8") == raw_text.encode("utf-8")
    assert linked.source_locator.model_dump() == rich_locator.model_dump()

    # 投影不得回写冻结观察。
    assert observation.source_text == before_text
    assert observation.source_locator.model_dump() == before_locator


def test_orphan_scale_version_without_named_scale_is_rejected() -> None:
    """仅有量表版本却没有量表名称属于结构矛盾，必须在观察边界拒绝。"""

    with pytest.raises(ValidationError, match="量表版本不能脱离量表名称单独存在"):
        _observation(
            row_id="design-row-orphan-scale-version",
            source_row_id="registry-row-orphan-scale-version",
            observation_id="obs-orphan-scale-version",
            field="exclusion_criterion",
            source_field_name="Exclusion Criteria",
            source_field_definition="Scale version without named scale",
            source_text="未命名量表的排除条件。",
            scale=None,
            scale_version="v9-orphan",
            assessment_timepoint="筛选期",
        )


def test_cross_trial_group_and_field_chain_ids_are_isolated() -> None:
    """同试验不同组别、同组别不同字段、仅 observation_id 不同时稳定链必须隔离。"""

    design = _design()
    base_kwargs = {
        "product_id": "product-ravulizumab",
        "trial_id": "trial-gamma",
        "cohort_id": "cohort-gamma",
        "field": "inclusion_criterion",
        "source_field_name": "Inclusion Criteria",
        "source_field_definition": "Isolation probe",
        "operator": ">=",
        "threshold_value": "1.5",
        "threshold_unit": "×ULN",
        "assessment_timepoint": "筛选期",
    }
    group_a = _observation(
        row_id="design-row-iso-group-a",
        source_row_id="registry-row-iso-group-a",
        observation_id="obs-iso-group-a",
        group_id="group-a",
        source_text="组别 A 入选：LDH ≥ 1.5×ULN。",
        **base_kwargs,
    )
    group_b = _observation(
        row_id="design-row-iso-group-b",
        source_row_id="registry-row-iso-group-b",
        observation_id="obs-iso-group-b",
        group_id="group-b",
        source_text="组别 B 入选：LDH ≥ 1.5×ULN。",
        **base_kwargs,
    )
    field_sibling = _observation(
        row_id="design-row-iso-field",
        source_row_id="registry-row-iso-field",
        observation_id="obs-iso-field",
        group_id="group-a",
        field="exclusion_criterion",
        source_field_name="Exclusion Criteria",
        source_field_definition="Isolation probe exclusion",
        source_text="组别 A 排除：活动性感染。",
        product_id="product-ravulizumab",
        trial_id="trial-gamma",
        cohort_id="cohort-gamma",
        assessment_timepoint="筛选期",
    )
    same_dims_different_obs = _observation(
        row_id="design-row-iso-obs-dup-dims",
        source_row_id="registry-row-iso-obs-dup-dims",
        observation_id="obs-iso-same-dims-different-id",
        group_id="group-a",
        source_text="同维不同观察 id 的入选条件。",
        **base_kwargs,
    )

    view = _project_view(
        design,
        (group_a, group_b, field_sibling, same_dims_different_obs),
    )
    rows = {row.observation_id: row for row in view.table_rows}
    assert len(rows) == 4
    chain_ids = {row.drilldown_chain_id for row in rows.values()}
    assert len(chain_ids) == 4

    assert rows["obs-iso-group-a"].drilldown_chain_id != rows["obs-iso-group-b"].drilldown_chain_id
    assert rows["obs-iso-group-a"].group_id != rows["obs-iso-group-b"].group_id
    assert (
        rows["obs-iso-group-a"].drilldown_chain_id
        != rows["obs-iso-field"].drilldown_chain_id
    )
    assert (
        rows["obs-iso-group-a"].drilldown_chain_id
        != rows["obs-iso-same-dims-different-id"].drilldown_chain_id
    )

    # 适应症维度也必须进入稳定链。
    alt_view = design.project_eligibility_drilldown(
        (group_a,),
        indication_id="indication-aHUS",
    )
    alt_row = _row_for_observation(alt_view, group_a)
    assert alt_row.indication_id == "indication-aHUS"
    assert alt_row.drilldown_chain_id != rows["obs-iso-group-a"].drilldown_chain_id


def test_table_chart_evidence_share_exact_chain_set_without_summary_substitution() -> None:
    """图/表/证据抽屉同源：链集合完全一致，证据原文不得被摘要替换。"""

    design = _design()
    view = _project_view(design, _eligibility_corpus())

    table_ids = {row.drilldown_chain_id for row in view.table_rows}
    chart_ids = {row.drilldown_chain_id for row in view.chart_rows}
    evidence_ids = set(view.evidence_by_chain_id)
    observation_ids = {row.observation_id for row in view.table_rows}

    assert table_ids == chart_ids == evidence_ids
    assert observation_ids == set(_APPLICABLE_IDS)
    assert len(view.table_rows) == len(_APPLICABLE_IDS)

    for row in view.table_rows:
        observation = _APPLICABLE_BY_ID[row.observation_id]
        linked = view.evidence_by_chain_id[row.drilldown_chain_id]
        assert linked.source_text == observation.source_text
        assert linked.source_text.encode("utf-8") == observation.source_text.encode(
            "utf-8"
        )
        # 禁止摘要冒充原文：长度与内容必须完整一致。
        assert len(linked.source_text) == len(observation.source_text)
        assert linked.source_locator == observation.source_locator


def test_blank_indication_rejected_and_duplicate_chain_collision_guarded() -> None:
    """空适应症拒绝；完全相同身份材料的重复观察触发稳定链碰撞保护。"""

    design = _design()
    observation = _APPLICABLE_OBSERVATIONS[0]
    with pytest.raises(Exception) as blank_exc:
        design.project_eligibility_drilldown((observation,), indication_id="  ")
    assert "适应症" in str(blank_exc.value) or "indication" in str(blank_exc.value).lower()

    with pytest.raises(Exception) as collision_exc:
        design.project_eligibility_drilldown(
            (observation, observation),
            indication_id=_INDICATION_ID,
        )
    message = str(collision_exc.value)
    assert "碰撞" in message or "collision" in message.lower()


def test_shared_design_observation_and_locator_contracts_still_roundtrip() -> None:
    """共享合同回归：投影消费的 DesignObservation / EvidenceLocator 仍满足 Task 7.1 合同。"""

    from ci_workflow.reports.c.contracts import (
        DesignObservation as SharedDesignObservation,
    )
    from ci_workflow.reports.c.contracts import (
        validate_design_observation,
    )

    design = _design()
    view = _project_view(design, _eligibility_corpus())
    assert len(view.table_rows) == len(_APPLICABLE_OBSERVATIONS)

    for observation in _APPLICABLE_OBSERVATIONS:
        # 构造合同与校验入口仍接受语料观察（共享合同未因 Task 7.2 破坏）。
        revalidated = SharedDesignObservation.model_validate(
            observation.model_dump(mode="python")
        )
        assert revalidated == observation
        validate_design_observation(observation)

        row = _row_for_observation(view, observation)
        # locator 合同仍禁止空锚点集合；投影后的 locator 可再构造。
        rebuilt = EvidenceLocator.model_validate(row.source_locator.model_dump())
        assert rebuilt == observation.source_locator
