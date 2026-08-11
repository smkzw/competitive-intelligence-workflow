from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo


def test_conflicting_values_form_field_level_conflict_set_without_first_value_wins() -> None:  # noqa: E501
    from ci_workflow.capabilities.resolution import build_fact_conflict_set
    from ci_workflow.domain.enums import FactDisclosureState, FactReviewState
    from ci_workflow.domain.facts import AtomicFactVersion

    def fact(*, value: str, version_id: str, fragment_id: str) -> AtomicFactVersion:
        return AtomicFactVersion(
            fact_id="fact-nps-change-treatment-week-24",
            fact_version_id=version_id,
            entity_id="trial-arm-CMS-K10-301-treatment",
            field_id="efficacy.nps.change_from_baseline",
            raw_value=value,
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
            primary_fragment_id=fragment_id,
            source_fragment_ids=(fragment_id,),
            extraction_method="精确字段抽取",
            quality_state="待冲突裁决",
            disclosure_maturity="已公开数值结果",
            source_role="clinical_trial_registry",
            disclosure_state=FactDisclosureState.REPORTED_VALUE,
            review_state=FactReviewState.ACCEPTED,
            normalization=None,
            published_at=datetime(
                2026, 7, 1, 8, 0, tzinfo=ZoneInfo("Asia/Shanghai")
            ),
            effective_at=None,
            created_at=datetime(
                2026, 8, 12, 1, 0, tzinfo=ZoneInfo("Asia/Shanghai")
            ),
        )

    registry_fact = fact(
        value="-2.1",
        version_id="fact-version-registry",
        fragment_id="fragment-registry",
    )
    publication_fact = fact(
        value="-1.9",
        version_id="fact-version-publication",
        fragment_id="fragment-publication",
    )
    conflict = build_fact_conflict_set(
        (registry_fact, publication_fact),
        created_at=datetime(2026, 8, 12, 1, 1, tzinfo=ZoneInfo("Asia/Shanghai")),
    )
    reverse_order = build_fact_conflict_set(
        (publication_fact, registry_fact),
        created_at=datetime(2026, 8, 12, 1, 1, tzinfo=ZoneInfo("Asia/Shanghai")),
    )

    assert conflict.entity_id == registry_fact.entity_id
    assert conflict.field_id == registry_fact.field_id
    assert conflict.context == registry_fact.context
    assert conflict.arm_id == registry_fact.arm_id
    assert conflict.population == registry_fact.population
    assert conflict.timepoint == registry_fact.timepoint
    assert conflict.resolution_state == "open"
    assert conflict.selected_fact_version_id is None
    assert conflict.resolution_note is None
    assert conflict.member_fact_version_ids == (
        "fact-version-publication",
        "fact-version-registry",
    )
    assert conflict.observed_values == ("-1.9", "-2.1")
    assert conflict.conflict_set_id == reverse_order.conflict_set_id
    assert conflict.member_fact_version_ids == reverse_order.member_fact_version_ids
    assert registry_fact.review_state is FactReviewState.ACCEPTED
    assert publication_fact.review_state is FactReviewState.ACCEPTED
    assert registry_fact.supersedes_fact_version_id is None
    assert publication_fact.supersedes_fact_version_id is None
