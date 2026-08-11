from __future__ import annotations

from datetime import datetime
from pathlib import Path


def _evidence_registry(tmp_path: Path, fragment_labels: tuple[str, ...]):
    from ci_workflow.capabilities.extraction_normalization import verify_reopened_fragment
    from ci_workflow.capabilities.lineage_registry import ScientificLineageRegistry
    from ci_workflow.domain.evidence import DateEvidence, EvidenceLocator
    from ci_workflow.storage.content_store import ContentAddressedStore, EvidenceRepository
    from ci_workflow.storage.migrations import apply_migrations

    project_root = tmp_path / "universe-evidence"
    database_path = project_root / "state/project.sqlite"
    apply_migrations(database_path)
    repository = EvidenceRepository(database_path, ContentAddressedStore(project_root))
    locator = EvidenceLocator(document_role="创新属性来源", paragraph="创新属性证据")
    timestamp = datetime.now().astimezone()
    source_version = repository.add_source_version(
        source_id="universe-evidence",
        content="\n".join(
            f"{label} 对应的创新属性原文证据" for label in fragment_labels
        ).encode(),
        media_type="text/plain",
        acquired_at=timestamp,
        published_at=DateEvidence(state="not_applicable", value=None, locator=locator),
        effective_at=DateEvidence(state="not_applicable", value=None, locator=locator),
        first_disclosed_at=DateEvidence(
            state="not_publicly_disclosed", value=None, locator=locator
        ),
    )
    verified = []
    for label in fragment_labels:
        original_text = f"{label} 对应的创新属性原文证据"
        fragment = repository.add_fragment(
            source_version_id=source_version.source_version_id,
            locator=EvidenceLocator(
                document_role="创新属性来源",
                paragraph=original_text,
            ),
            original_text=original_text,
            created_at=timestamp,
        )
        verified.append(
            verify_reopened_fragment(
                fragment,
                reopened_original_text=original_text,
                source_version_id=fragment.source_version_id,
                repository=repository,
            )
        )
    return ScientificLineageRegistry.from_verified_fragments(tuple(verified))


def test_complete_competitor_universe_never_uses_top_n_truncation(
    tmp_path: Path,
) -> None:
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
    registry = _evidence_registry(
        tmp_path, tuple(f"fragment-{item}" for item in range(1, 151))
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
            evidence_fragment_ids=(
                registry.verified_fragments[index - 1].fragment.fragment_id,
            ),
            boundary_reason=None,
            review_receipt=None,
        )
        for index, entity in enumerate(entities, start=1)
    )
    universe = CompetitorUniverse.build(
        entities=entities,
        eligibility=eligible,
        evidence_registry=registry,
    )
    assert universe.universe_closed is True
    assert len(universe.members) == 150
    assert universe.members[-1].entity.entity_id == entities[-1].entity_id
    assert universe.eligibility_audit == eligible


def test_competitor_universe_rejects_duplicate_or_missing_eligibility_records(
    tmp_path: Path,
) -> None:
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
            evidence_fragment_ids=(
                registry.verified_fragments[
                    entities.index(entity)
                ].fragment.fragment_id,
            ),
            boundary_reason=None,
            review_receipt=None,
        )

    registry = _evidence_registry(
        tmp_path, tuple(f"fragment-{entity.entity_id}" for entity in entities)
    )
    first = eligibility_for(entities[0])
    with pytest.raises(ValueError, match="每个实体必须且只能有一条适格记录"):
        CompetitorUniverse.build(
            entities=entities,
            eligibility=(first, first),
            evidence_registry=registry,
        )
    with pytest.raises(ValueError, match="每个实体必须且只能有一条适格记录"):
        CompetitorUniverse.build(
            entities=entities,
            eligibility=(first,),
            evidence_registry=registry,
        )


def test_pending_eligibility_prevents_identity_bound_universe_closure(
    tmp_path: Path,
) -> None:
    import pytest

    from ci_workflow.capabilities.extraction_normalization import (
        VerifiedEvidenceFragment,
    )
    from ci_workflow.capabilities.lineage_registry import ScientificLineageRegistry
    from ci_workflow.capabilities.ontology_universe import ComponentEligibility
    from ci_workflow.domain.entities import EntityIdentity, EntityType
    from ci_workflow.ingestion.identity import CompetitorUniverse

    entity = EntityIdentity.create(EntityType.PRODUCT, "待核验创新药", "project-pending")
    registry = _evidence_registry(tmp_path, ("fragment-pending",))
    verified = registry.verified_fragments[0]
    with pytest.raises(ValueError, match="只能由项目真源库验真后创建"):
        VerifiedEvidenceFragment(
            fragment=verified.fragment,
            reopened_original_text=verified.reopened_original_text,
            source_version=verified.source_version,
        )
    with pytest.raises(ValueError, match="只能由项目真源库验真片段创建"):
        ScientificLineageRegistry(verified_fragments=(verified,))
    pending = ComponentEligibility(
        component_id=entity.entity_id,
        component_name=entity.canonical_name,
        modality="repositioning",
        decision="review_pending",
        rule_id="manual-review",
        rule_version="1.0",
        reason_zh="需要进一步核验创新属性",
        evidence_fragment_ids=(
            registry.verified_fragments[0].fragment.fragment_id,
        ),
        boundary_reason="尚无规则直接覆盖",
        review_receipt=None,
    )
    universe = CompetitorUniverse.build(
        entities=(entity,),
        eligibility=(pending,),
        evidence_registry=registry,
    )
    assert universe.universe_closed is False
    assert universe.members == ()
    assert universe.eligibility_audit == (pending,)
