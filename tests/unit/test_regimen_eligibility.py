from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _ontology() -> object:
    from ci_workflow.capabilities.ontology_universe import InnovationOntology

    return InnovationOntology.from_yaml(
        ROOT / "policies/ontology/innovation-therapy-v1.yaml"
    )


def test_innovative_plus_traditional_background_includes_regimen_without_promoting_background_component(  # noqa: E501
) -> None:
    from ci_workflow.capabilities.ontology_universe import (
        InnovationOntology,
        TherapyComponent,
        TherapyRegimen,
    )

    ontology = _ontology()
    assert isinstance(ontology, InnovationOntology)
    result = ontology.evaluate_regimen(
        TherapyRegimen(
            name="创新单抗联合传统激素背景治疗",
            components=(
                TherapyComponent(
                    name="创新单抗",
                    modality="monoclonal_antibody",
                    evidence_fragment_ids=("fragment-innovative",),
                ),
                TherapyComponent(
                    name="传统激素",
                    modality="traditional_corticosteroid",
                    evidence_fragment_ids=("fragment-background",),
                ),
            ),
        )
    )
    assert result.decision == "included"
    assert result.regimen_count == 1
    assert result.competitor_profile_component_names == ("创新单抗",)
    assert result.innovation_component_count == 1
    assert result.component_results[1].decision == "excluded"
    assert result.component_results[1].component_id not in result.competitor_component_ids


def test_pure_traditional_regimen_is_excluded() -> None:
    from ci_workflow.capabilities.ontology_universe import (
        InnovationOntology,
        TherapyComponent,
        TherapyRegimen,
    )

    ontology = _ontology()
    assert isinstance(ontology, InnovationOntology)
    result = ontology.evaluate_regimen(
        TherapyRegimen(
            name="抗组胺药联合传统激素",
            components=(
                TherapyComponent(
                    name="抗组胺药",
                    modality="antihistamine",
                    evidence_fragment_ids=("fragment-antihistamine",),
                ),
                TherapyComponent(
                    name="传统激素",
                    modality="traditional_corticosteroid",
                    evidence_fragment_ids=("fragment-steroid",),
                ),
            ),
        )
    )
    assert result.decision == "excluded"
    assert result.regimen_count == 0
    assert result.innovation_component_count == 0
    assert result.competitor_component_ids == ()
    assert result.competitor_profile_component_names == ()
