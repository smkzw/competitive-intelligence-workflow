from __future__ import annotations


def test_complete_competitor_universe_never_uses_top_n_truncation() -> None:
    from ci_workflow.capabilities.ontology_universe import ComponentEligibility
    from ci_workflow.domain.entities import EntityIdentity, EntityType
    from ci_workflow.ingestion.identity import CompetitorUniverse

    entities = tuple(
        EntityIdentity.create(
            entity_type=EntityType.PRODUCT,
            canonical_name=f"创新项目 {index}",
            identity_basis=f"project-{index}",
        )
        for index in range(1, 151)
    )
    eligible = tuple(
        ComponentEligibility(
            component_id=entity.entity_id,
            component_name=entity.canonical_name,
            modality="small_molecule",
            decision="included",
            rule_id="include-small-molecule",
            rule_version="1.0",
            reason_zh="明确纳入",
            evidence_fragment_ids=(f"fragment-{index}",),
            boundary_reason=None,
            review_receipt=None,
        )
        for index, entity in enumerate(entities, start=1)
    )
    universe = CompetitorUniverse.build(entities=entities, eligibility=eligible)
    assert universe.universe_closed is True
    assert len(universe.members) == 150
    assert universe.members[-1].entity.entity_id == entities[-1].entity_id
    assert universe.eligibility_audit == eligible


def test_competitor_universe_rejects_duplicate_or_missing_eligibility_records() -> None:
    import pytest

    from ci_workflow.capabilities.ontology_universe import ComponentEligibility
    from ci_workflow.domain.entities import EntityIdentity, EntityType
    from ci_workflow.ingestion.identity import CompetitorUniverse

    entities = tuple(
        EntityIdentity.create(EntityType.PRODUCT, f"创新药 {index}", f"project-{index}")
        for index in range(1, 3)
    )

    def eligibility_for(entity: EntityIdentity) -> ComponentEligibility:
        return ComponentEligibility(
            component_id=entity.entity_id,
            component_name=entity.canonical_name,
            modality="small_molecule",
            decision="included",
            rule_id="include-small-molecule",
            rule_version="1.0",
            reason_zh="明确纳入",
            evidence_fragment_ids=(f"fragment-{entity.entity_id}",),
            boundary_reason=None,
            review_receipt=None,
        )

    first = eligibility_for(entities[0])
    with pytest.raises(ValueError, match="每个实体必须且只能有一条适格记录"):
        CompetitorUniverse.build(entities=entities, eligibility=(first, first))
    with pytest.raises(ValueError, match="每个实体必须且只能有一条适格记录"):
        CompetitorUniverse.build(entities=entities, eligibility=(first,))


def test_pending_eligibility_prevents_identity_bound_universe_closure() -> None:
    from ci_workflow.capabilities.ontology_universe import ComponentEligibility
    from ci_workflow.domain.entities import EntityIdentity, EntityType
    from ci_workflow.ingestion.identity import CompetitorUniverse

    entity = EntityIdentity.create(EntityType.PRODUCT, "待核验创新药", "project-pending")
    pending = ComponentEligibility(
        component_id=entity.entity_id,
        component_name=entity.canonical_name,
        modality="repositioning",
        decision="review_pending",
        rule_id="manual-review",
        rule_version="1.0",
        reason_zh="需要进一步核验创新属性",
        evidence_fragment_ids=("fragment-pending",),
        boundary_reason="尚无规则直接覆盖",
        review_receipt=None,
    )
    universe = CompetitorUniverse.build(entities=(entity,), eligibility=(pending,))
    assert universe.universe_closed is False
    assert universe.members == ()
    assert universe.eligibility_audit == (pending,)
