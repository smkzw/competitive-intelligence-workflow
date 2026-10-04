"""R24-64 固定 CT.gov C 协议原子到既有设计观察的生产投影合同测试。

覆盖：两研究固定 CAS 正向投影（身份、来源字节、定位与引文逐条复核）、原子族
映射完整性与未支持清单、缺席/空协议路径缺口、未知组别不猜测、复用身份与损坏
定位负例、终点逐实例配对、资格入选/排除段落的确定性派生（精确连续子串、完整
条款、嵌套项目符号与 AND/OR、标题缺失/重复/空段显式未决、来源字节漂移）以及
既有 C 消费投影（含入选/排除两页）的可达性。投影输出一律为 ``candidate``：
本层不签发 accepted，也不切换 current。
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from ci_workflow.application.ctgov_c_design_projection import (
    ELIGIBILITY_SECTION_COMPATIBILITY_RULE,
    CtgovCArmBinding,
    CtgovCDesignProjection,
    CtgovCDesignProjectionError,
    CtgovCEligibilitySectionKind,
    CtgovCEligibilitySectionReason,
    CtgovCTrialBinding,
    CtgovCUnresolvedReason,
    CtgovCUnsupportedReason,
    project_ctgov_c_design_observations,
)
from ci_workflow.application.ctgov_design_atoms import (
    CtgovProtocolDesignAtoms,
    extract_ctgov_protocol_design_atoms,
)
from ci_workflow.application.source_research_service import (
    SourceCapture,
    source_capture_from_ctgov_study,
)
from ci_workflow.domain.enums import FactDisclosureState, FactReviewState
from ci_workflow.domain.evidence import ContentBlob, EvidenceLocator
from ci_workflow.gates.models import ConflictDisposition, DisclosureMaturity, SourceRole
from ci_workflow.reports.c import (
    DesignFieldFamily,
    DesignGateDecision,
    DesignObservation,
    evaluate_design_gate,
    project_design_map,
    project_endpoint_definition_timepoint,
    project_exclusion_view,
    project_inclusion_view,
    project_population_view,
    project_trial_dossier,
    validate_design_observation,
)
from ci_workflow.reports.c.eligibility_source import extract_eligibility_sections
from ci_workflow.reports.c.endpoint_instances import (
    EndpointInstanceError,
    build_endpoint_instances,
    validate_endpoint_timepoint_pairs,
)
from ci_workflow.sources.connectors.ctgov_fetch import derive_saved_ctgov_record
from ci_workflow.storage.source_derivation import extract_locator_quote

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CAS_ROOT = _REPO_ROOT / "tests" / "fixtures" / "ctgov-c-source"
_CAS_DIGEST = "5d35c3ce835ebea73cc28e53cc6216773247fb77e0b1053b45eb83036ce6b3be"
_REPLAYED_AT = datetime(2026, 9, 26, tzinfo=UTC)
_INDICATION_ID = "pnh"

# 每个固定研究在父级资格全文观察之外各派生一条入选与一条排除段观察。
_EXPECTED_STUDY_OBSERVATIONS = {
    "NCT02264639": 34,
    "NCT03829449": 51,
}
_ELIGIBILITY_SECTION_FIELDS = frozenset({"inclusion_criterion", "exclusion_criterion"})


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


def _study(nct_id: str) -> tuple[SourceCapture, CtgovProtocolDesignAtoms]:
    capture = _fixed_capture(nct_id)
    return capture, extract_ctgov_protocol_design_atoms(capture)


def _full_bindings() -> tuple[CtgovCTrialBinding, ...]:
    return (
        CtgovCTrialBinding(
            trial_id="nct02264639",
            product_id="pegcetacoplan",
            arms=tuple(
                CtgovCArmBinding(
                    label=f"Cohort {index}",
                    group_id=f"group-nct02264639-cohort-{index}",
                    role="experimental_arm",
                )
                for index in (1, 2, 3, 4)
            ),
        ),
        CtgovCTrialBinding(
            trial_id="nct03829449",
            product_id="nomacopan",
            arms=(
                CtgovCArmBinding(
                    label="rVA576 Coversin",
                    group_id="group-nct03829449-coversin",
                    role="experimental_arm",
                ),
            ),
        ),
    )


def _project(
    studies: tuple[tuple[SourceCapture, CtgovProtocolDesignAtoms], ...],
    bindings: tuple[CtgovCTrialBinding, ...],
) -> CtgovCDesignProjection:
    return project_ctgov_c_design_observations(
        tuple(atoms for _, atoms in studies),
        captures={capture.source_id: capture for capture, _ in studies},
        bindings=bindings,
        indication_id=_INDICATION_ID,
    )


def _project_fixed(
    *nct_ids: str,
    bindings: tuple[CtgovCTrialBinding, ...] | None = None,
) -> CtgovCDesignProjection:
    return _project(
        tuple(_study(nct_id) for nct_id in nct_ids),
        _full_bindings() if bindings is None else bindings,
    )


def _rows(projection: CtgovCDesignProjection, trial_id: str) -> tuple[DesignObservation, ...]:
    return tuple(item for item in projection.observations if item.trial_id == trial_id)


def test_extension_population_sentence_is_not_a_dose_regimen() -> None:
    projection = _project_fixed("NCT02264639", "NCT03829449")
    doses = [row for row in projection.observations if row.field == "dosing_regimen"]
    assert len(doses) == 4
    assert {row.trial_id for row in doses} == {"nct02264639"}
    assert any(row.path == "$.protocolSection.armsInterventionsModule.armGroups[0].description"
               and row.trial_id == "NCT03829449" for row in projection.unresolved_atoms)


@pytest.mark.parametrize("nct_id,count", [("NCT02264639", "9"), ("NCT03829449", "15")])
def test_registry_sample_size_keeps_actual_token_without_altering_quote(
    nct_id: str, count: str,
) -> None:
    projection = _project_fixed(nct_id)
    row = next(item for item in projection.observations
               if item.field == "planned_or_actual_sample_size")
    assert row.source_text == count
    assert "ACTUAL" in (row.display_text or "")
    assert "实际" in (row.display_text or "")


def test_registry_version_dates_resolve_to_posted_day_not_identifier() -> None:
    capture = _fixed_capture("NCT03829449")
    for role in ("published_at", "first_disclosed_at"):
        evidence = capture.date_evidence(role)
        assert evidence.locator is not None
        quote = extract_locator_quote(capture.content_text, media_type=capture.media_type,
                                      locator=evidence.locator)
        assert evidence.value is not None
        assert quote == evidence.value.date().isoformat() == "2025-04-10"


def test_registry_protocol_pair_keeps_period_unknown_with_exact_source_proof() -> None:
    projection = _project_fixed("NCT02264639", "NCT03829449")
    captures = tuple(_fixed_capture(nct) for nct in ("NCT02264639", "NCT03829449"))
    instances = validate_endpoint_timepoint_pairs(
        projection.observations,
        universe_trial_ids={"nct02264639", "nct03829449"},
        protocol_sources={source.source_id: source.content_text for source in captures},
    )
    assert len(instances) == 17
    assert all(item.period is None for item in instances)
    assert all(item.timepoint for item in instances)
    assert {item.source_version_id for item in instances} == {
        source.source_id for source in captures
    }


@pytest.mark.parametrize("changed", ["quote", "path", "source", "window", "role", "url"])
def test_registry_unknown_period_requires_exact_instance_proof(changed: str) -> None:
    projection = _project_fixed("NCT02264639")
    rows = list(projection.observations)
    index = next(
        i for i, item in enumerate(rows) if item.field_family is DesignFieldFamily.TIMEPOINT
    )
    row = rows[index]
    changes: dict[str, Any] = {
        "quote": {"source_text": "Week 999"},
        "path": {"source_locator": row.source_locator.model_copy(update={
            "field_path": "$.protocolSection.outcomesModule.secondaryOutcomes[999].timeFrame"
        })},
        "source": {"source_version_id": "another-source-version"},
        "window": {"assessment_timepoint": "Week 999"},
        "role": {"endpoint_key": "secondary_endpoint"},
        "url": {"source_locator": row.source_locator.model_copy(update={
            "url": "https://clinicaltrials.gov/study/NCT03829449"
        })},
    }
    rows[index] = row.model_copy(update=changes[changed])
    capture = _fixed_capture("NCT02264639")
    with pytest.raises(EndpointInstanceError):
        validate_endpoint_timepoint_pairs(
            rows,
            universe_trial_ids={"nct02264639"},
            protocol_sources={capture.source_id: capture.content_text},
        )


def test_registry_unknown_period_does_not_pass_without_source_bytes() -> None:
    projection = _project_fixed("NCT02264639")
    with pytest.raises(EndpointInstanceError, match="period"):
        validate_endpoint_timepoint_pairs(projection.observations)


def _parent_criteria_row(projection: CtgovCDesignProjection, trial_id: str) -> DesignObservation:
    return next(
        item
        for item in _rows(projection, trial_id)
        if item.field == "target_population" and item.source_field_name == "eligibilityCriteria"
    )


def _section_row(
    projection: CtgovCDesignProjection, trial_id: str, field: str
) -> DesignObservation:
    return next(item for item in _rows(projection, trial_id) if item.field == field)


def _expected_sections(nct_id: str) -> tuple[str, str]:
    """既有 C 分段器的确定性结果；固定来源上必须与本层派生一致。"""

    return extract_eligibility_sections(json.loads(_fixed_capture(nct_id).content_text))


def _mutated_study(
    nct_id: str, mutate: Callable[[dict[str, Any]], None]
) -> tuple[SourceCapture, CtgovProtocolDesignAtoms]:
    capture = _mutated_capture(nct_id, mutate)
    return capture, extract_ctgov_protocol_design_atoms(capture)


@pytest.mark.parametrize("nct_id", sorted(_EXPECTED_STUDY_OBSERVATIONS))
def test_fixed_study_projection_preserves_identity_and_source_bytes(nct_id: str) -> None:
    capture, atoms = _study(nct_id)
    projection = _project(((capture, atoms),), _full_bindings())
    trial_id = nct_id.lower()
    rows = _rows(projection, trial_id)
    assert len(rows) == _EXPECTED_STUDY_OBSERVATIONS[nct_id]
    facts = {fact.fact_id: fact for fact in atoms.facts}
    assert {item.source_row_id for item in rows} <= set(facts)
    for observation in rows:
        assert observation.product_id == (
            "pegcetacoplan" if nct_id == "NCT02264639" else "nomacopan"
        )
        assert observation.trial_id == trial_id
        assert observation.review_state is FactReviewState.CANDIDATE
        assert observation.disclosure_state is FactDisclosureState.REPORTED_VALUE
        assert (
            observation.conflict_disposition is ConflictDisposition.RESOLVED_SELECTED_ACCEPTED_FACT
        )
        assert (
            observation.disclosure_maturity is DisclosureMaturity.REGISTRY_RESULT_OR_PRIMARY_REPORT
        )
        assert observation.source_role is SourceRole.CLINICAL_TRIAL_REGISTRY
        # 现行 C 研究包合同按来源实例识别；投影原样保留已验证采集的来源标识。
        assert observation.source_version_id == capture.source_id
        assert observation.source_locator.document_role == "clinical_trial_registry"
        assert (observation.source_locator.field_path or "").startswith("$.protocolSection")
        assert observation.source_locator.url == capture.url
        parent_quote = facts[observation.source_row_id].raw_value
        if observation.field in _ELIGIBILITY_SECTION_FIELDS:
            # 派生段落是父级标量的确定性显示子串：定位仍指向完整资格标量，
            # 不是更窄的引文定位，因此按连续子串与派生规则校验。
            assert observation.source_text in parent_quote
            assert observation.source_text != parent_quote
            assert observation.compatibility_rule == ELIGIBILITY_SECTION_COMPATIBILITY_RULE
            assert observation.source_locator == facts[observation.source_row_id].locator
        else:
            assert observation.source_text == parent_quote
            assert observation.source_text == extract_locator_quote(
                capture.content_text,
                media_type=capture.media_type,
                locator=observation.source_locator,
            )
        assert validate_design_observation(observation) == observation
    assert len({item.row_id for item in rows}) == len(rows)
    assert projection.indication_id == _INDICATION_ID


def test_projection_reports_per_family_completeness_and_unsupported_ids() -> None:
    projection = _project_fixed("NCT02264639", "NCT03829449")
    counts = {
        report.family: (
            report.atom_count,
            report.mapped_count,
            report.unsupported_count,
            report.unresolved_count,
        )
        for report in projection.atom_families
    }
    assert counts == {
        "eligibility": (10, 4, 6, 0),
        "trial-design": (17, 12, 5, 0),
        "arms": (20, 14, 5, 1),
        "interventions": (13, 0, 13, 0),
        "primary-endpoints": (15, 15, 0, 0),
        "secondary-endpoints": (36, 36, 0, 0),
    }
    assert sum(item[0] for item in counts.values()) == 111
    # 81 条原子观察 + 每个研究各 2 条资格段落；延长期人群不冒称剂量。
    assert len(projection.observations) == 85
    assert len(projection.eligibility_sections) == 4
    assert all(item.reason is None for item in projection.eligibility_sections)
    assert {(item.trial_id, item.section) for item in projection.eligibility_sections} == {
        (trial_id, kind)
        for trial_id in ("NCT02264639", "NCT03829449")
        for kind in CtgovCEligibilitySectionKind
    }
    assert len(projection.unresolved_atoms) == 1
    assert projection.unresolved_atoms[0].reason is (
        CtgovCUnresolvedReason.ARM_DESCRIPTION_WITHOUT_DOSE
    )
    unsupported = {item.field_id: item.reason for item in projection.unsupported_atoms}
    assert unsupported["ctgov.protocol.eligibility.sex"] is (
        CtgovCUnsupportedReason.NO_EXISTING_DESIGN_FIELD
    )
    assert "ctgov.protocol.design.phase" not in unsupported
    assert "ctgov.protocol.design.study_type" not in unsupported
    assert unsupported["ctgov.protocol.arm.type"] is (
        CtgovCUnsupportedReason.NO_EXISTING_DESIGN_FIELD
    )
    assert unsupported["ctgov.protocol.intervention.name"] is (
        CtgovCUnsupportedReason.INTERVENTIONS_MODULE_NOT_PROJECTED
    )
    assert unsupported["ctgov.protocol.intervention.arm_group_label"] is (
        CtgovCUnsupportedReason.RELATION_ATOM_ONLY
    )
    interventions = next(
        item for item in projection.atom_families if item.family == "interventions"
    )
    assert "ctgov.protocol.intervention.name" in interventions.unsupported_field_ids
    assert len(projection.unsupported_atoms) == 29
    assert len({item.atom_id for item in projection.unsupported_atoms}) == 29


@pytest.mark.parametrize("nct_id,phase", [("NCT02264639", "PHASE1"), ("NCT03829449", "PHASE3")])
def test_registered_phase_and_study_type_reach_identity_without_inventing_role(
    nct_id: str, phase: str,
) -> None:
    capture = _fixed_capture(nct_id)
    projection = _project_fixed(nct_id)
    rows = [row for row in projection.observations
            if row.field_family is DesignFieldFamily.TRIAL_IDENTITY]
    assert {row.source_text for row in rows} == {phase, "INTERVENTIONAL"}
    for row in rows:
        assert row.field == "trial_identity"
        assert row.development_role is None
        assert row.review_state is FactReviewState.CANDIDATE
        assert row.period is None
        assert extract_locator_quote(capture.content_text, media_type=capture.media_type,
                                     locator=row.source_locator) == row.source_text
    stage = next(row for row in rows if row.source_text == phase)
    assert stage.stage == phase
    assert "登记阶段" in (stage.display_text or "")


def test_multiple_phases_and_absence_keep_exact_source_instances() -> None:
    capture = _mutated_capture("NCT02264639", lambda record:
                              record["protocolSection"]["designModule"].update(
                                  {"phases": ["PHASE1", "PHASE2"]}))
    atoms = extract_ctgov_protocol_design_atoms(capture)
    projection = _project(((capture, atoms),), _full_bindings())
    rows = [row for row in projection.observations if row.stage is not None]
    assert len(rows) == 2
    assert {row.stage for row in rows} == {"PHASE1", "PHASE2"}
    assert len({row.row_id for row in rows}) == 2
    assert {row.source_locator.field_path for row in rows} == {
        "$.protocolSection.designModule.phases[0]",
        "$.protocolSection.designModule.phases[1]",
    }
    missing = _mutated_capture("NCT02264639", lambda record:
                              record["protocolSection"]["designModule"].pop("phases"))
    without = _project(((missing, extract_ctgov_protocol_design_atoms(missing)),), _full_bindings())
    assert not any(row.stage is not None for row in without.observations)
    assert any(gap.path == "$.protocolSection.designModule.phases" for gap in without.gaps)


def test_unknown_arm_binding_is_unresolved_and_never_guesses_group() -> None:
    bindings = (
        CtgovCTrialBinding(
            trial_id="nct02264639",
            product_id="pegcetacoplan",
            arms=(
                CtgovCArmBinding(
                    label="Cohort 1",
                    group_id="group-nct02264639-cohort-1",
                    role="experimental_arm",
                ),
                CtgovCArmBinding(
                    label="Cohort 2",
                    group_id="group-nct02264639-cohort-2",
                    role="experimental_arm",
                ),
            ),
        ),
    )
    projection = _project_fixed("NCT02264639", bindings=bindings)
    bound_groups = {"group-nct02264639-cohort-1", "group-nct02264639-cohort-2"}
    arm_rows = tuple(
        item
        for item in projection.observations
        if item.field in {"experimental_arm", "control_arm", "dosing_regimen"}
    )
    assert arm_rows
    assert {item.group_id for item in arm_rows} <= bound_groups
    unresolved = {item.field_id: item.reason for item in projection.unresolved_atoms}
    assert unresolved["ctgov.protocol.arm.label"] is (CtgovCUnresolvedReason.MISSING_ARM_BINDING)
    assert unresolved["ctgov.protocol.arm.description"] is (
        CtgovCUnresolvedReason.MISSING_ARM_BINDING
    )
    assert unresolved["ctgov.protocol.arm.intervention_name"] is (
        CtgovCUnresolvedReason.MISSING_ARM_BINDING
    )
    unresolved_paths = {item.path for item in projection.unresolved_atoms if item.path is not None}
    assert any(path.endswith("armGroups[2].label") for path in unresolved_paths)
    assert any(path.endswith("armGroups[3].description") for path in unresolved_paths)
    arms = next(item for item in projection.atom_families if item.family == "arms")
    assert arms.atom_count == 16
    assert arms.mapped_count == 6
    assert arms.unsupported_count == 4
    assert arms.unresolved_count == 6
    # 未绑定组别的原子不生成任何观察：不存在猜测的组别标识。
    assert not any(
        "cohort-3" in item.group_id or "cohort-4" in item.group_id
        for item in projection.observations
    )


def test_unmatched_caller_binding_fails_closed() -> None:
    capture, atoms = _study("NCT02264639")
    ghost_arm = CtgovCTrialBinding(
        trial_id="nct02264639",
        product_id="pegcetacoplan",
        arms=(CtgovCArmBinding(label="Ghost Arm", group_id="group-ghost", role="control_arm"),),
    )
    with pytest.raises(CtgovCDesignProjectionError):
        _project(((capture, atoms),), (ghost_arm,))


def test_unknown_product_binding_leaves_atoms_unresolved_without_observation() -> None:
    """没有产品绑定的研究不得生成观察；支持的原子逐条保持未决。"""
    capture, atoms = _study("NCT02264639")
    other_trial_only = tuple(item for item in _full_bindings() if item.trial_id == "nct03829449")
    projection = _project(((capture, atoms),), other_trial_only)
    assert projection.observations == ()
    assert projection.eligibility_sections == ()
    assert len(projection.unresolved_atoms) == 32
    assert all(
        item.reason is CtgovCUnresolvedReason.MISSING_TRIAL_BINDING
        for item in projection.unresolved_atoms
    )
    assert {item.trial_id for item in projection.unresolved_atoms} == {"NCT02264639"}
    assert len(projection.unsupported_atoms) == 17


@pytest.mark.parametrize(
    "variant",
    ["wrong_raw_trial", "wrong_field", "omitted_atom", "fake_gap", "eligibility_byte_drift"],
)
def test_replayed_source_proves_identity_semantics_and_complete_atom_set(variant: str) -> None:
    capture, atoms = _study("NCT02264639")
    if variant == "wrong_raw_trial":
        record = json.loads(capture.content_text)
        record["protocolSection"]["identificationModule"]["nctId"] = "NCT99999999"
        capture = capture.model_copy(update={"content_text": json.dumps(record)})
    elif variant == "eligibility_byte_drift":
        # 资格标量在采集侧漂移而原子仍来自原始字节：必须失败关闭，
        # 不允许投影把漂移后的分段当作原引文。
        record = json.loads(capture.content_text)
        module = record["protocolSection"]["eligibilityModule"]
        module["eligibilityCriteria"] = module["eligibilityCriteria"] + "\n* Drifted clause"
        capture = capture.model_copy(update={"content_text": json.dumps(record)})
    elif variant == "wrong_field":
        changed = atoms.facts[0].model_copy(update={"field_id": "ctgov.protocol.design.allocation"})
        atoms = replace(atoms, facts=(changed, *atoms.facts[1:]))
    elif variant == "omitted_atom":
        atoms = replace(atoms, facts=atoms.facts[1:])
    else:
        atoms = replace(atoms, absent_paths=(*atoms.absent_paths, "$.protocolSection.fakeGap"))
    with pytest.raises(CtgovCDesignProjectionError):
        _project(((capture, atoms),), _full_bindings())


@pytest.mark.parametrize(
    "variant",
    ["duplicate-trial-binding", "duplicate-arm-label", "duplicate-arm-group", "duplicate-study"],
)
def test_reused_identity_fails_closed(variant: str) -> None:
    base = _full_bindings()
    if variant == "duplicate-trial-binding":
        bindings = (base[0], base[0].model_copy(update={"product_id": "other"}))
    elif variant == "duplicate-arm-label":
        first = base[0]
        bindings = (
            first.model_copy(
                update={
                    "arms": (
                        first.arms[0],
                        first.arms[0].model_copy(update={"group_id": "group-reused"}),
                    )
                }
            ),
        )
    elif variant == "duplicate-arm-group":
        first = base[0]
        bindings = (
            first.model_copy(
                update={
                    "arms": (
                        first.arms[0],
                        first.arms[1].model_copy(update={"group_id": first.arms[0].group_id}),
                    )
                }
            ),
        )
    else:
        bindings = base
    studies = (_study("NCT02264639"),)
    if variant == "duplicate-study":
        studies = studies + studies
        bindings = (base[0],)
    with pytest.raises(CtgovCDesignProjectionError):
        _project(studies, bindings)


def test_malformed_atom_locator_fails_closed() -> None:
    capture, atoms = _study("NCT02264639")
    source_fact = atoms.facts[0]
    variants = (
        EvidenceLocator(document_role="clinical_trial_registry", url="https://example.test/x"),
        EvidenceLocator(
            document_role="clinical_trial_registry",
            field_path="protocolSection.eligibilityModule.eligibilityCriteria",
        ),
        EvidenceLocator(
            document_role="primary_trial_report",
            field_path="$.protocolSection.eligibilityModule.eligibilityCriteria",
        ),
        EvidenceLocator(
            document_role="clinical_trial_registry",
            field_path="$.protocolSection.eligibilityModule.eligibilityCriteria",
            url="https://clinicaltrials.gov/study/NCT99999999",
        ),
    )
    for locator in variants:
        broken = replace(
            atoms,
            facts=(source_fact.model_copy(update={"locator": locator}), *atoms.facts[1:]),
        )
        with pytest.raises(CtgovCDesignProjectionError):
            _project(((capture, broken),), _full_bindings())


def test_absent_and_empty_protocol_lists_become_gaps_not_observations() -> None:
    projection = _project_fixed("NCT02264639", "NCT03829449")
    gaps = {(item.trial_id, item.path): item.reason for item in projection.gaps}
    assert (
        "NCT02264639",
        "$.protocolSection.outcomesModule.secondaryOutcomes",
    ) in gaps
    assert all(item.reason == "absent_or_empty_protocol_path" for item in projection.gaps)
    assert not any(
        item.field.startswith("secondary_endpoint") for item in _rows(projection, "nct02264639")
    )

    def clear_secondary(record: dict[str, Any]) -> None:
        record["protocolSection"]["outcomesModule"]["secondaryOutcomes"] = []

    source = _mutated_capture("NCT03829449", clear_secondary)
    atoms = extract_ctgov_protocol_design_atoms(source)
    mutated = _project(((source, atoms),), _full_bindings())
    assert "$.protocolSection.outcomesModule.secondaryOutcomes" in atoms.absent_paths
    assert any(
        item.trial_id == "NCT03829449"
        and item.path == "$.protocolSection.outcomesModule.secondaryOutcomes"
        for item in mutated.gaps
    )
    secondary = next(item for item in mutated.atom_families if item.family == "secondary-endpoints")
    assert (secondary.atom_count, secondary.mapped_count) == (0, 0)
    assert not any(item.field.startswith("secondary_endpoint") for item in mutated.observations)
    assert len(mutated.observations) == _EXPECTED_STUDY_OBSERVATIONS["NCT03829449"] - 36


def test_endpoint_instances_pair_measure_and_timeframe_by_source_index() -> None:
    projection = _project_fixed("NCT02264639", "NCT03829449")
    expected_instances = {"nct02264639": 4, "nct03829449": 13}
    for trial_id, expected in expected_instances.items():
        rows = _rows(projection, trial_id)
        endpoints = {
            item.outcome_id: item
            for item in rows
            if item.field_family is DesignFieldFamily.ENDPOINT
        }
        timepoints = {
            item.outcome_id: item
            for item in rows
            if item.field_family is DesignFieldFamily.TIMEPOINT
        }
        assert set(endpoints) == set(timepoints)
        assert len(endpoints) == expected
        assert all(item.outcome_id for item in endpoints.values())
        for outcome_id, endpoint in endpoints.items():
            timepoint = timepoints[outcome_id]
            assert endpoint.assessment_timepoint == timepoint.source_text
            assert endpoint.endpoint_key == timepoint.endpoint_key
        instances = build_endpoint_instances(rows)
        assert len(instances) == expected
        assert all(item.timepoint for item in instances)
    view = project_endpoint_definition_timepoint(projection.observations)
    assert len(view.table_rows) == 17
    assert tuple(item.endpoint_identity for item in view.chart_rows) == tuple(
        item.endpoint_identity for item in view.table_rows
    )


def test_projection_reaches_existing_c_views_but_never_stamps_acceptance() -> None:
    projection = _project_fixed("NCT02264639", "NCT03829449")
    trial_ids = ("nct02264639", "nct03829449")
    assert project_design_map(projection.observations).table_rows
    for trial_id in trial_ids:
        dossier = project_trial_dossier(projection.observations, trial_id=trial_id)
        expected = {item.observation_id for item in _rows(projection, trial_id)}
        assert set(dossier.observation_ids) == expected
    assert project_population_view(projection.observations).table_rows
    gate = evaluate_design_gate(projection.observations, core_trial_ids=trial_ids)
    assert gate.decision is DesignGateDecision.BLOCKED
    assert gate.failures
    assert all(
        item.review_state is not FactReviewState.ACCEPTED for item in projection.observations
    )
    assert all(
        item.conflict_disposition is not ConflictDisposition.OPEN_CONFLICT_PRESERVED
        for item in projection.observations
    )


def test_projection_is_deterministic_and_keeps_capture_bytes_read_only() -> None:
    studies = (_study("NCT02264639"), _study("NCT03829449"))
    before = tuple(capture.content_text for capture, _ in studies)
    first = _project(studies, _full_bindings())
    second = _project(studies, _full_bindings())
    assert first == second
    # 输入顺序变化不改变观察身份集合或资格段落结果。
    reordered = _project(tuple(reversed(studies)), _full_bindings())
    by_observation_id = {item.observation_id: item for item in first.observations}
    assert {item.observation_id for item in reordered.observations} == set(by_observation_id)
    assert all(item == by_observation_id[item.observation_id] for item in reordered.observations)
    assert sorted(reordered.eligibility_sections, key=lambda item: item.trial_id) == sorted(
        first.eligibility_sections, key=lambda item: item.trial_id
    )
    assert tuple(capture.content_text for capture, _ in studies) == before


def test_min_age_normalizes_only_from_year_scalars_else_unresolved() -> None:
    projection = _project_fixed("NCT02264639")
    age_rows = tuple(
        item
        for item in projection.observations
        if item.field == "target_population" and item.threshold_value is not None
    )
    assert len(age_rows) == 1
    assert age_rows[0].threshold_value == "18"
    assert age_rows[0].threshold_unit == "岁"
    assert age_rows[0].operator == "≥"
    eligibility = next(item for item in projection.atom_families if item.family == "eligibility")
    assert eligibility.unsupported_field_ids == (
        "ctgov.protocol.eligibility.healthy_volunteers",
        "ctgov.protocol.eligibility.sex",
        "ctgov.protocol.eligibility.std_ages",
    )
    assert not projection.unresolved_atoms

    def months_only(record: dict[str, Any]) -> None:
        record["protocolSection"]["eligibilityModule"]["minimumAge"] = "6 Months"

    source = _mutated_capture("NCT02264639", months_only)
    atoms = extract_ctgov_protocol_design_atoms(source)
    mutated = _project(((source, atoms),), _full_bindings())
    unresolved = {item.field_id: item.reason for item in mutated.unresolved_atoms}
    assert unresolved["ctgov.protocol.eligibility.minimum_age"] is (
        CtgovCUnresolvedReason.UNPARSABLE_SCALAR_FOR_FIELD
    )
    assert not any(
        item.field == "target_population" and item.threshold_value is not None
        for item in mutated.observations
    )


@pytest.mark.parametrize("nct_id", sorted(_EXPECTED_STUDY_OBSERVATIONS))
def test_fixed_eligibility_sections_are_exact_contiguous_substrings(nct_id: str) -> None:
    capture, atoms = _study(nct_id)
    projection = _project(((capture, atoms),), _full_bindings())
    trial_id = nct_id.lower()
    parent = _parent_criteria_row(projection, trial_id)
    inclusion = _section_row(projection, trial_id, "inclusion_criterion")
    exclusion = _section_row(projection, trial_id, "exclusion_criterion")
    expected_inclusion, expected_exclusion = _expected_sections(nct_id)

    # 派生结果与既有 C 分段器逐字节一致，且为父级标量的精确连续子串。
    assert inclusion.source_text == expected_inclusion
    assert exclusion.source_text == expected_exclusion
    assert inclusion.source_text in parent.source_text
    assert exclusion.source_text in parent.source_text
    assert parent.source_text == extract_locator_quote(
        capture.content_text, media_type=capture.media_type, locator=parent.source_locator
    )
    # 来源事实 ID、来源实例与标量 JSON 定位与父级一致：派生段落不是新事实，
    # 定位仍指向完整资格标量而不是更窄的段落。
    assert inclusion.source_row_id == exclusion.source_row_id == parent.source_row_id
    assert inclusion.source_version_id == exclusion.source_version_id == capture.source_id
    assert inclusion.source_locator == exclusion.source_locator == parent.source_locator
    assert (inclusion.source_locator.field_path or "").endswith(".eligibilityCriteria")
    assert inclusion.field_family is DesignFieldFamily.POPULATION
    assert exclusion.field_family is DesignFieldFamily.POPULATION
    assert inclusion.review_state is FactReviewState.CANDIDATE
    # 本层不发明 period：来源无期间标量时保持 None，由上游决策。
    assert inclusion.period is None
    assert exclusion.period is None
    assert validate_design_observation(inclusion) == inclusion
    assert validate_design_observation(exclusion) == exclusion

    statuses = {item.section: item for item in projection.eligibility_sections}
    assert statuses[CtgovCEligibilitySectionKind.INCLUSION].observation_id == (
        inclusion.observation_id
    )
    assert statuses[CtgovCEligibilitySectionKind.EXCLUSION].observation_id == (
        exclusion.observation_id
    )
    assert all(item.reason is None for item in statuses.values())

    # 完整条款保留：嵌套项目符号/编号、AND/OR 与末条均不缺失、不扁平化。
    tokens = {
        "NCT02264639": (
            "* Male or Female",
            "screening OR have received at least one transfusion",
            "No vaccination against N. meningitidis",
        ),
        "NCT03829449": (
            "1. Patients 18 years and above",
            "OR have had a vasectomy",
            "Participation in other clinical trials with investigational product.",
        ),
    }
    inclusion_token, boolean_token, exclusion_tail = tokens[nct_id]
    assert inclusion_token in inclusion.source_text
    assert boolean_token in inclusion.source_text
    assert exclusion_tail in exclusion.source_text
    assert inclusion.source_text.count("\n") >= 5
    assert exclusion.source_text.count("\n") >= 5


def test_projection_feeds_inclusion_and_exclusion_views_with_complete_sections() -> None:
    projection = _project_fixed("NCT02264639", "NCT03829449")
    inclusion_view = project_inclusion_view(projection.observations, indication_id=_INDICATION_ID)
    exclusion_view = project_exclusion_view(projection.observations, indication_id=_INDICATION_ID)

    assert {row.design_element for row in inclusion_view.table_rows} == {"inclusion_criterion"}
    assert {row.design_element for row in exclusion_view.table_rows} == {"exclusion_criterion"}
    assert inclusion_view.chart_rows == inclusion_view.table_rows
    assert exclusion_view.chart_rows == exclusion_view.table_rows
    assert set(inclusion_view.evidence_by_chain_id) == {
        row.drilldown_chain_id for row in inclusion_view.table_rows
    }
    inclusion_by_trial = {row.trial_id: row for row in inclusion_view.table_rows}
    exclusion_by_trial = {row.trial_id: row for row in exclusion_view.table_rows}
    assert set(inclusion_by_trial) == {"nct02264639", "nct03829449"}
    for nct_id, trial_id in (("NCT02264639", "nct02264639"), ("NCT03829449", "nct03829449")):
        expected_inclusion, expected_exclusion = _expected_sections(nct_id)
        assert inclusion_by_trial[trial_id].source_text == expected_inclusion
        assert exclusion_by_trial[trial_id].source_text == expected_exclusion
        assert (
            inclusion_by_trial[trial_id].source_locator.document_role == "clinical_trial_registry"
        )


@pytest.mark.parametrize("mention", [
    "* Investigators must review exclusion criteria before enrollment.",
    "* Patients must meet inclusion criteria and have no active infection.",
])
def test_ordinary_eligibility_clause_is_not_a_second_heading(mention: str) -> None:
    def mutate(record: dict[str, Any]) -> None:
        module = record["protocolSection"]["eligibilityModule"]
        module["eligibilityCriteria"] = module["eligibilityCriteria"].replace(
            "Exclusion Criteria:", mention + "\n\nExclusion Criteria:", 1,
        )

    capture, atoms = _mutated_study("NCT02264639", mutate)
    projection = _project(((capture, atoms),), _full_bindings())
    inclusion = _section_row(projection, "nct02264639", "inclusion_criterion")
    assert mention in inclusion.source_text
    assert all(item.reason is None for item in projection.eligibility_sections)


def test_reversed_heading_order_does_not_label_inclusion_as_exclusion() -> None:
    def mutate(record: dict[str, Any]) -> None:
        record["protocolSection"]["eligibilityModule"]["eligibilityCriteria"] = (
            "Exclusion Criteria:\n* Active infection.\n\n"
            "Inclusion Criteria:\n* Adults with PNH."
        )

    capture, atoms = _mutated_study("NCT02264639", mutate)
    projection = _project(((capture, atoms),), _full_bindings())
    parent = _parent_criteria_row(projection, "nct02264639")
    assert "Adults with PNH" in parent.source_text
    assert all(item.observation_id is None for item in projection.eligibility_sections)
    assert all(item.reason is not None for item in projection.eligibility_sections)


def _heading_anomaly_mutation(variant: str) -> Callable[[dict[str, Any]], None]:
    def mutate(record: dict[str, Any]) -> None:
        module = record["protocolSection"]["eligibilityModule"]
        raw = module["eligibilityCriteria"]
        if variant == "missing_exclusion_heading":
            module["eligibilityCriteria"] = raw.replace(
                "Exclusion Criteria:", "Additional Notes:", 1
            )
        elif variant == "missing_inclusion_heading":
            module["eligibilityCriteria"] = raw.replace(
                "Inclusion Criteria:", "Eligibility Overview:", 1
            )
        elif variant == "repeated_exclusion_heading":
            module["eligibilityCriteria"] = raw.replace(
                "Exclusion Criteria:", "Exclusion Criteria:\n\nExclusion Criteria:", 1
            )
        elif variant == "repeated_inclusion_heading":
            module["eligibilityCriteria"] = raw.replace(
                "Inclusion Criteria:", "Inclusion Criteria:\n\nInclusion Criteria:", 1
            )
        else:
            module["eligibilityCriteria"] = (
                raw.split("Exclusion Criteria:")[0] + "Exclusion Criteria:"
            )

    return mutate


_HEADING_ANOMALY_CASES = (
    (
        "missing_exclusion_heading",
        CtgovCEligibilitySectionReason.INCLUSION_BOUNDARY_UNRESOLVED,
        CtgovCEligibilitySectionReason.EXCLUSION_HEADING_MISSING,
    ),
    (
        "missing_inclusion_heading",
        CtgovCEligibilitySectionReason.INCLUSION_HEADING_MISSING,
        None,
    ),
    (
        "repeated_exclusion_heading",
        CtgovCEligibilitySectionReason.INCLUSION_BOUNDARY_UNRESOLVED,
        CtgovCEligibilitySectionReason.EXCLUSION_HEADING_REPEATED,
    ),
    (
        "repeated_inclusion_heading",
        CtgovCEligibilitySectionReason.INCLUSION_HEADING_REPEATED,
        None,
    ),
    ("empty_exclusion_section", None, CtgovCEligibilitySectionReason.EXCLUSION_TEXT_EMPTY),
)


@pytest.mark.parametrize(
    ("variant", "inclusion_reason", "exclusion_reason"),
    _HEADING_ANOMALY_CASES,
)
def test_eligibility_heading_anomalies_stay_explicitly_unresolved(
    variant: str,
    inclusion_reason: CtgovCEligibilitySectionReason | None,
    exclusion_reason: CtgovCEligibilitySectionReason | None,
) -> None:
    capture, atoms = _mutated_study("NCT02264639", _heading_anomaly_mutation(variant))
    projection = _project(((capture, atoms),), _full_bindings())
    rows = _rows(projection, "nct02264639")
    parent = _parent_criteria_row(projection, "nct02264639")
    raw = json.loads(capture.content_text)["protocolSection"]["eligibilityModule"][
        "eligibilityCriteria"
    ]
    # 父级完整原文始终可用；未决只影响派生段落，不生成观察也不改写父级。
    assert parent.source_text == raw
    statuses = {item.section: item for item in projection.eligibility_sections}
    assert set(statuses) == set(CtgovCEligibilitySectionKind)
    assert {item.atom_id for item in projection.eligibility_sections} == {parent.source_row_id}
    assert all(
        item.parent_path.endswith("eligibilityCriteria") for item in projection.eligibility_sections
    )
    assert not projection.unresolved_atoms
    for kind, field, reason in (
        (CtgovCEligibilitySectionKind.INCLUSION, "inclusion_criterion", inclusion_reason),
        (CtgovCEligibilitySectionKind.EXCLUSION, "exclusion_criterion", exclusion_reason),
    ):
        outcome = statuses[kind]
        row = next((item for item in rows if item.field == field), None)
        if reason is None:
            assert outcome.reason is None
            assert row is not None
            assert outcome.observation_id == row.observation_id
            assert row.source_text in parent.source_text
            assert row.source_locator == parent.source_locator
            assert row.compatibility_rule == ELIGIBILITY_SECTION_COMPATIBILITY_RULE
        else:
            assert outcome.reason is reason
            assert outcome.observation_id is None
            assert row is None


_NESTED_CRITERIA = (
    "Inclusion Criteria:\n"
    "1. Adults with PNH AND\n"
    "   * Prior eculizumab for at least 3 months\n"
    "   * Hb < 10 g/dL OR documented transfusion history\n"
    "2. Willing and able to give informed consent\n"
    "Exclusion Criteria:\n"
    "1. Active infection\n"
    "   * Exception: resolved infection within 30 days\n"
    "2. Pregnancy OR breastfeeding\n"
)
_NESTED_INCLUSION = (
    "1. Adults with PNH AND\n"
    "   * Prior eculizumab for at least 3 months\n"
    "   * Hb < 10 g/dL OR documented transfusion history\n"
    "2. Willing and able to give informed consent"
)
_NESTED_EXCLUSION = (
    "1. Active infection\n"
    "   * Exception: resolved infection within 30 days\n"
    "2. Pregnancy OR breastfeeding"
)


def test_nested_criteria_and_boolean_logic_are_preserved_verbatim() -> None:
    def replace_criteria(record: dict[str, Any]) -> None:
        record["protocolSection"]["eligibilityModule"]["eligibilityCriteria"] = _NESTED_CRITERIA

    capture, atoms = _mutated_study("NCT02264639", replace_criteria)
    projection = _project(((capture, atoms),), _full_bindings())
    parent = _parent_criteria_row(projection, "nct02264639")
    inclusion = _section_row(projection, "nct02264639", "inclusion_criterion")
    exclusion = _section_row(projection, "nct02264639", "exclusion_criterion")

    assert parent.source_text == _NESTED_CRITERIA
    # 段落是父级标量的精确连续子串：不拆条、不改写、不扁平化布尔逻辑或嵌套项。
    assert inclusion.source_text == _NESTED_INCLUSION
    assert exclusion.source_text == _NESTED_EXCLUSION
    assert inclusion.source_text in parent.source_text
    assert exclusion.source_text in parent.source_text
    assert "\n   * " in inclusion.source_text
    assert "AND" in inclusion.source_text
    assert "OR" in inclusion.source_text
    assert "Exception:" in exclusion.source_text
    assert "OR" in exclusion.source_text


@pytest.mark.parametrize("collection", ["primaryOutcomes", "secondaryOutcomes"])
@pytest.mark.parametrize("absence", ["absent", "empty", "null"])
def test_missing_endpoint_window_is_local_unresolved_not_whole_projection_failure(
    collection: str, absence: str,
) -> None:
    """Missing source time cannot borrow a sibling window or discard other studies."""
    nct = "NCT03829449"

    def mutate(record: dict[str, Any]) -> None:
        outcome = record["protocolSection"]["outcomesModule"][collection][0]
        if absence == "absent":
            outcome.pop("timeFrame")
        else:
            outcome["timeFrame"] = "" if absence == "empty" else None

    changed = _mutated_study(nct, mutate)
    intact = _study("NCT02264639")
    original = _project((intact, _study(nct)), _full_bindings())
    prefix = f"$.protocolSection.outcomesModule.{collection}[0]."
    affected = {fact.fact_id for fact in changed[1].facts
                if (fact.locator.field_path or "").startswith(prefix)}
    assert affected
    projection = _project((changed, intact), _full_bindings())
    local = [item for item in projection.unresolved_atoms if item.atom_id in affected]
    assert {item.atom_id for item in local} == affected
    assert all(item.reason.value == "missing_outcome_timeframe" for item in local)
    assert all(item.trial_id == nct and (item.path or "").startswith(prefix)
               for item in local)
    assert any(item.path == prefix + "timeFrame" for item in projection.gaps)
    assert not any(item.source_row_id in affected for item in projection.observations)
    baseline_other = {row.observation_id: row for row in original.observations
                      if not (row.source_locator.field_path or "").startswith(prefix)
                      or row.trial_id != nct.casefold()}
    assert {row.observation_id: row for row in projection.observations} == baseline_other
    for family in projection.atom_families:
        assert family.atom_count == (
            family.mapped_count + family.unsupported_count + family.unresolved_count
        )
    facts = {fact.fact_id: fact for fact in changed[1].facts}
    for item in local:
        fact = facts[item.atom_id]
        assert extract_locator_quote(changed[0].content_text,
                                     media_type=changed[0].media_type,
                                     locator=fact.locator) == fact.raw_value
    reordered = _project((intact, changed), _full_bindings())
    assert {row.observation_id: row for row in reordered.observations} == baseline_other
