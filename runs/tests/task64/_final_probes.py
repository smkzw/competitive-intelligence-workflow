"""Task 6.4 final follow-up probes — only the two residual checks.

Targets:
A. Different effect_measure buckets keep unique comparison_row_ids AND never subtract.
B. Switching safety_family clears the prior family-dependent filters (term/event_def/window/pop/denom)
   and lets the new family hit its unique fact.
"""
from __future__ import annotations

from ci_workflow.domain.enums import FactDisclosureState
from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.reports.a.analysis import EndpointDirection
from ci_workflow.reports.b.efficacy import EfficacyArmRole, EfficacyFactRow
from ci_workflow.reports.b.pages import (
    MatrixComparisonStatus,
    apply_matrix_selection,
    build_bubble_matrix,
    build_matrix_comparison_rows,
    build_matrix_view_state,
)
from ci_workflow.reports.b.safety import SafetyArmRole, SafetyFactRow, SafetyFamily

EASI = "endpoint-easi75-response-v1"
WK12 = "timepoint-week-12-v1"
_LOC = EvidenceLocator(document_role="trial-results", table="T", row="r", column="c")


def E(row_id, *, arm_role, arm_id, value=60.0,
       direction=EndpointDirection.HIGHER_IS_BETTER,
       product="p", trial="T1", effect_measure=None):
    return EfficacyFactRow(
        row_id=row_id, source_row_id=f"s-{row_id}", observation_id=f"o-{row_id}",
        product_id=product, trial_id=trial, endpoint_family_id=EASI,
        endpoint_family_label_zh="应答率", compatibility_key=(EASI, WK12),
        original_endpoint="easi75", original_definition="EASI-75",
        endpoint_role="primary", direction=direction, unit="%",
        analysis_form="response_rate", actual_timepoint=12, actual_timepoint_unit="week",
        analysis_population="FAS", arm_role=arm_role, arm_id=arm_id,
        arm_label="治疗组" if arm_role is EfficacyArmRole.TREATMENT else "安慰剂",
        value=value, denominator=100, effect_measure=effect_measure,
        disclosure_state=FactDisclosureState.REPORTED_VALUE,
        source_version_id="v1", source_locator=_LOC,
    )


def S(row_id, *, arm_role, arm_id, value=20.0,
       state=FactDisclosureState.REPORTED_VALUE,
       product="p", trial="T1", denom=100, unit="%", term="teae-any",
       family=SafetyFamily.TEAE,
       time_window_zh="治疗期间", population_zh="安全性分析集",
       source_term="任何治疗期间不良事件",
       event_definition_zh="治疗期间出现的不良事件",
       denom_semantics=None):
    return SafetyFactRow(
        row_id=row_id, source_row_id=f"s-{row_id}", observation_id=f"o-{row_id}",
        product_id=product, trial_id=trial, family=family,
        term_id=term, source_term=source_term,
        event_definition_zh=event_definition_zh, time_window_zh=time_window_zh,
        analysis_population_zh=population_zh,
        arm_role=arm_role, arm_id=arm_id,
        arm_label="治疗组" if arm_role is SafetyArmRole.TREATMENT else "安慰剂",
        value=value, raw_value=f"{value:g}%" if value is not None else "原文未报告",
        unit=unit, denominator=denom, disclosure_state=state,
        denominator_semantics_zh=denom_semantics,
        source_version_id="v1", source_locator=_LOC,
    )


def section(name):
    print(f"\n===== {name} =====")


def probe(label, ok, info=""):
    print(f"[{'OK' if ok else 'FAIL'}] {label} :: {info}")


def _effect_measure_unique_row_ids():
    """A. Different effect_measure → unique row_ids, no subtraction across arms."""
    section("Effect-measure buckets keep unique row_ids and never subtract")

    # 1. RD vs OR
    rd_t = E("et", arm_role=EfficacyArmRole.TREATMENT, arm_id="arm-treatment",
             value=60.0, effect_measure="risk_difference")
    or_c = E("ec", arm_role=EfficacyArmRole.CONTROL, arm_id="arm-control",
             value=30.0, effect_measure="odds_ratio")
    sfy = [S("st", arm_role=SafetyArmRole.TREATMENT, arm_id="arm-treatment"),
           S("sc", arm_role=SafetyArmRole.CONTROL, arm_id="arm-control", value=10.0)]

    rows = build_matrix_comparison_rows(
        (rd_t, or_c), sfy,
        treatment_sample_sizes={("p", "T1", "arm-treatment"): 100},
    )
    probe("RD vs OR → 2 distinct comparison_row_ids",
          len(rows) == 2 and len({r.comparison_row_id for r in rows}) == 2,
          f"ids={[r.comparison_row_id for r in rows]}")
    probe("cross-bucket efficacy_signal = None (no subtraction across effect_measure)",
          all(r.efficacy_signal is None for r in rows))
    probe("raw T value preserved on RD bucket, raw C value on OR bucket",
          any(r.raw_treatment_efficacy_value == 60.0 for r in rows)
          and any(r.raw_control_efficacy_value == 30.0 for r in rows))
    probe("BubbleMatrixView no longer raises 'row_id collision'",
          len(build_bubble_matrix((rd_t, or_c), sfy,
                                  treatment_sample_sizes={("p", "T1", "arm-treatment"): 100}).points)
          >= 0)

    # 2. RR vs HR (both ratios but different effect-measure forms)
    rr_t = E("et", arm_role=EfficacyArmRole.TREATMENT, arm_id="arm-treatment",
             value=60.0, effect_measure="risk_ratio")
    hr_c = E("ec", arm_role=EfficacyArmRole.CONTROL, arm_id="arm-control",
             value=30.0, effect_measure="hazard_ratio")
    rows2 = build_matrix_comparison_rows(
        (rr_t, hr_c), sfy,
        treatment_sample_sizes={("p", "T1", "arm-treatment"): 100},
    )
    probe("RR vs HR → 2 distinct comparison_row_ids",
          len(rows2) == 2 and len({r.comparison_row_id for r in rows2}) == 2,
          f"ids={[r.comparison_row_id for r in rows2]}")

    # 3. Same effect_measure on both arms → 1 row, normal subtraction
    rd_both_t = E("et", arm_role=EfficacyArmRole.TREATMENT, arm_id="arm-treatment",
                  value=60.0, effect_measure="risk_difference")
    rd_both_c = E("ec", arm_role=EfficacyArmRole.CONTROL, arm_id="arm-control",
                  value=30.0, effect_measure="risk_difference")
    rows3 = build_matrix_comparison_rows(
        (rd_both_t, rd_both_c), sfy,
        treatment_sample_sizes={("p", "T1", "arm-treatment"): 100},
    )
    probe("matching effect_measure → 1 row, x_value=+30 (60-30)",
          len(rows3) == 1
          and rows3[0].efficacy_signal == 30.0
          and rows3[0].raw_treatment_efficacy_value == 60.0
          and rows3[0].raw_control_efficacy_value == 30.0,
          f"signal={rows3[0].efficacy_signal if rows3 else None}")
    # 4. Mixed: T appears twice with different effect_measure. Each becomes its own row,
    #    C-RD pair becomes a separate row.  No row spans different effect_measure forms.
    rd_only_t = E("et_or", arm_role=EfficacyArmRole.TREATMENT, arm_id="arm-treatment",
                  value=60.0, effect_measure="odds_ratio")
    rows_mixed = build_matrix_comparison_rows(
        (rd_both_t, rd_both_c, rd_only_t), sfy,
        treatment_sample_sizes={("p", "T1", "arm-treatment"): 100},
    )
    pairs = sum(1 for r in rows_mixed
                if r.efficacy_treatment is not None and r.efficacy_control is not None)
    halves = sum(1 for r in rows_mixed
                 if (r.efficacy_treatment is None) != (r.efficacy_control is None))
    probe("mixed (T-RD+C-RD pair + T-OR alone) → two rows, distinct row_ids, RD pair subtracts, OR row has no signal",
          len(rows_mixed) == 2
          and len({r.comparison_row_id for r in rows_mixed}) == 2
          and pairs == 1 and halves == 1
          and sum(1 for r in rows_mixed if r.efficacy_signal == 30.0) == 1
          and sum(1 for r in rows_mixed if r.efficacy_signal is None) == 1,
          f"signals={[r.efficacy_signal for r in rows_mixed]}, "
          f"ids={[r.comparison_row_id for r in rows_mixed]}, "
          f"pairs={pairs}, halves={halves}")



def _switch_safety_family_clears_filters():
    """B. Switching safety_family drops prior family-dependent filters and hits new family fact."""
    section("Switching safety_family drops previous family-dependent filters")

    # Build a snapshot where SAE rows exist (only one context).
    eff = [E("et", arm_role=EfficacyArmRole.TREATMENT, arm_id="arm-treatment"),
           E("ec", arm_role=EfficacyArmRole.CONTROL, arm_id="arm-control", value=30.0)]
    teae = [
        S("st-teae", arm_role=SafetyArmRole.TREATMENT, arm_id="arm-treatment",
          value=20.0, term="teae-any", family=SafetyFamily.TEAE,
          time_window_zh="治疗期间", event_definition_zh="治疗期间不良事件"),
        S("sc-teae", arm_role=SafetyArmRole.CONTROL, arm_id="arm-control",
          value=10.0, term="teae-any", family=SafetyFamily.TEAE,
          time_window_zh="治疗期间", event_definition_zh="治疗期间不良事件"),
    ]
    sae = [
        S("st-sae", arm_role=SafetyArmRole.TREATMENT, arm_id="arm-treatment",
          value=3.0, term="sae-any", family=SafetyFamily.SAE,
          source_term="任何严重不良事件",
          event_definition_zh="研究期间出现的严重不良事件",
          time_window_zh="研究期间", population_zh="全因 SAE 集",
          denom_semantics="全部随机化受试者"),
        S("sc-sae", arm_role=SafetyArmRole.CONTROL, arm_id="arm-control",
          value=2.0, term="sae-any", family=SafetyFamily.SAE,
          source_term="任何严重不良事件",
          event_definition_zh="研究期间出现的严重不良事件",
          time_window_zh="研究期间", population_zh="全因 SAE 集",
          denom_semantics="全部随机化受试者"),
    ]

    initial = build_matrix_view_state(
        eff, (*teae, *sae),
        treatment_sample_sizes={("p", "T1", "arm-treatment"): 100},
    )
    # Force initial selection to anchor on SAE unique facts (term_id="sae-any",
    # event_definition="研究期间出现的严重不良事件", time_window_zh="研究期间",
    # analysis_population_zh="全因 SAE 集", denominator_semantics="全部随机化受试者").
    sel_sae_anchored = initial.selection.model_copy(update={
        "safety_family": SafetyFamily.SAE,
        "safety_term_id": "sae-any",
        "safety_event_definition_zh": "研究期间出现的严重不良事件",
        "safety_time_window_zh": "研究期间",
        "safety_analysis_population_zh": "全因 SAE 集",
        "safety_denominator_semantics_zh": "全部随机化受试者",
    })
    sae_view = initial.with_selection(sel_sae_anchored)
    probe("baseline anchored on SAE → COMPARABLE, y=3.0",
          sae_view.comparison_rows[0].status is MatrixComparisonStatus.COMPARABLE
          and sae_view.chart.points[0].y_value == 3.0,
          f"y={sae_view.chart.points[0].y_value if sae_view.chart.points else None}")

    # Switch back to TEAE without explicitly clearing filters.
    switched = apply_matrix_selection(sae_view, {"safety_family": SafetyFamily.TEAE})
    sel = switched.selection
    probe("safety_family switched to TEAE",
          sel.safety_family is SafetyFamily.TEAE)
    probe("family-dependent filters reset to default (TEAE anchor), no stale SAE leaks",
          sel.safety_term_id == "teae-any"
          and sel.safety_event_definition_zh == "治疗期间不良事件"
          and sel.safety_time_window_zh == "治疗期间"
          and sel.safety_analysis_population_zh == "安全性分析集"
          and sel.safety_denominator_semantics_zh is None,
          f"term={sel.safety_term_id}, "
          f"event_def={sel.safety_event_definition_zh!r}, "
          f"window={sel.safety_time_window_zh!r}, "
          f"pop={sel.safety_analysis_population_zh!r}, "
          f"denom={sel.safety_denominator_semantics_zh!r}")
    probe("switched view COMPARABLE on TEAE rows (hits y=20)",
          switched.comparison_rows[0].status is MatrixComparisonStatus.COMPARABLE
          and switched.chart.points
          and switched.chart.points[0].y_value == 20.0
          and switched.chart.points[0].safety_family is SafetyFamily.TEAE,
          f"y={switched.chart.points[0].y_value if switched.chart.points else None}, "
          f"family={switched.chart.points[0].safety_family if switched.chart.points else None}")
    # URL: should NOT carry the previous SAE "sae-any" term anymore.
    url = sel.to_url()
    probe("URL does not carry stale SAE term/event/window/pop/denom from SAE-anchored selection",
          "event=sae-any" not in url
          and "event_definition=%E7%A0%94%E7%A9%B6" not in url  # 研究
          and "window=%E7%A0%94%E7%A9%B6" not in url
          and "%E5%85%A8%E5%9B%A0%20SAE%20%E9%9B%86" not in url,
          f"url={url}")
    # Reverse direction: TEAE → SAE without clearing filters must also clear.
    sel_teae_anchored = switched.selection.model_copy(update={
        "safety_family": SafetyFamily.TEAE,
        "safety_term_id": "teae-any",
        "safety_event_definition_zh": "治疗期间不良事件",
        "safety_time_window_zh": "治疗期间",
        "safety_analysis_population_zh": "安全性分析集",
    })
    teae_view = switched.with_selection(sel_teae_anchored)
    probe("TEAE anchored → COMPARABLE, y=20",
          teae_view.comparison_rows[0].status is MatrixComparisonStatus.COMPARABLE
          and teae_view.chart.points[0].y_value == 20.0)

    switched2 = apply_matrix_selection(teae_view, {"safety_family": SafetyFamily.SAE})
    sel2 = switched2.selection
    probe("TEAE→SAE family-dependent filters cleared to None",
          sel2.safety_term_id is None
          and sel2.safety_event_definition_zh is None
          and sel2.safety_time_window_zh is None
          and sel2.safety_analysis_population_zh is None
          and sel2.safety_denominator_semantics_zh is None,
          f"term={sel2.safety_term_id}, event_def={sel2.safety_event_definition_zh!r}, "
          f"window={sel2.safety_time_window_zh!r}, pop={sel2.safety_analysis_population_zh!r}, "
          f"denom={sel2.safety_denominator_semantics_zh!r}")
    probe("switched view COMPARABLE on SAE rows (hits y=3)",
          switched2.comparison_rows[0].status is MatrixComparisonStatus.COMPARABLE
          and switched2.chart.points
          and switched2.chart.points[0].y_value == 3.0
          and switched2.chart.points[0].safety_family is SafetyFamily.SAE,
          f"y={switched2.chart.points[0].y_value if switched2.chart.points else None}, "
          f"family={switched2.chart.points[0].safety_family if switched2.chart.points else None}")

    # When the user DOES NOT change safety_family, prior family filters stay.
    same_family = apply_matrix_selection(teae_view, {})  # no-op
    sf = same_family.selection
    probe("no-op apply_matrix_selection keeps prior family filters",
          sf.safety_term_id == "teae-any"
          and sf.safety_event_definition_zh == "治疗期间不良事件"
          and sf.safety_time_window_zh == "治疗期间",
          f"term={sf.safety_term_id}, event_def={sf.safety_event_definition_zh!r}, "
          f"window={sf.safety_time_window_zh!r}")


def _run():
    _effect_measure_unique_row_ids()
    _switch_safety_family_clears_filters()


_run()
print("\nFinal follow-up probes complete.")