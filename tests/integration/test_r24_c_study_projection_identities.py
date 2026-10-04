"""C study-only projection identities: explicit None products without known-ID drift."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import ValidationError

from ci_workflow.domain.enums import FactDisclosureState, FactReviewState
from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.gates.models import ConflictDisposition, DisclosureMaturity, SourceRole
from ci_workflow.reports.c import design, pages
from ci_workflow.reports.c.contracts import DesignFieldFamily, DesignObservation
from ci_workflow.reports.c.endpoint_instances import (
    EndpointInstanceError,
    validate_endpoint_timepoint_pairs,
)
from ci_workflow.reports.c.pages import (
    DesignFactRow,
    EndpointDefinitionTimepointRow,
    project_design_map,
    project_endpoint_definition_timepoint,
)

_INDICATION = "indication-pnh"
_LOCATOR = EvidenceLocator(
    document_role="clinical-trial-registry",
    field_path="protocolSection.eligibilityModule.eligibilityCriteria",
    heading="Eligibility Criteria",
    url="https://clinicaltrials.gov/study/NCT02912468",
)

# Frozen known-product identity anchors captured before this repair.
_KNOWN_DRILLDOWN_ID = "c-eligibility-drilldown_64c6e9e277c176dec69b8020"
_KNOWN_FACT_ID = "c-design-fact_f2b10414509442ffc161fbb5"
_KNOWN_ENDPOINT_ID = "c-endpoint-ternary_a66d58fb312134d618cd67f0"


def _observation(**overrides: object) -> DesignObservation:
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "row_id": "design-row-study",
        "source_row_id": "registry-row-study",
        "observation_id": "o1",
        "product_id": "product-ravulizumab",
        "trial_id": "trial-alpha",
        "cohort_id": "cohort-alpha",
        "group_id": "group-all",
        "field_family": DesignFieldFamily.POPULATION,
        "field": "inclusion_criterion",
        "source_field_name": "Inclusion",
        "source_field_definition": "def",
        "source_text": "text-原文",
        "source_version_id": "sv1",
        "source_locator": _LOCATOR,
        "source_role": SourceRole.CLINICAL_TRIAL_REGISTRY,
        "disclosure_maturity": DisclosureMaturity.REGISTRY_RESULT_OR_PRIMARY_REPORT,
        "review_state": FactReviewState.ACCEPTED,
        "disclosure_state": FactDisclosureState.REPORTED_VALUE,
        "conflict_disposition": ConflictDisposition.RESOLVED_SELECTED_ACCEPTED_FACT,
        "compatibility_rule": "c-eligibility-v1",
    }
    payload.update(overrides)
    return DesignObservation.model_validate(payload)


def _endpoint_pair(
    *,
    product_id: str | None,
    observation_prefix: str,
    trial_id: str = "trial-alpha",
) -> tuple[DesignObservation, DesignObservation]:
    endpoint = _observation(
        observation_id=f"{observation_prefix}-endpoint",
        row_id=f"row-{observation_prefix}-endpoint",
        source_row_id=f"src-{observation_prefix}-endpoint",
        product_id=product_id,
        trial_id=trial_id,
        field_family=DesignFieldFamily.ENDPOINT,
        field="primary_endpoint_definition",
        source_field_name="LDH",
        source_field_definition="Proportion LDH",
        source_text="终点原文",
        endpoint_key="primary",
        outcome_id=f"outcome-{observation_prefix}",
        period="P1",
        compatibility_rule="c-design-v1",
    )
    timepoint = _observation(
        observation_id=f"{observation_prefix}-timepoint",
        row_id=f"row-{observation_prefix}-timepoint",
        source_row_id=f"src-{observation_prefix}-timepoint",
        product_id=product_id,
        trial_id=trial_id,
        field_family=DesignFieldFamily.TIMEPOINT,
        field="primary_endpoint_timepoint",
        source_field_name="LDH 时间点",
        source_field_definition="评估时间点",
        source_text="时间点原文",
        assessment_timepoint="Week 26",
        endpoint_key="primary",
        outcome_id=f"outcome-{observation_prefix}",
        period="P1",
        compatibility_rule="c-design-v1",
    )
    return endpoint, timepoint


def _instance_obs(
    row_id: str,
    *,
    family: str,
    product_id: Any = "P1",
    include_product: bool = True,
    text: str = "measure",
    trial: str = "T1",
    outcome: str = "O1",
) -> SimpleNamespace:
    payload: dict[str, Any] = {
        "row_id": row_id,
        "trial_id": trial,
        "outcome_id": outcome,
        "field_family": family,
        "endpoint_key": "primary",
        "group_id": "G1",
        "cohort_id": "C1",
        "period": "P1",
        "assessment_timepoint": "W12",
        "source_text": text,
        "source_version_id": "sv1",
        "source_locator": None,
        "source_role": "",
    }
    if include_product:
        payload["product_id"] = product_id
    return SimpleNamespace(**payload)


def test_known_product_identity_algorithms_unchanged() -> None:
    known = _observation()
    assert design._drilldown_chain_id(_INDICATION, known) == _KNOWN_DRILLDOWN_ID
    assert pages._fact_row_identity(known) == _KNOWN_FACT_ID
    endpoint = known.model_copy(
        update={
            "field_family": DesignFieldFamily.ENDPOINT,
            "field": "primary_endpoint_definition",
            "observation_id": "oe1",
            "source_field_name": "LDH",
            "source_field_definition": "Proportion LDH",
            "endpoint_key": "primary",
            "outcome_id": "outcome-1",
            "period": "P1",
            "compatibility_rule": "c-eligibility-v1",
        }
    )
    assert (
        pages._endpoint_identity(
            endpoint=endpoint,
            pairing_key="primary_endpoint",
            display_name="LDH",
            definition="Proportion LDH",
            assessment_timepoint="Week 26",
        )
        == _KNOWN_ENDPOINT_ID
    )


def test_pure_none_eligibility_and_design_map_retain_rows_and_study_namespace() -> None:
    none_obs = _observation(product_id=None, observation_id="o-none", source_text="纯研究原文")
    drill = design.project_eligibility_drilldown((none_obs,), indication_id=_INDICATION)
    assert len(drill.table_rows) == 1
    row = drill.table_rows[0]
    assert row.product_id is None
    assert row.source_text == "纯研究原文"
    assert row.source_locator == _LOCATOR
    assert row.drilldown_chain_id.startswith("c-eligibility-drilldown-study_")
    assert row.drilldown_chain_id in drill.evidence_by_chain_id
    assert drill.evidence_by_chain_id[row.drilldown_chain_id].source_text == "纯研究原文"

    mapped = project_design_map((none_obs,))
    assert len(mapped.table_rows) == 1
    fact = mapped.table_rows[0]
    assert fact.product_id is None
    assert fact.source_text == "纯研究原文"
    assert fact.source_locator == _LOCATOR
    assert fact.row_identity.startswith("c-design-fact-study_")


def test_mixed_none_known_reorder_sort_stable_and_retains_all_rows() -> None:
    known = _observation(
        product_id="product-ravulizumab",
        observation_id="o-known",
        trial_id="trial-known",
        source_text="已知产品原文",
    )
    unknown = _observation(
        product_id=None,
        observation_id="o-unknown",
        trial_id="trial-unknown",
        source_text="未知关联原文",
    )
    forward = project_design_map((known, unknown))
    reverse = project_design_map((unknown, known))
    assert [row.observation_id for row in forward.table_rows] == [
        row.observation_id for row in reverse.table_rows
    ]
    assert {row.product_id for row in forward.table_rows} == {None, "product-ravulizumab"}
    assert {row.source_text for row in forward.table_rows} == {"已知产品原文", "未知关联原文"}
    assert all(
        (
            row.row_identity.startswith("c-design-fact_")
            if row.product_id is not None
            else row.row_identity.startswith("c-design-fact-study_")
        )
        for row in forward.table_rows
    )
    # known nonempty path must remain on the original namespace prefix
    known_row = next(row for row in forward.table_rows if row.product_id == "product-ravulizumab")
    assert known_row.row_identity.startswith("c-design-fact_")
    assert not known_row.row_identity.startswith("c-design-fact-study_")


def test_endpoint_projection_pairs_none_with_none_and_rejects_none_known_mix() -> None:
    none_endpoint, none_timepoint = _endpoint_pair(
        product_id=None, observation_prefix="study"
    )
    view = project_endpoint_definition_timepoint((none_endpoint, none_timepoint))
    assert len(view.table_rows) == 1
    row = view.table_rows[0]
    assert row.product_id is None
    assert row.endpoint_source_text == "终点原文"
    assert row.timepoint_source_text == "时间点原文"
    assert row.endpoint_identity.startswith("c-endpoint-ternary-study_")

    known_endpoint, _known_timepoint = _endpoint_pair(
        product_id="product-ravulizumab", observation_prefix="known"
    )
    # Same trial/cohort/group/pairing but product None vs known must not pair.
    mixed = project_endpoint_definition_timepoint((none_endpoint, _known_timepoint))
    assert mixed.table_rows == ()

    # Explicit cross-product mismatch on same study axes still yields no silent pair.
    crossed = project_endpoint_definition_timepoint((known_endpoint, none_timepoint))
    assert crossed.table_rows == ()


def test_endpoint_instance_none_distinct_from_missing_empty_and_known() -> None:
    none_endpoint = _instance_obs("e1", family="endpoint", product_id=None)
    none_timepoint = _instance_obs(
        "t1", family="timepoint", product_id=None, text="Week 12"
    )
    instances = validate_endpoint_timepoint_pairs(
        [none_endpoint, none_timepoint], universe_trial_ids={"T1"}
    )
    assert len(instances) == 1
    assert instances[0].product_id is None

    known_timepoint = _instance_obs(
        "t2", family="timepoint", product_id="P1", text="Week 12"
    )
    with pytest.raises(EndpointInstanceError):
        validate_endpoint_timepoint_pairs(
            [none_endpoint, known_timepoint], universe_trial_ids={"T1"}
        )

    missing_endpoint = _instance_obs("e-miss", family="endpoint", include_product=False)
    missing_timepoint = _instance_obs(
        "t-miss", family="timepoint", include_product=False, text="Week 12"
    )
    with pytest.raises(EndpointInstanceError, match="product_id"):
        validate_endpoint_timepoint_pairs(
            [missing_endpoint, missing_timepoint], universe_trial_ids={"T1"}
        )

    empty_endpoint = _instance_obs("e-empty", family="endpoint", product_id="")
    empty_timepoint = _instance_obs(
        "t-empty", family="timepoint", product_id="", text="Week 12"
    )
    with pytest.raises(EndpointInstanceError, match="product_id"):
        validate_endpoint_timepoint_pairs(
            [empty_endpoint, empty_timepoint], universe_trial_ids={"T1"}
        )

    spaced_endpoint = _instance_obs("e-space", family="endpoint", product_id=" ")
    spaced_timepoint = _instance_obs(
        "t-space", family="timepoint", product_id=" ", text="Week 12"
    )
    with pytest.raises(EndpointInstanceError, match="product_id"):
        validate_endpoint_timepoint_pairs(
            [spaced_endpoint, spaced_timepoint], universe_trial_ids={"T1"}
        )


def test_projection_models_reject_empty_or_missing_product_but_allow_explicit_none() -> None:
    locator = _LOCATOR
    common = dict(
        indication_id=_INDICATION,
        trial_id="trial-alpha",
        cohort_id="cohort-alpha",
        group_id="group-all",
        design_element="inclusion_criterion",
        source_field_name="Inclusion",
        source_text="原文",
        scale=None,
        scale_version=None,
        scale_applicability=design.FieldApplicability.NOT_APPLICABLE,
        scale_applicability_predicate_id="pred-scale",
        assessment_timepoint=None,
        operator=None,
        threshold_value=None,
        threshold_unit=None,
        operator_threshold_applicability=design.FieldApplicability.NOT_APPLICABLE,
        operator_threshold_applicability_predicate_id="pred-threshold",
        source_version_id="sv1",
        source_locator=locator,
        observation_id="o-model",
        drilldown_chain_id="c-eligibility-drilldown-study_deadbeefdeadbeefdeadbeef",
    )
    assert design.EligibilityDrilldownRow(product_id=None, **common).product_id is None
    with pytest.raises(ValidationError):
        design.EligibilityDrilldownRow(product_id="", **common)
    with pytest.raises(ValidationError):
        design.EligibilityDrilldownRow(product_id=" ", **common)
    with pytest.raises(ValidationError):
        design.EligibilityDrilldownRow(**common)  # missing product_id

    fact_common = dict(
        schema_version="1.0",
        row_identity="c-design-fact-study_deadbeefdeadbeefdeadbeef",
        row_id="r1",
        source_row_id="s1",
        observation_id="o1",
        trial_id="trial-alpha",
        cohort_id="cohort-alpha",
        group_id="group-all",
        field_family=DesignFieldFamily.POPULATION,
        field="inclusion_criterion",
        source_field_name="Inclusion",
        source_field_definition="def",
        source_text="原文",
        source_version_id="sv1",
        source_locator=locator,
        source_role=SourceRole.CLINICAL_TRIAL_REGISTRY,
        disclosure_maturity=DisclosureMaturity.REGISTRY_RESULT_OR_PRIMARY_REPORT,
        disclosure_state=FactDisclosureState.REPORTED_VALUE,
        review_state=FactReviewState.ACCEPTED,
        conflict_disposition=ConflictDisposition.RESOLVED_SELECTED_ACCEPTED_FACT,
        compatibility_rule="c-design-v1",
    )
    assert DesignFactRow(product_id=None, **fact_common).product_id is None
    with pytest.raises(ValidationError):
        DesignFactRow(product_id="", **fact_common)
    with pytest.raises(ValidationError):
        DesignFactRow(**fact_common)

    endpoint_common = dict(
        endpoint_identity="c-endpoint-ternary-study_deadbeefdeadbeefdeadbeef",
        pairing_key="primary_endpoint",
        trial_id="trial-alpha",
        cohort_id="cohort-alpha",
        group_id="group-all",
        endpoint_display_name="LDH",
        endpoint_definition="Proportion LDH",
        assessment_timepoint="Week 26",
        endpoint_observation_id="oe",
        timepoint_observation_id="ot",
        endpoint_source_text="终点原文",
        timepoint_source_text="时间点原文",
        endpoint_source_version_id="sv1",
        timepoint_source_version_id="sv1",
        endpoint_source_locator=locator,
        timepoint_source_locator=locator,
        endpoint_disclosure_state=FactDisclosureState.REPORTED_VALUE,
        timepoint_disclosure_state=FactDisclosureState.REPORTED_VALUE,
        endpoint_review_state=FactReviewState.ACCEPTED,
        timepoint_review_state=FactReviewState.ACCEPTED,
        endpoint_conflict_disposition=ConflictDisposition.RESOLVED_SELECTED_ACCEPTED_FACT,
        timepoint_conflict_disposition=ConflictDisposition.RESOLVED_SELECTED_ACCEPTED_FACT,
        endpoint_field="primary_endpoint_definition",
        timepoint_field="primary_endpoint_timepoint",
    )
    assert EndpointDefinitionTimepointRow(product_id=None, **endpoint_common).product_id is None
    with pytest.raises(ValidationError):
        EndpointDefinitionTimepointRow(product_id="", **endpoint_common)
    with pytest.raises(ValidationError):
        EndpointDefinitionTimepointRow(**endpoint_common)
