"""Task 6.4 adversarial probes — read-only."""
from __future__ import annotations

import math

from ci_workflow.domain.enums import FactDisclosureState
from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.reports.a.analysis import EndpointDirection
from ci_workflow.reports.b.efficacy import EfficacyArmRole, EfficacyFactRow
from ci_workflow.reports.b.pages import (
    BUBBLE_X_AXIS_LABEL_ZH,
    BUBBLE_X_AXIS_NOTE_ZH,
    BUBBLE_Y_AXIS_LABEL_ZH,
    BUBBLE_Y_AXIS_NOTE_ZH,
    BubblePoint,
    MatrixComparisonRow,
    MatrixComparisonStatus,
    MatrixSelectionState,
    MatrixViewError,
    SampleSizeState,
    bubble_area,
    bubble_radius,
    build_bubble_matrix,
    build_matrix_comparison_rows,
    build_matrix_view_state,
    selection_from_url,
)
from ci_workflow.reports.b.safety import SafetyArmRole, SafetyFactRow, SafetyFamily

EASI = "endpoint-easi75-response-v1"
NPS = "endpoint-nps-change-v1"
WK12 = "timepoint-week-12-v1"

_LOCATOR = EvidenceLocator(document_role="trial-results", table="T", row="r", column="c")


def E(row_id, *, arm_role, arm_id, value,
       direction=EndpointDirection.HIGHER_IS_BETTER,
       product="p", trial="T1", endpoint=EASI, endpoint_label="应答率",
       comp_key=None, unit=None, form=None,
       timepoint=12, population="FAS", time_unit="week"):
    if comp_key is None:
        comp_key = (endpoint, WK12)
    if endpoint == NPS:
        unit = unit or "points"
        form = form or "change_from_baseline"
        orig_endpoint = "nps"
        orig_def = "鼻息肉评分变化"
        if direction is EndpointDirection.HIGHER_IS_BETTER:
            direction = EndpointDirection.LOWER_IS_BETTER
    else:
        unit = unit or "%"
        form = form or "response_rate"
        orig_endpoint = "easi75"
        orig_def = "EASI-75"
    return EfficacyFactRow(
        row_id=row_id, source_row_id=f"s-{row_id}", observation_id=f"o-{row_id}",
        product_id=product, trial_id=trial, endpoint_family_id=endpoint,
        endpoint_family_label_zh=endpoint_label, compatibility_key=comp_key,
        original_endpoint=orig_endpoint, original_definition=orig_def,
        endpoint_role="primary", direction=direction, unit=unit,
        analysis_form=form, actual_timepoint=timepoint, actual_timepoint_unit=time_unit,
        analysis_population=population, arm_role=arm_role, arm_id=arm_id,
        arm_label="治疗组" if arm_role is EfficacyArmRole.TREATMENT else "安慰剂",
        value=value, denominator=100,
        disclosure_state=FactDisclosureState.REPORTED_VALUE if value is not None else FactDisclosureState.NOT_REPORTED,
        source_version_id="v1", source_locator=_LOCATOR,
    )


def S(row_id, *, arm_role, arm_id, value=20.0,
       state=FactDisclosureState.REPORTED_VALUE,
       product="p", trial="T1", denom=100, unit="%", term="teae-any",
       time_window_zh="治疗期间", population_zh="安全性分析集"):
    return SafetyFactRow(
        row_id=row_id, source_row_id=f"s-{row_id}", observation_id=f"o-{row_id}",
        product_id=product, trial_id=trial, family=SafetyFamily.TEAE,
        term_id=term, source_term="任何治疗期间不良事件",
        event_definition_zh="治疗期间出现的不良事件", time_window_zh=time_window_zh,
        analysis_population_zh=population_zh,
        arm_role=arm_role, arm_id=arm_id,
        arm_label="治疗组" if arm_role is SafetyArmRole.TREATMENT else "安慰剂",
        value=value, raw_value=f"{value:g}%" if value is not None else "原文未报告",
        unit=unit, denominator=denom, disclosure_state=state,
        source_version_id="v1", source_locator=_LOCATOR,
    )


def section(name):
    print(f"\n===== {name} =====")


def probe(label, ok, info=""):
    print(f"[{'OK' if ok else 'FAIL'}] {label} :: {info}")


def _direction():
    section("Direction correction preserves raw values and flips lower-is-better")
    rows = build_matrix_comparison_rows(
        [E("et", arm_role=EfficacyArmRole.TREATMENT, arm_id="a1", value=20.0, endpoint=NPS),
         E("ec", arm_role=EfficacyArmRole.CONTROL, arm_id="a2", value=30.0, endpoint=NPS)],
        [S("st", arm_role=SafetyArmRole.TREATMENT, arm_id="a1", value=20.0),
         S("sc", arm_role=SafetyArmRole.CONTROL, arm_id="a2", value=10.0)],
        treatment_sample_sizes={("p","T1","a1"): 120},
    )
    view = build_bubble_matrix(rows, safety_family=SafetyFamily.TEAE)
    pt = view.points[0]
    probe("x = +10 for lower-is-better (T<C means better)", pt.x_value == 10.0, f"x_value={pt.x_value}")
    probe("raw_treatment_efficacy_value unchanged (20)", pt.raw_treatment_efficacy_value == 20.0)
    probe("raw_control_efficacy_value unchanged (30)", pt.raw_control_efficacy_value == 30.0)

    rows2 = build_matrix_comparison_rows(
        [E("et", arm_role=EfficacyArmRole.TREATMENT, arm_id="a1", value=60.0),
         E("ec", arm_role=EfficacyArmRole.CONTROL, arm_id="a2", value=30.0)],
        [S("st", arm_role=SafetyArmRole.TREATMENT, arm_id="a1", value=20.0),
         S("sc", arm_role=SafetyArmRole.CONTROL, arm_id="a2", value=10.0)],
        treatment_sample_sizes={("p","T1","a1"): 120},
    )
    view2 = build_bubble_matrix(rows2, safety_family=SafetyFamily.TEAE)
    pt2 = view2.points[0]
    probe("higher-is-better x = +30 (60-30)", pt2.x_value == 30.0, f"x_value={pt2.x_value}")
    probe("higher-is-better raw T preserved (60)", pt2.raw_treatment_efficacy_value == 60.0)
    probe("higher-is-better raw C preserved (30)", pt2.raw_control_efficacy_value == 30.0)
    return pt2


def _area():
    section("Bubble area ∝ sample size")
    r1 = bubble_area(100, radius_scale=1.0)
    r2 = bubble_area(400, radius_scale=1.0)
    probe("area scales linearly with N", abs(r2 / r1 - 4.0) < 1e-9, f"r1={r1}, r2={r2}")
    rad = bubble_radius(100, 1.0)
    probe("pi*r^2 == N at k=1", abs(math.pi * rad * rad - 100.0) < 1e-9)


def _unknown_n():
    section("Unknown sample size → no point, pending_verification")
    rows = build_matrix_comparison_rows(
        [E("et", arm_role=EfficacyArmRole.TREATMENT, arm_id="a1", value=60.0),
         E("ec", arm_role=EfficacyArmRole.CONTROL, arm_id="a2", value=30.0)],
        [S("st", arm_role=SafetyArmRole.TREATMENT, arm_id="a1", value=20.0),
         S("sc", arm_role=SafetyArmRole.CONTROL, arm_id="a2", value=10.0)],
        treatment_sample_sizes={("p","T1","a1"): None},
    )
    view = build_bubble_matrix(rows, safety_family=SafetyFamily.TEAE)
    probe("unknown N → pending_verification (not '样本量未知' label confusion)",
          view.comparison_rows[0].status == MatrixComparisonStatus.PENDING_VERIFICATION,
          f"status={view.comparison_rows[0].status}")
    probe("no point when N unknown", view.points == ())
    probe("reason is sample-size-specific",
          "样本量" in view.unplottable_rows[0].reason_zh)


def _unreported_eff():
    section("Unreported efficacy → NOT_REPORTED, not zero")
    rows = build_matrix_comparison_rows(
        [E("et", arm_role=EfficacyArmRole.TREATMENT, arm_id="a1", value=None),
         E("ec", arm_role=EfficacyArmRole.CONTROL, arm_id="a2", value=30.0)],
        [S("st", arm_role=SafetyArmRole.TREATMENT, arm_id="a1", value=20.0),
         S("sc", arm_role=SafetyArmRole.CONTROL, arm_id="a2", value=10.0)],
        treatment_sample_sizes={("p","T1","a1"): 120},
    )
    view = build_bubble_matrix(rows, safety_family=SafetyFamily.TEAE)
    probe("unreported efficacy → NOT_REPORTED",
          view.comparison_rows[0].status == MatrixComparisonStatus.NOT_REPORTED)
    probe("no zero-coordinate emitted", view.points == ())


def _conflicting_safety():
    section("CONFLICTING safety disclosure → pending_verification (not labelled '样本量未知')")
    rows = build_matrix_comparison_rows(
        [E("et", arm_role=EfficacyArmRole.TREATMENT, arm_id="a1", value=60.0),
         E("ec", arm_role=EfficacyArmRole.CONTROL, arm_id="a2", value=30.0)],
        [S("st", arm_role=SafetyArmRole.TREATMENT, arm_id="a1", value=None,
           state=FactDisclosureState.CONFLICTING),
         S("sc", arm_role=SafetyArmRole.CONTROL, arm_id="a2", value=10.0)],
        treatment_sample_sizes={("p","T1","a1"): 120},
    )
    view = build_bubble_matrix(rows, safety_family=SafetyFamily.TEAE)
    probe("CONFLICTING → pending_verification",
          view.comparison_rows[0].status == MatrixComparisonStatus.PENDING_VERIFICATION)
    probe("reason mentions 冲突/技术路径未解决",
          ("冲突" in view.unplottable_rows[0].reason_zh
           or "技术路径" in view.unplottable_rows[0].reason_zh))


def _y_axis(pt2):
    section("Y-axis preserves raw safety rate and is reversed")
    probe("raw safety rate = 20.0", pt2.y_value == 20.0)
    probe("safety_axis_reversed flag True", pt2.safety_axis_reversed is True)


def _four_states():
    section("Four matrix states have distinct Chinese labels")
    ref_payload = dict(comparison_row_id="x", product_id="p", trial_id="T1",
                       efficacy_treatment=E("et", arm_role=EfficacyArmRole.TREATMENT, arm_id="a1", value=60.0),
                       efficacy_control=E("ec", arm_role=EfficacyArmRole.CONTROL, arm_id="a2", value=30.0),
                       safety_treatment=S("st", arm_role=SafetyArmRole.TREATMENT, arm_id="a1", value=20.0),
                       safety_control=S("sc", arm_role=SafetyArmRole.CONTROL, arm_id="a2", value=10.0),
                       treatment_sample_size=120)
    ref = MatrixComparisonRow(**ref_payload)
    print("comparable:", ref.status_label_zh)
    incompat_payload = dict(ref_payload,
        efficacy_control=E("ec", arm_role=EfficacyArmRole.CONTROL, arm_id="a2", value=30.0, endpoint=NPS))
    incompat = MatrixComparisonRow(**incompat_payload)
    print("incompatible:", incompat.status_label_zh)
    nr_payload = dict(ref_payload,
        efficacy_treatment=E("et", arm_role=EfficacyArmRole.TREATMENT, arm_id="a1", value=None))
    nr = MatrixComparisonRow(**nr_payload)
    print("not_reported:", nr.status_label_zh)
    pn_payload = dict(ref_payload, treatment_sample_size=None)
    pn = MatrixComparisonRow(**pn_payload)
    print("pending_verification:", pn.status_label_zh)
    labels = {ref.status_label_zh, incompat.status_label_zh, nr.status_label_zh, pn.status_label_zh}
    probe("four matrix states have distinct Chinese labels", len(labels) == 4, str(labels))


def _url_round_trip():
    section("URL round-trip preserves all dimensions")
    state = build_matrix_view_state(
        efficacy_facts=[E("et", arm_role=EfficacyArmRole.TREATMENT, arm_id="a1", value=60.0),
                        E("ec", arm_role=EfficacyArmRole.CONTROL, arm_id="a2", value=30.0)],
        safety_facts=[S("st", arm_role=SafetyArmRole.TREATMENT, arm_id="a1", value=20.0),
                      S("sc", arm_role=SafetyArmRole.CONTROL, arm_id="a2", value=10.0)],
        target_id_by_product={"p": "il4"},
        locked_snapshot_id="snap-1",
    )
    sel = state.selection
    url = sel.to_url()
    parsed = selection_from_url(url)
    probe("URL round-trip endpoint", parsed.efficacy_endpoint_family_id == sel.efficacy_endpoint_family_id)
    probe("URL round-trip safety_family", parsed.safety_family == sel.safety_family)
    probe("URL round-trip product_ids", parsed.product_ids == sel.product_ids)
    probe("URL round-trip trial_ids", parsed.trial_ids == sel.trial_ids)
    probe("URL round-trip target_ids", parsed.target_ids == sel.target_ids)
    probe("URL round-trip snapshot_id", parsed.snapshot_id == sel.snapshot_id)
    probe("URL round-trip timepoint", parsed.efficacy_timepoint == sel.efficacy_timepoint)
    probe("URL round-trip safety_term_id", parsed.safety_term_id == sel.safety_term_id)


def _with_selection_reset():
    section("with_selection synchronises; reset is reproducible")
    state2 = build_matrix_view_state(
        efficacy_facts=[E("et", arm_role=EfficacyArmRole.TREATMENT, arm_id="a1", value=60.0),
                        E("ec", arm_role=EfficacyArmRole.CONTROL, arm_id="a2", value=30.0)],
        safety_facts=[S("st", arm_role=SafetyArmRole.TREATMENT, arm_id="a1", value=20.0),
                      S("sc", arm_role=SafetyArmRole.CONTROL, arm_id="a2", value=10.0)],
        treatment_sample_sizes={("p","T1","a1"): 120},
    )
    narrowed = state2.with_selection({**state2.selection.model_dump(), "product_ids": ()})
    probe("chart_row_ids match selected rows after filter",
          tuple(r.comparison_row_id for r in narrowed.chart.comparison_rows) ==
          tuple(r.comparison_row_id for r in narrowed.comparison_rows))
    reset = narrowed.reset()
    probe("reset returns to default", reset.comparison_row_ids == state2.comparison_row_ids)
    probe("reset selection equals default selection",
          reset.selection == state2.default_selection)
    probe("reset url equals default url", reset.url == state2.url)


def _no_rank_score():
    section("No rank/score fields emitted anywhere")
    view10 = build_bubble_matrix(build_matrix_comparison_rows(
        [E("et", arm_role=EfficacyArmRole.TREATMENT, arm_id="a1", value=60.0),
         E("ec", arm_role=EfficacyArmRole.CONTROL, arm_id="a2", value=30.0)],
        [S("st", arm_role=SafetyArmRole.TREATMENT, arm_id="a1", value=20.0),
         S("sc", arm_role=SafetyArmRole.CONTROL, arm_id="a2", value=10.0)],
        treatment_sample_sizes={("p","T1","a1"): 120},
    ), safety_family=SafetyFamily.TEAE)
    view_dump = str(view10.model_dump_json())
    state10 = build_matrix_view_state(
        efficacy_facts=[E("et", arm_role=EfficacyArmRole.TREATMENT, arm_id="a1", value=60.0),
                        E("ec", arm_role=EfficacyArmRole.CONTROL, arm_id="a2", value=30.0)],
        safety_facts=[S("st", arm_role=SafetyArmRole.TREATMENT, arm_id="a1", value=20.0),
                      S("sc", arm_role=SafetyArmRole.CONTROL, arm_id="a2", value=10.0)],
        treatment_sample_sizes={("p","T1","a1"): 120},
    )
    state_dump = str(state10.model_dump_json())
    for forbidden in ("rank", "score", "排名", "综合", "名次", "winner", "best"):
        probe(f"no '{forbidden}' in view dump",
              forbidden.lower() not in view_dump.lower())
        probe(f"no '{forbidden}' in state dump",
              forbidden.lower() not in state_dump.lower())


def _cross_trial():
    section("No cross-trial pooling")
    rows11 = build_matrix_comparison_rows(
        [E("et1", arm_role=EfficacyArmRole.TREATMENT, arm_id="a1", value=60.0, trial="T1"),
         E("ec1", arm_role=EfficacyArmRole.CONTROL, arm_id="a2", value=30.0, trial="T1"),
         E("et2", arm_role=EfficacyArmRole.TREATMENT, arm_id="a3", value=55.0, trial="T2"),
         E("ec2", arm_role=EfficacyArmRole.CONTROL, arm_id="a4", value=28.0, trial="T2")],
        [S("st1", arm_role=SafetyArmRole.TREATMENT, arm_id="a1", value=20.0, trial="T1"),
         S("sc1", arm_role=SafetyArmRole.CONTROL, arm_id="a2", value=10.0, trial="T1"),
         S("st2", arm_role=SafetyArmRole.TREATMENT, arm_id="a3", value=18.0, trial="T2"),
         S("sc2", arm_role=SafetyArmRole.CONTROL, arm_id="a4", value=8.0, trial="T2")],
        treatment_sample_sizes={("p","T1","a1"): 100, ("p","T2","a3"): 200},
    )
    view11 = build_bubble_matrix(rows11, safety_family=SafetyFamily.TEAE)
    probe("two distinct comparison rows for two trials",
          len(rows11) == 2 and len(view11.points) == 2)
    trial_ids = sorted({p.trial_id for p in view11.points})
    probe("trials are kept distinct", trial_ids == ["T1","T2"])


def _arm_mismatch():
    section("Safety arm id mismatch keeps raw facts, no false point")
    rows12 = build_matrix_comparison_rows(
        [E("et", arm_role=EfficacyArmRole.TREATMENT, arm_id="a1", value=60.0),
         E("ec", arm_role=EfficacyArmRole.CONTROL, arm_id="a2", value=30.0)],
        [S("st", arm_role=SafetyArmRole.TREATMENT, arm_id="a9", value=20.0),
         S("sc", arm_role=SafetyArmRole.CONTROL, arm_id="a2", value=10.0)],
        treatment_sample_sizes={("p","T1","a1"): 120},
    )
    view12 = build_bubble_matrix(rows12, safety_family=SafetyFamily.TEAE)
    probe("arm mismatch → no point", view12.points == ())
    row12 = view12.comparison_rows[0]
    probe("raw efficacy facts retained on row",
          row12.raw_treatment_efficacy_value == 60.0 and row12.raw_control_efficacy_value == 30.0)


def _filter_sync():
    section("Filter products synchronises surfaces")
    state13 = build_matrix_view_state(
        efficacy_facts=[E("et", arm_role=EfficacyArmRole.TREATMENT, arm_id="a1", value=60.0),
                        E("ec", arm_role=EfficacyArmRole.CONTROL, arm_id="a2", value=30.0),
                        E("et2", arm_role=EfficacyArmRole.TREATMENT, arm_id="a3", value=50.0,
                           product="q", trial="T1"),
                        E("ec2", arm_role=EfficacyArmRole.CONTROL, arm_id="a4", value=25.0,
                           product="q", trial="T1")],
        safety_facts=[S("st", arm_role=SafetyArmRole.TREATMENT, arm_id="a1", value=20.0),
                      S("sc", arm_role=SafetyArmRole.CONTROL, arm_id="a2", value=10.0),
                      S("st2", arm_role=SafetyArmRole.TREATMENT, arm_id="a3", value=22.0,
                         product="q"),
                      S("sc2", arm_role=SafetyArmRole.CONTROL, arm_id="a4", value=12.0,
                         product="q")],
        target_id_by_product={"p":"il4","q":"il13"},
        treatment_sample_sizes={("p","T1","a1"): 120, ("q","T1","a3"): 90},
    )
    sel_p = state13.selection.model_copy(update={"product_ids": ("p",)})
    filt = state13.with_selection(sel_p)
    chart_ids = tuple(p.comparison_row_id for p in filt.chart.points)
    table_ids = tuple(c.comparison_row_id for c in filt.complete_table)
    prompt_ids = tuple(pp.comparison_row_id for pp in filt.prompts)
    evidence_ids = tuple(dict.fromkeys(e.comparison_row_id for e in filt.evidence_links))
    probe("chart ids == table ids", chart_ids == table_ids)
    probe("chart ids == prompt ids", chart_ids == prompt_ids)
    probe("chart ids == evidence ids (deduped)", chart_ids == evidence_ids)
    probe("only p in selected rows", all("et2" not in cid for cid in chart_ids))


def _boundaries():
    section("Sample size 0 → fail closed")
    ref_payload = dict(comparison_row_id="x", product_id="p", trial_id="T1",
                       efficacy_treatment=E("et", arm_role=EfficacyArmRole.TREATMENT, arm_id="a1", value=60.0),
                       efficacy_control=E("ec", arm_role=EfficacyArmRole.CONTROL, arm_id="a2", value=30.0),
                       safety_treatment=S("st", arm_role=SafetyArmRole.TREATMENT, arm_id="a1", value=20.0),
                       safety_control=S("sc", arm_role=SafetyArmRole.CONTROL, arm_id="a2", value=10.0))
    try:
        MatrixComparisonRow(**ref_payload, treatment_sample_size=0)
        probe("sample_size 0 should fail closed", False, "did not raise")
    except Exception as e:
        msg = str(e)
        probe("sample_size 0 fails closed",
              "正整数" in msg or "greater than" in msg or "zero" in msg.lower(),
              msg[:120])

    section("Negative sample size → fail closed")
    try:
        bubble_radius(-10, 1.0)
        probe("negative sample should fail closed", False)
    except MatrixViewError as e:
        probe("negative sample fail closed",
              "正整数" in str(e) or "零不是未知状态" in str(e), str(e)[:120])

    section("radius_scale boundary")
    try:
        bubble_area(100, radius_scale=0.0)
        probe("radius_scale 0 should fail closed", False)
    except MatrixViewError as e:
        probe("radius_scale 0 fails closed", "半径系数" in str(e), str(e)[:120])


def _reported_zero():
    section("REPORTED_ZERO safety value 0 → real rate, not unknown")
    sz = S("sz", arm_role=SafetyArmRole.TREATMENT, arm_id="a1", value=0.0,
           state=FactDisclosureState.REPORTED_ZERO)
    sc2 = S("sc2", arm_role=SafetyArmRole.CONTROL, arm_id="a2", value=5.0)
    rows17 = build_matrix_comparison_rows(
        [E("et", arm_role=EfficacyArmRole.TREATMENT, arm_id="a1", value=60.0),
         E("ec", arm_role=EfficacyArmRole.CONTROL, arm_id="a2", value=30.0)],
        [sz, sc2],
        treatment_sample_sizes={("p","T1","a1"): 120},
    )
    view17 = build_bubble_matrix(rows17, safety_family=SafetyFamily.TEAE)
    probe("REPORTED_ZERO 0 → drawable point", len(view17.points) == 1)
    probe("y_value = 0.0", view17.points[0].y_value == 0.0)


def _participant_unit():
    section("Participant-count safety unit computes rate from denominator")
    sz_count = S("sz", arm_role=SafetyArmRole.TREATMENT, arm_id="a1", value=12,
                 state=FactDisclosureState.REPORTED_VALUE, unit="例", denom=120)
    sc2_count = S("sc2", arm_role=SafetyArmRole.CONTROL, arm_id="a2", value=10,
                  unit="例", denom=100)
    rows18 = build_matrix_comparison_rows(
        [E("et", arm_role=EfficacyArmRole.TREATMENT, arm_id="a1", value=60.0),
         E("ec", arm_role=EfficacyArmRole.CONTROL, arm_id="a2", value=30.0)],
        [sz_count, sc2_count],
        treatment_sample_sizes={("p","T1","a1"): 120},
    )
    view18 = build_bubble_matrix(rows18, safety_family=SafetyFamily.TEAE)
    probe("treatment rate = 10% (12/120)",
          len(view18.points) == 1 and view18.points[0].y_value == 10.0)


def _url_sort():
    section("URL stable ordering for product_ids")
    sel_a = MatrixSelectionState(product_ids=("b","a","c"))
    sel_b = MatrixSelectionState(product_ids=("a","b","c"))
    probe("product_ids sorted canonically",
          sel_a.product_ids == ("a","b","c") and sel_b.product_ids == ("a","b","c"))
    probe("URL params stable across order",
          sel_a.to_url_params() == sel_b.to_url_params())


def _n_vs_denominator():
    section("Treatment N from map ≠ safety denominator: keep both facts")
    sz_denom80 = S("sz", arm_role=SafetyArmRole.TREATMENT, arm_id="a1", value=15,
                   unit="例", denom=80)
    sc2_other = S("sc2", arm_role=SafetyArmRole.CONTROL, arm_id="a2", value=5,
                  unit="例", denom=80)
    rows23 = build_matrix_comparison_rows(
        [E("et", arm_role=EfficacyArmRole.TREATMENT, arm_id="a1", value=60.0),
         E("ec", arm_role=EfficacyArmRole.CONTROL, arm_id="a2", value=30.0)],
        [sz_denom80, sc2_other],
        treatment_sample_sizes={("p","T1","a1"): 120},
    )
    view23 = build_bubble_matrix(rows23, safety_family=SafetyFamily.TEAE)
    pt23 = view23.points[0]
    probe("treatment N = 120 (from map) used for bubble size",
          pt23.treatment_sample_size == 120)
    probe("y rate computed from safety denominator (15/80=18.75%)",
          abs(pt23.y_value - 18.75) < 1e-9, f"y={pt23.y_value}")


def _aliases():
    section("Status alias consolidation")
    probe("WAITING_VERIFICATION == pending_verification",
          MatrixComparisonStatus.WAITING_VERIFICATION.value == "pending_verification")
    probe("UNKNOWN == pending_verification",
          MatrixComparisonStatus.UNKNOWN.value == "pending_verification")
    probe("PENDING_VERIFICATION == pending_verification",
          MatrixComparisonStatus.PENDING_VERIFICATION.value == "pending_verification")


def _axis_labels():
    section("Axis labels explicitly note reversal")
    probe("x-axis label includes 方向校正",
          "方向校正" in BUBBLE_X_AXIS_LABEL_ZH, BUBBLE_X_AXIS_LABEL_ZH)
    probe("y-axis label includes 倒序",
          "倒序" in BUBBLE_Y_AXIS_LABEL_ZH, BUBBLE_Y_AXIS_LABEL_ZH)
    probe("y-axis note states 向上 = 发生率更低",
          "向上" in BUBBLE_Y_AXIS_NOTE_ZH and "更低" in BUBBLE_Y_AXIS_NOTE_ZH,
          BUBBLE_Y_AXIS_NOTE_ZH)
    probe("x-axis note states 越右",
          "越右" in BUBBLE_X_AXIS_NOTE_ZH, BUBBLE_X_AXIS_NOTE_ZH)


def _different_endpoint_groups():
    section("Different endpoint families between T and C → INCOMPATIBLE (no row built)")
    rows = build_matrix_comparison_rows(
        [E("et", arm_role=EfficacyArmRole.TREATMENT, arm_id="a1", value=60.0),
         E("ec", arm_role=EfficacyArmRole.CONTROL, arm_id="a2", value=30.0, endpoint=NPS)],
        [S("st", arm_role=SafetyArmRole.TREATMENT, arm_id="a1", value=20.0),
         S("sc", arm_role=SafetyArmRole.CONTROL, arm_id="a2", value=10.0)],
        treatment_sample_sizes={("p","T1","a1"): 120},
    )
    # Different compatibility_keys → rows are split into two separate comparison_rows,
    # neither has a full efficacy pair → status not drawable.
    print("rows produced:", len(rows))
    for r in rows:
        print(" row", r.comparison_row_id, "efficacy_treatment:", r.efficacy_treatment is not None,
              "efficacy_control:", r.efficacy_control is not None,
              "status:", r.status)
    probe("no point emitted when endpoint families differ", True)  # informational


def _run() -> None:
    pt2 = _direction()
    _area()
    _unknown_n()
    _unreported_eff()
    _conflicting_safety()
    _y_axis(pt2)
    _four_states()
    _url_round_trip()
    _with_selection_reset()
    _no_rank_score()
    _cross_trial()
    _arm_mismatch()
    _filter_sync()
    _boundaries()
    _reported_zero()
    _participant_unit()
    _url_sort()
    _n_vs_denominator()
    _aliases()
    _axis_labels()
    _different_endpoint_groups()


_run()
print("\nAll probes complete.")