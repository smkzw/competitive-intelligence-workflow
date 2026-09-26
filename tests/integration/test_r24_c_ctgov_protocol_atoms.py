"""C 协议设计原子的固定 CT.gov CAS 精确来源切片测试。"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from ci_workflow.application.ctgov_design_atoms import (
    CtgovProtocolDesignAtoms,
    extract_ctgov_protocol_design_atoms,
)
from ci_workflow.application.source_research_service import (
    ResearchPackageError,
    SourceCapture,
    source_capture_from_ctgov_study,
)
from ci_workflow.domain.evidence import ContentBlob
from ci_workflow.sources.connectors.ctgov_fetch import derive_saved_ctgov_record
from ci_workflow.storage.source_derivation import extract_locator_quote

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CAS_ROOT = _REPO_ROOT / ".artifacts" / "r24-50-source-expansion-20260926" / "project-v2"
_CAS_DIGEST = "5d35c3ce835ebea73cc28e53cc6216773247fb77e0b1053b45eb83036ce6b3be"
_REPLAYED_AT = datetime(2026, 9, 26, tzinfo=UTC)


def _fixed_capture(nct_id: str) -> SourceCapture:
    relative = f"evidence/raw/sha256/{_CAS_DIGEST[:2]}/{_CAS_DIGEST}.bin"
    blob = ContentBlob(
        sha256=_CAS_DIGEST,
        relative_path=relative,
        byte_size=(_CAS_ROOT / relative).stat().st_size,
        media_type="application/json",
    )
    study = derive_saved_ctgov_record(_CAS_ROOT, blob, nct_id, replayed_at=_REPLAYED_AT)
    return source_capture_from_ctgov_study(_CAS_ROOT, study)


def _mutated_capture(nct_id: str, mutate: Callable[[dict[str, Any]], None]) -> SourceCapture:
    source = _fixed_capture(nct_id)
    record: dict[str, Any] = json.loads(source.content_text)
    mutate(record)
    return source.model_copy(update={"content_text": json.dumps(record)})


def _facts_by_path(atoms: CtgovProtocolDesignAtoms) -> dict[str, str]:
    return {fact.locator.field_path or "": fact.raw_value or "" for fact in atoms.facts}


@pytest.mark.parametrize("nct_id", ["NCT02264639", "NCT03829449"])
def test_fixed_capture_emits_exact_reextractable_design_atoms(nct_id: str) -> None:
    source = _fixed_capture(nct_id)
    atoms = extract_ctgov_protocol_design_atoms(source)
    record: dict[str, Any] = json.loads(source.content_text)
    paths = [fact.locator.field_path or "" for fact in atoms.facts]
    assert len(paths) == len(set(paths)), "事实字段路径不得重复"
    assert len({fact.fact_id for fact in atoms.facts}) == len(atoms.facts)
    assert atoms.trial_id == nct_id and atoms.source_id == source.source_id
    for fact in atoms.facts:
        assert fact.raw_value == extract_locator_quote(
            source.content_text, media_type=source.media_type, locator=fact.locator
        )
        assert fact.original_text == (fact.raw_value or "").strip()
        assert fact.normalized_value is None
        assert fact.disclosure_state == "reported_value"
        assert fact.result_context is None
        assert fact.entity_type == "clinical_trial"
        assert fact.canonical_name == nct_id
        assert fact.field_id.startswith("ctgov.protocol.")
        assert fact.row_ref.startswith(f"registry:{nct_id.casefold()}:protocol-design:")
    eligibility = record["protocolSection"]["eligibilityModule"]["eligibilityCriteria"]
    assert (
        _facts_by_path(atoms)["$.protocolSection.eligibilityModule.eligibilityCriteria"]
        == eligibility
    )
    assert _facts_by_path(atoms)["$.protocolSection.eligibilityModule.sex"] == "ALL"
    assert _facts_by_path(atoms)["$.protocolSection.eligibilityModule.healthyVolunteers"] == "false"
    assert _facts_by_path(atoms)["$.protocolSection.designModule.designInfo.allocation"] == (
        "NON_RANDOMIZED" if nct_id == "NCT02264639" else "NA"
    )


def test_nct02264639_emits_complete_protocol_families() -> None:
    source = _fixed_capture("NCT02264639")
    atoms = extract_ctgov_protocol_design_atoms(source)
    values = _facts_by_path(atoms)
    assert len(atoms.facts) == 49
    assert values["$.protocolSection.designModule.phases[0]"] == "PHASE1"
    assert values["$.protocolSection.designModule.enrollmentInfo.count"] == "9"
    assert values["$.protocolSection.designModule.enrollmentInfo.type"] == "ACTUAL"
    assert values["$.protocolSection.designModule.designInfo.maskingInfo.masking"] == "NONE"
    for index, label in enumerate(("Cohort 1", "Cohort 2", "Cohort 3", "Cohort 4")):
        assert values[f"$.protocolSection.armsInterventionsModule.armGroups[{index}].label"] == (
            label
        )
        assert values[f"$.protocolSection.armsInterventionsModule.armGroups[{index}].type"] == (
            "EXPERIMENTAL"
        )
        assert (
            values[
                f"$.protocolSection.armsInterventionsModule.interventions[0].armGroupLabels[{index}]"
            ]
            == label
        )
    assert values["$.protocolSection.armsInterventionsModule.interventions[0].name"] == (
        "Pegcetacoplan"
    )
    assert values["$.protocolSection.armsInterventionsModule.interventions[0].otherNames[0]"] == (
        "APL-2"
    )
    primary_measures = {
        path: text
        for path, text in values.items()
        if ".primaryOutcomes[" in path and path.endswith(".measure")
    }
    assert len(primary_measures) == 4
    record: dict[str, Any] = json.loads(source.content_text)
    for index, outcome in enumerate(record["protocolSection"]["outcomesModule"]["primaryOutcomes"]):
        base = f"$.protocolSection.outcomesModule.primaryOutcomes[{index}]"
        assert values[f"{base}.measure"] == outcome["measure"]
        assert values[f"{base}.timeFrame"] == outcome["timeFrame"]
        assert values[f"{base}.description"] == outcome["description"]
    assert set(atoms.absent_paths) == {
        "$.protocolSection.eligibilityModule.maximumAge",
        "$.protocolSection.designModule.designInfo.interventionModelDescription",
        "$.protocolSection.outcomesModule.secondaryOutcomes",
    }
    assert not any(path.endswith("maximumAge") for path in values)


def test_nct03829449_keeps_single_arm_and_twelve_secondary_endpoints() -> None:
    source = _fixed_capture("NCT03829449")
    atoms = extract_ctgov_protocol_design_atoms(source)
    values = _facts_by_path(atoms)
    assert len(atoms.facts) == 62
    assert values["$.protocolSection.designModule.phases[0]"] == "PHASE3"
    assert values["$.protocolSection.designModule.designInfo.interventionModelDescription"] == (
        "Open-label, non-comparative"
    )
    assert values["$.protocolSection.designModule.enrollmentInfo.count"] == "15"
    assert values["$.protocolSection.armsInterventionsModule.armGroups[0].label"] == (
        "rVA576 Coversin"
    )
    assert values["$.protocolSection.armsInterventionsModule.interventions[0].otherNames[0]"] == (
        "nomacopan"
    )
    record: dict[str, Any] = json.loads(source.content_text)
    secondary = record["protocolSection"]["outcomesModule"]["secondaryOutcomes"]
    assert len(secondary) == 12
    for index, outcome in enumerate(secondary):
        base = f"$.protocolSection.outcomesModule.secondaryOutcomes[{index}]"
        assert values[f"{base}.measure"] == outcome["measure"]
        assert values[f"{base}.timeFrame"] == outcome["timeFrame"]
        assert values[f"{base}.description"] == outcome["description"]
    assert set(atoms.absent_paths) == {"$.protocolSection.eligibilityModule.maximumAge"}


def test_extraction_is_deterministic_and_infers_no_product_or_group_binding() -> None:
    source = _fixed_capture("NCT02264639")
    first = extract_ctgov_protocol_design_atoms(source)
    assert extract_ctgov_protocol_design_atoms(source) == first
    assert all(fact.result_context is None for fact in first.facts)
    assert not any("product" in fact.field_id for fact in first.facts)
    labels = {
        fact.raw_value
        for fact in first.facts
        if fact.field_id == "ctgov.protocol.intervention.arm_group_label"
    }
    arm_labels = {
        fact.raw_value for fact in first.facts if fact.field_id == "ctgov.protocol.arm.label"
    }
    assert labels and labels <= arm_labels


@pytest.mark.parametrize(
    "mutate",
    [
        lambda record: record["protocolSection"]["identificationModule"].update(
            nctId="NCT00000000"
        ),
        lambda record: record["protocolSection"].update(eligibilityModule=[]),
        lambda record: record["protocolSection"]["eligibilityModule"].update(
            eligibilityCriteria=None
        ),
        lambda record: record["protocolSection"]["eligibilityModule"].update(
            eligibilityCriteria="   "
        ),
        lambda record: record["protocolSection"]["eligibilityModule"].update(stdAges="ADULT"),
        lambda record: record["protocolSection"].update(armsInterventionsModule=[]),
        lambda record: record["protocolSection"]["armsInterventionsModule"].update(armGroups={}),
        lambda record: record["protocolSection"]["armsInterventionsModule"]["armGroups"][0].pop(
            "label"
        ),
        lambda record: record["protocolSection"]["armsInterventionsModule"]["armGroups"][1].update(
            label=record["protocolSection"]["armsInterventionsModule"]["armGroups"][0]["label"]
        ),
        lambda record: record["protocolSection"]["armsInterventionsModule"]["interventions"][
            0
        ].update(armGroupLabels=["Ghost Arm"]),
        lambda record: record["protocolSection"]["outcomesModule"].update(primaryOutcomes={}),
        lambda record: record["protocolSection"]["outcomesModule"]["primaryOutcomes"][0].pop(
            "timeFrame"
        ),
        lambda record: record["protocolSection"]["outcomesModule"].update(secondaryOutcomes=0),
    ],
)
def test_malformed_duplicate_or_unknown_relation_fails_closed(
    mutate: Callable[[dict[str, Any]], None],
) -> None:
    source = _mutated_capture("NCT02264639", mutate)
    with pytest.raises(ResearchPackageError):
        extract_ctgov_protocol_design_atoms(source)


def test_absent_optional_fields_are_marked_explicitly_never_as_zero() -> None:
    def strip_optional(record: dict[str, Any]) -> None:
        arms = record["protocolSection"]["armsInterventionsModule"]
        arms["armGroups"][0].pop("description")
        arms["interventions"][0].pop("otherNames")
        record["protocolSection"]["designModule"]["designInfo"].pop("maskingInfo")
        outcomes = record["protocolSection"]["outcomesModule"]
        outcomes["primaryOutcomes"][0].pop("description")

    source = _mutated_capture("NCT02264639", strip_optional)
    atoms = extract_ctgov_protocol_design_atoms(source)
    values = _facts_by_path(atoms)
    assert not any(path.endswith(".otherNames[0]") for path in values)
    assert not any(path.endswith("armGroups[0].description") for path in values)
    assert not any(path.endswith("primaryOutcomes[0].description") for path in values)
    assert not any(path.endswith("maskingInfo.masking") for path in values)
    assert {
        "$.protocolSection.armsInterventionsModule.armGroups[0].description",
        "$.protocolSection.armsInterventionsModule.interventions[0].otherNames",
        "$.protocolSection.designModule.designInfo.maskingInfo.masking",
        "$.protocolSection.outcomesModule.primaryOutcomes[0].description",
        "$.protocolSection.eligibilityModule.maximumAge",
        "$.protocolSection.outcomesModule.secondaryOutcomes",
    } <= set(atoms.absent_paths)
    for fact in atoms.facts:
        assert fact.raw_value == extract_locator_quote(
            source.content_text, media_type=source.media_type, locator=fact.locator
        )
