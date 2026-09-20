"""Task 7.3 C 类终点—定义—时间点三元身份 RED 测试。

合同断言（先失败后通过；本文件不提供实现 stub）：
- 投影入口位于 ``reports.c.pages.project_endpoint_definition_timepoint``；
- 可比较终点行身份是不可拆分三元组：终点显示名、完整来源定义、评估时间点；
- 终点观察与时间点观察仅能通过现有合同字段 ``field`` 上的显式配对键结合：
  终点 ``{pairing_key}_definition`` ↔ 时间点 ``{pairing_key}_timepoint``，且必须同一
  product/trial/cohort/group；禁止按输入顺序、显示名近似或跨试验/组别回退配对；
- 同名但定义或时间点不同的终点保留独立三元身份，不得静默合并；
- 缺定义或缺配对时间点不得生成可比较终点行；
- 每条投影行保留两端观察身份、原文、来源版本、完整 EvidenceLocator、披露/审查/
  冲突处置；输入重排不得改变稳定身份集合。
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

_PAIR_PRIMARY = "primary_endpoint"
_PAIR_SECONDARY_LDH = "secondary_endpoint_ldh"
_PAIR_SECONDARY_FACIT = "secondary_endpoint_facit"
_PAIR_SIBLING = "primary_endpoint"  # 与主试验同名配对键，但跨试验不得误配

_LOCATOR_ALPHA_ENDPOINT = EvidenceLocator(
    document_role="clinical-trial-registry",
    field_path="protocolSection.outcomesModule.primaryOutcomes[0].measure",
    heading="Primary Outcome Measures",
    table="Outcome Measures",
    row="Primary: LDH normalization",
    column="Measure",
    url="https://clinicaltrials.gov/study/NCT02912468#outcomes",
)
_LOCATOR_ALPHA_TIMEPOINT = EvidenceLocator(
    document_role="clinical-trial-registry",
    field_path="protocolSection.outcomesModule.primaryOutcomes[0].timeFrame",
    heading="Primary Outcome Measures",
    table="Outcome Measures",
    row="Primary: LDH normalization",
    column="Time Frame",
    url="https://clinicaltrials.gov/study/NCT02912468#outcomes",
)
_LOCATOR_BETA_ENDPOINT = EvidenceLocator(
    document_role="clinical-trial-registry",
    field_path="protocolSection.outcomesModule.primaryOutcomes[0].measure",
    heading="Primary Outcome Measures",
    table="Outcome Measures",
    row="Primary: LDH normalization (sibling)",
    column="Measure",
    url="https://clinicaltrials.gov/study/NCT00000002#outcomes",
)
_LOCATOR_BETA_TIMEPOINT = EvidenceLocator(
    document_role="clinical-trial-registry",
    field_path="protocolSection.outcomesModule.primaryOutcomes[0].timeFrame",
    heading="Primary Outcome Measures",
    table="Outcome Measures",
    row="Primary: LDH normalization (sibling)",
    column="Time Frame",
    url="https://clinicaltrials.gov/study/NCT00000002#outcomes",
)


def _pages() -> ModuleType:
    """延迟导入计划中的 C 类设计视图投影；实现前每个用例精确失败而非收集期中断。"""

    import importlib

    try:
        return importlib.import_module("ci_workflow.reports.c.pages")
    except ModuleNotFoundError as exc:
        pytest.fail(f"C 类设计视图投影尚未实现：{exc}", pytrace=False)


def _observation(**overrides: object) -> DesignObservation:
    """构造一条已接受的登记来源设计观察；默认属于终点族。"""

    payload: dict[str, object] = {
        "schema_version": "1.0",
        "row_id": "design-row-endpoint",
        "source_row_id": "registry-row-endpoint",
        "observation_id": "obs-endpoint-alpha-primary",
        "product_id": "product-ravulizumab",
        "trial_id": "trial-alpha",
        "cohort_id": "cohort-alpha",
        "group_id": "group-all-enrolled",
        "field_family": DesignFieldFamily.ENDPOINT,
        "field": f"{_PAIR_PRIMARY}_definition",
        "source_field_name": "LDH 正常化",
        "source_field_definition": (
            "Proportion of subjects with LDH ≤1×ULN at Week 26"
        ),
        "source_text": "第 26 周 LDH 正常化（≤1×ULN）的受试者比例。",
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
        "source_locator": _LOCATOR_ALPHA_ENDPOINT,
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


def _endpoint(
    *,
    pairing_key: str,
    observation_id: str,
    display_name: str,
    definition: str,
    source_text: str,
    locator: EvidenceLocator,
    product_id: str = "product-ravulizumab",
    trial_id: str = "trial-alpha",
    cohort_id: str = "cohort-alpha",
    group_id: str = "group-all-enrolled",
    source_version_id: str = "registry-version-alpha-1",
    assessment_timepoint: str | None = None,
    **extra: object,
) -> DesignObservation:
    return _observation(
        row_id=f"design-row-{observation_id}",
        source_row_id=f"registry-row-{observation_id}",
        observation_id=observation_id,
        product_id=product_id,
        trial_id=trial_id,
        cohort_id=cohort_id,
        group_id=group_id,
        field_family=DesignFieldFamily.ENDPOINT,
        field=f"{pairing_key}_definition",
        source_field_name=display_name,
        source_field_definition=definition,
        source_text=source_text,
        assessment_timepoint=assessment_timepoint,
        source_version_id=source_version_id,
        source_locator=locator,
        **extra,
    )


def _timepoint(
    *,
    pairing_key: str,
    observation_id: str,
    assessment_timepoint: str,
    source_text: str,
    locator: EvidenceLocator,
    display_name: str | None = None,
    product_id: str = "product-ravulizumab",
    trial_id: str = "trial-alpha",
    cohort_id: str = "cohort-alpha",
    group_id: str = "group-all-enrolled",
    source_version_id: str = "registry-version-alpha-1",
    **extra: object,
) -> DesignObservation:
    return _observation(
        row_id=f"design-row-{observation_id}",
        source_row_id=f"registry-row-{observation_id}",
        observation_id=observation_id,
        product_id=product_id,
        trial_id=trial_id,
        cohort_id=cohort_id,
        group_id=group_id,
        field_family=DesignFieldFamily.TIMEPOINT,
        field=f"{pairing_key}_timepoint",
        source_field_name=display_name or f"{pairing_key} 评估时间点",
        source_field_definition=f"{pairing_key} 评估时间点定义",
        source_text=source_text,
        assessment_timepoint=assessment_timepoint,
        source_version_id=source_version_id,
        source_locator=locator,
        **extra,
    )


def _endpoint_timepoint_corpus() -> tuple[DesignObservation, ...]:
    """确定性登记观察语料：可配对终点、同名异义/异时点、跨试验对照与噪声。"""

    return (
        # 主终点：可配对三元（故意在终点观察上放一个不得单独采用的时间点噪声）。
        _endpoint(
            pairing_key=_PAIR_PRIMARY,
            observation_id="obs-endpoint-alpha-primary",
            display_name="LDH 正常化",
            definition="Proportion of subjects with LDH ≤1×ULN at Week 26",
            source_text="第 26 周 LDH 正常化（≤1×ULN）的受试者比例。",
            locator=_LOCATOR_ALPHA_ENDPOINT,
            assessment_timepoint="筛选期",  # 噪声：不得替代配对时间点观察
        ),
        _timepoint(
            pairing_key=_PAIR_PRIMARY,
            observation_id="obs-timepoint-alpha-primary",
            assessment_timepoint="第26周",
            source_text="主要终点评估时间点：第 26 周。",
            locator=_LOCATOR_ALPHA_TIMEPOINT,
            display_name="LDH 正常化",
        ),
        # 同名、不同定义、不同时间点：必须独立行。
        _endpoint(
            pairing_key=_PAIR_SECONDARY_LDH,
            observation_id="obs-endpoint-alpha-secondary-ldh",
            display_name="LDH 正常化",
            definition=(
                "Change from baseline in LDH at Week 52 (secondary definition)"
            ),
            source_text="次要终点：第 52 周 LDH 相对基线变化。",
            locator=EvidenceLocator(
                document_role="clinical-trial-registry",
                field_path="protocolSection.outcomesModule.secondaryOutcomes[0].measure",
                heading="Secondary Outcome Measures",
                table="Outcome Measures",
                row="Secondary: LDH change",
                column="Measure",
                url="https://clinicaltrials.gov/study/NCT02912468#outcomes",
            ),
        ),
        _timepoint(
            pairing_key=_PAIR_SECONDARY_LDH,
            observation_id="obs-timepoint-alpha-secondary-ldh",
            assessment_timepoint="第52周",
            source_text="次要 LDH 终点评估时间点：第 52 周。",
            locator=EvidenceLocator(
                document_role="clinical-trial-registry",
                field_path=(
                    "protocolSection.outcomesModule.secondaryOutcomes[0].timeFrame"
                ),
                heading="Secondary Outcome Measures",
                table="Outcome Measures",
                row="Secondary: LDH change",
                column="Time Frame",
                url="https://clinicaltrials.gov/study/NCT02912468#outcomes",
            ),
            display_name="LDH 正常化",
        ),
        # 同名显示名近似但配对键不同：不得因文本相似与主终点合并。
        _endpoint(
            pairing_key=_PAIR_SECONDARY_FACIT,
            observation_id="obs-endpoint-alpha-facit",
            display_name="LDH 正常化率",
            definition="FACIT-Fatigue total score change from baseline at Week 26",
            source_text="第 26 周 FACIT-Fatigue 总分相对基线变化。",
            locator=EvidenceLocator(
                document_role="clinical-trial-registry",
                field_path="protocolSection.outcomesModule.secondaryOutcomes[1].measure",
                heading="Secondary Outcome Measures",
                table="Outcome Measures",
                row="Secondary: FACIT-Fatigue",
                column="Measure",
                url="https://clinicaltrials.gov/study/NCT02912468#outcomes",
            ),
            scale="FACIT-Fatigue",
            scale_version="v4",
        ),
        _timepoint(
            pairing_key=_PAIR_SECONDARY_FACIT,
            observation_id="obs-timepoint-alpha-facit",
            assessment_timepoint="第26周",
            source_text="FACIT-Fatigue 评估时间点：第 26 周。",
            locator=EvidenceLocator(
                document_role="clinical-trial-registry",
                field_path=(
                    "protocolSection.outcomesModule.secondaryOutcomes[1].timeFrame"
                ),
                heading="Secondary Outcome Measures",
                table="Outcome Measures",
                row="Secondary: FACIT-Fatigue",
                column="Time Frame",
                url="https://clinicaltrials.gov/study/NCT02912468#outcomes",
            ),
            display_name="LDH 正常化率",
        ),
        # 跨试验同配对键/同显示名：不得与 alpha 合并或误配时间点。
        _endpoint(
            pairing_key=_PAIR_SIBLING,
            observation_id="obs-endpoint-beta-primary",
            display_name="LDH 正常化",
            definition="Proportion with LDH ≤1.5×ULN at Week 16 (sibling trial)",
            source_text="试验 B：第 16 周 LDH≤1.5×ULN 比例。",
            locator=_LOCATOR_BETA_ENDPOINT,
            product_id="product-eculizumab",
            trial_id="trial-beta",
            cohort_id="cohort-beta",
            group_id="group-experimental",
            source_version_id="registry-version-beta-1",
        ),
        _timepoint(
            pairing_key=_PAIR_SIBLING,
            observation_id="obs-timepoint-beta-primary",
            assessment_timepoint="第16周",
            source_text="试验 B 主要终点评估时间点：第 16 周。",
            locator=_LOCATOR_BETA_TIMEPOINT,
            display_name="LDH 正常化",
            product_id="product-eculizumab",
            trial_id="trial-beta",
            cohort_id="cohort-beta",
            group_id="group-experimental",
            source_version_id="registry-version-beta-1",
        ),
        # 缺时间点配对：不得生成可比较行。
        _endpoint(
            pairing_key="orphan_endpoint_no_timepoint",
            observation_id="obs-endpoint-alpha-orphan",
            display_name="突破性溶血发生率",
            definition="Incidence of breakthrough hemolysis through Week 26",
            source_text="至第 26 周突破性溶血发生率。",
            locator=EvidenceLocator(
                document_role="clinical-trial-registry",
                field_path="protocolSection.outcomesModule.secondaryOutcomes[9].measure",
                heading="Secondary Outcome Measures",
                url="https://clinicaltrials.gov/study/NCT02912468#outcomes",
            ),
        ),
        # 缺定义（仅时间点）：不得生成可比较行。
        _timepoint(
            pairing_key="orphan_timepoint_no_endpoint",
            observation_id="obs-timepoint-alpha-orphan",
            assessment_timepoint="第8周",
            source_text="孤立时间点：第 8 周。",
            locator=EvidenceLocator(
                document_role="clinical-trial-registry",
                field_path="protocolSection.outcomesModule.otherOutcomes[0].timeFrame",
                heading="Other Outcome Measures",
                url="https://clinicaltrials.gov/study/NCT02912468#outcomes",
            ),
        ),
        # 同试验跨组别：同配对键也不得串组合并。
        _endpoint(
            pairing_key=_PAIR_PRIMARY,
            observation_id="obs-endpoint-alpha-group-b",
            display_name="LDH 正常化",
            definition="Group B only: LDH ≤1×ULN at Week 26",
            source_text="组别 B：第 26 周 LDH 正常化比例。",
            locator=EvidenceLocator(
                document_role="clinical-trial-registry",
                field_path="Arms[1].Outcomes[0].measure",
                heading="Arm-Specific Outcomes",
                url="https://clinicaltrials.gov/study/NCT02912468#outcomes",
            ),
            group_id="group-experimental-b",
        ),
        _timepoint(
            pairing_key=_PAIR_PRIMARY,
            observation_id="obs-timepoint-alpha-group-b",
            assessment_timepoint="第26周",
            source_text="组别 B 主要终点评估时间点：第 26 周。",
            locator=EvidenceLocator(
                document_role="clinical-trial-registry",
                field_path="Arms[1].Outcomes[0].timeFrame",
                heading="Arm-Specific Outcomes",
                url="https://clinicaltrials.gov/study/NCT02912468#outcomes",
            ),
            display_name="LDH 正常化",
            group_id="group-experimental-b",
        ),
        # 非终点噪声：不得进入终点投影。
        _observation(
            row_id="design-row-population-noise",
            source_row_id="registry-row-population-noise",
            observation_id="obs-population-noise-alpha",
            field_family=DesignFieldFamily.POPULATION,
            field="target_population",
            source_field_name="目标人群",
            source_field_definition="Adults with PNH",
            source_text="确诊 PNH 成人受试者。",
            assessment_timepoint="筛选期",
            source_locator=EvidenceLocator(
                document_role="clinical-trial-registry",
                field_path="protocolSection.eligibilityModule.eligibilityCriteria",
                heading="Eligibility Criteria",
                url="https://clinicaltrials.gov/study/NCT02912468",
            ),
        ),
    )


_CORPUS = _endpoint_timepoint_corpus()
_CORPUS_BY_ID = {item.observation_id: item for item in _CORPUS}

_EXPECTED_COMPARABLE_PAIRS: tuple[tuple[str, str, str, str, str], ...] = (
    # (endpoint_obs_id, timepoint_obs_id, display_name, definition, timepoint)
    (
        "obs-endpoint-alpha-primary",
        "obs-timepoint-alpha-primary",
        "LDH 正常化",
        "Proportion of subjects with LDH ≤1×ULN at Week 26",
        "第26周",
    ),
    (
        "obs-endpoint-alpha-secondary-ldh",
        "obs-timepoint-alpha-secondary-ldh",
        "LDH 正常化",
        "Change from baseline in LDH at Week 52 (secondary definition)",
        "第52周",
    ),
    (
        "obs-endpoint-alpha-facit",
        "obs-timepoint-alpha-facit",
        "LDH 正常化率",
        "FACIT-Fatigue total score change from baseline at Week 26",
        "第26周",
    ),
    (
        "obs-endpoint-beta-primary",
        "obs-timepoint-beta-primary",
        "LDH 正常化",
        "Proportion with LDH ≤1.5×ULN at Week 16 (sibling trial)",
        "第16周",
    ),
    (
        "obs-endpoint-alpha-group-b",
        "obs-timepoint-alpha-group-b",
        "LDH 正常化",
        "Group B only: LDH ≤1×ULN at Week 26",
        "第26周",
    ),
)


def _project(pages: ModuleType, observations: Sequence[DesignObservation]) -> Any:
    project = getattr(pages, "project_endpoint_definition_timepoint", None)
    if project is None:
        pytest.fail(
            "C 类设计视图缺少 project_endpoint_definition_timepoint",
            pytrace=False,
        )
    return project(tuple(observations))


def _comparable_rows(view: Any) -> tuple[Any, ...]:
    rows = getattr(view, "table_rows", None)
    if rows is None:
        rows = getattr(view, "rows", None)
    if rows is None:
        pytest.fail(
            "终点三元投影视图缺少 table_rows/rows",
            pytrace=False,
        )
    return tuple(rows)


def _ternary(row: Any) -> tuple[str, str, str]:
    display = getattr(row, "endpoint_display_name", None)
    if display is None:
        display = getattr(row, "endpoint_name", None)
    definition = getattr(row, "endpoint_definition", None)
    if definition is None:
        definition = getattr(row, "source_field_definition", None)
    timepoint = getattr(row, "assessment_timepoint", None)
    assert isinstance(display, str) and display.strip()
    assert isinstance(definition, str) and definition.strip()
    assert isinstance(timepoint, str) and timepoint.strip()
    return display, definition, timepoint


def _row_identity(row: Any) -> str:
    identity = getattr(row, "endpoint_identity", None)
    if identity is None:
        identity = getattr(row, "ternary_identity", None)
    if identity is None:
        identity = getattr(row, "comparison_identity", None)
    assert isinstance(identity, str) and identity.strip()
    return identity


def _row_for_endpoint(view: Any, endpoint_observation_id: str) -> Any:
    matches = [
        row
        for row in _comparable_rows(view)
        if getattr(row, "endpoint_observation_id", None) == endpoint_observation_id
    ]
    assert len(matches) == 1, (
        f"期望恰好一行绑定终点观察 {endpoint_observation_id}，实际 {len(matches)}"
    )
    return matches[0]


def _assert_pairing_key(row: Any, expected: str) -> None:
    pairing_key = getattr(row, "pairing_key", None)
    assert pairing_key == expected


def _assert_source_fidelity(
    row: Any,
    *,
    endpoint: DesignObservation,
    timepoint: DesignObservation,
) -> None:
    assert row.endpoint_observation_id == endpoint.observation_id
    assert row.timepoint_observation_id == timepoint.observation_id
    assert row.product_id == endpoint.product_id == timepoint.product_id
    assert row.trial_id == endpoint.trial_id == timepoint.trial_id
    assert row.cohort_id == endpoint.cohort_id == timepoint.cohort_id
    assert row.group_id == endpoint.group_id == timepoint.group_id

    assert row.endpoint_source_text.encode("utf-8") == endpoint.source_text.encode(
        "utf-8"
    )
    assert row.timepoint_source_text.encode("utf-8") == timepoint.source_text.encode(
        "utf-8"
    )
    assert row.endpoint_source_version_id == endpoint.source_version_id
    assert row.timepoint_source_version_id == timepoint.source_version_id
    assert row.endpoint_source_locator == endpoint.source_locator
    assert row.timepoint_source_locator == timepoint.source_locator
    assert row.endpoint_source_locator.model_dump() == endpoint.source_locator.model_dump()
    assert (
        row.timepoint_source_locator.model_dump()
        == timepoint.source_locator.model_dump()
    )

    assert row.endpoint_disclosure_state == endpoint.disclosure_state
    assert row.timepoint_disclosure_state == timepoint.disclosure_state
    assert row.endpoint_review_state == endpoint.review_state
    assert row.timepoint_review_state == timepoint.review_state
    assert row.endpoint_conflict_disposition == endpoint.conflict_disposition
    assert row.timepoint_conflict_disposition == timepoint.conflict_disposition


# ---------------------------------------------------------------------------
# RED cases
# ---------------------------------------------------------------------------


def test_pages_module_exposes_endpoint_definition_timepoint_projector() -> None:
    pages = _pages()
    assert callable(
        getattr(pages, "project_endpoint_definition_timepoint", None)
    ), "需要 project_endpoint_definition_timepoint 投影入口"


def test_comparable_rows_equal_explicitly_paired_endpoint_timepoint_set() -> None:
    """可比较行集合必须等于显式配对成功的终点—时间点集合，禁止手抽或顺序配对。"""

    pages = _pages()
    view = _project(pages, _CORPUS)
    rows = _comparable_rows(view)

    actual_pairs = {
        (
            row.endpoint_observation_id,
            row.timepoint_observation_id,
            *_ternary(row),
        )
        for row in rows
    }
    expected_pairs = set(_EXPECTED_COMPARABLE_PAIRS)
    assert actual_pairs == expected_pairs
    assert len(rows) == len(_EXPECTED_COMPARABLE_PAIRS)

    # 孤儿与噪声不得出现。
    projected_endpoint_ids = {row.endpoint_observation_id for row in rows}
    projected_timepoint_ids = {row.timepoint_observation_id for row in rows}
    assert "obs-endpoint-alpha-orphan" not in projected_endpoint_ids
    assert "obs-timepoint-alpha-orphan" not in projected_timepoint_ids
    assert "obs-population-noise-alpha" not in projected_endpoint_ids


@pytest.mark.parametrize(
    ("endpoint_id", "timepoint_id", "display_name", "definition", "timepoint"),
    _EXPECTED_COMPARABLE_PAIRS,
    ids=[pair[0] for pair in _EXPECTED_COMPARABLE_PAIRS],
)
def test_each_paired_row_keeps_ternary_identity_and_source_fidelity(
    endpoint_id: str,
    timepoint_id: str,
    display_name: str,
    definition: str,
    timepoint: str,
) -> None:
    pages = _pages()
    view = _project(pages, _CORPUS)
    endpoint = _CORPUS_BY_ID[endpoint_id]
    timepoint_obs = _CORPUS_BY_ID[timepoint_id]
    row = _row_for_endpoint(view, endpoint_id)

    assert _ternary(row) == (display_name, definition, timepoint)
    # 时间点必须来自配对的 TIMEPOINT 观察，不得采用终点观察上的噪声时间点。
    assert row.assessment_timepoint == timepoint_obs.assessment_timepoint
    if endpoint.assessment_timepoint not in (None, timepoint_obs.assessment_timepoint):
        assert row.assessment_timepoint != endpoint.assessment_timepoint

    expected_key = endpoint.field[: -len("_definition")]
    assert timepoint_obs.field == f"{expected_key}_timepoint"
    _assert_pairing_key(row, expected_key)
    _assert_source_fidelity(row, endpoint=endpoint, timepoint=timepoint_obs)

    identity = _row_identity(row)
    assert identity  # 稳定三元身份存在且非空


def test_same_display_name_different_definition_or_timepoint_are_not_merged() -> None:
    pages = _pages()
    view = _project(pages, _CORPUS)
    rows = [
        row
        for row in _comparable_rows(view)
        if row.trial_id == "trial-alpha"
        and row.group_id == "group-all-enrolled"
        and _ternary(row)[0] == "LDH 正常化"
    ]
    ternaries = {_ternary(row) for row in rows}
    identities = {_row_identity(row) for row in rows}

    assert len(rows) == 2
    assert len(ternaries) == 2
    assert len(identities) == 2
    assert {
        (
            "LDH 正常化",
            "Proportion of subjects with LDH ≤1×ULN at Week 26",
            "第26周",
        ),
        (
            "LDH 正常化",
            "Change from baseline in LDH at Week 52 (secondary definition)",
            "第52周",
        ),
    } == ternaries


def test_cross_trial_and_cross_group_do_not_mispair_or_merge() -> None:
    pages = _pages()
    view = _project(pages, _CORPUS)

    alpha = _row_for_endpoint(view, "obs-endpoint-alpha-primary")
    beta = _row_for_endpoint(view, "obs-endpoint-beta-primary")
    group_b = _row_for_endpoint(view, "obs-endpoint-alpha-group-b")

    assert alpha.trial_id == "trial-alpha"
    assert beta.trial_id == "trial-beta"
    assert alpha.timepoint_observation_id == "obs-timepoint-alpha-primary"
    assert beta.timepoint_observation_id == "obs-timepoint-beta-primary"
    assert alpha.timepoint_observation_id != beta.timepoint_observation_id
    assert _row_identity(alpha) != _row_identity(beta)
    assert _ternary(alpha) != _ternary(beta)

    assert group_b.group_id == "group-experimental-b"
    assert group_b.timepoint_observation_id == "obs-timepoint-alpha-group-b"
    assert group_b.timepoint_observation_id != alpha.timepoint_observation_id
    assert _row_identity(group_b) != _row_identity(alpha)


def test_positional_order_and_text_similarity_cannot_pair_or_change_identities() -> None:
    """交错顺序与近似显示名不得产生错误配对；重排不改变稳定身份集合。"""

    pages = _pages()
    baseline = _project(pages, _CORPUS)
    baseline_identities = sorted(_row_identity(row) for row in _comparable_rows(baseline))
    baseline_pairs = sorted(
        (row.endpoint_observation_id, row.timepoint_observation_id)
        for row in _comparable_rows(baseline)
    )

    # 故意把“错误邻居”放在一起：endpoint_A, timepoint_B, endpoint_B, timepoint_A…
    adversarial_order: list[DesignObservation] = [
        _CORPUS_BY_ID["obs-endpoint-alpha-primary"],
        _CORPUS_BY_ID["obs-timepoint-alpha-secondary-ldh"],
        _CORPUS_BY_ID["obs-endpoint-alpha-secondary-ldh"],
        _CORPUS_BY_ID["obs-timepoint-alpha-primary"],
        _CORPUS_BY_ID["obs-endpoint-alpha-facit"],
        _CORPUS_BY_ID["obs-timepoint-beta-primary"],
        _CORPUS_BY_ID["obs-endpoint-beta-primary"],
        _CORPUS_BY_ID["obs-timepoint-alpha-facit"],
        _CORPUS_BY_ID["obs-endpoint-alpha-group-b"],
        _CORPUS_BY_ID["obs-timepoint-alpha-group-b"],
        _CORPUS_BY_ID["obs-endpoint-alpha-orphan"],
        _CORPUS_BY_ID["obs-timepoint-alpha-orphan"],
        _CORPUS_BY_ID["obs-population-noise-alpha"],
    ]
    shuffled = _project(pages, tuple(reversed(adversarial_order)))
    shuffled_identities = sorted(_row_identity(row) for row in _comparable_rows(shuffled))
    shuffled_pairs = sorted(
        (row.endpoint_observation_id, row.timepoint_observation_id)
        for row in _comparable_rows(shuffled)
    )

    assert shuffled_identities == baseline_identities
    assert shuffled_pairs == baseline_pairs

    # 近似名“LDH 正常化率”不得吞并“LDH 正常化”。
    facit = _row_for_endpoint(shuffled, "obs-endpoint-alpha-facit")
    primary = _row_for_endpoint(shuffled, "obs-endpoint-alpha-primary")
    assert _ternary(facit)[0] == "LDH 正常化率"
    assert _ternary(primary)[0] == "LDH 正常化"
    assert facit.timepoint_observation_id == "obs-timepoint-alpha-facit"
    assert primary.timepoint_observation_id == "obs-timepoint-alpha-primary"


def test_missing_definition_or_timepoint_partner_yields_no_comparable_row() -> None:
    pages = _pages()
    orphan_endpoint = _CORPUS_BY_ID["obs-endpoint-alpha-orphan"]
    orphan_timepoint = _CORPUS_BY_ID["obs-timepoint-alpha-orphan"]
    view = _project(pages, (orphan_endpoint, orphan_timepoint))
    assert _comparable_rows(view) == ()


def test_chart_and_table_share_endpoint_identities_when_both_present() -> None:
    pages = _pages()
    view = _project(pages, _CORPUS)
    table_ids = {_row_identity(row) for row in _comparable_rows(view)}
    chart_rows = getattr(view, "chart_rows", None)
    if chart_rows is None:
        pytest.fail("终点三元投影视图缺少 chart_rows（需与表同源）", pytrace=False)
    chart_ids = {_row_identity(row) for row in tuple(chart_rows)}
    assert chart_ids == table_ids


def test_projector_revalidates_observations_and_rejects_blank_identity() -> None:
    pages = _pages()
    project = pages.project_endpoint_definition_timepoint
    good_endpoint = _CORPUS_BY_ID["obs-endpoint-alpha-primary"]
    good_timepoint = _CORPUS_BY_ID["obs-timepoint-alpha-primary"]

    blank_trial = good_endpoint.model_dump(mode="python")
    blank_trial["trial_id"] = "   "
    with pytest.raises((ValueError, TypeError)) as exc_info:
        project((blank_trial, good_timepoint.model_dump(mode="python")))
    message = str(exc_info.value)
    assert "试验" in message or "trial" in message.lower()



# ---------------------------------------------------------------------------
# Worker 03 adversarial endpoint audit
# ---------------------------------------------------------------------------


def test_non_unique_pairing_key_in_same_scope_rejects_silent_merge() -> None:
    """同一 product/trial/cohort/group/pairing_key 出现多条终点时必须拒绝静默合并。"""

    pages = _pages()
    project = pages.project_endpoint_definition_timepoint
    first = _CORPUS_BY_ID["obs-endpoint-alpha-primary"]
    timepoint = _CORPUS_BY_ID["obs-timepoint-alpha-primary"]
    second = _endpoint(
        pairing_key=_PAIR_PRIMARY,
        observation_id="obs-endpoint-alpha-primary-dup",
        display_name="LDH 正常化",
        definition="Alternate conflicting definition at Week 26",
        source_text="冲突定义：不得与主终点静默合并。",
        locator=EvidenceLocator(
            document_role="clinical-trial-registry",
            field_path="protocolSection.outcomesModule.primaryOutcomes[9].measure",
            heading="Primary Outcome Measures",
            url="https://clinicaltrials.gov/study/NCT02912468#outcomes",
        ),
    )

    with pytest.raises((ValueError, TypeError)) as exc_info:
        project((first, second, timepoint))
    message = str(exc_info.value)
    assert "不唯一" in message or "合并" in message or "unique" in message.lower()


def test_same_pairing_key_across_cohorts_stays_separate() -> None:
    """同配对键跨队列必须保留独立三元行，不得串队列配对或合并。"""

    pages = _pages()
    alpha_endpoint = _CORPUS_BY_ID["obs-endpoint-alpha-primary"]
    alpha_timepoint = _CORPUS_BY_ID["obs-timepoint-alpha-primary"]
    cohort_b_endpoint = _endpoint(
        pairing_key=_PAIR_PRIMARY,
        observation_id="obs-endpoint-alpha-cohort-b",
        display_name="LDH 正常化",
        definition="Cohort B: LDH ≤1×ULN at Week 26",
        source_text="队列 B：第 26 周 LDH 正常化比例。",
        locator=EvidenceLocator(
            document_role="clinical-trial-registry",
            field_path="Cohorts[1].Outcomes[0].measure",
            heading="Cohort-Specific Outcomes",
            url="https://clinicaltrials.gov/study/NCT02912468#outcomes",
        ),
        cohort_id="cohort-alpha-b",
    )
    cohort_b_timepoint = _timepoint(
        pairing_key=_PAIR_PRIMARY,
        observation_id="obs-timepoint-alpha-cohort-b",
        assessment_timepoint="第26周",
        source_text="队列 B 主要终点评估时间点：第 26 周。",
        locator=EvidenceLocator(
            document_role="clinical-trial-registry",
            field_path="Cohorts[1].Outcomes[0].timeFrame",
            heading="Cohort-Specific Outcomes",
            url="https://clinicaltrials.gov/study/NCT02912468#outcomes",
        ),
        display_name="LDH 正常化",
        cohort_id="cohort-alpha-b",
    )

    view = _project(
        pages,
        (alpha_endpoint, alpha_timepoint, cohort_b_endpoint, cohort_b_timepoint),
    )
    rows = _comparable_rows(view)
    assert len(rows) == 2

    alpha_row = _row_for_endpoint(view, "obs-endpoint-alpha-primary")
    cohort_b_row = _row_for_endpoint(view, "obs-endpoint-alpha-cohort-b")
    assert alpha_row.cohort_id == "cohort-alpha"
    assert cohort_b_row.cohort_id == "cohort-alpha-b"
    assert alpha_row.timepoint_observation_id == "obs-timepoint-alpha-primary"
    assert cohort_b_row.timepoint_observation_id == "obs-timepoint-alpha-cohort-b"
    assert _row_identity(alpha_row) != _row_identity(cohort_b_row)
    assert alpha_row.pairing_key == cohort_b_row.pairing_key == _PAIR_PRIMARY