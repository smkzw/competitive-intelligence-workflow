from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


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
) -> None:
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
        pending = ontology.evaluate_component(
            TherapyComponent(
                name=f"边界项目-{modality}",
                modality=modality,
                evidence_fragment_ids=(f"fragment-{modality}",),
            )
        )
        universe = close_competitor_universe((pending,))
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
            evidence_fragment_ids=(f"fragment-{modality}",),
        )
        closed = close_competitor_universe((resolved,))
        assert resolved.decision == "excluded"
        assert resolved.review_receipt is not None
        assert resolved.review_receipt.rule_version == "1.0"
        assert closed.universe_closed is True
        assert closed.allowed_downstream_nodes == ("gate", "snapshot", "render")
        assert closed.audit_records == (resolved,)
