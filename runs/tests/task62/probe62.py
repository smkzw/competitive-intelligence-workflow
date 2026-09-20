"""Independent Task 6.2 probes — Chinese senior clinical trial medical manager review.

Probes exercise the contract from the outside (build → assert structural
invariants) and never modify state. They use canonical schema fields and the
real compatibility policies shipped with the project.
"""

from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path
from typing import Any

REPO = Path("/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow")
sys.path.insert(0, str(REPO / "src"))

from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.domain.enums import FactDisclosureState
from ci_workflow.reports.a.analysis import EndpointDirection
from ci_workflow.reports.b.contracts import (
    EndpointObservation,
    load_endpoint_compatibility_policy,
    load_timepoint_compatibility_policy,
    match_endpoint_compatibility,
)
from ci_workflow.reports.b.efficacy import (
    EfficacyArmRole,
    EfficacyFactRow,
    EfficacySortKey,
    GuidanceEvidence,
    build_efficacy_views,
    build_endpoint_basis,
    guidance_lifecycle_state,
    guidance_status_label_zh,
    reset_efficacy_sort,
    select_current_guidance,
    sort_efficacy_rows,
)

# Load real policies (read-only).
_ENDPOINT_POLICY = load_endpoint_compatibility_policy()
_TIMEPOINT_POLICY = load_timepoint_compatibility_policy()

EASI75_RULE = "endpoint-easi75-response-v1"
EASI75_RAW = "easi75"
EASI75_UNIT = "%"
EASI75_FORM = "response_rate"
TP_12_RULE = "timepoint-week-12-v1"
TP_24_RULE = "timepoint-week-24-v1"
NPS_RULE = "endpoint-nps-change-v1"


def _observation(
    raw_endpoint_id: str,
    trial_id: str,
    *,
    endpoint_role: str = "primary",
    timepoint: int = 12,
    unit: str = EASI75_UNIT,
    analysis_form: str = EASI75_FORM,
    direction: EndpointDirection = EndpointDirection.HIGHER_IS_BETTER,
) -> EndpointObservation:
    return EndpointObservation(
        observation_id=f"obs-{trial_id}-{raw_endpoint_id}-{endpoint_role}-{timepoint}",
        trial_id=trial_id,
        endpoint_id=raw_endpoint_id,
        endpoint_definition=f"def-{raw_endpoint_id}",
        endpoint_role=endpoint_role,
        unit=unit,
        direction=direction,
        analysis_form=analysis_form,
        timepoint=timepoint,
        time_unit="week",
    )


def _compat(
    raw_endpoint_id: str,
    timepoint: int,
    trial_id: str,
    direction: EndpointDirection = EndpointDirection.HIGHER_IS_BETTER,
):
    obs = _observation(
        raw_endpoint_id, trial_id, timepoint=timepoint, direction=direction
    )
    return match_endpoint_compatibility(
        obs, endpoint_policy=_ENDPOINT_POLICY, timepoint_policy=_TIMEPOINT_POLICY
    )


def _fact(
    row_id: str,
    *,
    arm_role: EfficacyArmRole,
    arm_id: str,
    trial_id: str,
    timepoint: int,
    value: float | None,
    comparison_id: str,
    raw_endpoint_id: str = EASI75_RAW,
    endpoint_family_id: str = EASI75_RULE,
    timepoint_rule: str = TP_12_RULE,
    direction: EndpointDirection = EndpointDirection.HIGHER_IS_BETTER,
    unit: str = EASI75_UNIT,
    analysis_form: str = EASI75_FORM,
) -> EfficacyFactRow:
    obs = _observation(
        raw_endpoint_id,
        trial_id,
        timepoint=timepoint,
        unit=unit,
        analysis_form=analysis_form,
        direction=direction,
    )
    compat = match_endpoint_compatibility(
        obs, endpoint_policy=_ENDPOINT_POLICY, timepoint_policy=_TIMEPOINT_POLICY
    )
    return EfficacyFactRow(
        row_id=row_id,
        source_row_id=f"source-{row_id}",
        observation_id=obs.observation_id,
        product_id="product-a",
        trial_id=trial_id,
        endpoint_family_id=endpoint_family_id,
        endpoint_family_label_zh=endpoint_family_id,
        compatibility_key=(endpoint_family_id, timepoint_rule),
        original_endpoint=raw_endpoint_id,
        original_definition=obs.endpoint_definition,
        endpoint_role=obs.endpoint_role,
        direction=direction,
        unit=unit,
        analysis_form=analysis_form,
        actual_timepoint=timepoint,
        actual_timepoint_unit="week",
        analysis_population="全分析集",
        arm_role=arm_role,
        arm_id=arm_id,
        arm_label="治疗组" if arm_role is EfficacyArmRole.TREATMENT else "对照组",
        value=value,
        denominator=100,
        disclosure_state=(
            FactDisclosureState.REPORTED_VALUE
            if value is not None
            else FactDisclosureState.NOT_REPORTED
        ),
        source_version_id="source-version-1",
        source_locator=EvidenceLocator(
            document_role="trial-results", row=f"row-{row_id}"
        ),
        observation=obs,
        compatibility=compat,
        comparison_id=comparison_id,
    )


def probe1_guidance_parallel_and_lifecycle() -> dict[str, Any]:
    out: dict[str, Any] = {"probe": "1_guidance_parallel_lifecycle"}
    cde_old = GuidanceEvidence(
        guideline_series_id="cde-ad",
        guideline_version_id="cde-ad-old-v1",
        jurisdiction="CN",
        agency="CDE",
        document_id="doc-cde-ad-old",
        title="CDE 旧 AD 指南",
        guidance_status="final",
        version_date="2015-01-01",
        population_context="成人中重度 AD",
        development_context="中国境内研发",
        source_url="https://example.test/doc-old",
        locator=EvidenceLocator(document_role="guidance", row="1"),
        content_sha256="c" * 64,
        captured_at="2015-06-01T00:00:00+00:00",
        lifecycle_status="superseded",
        superseded_by_version_id="cde-ad-v1",
        can_drive_current_default=False,
    )
    cde = GuidanceEvidence(
        guideline_series_id="cde-ad",
        guideline_version_id="cde-ad-v1",
        jurisdiction="CN",
        agency="CDE",
        document_id="doc-cde-ad",
        title="CDE AD guideline",
        guidance_status="final",
        version_date="2024-01-01",
        population_context="成人中重度 AD",
        development_context="中国境内研发",
        source_url="https://example.test/doc",
        locator=EvidenceLocator(document_role="guidance", row="1"),
        content_sha256="a" * 64,
        captured_at="2024-01-01T00:00:00+00:00",
        lifecycle_status="active",
        supersedes_version_ids=("cde-ad-old-v1",),
        can_drive_current_default=True,
    )
    fda = GuidanceEvidence(
        guideline_series_id="fda-ad",
        guideline_version_id="fda-ad-v1",
        jurisdiction="US",
        agency="FDA",
        document_id="doc-fda-ad",
        title="FDA AD guidance",
        guidance_status="final",
        version_date="2024-01-01",
        population_context="adults moderate-to-severe AD",
        development_context="global development",
        source_url="https://example.test/doc",
        locator=EvidenceLocator(document_role="guidance", row="1"),
        content_sha256="b" * 64,
        captured_at="2024-01-01T00:00:00+00:00",
        lifecycle_status="active",
        can_drive_current_default=True,
    )
    draft = GuidanceEvidence(
        guideline_series_id="fda-ad-draft",
        guideline_version_id="fda-ad-draft-v1",
        jurisdiction="US",
        agency="FDA",
        document_id="doc-fda-ad-draft",
        title="FDA AD draft",
        guidance_status="draft",
        version_date="2024-06-01",
        population_context="adults moderate-to-severe AD",
        development_context="global development",
        source_url="https://example.test/doc-draft",
        locator=EvidenceLocator(document_role="guidance", row="1"),
        content_sha256="d" * 64,
        captured_at="2024-06-01T00:00:00+00:00",
        lifecycle_status="active",
        can_drive_current_default=False,
    )
    out["sup_lifecycle"] = str(guidance_lifecycle_state(cde_old))
    out["sup_label"] = guidance_status_label_zh(cde_old)
    out["draft_lifecycle"] = str(guidance_lifecycle_state(draft))
    out["draft_label"] = guidance_status_label_zh(draft)
    out["cur_lifecycle"] = str(guidance_lifecycle_state(cde))
    out["cur_label"] = guidance_status_label_zh(cde)
    current = select_current_guidance((cde_old, cde, fda, draft))
    out["default_ids"] = [g.guideline_series_id for g in current]
    out["default_kept_superseded"] = "cde-ad-old" in out["default_ids"] or any(
        g.guideline_version_id == "cde-ad-old-v1" for g in current
    )
    out["default_kept_draft"] = "fda-ad-draft" in out["default_ids"]
    out["default_has_cde_and_fda"] = {"cde-ad", "fda-ad"}.issubset(set(out["default_ids"]))
    # Even though superseded is present in the input, default set must exclude
    # it: can_drive_current_default is False.
    out["default_has_superseded"] = any(
        g.guideline_version_id == "cde-ad-old-v1" for g in current
    )
    return out


def probe2_consensus_denominator_and_role() -> dict[str, Any]:
    out: dict[str, Any] = {"probe": "2_consensus_denominator_role"}
    core = tuple(f"NCT0000000{i}" for i in range(1, 5))
    obs_list = [
        _observation(EASI75_RAW, "NCT00000001", timepoint=12),
        _observation(EASI75_RAW, "NCT00000002", timepoint=12),
        _observation(EASI75_RAW, "NCT00000003", timepoint=12),
        _observation(EASI75_RAW, "NCT00000004", endpoint_role="secondary", timepoint=12),
        _observation(
            "easi_total_score",
            "NCT00000004",
            timepoint=12,
            unit="points",
            analysis_form="change_from_baseline",
            direction=EndpointDirection.LOWER_IS_BETTER,
        ),
    ]
    bases = build_endpoint_basis(
        observations=obs_list,
        core_trial_ids=core,
        endpoint_policy=_ENDPOINT_POLICY,
        timepoint_policy=_TIMEPOINT_POLICY,
    )
    out["basis_keys"] = []
    for b in bases:
        out["basis_keys"].append(
            {
                "endpoint": list(b.compatibility_rule_ids),
                "adoption": str(b.adoption_status),
                "primary_trial_ids": list(b.hit_trial_ids),
                "denominator": list(b.denominator_trial_ids),
            }
        )
    return out


def probe3_longitudinal_vs_singletimepoint() -> dict[str, Any]:
    out: dict[str, Any] = {"probe": "3_longitudinal_vs_singletimepoint"}
    rows = (
        _fact(
            "t-12",
            arm_role=EfficacyArmRole.TREATMENT,
            arm_id="arm-t",
            trial_id="NCT00000001",
            timepoint=12,
            value=61.0,
            comparison_id="cmp-1",
            timepoint_rule=TP_12_RULE,
        ),
        _fact(
            "c-12",
            arm_role=EfficacyArmRole.CONTROL,
            arm_id="arm-c",
            trial_id="NCT00000001",
            timepoint=12,
            value=30.0,
            comparison_id="cmp-1",
            timepoint_rule=TP_12_RULE,
        ),
        _fact(
            "t-24",
            arm_role=EfficacyArmRole.TREATMENT,
            arm_id="arm-t",
            trial_id="NCT00000001",
            timepoint=24,
            value=68.0,
            comparison_id="cmp-1",
            timepoint_rule=TP_24_RULE,
        ),
        _fact(
            "c-24",
            arm_role=EfficacyArmRole.CONTROL,
            arm_id="arm-c",
            trial_id="NCT00000001",
            timepoint=24,
            value=33.0,
            comparison_id="cmp-1",
            timepoint_rule=TP_24_RULE,
        ),
    )
    single_12 = build_efficacy_views(
        facts=rows, compatibility_key=(EASI75_RULE, TP_12_RULE)
    )
    single_24 = build_efficacy_views(
        facts=rows, compatibility_key=(EASI75_RULE, TP_24_RULE)
    )
    long_view = build_efficacy_views(facts=rows, compatibility_key=None)
    out["single_12_rows"] = [r.row_id for r in single_12.fact_rows]
    out["single_24_rows"] = [r.row_id for r in single_24.fact_rows]
    out["single_12_cross_pollution"] = any(
        r in out["single_12_rows"] for r in ("c-24", "t-24")
    )
    out["single_24_cross_pollution"] = any(
        r in out["single_24_rows"] for r in ("c-12", "t-12")
    )
    if long_view.longitudinal_views:
        view = long_view.longitudinal_views[0]
        out["longitudinal_timepoints"] = list(view.timepoints)
        out["longitudinal_present"] = True
    else:
        out["longitudinal_timepoints"] = None
        out["longitudinal_present"] = False
    return out


def probe4_forest_no_derive_parallel_arms() -> dict[str, Any]:
    out: dict[str, Any] = {"probe": "4_forest_no_derive_parallel_arms"}
    rows = (
        _fact(
            "t1",
            arm_role=EfficacyArmRole.TREATMENT,
            arm_id="arm-t",
            trial_id="NCT00000001",
            timepoint=12,
            value=61.0,
            comparison_id="cmp-1",
        ),
        _fact(
            "c1",
            arm_role=EfficacyArmRole.CONTROL,
            arm_id="arm-c",
            trial_id="NCT00000001",
            timepoint=12,
            value=30.0,
            comparison_id="cmp-1",
        ),
    )
    views = build_efficacy_views(
        facts=rows, compatibility_key=(EASI75_RULE, TP_12_RULE)
    )
    out["forest_view_count"] = len(views.source_effect_size_views)
    if views.single_timepoint_views:
        comps = views.single_timepoint_views[0].comparisons
        out["single_comparisons"] = [
            {
                "comparison_id": c.comparison_id,
                "treatment": c.treatment.row_id,
                "control": c.control.row_id,
            }
            for c in comps
        ]
    else:
        out["single_comparisons"] = []
    return out


def probe5_sort_default_unknown_reset() -> dict[str, Any]:
    out: dict[str, Any] = {"probe": "5_sort_default_unknown_reset"}
    BUCKET = (EASI75_RULE, TP_12_RULE)
    rows_a = (
        _fact(
            "a-treatment",
            arm_role=EfficacyArmRole.TREATMENT,
            arm_id="arm-t-a",
            trial_id="NCT00000001",
            timepoint=12,
            value=61.0,
            comparison_id="cmp-A",
        ),
        _fact(
            "a-control",
            arm_role=EfficacyArmRole.CONTROL,
            arm_id="arm-c-a",
            trial_id="NCT00000001",
            timepoint=12,
            value=30.0,
            comparison_id="cmp-A",
        ),
        _fact(
            "b-treatment",
            arm_role=EfficacyArmRole.TREATMENT,
            arm_id="arm-t-b",
            trial_id="NCT00000002",
            timepoint=12,
            value=55.0,
            comparison_id="cmp-B",
        ),
        _fact(
            "b-control",
            arm_role=EfficacyArmRole.CONTROL,
            arm_id="arm-c-b",
            trial_id="NCT00000002",
            timepoint=12,
            value=29.0,
            comparison_id="cmp-B",
        ),
    )
    rows_b = rows_a[::-1]
    default_a = sort_efficacy_rows(rows_a, BUCKET)
    default_b = sort_efficacy_rows(rows_b, BUCKET)
    out["default_stable_across_construction_order"] = [
        r.row_id for r in default_a.rows
    ] == [r.row_id for r in default_b.rows]
    out["default_first_two"] = [r.row_id for r in default_a.rows[:2]]
    out["default_last_two"] = [r.row_id for r in default_a.rows[2:]]
    rows_lower = (
        _fact(
            "lower-t",
            arm_role=EfficacyArmRole.TREATMENT,
            arm_id="arm-t",
            trial_id="NCT00000001",
            timepoint=12,
            value=3.0,
            comparison_id="cmp-L",
            raw_endpoint_id="nps",
            endpoint_family_id=NPS_RULE,
            unit="points",
            analysis_form="change_from_baseline",
            direction=EndpointDirection.LOWER_IS_BETTER,
        ),
        _fact(
            "lower-c",
            arm_role=EfficacyArmRole.CONTROL,
            arm_id="arm-c",
            trial_id="NCT00000001",
            timepoint=12,
            value=5.0,
            comparison_id="cmp-L",
            raw_endpoint_id="nps",
            endpoint_family_id=NPS_RULE,
            unit="points",
            analysis_form="change_from_baseline",
            direction=EndpointDirection.LOWER_IS_BETTER,
        ),
        _fact(
            "unknown-t",
            arm_role=EfficacyArmRole.TREATMENT,
            arm_id="arm-t2",
            trial_id="NCT00000002",
            timepoint=12,
            value=None,
            comparison_id="cmp-U",
            raw_endpoint_id="nps",
            endpoint_family_id=NPS_RULE,
            unit="points",
            analysis_form="change_from_baseline",
            direction=EndpointDirection.LOWER_IS_BETTER,
        ),
        _fact(
            "unknown-c",
            arm_role=EfficacyArmRole.CONTROL,
            arm_id="arm-c2",
            trial_id="NCT00000002",
            timepoint=12,
            value=20.0,
            comparison_id="cmp-U",
            raw_endpoint_id="nps",
            endpoint_family_id=NPS_RULE,
            unit="points",
            analysis_form="change_from_baseline",
            direction=EndpointDirection.LOWER_IS_BETTER,
        ),
    )
    LOWER_BUCKET = (NPS_RULE, TP_12_RULE)
    ranked = sort_efficacy_rows(
        rows_lower, LOWER_BUCKET, sort_mode=EfficacySortKey.EFFICACY_SIGNAL
    )
    out["signals"] = dict(ranked.signal_by_row_id)
    out["unknown_ids"] = list(ranked.unknown_row_ids)
    reset = reset_efficacy_sort(rows_lower, LOWER_BUCKET)
    out["reset_rows"] = [r.row_id for r in reset.rows]
    cross_rows = (
        _fact(
            "wk12",
            arm_role=EfficacyArmRole.TREATMENT,
            arm_id="a",
            trial_id="NCT00000003",
            timepoint=12,
            value=40.0,
            comparison_id="cmp-X",
            timepoint_rule=TP_12_RULE,
        ),
        _fact(
            "wk24",
            arm_role=EfficacyArmRole.TREATMENT,
            arm_id="a",
            trial_id="NCT00000003",
            timepoint=24,
            value=45.0,
            comparison_id="cmp-X",
            timepoint_rule=TP_24_RULE,
        ),
    )
    try:
        sort_efficacy_rows(cross_rows, BUCKET)
        out["cross_bucket_rejected"] = False
        out["cross_bucket_error"] = None
    except Exception as exc:
        out["cross_bucket_rejected"] = True
        out["cross_bucket_error"] = type(exc).__name__
    return out


def main() -> None:
    results: dict[str, dict[str, Any]] = {}
    for fn in (
        probe1_guidance_parallel_and_lifecycle,
        probe2_consensus_denominator_and_role,
        probe3_longitudinal_vs_singletimepoint,
        probe4_forest_no_derive_parallel_arms,
        probe5_sort_default_unknown_reset,
    ):
        try:
            results[fn.__name__] = fn()
        except Exception as exc:
            results[fn.__name__] = {
                "probe": fn.__name__,
                "exception": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(),
            }
    print(json.dumps(results, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()