from __future__ import annotations

from typing import Any

import pytest

from ci_workflow.reports.b.contracts import EndpointObservation, match_endpoint_compatibility
from ci_workflow.reports.b.efficacy import (
    EndpointAdoptionStatus,
    EndpointBasisError,
    GuidanceEvidence,
    GuidanceLifecycleState,
    GuidanceTrack,
    build_endpoint_basis,
    guidance_lifecycle_state,
    select_current_guidance,
    validate_endpoint_basis,
)


def _observation(
    observation_id: str,
    trial_id: str,
    *,
    endpoint_id: str = "easi75",
    role: str = "primary",
) -> EndpointObservation:
    return EndpointObservation.model_validate(
        {
            "observation_id": observation_id,
            "trial_id": trial_id,
            "endpoint_id": endpoint_id,
            "endpoint_definition": f"{endpoint_id} 原始定义",
            "endpoint_role": role,
            "unit": "%" if endpoint_id == "easi75" else "points",
            "direction": "higher_is_better" if endpoint_id == "easi75" else "lower_is_better",
            "analysis_form": "response_rate" if endpoint_id == "easi75" else "change_from_baseline",
            "timepoint": 12,
            "time_unit": "week",
        }
    )


def _guidance(
    *,
    document_id: str,
    agency: str,
    jurisdiction: str,
    version_date: str,
    content_sha256: str,
    guidance_status: str = "final",
    lifecycle_status: str = "active",
    endpoint_family_id: str = "endpoint-easi75-response-v1",
    supersedes_version_ids: tuple[str, ...] = (),
    superseded_by_version_id: str | None = None,
    withdrawn_at: str | None = None,
    population_context: str = "成人目标适应症受试者",
    development_context: str = "确证性药物临床试验主要终点",
) -> GuidanceEvidence:
    return GuidanceEvidence.create(
        jurisdiction=jurisdiction,
        agency=agency,
        document_id=document_id,
        title=f"{agency} endpoint guidance",
        guidance_status=guidance_status,
        version_date=version_date,
        population_context=population_context,
        development_context=development_context,
        source_url=f"https://example.test/{document_id}/{version_date}",
        locator_label="第 5 页主要终点",
        locator_page=5,
        content_sha256=content_sha256,
        captured_at="2026-08-29T09:00:00+08:00",
        lifecycle_status=lifecycle_status,
        supersedes_version_ids=supersedes_version_ids,
        superseded_by_version_id=superseded_by_version_id,
        withdrawn_at=withdrawn_at,
        endpoint_family_id=endpoint_family_id,
    )


def _envelope(
    observation_id: str,
    trial_id: str,
    *,
    endpoint_id: str = "easi75",
    role: str = "primary",
    study_role: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "observation": _observation(
            observation_id,
            trial_id,
            endpoint_id=endpoint_id,
            role=role,
        )
    }
    if study_role is not None:
        payload["study_role"] = study_role
    return payload


def test_home_basis_uses_parallel_current_cde_fda_tracks_and_preserves_exact_lineage() -> None:
    cde_seed = _guidance(
        document_id="cde-endpoints",
        agency="CDE",
        jurisdiction="CN",
        version_date="2021-01-01",
        content_sha256="a" * 64,
    )
    cde_current = _guidance(
        document_id="cde-endpoints",
        agency="CDE",
        jurisdiction="CN",
        version_date="2025-01-01",
        content_sha256="b" * 64,
        supersedes_version_ids=(cde_seed.guideline_version_id,),
    )
    cde_historical = _guidance(
        document_id="cde-endpoints",
        agency="CDE",
        jurisdiction="CN",
        version_date="2021-01-01",
        content_sha256="a" * 64,
        lifecycle_status="superseded",
        superseded_by_version_id=cde_current.guideline_version_id,
    )
    fda_current = _guidance(
        document_id="fda-endpoints",
        agency="FDA",
        jurisdiction="US",
        version_date="2024-01-01",
        content_sha256="c" * 64,
    )
    fda_draft = _guidance(
        document_id="fda-draft",
        agency="FDA",
        jurisdiction="US",
        version_date="2026-01-01",
        content_sha256="d" * 64,
        guidance_status="draft",
    )
    withdrawn = _guidance(
        document_id="withdrawn-endpoints",
        agency="CDE",
        jurisdiction="CN",
        version_date="2018-01-01",
        content_sha256="e" * 64,
        lifecycle_status="withdrawn",
        withdrawn_at="2020-01-01",
    )

    lineage = (cde_historical, cde_current, fda_current, fda_draft, withdrawn)
    assert guidance_lifecycle_state(cde_current) is GuidanceLifecycleState.CURRENT
    assert guidance_lifecycle_state(fda_draft) is GuidanceLifecycleState.DRAFT
    assert guidance_lifecycle_state(cde_historical) is GuidanceLifecycleState.SUPERSEDED
    assert guidance_lifecycle_state(withdrawn) is GuidanceLifecycleState.WITHDRAWN
    assert select_current_guidance(lineage) == (cde_current, fda_current)
    assert select_current_guidance(lineage, track=GuidanceTrack.CDE) == (cde_current,)

    bases = build_endpoint_basis(
        (_envelope("e1", "NCT00000001"), _envelope("e2", "NCT00000002")),
        core_trial_ids=("NCT00000001", "NCT00000002"),
        guidelines=lineage,
    )
    assert len(bases) == 1
    basis = bases[0]
    assert basis.guidance_evidence == tuple(
        sorted(
            lineage,
            key=lambda item: (
                item.guideline_series_id,
                item.version_date,
                item.guideline_version_id,
            ),
        )
    )
    assert basis.current_guidance_evidence == (cde_current, fda_current)
    assert basis.cde_guidance == (cde_historical, cde_current, withdrawn)
    assert set(basis.fda_guidance) == {fda_current, fda_draft}
    assert basis.guidance_tracks == (GuidanceTrack.CDE, GuidanceTrack.FDA)
    assert basis.guidance_groups[0].current_guidance_evidence == (cde_current, fda_current)
    assert basis.guidance_groups[0].draft_guidance_evidence == (fda_draft,)
    assert basis.guidance_groups[0].historical_guidance_evidence == (
        cde_historical,
        withdrawn,
    )


def test_superseded_guidance_never_drives_default_and_draft_is_never_presented_as_final() -> None:
    historical_seed = _guidance(
        document_id="cde-history",
        agency="CDE",
        jurisdiction="CN",
        version_date="2021-01-01",
        content_sha256="2" * 64,
    )
    current = _guidance(
        document_id="cde-current",
        agency="CDE",
        jurisdiction="CN",
        version_date="2025-01-01",
        content_sha256="1" * 64,
        supersedes_version_ids=(historical_seed.guideline_version_id,),
    )
    superseded = _guidance(
        document_id="cde-history",
        agency="CDE",
        jurisdiction="CN",
        version_date="2021-01-01",
        content_sha256="2" * 64,
        lifecycle_status="superseded",
        superseded_by_version_id=current.guideline_version_id,
    )
    draft = _guidance(
        document_id="fda-draft",
        agency="FDA",
        jurisdiction="US",
        version_date="2026-01-01",
        content_sha256="3" * 64,
        guidance_status="draft",
    )

    assert select_current_guidance((superseded, draft, current)) == (current,)
    assert guidance_lifecycle_state(superseded) is GuidanceLifecycleState.SUPERSEDED
    assert guidance_lifecycle_state(draft) is GuidanceLifecycleState.DRAFT
    assert draft.lifecycle_label_zh == "草案"
    assert superseded.lifecycle_label_zh == "已替代（历史）"


def test_compatible_guidance_families_merge_with_all_labels_and_material_context_differences_split(
) -> None:
    cde = _guidance(
        document_id="cde-adult",
        agency="CDE",
        jurisdiction="CN",
        version_date="2025-01-01",
        content_sha256="4" * 64,
    )
    fda = _guidance(
        document_id="fda-adult",
        agency="FDA",
        jurisdiction="US",
        version_date="2024-01-01",
        content_sha256="5" * 64,
    )
    pediatric = _guidance(
        document_id="fda-pediatric",
        agency="FDA",
        jurisdiction="US",
        version_date="2024-06-01",
        content_sha256="6" * 64,
        population_context="儿童目标适应症受试者",
    )

    basis = build_endpoint_basis(
        (_envelope("e1", "NCT00000001"), _envelope("e2", "NCT00000002")),
        core_trial_ids=("NCT00000001", "NCT00000002"),
        guidelines=(cde, fda, pediatric),
    )[0]

    groups = {group.population_context: group for group in basis.guidance_groups}
    adult = groups["成人目标适应症受试者"]
    child = groups["儿童目标适应症受试者"]
    assert adult.guidance_evidence == (cde, fda)
    assert adult.cde_guidance == (cde,)
    assert adult.fda_guidance == (fda,)
    assert adult.merge_reason_zh == (
        "终点兼容规则、适用人群和研发语境一致；CDE/FDA 依据平行展示，不设优先级"
    )
    assert child.guidance_evidence == (pediatric,)
    assert all(group.split_reason_zh for group in basis.guidance_groups)
    assert basis.compatibility_rule_ids == ("endpoint-easi75-response-v1",)


def test_current_guidance_family_remains_visible_without_competitor_adoption() -> None:
    nps_guidance = _guidance(
        document_id="fda-nps",
        agency="FDA",
        jurisdiction="US",
        version_date="2025-01-01",
        content_sha256="7" * 64,
        endpoint_family_id="endpoint-nps-change-v1",
    )

    bases = build_endpoint_basis(
        (_envelope("e1", "NCT00000001"), _envelope("e2", "NCT00000002")),
        core_trial_ids=("NCT00000001", "NCT00000002"),
        guidelines=(nps_guidance,),
    )
    by_family = {basis.endpoint_family_id: basis for basis in bases}

    assert by_family["endpoint-nps-change-v1"].hit_trial_ids == ()
    assert by_family["endpoint-nps-change-v1"].compatibility_keys == ()
    assert by_family["endpoint-nps-change-v1"].current_guidance_evidence == (nps_guidance,)
    assert (
        by_family["endpoint-nps-change-v1"].adoption_status
        is EndpointAdoptionStatus.NOT_SELECTED
    )


def test_strict_majority_counts_only_primary_endpoints_in_locked_core_denominator() -> None:
    core = tuple(f"NCT0000000{index}" for index in range(1, 5))
    observations = (
        _envelope("easi-1", core[0]),
        _envelope("easi-2", core[1]),
        _envelope("easi-3", core[2]),
        _envelope("nps-primary-1", core[0], endpoint_id="nps"),
        _envelope("nps-primary-2", core[1], endpoint_id="nps"),
        _envelope("nps-secondary-3", core[2], endpoint_id="nps", role="secondary"),
        _envelope("nps-support-4", core[3], endpoint_id="nps", study_role="supporting"),
        _envelope("easi-out-of-scope", "NCT99999999"),
    )

    bases = build_endpoint_basis(observations, core_trial_ids=core)
    by_family = {item.endpoint_family_id: item for item in bases}
    easi = by_family["endpoint-easi75-response-v1"]
    nps = by_family["endpoint-nps-change-v1"]

    assert easi.denominator_trial_ids == core
    assert easi.strict_majority_required == 3
    assert easi.hit_trial_ids == core[:3]
    assert easi.adoption_status is EndpointAdoptionStatus.STRICT_MAJORITY
    assert easi.adoption_label_zh == "多数竞品采用"
    assert nps.hit_trial_ids == core[:2]
    assert nps.hit_count == 2
    assert nps.adoption_status is EndpointAdoptionStatus.NOT_SELECTED
    assert {item.endpoint_role for item in nps.endpoint_records} == {"primary", "secondary"}


def test_without_strict_majority_only_highest_two_trial_family_is_most_common() -> None:
    core = tuple(f"NCT0000000{index}" for index in range(1, 7))
    observations = (
        *tuple(_envelope(f"easi-{index}", core[index - 1]) for index in (1, 2, 3)),
        *tuple(_envelope(f"nps-{index}", core[index - 1], endpoint_id="nps") for index in (1, 2)),
    )

    bases = build_endpoint_basis(observations, core_trial_ids=core)
    by_family = {item.endpoint_family_id: item for item in bases}
    assert by_family["endpoint-easi75-response-v1"].hit_count == 3
    assert (
        by_family["endpoint-easi75-response-v1"].adoption_status
        is EndpointAdoptionStatus.MOST_COMMON
    )
    assert by_family["endpoint-easi75-response-v1"].adoption_label_zh == "最常采用"
    assert (
        by_family["endpoint-nps-change-v1"].adoption_status is EndpointAdoptionStatus.NOT_SELECTED
    )


def test_authoritative_builder_rejects_forged_compatibility_and_guidance_copies() -> None:
    observation = _observation("e1", "NCT00000001")
    valid = match_endpoint_compatibility(observation)
    forged_compatibility = valid.model_copy(
        update={
            "endpoint_rule_id": "endpoint-nps-change-v1",
            "compatibility_key": (
                "endpoint-nps-change-v1",
                "timepoint-week-12-v1",
            ),
        }
    )
    with pytest.raises(EndpointBasisError, match="重新计算"):
        build_endpoint_basis(
            (forged_compatibility,),
            core_trial_ids=("NCT00000001",),
        )

    valid_guidance = _guidance(
        document_id="cde-endpoints",
        agency="CDE",
        jurisdiction="CN",
        version_date="2025-01-01",
        content_sha256="f" * 64,
    )
    forged_guidance = valid_guidance.model_copy(update={"can_drive_current_default": False})
    with pytest.raises(EndpointBasisError, match="指南依据重新校验"):
        build_endpoint_basis(
            (_envelope("e1", "NCT00000001"),),
            core_trial_ids=("NCT00000001",),
            guidelines=(forged_guidance,),
        )


def test_guidance_track_cannot_be_injected_over_derived_identity() -> None:
    with pytest.raises(ValueError, match="监管轨"):
        GuidanceEvidence.model_validate(
            {
                "guideline_series_id": "series",
                "guideline_version_id": "version",
                "jurisdiction": "CN",
                "agency": "CDE",
                "document_id": "doc",
                "title": "指南",
                "guidance_status": "final",
                "version_date": "2026-01-01",
                "population_context": "成人受试者",
                "development_context": "确证性研究",
                "source_url": "https://example.test/doc",
                "locator": {
                    "document_role": "CDE 指南",
                    "page": 1,
                },
                "content_sha256": "1" * 64,
                "captured_at": "2026-08-29T09:00:00+08:00",
                "lifecycle_status": "active",
                "supersedes_version_ids": (),
                "superseded_by_version_id": None,
                "withdrawn_at": None,
                "can_drive_current_default": True,
                "track": "fda",
            }
        )


def test_endpoint_basis_revalidation_rejects_tampered_model_copy() -> None:
    basis = build_endpoint_basis(
        (_envelope("e1", "NCT00000001"),),
        core_trial_ids=("NCT00000001",),
    )[0]
    assert validate_endpoint_basis(basis) == basis

    forged = basis.model_copy(update={"hit_trial_ids": ("NCT99999999",)})
    with pytest.raises(EndpointBasisError, match="重新校验"):
        validate_endpoint_basis(forged)
