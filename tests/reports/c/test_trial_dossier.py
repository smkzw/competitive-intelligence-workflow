"""Task 7.3 C 类逐试验完整设计档案与设计图谱独立审计。

合同攻击面（本文件不修改实现）：
- 逐试验档案观察身份集合必须等于该试验全部已校验输入观察，禁止 allowlist 截断；
- 兄弟试验不得泄漏进目标档案；
- 每条投影行保留观察身份、原文、来源版本、完整 EvidenceLocator、披露/审查/冲突处置；
- 设计图谱与专题投影在输入重排下保持稳定身份集合；不得发明未公开统计；
- 入选/排除视图复用 Task 7.2 投影入口，不复制下钻逻辑；
- 档案 observation_ids 顺序应与 table_rows 同源对齐（与 DesignTopicView 一致）。
"""

from __future__ import annotations

from collections.abc import Sequence
from types import ModuleType
from typing import Any

import pytest

from ci_workflow.domain.enums import FactDisclosureState, FactReviewState
from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.gates.models import ConflictDisposition, DisclosureMaturity, SourceRole
from ci_workflow.reports.c.contracts import DesignFieldFamily, DesignObservation

_INDICATION_ID = "indication-pnh"
_TRIAL_ALPHA = "trial-alpha"
_TRIAL_BETA = "trial-beta"

_LOCATOR_ALPHA = EvidenceLocator(
    document_role="clinical-trial-registry",
    field_path="protocolSection.designModule",
    heading="Study Design",
    table="Design Facts",
    row="Alpha registry row",
    column="Value",
    url="https://clinicaltrials.gov/study/NCT02912468#design",
    paragraph="Design",
)
_LOCATOR_BETA = EvidenceLocator(
    document_role="clinical-trial-registry",
    field_path="protocolSection.designModule",
    heading="Study Design",
    table="Design Facts",
    row="Beta registry row",
    column="Value",
    url="https://clinicaltrials.gov/study/NCT00000002#design",
    paragraph="Design",
)


def _pages() -> ModuleType:
    """延迟导入 C 类设计视图投影；缺失时精确失败。"""

    import importlib

    try:
        return importlib.import_module("ci_workflow.reports.c.pages")
    except ModuleNotFoundError as exc:
        pytest.fail(f"C 类设计视图投影尚未实现：{exc}", pytrace=False)


def _observation(**overrides: object) -> DesignObservation:
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "row_id": "design-row-dossier",
        "source_row_id": "registry-row-dossier",
        "observation_id": "obs-dossier-default",
        "product_id": "product-ravulizumab",
        "trial_id": _TRIAL_ALPHA,
        "cohort_id": "cohort-alpha",
        "group_id": "group-all-enrolled",
        "field_family": DesignFieldFamily.TRIAL_IDENTITY,
        "field": "stage",
        "source_field_name": "试验阶段",
        "source_field_definition": "Highest clinical development stage",
        "source_text": "III 期关键注册试验。",
        "scale": None,
        "scale_version": None,
        "operator": None,
        "threshold_value": None,
        "threshold_unit": None,
        "assessment_timepoint": None,
        "stage": "III",
        "development_role": "关键注册试验",
        "randomization": None,
        "blinding": None,
        "source_version_id": "registry-version-alpha-1",
        "source_locator": _LOCATOR_ALPHA,
        "source_role": SourceRole.CLINICAL_TRIAL_REGISTRY,
        "disclosure_maturity": DisclosureMaturity.REGISTRY_RESULT_OR_PRIMARY_REPORT,
        "review_state": FactReviewState.ACCEPTED,
        "disclosure_state": FactDisclosureState.REPORTED_VALUE,
        "conflict_disposition": ConflictDisposition.RESOLVED_SELECTED_ACCEPTED_FACT,
        "reported_zero_text": None,
        "route_receipt_id": None,
        "applicability_predicate_id": None,
        "compatibility_rule": "c-design-v1",
        "difference_labels_zh": (),
    }
    payload.update(overrides)
    return DesignObservation.model_validate(payload)


def _dossier_corpus() -> tuple[DesignObservation, ...]:
    """覆盖全部字段族 + 兄弟试验 + 未公开统计 + 零值报告的确定性语料。"""

    return (
        _observation(
            row_id="design-row-stage",
            source_row_id="registry-row-stage",
            observation_id="obs-alpha-stage",
            field_family=DesignFieldFamily.TRIAL_IDENTITY,
            field="stage",
            source_field_name="试验阶段",
            source_field_definition="Highest clinical development stage",
            source_text="III 期关键注册试验。",
            stage="III",
            development_role="关键注册试验",
        ),
        _observation(
            row_id="design-row-population",
            source_row_id="registry-row-population",
            observation_id="obs-alpha-population",
            field_family=DesignFieldFamily.POPULATION,
            field="target_population",
            source_field_name="目标人群",
            source_field_definition="Adults with PNH",
            source_text="确诊 PNH 的成人受试者。",
            assessment_timepoint="筛选期",
        ),
        _observation(
            row_id="design-row-inclusion",
            source_row_id="registry-row-inclusion",
            observation_id="obs-alpha-inclusion",
            field_family=DesignFieldFamily.POPULATION,
            field="inclusion_criterion",
            source_field_name="Inclusion Criteria",
            source_field_definition="Registry inclusion criterion text",
            source_text="筛选期 LDH ≥ 1.5×ULN。",
            operator=">=",
            threshold_value="1.5",
            threshold_unit="×ULN",
            assessment_timepoint="筛选期",
        ),
        _observation(
            row_id="design-row-exclusion",
            source_row_id="registry-row-exclusion",
            observation_id="obs-alpha-exclusion",
            field_family=DesignFieldFamily.POPULATION,
            field="exclusion_criterion",
            source_field_name="Exclusion Criteria",
            source_field_definition="Registry exclusion criterion text",
            source_text="活动性未控制感染。",
            assessment_timepoint="筛选期",
        ),
        _observation(
            row_id="design-row-grouping",
            source_row_id="registry-row-grouping",
            observation_id="obs-alpha-grouping",
            field_family=DesignFieldFamily.GROUPING,
            field="arm_randomization_blinding",
            source_field_name="分组/随机/盲法",
            source_field_definition="Randomized double-blind parallel arms",
            source_text="1:1 随机、双盲、平行对照。",
            randomization="1:1 随机",
            blinding="双盲",
        ),
        _observation(
            row_id="design-row-intervention",
            source_row_id="registry-row-intervention",
            observation_id="obs-alpha-intervention",
            field_family=DesignFieldFamily.INTERVENTION,
            field="experimental_arm",
            source_field_name="试验组干预",
            source_field_definition="Ravulizumab IV dosing",
            source_text="Ravulizumab 按体重静脉给药。",
            group_id="group-experimental",
        ),
        _observation(
            row_id="design-row-dose",
            source_row_id="registry-row-dose",
            observation_id="obs-alpha-dose",
            field_family=DesignFieldFamily.DOSE_SCHEDULE,
            field="treatment_duration",
            source_field_name="疗程",
            source_field_definition="Primary treatment period",
            source_text="主要治疗期 26 周。",
            assessment_timepoint="第26周",
        ),
        _observation(
            row_id="design-row-endpoint",
            source_row_id="registry-row-endpoint",
            observation_id="obs-alpha-endpoint",
            field_family=DesignFieldFamily.ENDPOINT,
            field="primary_endpoint_definition",
            source_field_name="LDH 正常化",
            source_field_definition=(
                "Proportion of subjects with LDH ≤1×ULN at Week 26"
            ),
            source_text="第 26 周 LDH 正常化（≤1×ULN）的受试者比例。",
        ),
        _observation(
            row_id="design-row-timepoint",
            source_row_id="registry-row-timepoint",
            observation_id="obs-alpha-timepoint",
            field_family=DesignFieldFamily.TIMEPOINT,
            field="primary_endpoint_timepoint",
            source_field_name="主要终点时间点",
            source_field_definition="Primary endpoint assessment timepoint",
            source_text="主要终点评估时间点：第 26 周。",
            assessment_timepoint="第26周",
        ),
        _observation(
            row_id="design-row-sample-size",
            source_row_id="registry-row-sample-size",
            observation_id="obs-alpha-sample-size",
            field_family=DesignFieldFamily.SAMPLE_SIZE,
            field="planned_sample_size",
            source_field_name="计划样本量",
            source_field_definition="Planned enrollment",
            source_text="计划入组 246 例。",
            threshold_value="246",
            threshold_unit="例",
        ),
        _observation(
            row_id="design-row-operational",
            source_row_id="registry-row-operational",
            observation_id="obs-alpha-operational",
            field_family=DesignFieldFamily.OPERATIONAL,
            field="follow_up_schedule",
            source_field_name="随访安排",
            source_field_definition="Post-treatment follow-up",
            source_text="治疗结束后随访至第 52 周。",
            assessment_timepoint="第52周",
        ),
        _observation(
            row_id="design-row-stats-disclosed",
            source_row_id="registry-row-stats-disclosed",
            observation_id="obs-alpha-stats-disclosed",
            field_family=DesignFieldFamily.STATISTICAL,
            field="analysis_population",
            source_field_name="分析人群",
            source_field_definition="Primary analysis population",
            source_text="主要分析集为 FAS。",
        ),
        _observation(
            row_id="design-row-stats-undisclosed",
            source_row_id="registry-row-stats-undisclosed",
            observation_id="obs-alpha-stats-undisclosed",
            field_family=DesignFieldFamily.STATISTICAL,
            field="statistical_model",
            source_field_name="统计模型与检验",
            source_field_definition="Primary statistical model",
            source_text="登记资料未公开具体统计模型与检验方法。",
            disclosure_state=FactDisclosureState.NOT_PUBLICLY_DISCLOSED,
            operator=None,
            threshold_value=None,
            threshold_unit=None,
            scale=None,
            scale_version=None,
        ),
        _observation(
            row_id="design-row-stats-zero",
            source_row_id="registry-row-stats-zero",
            observation_id="obs-alpha-stats-zero",
            field_family=DesignFieldFamily.SAMPLE_SIZE,
            field="interim_events",
            source_field_name="中期事件数",
            source_field_definition="Interim observed events",
            source_text="中期分析观察到 0 例协议定义事件。",
            disclosure_state=FactDisclosureState.REPORTED_ZERO,
            reported_zero_text="0 例协议定义事件",
        ),
        # 同试验另一组别：不得因组别不同被档案截断。
        _observation(
            row_id="design-row-control",
            source_row_id="registry-row-control",
            observation_id="obs-alpha-control",
            field_family=DesignFieldFamily.INTERVENTION,
            field="control_arm",
            source_field_name="对照组干预",
            source_field_definition="Eculizumab IV dosing",
            source_text="Eculizumab 按标签静脉给药。",
            group_id="group-control",
        ),
        # 兄弟试验：不得泄漏进 alpha 档案。
        _observation(
            row_id="design-row-beta-stage",
            source_row_id="registry-row-beta-stage",
            observation_id="obs-beta-stage",
            product_id="product-eculizumab",
            trial_id=_TRIAL_BETA,
            cohort_id="cohort-beta",
            group_id="group-experimental",
            field_family=DesignFieldFamily.TRIAL_IDENTITY,
            field="stage",
            source_field_name="试验阶段",
            source_field_definition="Highest clinical development stage",
            source_text="III 期对照试验。",
            stage="III",
            development_role="关键对照试验",
            source_version_id="registry-version-beta-1",
            source_locator=_LOCATOR_BETA,
        ),
        _observation(
            row_id="design-row-beta-endpoint",
            source_row_id="registry-row-beta-endpoint",
            observation_id="obs-beta-endpoint",
            product_id="product-eculizumab",
            trial_id=_TRIAL_BETA,
            cohort_id="cohort-beta",
            group_id="group-experimental",
            field_family=DesignFieldFamily.ENDPOINT,
            field="primary_endpoint_definition",
            source_field_name="LDH 正常化",
            source_field_definition="Proportion with LDH ≤1.5×ULN at Week 16",
            source_text="试验 B：第 16 周 LDH≤1.5×ULN 比例。",
            source_version_id="registry-version-beta-1",
            source_locator=_LOCATOR_BETA,
        ),
    )


_CORPUS = _dossier_corpus()
_CORPUS_BY_ID = {item.observation_id: item for item in _CORPUS}
_ALPHA_IDS = frozenset(
    item.observation_id for item in _CORPUS if item.trial_id == _TRIAL_ALPHA
)
_BETA_IDS = frozenset(
    item.observation_id for item in _CORPUS if item.trial_id == _TRIAL_BETA
)


def _require_callable(pages: ModuleType, name: str) -> Any:
    func = getattr(pages, name, None)
    if not callable(func):
        pytest.fail(f"C 类设计视图缺少 {name}", pytrace=False)
    return func


def _dossier(pages: ModuleType, observations: Sequence[DesignObservation], trial_id: str) -> Any:
    return _require_callable(pages, "project_trial_dossier")(
        observations, trial_id=trial_id
    )


def _assert_source_fidelity(row: Any, source: DesignObservation) -> None:
    assert row.schema_version == source.schema_version
    assert row.row_id == source.row_id
    assert row.source_row_id == source.source_row_id
    assert row.observation_id == source.observation_id
    assert row.product_id == source.product_id
    assert row.trial_id == source.trial_id
    assert row.cohort_id == source.cohort_id
    assert row.group_id == source.group_id
    assert row.field_family == source.field_family
    assert row.field == source.field
    assert row.source_field_name == source.source_field_name
    assert row.source_field_definition == source.source_field_definition
    assert row.source_text.encode("utf-8") == source.source_text.encode("utf-8")
    assert row.source_version_id == source.source_version_id
    assert row.source_locator == source.source_locator
    assert row.source_locator.model_dump() == source.source_locator.model_dump()
    assert row.source_role == source.source_role
    assert row.disclosure_maturity == source.disclosure_maturity
    assert row.disclosure_state == source.disclosure_state
    assert row.review_state == source.review_state
    assert row.conflict_disposition == source.conflict_disposition
    assert row.assessment_timepoint == source.assessment_timepoint
    assert row.stage == source.stage
    assert row.development_role == source.development_role
    assert row.randomization == source.randomization
    assert row.blinding == source.blinding
    assert row.scale == source.scale
    assert row.scale_version == source.scale_version
    assert row.operator == source.operator
    assert row.threshold_value == source.threshold_value
    assert row.threshold_unit == source.threshold_unit
    assert row.reported_zero_text == source.reported_zero_text
    assert row.route_receipt_id == source.route_receipt_id
    assert row.applicability_predicate_id == source.applicability_predicate_id
    assert row.compatibility_rule == source.compatibility_rule
    assert tuple(row.difference_labels_zh) == tuple(source.difference_labels_zh)


# ---------------------------------------------------------------------------
# Independent audit cases
# ---------------------------------------------------------------------------


def test_pages_module_exposes_dossier_and_design_projectors() -> None:
    pages = _pages()
    for name in (
        "project_trial_dossier",
        "project_design_map",
        "project_population_view",
        "project_intervention_view",
        "project_visit_schedule_view",
        "project_statistics_view",
        "project_inclusion_view",
        "project_exclusion_view",
    ):
        assert callable(getattr(pages, name, None)), f"需要 {name}"


def test_trial_dossier_observation_set_equals_all_validated_inputs_for_trial() -> None:
    """档案身份集合必须等于该试验全部输入观察；禁止代表性子集或字段族 allowlist 截断。"""

    pages = _pages()
    view = _dossier(pages, _CORPUS, _TRIAL_ALPHA)
    projected_ids = {row.observation_id for row in view.table_rows}

    assert projected_ids == set(_ALPHA_IDS)
    assert set(view.observation_ids) == set(_ALPHA_IDS)
    assert len(view.table_rows) == len(_ALPHA_IDS)
    assert len(set(view.observation_ids)) == len(view.observation_ids)

    # 全字段族均须进入档案，不得只保留预设专题字段。
    projected_families = {row.field_family for row in view.table_rows}
    assert projected_families == set(DesignFieldFamily)

    # 对照组与未公开统计/零值观察不得被截断。
    for required_id in (
        "obs-alpha-control",
        "obs-alpha-stats-undisclosed",
        "obs-alpha-stats-zero",
        "obs-alpha-operational",
    ):
        assert required_id in projected_ids


def test_sibling_trial_does_not_leak_into_dossier() -> None:
    pages = _pages()
    alpha = _dossier(pages, _CORPUS, _TRIAL_ALPHA)
    beta = _dossier(pages, _CORPUS, _TRIAL_BETA)

    alpha_ids = {row.observation_id for row in alpha.table_rows}
    beta_ids = {row.observation_id for row in beta.table_rows}

    assert alpha_ids == set(_ALPHA_IDS)
    assert beta_ids == set(_BETA_IDS)
    assert alpha_ids.isdisjoint(beta_ids)
    assert "obs-beta-stage" not in alpha_ids
    assert "obs-beta-endpoint" not in alpha_ids
    assert "obs-alpha-stage" not in beta_ids
    assert alpha.trial_id == _TRIAL_ALPHA
    assert beta.trial_id == _TRIAL_BETA


@pytest.mark.parametrize("observation_id", sorted(_ALPHA_IDS))
def test_each_dossier_row_keeps_full_source_fidelity(observation_id: str) -> None:
    pages = _pages()
    source = _CORPUS_BY_ID[observation_id]
    view = _dossier(pages, _CORPUS, _TRIAL_ALPHA)
    matches = [row for row in view.table_rows if row.observation_id == observation_id]
    assert len(matches) == 1
    _assert_source_fidelity(matches[0], source)
    assert isinstance(matches[0].row_identity, str) and matches[0].row_identity.strip()


def test_dossier_chart_and_table_are_same_ordered_fact_set() -> None:
    pages = _pages()
    view = _dossier(pages, _CORPUS, _TRIAL_ALPHA)
    assert tuple(view.chart_rows) == tuple(view.table_rows)
    row_order_ids = tuple(row.observation_id for row in view.table_rows)
    # 与 DesignTopicView 对齐：observation_ids 顺序应跟随 table_rows，而非另做字母序重排。
    assert tuple(view.observation_ids) == row_order_ids, (
        "TrialDossierView.observation_ids 必须与 table_rows 顺序同源对齐；"
        f" actual={tuple(view.observation_ids)!r} expected={row_order_ids!r}"
    )


def test_input_reordering_does_not_change_dossier_or_design_map_identities() -> None:
    pages = _pages()
    dossier_project = _require_callable(pages, "project_trial_dossier")
    map_project = _require_callable(pages, "project_design_map")

    baseline_dossier = dossier_project(_CORPUS, trial_id=_TRIAL_ALPHA)
    baseline_map = map_project(_CORPUS)

    reversed_corpus = tuple(reversed(_CORPUS))
    # 交错重排：把 beta 观察插到 alpha 中间，攻击顺序依赖过滤。
    interleaved = []
    alpha_items = [item for item in _CORPUS if item.trial_id == _TRIAL_ALPHA]
    beta_items = [item for item in _CORPUS if item.trial_id == _TRIAL_BETA]
    for index, item in enumerate(alpha_items):
        interleaved.append(item)
        if index < len(beta_items):
            interleaved.append(beta_items[index])
    interleaved.extend(beta_items[len(alpha_items) :])
    adversarial = tuple(interleaved)

    for ordered in (reversed_corpus, adversarial):
        dossier = dossier_project(ordered, trial_id=_TRIAL_ALPHA)
        design_map = map_project(ordered)

        assert {row.observation_id for row in dossier.table_rows} == set(_ALPHA_IDS)
        assert {row.row_identity for row in dossier.table_rows} == {
            row.row_identity for row in baseline_dossier.table_rows
        }
        assert [row.observation_id for row in dossier.table_rows] == [
            row.observation_id for row in baseline_dossier.table_rows
        ]
        assert [row.row_identity for row in dossier.table_rows] == [
            row.row_identity for row in baseline_dossier.table_rows
        ]

        assert {row.observation_id for row in design_map.table_rows} == {
            item.observation_id for item in _CORPUS
        }
        assert [row.row_identity for row in design_map.table_rows] == [
            row.row_identity for row in baseline_map.table_rows
        ]
        assert tuple(design_map.observation_ids) == tuple(
            row.observation_id for row in design_map.table_rows
        )


def test_design_map_keeps_all_observations_without_family_allowlist_truncation() -> None:
    pages = _pages()
    view = _require_callable(pages, "project_design_map")(_CORPUS)
    projected_ids = {row.observation_id for row in view.table_rows}
    assert projected_ids == {item.observation_id for item in _CORPUS}
    assert {row.field_family for row in view.table_rows} == {
        item.field_family for item in _CORPUS
    }
    assert tuple(view.chart_rows) == tuple(view.table_rows)


def test_statistics_view_preserves_undisclosed_state_and_does_not_invent_details() -> None:
    pages = _pages()
    view = _require_callable(pages, "project_statistics_view")(_CORPUS)
    rows_by_id = {row.observation_id: row for row in view.table_rows}

    assert "obs-alpha-stats-undisclosed" in rows_by_id
    assert "obs-alpha-stats-disclosed" in rows_by_id
    assert "obs-alpha-sample-size" in rows_by_id
    # 非统计族不得进入统计专题。
    assert "obs-alpha-endpoint" not in rows_by_id
    assert "obs-alpha-population" not in rows_by_id

    undisclosed = rows_by_id["obs-alpha-stats-undisclosed"]
    source = _CORPUS_BY_ID["obs-alpha-stats-undisclosed"]
    _assert_source_fidelity(undisclosed, source)
    assert undisclosed.disclosure_state is FactDisclosureState.NOT_PUBLICLY_DISCLOSED
    assert undisclosed.operator is None
    assert undisclosed.threshold_value is None
    assert undisclosed.threshold_unit is None
    assert undisclosed.scale is None
    assert "未公开" in undisclosed.source_text
    # 禁止把未公开模型改写成常见行业做法文案。
    forbidden_inventions = ("ANCOVA", "Cox", "分层检验", "行业常见", "默认模型")
    assert not any(token in undisclosed.source_text for token in forbidden_inventions)


def test_topical_views_are_family_scoped_and_order_invariant() -> None:
    pages = _pages()
    population = _require_callable(pages, "project_population_view")
    intervention = _require_callable(pages, "project_intervention_view")
    visits = _require_callable(pages, "project_visit_schedule_view")

    baseline_population = population(_CORPUS)
    baseline_intervention = intervention(_CORPUS)
    baseline_visits = visits(_CORPUS)
    reversed_corpus = tuple(reversed(_CORPUS))

    assert {row.field_family for row in baseline_population.table_rows} == {
        DesignFieldFamily.POPULATION
    }
    assert {row.field_family for row in baseline_intervention.table_rows} <= {
        DesignFieldFamily.GROUPING,
        DesignFieldFamily.INTERVENTION,
        DesignFieldFamily.DOSE_SCHEDULE,
    }
    assert {row.field_family for row in baseline_visits.table_rows} <= {
        DesignFieldFamily.DOSE_SCHEDULE,
        DesignFieldFamily.OPERATIONAL,
        DesignFieldFamily.TIMEPOINT,
    }

    for projector, baseline in (
        (population, baseline_population),
        (intervention, baseline_intervention),
        (visits, baseline_visits),
    ):
        shuffled = projector(reversed_corpus)
        assert [row.row_identity for row in shuffled.table_rows] == [
            row.row_identity for row in baseline.table_rows
        ]
        assert tuple(shuffled.observation_ids) == tuple(
            row.observation_id for row in shuffled.table_rows
        )


def test_inclusion_and_exclusion_views_reuse_task72_without_copying_non_criteria() -> None:
    pages = _pages()
    inclusion = _require_callable(pages, "project_inclusion_view")(
        _CORPUS, indication_id=_INDICATION_ID
    )
    exclusion = _require_callable(pages, "project_exclusion_view")(
        _CORPUS, indication_id=_INDICATION_ID
    )

    inclusion_ids = {row.observation_id for row in inclusion.table_rows}
    exclusion_ids = {row.observation_id for row in exclusion.table_rows}

    assert inclusion_ids == {"obs-alpha-inclusion"}
    assert exclusion_ids == {"obs-alpha-exclusion"}
    # 人群其他要素应留在人口学专题，不得被入选/排除视图吞并。
    assert "obs-alpha-population" not in inclusion_ids
    assert "obs-alpha-population" not in exclusion_ids

    # 复用 Task 7.2：行上应暴露稳定下钻链身份，而非自建第二套链。
    inclusion_row = next(iter(inclusion.table_rows))
    assert getattr(inclusion_row, "drilldown_chain_id", None)
    assert inclusion_row.source_text.encode("utf-8") == _CORPUS_BY_ID[
        "obs-alpha-inclusion"
    ].source_text.encode("utf-8")


def test_dossier_rejects_blank_trial_id_and_duplicate_observation_identity() -> None:
    pages = _pages()
    project = _require_callable(pages, "project_trial_dossier")

    with pytest.raises((ValueError, TypeError)) as blank_exc:
        project(_CORPUS, trial_id="   ")
    blank_message = str(blank_exc.value)
    assert "试验" in blank_message or "trial" in blank_message.lower()

    duplicate = (
        _CORPUS_BY_ID["obs-alpha-stage"],
        _CORPUS_BY_ID["obs-alpha-stage"].model_copy(
            update={
                "row_id": "design-row-stage-dup",
                "source_row_id": "registry-row-stage-dup",
                "field": "development_role",
                "source_field_name": "研发角色",
                "source_field_definition": "Development role label",
                "source_text": "关键注册试验（重复观察身份攻击）。",
            }
        ),
    )
    with pytest.raises((ValueError, TypeError)) as dup_exc:
        project(duplicate, trial_id=_TRIAL_ALPHA)
    dup_message = str(dup_exc.value)
    assert "重复" in dup_message or "一致" in dup_message or "duplicate" in dup_message.lower()


def test_shared_design_observation_contract_still_rejects_unknown_fields() -> None:
    """共享合同回归：页面投影依赖的 DesignObservation 重新校验边界保持有效。"""

    from ci_workflow.reports.c.contracts import (
        DesignObservationError,
        validate_design_observation,
    )

    payload = _CORPUS_BY_ID["obs-alpha-stage"].model_dump(mode="python")
    payload["unexpected_page_only_field"] = "should-fail"
    with pytest.raises(DesignObservationError):
        validate_design_observation(payload)

    pages = _pages()
    with pytest.raises((ValueError, TypeError)):
        _require_callable(pages, "project_trial_dossier")(
            (payload,), trial_id=_TRIAL_ALPHA
        )
