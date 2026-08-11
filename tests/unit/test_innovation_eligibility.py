from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _evidence_registry(tmp_path: Path, fragment_labels: tuple[str, ...]):
    from ci_workflow.capabilities.extraction_normalization import verify_reopened_fragment
    from ci_workflow.capabilities.lineage_registry import ScientificLineageRegistry
    from ci_workflow.domain.evidence import DateEvidence, EvidenceLocator
    from ci_workflow.storage.content_store import ContentAddressedStore, EvidenceRepository
    from ci_workflow.storage.migrations import apply_migrations

    project_root = tmp_path / "innovation-evidence"
    database_path = project_root / "state/project.sqlite"
    apply_migrations(database_path)
    repository = EvidenceRepository(database_path, ContentAddressedStore(project_root))
    locator = EvidenceLocator(document_role="创新属性来源", paragraph="创新属性证据")
    timestamp = datetime.now().astimezone()
    source_version = repository.add_source_version(
        source_id="innovation-evidence",
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


def test_innovation_modalities_include_adc_and_fusion_protein() -> None:
    from ci_workflow.capabilities.ontology_universe import (
        InnovationOntology,
        TherapyComponent,
    )

    ontology = InnovationOntology.from_yaml(
        ROOT / "policies/ontology/innovation-therapy-v1.yaml"
    )
    for modality in (
        "monoclonal_antibody",
        "multispecific_antibody",
        "small_molecule",
        "protac",
        "sirna",
        "adc",
        "fusion_protein",
    ):
        result = ontology.evaluate_component(
            TherapyComponent(
                name=f"测试项目-{modality}",
                modality=modality,
                evidence_fragment_ids=(f"fragment-{modality}",),
            )
        )
        assert result.decision == "included"
        assert result.rule_version == "1.0"
        assert result.rule_id != "other"
        assert result.evidence_fragment_ids == (f"fragment-{modality}",)


def test_unmatched_reformulation_repositioning_or_fixed_combination_stays_review_pending(
    tmp_path: Path,
) -> None:
    from ci_workflow.capabilities.lineage_registry import ScientificLineageRegistry
    from ci_workflow.capabilities.ontology_universe import (
        InnovationOntology,
        TherapyComponent,
        close_competitor_universe,
    )

    ontology = InnovationOntology.from_yaml(
        ROOT / "policies/ontology/innovation-therapy-v1.yaml"
    )
    for modality in (
        "reformulation",
        "repositioning",
        "fixed_combination",
        "unknown_boundary",
    ):
        evidence_registry = _evidence_registry(
            tmp_path, (f"fragment-{modality}",)
        )
        verified_fragment_id = (
            evidence_registry.verified_fragments[0].fragment.fragment_id
        )
        pending = ontology.evaluate_component(
            TherapyComponent(
                name=f"边界项目-{modality}",
                modality=modality,
                evidence_fragment_ids=(verified_fragment_id,),
            )
        )
        universe = close_competitor_universe(
            (pending,),
            evidence_registry=evidence_registry,
        )
        assert pending.decision == "review_pending"
        assert pending.boundary_reason
        assert pending.review_receipt is None
        assert universe.universe_closed is False
        assert universe.allowed_downstream_nodes == ()

        resolved = ontology.review_boundary(
            pending,
            decision="excluded",
            reviewer_id="independent-reviewer-001",
            rationale="未证明相对现有产品具有创新药属性",
            evidence_fragment_ids=(verified_fragment_id,),
        )
        closed = close_competitor_universe(
            (resolved,),
            evidence_registry=evidence_registry,
        )
        assert resolved.decision == "excluded"
        assert resolved.review_receipt is not None
        assert resolved.review_receipt.rule_version == "1.0"
        assert closed.universe_closed is True
        assert closed.allowed_downstream_nodes == ("gate", "snapshot", "render")
        assert closed.audit_records == (resolved,)

        with pytest.raises(ValueError, match="尚未登记并重开"):
            close_competitor_universe(
                (resolved,),
                evidence_registry=ScientificLineageRegistry.empty(),
            )
        review_with_unregistered_fragment = ontology.review_boundary(
            pending,
            decision="excluded",
            reviewer_id="independent-reviewer-002",
            rationale="边界证据不足，暂不纳入创新药竞品宇宙",
            evidence_fragment_ids=(f"review-fragment-{modality}",),
        )
        with pytest.raises(ValueError, match="边界审查引用了尚未登记并重开"):
            close_competitor_universe(
                (review_with_unregistered_fragment,),
                evidence_registry=evidence_registry,
            )
