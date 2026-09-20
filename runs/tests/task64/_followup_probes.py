"""Task 6.4 follow-up probes — focused on Codex targeted fixes.

Targets:
1. Broad product/trial/arm sample-size keys must not lend N to another arm.
2. Precise triple-key (product, trial, arm) and nested trial-scoped arm key still work.
3. Multiple safety time-windows must be "pending_verification + ask user to select", never "未报告".
4. Existing safety dimension but unmatched filter must NOT be labeled "未报告" with a TEAE-flavoured reason.
5. When no unique overall-TEAE exists, default must NOT silently fall back to SAE/AESI.
6. Effect-measure form must be part of the comparison bucket (RD vs OR can't collide).
"""
from __future__ import annotations

from ci_workflow.domain.enums import FactDisclosureState
from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.reports.a.analysis import EndpointDirection
from ci_workflow.reports.b.efficacy import EfficacyArmRole, EfficacyFactRow
from ci_workflow.reports.b.pages import (
    MatrixComparisonStatus,
    MatrixSelectionState,
    build_bubble_matrix,
    build_matrix_comparison_rows,
    build_matrix_view_state,
)
from ci_workflow.reports.b.safety import SafetyArmRole, SafetyFactRow, SafetyFamily

EASI = "endpoint-easi75-response-v1"
NPS = "endpoint-nps-change-v1"
WK12 = "timepoint-week-12-v1"

_LOC = EvidenceLocator(document_role="trial-results", table="T", row="r", column="c")


def E(row_id, *, arm_role, arm_id, value=60.0,
       direction=EndpointDirection.HIGHER_IS_BETTER,
       product="p", trial="T1", endpoint=EASI,
       effect_measure=None, analysis_form=None, unit="%",
       analysis_population="FAS"):
    if endpoint == NPS:
        unit = "points"
        analysis_form = analysis_form or "change_from_baseline"
        orig_ep = "nps"
        orig_def = "鼻息肉评分变化"
        if direction is EndpointDirection.HIGHER_IS_BETTER:
            direction = EndpointDirection.LOWER_IS_BETTER
    else:
        unit = unit or "%"
        analysis_form = analysis_form or "response_rate"
        orig_ep = "easi75"
        orig_def = "EASI-75"
    return EfficacyFactRow(
        row_id=row_id, source_row_id=f"s-{row_id}", observation_id=f"o-{row_id}",
        product_id=product, trial_id=trial, endpoint_family_id=endpoint,
        endpoint_family_label_zh="应答率", compatibility_key=(endpoint, WK12),
        original_endpoint=orig_ep, original_definition=orig_def,
        endpoint_role="primary", direction=direction, unit=unit,
        analysis_form=analysis_form, actual_timepoint=12, actual_timepoint_unit="week",
        analysis_population=analysis_population, arm_role=arm_role, arm_id=arm_id,
        arm_label="治疗组" if arm_role is EfficacyArmRole.TREATMENT else "安慰剂",
        value=value, denominator=100,
        effect_measure=effect_measure,
        disclosure_state=FactDisclosureState.REPORTED_VALUE,
        source_version_id="v1", source_locator=_LOC,
    )


def S(row_id, *, arm_role, arm_id, value=20.0,
       state=FactDisclosureState.REPORTED_VALUE,
       product="p", trial="T1", denom=100, unit="%", term="teae-any",
       family=SafetyFamily.TEAE,
       time_window_zh="治疗期间", population_zh="安全性分析集"):
    return SafetyFactRow(
        row_id=row_id, source_row_id=f"s-{row_id}", observation_id=f"o-{row_id}",
        product_id=product, trial_id=trial, family=family,
        term_id=term, source_term="任何治疗期间不良事件",
        event_definition_zh="治疗期间出现的不良事件", time_window_zh=time_window_zh,
        analysis_population_zh=population_zh,
        arm_role=arm_role, arm_id=arm_id,
        arm_label="治疗组" if arm_role is SafetyArmRole.TREATMENT else "安慰剂",
        value=value, raw_value=f"{value:g}%" if value is not None else "原文未报告",
        unit=unit, denominator=denom, disclosure_state=state,
        source_version_id="v1", source_locator=_LOC,
    )


def section(name):
    print(f"\n===== {name} =====")


def probe(label, ok, info=""):
    print(f"[{'OK' if ok else 'FAIL'}] {label} :: {info}")


def _broad_key_no_lend():
    section("Broad sample-size keys cannot lend N to a trial arm")
    eff = [E("et", arm_role=EfficacyArmRole.TREATMENT, arm_id="arm-treatment"),
           E("ec", arm_role=EfficacyArmRole.CONTROL, arm_id="arm-control", value=30.0)]
    sfy = [S("st", arm_role=SafetyArmRole.TREATMENT, arm_id="arm-treatment"),
           S("sc", arm_role=SafetyArmRole.CONTROL, arm_id="arm-control", value=10.0)]

    for broad_key in ("p", "T1", "arm-treatment", ("p", "T1")):
        view = build_bubble_matrix(
            eff, sfy, treatment_sample_sizes={broad_key: 999},
        )
        ok = view.comparison_rows[0].treatment_sample_size is None
        ok2 = view.comparison_rows[0].status is MatrixComparisonStatus.PENDING_VERIFICATION
        ok3 = view.points == ()
        probe(f"broad_key={broad_key}: N is None, PENDING_VERIFICATION, no point",
              ok and ok2 and ok3,
              f"N={view.comparison_rows[0].treatment_sample_size}, "
              f"status={view.comparison_rows[0].status}, points={len(view.points)}")


def _precise_keys_still_work():
    section("Precise triple-key and nested scoped arm key still work")
    eff = [E("et", arm_role=EfficacyArmRole.TREATMENT, arm_id="arm-treatment"),
           E("ec", arm_role=EfficacyArmRole.CONTROL, arm_id="arm-control", value=30.0)]
    sfy = [S("st", arm_role=SafetyArmRole.TREATMENT, arm_id="arm-treatment"),
           S("sc", arm_role=SafetyArmRole.CONTROL, arm_id="arm-control", value=10.0)]

    v1 = build_bubble_matrix(
        eff, sfy,
        treatment_sample_sizes={("p", "T1", "arm-treatment"): 120},
    )
    probe("triple-key (p,T1,arm-treatment) → N=120 COMPARABLE point",
          v1.points[0].treatment_sample_size == 120
          and v1.comparison_rows[0].status is MatrixComparisonStatus.COMPARABLE,
          f"N={v1.points[0].treatment_sample_size if v1.points else None}")

    v2 = build_bubble_matrix(
        eff, sfy,
        treatment_sample_sizes={("p", "T1"): {"arm-treatment": 123}},
    )
    probe("trial-scoped nested arm key → N=123 COMPARABLE point",
          v2.points[0].treatment_sample_size == 123
          and v2.comparison_rows[0].status is MatrixComparisonStatus.COMPARABLE,
          f"N={v2.points[0].treatment_sample_size if v2.points else None}")

    v3 = build_bubble_matrix(
        eff, sfy,
        treatment_sample_sizes={("p", "T1"): {"arm-treatmentXXX": 999}},
    )
    probe("trial-scoped nested with WRONG arm name → no lend (None + PENDING)",
          v3.comparison_rows[0].treatment_sample_size is None
          and v3.comparison_rows[0].status is MatrixComparisonStatus.PENDING_VERIFICATION,
          f"N={v3.comparison_rows[0].treatment_sample_size}")


def _multi_safety_window():
    section("Multiple safety time-windows require selection, never '未报告'")
    eff = [E("et", arm_role=EfficacyArmRole.TREATMENT, arm_id="arm-treatment"),
           E("ec", arm_role=EfficacyArmRole.CONTROL, arm_id="arm-control", value=30.0)]
    sfy = [
        S("st1", arm_role=SafetyArmRole.TREATMENT, arm_id="arm-treatment",
          value=18.0, time_window_zh="治疗16周"),
        S("sc1", arm_role=SafetyArmRole.CONTROL, arm_id="arm-control",
          value=8.0, time_window_zh="治疗16周"),
        S("st2", arm_role=SafetyArmRole.TREATMENT, arm_id="arm-treatment",
          value=35.0, time_window_zh="整个研究期"),
        S("sc2", arm_role=SafetyArmRole.CONTROL, arm_id="arm-control",
          value=25.0, time_window_zh="整个研究期"),
    ]
    state = build_matrix_view_state(
        eff, sfy,
        treatment_sample_sizes={("p", "T1", "arm-treatment"): 100},
    )
    sel = state.selection
    row = state.comparison_rows[0]
    cell_reason = state.complete_table[0].reason_zh if state.complete_table else ""
    probe("no safety_time_window selected → multiple contexts detected",
          sel.safety_time_window_zh is None
          and row.status is MatrixComparisonStatus.PENDING_VERIFICATION
          and state.chart.points == (),
          f"time_window={sel.safety_time_window_zh}, "
          f"status={row.status}, points={len(state.chart.points)}")
    probe("reason mentions '多个安全性统计口径'",
          "存在多个安全性统计口径" in cell_reason or "存在多个安全性统计口径" in (row.status_reason_zh or ""),
          f"cell={cell_reason!r}, row={row.status_reason_zh!r}")
    probe("does NOT say 未报告",
          "未报告" not in cell_reason and "未报告" not in (row.status_reason_zh or ""),
          f"cell={cell_reason!r}")


def _existing_dim_unmatched_filter():
    section("Existing safety dimension but unmatched filter is not '未报告'")
    eff = [E("et", arm_role=EfficacyArmRole.TREATMENT, arm_id="arm-treatment"),
           E("ec", arm_role=EfficacyArmRole.CONTROL, arm_id="arm-control", value=30.0)]
    sfy = [
        S("st", arm_role=SafetyArmRole.TREATMENT, arm_id="arm-treatment",
          value=18.0, time_window_zh="整个研究期"),
        S("sc", arm_role=SafetyArmRole.CONTROL, arm_id="arm-control",
          value=8.0, time_window_zh="整个研究期"),
    ]
    rows = build_matrix_comparison_rows(
        eff, sfy,
        safety_time_window_zh="治疗16周",
        treatment_sample_sizes={("p", "T1", "arm-treatment"): 100},
    )
    row = rows[0]
    probe("filter mismatch on existing dim → PENDING_VERIFICATION (not 未报告)",
          row.status is MatrixComparisonStatus.PENDING_VERIFICATION
          and "未报告" not in (row.status_reason_zh or ""),
          f"status={row.status}, reason={row.status_reason_zh!r}")
    probe("reason explicitly says '已有该安全性维度数据'",
          "已有该安全性维度数据" in (row.status_reason_zh or ""),
          f"reason={row.status_reason_zh!r}")


def _no_overall_teae_no_silent_default():
    section("No overall-TEAE → default must NOT silently fall back to SAE/AESI")
    eff = [E("et", arm_role=EfficacyArmRole.TREATMENT, arm_id="arm-treatment"),
           E("ec", arm_role=EfficacyArmRole.CONTROL, arm_id="arm-control", value=30.0)]
    sfy_sae_only = [
        S("st-sae", arm_role=SafetyArmRole.TREATMENT, arm_id="arm-treatment",
          value=3.0, term="sae-any", family=SafetyFamily.SAE,
          time_window_zh="治疗期间"),
        S("sc-sae", arm_role=SafetyArmRole.CONTROL, arm_id="arm-control",
          value=2.0, term="sae-any", family=SafetyFamily.SAE,
          time_window_zh="治疗期间"),
    ]
    sel = MatrixSelectionState.from_facts(efficacy_facts=eff, safety_facts=sfy_sae_only)
    probe("safety_family default is TEAE (not silently SAE)",
          sel.safety_family is SafetyFamily.TEAE,
          f"safety_family={sel.safety_family}")
    probe("safety_term_id default is None when no unique overall TEAE",
          sel.safety_term_id is None,
          f"safety_term_id={sel.safety_term_id}")
    probe("safety_time_window_zh default is None (no silent overall-study default)",
          sel.safety_time_window_zh is None,
          f"time_window_zh={sel.safety_time_window_zh}")


def _effect_measure_bucketing():
    section("Effect-measure form is part of bucketing (RD vs OR must not collide)")
    eff_rd_or = [
        E("et", arm_role=EfficacyArmRole.TREATMENT, arm_id="arm-treatment",
          value=60.0, effect_measure="risk_difference"),
        E("ec", arm_role=EfficacyArmRole.CONTROL, arm_id="arm-control",
          value=30.0, effect_measure="odds_ratio"),
    ]
    sfy = [S("st", arm_role=SafetyArmRole.TREATMENT, arm_id="arm-treatment"),
           S("sc", arm_role=SafetyArmRole.CONTROL, arm_id="arm-control", value=10.0)]
    rows = build_matrix_comparison_rows(
        eff_rd_or, sfy,
        treatment_sample_sizes={("p", "T1", "arm-treatment"): 100},
    )
    print("rows produced:", len(rows))
    ids = [r.comparison_row_id for r in rows]
    probe("different effect_measure → split into two rows (no cross-arm signal)",
          len(rows) == 2
          and rows[0].efficacy_treatment is None and rows[0].efficacy_control is not None
          and rows[1].efficacy_treatment is not None and rows[1].efficacy_control is None,
          f"ids={ids}")
    probe("cross-arm efficacy_signal is None for both rows",
          all(r.efficacy_signal is None for r in rows))
    probe("raw T and raw C values preserved on their respective rows",
          any(r.raw_treatment_efficacy_value == 60.0 for r in rows)
          and any(r.raw_control_efficacy_value == 30.0 for r in rows))
    if len(set(ids)) < len(ids):
        print("[GAP] comparison_row_id collisions across distinct effect-measure rows;"
              " comparison_row_id is missing effect_measure in row_material")
    else:
        probe("comparison_row_id is unique across effect-measure buckets", True)


def _run():
    _broad_key_no_lend()
    _precise_keys_still_work()
    _multi_safety_window()
    _existing_dim_unmatched_filter()
    _no_overall_teae_no_silent_default()
    _effect_measure_bucketing()


_run()
print("\nAll follow-up probes complete.")